import os

import discord
from discord.ext.commands import *
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

bot = commands.Bot(command_prefix="IMPERIAL")

@bot.event
async def on_message(message):
  roles = [role.name for role in message.author.roles]
  print(roles)
  if message.content.startswith("OFFICIAL PROPOSAL:"):

    # Check if author is part of the Imperial Senate
    if 'ImperialSenator' not in roles and 'Emperor' not in roles:
      # Reject the Message
      await message.reply(content="You are not an Imperial Senator, so your proposal is immediately rejected.")
      return

@bot.event
async def on_reaction_add(reaction, user):
  if reaction.message.content.startswith("OFFICIAL PROPOSAL:"):
    # Check if author is part of the Imperial Senate
    roles = [role.name for role in reaction.message.author.roles]
    print(roles)
    if 'ImperialSenator' in roles or 'Emperor' in roles:
      print(bytes(str(reaction.emoji),'utf-8'))
      if '️⬆' in str(reaction.emoji):
        await reaction.message.reply(content=f"GREAT {reaction.count}")
      else:
        await reaction.message.reply(content=reaction.emoji)

bot.run(TOKEN)