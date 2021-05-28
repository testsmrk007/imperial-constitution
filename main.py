import os

import discord
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

client = discord.Client()

@client.event
async def on_message(message):
  roles = [role.name for role in message.author.roles]
  print(roles)
  if message.content.startswith("OFFICIAL PROPOSAL:"):

    # Check if author is part of the Imperial Senate
    if 'ImperialSenator' not in roles and 'Emperor' not in roles:
      # Reject the Message
      await message.reply(content="You are not an Imperial Senator, so your proposal is immediately rejected.")
      return

@client.event
async def on_reaction_add(reaction, user):
  if reaction.message.content.startswith("OFFICIAL PROPOSAL:"):
    # Check if author is part of the Imperial Senate
    roles = [role.name for role in reaction.message.author.roles]
    print(roles)
    if 'ImperialSenator' in roles or 'Emperor' in roles:
      if '️⬆' in str(reaction.emoji):
        await reaction.message.reply(content=f"GREAT {reaction.count}")
      else:
        await reaction.message.reply(content=reaction.emoji)

client.run(TOKEN)