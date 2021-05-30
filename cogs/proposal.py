# -*- coding: utf-8 -*-
import discord
import json
import typing
import logging as log
import subprocess

from discord.ext import commands
from discord import utils

EmojiUnion = typing.Union[discord.Emoji, discord.PartialEmoji, str]

def checkAuthorized(user):
    return isSenator(user) or isEmperor(user)

def isSenator(user):
    return 'ImperialSenator' in [role.name for role in user.roles]

def isEmperor(user):
    return 'Emperor' in [role.name for role in user.roles]

async def getSenateSupportCount(reaction):
    # Assume reaction is upvote
    senators_ids = set([member.id for member in filter(isSenator,reaction.message.channel.members)])
    users = await reaction.users().flatten()
    user_ids = set([user.id for user in users])
    senate_votes = senators_ids & user_ids
    return len(senate_votes)

def getTotalSenators(reaction):
    senators = [*filter(isSenator,reaction.message.channel.members)]
    return len(senators)

async def getEmperorSupport(reaction):
    users = await reaction.users().flatten()
    votes = [*filter(isEmperor,users)]
    return len(votes) > 0

def getEmojiName(emoji: EmojiUnion):
    if isinstance(emoji, str):
        return emoji
    elif isinstance(emoji, discord.PartialEmoji) or isinstance(emoji, discord.Emoji):
        return emoji.name

def isUpArrow(emoji: EmojiUnion):
    return getEmojiName(emoji) == '⬆️'

class Proposal(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.readProposals()
        self.readBans()

        # We cannot use on_reaction_add as it only triggers on messages that are
        # inside the internal message cache
        bot.event(self.on_raw_reaction_add)
        bot.event(self.on_raw_reaction_remove)

    # TODO: actually have a DB of proposals
    def readProposals(self):
        try:
            with open('proposals', 'r') as f:
                self.proposals = json.load(f)
        except:
            print('Error with reading proposals')
            self.proposals = {}

    def writeProposals(self):
        with open('proposals', 'w') as f:
            json.dump(self.proposals, f)

    def readBans(self):
        try:
            with open('bans', 'r') as f:
                self.bans = json.load(f)
        except:
            print('Error with reading bans')
            self.bans = []

    def writeBans(self):
        with open('bans', 'w') as f:
            json.dump(self.bans, f)

    @commands.command()
    async def ban(self, ctx, *, word):
        # Check if authorized
        if not checkAuthorized(ctx.message.author):
            await ctx.message.reply(content='You are not an Imperial senator, ' +
                    'so your proposal is immediately rejected')
            return

        self.proposals[str(ctx.message.id)] = { 'type': 'ban', 'body': word }
        self.writeProposals()

        await ctx.message.reply(content=f'Proposal #{ctx.message.id} has been ' +
                'added :white_check_mark:.')

    @commands.command()
    async def unban(self, ctx, *, word):
        # Check if authorized
        if not checkAuthorized(ctx.message.author):
            await ctx.message.reply(content='You are not an Imperial senator, ' +
                    'so your proposal is immediately rejected')
            return

        self.proposals[str(ctx.message.id)] = { 'type': 'unban', 'body': word }
        self.writeProposals()

        await ctx.message.reply(content=f'Proposal #{ctx.message.id} has been ' +
                'added :white_check_mark:.')

    @commands.command()
    async def propose(self, ctx, proposal_url, proposal_branch):

        # Check if authorized
        if not checkAuthorized(ctx.message.author):
            await ctx.message.reply(content='You are not an Imperial senator, ' +
                    'so your proposal is immediately rejected')
            return

        # Check if proposition is valid
        subprocess.call(['git','fetch'])
        branches = [branch.lstrip() for branch in subprocess.check_output(['git', 'branch', '-r']).decode().split('\n')]
        print(branches)

        if not proposal_url or not proposal_branch:
            await ctx.message.reply(content='The proposition presented is invalid.\n' +
                    'Please create a pull request here: https://github.com/smrk007/imperial-constitution\n' +
                    'Then, type the exact name of the branch as your proposition, like:\n\n' +
                    '>propose your-fork-repo-url your-branch-name')
            return

        self.proposals[str(ctx.message.id)] = { 'type': 'amendment', 'proposal_url': proposal_url, 'proposal_branch': proposal_branch }
        self.writeProposals()

        await ctx.message.reply(content=f'Proposal #{ctx.message.id} has been ' +
                'added :white_check_mark:.')

    async def _load_reaction_data(self, payload):
        emoji = getEmojiName(payload.emoji)
        guild = self.bot.get_guild(payload.guild_id)
        user = guild.get_member(payload.user_id)
        chan = self.bot.get_channel(payload.channel_id)

        message = await chan.fetch_message(payload.message_id)
        reaction = utils.find(lambda r: getEmojiName(r.emoji) == emoji,
                message.reactions)
        return reaction, message, user

    async def on_raw_reaction_add(self, payload):
        if str(payload.message_id) not in self.proposals:
            return
        await self.update_reaction(*await self._load_reaction_data(payload))

    async def on_raw_reaction_remove(self, payload):
        if str(payload.message_id) not in self.proposals:
            return
        await self.update_reaction(*await self._load_reaction_data(payload))

    def passProposal(self, proposal, message):
        if proposal['type'] == 'amendment':
            proposal_url = self.proposals[str(message.id)]['proposal_url']
            proposal_branch = self.proposals[str(message.id)]['proposal_branch']
            subprocess.call(['bash','acceptAmendment.sh',proposal_url,proposal_branch,'&'])
            exit()
        if proposal['type'] == 'ban':
            if proposal['body'] not in self.bans:
                self.bans.append(proposal['body'])
            self.writeBans()
        if proposal['type'] == 'unban':
            self.bans.remove(proposal['body'])
            self.writeBans()

    async def update_reaction(self, reaction, message, user):
        if str(message.id) not in self.proposals:
            return

        # If reaction is None, this means that the removing the reaction caused
        # it to remove from the list of reactions
        if reaction == None:
            reaction = utils.find(lambda r: isUpArrow(r.emoji),
                    message.reactions)

        # We could not find any up-arrows so return out
        if reaction == None:
            await message.reply(content='No votes for proposal')
            return

        if isUpArrow(reaction.emoji):
            # Check if there is a super majority of senators who have voted
            # Or if emperor + simple majority
            senatorSupportCount = await getSenateSupportCount(reaction)
            totalSenators = getTotalSenators(reaction)
            emperorSupport = await getEmperorSupport(reaction)

            percentSupport = int(senatorSupportCount*100/totalSenators)
            if emperorSupport and ( percentSupport > 50 ):
                await message.reply(content=f"This proposal has received {percentSupport}% support " +
                    "with support from the emperor and has passed.")
                self.passProposal(self.proposals[str(message.id)],message)
            elif not emperorSupport and ( percentSupport > 66 ):
                await message.reply(content=f"This proposal has received {percentSupport}% support " +
                    "without support from the emperor and has passed.")
                self.passProposal(self.proposals[str(message.id)],message)
        else:
            return

def setup(bot):
    bot.add_cog(Proposal(bot))
