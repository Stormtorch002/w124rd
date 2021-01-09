from discord.ext import commands
from akinator.async_aki import Akinator
import akinator
import discord
import asyncio


class Aki(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='aki')
    async def __aki(self, ctx):
        """A command that lets you play a game of Akinator. Choose any character and I will try to guess it!"""
        aki = Akinator()

        def check(m):
            return m.channel == ctx.channel and m.author == ctx.author

        q = await aki.start_game()
        progression = 80
        while True:
            embed = discord.Embed(title=q, color=discord.Colour.red())
            embed.set_author(name=f'{ctx.author} - Question {aki.step}',
                             icon_url=str(ctx.author.avatar_url_as(format='png')))
            embed.set_footer(text="y = Yes, n = No, idk = I don't know, p = Probably, pn = Probably not, b = back")
            await ctx.send(embed=embed)
            while True:
                try:
                    a = await self.bot.wait_for('message', timeout=15, check=check)
                except asyncio.TimeoutError:
                    await ctx.send(f'{ctx.author.mention}, you took too long to give an answer! Game canceled.')
                    return
                if a.content.lower() in ['back', 'b']:
                    try:
                        a = await aki.back()
                    except akinator.CantGoBackAnyFurther:
                        await ctx.send('You cannot go back any further!')
                elif a.content.lower() in ["i don't know", 'idk', 'i', 'i dont know']:
                    a = 2
                elif a.content.lower() in ['yes', 'y']:
                    a = 0
                elif a.content.lower() in ['no', 'n']:
                    a = 1
                elif a.content.lower() in ['probably not', 'pn']:
                    a = 4
                elif a.content.lower() in ['probably', 'p']:
                    a = 3
                else:
                    continue
                break
            try:
                q = await aki.answer(a)
            except akinator.AkiNoQuestions:
                await ctx.send(f'I have run out of questions to give you! You stumped me!')
                return
            if aki.progression >= progression:
                await aki.win()
                guess = aki.first_guess
                embed = discord.Embed(
                    title=guess['name'],
                    color=discord.Colour.red(),
                    description=guess['description'],
                    url=guess['absolute_picture_path']
                )
                embed.set_image(url=guess['absolute_picture_path'])
                embed.set_author(name='Is This Your Character?')
                await ctx.send(embed=embed)

                try:
                    correct = await self.bot.wait_for('message', timeout=15, check=check)
                except asyncio.TimeoutError:
                    correct = 'y'

                if correct.content.lower() in ['y', 'yes']:
                    await ctx.send('Guessed right one more time! I love playing with you!')
                    return
                elif correct.content.lower() in ['n', 'no']:
                    if progression == 80:
                        progression = 90
                    else:
                        await ctx.send('Dang it, you stumped me! Please play again sometime.')
                        return
                else:
                    return


def setup(bot):
    bot.add_cog(Aki(bot))
