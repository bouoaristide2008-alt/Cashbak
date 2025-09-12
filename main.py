#         return
# bot_persistent.py
import json
import os
import re
import time
import logging
from telegram import ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- CONFIG (via variables d'environnement sur Render) ----------
BOT_TOKEN = os.getenv("BOT_TOKEN")                    # token BotFather (obligatoire)
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))           # ton Telegram ID (entier)
CHANNEL_ID = os.getenv("CHANNEL_ID", "")             # ex: "@MonCanal" ou "-1001234567890"
PROMO_CODE = os.getenv("PROMO_CODE", "BCAF")         # ton code promo (facultatif)
PROMO_LINK = os.getenv("PROMO_LINK", "https://ton-lien-1xbet.com")  # lien procédure

BUTTON_LABEL = "🎫 Entrer mon ID 1xBet"
CHECK_DELAY = 5 * 60 * 60  # 5 heures en secondes

# ---------- utilitaires ----------
def load_json_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        logger.exception(f"Erreur lecture {path}: {e}")
        return {}

def save_json_file(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_users():
    return load_json_file("users.json")        # IDs validés (admin les ajoute)

def load_players():
    return load_json_file("players.json")      # enregistrements automatiques

def save_players(players):
    save_json_file("players.json", players)

def extract_first_digits(text):
    if not text:
        return None
    m = re.search(r"(\d+)", text)
    return m.group(1) if m else None

# ---------- scheduling & vérification ----------
def schedule_check(app, telegram_id, bet_id, delay=CHECK_DELAY):
    """
    Persiste la demande dans players.json puis schedule le job via job_queue.
    """
    players = load_players()
    now = int(time.time())
    players[str(telegram_id)] = {
        "username": players.get(str(telegram_id), {}).get("username"),
        "bet_id": bet_id,
        "status": "pending",
        "scheduled_at": now
    }
    save_players(players)

    try:
        app.job_queue.run_once(check_after_delay, when=delay, data={"telegram_id": telegram_id, "bet_id": bet_id})
        logger.info(f"Job scheduled for {telegram_id} in {delay}s (bet_id={bet_id})")
    except Exception as e:
        logger.exception(f"Erreur scheduling job: {e}")

async def check_after_delay(context: ContextTypes.DEFAULT_TYPE):
    """Exécuté par job_queue après délai; notifie l'utilisateur selon users.json"""
    job_data = context.job.data
    telegram_id = job_data["telegram_id"]
    bet_id = job_data["bet_id"]

    users = load_users()
    players = load_players()
    player = players.get(str(telegram_id), {})

    # Marquer checked et sauvegarder
    player["status"] = "checked"
    player["checked_at"] = int(time.time())
    players[str(telegram_id)] = player
    save_players(players)

    if bet_id not in users:
        # message final si pas validé
        try:
            text = (
                f"❌ Votre compte n’a pas été créé avec le code promo {PROMO_CODE}.\n"
                f"Veuillez créer un nouveau compte 1xBet avec le code promo *{PROMO_CODE}* et réessayer.\n\n"
                f"👉 <a href=\"{PROMO_LINK}\">Cliquez ici pour suivre la procédure</a>"
            )
            await context.bot.send_message(chat_id=telegram_id, text=text, parse_mode="HTML")
        except Exception as e:
            logger.warning(f"Erreur envoi message retardé à {telegram_id}: {e}")
    else:
        # si validé
        try:
            await context.bot.send_message(chat_id=telegram_id, text=f"🎉 Votre compte est validé avec le code promo {PROMO_CODE}. Vous recevrez vos remboursements chaque semaine.")
        except Exception as e:
            logger.warning(f"Erreur envoi message validé à {telegram_id}: {e}")

# ---------- handlers ----------
async def start(update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[KeyboardButton(BUTTON_LABEL)]]
    reply_markup = ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("👋 Bienvenue !\n\nClique sur le bouton ci-dessous pour inscrire ton ID 1xBet.", reply_markup=reply_markup)

async def handle_message(update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    users = load_users()
    user = update.effective_user
    tg_username = user.username if user.username else f"id:{user.id}"

    # clic sur bouton
    if text == BUTTON_LABEL:
        context.user_data["awaiting_id"] = True
        await update.message.reply_text("➡️ Envoie maintenant uniquement ton ID 1xBet (numérique).")
        return

    # Si en attente d'ID (après clic)
    if context.user_data.get("awaiting_id"):
        id_extrait = extract_first_digits(text)
        if not id_extrait:
            await update.message.reply_text("❌ Envoie uniquement ton ID 1xBet (ex: 11638822).")
            return

        # enregistrer dans players.json (avec statut pending)
        players = load_players()
        players[str(user.id)] = {"username": tg_username, "bet_id": id_extrait, "status": "pending", "scheduled_at": int(time.time())}
        save_players(players)

        # envoyer au canal admin si configuré
        channel_env = os.getenv("CHANNEL_ID") or CHANNEL_ID
        if channel_env:
            try:
                chat_id_to_send = int(channel_env) if re.match(r"^-?\d+$", str(channel_env)) else channel_env
                await context.bot.send_message(chat_id=chat_id_to_send, text=f"📥 Nouvel ID reçu :\n👤 @{tg_username}\n🆔 Telegram: {user.id}\n🎫 ID 1xBet: {id_extrait}")
            except Exception as e:
                logger.warning(f"Impossible d'envoyer au canal: {e}")
        else:
            logger.info("CHANNEL_ID non configuré; saut de l'envoi au canal.")

        await update.message.reply_text("⏳ Veuillez patienter 5h, nous vérifions votre compte...")
        # planifier la vérification (persistée et programmée)
        schedule_check(context.application, user.id, id_extrait)
        context.user_data["awaiting_id"] = False
        return

    # si envoie directement un ID sans cliquer le bouton
    id_direct = extract_first_digits(text)
    if id_direct:
        players = load_players()
        players[str(user.id)] = {"username": tg_username, "bet_id": id_direct, "status": "pending", "scheduled_at": int(time.time())}
        save_players(players)
        await update.message.reply_text("⏳ Veuillez patienter 5h, nous vérifions votre compte...")
        schedule_check(context.application, user.id, id_direct)
        return

    await update.message.reply_text("⚠️ Envoie ton ID 1xBet (numérique) ou clique sur le bouton.")

# commande admin broadcast
async def broadcast(update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 Tu n’as pas l’autorisation.")
        return
    if not context.args:
        await update.message.reply_text("⚠️ Utilisation : /broadcast Ton message ici")
        return
    message = " ".join(context.args)
    players = load_players()
    sent = 0
    for tid_str in players.keys():
        try:
            await context.bot.send_message(chat_id=int(tid_str), text=message)
            sent += 1
        except Exception as e:
            logger.warning(f"Erreur envoi {tid_str}: {e}")
    await update.message.reply_text(f"✅ Message envoyé à {sent} joueurs.")

# ---------- reprise des checks pendants au démarrage ----------
def resume_pending_checks(app):
    players = load_players()
    now = int(time.time())
    for tid_str, info in players.items():
        if info.get("status") == "pending" and info.get("scheduled_at"):
            scheduled_at = int(info["scheduled_at"])
            elapsed = now - scheduled_at
            remaining = CHECK_DELAY - elapsed
            try:
                if remaining <= 0:
                    app.job_queue.run_once(check_after_delay, when=0, data={"telegram_id": int(tid_str), "bet_id": info.get("bet_id")})
                else:
                    app.job_queue.run_once(check_after_delay, when=remaining, data={"telegram_id": int(tid_str), "bet_id": info.get("bet_id")})
                logger.info(f"Resume job for {tid_str}, remaining={remaining}s")
            except Exception as e:
                logger.exception(f"Erreur scheduling resume for {tid_str}: {e}")

# ---------- main ----------
def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN manquant. Défini la variable d'environnement BOT_TOKEN.")
        return

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CommandHandler("broadcast", broadcast))

    # Reprendre les jobs pendants avant run_polling
    resume_pending_checks(app)

    logger.info("Bot démarré.")
    app.run_polling()

if __name__ == "__main__":
    main()
