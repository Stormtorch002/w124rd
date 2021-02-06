from discord.ext import commands
from humanize import precisedelta
import time
from datetime import datetime
import discord
from cogs.utils.timeparser import TimeConverter
import asyncio
from emoji import UNICODE_EMOJI
import random
from cogs.level import get_level


class Giveaway(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.msg_ids = []
        self.bot.loop.create_task(self.dispatch())

    async def win(self, res, *, reroll=False):
        msg_id = res['msg_id']

        if not reroll and msg_id not in self.msg_ids:
            return

        channel = self.bot.get_channel(res['ch_id'])
        msg = await channel.fetch_message(msg_id)
        reaction = msg.reactions[0]
        entered = await reaction.users().flatten()

        if self.bot.user in entered:
            entered.remove(self.bot.user)

        winners = []

        if reroll:
            while True:
                try:
                    winner = random.choice(entered)
                except IndexError:
                    return await channel.send('A new winner couldn\'t be picked ((')
                entered.remove(winner)
                if res['role_id']:
                    if not await self.reqs(res, reaction.emoji, winner, remove_reaction=False):
                        continue
                    else:
                        break
                else:
                    break
            embed = msg.embeds[0].to_dict()
            value = embed['fields'][0]['value']
            mentions = value.splitlines()
            if winner.mention not in mentions:
                if value == 'Nobody':
                    embed['fields'][0]['value'] = f'\n{winner.mention}'
                else:
                    embed['fields'][0]['value'] += f'\n{winner.mention}'
            await msg.edit(embed=discord.Embed.from_dict(embed))
            return await channel.send(f'Our new winner is {winner.mention}! Congrats ))')

        self.msg_ids.remove(res['msg_id'])
        query = 'UPDATE gvwys SET ended = $1 WHERE msg_id = $2'
        await self.bot.db.execute(query, True, res['msg_id'])

        while True:
            try:
                winner = random.choice(entered)
            except IndexError:
                break
            entered.remove(winner)

            if res['role_id']:
                if not (await self.reqs(res, reaction.emoji, winner, remove_reaction=False))[0]:
                    continue

            winners.append(winner)
            if len(winners) == res['winners']:
                break

        host = self.bot.get_user(res['host_id'])
        if len(winners) == 0:
            await channel.send(f'Nobody has entered the giveaway for **{res["prize"]}** ((')
            mentions = 'Nobody'
        else:
            mentions = '\n'.join(m.mention for m in winners)
            await channel.send(f':tada: The giveaway for `{res["prize"]}` has ended! :tada:\n'
                               f'__**Our winners are:**__\n\n{mentions}\n\n'
                               f'Congratulations on winning ))')
            for m in winners:
                await m.send(f':tada: Congratulations on winning the giveaway for **{res["prize"]}** in SLounge!\n'
                             f'You might have to DM the host ({host.mention}) to officially claim your prize.')
            embed = discord.Embed(
                title='Your Giveaway Has Ended!',
                color=discord.Colour.blue()
            ).add_field(
                name='Winners', value=mentions, inline=False
            ).add_field(
                name='Prize', value=res['prize'], inline=False
            ).add_field(
                name='Channel', value=f'{channel.mention}\n[Jump to Giveaway]({msg.jump_url})', inline=False
            )
            await host.send(embed=embed)
        embed = discord.Embed(
            title=res['prize'],
            description='*Giveaway ended*',
            color=discord.Colour.blue(),
            timestamp=datetime.utcnow()
        ).add_field(
            name='\U0001f389 Winners', value=mentions, inline=False
        ).add_field(
            name='\U0001f451 Host', value=host.mention, inline=False
        ).set_footer(
            text='\U000023f0 Time ended \u27a1',
            icon_url='https://cdn.discordapp.com/emojis/795660003369025546.gif?v=1'
        ).set_thumbnail(url='https://cdn.discordapp.com/attachments/725093929481142292/792530547120799764/'
                            'download_-_2020-12-26T181245.032.png')
        await msg.edit(embed=embed)

    async def wait_for_msg(self, ctx, timeout):

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            return await self.bot.wait_for('message', check=check, timeout=timeout)
        except asyncio.TimeoutError:
            await ctx.send('Looks like you went AFK. Please try again.')
            return

    async def dispatch(self):
        res = await self.bot.db.fetch('SELECT * FROM gvwys WHERE ended = $1', False)
        self.msg_ids = [res['msg_id'] for res in res]

        for row in res:
            async def task():
                await asyncio.sleep(row['end'] - time.time())
                await self.win(row)

            self.bot.loop.create_task(task())

    async def reqs(self, res, emoji, member, *, remove_reaction=True):
        es = str(emoji)

        async def remove():
            msg = await self.bot.get_channel(res['ch_id']).fetch_message(res['msg_id'])
            await msg.remove_reaction(es, member)

        if 0 < res['role_id'] < 69:
            query = 'SELECT total_xp FROM xp WHERE user_id = $1'
            xp = await self.bot.db.fetchrow(query, member.id)
            if not xp:
                req = False
            else:
                level = get_level(xp['total_xp'])
                if res['role_id'] > level:
                    if remove_reaction:
                        await remove()
                    req = False
                else:
                    req = True
            if not req:
                return False, f'You can\'t enter this giveaway because you need to be at least ' \
                              f'**Level {res["role_id"]}**!'
        else:
            if res['role_id'] not in [r.id for r in member.roles]:
                if remove_reaction:
                    await remove()
                role = self.bot.slounge.get_role(res['role_id'])
                return False, f'You can\'t enter this giveaway because you don\'t have the `{role.name}` role.\n' \
                              'If this is a Reaction Role, you can obtain it in <#724745898726391850>.'
        return True, ''

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.member.bot:
            return
        if payload.message_id in self.msg_ids:
            query = 'SELECT * FROM gvwys WHERE msg_id = $1'
            res = await self.bot.db.fetchrow(query, payload.message_id)
            if str(payload.emoji) != res['emoji']:
                return
            if res['role_id']:
                enter, msg = await self.reqs(res, payload.emoji, payload.member)
                if not enter:
                    await payload.member.send(msg)

    @commands.command()
    @commands.has_role(794618677806104576)
    async def reroll(self, ctx, msg_id: int):
        """Picks a new winner for an ended giveaway.
           You need the `Giveaways` role in SLounge to do this.

           **Usage:** `$reroll <message ID>`
        """
        query = 'SELECT * FROM gvwys WHERE msg_id = $1 AND ended = $2'
        res = await self.bot.db.fetchrow(query, msg_id, True)
        if not res:
            return await ctx.send(f'There is no ended giveaway with message ID `{msg_id}`.')
        await ctx.send('Rerolling...')
        await self.win(res, reroll=True)

    @commands.command()
    @commands.has_role(794618677806104576)
    async def end(self, ctx, msg_id: int):
        """Force-ends a giveaway that hasn't automatically ended yet.
           You need the `Giveaways` role in SLounge to do this.

           **Usage:** `$end <message ID>`
        """
        query = 'SELECT * FROM gvwys WHERE msg_id = $1 AND ended = $2'
        res = await self.bot.db.fetchrow(query, msg_id, False)
        if not res:
            return await ctx.send(f'There is no active giveaway with message ID `{msg_id}`.')
        await ctx.send('Ending...')
        await self.win(res)

    @commands.command()
    @commands.has_role(794618677806104576)
    async def giveaway(self, ctx):
        """Starts an interactive giveaway-making process.
           You need the `Giveaways` role in SLounge to do this.
           If you want to host a giveaway, ask an admin.
        """
        await ctx.send('Channel?')
        while True:
            msg = await self.wait_for_msg(ctx, 30)
            if not msg:
                return
            try:
                channel = await commands.TextChannelConverter().convert(ctx, msg.content)
                break
            except commands.BadArgument:
                await ctx.send(f'`{msg.content}` isn\'t a valid channel. '
                               'Try again.')
        await ctx.send('Prize?')
        while True:
            msg = await self.wait_for_msg(ctx, 60)
            if not msg:
                return
            if len(msg.content) > 256:
                await ctx.send('The prize must be 256 characters or under. '
                               'Try a shorter prize so it can fit ))')
            else:
                prize = msg.content
                break
        await ctx.send('# of Winners?')
        while True:
            msg = await self.wait_for_msg(ctx, 60)
            if not msg:
                return
            if not msg.content.isdigit() or int(msg.content) < 1:
                await ctx.send('Does that look like a positive integer to you? '
                               'Try again, baka.')
            else:
                winners = int(msg.content)
                break
        await ctx.send('Duration?')
        while True:
            msg = await self.wait_for_msg(ctx, 60)
            if not msg:
                return
            duration = await TimeConverter().convert(ctx, msg.content)
            if duration == 0:
                await ctx.send('That doesn\'t seem to be a valid time... '
                               'try something like `6d 9m 42s`.')
            else:
                break
        prompt = await ctx.send('Role requirement? (optional, press \u23e9 to skip)\n'
                                '**If this is a level role, simply type out the level number.**')
        await prompt.add_reaction('\u23e9')

        def msg_check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        def r_check(p):
            return p.message_id == prompt.id and p.user_id == ctx.author.id and str(p.emoji) == '\u23e9'

        while True:
            done, pending = await asyncio.wait([
                self.bot.wait_for('message', check=msg_check),
                self.bot.wait_for('raw_reaction_add', check=r_check)
            ], return_when=asyncio.FIRST_COMPLETED, timeout=60)

            for future in pending:
                future.cancel()
            if len(done) == 0:
                return await ctx.send('BAKA, imagine going AFK now ((')
            payload = done.pop().result()
            role_id = 0
            level = False

            if isinstance(payload, discord.Message):
                msg = payload
                if msg.content.isdigit():
                    if 0 < int(msg.content) < 69:
                        role_id = int(msg.content)
                        level = True
                        break
                try:
                    role = await commands.RoleConverter().convert(ctx, msg.content)
                    role_id = role.id
                    break
                except commands.BadArgument:
                    await ctx.send(f'I couldn\'t find a role that matches `{msg.content}`... '
                                   f'try again and make sure you spelled things right!')
            else:
                break

        prompt = await ctx.send('Description? (optional, press \u23e9 to skip).')
        await prompt.add_reaction('\u23e9')
        done, pending = await asyncio.wait([
            self.bot.wait_for('message', check=msg_check),
            self.bot.wait_for('raw_reaction_add', check=r_check)
        ], return_when=asyncio.FIRST_COMPLETED, timeout=60)

        for future in pending:
            future.cancel()
        if len(done) == 0:
            return await ctx.send('BAKA, imagine going AFK now ((')
        payload = done.pop().result()
        desc = ''
        if isinstance(payload, discord.Message):
            desc = payload.content

        await ctx.send('Last but not least, emoji? ))')
        while True:
            msg = await self.wait_for_msg(ctx, 60)
            if not msg:
                return
            try:
                emoji = await commands.EmojiConverter().convert(ctx, msg.content)
                break
            except commands.BadArgument:
                if msg.content in UNICODE_EMOJI:
                    emoji = msg.content
                    break
                else:
                    await ctx.send(f'I couldn\'t find an emoji called `{msg.content}`... '
                                   f'if it\'s a custom one, make sure it\'s in this server!')

        end = int(time.time() + duration)
        embed = discord.Embed(
            title=prize + f' - {winners} Winners',
            description=desc,
            timestamp=datetime.utcfromtimestamp(end),
            color=discord.Colour.blue()
        ).add_field(
            name='\U0001f451 Host', value=ctx.author.mention, inline=False
        ).add_field(
            name='\U000023f0 Duration', value=precisedelta(duration), inline=False
        ).set_footer(
            text='React with the first emoji below to enter\nEnding time \u27a1',
            icon_url='https://cdn.discordapp.com/emojis/795660003369025546.gif?v=1'
        ).set_thumbnail(url='https://cdn.discordapp.com/attachments/725093929481142292/792530547120799764/'
                            'download_-_2020-12-26T181245.032.png')
        if role_id:
            if level:
                value = f'Must be at least **Level {role_id}**'
            else:
                mention = ctx.guild.get_role(role_id).mention
                value = f'Must have the {mention} role'
            embed = embed.to_dict()
            embed['fields'].insert(0, {'name': '\U0001f4dd Requirement', 'value': value, 'inline': False})
            embed = discord.Embed.from_dict(embed)
        embed = await channel.send(embed=embed)
        await embed.add_reaction(emoji)
        await channel.send('<@&728666898597937163>')
        self.msg_ids.append(embed.id)
        query = '''INSERT INTO gvwys (ch_id, msg_id, prize, winners, host_id, role_id, "end", ended, emoji) 
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                '''
        await self.bot.db.execute(
            query, channel.id, embed.id, prize, winners, ctx.author.id, role_id, end, False, str(emoji))
        await ctx.send(f'Your giveaway has started! {emoji}')

        async def task():
            await asyncio.sleep(duration)
            res = await self.bot.db.fetchrow('SELECT * FROM gvwys WHERE msg_id = $1', embed.id)
            await self.win(res)

        self.bot.loop.create_task(task())

    @commands.command(aliases=['timers'])
    async def giveaways(self, ctx):
        res = await self.bot.db.fetch('SELECT msg_id, ch_id, prize, "end" '
                                      'FROM gvwys WHERE ended = $1', False)
        if not res:
            return await ctx.send('No active giveaways.')
        desc = []
        for row in res:
            jump_url = f'https://discord.com/channels/{ctx.guild.id}/{row["ch_id"]}/{row["msg_id"]}'
            delta = precisedelta(row['end'] - time.time())
            desc.append(f'[**{row["prize"]}**]({jump_url})\nEnds in {delta}')

        embed = discord.Embed(
            title='Active Giveaways in SLounge',
            color=ctx.author.color,
            description='\n\n'.join(desc)
        ).set_thumbnail(url=ctx.guild.icon_url_as(format='png'))
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Giveaway(bot))
