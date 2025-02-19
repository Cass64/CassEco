import os  
from dotenv import load_dotenv
import discord
from discord import app_commands
from discord.ext import commands
import random
from keep_alive import keep_alive
import json
import asyncio
import pymongo
from pymongo import MongoClient
import datetime
import math

load_dotenv()

# Connexion à MongoDB via l'URI
mongo_uri = os.getenv("MONGO_URI")
client = MongoClient(mongo_uri)
db = client['Cass-Eco2']  # Nom de la base de données
economy_collection = db['economy']  # Collection pour stocker les données économiques

# Vérification de la connexion MongoDB
try:
    client.admin.command('ping')
    print("✅ Connexion à MongoDB réussie !")
except Exception as e:
    print(f"❌ Échec de connexion à MongoDB : {e}")
    exit()

token = os.getenv('TOKEN_BOT_DISCORD')

# Intents et configuration du bot
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot connecté en tant que {bot.user}")

# Fonction pour récupérer ou créer un utilisateur dans MongoDB
def get_user_data(user_id):
    user_id = str(user_id)
    user_data = economy_collection.find_one({"user_id": user_id})
    if user_data is None:
        new_user = {"user_id": user_id, "cash": 0, "bank": 0, "total": 0, "last_claim": None}
        economy_collection.insert_one(new_user)
        return new_user
    return user_data

# Fonction pour sauvegarder les données économiques
def save_user_data(user_id, user_data):
    user_id = str(user_id)
    economy_collection.update_one({"user_id": user_id}, {"$set": user_data})

# Fonction pour créer un embed stylisé
def create_embed(title, description, ctx):
    embed = discord.Embed(
        title=f"**{title}**", 
        description=f"**──────────**\n{description}\n**──────────**", 
        color=discord.Color.red()
    )
    embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
    embed.set_footer(text="💰 Système Économique | Cass-Eco")
    return embed

# Commande pour afficher la balance de l'utilisateur
@bot.command(name="balance")
async def balance(ctx):
    user_data = get_user_data(ctx.author.id)
    embed = create_embed(
        "💰 Votre Balance",
        f"💵 **Cash** : `{user_data['cash']}`\n🏦 **Banque** : `{user_data['bank']}`\n💰 **Total** : `{user_data['total']}`",
        ctx
    )
    await ctx.send(embed=embed)

# Commande générique pour dépôt/retrait
async def modify_balance(ctx, amount, transaction_type):
    user_data = get_user_data(ctx.author.id)
    
    if amount.lower() == "all":
        amount = user_data["cash"] if transaction_type == "deposit" else user_data["bank"]
    
    try:
        amount = int(amount)
    except ValueError:
        return await ctx.send(embed=create_embed("⚠️ Erreur", "Veuillez entrer un montant valide.", ctx))

    if amount <= 0:
        return await ctx.send(embed=create_embed("⚠️ Erreur", "Le montant doit être supérieur à 0.", ctx))

    if transaction_type == "deposit" and amount > user_data["cash"]:
        return await ctx.send(embed=create_embed("⚠️ Erreur", "Vous n'avez pas assez d'argent en cash.", ctx))
    elif transaction_type == "withdraw" and amount > user_data["bank"]:
        return await ctx.send(embed=create_embed("⚠️ Erreur", "Vous n'avez pas assez d'argent en banque.", ctx))

    if transaction_type == "deposit":
        user_data["cash"] -= amount
        user_data["bank"] += amount
    else:
        user_data["cash"] += amount
        user_data["bank"] -= amount

    user_data["total"] = user_data["cash"] + user_data["bank"]
    save_user_data(ctx.author.id, user_data)

    embed = create_embed(
        "🏦 Transaction Réussie",
        f"Vous avez {'déposé' if transaction_type == 'deposit' else 'retiré'} **{amount}** 💵.",
        ctx
    )
    await ctx.send(embed=embed)

@bot.command(name="deposit")
async def deposit(ctx, amount: str):
    await modify_balance(ctx, amount, "deposit")

@bot.command(name="withdraw")
async def withdraw(ctx, amount: str):
    await modify_balance(ctx, amount, "withdraw")

# Commande pour récupérer une récompense quotidienne
@bot.command(name="daily")
async def daily(ctx):
    user_data = get_user_data(ctx.author.id)
    today = datetime.datetime.utcnow().date()
    
    if user_data.get("last_claim") == str(today):
        return await ctx.send(embed=create_embed("📅 Récompense Déjà Réclamée", "Vous avez déjà pris votre récompense aujourd'hui.", ctx))

    reward = random.randint(100, 500)
    user_data["cash"] += reward
    user_data["total"] = user_data["cash"] + user_data["bank"]
    user_data["last_claim"] = str(today)

    save_user_data(ctx.author.id, user_data)
    await ctx.send(embed=create_embed("🎁 Récompense Quotidienne", f"Vous avez reçu **{reward}** 💵 ! Revenez demain.", ctx))

# Fonction pour créer un embed de leaderboard 
async def create_leaderboard_embed(page, users, ctx):
    description = ""
    start_index = (page - 1) * 10  # Calculer l'index de départ
    end_index = start_index + 10  # Limiter à 10 utilisateurs par page

    # Générer la description des utilisateurs pour la page donnée
    for i, user in enumerate(users[start_index:end_index]):
        member = await bot.fetch_user(int(user["user_id"]))
        description += f"**#{start_index + i + 1}** {member.name} - 💰 `{user['total']}`\n"
    
    embed = discord.Embed(
        title="🏆 Classement Économique",
        description=description or "Aucun utilisateur enregistré.",
        color=discord.Color.green()
    )
    embed.set_footer(text=f"Page {page}/{math.ceil(len(users) / 10)}")  # Afficher le numéro de page actuel
    return embed
    
# Commande pour afficher le classement économique
@bot.command(name="leaderboard")
async def leaderboard(ctx, page: int = 1):
    # Récupérer tous les utilisateurs triés par total
    all_users = list(economy_collection.find().sort("total", -1))

    # S'assurer que la page est valide
    if page < 1 or page > math.ceil(len(all_users) / 10):
        return await ctx.send(embed=create_embed("⚠️ Erreur", "Page invalide.", ctx))

    # Créer et envoyer l'embed de leaderboard pour la page spécifiée
    embed = await create_leaderboard_embed(page, all_users, ctx)
    leaderboard_message = await ctx.send(embed=embed)

    # Ajouter des réactions pour naviguer entre les pages
    await leaderboard_message.add_reaction("⬅️")
    await leaderboard_message.add_reaction("➡️")

    # Fonction pour gérer les réactions
    def check(reaction, user):
        return user != bot.user and str(reaction.emoji) in ["⬅️", "➡️"] and reaction.message.id == leaderboard_message.id

    try:
        while True:
            reaction, user = await bot.wait_for("reaction_add", check=check, timeout=60)  # Timeout de 60 secondes pour les réactions
            if str(reaction.emoji) == "⬅️" and page > 1:
                page -= 1
            elif str(reaction.emoji) == "➡️" and page < math.ceil(len(all_users) / 10):
                page += 1

            # Mettre à jour l'embed avec la nouvelle page
            embed = await create_leaderboard_embed(page, all_users, ctx)
            await leaderboard_message.edit(embed=embed)

            # Enlever la réaction de l'utilisateur
            await leaderboard_message.remove_reaction(reaction, user)

    except asyncio.TimeoutError:
        await leaderboard_message.clear_reactions()

# Lancement du bot
keep_alive()
bot.run(token)
