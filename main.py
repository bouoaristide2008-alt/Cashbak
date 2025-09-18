import telebot
from telebot import types

# Mets ton token ici
BOT_TOKEN = "8358605759:AAFUBRTk7juCFO6qPIA0QDfosp2ngWNFzJI"
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
bot.remove_webhook()

# Ton ID Telegram admin (remplace par le tien)
ADMIN_ID = 6357925694

# ID du canal où toutes les demandes doivent aller
CHANNEL_ID = -1002845193051  # Remplace par ton canal

# Dictionnaire temporaire pour stocker les étapes utilisateur
user_data = {}

# ------------------ START ------------------
@bot.message_handler(commands=["start"])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("📌 1xBet")
    btn2 = types.KeyboardButton("📌 Melbet")
    btn3 = types.KeyboardButton("📌 Betwinner")
    markup.add(btn1, btn2, btn3)

    bot.send_message(
        message.chat.id,
        f"👋 Bienvenue <b>{message.from_user.first_name}</b> !\n\n"
        "Choisis ton bookmaker pour continuer :",
        reply_markup=markup
    )
    user_data[message.chat.id] = {}

# ------------------ CHOIX BOOKMAKER ------------------
@bot.message_handler(func=lambda msg: msg.text in ["📌 1xBet", "📌 Melbet", "📌 Betwinner"])
def get_bookmaker(message):
    user_data[message.chat.id]["bookmaker"] = message.text
    bot.send_message(message.chat.id, "🔑 Envoie maintenant ton ID joueur :")
    bot.register_next_step_handler(message, save_user_id)

def save_user_id(message):
    user_data[message.chat.id]["user_id"] = message.text

    bookmaker = user_data[message.chat.id]["bookmaker"]
    user_id = user_data[message.chat.id]["user_id"]

    text = (
        f"📩 Nouvelle demande de cashback\n\n"
        f"👤 Utilisateur : {message.from_user.first_name} (@{message.from_user.username})\n"
        f"🏦 Bookmaker : {bookmaker}\n"
        f"🆔 ID Joueur : {user_id}\n"
        f"✅ En attente de validation par l’administrateur."
    )

    # Envoyer à l’admin
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("✅ Accepter", callback_data=f"accept_{message.chat.id}")
    btn2 = types.InlineKeyboardButton("❌ Refuser", callback_data=f"reject_{message.chat.id}")
    markup.add(btn1, btn2)

    bot.send_message(ADMIN_ID, text, reply_markup=markup)

    # Envoyer dans le canal
    bot.send_message(CHANNEL_ID, text)

    bot.send_message(message.chat.id, "⏳ Votre demande a été envoyée, veuillez patienter.")

# ------------------ BOUTONS ADMIN ------------------
@bot.callback_query_handler(func=lambda call: call.data.startswith("accept_") or call.data.startswith("reject_"))
def handle_admin_action(call):
    user_chat_id = int(call.data.split("_")[1])

    if call.data.startswith("accept_"):
        bot.send_message(user_chat_id, "🎉 Votre demande a été <b>ACCEPTÉE</b> ✅")
        bot.send_message(call.message.chat.id, "👍 Demande acceptée avec succès.")
    else:
        bot.send_message(user_chat_id, "❌ Votre demande a été <b>REFUSÉE</b>.")
        bot.send_message(call.message.chat.id, "👎 Demande refusée.")

# ------------------ MENU SUPPORT ------------------
@bot.message_handler(commands=["menu"])
def menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("💰 Mon Cashback")
    btn2 = types.KeyboardButton("📞 Support")
    btn3 = types.KeyboardButton("ℹ️ Aide")
    markup.add(btn1, btn2, btn3)
    bot.send_message(message.chat.id, "📍 Menu principal :", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text == "📞 Support")
def support(message):
    bot.send_message(message.chat.id, "📩 Contactez l’admin ici : @TonUsername")

@bot.message_handler(func=lambda msg: msg.text == "ℹ️ Aide")
def aide(message):
    bot.send_message(message.chat.id, "ℹ️ Pour recevoir ton cashback, inscris-toi avec le code promo B-C-A-F.\n"
                                      "Ensuite, envoie ton ID pour validation.")

@bot.message_handler(func=lambda msg: msg.text == "💰 Mon Cashback")
def cashback(message):
    bot.send_message(message.chat.id, "💸 Ton solde cashback sera mis à jour par l’administrateur.")

# ------------------ LANCEMENT ------------------
print("✅ Bot Cashback lancé...")
bot.infinity_polling()
