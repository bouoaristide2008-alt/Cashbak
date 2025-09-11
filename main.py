import json
import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

ADMIN_ID = 123456789   # Remplace par TON ID Telegram
CHANNEL_ID = "@mon_canal_ids"  # Remplace par le @username de ton canal (ou -100xxxxxx pour un groupe privé)

# Charger la liste des utilisateurs validés
def load_users():
    with open("users.json", "r", encoding="utf-8") as f:
        return json.load(f)

# Sauvegarder les joueurs qui envoient leur ID
def save_player(telegram_id, username, bet_id):
    file = "players.json"
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}

    data[str(telegram_id)] = {"username": username, "bet_id": bet_id}

    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# Commande /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["🎫 Entrer mon ID 1xBet"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        "👋 Bienvenue sur le bot Cashback 1xBet.\n\n"
        "Clique sur le bouton ci-dessous et envoie ton ID 1xBet 👇",
        reply_markup=reply_markup
    )

# Réception d’un ID
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    users = load_users()
    tg_user = update.effective_user
    username = tg_user.username if tg_user.username else f"id:{tg_user.id}"

    if user_input.isdigit():
        # Sauvegarde le joueur
        save_player(tg_user.id, username, user_input)

        # Envoie dans ton canal
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=f"📥 Nouvel ID reçu :\n\n👤 User: @{username}\n🆔 Telegram: {tg_user.id}\n🎫 ID 1xBet: {user_input}"
        )

        # Vérifie si l'ID est validé
        if user_input in users:
            await update.message.reply_text(
                f"✅ ID {user_input} validé.\n"
                f"Bienvenue {users[user_input]['nom']} ! 🎉\n\n"
                "Tu bénéficies de 15% de cashback chaque semaine."
            )
        else:
            await update.message.reply_text(
                "❌ Désolé, ton ID n’est pas encore validé avec notre code promo.\n"
                "👉 Contacte l’admin pour vérification."
            )
    else:
        await update.message.reply_text("⚠️ Merci d’envoyer uniquement ton ID numérique 1xBet.")

# Commande admin : /broadcast <message>
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 Tu n’as pas l’autorisation d’utiliser cette commande.")
        return

    if not context.args:
        await update.message.reply_text("⚠️ Utilisation : /broadcast Ton message ici")
        return

    message = " ".join(context.args)

    try:
        with open("players.json", "r", encoding="utf-8") as f:
            players = json.load(f)
    except FileNotFoundError:
        players = {}

    count = 0
    for tid in players.keys():
        try:
            await context.bot.send_message(chat_id=int(tid), text=message)
            count += 1
        except Exception as e:
            print(f"Erreur envoi {tid}: {e}")

    await update.message.reply_text(f"✅ Message envoyé à {count} joueurs.")

# Lancer le bot
def main():
    TOKEN = os.getenv("BOT_TOKEN")
    if not TOKEN:
        print("❌ Erreur : BOT_TOKEN manquant")
        return

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CommandHandler("broadcast", broadcast))

    print("🤖 Bot lancé avec succès !")
    app.run_polling()

if __name__ == "__main__":
    main()