import os
import sqlite3
from threading import Lock
from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# === CONFIG ===
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN non défini !")

ADMIN_IDS = [6357925694]   # ton ID admin
CHANNEL_URL = "https://t.me/kingpronosbs"  # lien canal obligatoire

DB_FILE = "cashback.db"
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
db_lock = Lock()

# === DB INIT ===
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()
c.execute("""CREATE TABLE IF NOT EXISTS demandes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    montant TEXT,
    statut TEXT DEFAULT 'En attente'
)""")
conn.commit()

# === MENU ===
def menu_principal():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("💰 Faire une demande", callback_data="demande"))
    markup.add(InlineKeyboardButton("📊 Mes demandes", callback_data="mes_demandes"))
    markup.add(InlineKeyboardButton("📢 Rejoindre canal", url=CHANNEL_URL))
    return markup

# === START ===
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "👋 Bienvenue sur le bot Cashback !", reply_markup=menu_principal())

# === CALLBACK ===
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    if call.data == "demande":
        bot.send_message(call.message.chat.id, "Entrez le montant de votre demande 💵 :")
        bot.register_next_step_handler(call.message, save_demande)

    elif call.data == "mes_demandes":
        with db_lock:
            c.execute("SELECT id, montant, statut FROM demandes WHERE user_id=?", (call.from_user.id,))
            rows = c.fetchall()
        if not rows:
            bot.send_message(call.message.chat.id, "❌ Vous n’avez aucune demande.")
        else:
            msg = "📊 Vos demandes :\n\n"
            for r in rows:
                msg += f"ID: {r[0]} | Montant: {r[1]} | Statut: {r[2]}\n"
            bot.send_message(call.message.chat.id, msg)

# === SAVE DEMANDE ===
def save_demande(message):
    montant = message.text
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    with db_lock:
        c.execute("INSERT INTO demandes (user_id, username, montant) VALUES (?,?,?)",
                  (user_id, username, montant))
        conn.commit()
    bot.send_message(message.chat.id, f"✅ Demande enregistrée pour {montant} CFA.\n👉 Rejoins le canal : {CHANNEL_URL}")

    # Notif admin
    for admin in ADMIN_IDS:
        bot.send_message(admin, f"📢 Nouvelle demande : @{username} - {montant} CFA")

# === ADMIN COMMANDS ===
@bot.message_handler(commands=['valider'])
def valider(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        demande_id = int(message.text.split()[1])
        with db_lock:
            c.execute("UPDATE demandes SET statut='Validée' WHERE id=?", (demande_id,))
            conn.commit()
        bot.send_message(message.chat.id, f"✅ Demande {demande_id} validée.")
    except:
        bot.send_message(message.chat.id, "Usage: /valider <id>")

@bot.message_handler(commands=['rejeter'])
def rejeter(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        demande_id = int(message.text.split()[1])
        with db_lock:
            c.execute("UPDATE demandes SET statut='Rejetée' WHERE id=?", (demande_id,))
            conn.commit()
        bot.send_message(message.chat.id, f"❌ Demande {demande_id} rejetée.")
    except:
        bot.send_message(message.chat.id, "Usage: /rejeter <id>")

# === WEBHOOK FLASK ===
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "", 200

# === LAUNCH ===
if __name__ == "__main__":
    bot.remove_webhook()
    PORT = int(os.environ.get("PORT", 5000))
    SERVICE_URL = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}"
    bot.set_webhook(url=f"{SERVICE_URL}/{TOKEN}")
    app.run(host="0.0.0.0", port=PORT)
