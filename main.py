import os

import discord
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

client = discord.Client()

@client.event
async def on_message(message):
  if message.content.startswith("OFFICIAL PROPOSAL:"):
    # Check if member is a senator
    if 'ImperialSenator' not in message.author.roles and 'Emperor' not in message.author.roles:
      # Reject the Message
      await message.reply(content="You are not an Imperial Senator, so your proposal is immediately rejected.")
      pass
    pass

client.run(TOKEN)