import os  
from dotenv import load_dotenv
import discord
from discord import app_commands
from discord.ext import commands
import random
from keep_alive import keep_alive
import json
import asyncio


load_dotenv()


token = os.getenv('TOKEN_BOT_DISCORD')

# Intents et configuration du bot
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot connecté en tant que {bot.user}")
# Fichier JSON pour stocker les informations économiques
data_file = "economy_data.json"

# Charger les données des utilisateurs
def load_data():
    if os.path.exists(data_file):
        with open(data_file, "r") as f:
            return json.load(f)
    else:
        return {}

# Sauvegarder les données des utilisateurs
def save_data(data):
    with open(data_file, "w") as f:
        json.dump(data, f, indent=4)

# Fonction pour obtenir les informations économiques d'un utilisateur
def get_user_data(user_id, data):
    if str(user_id) not in data:
        data[str(user_id)] = {"cash": 0, "bank": 0, "total": 0}
    return data[str(user_id)]

# Fonction pour créer un embed
def create_embed(title, description, color, ctx):
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
    return embed

# Commande pour afficher la balance de l'utilisateur
@bot.command(name="balance")
async def balance(ctx):
    data = load_data()
    user_data = get_user_data(ctx.author.id, data)

    embed = create_embed("💰 Votre balance", 
                         f"💵 **Cash** : `{user_data['cash']}`\n"
                         f"🏦 **Banque** : `{user_data['bank']}`\n"
                         f"💰 **Total** : `{user_data['total']}`",
                         discord.Color.gold(), ctx)
    await ctx.send(embed=embed)

# Cooldown de 30 minutes pour la commande "work"
@bot.command(name="work")
@commands.cooldown(1, 1800, commands.BucketType.user)  # 1800 secondes = 30 minutes
async def work(ctx):
    data = load_data()
    user_data = get_user_data(ctx.author.id, data)

    earned_money = random.randint(50, 200)
    user_data["cash"] += earned_money
    user_data["total"] = user_data["cash"] + user_data["bank"]

    save_data(data)

    embed = create_embed("💼 Travail réussi !", 
                         f"Vous avez travaillé et gagné **{earned_money}** 💵 !", 
                         discord.Color.green(), ctx)
    await ctx.send(embed=embed)

@work.error
async def work_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        embed = create_embed("⏳ Travail en attente", 
                             f"Vous devez attendre encore **{round(error.retry_after / 60)} minutes** avant de retravailler.", 
                             discord.Color.red(), ctx)
        await ctx.send(embed=embed)

# Commande pour déposer de l'argent à la banque (inclut "all")
@bot.command(name="deposit")
async def deposit(ctx, amount: str):
    data = load_data()
    user_data = get_user_data(ctx.author.id, data)

    if amount.lower() == "all":
        amount = user_data["cash"]

    try:
        amount = int(amount)
    except ValueError:
        embed = create_embed("⚠️ Erreur", 
                             "Veuillez entrer un montant valide.", 
                             discord.Color.red(), ctx)
        return await ctx.send(embed=embed)

    if amount <= 0 or amount > user_data["cash"]:
        embed = create_embed("⚠️ Erreur", 
                             "Vous n'avez pas assez d'argent en cash.", 
                             discord.Color.red(), ctx)
        return await ctx.send(embed=embed)

    user_data["cash"] -= amount
    user_data["bank"] += amount
    user_data["total"] = user_data["cash"] + user_data["bank"]

    save_data(data)

    embed = create_embed("🏦 Dépôt effectué", 
                         f"Vous avez déposé **{amount}** 💵 à la banque.", 
                         discord.Color.blue(), ctx)
    await ctx.send(embed=embed)

# Commande pour retirer de l'argent de la banque (inclut "all")
@bot.command(name="withdraw")
async def withdraw(ctx, amount: str):
    data = load_data()
    user_data = get_user_data(ctx.author.id, data)

    if amount.lower() == "all":
        amount = user_data["bank"]

    try:
        amount = int(amount)
    except ValueError:
        embed = create_embed("⚠️ Erreur", 
                             "Veuillez entrer un montant valide.", 
                             discord.Color.red(), ctx)
        return await ctx.send(embed=embed)

    if amount <= 0 or amount > user_data["bank"]:
        embed = create_embed("⚠️ Erreur", 
                             "Vous n'avez pas assez d'argent en banque.", 
                             discord.Color.red(), ctx)
        return await ctx.send(embed=embed)

    user_data["cash"] += amount
    user_data["bank"] -= amount
    user_data["total"] = user_data["cash"] + user_data["bank"]

    save_data(data)

    embed = create_embed("🏦 Retrait effectué", 
                         f"Vous avez retiré **{amount}** 💵 de votre banque.", 
                         discord.Color.blue(), ctx)
    await ctx.send(embed=embed)
# Lancement du bot
keep_alive()
bot.run(token)
