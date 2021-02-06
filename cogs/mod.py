from discord.ext import commands
import discord
import time
from cogs.utils.timeparser import TimeConverter
from datetime import datetime
from typing import Union
from humanize import precisedelta
import asyncio
from cogs.utils.chunk import chunk
from pytz import timezone


def unbypass(text):
    return ''.join(ch for ch in text.lower() if ch.isalpha())


class Mod(commands.Cog):
    ALL_MODS = (725117477578866798, 725117459803275306, 725117475368206377, 725117475997483126)
    MODS = (725117459803275306, 725117475368206377, 725117475997483126)

    def __init__(self, bot):
        self.bot = bot
        self.db = self.bot.db
        self.swears = (
            'nigga',
            'nigger',
            'fag',
            'retard',
            'cunt'
        )
        self.bot.swears = self.swears
        self.est = timezone('US/Eastern')
        self.muted = 750144772559208599
        self.bot.loop.create_task(self.dispatch_bans())
        self.bot.loop.create_task(self.dispatch_mutes())

    def avatar(self, user):
        user = self.bot.get_user(user.id)
        fmt = 'png' if not user.is_avatar_animated() else 'gif'
        return str(user.avatar_url_as(format=fmt))

    async def dispatch_mutes(self):
        res = await self.db.fetch('SELECT user_id, "end" FROM mutes')
        for row in res:
            async def task(end):
                await asyncio.sleep(row['end'] - time.time())
                query = 'SELECT "end" FROM mutes WHERE user_id = $1'
                res2 = await self.db.fetchrow(query, row['user_id'])
                if res2 and end == res2['end']:
                    member = self.bot.slounge.get_member(row['user_id'])
                    await member.remove_roles(discord.Object(id=self.muted))
                    print(f'Unmuted {member}')

            self.bot.loop.create_task(task(row['end']))

    async def dispatch_bans(self):
        res = await self.db.fetch('SELECT user_id, "end" FROM bans')
        for row in res:
            async def task(end):
                await asyncio.sleep(row['end'] - time.time())
                query = 'SELECT "end" FROM bans WHERE user_id = $1'
                res2 = await self.db.fetchrow(query, row['user_id'])
                if res2 and end == res2['end']:
                    await self.bot.slounge.unban(discord.Object(id=row['user_id']))

            self.bot.loop.create_task(task(row['end']))

    async def warn(self, user, mod, reason):
        query = 'INSERT INTO warns (user_id, mod_id, reason, time) VALUES ($1, $2, $3, $4)'
        await self.db.execute(query, user.id, mod.id, reason, int(time.time()))
        query = 'SELECT COUNT(id) FROM warns WHERE user_id = $1'
        return (await self.db.fetchrow(query, user.id))['count']

    async def check_swears(self, message):
        if message.author.bot:
            return
        text = unbypass(message.content)
        for swear in self.swears:
            if swear in text:
                await message.delete()
                return True
        return False

    async def warn_embed(self, ctx, res, page, *, user=None, mod=None):
        pages = []
        i = 1
        length = len(res) // 5 + 1
        chunks = chunk(res, 5)

        for warns in chunks:
            if user:
                s = f'for {user}'
            elif mod:
                s = f'done by {mod}'
            else:
                s = ''
            embed = discord.Embed(
                title=f'Warnings {s} - Page {i}/{length}',
                color=ctx.author.color
            )
            for warn in warns:
                if not user:
                    u = self.bot.get_user(warn["user_id"])
                    u = u.mention if u else 'User left'
                    u = f'**User:** {u}\n'
                else:
                    u = ''
                if not mod:
                    m = self.bot.get_user(warn["mod_id"])
                    m = m.mention if m else 'Mod left'
                    m = f'**Mod:** {m}\n'
                else:
                    m = ''
                t = datetime.fromtimestamp(warn['time']).astimezone(self.est).strftime('%m/%d %I:%M:%S %p')

                embed.add_field(name=f'ID: {warn["id"]}', value=u + m + f'**Time:** {t}\n'
                                                                        f'**Reason:** {warn["reason"]}',
                                inline=False)
            pages.append(embed)

        try:
            embed = pages[page - 1]
        except IndexError:
            return await ctx.send(f'Page `{page}` doesn\'t exist ((')
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        bad = await self.check_swears(message)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.content != after.content:
            await self.check_swears(after)

    @commands.group(name='warn', invoke_without_command=True)
    @commands.has_any_role(*ALL_MODS)
    async def warn_cmd(self, ctx, member: discord.Member, *, reason):
        count = await self.warn(member, ctx.author, reason)
        embed = discord.Embed(
            color=member.color,
            title='Warn Issued'
        ).set_author(
            name=str(member), icon_url=member.avatar_url_as(format='png')
        ).add_field(
            name='Reason', value=f'`{reason}`'
        ).add_field(
            name='Total Warnings', value=f'**{count}**'
        )
        await ctx.send(embed=embed)

    @commands.group(invoke_without_command=True, aliases=['del', 'remove', 'delete'])
    @commands.has_any_role(*MODS)
    async def clearwarn(self, ctx, warning_ids: commands.Greedy[int]):
        cleared = {}
        for wid in warning_ids:
            res = await self.db.fetchrow('SELECT user_id FROM warns WHERE id = $1', wid)
            if res:
                user = self.bot.get_user(res['user_id'])
                if user in cleared:
                    cleared[user] += 1
                else:
                    cleared[user] = 1

        query = 'DELETE FROM warns WHERE "id" = ANY($1)'
        await self.db.execute(query, warning_ids)

        embed = discord.Embed(
            title='Warnings Cleared',
            description=f'Successfully cleared `{len(cleared)}` warnings.',
            color=ctx.author.color
        )
        for user, count in cleared.items():
            embed.add_field(name=str(user), value=f'`{count}`', inline=False)

        await ctx.send(embed=embed)

    @clearwarn.command()
    @commands.has_permissions(administrator=True)
    async def all(self, ctx):
        await ctx.send('Are you SURE you want to delete all warnings? This cannot be undone.')

        def check(m):
            return m.channel == ctx.channel and m.author == ctx.author and m.content.lower() in ('y', 'yes')

        try:
            await self.bot.wait_for('message', check=check, timeout=15)
        except asyncio.TimeoutError:
            return

        await self.db.execute('DELETE FROM warns')
        await ctx.send('Cleared all warnings ))')

    @commands.command()
    async def howmanywarningsdoihave(self, ctx):
        await ctx.send((await self.bot.db.fetchrow('SELECT COUNT(id) FROM warns WHERE user_id = $1', ctx.author.id))['count'])

    @clearwarn.command()
    @commands.has_any_role(*MODS)
    async def latest(self, ctx):
        query = 'SELECT id, user_id FROM warns ORDER BY "id" DESC'
        res = await self.bot.db.fetchrow(query)
        user_id = res['user_id']

        if user_id:
            await self.bot.db.execute('DELETE FROM warns WHERE id = $1', res['id'])
            await ctx.send(f'Cleared warning from `{ctx.guild.get_member(user_id)}`')
        else:
            return await ctx.send('No warnings found.')

    @commands.group(aliases=['warns'], invoke_without_command=True)
    @commands.has_any_role(*ALL_MODS)
    async def warnings(self, ctx, page: int = 1):
        query = 'SELECT id, user_id, mod_id, time, reason FROM warns'
        res = await self.db.fetch(query)
        if not res:
            return await ctx.send('No warnings found.')
        await self.warn_embed(ctx, res, page)

    @warnings.command(name='for')
    @commands.has_any_role(*ALL_MODS)
    async def _for(self, ctx, member: discord.Member, page: int = 1):
        query = 'SELECT id, user_id, mod_id, time, reason FROM warns WHERE user_id = $1'
        res = await self.db.fetch(query, member.id)
        if not res:
            return await ctx.send('No warnings found.')
        await self.warn_embed(ctx, res, page, user=member)

    @warnings.command(aliases=['by', 'from'])
    @commands.has_any_role(*ALL_MODS)
    async def done(self, ctx, mod: discord.Member, page: int = 1):
        query = 'SELECT id, user_id, mod_id, time, reason FROM warns WHERE mod_id = $1'
        res = await self.db.fetch(query, mod.id)
        if not res:
            return await ctx.send('No warnings found.')
        await self.warn_embed(ctx, res, page, mod=mod)

    @commands.command()
    @commands.has_any_role(*ALL_MODS)
    async def mute(self, ctx, member: discord.Member, *, time_reason):

        if 'Muted' in [r.name for r in member.roles]:
            return await ctx.send(f'`{member}` is already muted.')

        length = await TimeConverter().convert(ctx, time_reason)
        t = int(time.time() + length)
        reason = ' '.join([word for word in time_reason.split()
                           if len(word) == 1 or (not word[0].isdigit() and not word[1].isdigit())])

        if reason.isspace():
            reason = 'None'

        role = ctx.guild.get_role(self.muted)
        await member.add_roles(role, reason=reason)

        if length == 0:
            return await ctx.send(f'Successfully muted `{member}` indefinitely.')

        query = '''INSERT INTO mutes (user_id, "end") 
                   VALUES ($1, $2) 
                   ON CONFLICT (user_id)
                   DO UPDATE
                   SET "end" = $2
                '''
        await self.db.execute(query, member.id, t)

        async def task(end):
            await asyncio.sleep(length)
            res = await self.db.fetchrow('SELECT "end" FROM mutes WHERE user_id = $1', member.id)
            if res and res['end'] == end:
                await member.remove_roles(role)
                print(f'Unmuted {member}')

        self.bot.loop.create_task(task(t))

        embed = discord.Embed(color=member.color)
        embed.set_author(name=f'{member} was Muted', icon_url=self.avatar(member))
        embed.add_field(name='User', value=member.mention)
        embed.add_field(name='Length', value=precisedelta(length))
        embed.add_field(name='Unmute Time',
                        value=datetime.fromtimestamp(time.time() + length).strftime('%m/%d %I:%M:%S %p'))
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_any_role(*ALL_MODS)
    async def unmute(self, ctx, *, member: discord.Member):
        query = 'DELETE FROM mutes WHERE user_id = $1'
        await self.db.execute(query, member.id)

        if self.muted in [r.id for r in member.roles]:
            await member.remove_roles(ctx.guild.get_role(self.muted))
        else:
            return await ctx.send(f'`{member}` isn\'t currently muted.')

        await ctx.send(f'Successfully unmuted `{member}`.')

    @commands.Cog.listener()
    async def on_member_join(self, member):
        query = 'SELECT id FROM mutes WHERE user_id = $1'
        if await self.db.fetchrow(query, member.id):
            await member.add_roles(member.guild.get_role(self.muted))

    @commands.command()
    @commands.has_any_role(*MODS)
    async def ban(self, ctx, member: Union[discord.Member, int], *, time_reason):
        i = member.id if isinstance(member, discord.Member) else member
        if i in [entry.user.id for entry in await ctx.guild.bans()]:
            return await ctx.send(f'`{member}` is already banned.')

        length = await TimeConverter().convert(ctx, time_reason)
        t = int(length + time.time())
        reason = ' '.join([word for word in time_reason.split()
                           if not (word[0].isdigit() and not word[1].isdigit())])
        reason = None if reason.isspace() else reason
        await ctx.guild.ban(discord.Object(id=i), reason=reason)

        if t == 0:
            await ctx.send(f'Successfully banned `{member}`.')
            return

        query = '''INSERT INTO bans (user_id, "end") 
                   VALUES ($1, $2) 
                   ON CONFLICT (user_id)
                   DO UPDATE
                   SET "end" = $2
                '''
        await self.db.execute(query, member.id, t)

        async def task(end):
            await asyncio.sleep(length)
            res = await self.db.fetchrow('SELECT "end" FROM bans WHERE user_id = $1', member.id)
            if res and res['end'] == end:
                await ctx.guild.unban(discord.Object(id=member.id))
                print(f'Unbanned {member}')

        self.bot.loop.create_task(task(t))

        embed = discord.Embed(color=member.color)
        embed.set_author(name=f'{member} was Tempbanned', icon_url=self.avatar(member))
        embed.add_field(name='User', value=member.mention)
        embed.add_field(name='Length', value=precisedelta(length))
        embed.add_field(name='Unban Time',
                        value=datetime.fromtimestamp(time.time() + length).strftime('%m/%d %I:%M:%S %p'))
        await ctx.send(embed=embed)

    @commands.command(aliases=['muted'])
    @commands.has_any_role(*ALL_MODS)
    async def mutes(self, ctx):
        res = await self.db.fetch('SELECT user_id, "end" FROM mutes')
        if not res:
            return await ctx.send('No one is currently muted.')

        embed = discord.Embed(
            title='Muted Members',
            color=ctx.author.color
        ).set_thumbnail(url=str(ctx.guild.icon_url_as(format='png')))

        for row in res:
            user = ctx.guild.get_member(row['user_id'])
            username = str(user) if user else f'Member {row["user_id"]} left'
            delta = precisedelta(row['end'] - time.time())
            t = datetime.fromtimestamp(row['end']).astimezone(self.est).strftime('%m/%d %I:%M:%S %p')

            embed.add_field(name=username, value=f'Unmuted in {delta}\n({t})')

        await ctx.send(embed=embed)

    @commands.command(aliases=['banned', 'tempbans', 'tempbanned'])
    @commands.has_any_role(*ALL_MODS)
    async def bans(self, ctx):
        res = await self.db.fetch('SELECT user_id, "end" FROM bans')
        if not res:
            return await ctx.send('No one is currently tempbanned.')

        embed = discord.Embed(
            title='Tempbanned Members',
            color=ctx.author.color
        ).set_thumbnail(url=str(ctx.guild.icon_url_as(format='png')))

        for row in res:
            user = ctx.guild.get_member(row['user_id'])
            username = str(user) if user else f'Member {row["user_id"]} left'
            delta = precisedelta(row['end'] - time.time())
            t = datetime.fromtimestamp(row['end']).astimezone(self.est).strftime('%m/%d %I:%M:%S %p')

            embed.add_field(name=username, value=f'Unbanned in {delta}\n({t})')

        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_any_role(*MODS)
    async def purge(self, ctx, amount: int, user: discord.User = None):
        if user:
            
            def check(m):
                return m.author == user or m == ctx.message

            msgs = []
            i = 0
            while True:
                i += 1
                async for msg in ctx.channel.history(limit=100):
                    if check(msg):
                        msgs.append(msg)
                    if i >= 10 or len(msgs) == amount + 1 or len(msgs) >= 100:
                        break
                if i >= 10 or len(msgs) == amount + 1 or len(msgs) >= 100:
                        break

            await ctx.channel.delete_messages(msgs)
            
        await ctx.channel.purge(limit=amount + 1, check=check)

    @commands.command()
    @commands.has_any_role(*MODS)
    async def slowmode(self, ctx, channel: discord.TextChannel, delay: float):
        await channel.edit(slowmode_delay=delay)
        await ctx.send('Done')

    @commands.command()
    @commands.has_any_role(*MODS)
    async def kick(self, ctx, member: discord.Member, *, reason=None):
        await member.kick(reason=reason)
        await ctx.send(f'Successfully kicked `{member}`.')


def setup(bot):
    bot.add_cog(Mod(bot))
