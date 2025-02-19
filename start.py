import os  
from dotenv import load_dotenv
import discord
from discord.ext import commands
from keep_alive import keep_alive
import random
import json
import asyncio
import pymongo
from pymongo import MongoClient
import datetime
import math

load_dotenv()

# Connexion MongoDB
mongo_uri = os.getenv("MONGO_URI")
client = MongoClient(mongo_uri)
db = client['Cass-Eco2']
economy_collection = db['economy']
store_collection = db['store']

# Vérification MongoDB
try:
    client.admin.command('ping')
    print("✅ Connexion à MongoDB réussie !")
except Exception as e:
    print(f"❌ Échec de connexion à MongoDB : {e}")
    exit()

token = os.getenv('TOKEN_BOT_DISCORD')
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!!", intents=intents)

def get_user_data(user_id):
    user_data = economy_collection.find_one({"user_id": str(user_id)})
    if user_data is None:
        user_data = {"user_id": str(user_id), "cash": 0, "bank": 0, "total": 0, "last_claim": None, "inventory": []}
        economy_collection.insert_one(user_data)
    return user_data

def save_user_data(user_id, user_data):
    economy_collection.update_one({"user_id": str(user_id)}, {"$set": user_data})

def create_embed(title, description, color=discord.Color.green()):
    return discord.Embed(title=title, description=description, color=color)

@bot.event
async def on_ready():
    print(f"Bot connecté en tant que {bot.user}")

@bot.command(name="balance")
async def balance(ctx):
    user_data = get_user_data(ctx.author.id)
    embed = create_embed("💰 Votre Balance", f"💵 **Cash** : `{user_data['cash']}`\n🏦 **Banque** : `{user_data['bank']}`\n💰 **Total** : `{user_data['total']}`")
    await ctx.send(embed=embed)

@bot.command(name="work")
@commands.cooldown(1, 1800, commands.BucketType.user)
async def work(ctx):
    user_data = get_user_data(ctx.author.id)
    earned_money = random.randint(50, 200)
    user_data["cash"] += earned_money
    user_data["total"] = user_data["cash"] + user_data["bank"]
    save_user_data(ctx.author.id, user_data)
    await ctx.send(embed=create_embed("💼 Travail Réussi !", f"Vous avez gagné **{earned_money}** 💵 !"))

@bot.command(name="daily")
async def daily(ctx):
    user_data = get_user_data(ctx.author.id)
    today = datetime.datetime.utcnow().date()
    if user_data.get("last_claim") == str(today):
        return await ctx.send(embed=create_embed("📅 Déjà Réclamé", "Revenez demain !"))
    reward = random.randint(100, 500)
    user_data["cash"] += reward
    user_data["total"] = user_data["cash"] + user_data["bank"]
    user_data["last_claim"] = str(today)
    save_user_data(ctx.author.id, user_data)
    await ctx.send(embed=create_embed("🎁 Récompense Quotidienne", f"Vous avez reçu **{reward}** 💵 !"))

@bot.command(name="store")
async def store(ctx):
    items = list(store_collection.find())
    if not items:
        return await ctx.send(embed=create_embed("🏪 Boutique", "Aucun objet disponible."))
    desc = "\n".join([f"**{item['name']}** - {item['price']} 💵 ({item['stock']} en stock)\n_{item['description']}_" for item in items])
    await ctx.send(embed=create_embed("🏪 Boutique", desc))

@bot.command(name="add-store")
@commands.has_role(".Destiny")
async def add_store(ctx, name: str, price: int, stock: int, *, description: str):
    store_collection.insert_one({"name": name, "price": price, "stock": stock, "description": description})
    await ctx.send(embed=create_embed("✅ Ajouté !", f"**{name}** ajouté au store."))

@bot.command(name="item-buy")
async def item_buy(ctx, *, item_name: str):
    user_data = get_user_data(ctx.author.id)
    item = store_collection.find_one({"name": item_name})
    if not item or item['stock'] <= 0:
        return await ctx.send(embed=create_embed("❌ Erreur", "Objet non disponible."))
    if user_data["cash"] < item['price']:
        return await ctx.send(embed=create_embed("❌ Fonds insuffisants", "Retirez de la banque si besoin."))
    user_data["cash"] -= item['price']
    user_data["total"] = user_data["cash"] + user_data["bank"]
    user_data["inventory"].append(item_name)
    save_user_data(ctx.author.id, user_data)
    store_collection.update_one({"name": item_name}, {"$inc": {"stock": -1}})
    await ctx.send(embed=create_embed("✅ Achat Réussi", f"Vous avez acheté **{item_name}** !"))

@bot.command(name="item-inventory")
async def item_inventory(ctx):
    user_data = get_user_data(ctx.author.id)
    inventory = user_data.get("inventory", [])
    desc = "\n".join(inventory) if inventory else "Votre inventaire est vide."
    await ctx.send(embed=create_embed("🎒 Inventaire", desc))

@bot.command(name="leaderboard")
async def leaderboard(ctx, page: int = 1):
    all_users = list(economy_collection.find().sort("total", -1))
    pages = math.ceil(len(all_users) / 10)
    if page < 1 or page > pages:
        return await ctx.send(embed=create_embed("⚠️ Erreur", "Page invalide."))
    desc = "\n".join([f"**#{i+1}** {await bot.fetch_user(int(u['user_id']))} - 💰 `{u['total']}`" for i, u in enumerate(all_users[(page-1)*10:page*10])])
    embed = create_embed("🏆 Classement Économique", desc)
    embed.set_footer(text=f"Page {page}/{pages}")
    await ctx.send(embed=embed)
keep_alive()
bot.run(token)
