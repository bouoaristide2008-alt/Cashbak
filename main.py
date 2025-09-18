import os
import telebot
from telebot import types
import sqlite3
import random
import string
import threading
from flask import Flask, request

# ==============================
# CONFIG
# ==============================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8358605759:AAFUBRTk7juCFO6qPIA0QDfosp2ngWNFzJI")
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# Admins
ADMIN_IDS = [6357925694]  # Ton ID ici

# Base de données
conn = sqlite3.connect("cashback.db", check_same_thread=False)
c = conn.cursor()
c.execute("""CREATE TABLE IF NOT EXISTS demandes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                bookmaker TEXT,
                identifiant TEXT,
                statut TEXT DEFAULT 'En attente',
                code_cashback TEXT)""")
conn.commit()

db_lock = threading.Lock()

# ==============================
# MENU PRINCIPAL
# ==============================
@bot.message_handler(commands=["start"])
def start(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📌 Faire une demande", callback_data="faire_demande"))
    markup.add(types.InlineKeyboardButton("💰 Mon cashback", callback_data="cashback"))
    markup.add(types.InlineKeyboardButton("🆘 Support", callback_data="support"))
    markup.add(types.InlineKeyboardButton("❓ Aide", callback_data="aide"))
    bot.send_message(message.chat.id, "👋 Bienvenue sur le bot Cashback.\nQue voulez-vous faire ?", reply_markup=markup)

# ==============================
# CALLBACKS
# ==============================
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    # ==== Faire une demande ====
    if call.data == "faire_demande":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("1xBet", callback_data="bookmaker_1xBet"))
        markup.add(types.InlineKeyboardButton("Betwinner", callback_data="bookmaker_Betwinner"))
        markup.add(types.InlineKeyboardButton("1Win", callback_data="bookmaker_1Win"))
        bot.send_message(call.message.chat.id, "📌 Choisissez votre bookmaker :", reply_markup=markup)

    # ==== Choix bookmaker ====
    elif call.data.startswith("bookmaker_"):
        bookmaker = call.data.split("_")[1]
        bot.send_message(call.message.chat.id, f"👉 Entrez votre ID {bookmaker} :")
        bot.register_next_step_handler(call.message, save_demande, call.from_user.id, bookmaker)

    # ==== Mon cashback ====
    elif call.data == "cashback":
        show_cashback(call.message)

    # ==== Support ====
    elif call.data == "support":
        bot.send_message(call.message.chat.id, "🆘 Contacte le support ici : @managerxxten")

    # ==== Aide ====
    elif call.data == "aide":
        bot.send_message(call.message.chat.id,
                         "📖 Guide Cashback :\n"
                         "1️⃣ Choisissez un bookmaker\n"
                         "2️⃣ Saisissez votre identifiant\n"
                         "3️⃣ Attendez la validation de l'admin\n"
                         "4️⃣ Recevez votre code cashback 🎁")

    # ==== ADMIN : Accepter ====
    elif call.data.startswith("accepter_") and call.from_user.id in ADMIN_IDS:
        demande_id = int(call.data.split("_")[1])
        code_cash = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        with db_lock:
            c.execute("UPDATE demandes SET statut='Acceptée', code_cashback=? WHERE id=?", (code_cash, demande_id))
            conn.commit()
            c.execute("SELECT user_id FROM demandes WHERE id=?", (demande_id,))
            row = c.fetchone()
        if row:
            bot.send_message(row[0], f"✅ Votre demande a été acceptée !\n🎁 Code cashback : <b>{code_cash}</b>")
        bot.edit_message_text("✅ Demande acceptée", call.message.chat.id, call.message.message_id)

    # ==== ADMIN : Rejeter ====
    elif call.data.startswith("rejeter_") and call.from_user.id in ADMIN_IDS:
        demande_id = int(call.data.split("_")[1])
        with db_lock:
            c.execute("UPDATE demandes SET statut='Rejetée' WHERE id=?", (demande_id,))
            conn.commit()
            c.execute("SELECT user_id FROM demandes WHERE id=?", (demande_id,))
            row = c.fetchone()
        if row:
            bot.send_message(row[0], "❌ Votre demande a été rejetée.")
        bot.edit_message_text("❌ Demande rejetée", call.message.chat.id, call.message.message_id)

# ==============================
# SAUVEGARDE DEMANDE
# ==============================
def save_demande(message, user_id, bookmaker):
    identifiant = message.text.strip()
    with db_lock:
        c.execute("INSERT INTO demandes (user_id, bookmaker, identifiant) VALUES (?, ?, ?)",
                  (user_id, bookmaker, identifiant))
        conn.commit()
        demande_id = c.lastrowid

    # Notif admin
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Accepter", callback_data=f"accepter_{demande_id}"),
               types.InlineKeyboardButton("❌ Rejeter", callback_data=f"rejeter_{demande_id}"))
    for admin_id in ADMIN_IDS:
        bot.send_message(admin_id, f"📩 Nouvelle demande :\n"
                                   f"👤 ID User : {user_id}\n"
                                   f"🏦 Bookmaker : {bookmaker}\n"
                                   f"🆔 Identifiant : {identifiant}", reply_markup=markup)

    bot.send_message(message.chat.id, "📌 Votre demande a été envoyée ✅\nVeuillez attendre la validation de l'admin.")

# ==============================
# AFFICHER CASHBACK
# ==============================
def show_cashback(message):
    with db_lock:
        c.execute("SELECT bookmaker, identifiant, statut, code_cashback FROM demandes WHERE user_id=?", (message.chat.id,))
        rows = c.fetchall()
    if not rows:
        bot.send_message(message.chat.id, "⚠️ Vous n'avez pas encore fait de demande.")
        return

    txt = "💰 Historique de vos demandes :\n\n"
    for bookmaker, identifiant, statut, code in rows:
        txt += f"🏦 {bookmaker}\n🆔 {identifiant}\n📌 Statut : {statut}\n"
        if code:
            txt += f"🎁 Code : {code}\n"
        txt += "─────────────\n"
    bot.send_message(message.chat.id, txt)

# ==============================
# FLASK + WEBHOOK (Render)
# ==============================
app = Flask(__name__)

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    json_str = request.stream.read().decode("UTF-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

@app.route("/")
def index():
    return "Bot en ligne !"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))   
