import os

import discord
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

client = discord.Client()

@client.event
async def on_message(message):
  if message.content.startswith("OFFICIAL PROPOSAL:"):

    # Check if author is part of the Imperial Senate
    if 'ImperialSenator' not in message.author.roles and 'Emperor' not in message.author.roles:
      # Reject the Message
      await message.reply(content="You are not an Imperial Senator, so your proposal is immediately rejected.")
      return

@client.event
async def on_reaction_add(reaction, user):
  print(reaction.count)
  print(reaction.emoji)
  print(reaction.message.content)

client.run(TOKEN)