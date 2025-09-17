import json
import os
import threading
import asyncio
from flask import Flask
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder

# === CONFIG ===
BOT_TOKEN = "8358605759:AAFUBRTk7juCFO6qPIA0QDfosp2ngWNFzJI"
ADMIN_ID = 6357925694
CANAL_LIEN = "https://t.me/kingpronosbs"

# === INITIALISATION BOT ===
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

DATA_FILE = "data.json"

# === FLASK POUR KEEP-ALIVE ===
app = Flask(__name__)

@app.route("/")
def index():
    return "Bot MonCacheBar is running!"

# === GESTION DES DONNÉES ===
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"users": {}, "pending": {}, "counter": 0}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

# === MENUS ===
def get_user_menu():
    kb = ReplyKeyboardBuilder()
    kb.button(text="Contacter Support")
    kb.button(text="MonCashbak")
    return kb.as_markup(resize_keyboard=True)

def get_admin_menu():
    kb = ReplyKeyboardBuilder()
    kb.button(text="Voir demandes")
    kb.button(text="Ajouter cashback")
    return kb.as_markup(resize_keyboard=True)

# === COMMANDES ===
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("👑 Menu Admin", reply_markup=get_admin_menu())
    else:
        await message.answer(
            f"👋 Bienvenue sur *MonCashbak* !\n\n"
            "🔥 Cashback 15% sur tes pertes avec le code promo *BCAF* :\n"
            "- 1xBet\n- Melbet\n- Betwinner\n\n"
            "👉 Pour commencer, tape /stars",
            parse_mode="Markdown",
            reply_markup=get_user_menu()
        )

# === SUPPORT ===
@dp.message(lambda m: m.text == "Contacter Support")
async def support_cmd(message: types.Message):
    await bot.send_message(
        ADMIN_ID,
        f"🆘 Support demandé par @{message.from_user.username or message.from_user.full_name} (UserID: {message.from_user.id})"
    )
    await message.answer(
        f"✅ Votre demande de support a été envoyée.\n"
        f"Rejoins le canal officiel pour assistance : [Clique ici]({CANAL_LIEN})",
        parse_mode="Markdown"
    )

# === CHOIX BOOKMAKER ===
@dp.message(Command("stars"))
async def stars_cmd(message: types.Message):
    kb = ReplyKeyboardBuilder()
    kb.button(text="1xBet")
    kb.button(text="Melbet")
    kb.button(text="Betwinner")
    await message.answer("📌 Choisis ton bookmaker :", reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(lambda m: m.text in ["1xBet", "Melbet", "Betwinner"])
async def bookmaker_choice(message: types.Message):
    user_id = str(message.from_user.id)
    data["counter"] += 1
    demande_num = str(data["counter"])
    data["pending"][demande_num] = {
        "user_id": user_id,
        "bookmaker": message.text,
        "status": "attente_id"
    }
    save_data(data)
    await message.answer(f"Merci ✅\nVotre demande numéro *{demande_num}* est créée.\nMaintenant, entre ton *ID joueur* :", parse_mode="Markdown")

# === ENTRÉE ID JOUEUR ===
@dp.message(lambda m: m.text.isdigit())
async def id_joueur(message: types.Message):
    user_id = str(message.from_user.id)
    demandes_utilisateur = [num for num, info in data["pending"].items()
                            if info["user_id"] == user_id and info.get("status") == "attente_id"]
    if not demandes_utilisateur:
        return
    demande_num = demandes_utilisateur[-1]
    data["pending"][demande_num]["id_joueur"] = message.text
    data["pending"][demande_num]["status"] = "en_attente_validation"
    save_data(data)

    info = data["pending"][demande_num]

    # 🔹 Récapitulatif utilisateur avec lien canal
    user_recap = (
        f"🎯 Nouvelle demande #{demande_num}\n"
        f"Bookmaker : {info['bookmaker']}\n"
        f"ID joueur : {info['id_joueur']}\n"
        f"Nom : {message.from_user.full_name}\n"
        f"Pseudo : @{message.from_user.username or 'aucun'}\n"
        f"UserID : {user_id}\n\n"
        f"🔗 Rejoins le canal officiel pour assistance : [Clique ici]({CANAL_LIEN})"
    )
    await message.answer(user_recap, parse_mode="Markdown")

    # 🔹 Récapitulatif admin en PV
    admin_recap = (
        f"🎯 Nouvelle demande #{demande_num}\n"
        f"Bookmaker : {info['bookmaker']}\n"
        f"ID joueur : {info['id_joueur']}\n"
        f"Nom : {message.from_user.full_name}\n"
        f"Pseudo : @{message.from_user.username or 'aucun'}\n"
        f"UserID : {user_id}"
    )
    await bot.send_message(ADMIN_ID, admin_recap)

# === VALIDATION PAR ADMIN ===
@dp.message(Command("accepter"))
async def accepter_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        _, demande_num, code = message.text.split()
    except:
        await message.reply("Usage: /accepter <num_demande> <code à 4 chiffres>")
        return
    if demande_num not in data["pending"]:
        await message.reply("❌ Demande introuvable.")
        return
    info = data["pending"][demande_num]
    uid = info["user_id"]

    data["users"][code] = {
        "user_id": uid,
        "pseudo": f"@{message.from_user.username}" if message.from_user.username else "",
        "bookmaker": info["bookmaker"],
        "id_joueur": info["id_joueur"],
        "solde": 0,
        "valide": True
    }
    del data["pending"][demande_num]
    save_data(data)

    await bot.send_message(
        int(uid),
        f"✅ Votre compte a été validé !\n"
        f"Votre code *MonCacheBar* est : `{code}`\n\n"
        f"👉 Utilisez le bouton 'MonCacheBar' pour consulter vos gains.",
        parse_mode="Markdown"
    )

    await message.reply(f"Demande #{demande_num} validée avec le code {code}")
    await message.answer("👑 Menu Admin", reply_markup=get_admin_menu())

# === AJOUT CASHBACK ===
@dp.message(Command("ajouter"))
async def ajouter_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        _, code, montant = message.text.split()
        montant = int(montant)
    except:
        await message.reply("Usage: /ajouter <code> <montant>")
        return

    if code in data["users"]:
        data["users"][code]["solde"] += montant
        save_data(data)
        uid = int(data["users"][code]["user_id"])
        await bot.send_message(uid, f"💰 Nouveau cashback ajouté : {montant} FCFA\nSolde total : {data['users'][code]['solde']} FCFA")
        await message.reply(f"✅ Ajouté {montant} FCFA au code {code}")
    else:
        await message.reply("❌ Code introuvable.")

# === MONCACHEBAR ===
@dp.message(lambda m: m.text == "MonCacheBar")
async def moncachebar_cmd(message: types.Message):
    await message.answer("🔑 Entrez votre code MonCacheBar (4 chiffres).")

@dp.message(lambda m: m.text.isdigit() and len(m.text) == 4)
async def check_code(message: types.Message):
    code = message.text
    if code in data["users"]:
        solde = data["users"][code]["solde"]
        await message.answer(f"💰 Solde MonCacheBar : {solde} FCFA")
    else:
        await message.answer("❌ Code invalide ou non encore validé.")

# === DÉMARRAGE BOT EN THREAD ===
async def start_bot():
    await dp.start_polling(bot)

def run_bot():
    asyncio.run(start_bot())

if __name__ == "__main__":
    # Lancer le bot Telegram dans un thread
    threading.Thread(target=run_bot).start()
    # Lancer Flask pour keep-alive
    app.run(host="0.0.0.0", port=5000)
