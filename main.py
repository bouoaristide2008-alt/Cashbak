# bot.py
import json
import os
import re
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

# CONFIG: à personnaliser via variables d'environnement sur Render
BOT_TOKEN = os.getenv("BOT_TOKEN")           # obligatoire
ADMIN_ID = int(os.getenv("ADMIN_ID", "6357925694"))  # ton id Telegram (entier)
CHANNEL_ID = os.getenv("CHANNEL_ID", "-1002845193051")     # ex "@mon_canal" ou "-1001234567890"

BUTTON_LABEL = "🎫 Entrer mon ID 1xBet"

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
    return load_json_file("users.json")

def save_player(telegram_id, username, bet_id):
    players = load_json_file("players.json")
    players[str(telegram_id)] = {"username": username, "bet_id": bet_id}
    save_json_file("players.json", players)

def extract_first_digits(text):
    if not text:
        return None
    m = re.search(r"(\d+)", text)
    return m.group(1) if m else None

# ---------- tâche après 5h ----------
async def check_after_delay(context: ContextTypes.DEFAULT_TYPE):
    job_data = context.job.data
    telegram_id = job_data["telegram_id"]
    bet_id = job_data["bet_id"]

    users = load_users()
    if bet_id not in users:  # ID pas validé après 5h
        try:
            await context.bot.send_message(
                chat_id=telegram_id,
                text=(
                    "❌ Votre compte n’a pas été créé avec le code promo BCAF.\n"
                    "Veuillez créer un nouveau compte 1xBet avec le code promo **BCAF** et réessayer.\n\n"
                    "👉 [Cliquez ici pour suivre la procédure](https://ton-lien-1xbet.com)"
                ),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Erreur envoi message retardé à {telegram_id}: {e}")

# ---------- handlers ----------
async def start(update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[KeyboardButton(BUTTON_LABEL)]]
    reply_markup = ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        "👋 Bienvenue !\n\nClique sur le bouton ci-dessous pour inscrire ton ID 1xBet.",
        reply_markup=reply_markup
    )

async def handle_message(update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    users = load_users()
    user = update.effective_user
    tg_username = user.username if user.username else f"id:{user.id}"

    # Si clic sur le bouton
    if text == BUTTON_LABEL:
        context.user_data["awaiting_id"] = True
        await update.message.reply_text("➡️ Envoie maintenant **seulement** ton ID 1xBet (numérique).")
        return

    # Si en attente d'ID
    if context.user_data.get("awaiting_id"):
        id_extrait = extract_first_digits(text)
        if not id_extrait:
            await update.message.reply_text("❌ Envoie uniquement ton ID 1xBet (ex: 11638822).")
            return

        save_player(user.id, tg_username, id_extrait)

        # envoi canal
        try:
            chat_id_to_send = CHANNEL_ID
            if chat_id_to_send and re.match(r"^-?\d+$", chat_id_to_send):
                chat_id_to_send = int(chat_id_to_send)
            await context.bot.send_message(
                chat_id=chat_id_to_send,
                text=f"📥 Nouvel ID reçu :\n👤 @{tg_username}\n🆔 Telegram: {user.id}\n🎫 ID 1xBet: {id_extrait}"
            )
        except Exception as e:
            logger.exception(f"Erreur envoi canal: {e}")

        # réponse immédiate
        await update.message.reply_text("⏳ Veuillez patienter 5h, nous vérifions votre compte...")

        # planification vérification 5h
        context.job_queue.run_once(
            check_after_delay,
            when=18000,  # 5 heures = 18000 secondes
            data={"telegram_id": user.id, "bet_id": id_extrait}
        )
        context.user_data["awaiting_id"] = False
        return

    # Si envoie directement un chiffre sans cliquer bouton
    id_direct = extract_first_digits(text)
    if id_direct:
        save_player(user.id, tg_username, id_direct)
        await update.message.reply_text("⏳ Veuillez patienter 5h, nous vérifions votre compte...")
        context.job_queue.run_once(
            check_after_delay,
            when=18000,
            data={"telegram_id": user.id, "bet_id": id_direct}
        )
        return

    await update.message.reply_text("⚠️ Envoie ton ID 1xBet (numérique) ou clique sur le bouton.")

# commande admin
async def broadcast(update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 Tu n’as pas l’autorisation.")
        return
    if not context.args:
        await update.message.reply_text("⚠️ Utilisation : /broadcast Ton message ici")
        return
    message = " ".join(context.args)
    players = load_json_file("players.json")
    sent = 0
    for tid_str in players.keys():
        try:
            await context.bot.send_message(chat_id=int(tid_str), text=message)
            sent += 1
        except Exception as e:
            logger.warning(f"Erreur envoi {tid_str}: {e}")
    await update.message.reply_text(f"✅ Message envoyé à {sent} joueurs.")

# ---------- main ----------
def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN manquant.")
        return

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CommandHandler("broadcast", broadcast))

    logger.info("Bot démarré.")
    app.run_polling()

if __name__ == "__main__":
    main()
