import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ================== CONFIG ==================
TOKEN = "8277555619:AAHB4cx7uPJm9jlEej_e2UvHfUCkQI56lpM"
ADMIN_ID = 6357925694
CHANNEL_ID = -1002845193051
GROUP_ID = -1002365829730
GROUP_LINK = "https://t.me/kingpronosbs"

bot = telebot.TeleBot(TOKEN)

# ================== DONNÉES ==================
users_data = {}
pending_requests = []

# ================== MENUS ==================
def main_menu():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("💰 Cashback", callback_data="cashback"))
    markup.add(InlineKeyboardButton("🆘 Support", callback_data="support"))
    return markup

def bookmaker_menu():
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("1️⃣ 1xBet", callback_data="bookmaker_1xbet"),
        InlineKeyboardButton("2️⃣ Melbet", callback_data="bookmaker_melbet"),
        InlineKeyboardButton("3️⃣ BetWinner", callback_data="bookmaker_betwinner")
    )
    return markup

def admin_menu():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✅ Accepter", callback_data="admin_accept"))
    markup.add(InlineKeyboardButton("❌ Rejeter", callback_data="admin_reject"))
    return markup

# ================== START ==================
@bot.message_handler(commands=['start'])
def start(message):
    welcome_msg = (
        f"👋 Bonjour {message.from_user.first_name} !\n\n"
        "Vous pouvez recevoir **15% de cashback** sur vos pertes sur 1xBet, Melbet et BetWinner "
        "en utilisant le code promo **BCAF**.\n\n"
        "Quel bookmaker utilisez-vous ?"
    )
    bot.send_message(message.chat.id, welcome_msg, reply_markup=bookmaker_menu())

# ================== CALLBACK ==================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    username = call.from_user.username or call.from_user.first_name

    if call.data.startswith("bookmaker_"):
        bookmaker = call.data.split("_")[1]
        bot.send_message(call.message.chat.id, f"📌 Entrez votre ID {bookmaker} :")
        bot.register_next_step_handler(call.message, get_user_id, bookmaker)

    elif call.data == "cashback":
        if user_id in users_data and users_data[user_id]['statut'] == "accepté":
            montant = users_data[user_id].get('montant', 0)
            bot.send_message(call.message.chat.id, f"💰 Votre cashback : {montant} CFA")
        else:
            bot.send_message(call.message.chat.id, "❌ Vous n'avez pas de cashback disponible.")

    elif call.data == "support":
        bot.send_message(call.message.chat.id, f"🆘 Contactez l'admin : @{bot.get_me().username}")

    elif call.data.startswith("admin_"):
        if user_id != ADMIN_ID:
            bot.answer_callback_query(call.id, "⛔ Vous n'êtes pas admin !")
            return
        action = call.data.split("_")[1]
        if not pending_requests:
            bot.answer_callback_query(call.id, "📭 Pas de demandes en attente.")
            return
        target_id = pending_requests.pop(0)
        if action == "accept":
            users_data[target_id]['statut'] = "accepté"
            bot.send_message(target_id, "✅ Votre demande a été acceptée ! Vous pouvez maintenant voir votre cashback et contacter le support.")
            bot.answer_callback_query(call.id, "✅ Demande acceptée !")
        else:
            users_data[target_id]['statut'] = "rejeté"
            bot.send_message(target_id, "❌ Votre demande a été rejetée.")
            bot.answer_callback_query(call.id, "❌ Demande rejetée !")

# ================== GET USER ID ==================
def get_user_id(message, bookmaker):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    bookmaker_id = message.text.strip()

    users_data[user_id] = {
        'username': username,
        'bookmaker': bookmaker,
        'bookmaker_id': bookmaker_id,
        'statut': 'en attente',
        'montant': 0
    }
    pending_requests.append(user_id)

    bot.send_message(message.chat.id, f"📩 Votre demande est en cours de vérification.\nVeuillez rejoindre notre groupe : {GROUP_LINK}")

    recap_msg = (
        f"📩 Nouvelle demande de cashback !\n"
        f"Utilisateur : @{username}\n"
        f"Bookmaker : {bookmaker}\n"
        f"ID : {bookmaker_id}"
    )
    # ✅ Ajout des boutons admin
    bot.send_message(CHANNEL_ID, recap_msg, reply_markup=admin_menu())
    bot.send_message(GROUP_ID, recap_msg, reply_markup=admin_menu())

# ================== ADMIN AJOUT MONTANT ==================
@bot.message_handler(commands=['ajouter_montant'])
def add_montant(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "⛔ Pas autorisé !")
        return
    try:
        _, target_id, montant = message.text.split()
        target_id = int(target_id)
        montant = int(montant)
        if target_id in users_data:
            users_data[target_id]['montant'] = montant
            bot.send_message(message.chat.id, f"✅ Montant {montant} CFA ajouté à @{users_data[target_id]['username']}")
        else:
            bot.send_message(message.chat.id, "❌ Utilisateur introuvable.")
    except:
        bot.send_message(message.chat.id, "Usage: /ajouter_montant <user_id> <montant>")

# ================== LANCEMENT ==================
bot.infinity_polling()
