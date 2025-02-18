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

# Commande pour afficher la balance de l'utilisateur
@bot.command(name="balance")
async def balance(ctx):
    data = load_data()
    user_data = get_user_data(ctx.author.id, data)
    cash = user_data["cash"]
    bank = user_data["bank"]
    total = user_data["total"]
    await ctx.send(f"{ctx.author.mention}, voici votre balance :\n"
                   f"Argent en cash : {cash} 💵\n"
                   f"Argent en banque : {bank} 🏦\n"
                   f"Total : {total} 💰")

# Commande pour faire travailler un utilisateur et gagner de l'argent
@bot.command(name="work")
async def work(ctx):
    data = load_data()
    user_data = get_user_data(ctx.author.id, data)

    # Gagner de l'argent (par exemple, 50 à 200 coins par travail)
    earned_money = random.randint(50, 200)
    user_data["cash"] += earned_money
    user_data["total"] = user_data["cash"] + user_data["bank"]

    save_data(data)
    await ctx.send(f"{ctx.author.mention}, vous avez travaillé et gagné {earned_money} 💵 !")

# Commande pour déposer de l'argent à la banque
@bot.command(name="deposit")
async def deposit(ctx, amount: int):
    data = load_data()
    user_data = get_user_data(ctx.author.id, data)

    if amount <= 0 or amount > user_data["cash"]:
        await ctx.send(f"{ctx.author.mention}, vous n'avez pas assez d'argent ou le montant est invalide.")
        return

    user_data["cash"] -= amount
    user_data["bank"] += amount
    user_data["total"] = user_data["cash"] + user_data["bank"]

    save_data(data)
    await ctx.send(f"{ctx.author.mention}, vous avez déposé {amount} 💵 à la banque.")

# Commande pour retirer de l'argent de la banque
@bot.command(name="withdraw")
async def withdraw(ctx, amount: int):
    data = load_data()
    user_data = get_user_data(ctx.author.id, data)

    if amount <= 0 or amount > user_data["bank"]:
        await ctx.send(f"{ctx.author.mention}, vous n'avez pas assez d'argent à la banque.")
        return

    user_data["cash"] += amount
    user_data["bank"] -= amount
    user_data["total"] = user_data["cash"] + user_data["bank"]

    save_data(data)
    await ctx.send(f"{ctx.author.mention}, vous avez retiré {amount} 💵 de votre banque.")

# Lancement du bot
keep_alive()
bot.run(token)
