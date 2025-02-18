import discord
from dotenv import load_dotenv
import os

load_dotenv()
token = os.getenv('TOKEN_BOT_DISCORD')

client = discord.Client(intents=discord.Intents.all())

client.run(token=token)
