# -*- coding: utf-8 -*-
import discord
import json
import typing
import logging as log
import subprocess

from discord.ext import commands
from discord import utils

EmojiUnion = typing.Union[discord.Emoji, discord.PartialEmoji, str]

def streq(a, b):
    a.lower() == b.lower()

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

class ProposalDB:
    # TODO: actually have a DB of proposals
    def __init__(self):
        self._read_proposals()
        self._read_bans()

    def add_proposal(self, proposal_msg: discord.Message,
            type: str, **data):
        msg_ref = discord.MessageReference.from_message(proposal_msg)
        data['type'] = type
        data['ref'] = msg_ref.to_dict()
        data['assoc'] = []
        self.proposals[str(msg_ref.message_id)] = data
        self._write_proposals()

    def get_proposal(self, proposal_id: int):
        return self.proposals[str(proposal_id)]

    def has_proposal(self, proposal_id: int):
        return str(proposal_id) in self.proposals

    def pop_proposal(self, proposal_id: int):
        res = self.proposals.pop(str(proposal_id))
        self._write_proposals()
        return res

    def _read_proposals(self):
        try:
            with open('proposals', 'r') as f:
                self.proposals = json.load(f)
        except:
            print('Error with reading proposals')
            self.proposals = {}

    def _write_proposals(self):
        with open('proposals', 'w') as f:
            json.dump(self.proposals, f)

    def add_ban(self, ban_proposal: dict):
        ref = ban_proposal['ref']
        self.bans[str(ref['message_id'])] = {
            'ref': ref,
            'word': ban_proposal['word'],
        }
        self._write_bans()

    def has_ban(self, ban_id: int):
        return str(ban_id) in self.bans

    def pop_ban(self, proposal_id: int):
        res = self.bans.pop(str(proposal_id))
        self._write_bans()
        return res

    def _read_bans(self):
        try:
            with open('bans', 'r') as f:
                self.bans = json.load(f)
                # bad backwards compat thing
                if isinstance(self.bans, list): self.bans = {}
        except:
            print('Error with reading bans')
            self.bans = {}

    def _write_bans(self):
        with open('bans', 'w') as f:
            json.dump(self.bans, f)


class Proposal(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = ProposalDB()

        # We cannot use on_reaction_add as it only triggers on messages that are
        # inside the internal message cache
        bot.event(self.on_raw_reaction_add)
        bot.event(self.on_raw_reaction_remove)

    async def _confirm_proposal(self, message: discord.Message):
        prop_id = message.id
        prop_msg = self._show_proposal(prop_id)
        msg = f'Proposal #{prop_id} has been added :white_check_mark:: {prop_msg}'
        return await message.reply(content=msg)

    def _show_proposal(self, proposal_id):
        proposal = self.db.get_proposal(proposal_id)
        if proposal['type'] == 'amendment':
            return f'amendment at {proposal["proposal_url"]}/tree/{proposal["proposal_branch"]}'
        elif proposal['type'] == 'ban':
            return f'ban word `{proposal["word"]}`, id={proposal_id}'
        elif proposal['type'] == 'unban':
            word = proposal['ban_id']
            return f'unban word {word}, id={proposal["ban_id"]}'
        else:
            return 'Unknown proposal'

    @commands.command()
    async def bans(self, ctx):
        if len(self.db.bans) == 0:
            msg = 'No ban words'
        else:
            pref = self.bot.command_prefix
            msg = f'List of bans: (Unban with `{pref}unban <ID>`)'
            for ban in self.db.bans.values():
                msg += f'\n  {ban["word"]}: ID={ban["ref"]["message_id"]}'
        await ctx.message.reply(content=msg)

    @commands.command()
    async def ban(self, ctx, *, word):
        # Check if authorized
        if not checkAuthorized(ctx.message.author):
            await ctx.message.reply(content='You are not an Imperial senator, ' +
                    'so your proposal is immediately rejected')
            return

        self.db.add_proposal(ctx.message, 'ban', word=word)
        await self._confirm_proposal(ctx.message)

    @commands.command()
    async def unban(self, ctx, ban_id: str):
        # Check if authorized
        # TODO: change this into a check
        if not checkAuthorized(ctx.message.author):
            await ctx.message.reply(content='You are not an Imperial senator, ' +
                    'so your proposal is immediately rejected')
            return

        # Parse proposal id
        try:
            ban_id = int(ban_id)
        except:
            await ctx.message.reply(content=f'Invalid ban ID')
            return

        # Check that it is a ban that currently exists
        if not self.db.has_ban(ban_id):
            await ctx.message.reply(content=f'Invalid ban ID')
            return

        self.db.add_proposal(ctx.message, 'unban', ban_id=ban_id)
        await self._confirm_proposal(ctx.message)

    @commands.command('proposals')
    async def proposals(self, ctx):
        if len(self.db.proposals) == 0:
            msg = 'No proposals'
        else:
            pref = self.bot.command_prefix
            msg = 'List of proposals:'
            num = 1
            for prop in self.db.proposals.values():
                # TODO: show voting percentage
                prop_id = prop['ref']['message_id']
                url = discord.MessageReference(**prop['ref']).jump_url
                msg += f'\n  {num}. [[Jump]]({url}) {self._show_proposal(prop_id)}'
                num += 1
        await ctx.message.reply(embed=discord.Embed(
            title = 'List of proposals',
            type = 'rich',
            description = msg,
            color = 0x00ff00))

    @commands.command()
    async def propose(self, ctx, proposal_url, proposal_branch):
        # Check if authorized
        if not checkAuthorized(ctx.message.author):
            await ctx.message.reply(content='You are not an Imperial senator, ' +
                    'so your proposal is immediately rejected')
            return

        # Check if proposition is valid
        #print(branches)
        #if not proposal_url or not proposal_branch:
        #    subprocess.call(['git','fetch'])
        #    branches = [branch.lstrip() for branch in subprocess.check_output(['git', 'branch', '-r']).decode().split('\n')]
        #    await ctx.message.reply(content='The proposition presented is invalid.\n' +
        #            'Please create a pull request here: https://github.com/smrk007/imperial-constitution\n' +
        #            'Then, type the exact name of the branch as your proposition, like:\n\n' +
        #            '>propose your-fork-repo-url your-branch-name')
        #    return

        self.db.add_proposal(ctx.message, 'amendment',
                proposal_url=proposal_url, proposal_branch=proposal_branch)
        await self._confirm_proposal(ctx.message)

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
        if not self.db.has_proposal(payload.message_id):
            return
        await self.update_reaction(*await self._load_reaction_data(payload))

    async def on_raw_reaction_remove(self, payload):
        if not self.db.has_proposal(payload.message_id):
            return
        await self.update_reaction(*await self._load_reaction_data(payload))

    def pass_proposal(self, proposal_id):
        proposal = self.db.pop_proposal(proposal_id)
        if proposal['type'] == 'amendment':
            proposal_url = proposal['proposal_url']
            proposal_branch = proposal['proposal_branch']
            subprocess.call(['bash','acceptAmendment.sh',proposal_url,proposal_branch,'&'])
            exit()
        elif proposal['type'] == 'ban':
            if not any(map(lambda ban: streq(ban['word'], proposal['word']),
                self.db.bans.values())):
                    self.db.add_ban(proposal)
        elif proposal['type'] == 'unban':
            if self.db.has_ban(proposal['ban_id']):
                self.db.pop_ban(proposal['ban_id'])
        else:
            print("Invalid type of proposal!!")

    async def update_reaction(self, reaction, message, user):
        if not self.db.has_proposal(message.id): return

        # If reaction is None, this means that the removing the reaction caused
        # it to remove from the list of reactions
        if reaction == None:
            reaction = utils.find(lambda r: isUpArrow(r.emoji),
                    message.reactions)

        # We could not find any up-arrows so return out
        if reaction == None: return

        if isUpArrow(reaction.emoji):
            # Check if there is a super majority of senators who have voted
            # Or if emperor + simple majority
            senatorSupportCount = await getSenateSupportCount(reaction)
            totalSenators = getTotalSenators(reaction)
            emperorSupport = await getEmperorSupport(reaction)
            chan = message.channel
            percentSupport = int(senatorSupportCount*100/totalSenators)

            msg = f'> {self._show_proposal(message.id)}\n'
            if emperorSupport and ( percentSupport > 50 ):
                msg += f"This proposal has received {percentSupport}% support "
                msg += "with support from the emperor and has passed."
            elif not emperorSupport and ( percentSupport > 66 ):
                msg += f"This proposal has received {percentSupport}% support "
                msg += "without support from the emperor and has passed."
            await chan.send(content=msg)
            self.pass_proposal(message.id)
        else:
            return

def setup(bot):
    bot.add_cog(Proposal(bot))
