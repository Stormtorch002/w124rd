from discord.ext import commands
import random
import asyncio


class RNG(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def rng(self, ctx, low: int = 1, high: int = 10):
        """Generates a random number between a specified low and high.
        If left blank, the low and high default to 1 and 10, respectively.

        **Usage**: `$rng [low] [high]`"""
        await ctx.send(random.randint(low, high))

    @commands.command()
    async def flip(self, ctx):
        """Flips a coin and randomly sends either Heads or Tails."""
        msg = await ctx.send(':coin: Flipping...')
        await asyncio.sleep(2)
        await msg.edit(content=random.choice(['Heads!', 'Tails!']))

    @commands.command()
    async def choose(self, ctx, *, items):
        """Randomly chooses between the items inputted.
           The items must be comma separated.

           **Usage**: `$choose <items>`"""
        items = items.split(', ')
        await ctx.send(random.choice(items))


def setup(bot):
    bot.add_cog(RNG(bot))
