from discord.ext import commands
from owoify import owoify


class Furry(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.group(invoke_without_command=True)
    async def furry(self, ctx):
        """A command that contains a variety of subcommands to furrify text.
        You have been warned."""
        await ctx.send_help(ctx.command)

    @furry.command()
    async def uvu(self, ctx, *, text):
        """Turns text into UvU.

        **Usage:** `$furry uvu <text>`"""
        await ctx.send(owoify(text, 'uvu'))

    @furry.command()
    async def uwu(self, ctx, *, text):
        """Turns text into UwU.

        **Usage:** `$furry uwu <text>`"""
        await ctx.send(owoify(text, 'uwu'))

    @furry.command()
    async def owo(self, ctx, *, text):
        """Turns text into OwO.

        **Usage:** `$furry owo <text>`"""
        await ctx.send(owoify(text, 'owo'))


def setup(bot):
    bot.add_cog(Furry(bot))
