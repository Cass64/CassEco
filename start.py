import os  
from dotenv import load_dotenv
from discord import app_commands
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
    await bot.tree.sync()
    print(f"Bot connecté en tant que {bot.user}")

# Dépôt et retrait
deposit_withdraw_commands = {"deposit": "déposé", "withdraw": "retiré"}
for cmd, action in deposit_withdraw_commands.items():
    @bot.command(name=cmd)
    async def transaction(ctx, amount: str, transaction_type=cmd, action=action):
        user_data = get_user_data(ctx.author.id)
        if amount.lower() == "all":
            amount = user_data["cash"] if transaction_type == "deposit" else user_data["bank"]
        try:
            amount = int(amount)
        except ValueError:
            return await ctx.send(embed=create_embed("⚠️ Erreur", "Montant invalide."))

        if amount <= 0 or (transaction_type == "deposit" and amount > user_data["cash"]) or (transaction_type == "withdraw" and amount > user_data["bank"]):
            return await ctx.send(embed=create_embed("⚠️ Erreur", "Montant incorrect."))

        user_data["cash"] -= amount if transaction_type == "deposit" else -amount
        user_data["bank"] += amount if transaction_type == "deposit" else -amount
        user_data["total"] = user_data["cash"] + user_data["bank"]
        save_user_data(ctx.author.id, user_data)

        await ctx.send(embed=create_embed("🏦 Transaction réussie", f"Vous avez {action} `{amount}` 💵."))
        
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

@bot.tree.command(name="add-store", description="Ajoute un objet dans le store (réservé au rôle .Destiny)")
@app_commands.checks.has_role(".Destiny")
@app_commands.describe(
    name="Nom de l'objet",
    price="Prix de l'objet",
    stock="Quantité disponible",
    description="Description de l'objet"
)
async def add_store(interaction: discord.Interaction, name: str, price: int, stock: int, description: str):
    store_collection.insert_one({"name": name, "price": price, "stock": stock, "description": description})
    
    embed = discord.Embed(
        title="✅ Objet ajouté !",
        description=f"**{name}** a été ajouté au store.\n💰 Prix: `{price}`\n📦 Stock: `{stock}`\n📝 {description}",
        color=discord.Color.green()
    )
    
    await interaction.response.send_message(embed=embed)



@bot.command(name="item-buy")
async def item_buy(ctx, *, item_name: str):
    user_data = get_user_data(ctx.author.id)
    item = store_collection.find_one({"name": item_name})

    if not item:
        return await ctx.send(embed=create_embed("❌ Erreur", "L'objet n'existe pas dans le store."))
    if item['stock'] <= 0:
        return await ctx.send(embed=create_embed("❌ Stock épuisé", f"L'objet **{item_name}** est en rupture de stock."))
    if user_data["cash"] < item['price']:
        return await ctx.send(embed=create_embed("❌ Fonds insuffisants", "Vous n'avez pas assez d'argent pour cet achat."))

    # Mise à jour de l'utilisateur et du stock
    user_data["cash"] -= item['price']
    user_data["total"] = user_data["cash"] + user_data["bank"]
    user_data["inventory"].append(item_name)
    save_user_data(ctx.author.id, user_data)

    # Mise à jour du stock
    store_collection.update_one({"name": item_name}, {"$inc": {"stock": -1}})
    
    await ctx.send(embed=create_embed("✅ Achat Réussi", f"Vous avez acheté **{item_name}** pour **{item['price']} 💵** !"))


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
