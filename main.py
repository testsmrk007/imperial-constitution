import os
import logging as log
import discord
from discord.ext.commands import *
from discord.ext import commands
import subprocess
import traceback
import re
from auth import DISCORD_TOKEN
from trim import trim_nl
import json

# TODO: show typing when in progress

extensions = []

bot = commands.Bot(command_prefix=">", intents=discord.Intents.all())

def readBans():
  try:
    with open('bans', 'r') as f:
      return(json.load(f))
  except:
    print('Error with reading bans')
    return {}

@bot.event
async def on_message(message):
  await bot.process_commands(message)
  await check_bans(message)

async def check_bans(message):
  if message.author.id == bot.user.id:
      return
  bans = readBans()
  for ban in bans.values():
    if ban['word'].lower() in message.content.lower():
      print('Banned: ' + message.content)
      await message.reply(content="This message uses forbidden language.")
      await message.delete()
      return

@bot.event
async def on_error(evt_type, *args, **kwargs):
    if evt_type == 'on_message':
        await args[0].reply('An error has occurred... :disappointed:')
        await args[0].reply(traceback.format_exc())
    log.error(f'Ignoring exception at {evt_type}')
    log.error(traceback.format_exc())


@bot.event
async def on_command_error(ctx, err):
    if isinstance(err, MissingPermissions):
        await ctx.send('You do not have permission to do that! ¯\_(ツ)_/¯')
    elif isinstance(err, MissingRequiredArgument):
        await ctx.send(':bangbang: Missing arguments to command');
    elif isinstance(err, BotMissingPermissions):
        await ctx.send(trim_nl(f''':cry: I can\'t do that. Please ask server ops
        to add all the permission for me!

        ```{str(err)}```'''))
    elif isinstance(err, DisabledCommand):
        await ctx.send(':skull: Command has been disabled!')
    elif isinstance(err, CommandNotFound):
        await ctx.send(f'Invalid command passed. Use {bot.command_prefix}help.')
    elif isinstance(err, NoPrivateMessage):
        await ctx.send(':bangbang: This command cannot be used in PMs.')
    else:
        await ctx.send('An error has occurred... :disappointed:')
        log.error(f'Ignoring exception in command {ctx.command}')
        log.error(''.join(traceback.format_exception(type(err), err,
                err.__traceback__)))

if __name__ == '__main__':
    for extension in os.listdir('cogs'):
        if extension.endswith('.py'):
            extension = extension[:-3]
        else:
            continue
        print(f'Loading cog {extension}')
        bot.load_extension('cogs.' + extension)

    print("Starting bot...")
    bot.run(DISCORD_TOKEN)
