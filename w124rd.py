from discord.ext import commands
import discord
import config
import asyncpg
from prettytable import PrettyTable
from datetime import datetime
from pytz import timezone
from humanize import precisedelta
import aiohttp
from mtranslate import translate


class W124RD(commands.Bot):

    def __init__(self):
        super().__init__(
            command_prefix=config.PREFIX,
            case_insensitive=True,
            intents=discord.Intents.all(),
            allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=True)
        )
        self.COG_NAMES = (
            'jishaku',
            'cogs.rng',
            'cogs.help',
            'cogs.furry',
            'cogs.aki',
            'cogs.npc',
            'cogs.giveaway',
            'cogs.tag',
            'cogs.mod',
            'cogs.level',
            'cogs.chess',
            'cogs.snipe',
            'cogs.count',
            'cogs.reminder',
            'cogs.eh'
        )
        self.db = None
        self.slounge = None
        self.slounge_id = 641379116007817216
        self.loop.create_task(self.startup())

    async def startup(self):
        self.db = await asyncpg.create_pool(**config.PG)

        with open('./query.sql') as f:
            await self.db.execute(f.read())

        await self.wait_until_ready()
        self.storch = self.get_user(718475543061987329)
        self.slounge = self.get_guild(self.slounge_id)

        for cog_name in self.COG_NAMES:
            self.load_extension(cog_name)

    async def on_ready(self):
        print(f'{self.user.name} is ready\n'
              f'{discord.utils.oauth_url(self.user.id)}')


w124rd = W124RD()


@w124rd.command()
async def reload(ctx, name=None):
    if ctx.author.id not in (718475543061987329,):
        return
    msg = await ctx.send('Reloading...')
    if name:
        await msg.edit(content=f'Reloading `{name}.py`...')
        w124rd.reload_extension('cogs.' + name)
    else:
        for name in w124rd.COG_NAMES:
            short = name.lstrip('cogs.')
            await msg.edit(content=f'Reloading `{short}.py`...')
            w124rd.reload_extension(name)
    await msg.edit(content='Done!')


@w124rd.command()
async def sql(ctx, *, query):
    if ctx.author.id not in (718475543061987329,):
        return
    if query.lower().startswith('select '):
        table = PrettyTable()
        res = await w124rd.db.fetch(query)
        if not res:
            return await ctx.send('No rows queried.')
        table.field_names = list(res[0].keys())
        for row in res:
            table.add_row(list(row.values()))
        final = f'```{table.get_string()}```'
        if len(final) > 2000:
            data = bytes(final, 'utf-8')
            async with aiohttp.ClientSession() as session:
                async with session.post('https://mystb.in/documents', data=data) as r:
                    await ctx.send((await r.json())['key'])
        else:
            await ctx.send(final)
    else:
        res = await w124rd.db.execute(query)
        await ctx.send(f'```sql\n{res}```')


@w124rd.command()
async def trump(ctx):
    """Shows the amount of time before noon on January 20th (the time Trump's presidency will end)."""
    est = timezone('US/Eastern')
    kick = datetime(2021, 1, 20, hour=12).astimezone(est)
    now = datetime.now().astimezone(est)
    delta = precisedelta((kick - now).total_seconds())
    await ctx.send(f'Time until Trump gets kicked out:\n\n{delta}')


@w124rd.command(name='translate', aliases=['googletrans', 'trans'])
async def _translate(ctx, lang, *, text):
    """Translates text to the language given.

       **Usage:** `$translate <language code> <text>`
    """
    await ctx.send(await ctx.bot.loop.run_in_executor(None, translate, text, lang, 'auto'))


w124rd.run(config.TOKEN)
