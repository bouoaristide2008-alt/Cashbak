import json
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram import F
import asyncio
import os

# === CONFIG ===
BOT_TOKEN = "8358605759:AAFUBRTk7juCFO6qPIA0QDfosp2ngWNFzJI"
ADMIN_ID = 6357925694
CANAL_LIEN = "https://t.me/TON_CANAL_ICI"  # Remplace par ton canal pour les utilisateurs

# === INITIALISATION ===
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

DATA_FILE = "data.json"

# Charger ou créer le fichier JSON
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"users": {}, "pending": {}, "counter": 0}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

# === COMMANDES UTILISATEUR ===

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    kb = ReplyKeyboardBuilder()
    kb.button(text="Contacter Support")
    kb.button(text="MonCacheBar")
    await message.answer(
        f"👋 Bienvenue sur *MonCacheBar* !\n\n"
        "🔥 Ici, tu peux recevoir *15% de tes pertes* en cashback chaque semaine sur :\n"
        "- 1xBet\n- Melbet\n- Betwinner\n\n"
        "⚡ Condition : inscrit avec le code promo *BCAF*\n\n"
        "👉 Pour commencer, tape la commande /stars",
        parse_mode="Markdown",
        reply_markup=kb.as_markup(resize_keyboard=True)
    )

@dp.message(F.text == "Contacter Support")
async def support_cmd(message: types.Message):
    # Envoie uniquement à l'admin
    await bot.send_message(
        ADMIN_ID,
        f"🆘 Support demandé par @{message.from_user.username or message.from_user.full_name} (UserID: {message.from_user.id})"
    )
    # Retour utilisateur
    await message.answer(
        f"✅ Votre demande de support a été envoyée.\n"
        f"Rejoins le canal officiel pour assistance : [Clique ici]({CANAL_LIEN})",
        parse_mode="Markdown"
    )

@dp.message(Command("stars"))
async def stars_cmd(message: types.Message):
    kb = ReplyKeyboardBuilder()
    kb.button(text="1xBet")
    kb.button(text="Melbet")
    kb.button(text="Betwinner")
    await message.answer("📌 Choisis ton bookmaker :", reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(F.text.in_(["1xBet", "Melbet", "Betwinner"]))
async def bookmaker_choice(message: types.Message):
    user_id = str(message.from_user.id)
    data["counter"] += 1
    demande_num = data["counter"]
    data["pending"][str(demande_num)] = {
        "user_id": user_id,
        "bookmaker": message.text,
        "status": "attente_id"
    }
    save_data(data)
    await message.answer(f"Merci ✅\nVotre demande numéro *{demande_num}* est créée.\nMaintenant, entre ton *ID joueur* :", parse_mode="Markdown")

@dp.message(F.text.regexp(r"^\d+$"))
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

    # 🔹 Récapitulatif pour l'utilisateur avec lien canal
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

    # 🔹 Récapitulatif uniquement pour l'admin en PV
    admin_recap = (
        f"🎯 Nouvelle demande #{demande_num}\n"
        f"Bookmaker : {info['bookmaker']}\n"
        f"ID joueur : {info['id_joueur']}\n"
        f"Nom : {message.from_user.full_name}\n"
        f"Pseudo : @{message.from_user.username or 'aucun'}\n"
        f"UserID : {user_id}"
    )
    await bot.send_message(ADMIN_ID, admin_recap)

# === COMMANDES ADMIN ===

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
        await bot.send_message(uid, f"💰 Nouveau cashback ajouté : {montant} FCFA\n"
                                    f"Solde total : {data['users'][code]['solde']} FCFA")
        await message.reply(f"✅ Ajouté {montant} FCFA au code {code}")
    else:
        await message.reply("❌ Code introuvable.")

# === MONCACHEBAR ===

@dp.message(Command("moncachebar"))
async def moncachebar_cmd(message: types.Message):
    await message.answer("🔑 Entrez votre code MonCacheBar (4 chiffres).")

@dp.message(F.text.regexp(r"^\d{4}$"))
async def check_code(message: types.Message):
    code = message.text
    if code in data["users"]:
        solde = data["users"][code]["solde"]
        await message.answer(f"💰 Solde MonCacheBar : {solde} FCFA")
    else:
        await message.answer("❌ Code invalide ou non encore validé.")

# === MAIN ===

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
