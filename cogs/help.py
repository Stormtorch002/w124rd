import asyncio
import discord
from discord.ext import commands, menus


class EmbedMenu(menus.Menu):
    def __init__(self, pages):
        super().__init__(clear_reactions_after=True)
        self.pages = pages
        self.current_page = 0
        print('Loaded help.py')

    def _skip_when(self):
        return len(self.pages) <= 2

    async def update_page(self):
        embed = self.pages[self.current_page]
        await self.message.edit(embed=embed)

    @menus.button("\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\ufe0f", skip_if=_skip_when)
    async def jump_to_first(self, payload):
        self.current_page = 0
        await self.update_page()

    @menus.button("\N{BLACK LEFT-POINTING TRIANGLE}\ufe0f")
    async def previous_page(self, payload):
        if self.current_page > 0:
            self.current_page -= 1
            await self.update_page()

    @menus.button('\N{BLACK SQUARE FOR STOP}\ufe0f')
    async def stop_pages(self, payload):
        self.stop()

    @menus.button("\N{BLACK RIGHT-POINTING TRIANGLE}\ufe0f")
    async def next_page(self, payload):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            await self.update_page()

    @menus.button("\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\ufe0f", skip_if=_skip_when)
    async def jump_to_last(self, payload):
        self.current_page = len(self.pages) - 1
        await self.update_page()

    @menus.button("\N{INPUT SYMBOL FOR NUMBERS}")
    async def jump_to(self, payload):
        msg = await self.message.channel.send("Which page would you like to go to?")
        n = None

        def check(m):
            return m.author == self.ctx.author and m.channel == self.ctx.channel and m.content.isdigit()

        try:
            n = await self.bot.wait_for("message", check=check, timeout=30)
        except asyncio.TimeoutError:
            return
        else:
            page = int(n.content) - 1
            if not 0 < page < len(self.pages):
                return await self.ctx.send(f'That page doesn\'t exist ((')
            self.current_page = page
            await self.update_page()
        finally:
            await msg.delete()
            if n:
                await n.delete()

    async def send_initial_message(self, ctx, channel):
        return await channel.send(embed=self.pages[self.current_page])


class PaginatedHelpCommand(commands.HelpCommand):

    def format_commands(self, cog, cmds, *, pages):
        if not cmds:
            return
        desc = ' '.join(f'`{command.qualified_name}`' for command in cmds)
        embed = discord.Embed(colour=self.context.author.color,
                              title=cog.qualified_name if cog else 'Unsorted',
                              description=desc)
        embed.add_field(
            name='Description',
            value=f'**{cog.description}**' if cog else f'**No description**'
        )
        embed.set_footer(
            text=f'Use "{self.clean_prefix}help <command>" for more information.')
        pages.append(embed)

    async def send_bot_help(self, mapping):
        pages = []

        for cog, cmds in mapping.items():
            cmds = await self.filter_commands(cmds, sort=True)
            self.format_commands(cog, cmds, pages=pages)

        total = len(pages)
        for i, embed in enumerate(pages, start=1):
            embed.title = f'Page {i}/{total}: {embed.title}'

        pg = EmbedMenu(pages)
        await pg.start(self.context)

    async def send_cog_help(self, cog):
        pages = []
        self.format_commands(cog, await self.filter_commands(cog.get_commands(), sort=True), pages=pages)

        total = len(pages)
        for i, embed in enumerate(pages, start=1):
            embed.title = f'Page {i}/{total}: {embed.title}'

        pg = EmbedMenu(pages)
        await pg.start(self.context)

    def command_not_found(self, string):
        return f'Command `{string}` doesn\'t exist.'

    async def send_group_help(self, group: commands.Group):
        if not group.commands:
            return await self.send_command_help(group)
        embed = discord.Embed(colour=self.context.author.color)
        embed.title = f'{self.clean_prefix}{group.qualified_name} {group.signature}'
        embed.description = group.help or 'No help provided'
        embed.set_footer(
            text=f'Use "{self.clean_prefix}help <command>" for more information.')
        embed.add_field(name='Subcommands', value=' '.join(
            f'`{c.name}`' for c in group.commands))
        await self.context.send(embed=embed)

    async def send_command_help(self, command: commands.Command):
        embed = discord.Embed(colour=self.context.author.color)
        embed.title = f'{self.clean_prefix}{command.qualified_name}'
        embed.description = command.help or 'No help provided'
        await self.context.send(embed=embed)


def setup(bot):
    bot._original_help_command = bot.help_command
    bot.help_command = PaginatedHelpCommand()


def teardown(bot):
    bot.help_command = bot._original_help_command
