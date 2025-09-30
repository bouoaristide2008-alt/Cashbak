import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ================== CONFIG ==================
# Assurez-vous que ces valeurs sont correctes pour votre bot
TOKEN = "8277555619:AAHB4cx7uPJm9jlEej_e2UvHfUCkQI56lpM"
ADMIN_ID = 6357925694
CHANNEL_ID = -1002845193051
GROUP_ID = -1002365829730
GROUP_LINK = "https://t.me/kingpronosbs
https://t.me/lionel_officiel1"
AFFILIATE_LINK = "https://reffpa.com/L?tag=d_3684565m_97c_&site=3684565&ad=97&r=bienvenuaridtlrbj"

bot = telebot.TeleBot(TOKEN)

# ================== DONNÉES ==================
# Ces dictionnaires et listes devraient idéalement être stockés dans une base de données
# pour persister les données après un redémarrage du bot.
users_data = {}
pending_requests = []

# ================== MENUS ==================
def main_menu():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("💰 Cashback", callback_data="cashback"))
    markup.add(InlineKeyboardButton("🆘 Support", callback_data="support"))
    markup.add(InlineKeyboardButton("👥 Parrainage", callback_data="parrainage"))
    return markup

def bookmaker_menu():
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("1️⃣ 1xBet", callback_data="bookmaker_1xbet"),
        InlineKeyboardButton("2️⃣ Melbet", callback_data="bookmaker_melbet"),
        InlineKeyboardButton("3️⃣ BetWinner", callback_data="bookmaker_betwinner")
    )
    return markup

# ================== START ==================
@bot.message_handler(commands=['start'])
def start(message):
    welcome_msg = (
        f"👋 Bonjour **{message.from_user.first_name}** !\n\n"
        "Vous pouvez récupérer **15% de cashback** sur vos pertes sur 1xBet, Melbet et BetWinner "
        "en utilisant le code promo BCAF ou KANE225.\n\n"
        "Inscrivez-vous maintenant et commencez à récupérer vos pertes !"
    )
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🚀 S’inscrire sur 1xbet", url=AFFILIATE_LINK))
    bot.send_message(message.chat.id, welcome_msg, reply_markup=markup, parse_mode="Markdown")
    bot.send_message(message.chat.id, "Quel bookmaker utilisez-vous ?", reply_markup=bookmaker_menu())

# ================== CALLBACK ==================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    # Il est crucial d'appeler answer_callback_query pour fermer le sablier/l'attente
    bot.answer_callback_query(call.id)

    if call.data.startswith("bookmaker_"):
        bookmaker = call.data.split("_")[1]
        
        # Vérifie si l'utilisateur a déjà une demande en cours avant de demander l'ID
        if user_id in users_data and users_data[user_id]['statut'] == 'en attente':
            bot.send_message(call.message.chat.id, "⚠️ Vous avez déjà une demande en attente pour le bookmaker. Veuillez patienter.")
            return

        # Supprime le clavier précédent pour la clarté
        bot.edit_message_text(f"✅ Bookmaker sélectionné : **{bookmaker.upper()}**", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
        
        # Demande l'ID et enregistre l'étape suivante
        msg = bot.send_message(call.message.chat.id, f"📌 Entrez votre ID **{bookmaker.upper()}** :")
        bot.register_next_step_handler(msg, get_user_id, bookmaker)

    elif call.data == "cashback":
        if user_id in users_data and users_data[user_id]['statut'] == "accepté":
            montant = users_data[user_id].get('montant', 0)
            bot.send_message(call.message.chat.id, f"💰 Votre cashback : **{montant} CFA**", parse_mode="Markdown")
        else:
            bot.send_message(call.message.chat.id, "❌ Vous n'avez pas de cashback disponible ou votre demande est toujours en attente de validation.")

    elif call.data == "support":
        # Utiliser l'ADMIN_ID directement est plus fiable
        bot.send_message(call.message.chat.id, f"🆘 Contactez l'administrateur : <a href='tg://user?id={ADMIN_ID}'>Support Admin</a>", parse_mode="HTML")

    elif call.data == "parrainage":
        # Le parrainage utilise désormais le nom d'utilisateur du bot pour un lien universel
        bot_username = bot.get_me().username
        referral_link = f"https://t.me/{bot_username}?start={user_id}"
        
        bot.send_message(call.message.chat.id,
                         f"👥 Partagez ce lien avec vos amis pour parrainer :\n"
                         f"**{referral_link}**\n\n"
                         f"Chaque parrainage validé vous donne un bonus supplémentaire !",
                         parse_mode="Markdown")

# ================== GET USER ID ==================
def get_user_id(message, bookmaker):
    user_id = message.from_user.id
    # Utilise le nom d'utilisateur Telegram s'il existe, sinon le prénom
    username = message.from_user.username or message.from_user.first_name
    bookmaker_id = message.text.strip()
    
    # Validation basique pour s'assurer que l'ID est fourni
    if not bookmaker_id:
        bot.send_message(message.chat.id, "❌ Veuillez entrer un ID de bookmaker valide.")
        return

    # Vérifie si l'utilisateur a déjà une demande en attente (redondance retirée)
    if user_id in users_data and users_data[user_id]['statut'] == 'en attente':
        bot.send_message(message.chat.id, "⚠️ Vous avez déjà une demande en attente.")
        return

    # Enregistrement des données et statut
    users_data[user_id] = {
        'username': username,
        'bookmaker': bookmaker,
        'bookmaker_id': bookmaker_id,
        'statut': 'en attente',
        'montant': 0
    }
    # Ajout à la file d'attente
    if user_id not in pending_requests:
        pending_requests.append(user_id)

    bot.send_message(message.chat.id, f"📩 Votre demande est enregistrée et en attente de validation.\n"
                                      f"Veuillez rejoindre notre groupe : **{GROUP_LINK}**",
                                      parse_mode="Markdown")

    # Notification Admin (Canal et Groupe)
    username_display = f"@{username}" if message.from_user.username else f"{username} (ID: {user_id})"
    
    recap_msg = (
        f"📩 **Nouvelle demande de cashback !**\n"
        f"Utilisateur : {username_display}\n"
        f"Bookmaker : **{bookmaker.upper()}**\n"
        f"ID Bookmaker : `{bookmaker_id}`\n"
        f"Statut : _En attente_\n\n"
        f"▶️ Pour valider : `/valider {user_id} <montant>`\n"
        f"❌ Pour rejeter : `/rejeter {user_id}`"
    )
    bot.send_message(CHANNEL_ID, recap_msg, parse_mode="Markdown")
    bot.send_message(GROUP_ID, recap_msg, parse_mode="Markdown")

# ================== ADMIN COMMANDES ==================

@bot.message_handler(commands=['valider'])
def valider_demande(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "⛔ Pas autorisé ! Cette commande est réservée à l'administrateur.")
        return
        
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.send_message(message.chat.id, "❌ **Usage incorrect.** Utilisation: `/valider <user_id> <montant>`", parse_mode="Markdown")
            return
            
        target_id = int(parts[1])
        montant = int(parts[2])
        
    except ValueError:
        bot.send_message(message.chat.id, "❌ **Erreur de format.** L'ID utilisateur et le montant doivent être des nombres entiers.", parse_mode="Markdown")
        return

    if target_id in users_data:
        # Mise à jour des données
        users_data[target_id]['montant'] = montant
        users_data[target_id]['statut'] = 'accepté'
        
        # Nettoyage de la file d'attente
        if target_id in pending_requests:
            pending_requests.remove(target_id)
            
        # Notification admin
        username = users_data[target_id]['username']
        bot.send_message(message.chat.id, f"✅ Montant **{montant} CFA** validé pour l'utilisateur **{username}** (ID: {target_id}).", parse_mode="Markdown")
        
        # Notification utilisateur
        try:
            bot.send_message(target_id, 
                             f"🎉 Votre demande de cashback a été **validée** !\n"
                             f"Vous avez un cashback de **{montant} CFA** disponible. Consultez le menu 'Cashback' pour plus d'infos.",
                             parse_mode="Markdown")
        except telebot.apihelper.ApiTelegramException:
            bot.send_message(message.chat.id, f"⚠️ Impossible de notifier l'utilisateur {username} car il a bloqué le bot ou le chat est introuvable.", parse_mode="Markdown")
            
    else:
        bot.send_message(message.chat.id, f"❌ Utilisateur avec l'ID **{target_id}** introuvable dans la base de données.", parse_mode="Markdown")

@bot.message_handler(commands=['rejeter'])
def rejeter_demande(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "⛔ Pas autorisé ! Cette commande est réservée à l'administrateur.")
        return
        
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.send_message(message.chat.id, "❌ **Usage incorrect.** Utilisation: `/rejeter <user_id>`", parse_mode="Markdown")
            return
            
        target_id = int(parts[1])
        
    except ValueError:
        bot.send_message(message.chat.id, "❌ **Erreur de format.** L'ID utilisateur doit être un nombre entier.", parse_mode="Markdown")
        return

    if target_id in users_data:
        # Mise à jour des données
        users_data[target_id]['statut'] = 'rejeté'
        
        # Nettoyage de la file d'attente
        if target_id in pending_requests:
            pending_requests.remove(target_id)
            
        # Notification admin
        username = users_data[target_id]['username']
        bot.send_message(message.chat.id, f"❌ Demande de **{username}** (ID: {target_id}) rejetée.", parse_mode="Markdown")
        
        # Notification utilisateur
        try:
            bot.send_message(target_id, "❌ Votre demande de cashback a été **rejetée** par l'administrateur. Veuillez contacter le support pour plus d'informations.", parse_mode="Markdown")
        except telebot.apihelper.ApiTelegramException:
            bot.send_message(message.chat.id, f"⚠️ Impossible de notifier l'utilisateur {username} car il a bloqué le bot ou le chat est introuvable.", parse_mode="Markdown")
            
    else:
        bot.send_message(message.chat.id, f"❌ Utilisateur avec l'ID **{target_id}** introuvable dans la base de données.", parse_mode="Markdown")

# ================== LANCEMENT ==================
if __name__ == '__main__':
    print("🤖 Le bot est en cours d'exécution...")
    bot.infinity_polling()
