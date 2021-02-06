from discord.ext import commands
import aiohttp
import json
import random
import discord


# officer
# we found the horny
# go to horny jail


class Hentai(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        with open('./cogs/hentai.json') as f:
            self.hentai = json.load(f)

    def cog_unload(self):
        with open('./cogs/hentai.json', 'w') as f:
            json.dump(self.hentai, f, indent=4)

    @commands.command(aliases=['waifu', 'storchylikesmypp'])
    async def hentai(self, ctx, *, waifu):
        """Gets a random picture (from reddit) of your favorite waifu!

           **Usage:** `$waifu <waifu>`
        """
        try:
            posts = self.hentai[waifu.lower()]
        except KeyError:
            return await ctx.send('Waifu not found ((')
        post = random.choice(posts)
        post = post['data']
        embed = discord.Embed(
            title=post['title'],
            url=post['url_overridden_by_dest'],
            color=ctx.author.color
        ).set_image(url=post['url_overridden_by_dest'])
        await ctx.send(embed=embed)
        # what the actual fuck
        # this skin wasnt made by me ok

    @commands.command()
    async def addwaifu(self, ctx, sub, *, alias):
        if alias.lower() in self.hentai:
            return await ctx.send('Waifu already in use CHIGGER CHIGGER CHIGGER CHIGGER (((((((((((((((((((((((((((((((((((((((((((((((((((.')

        async with aiohttp.ClientSession() as session:
            async with session.get(f'https://reddit.com/r/{sub}.json?limit=420') as resp:
                if resp.status == 404:
                    return await ctx.send(f'Subreddit `{sub}` not found.')
                elif resp.status != 200:
                    return await ctx.send(f'`{resp.status}`: Something went wrong while fetching the waifus ((')
                data = await resp.json()

        data = data['data']['children']
        for p in data:
            post = p['data']
            suffixes = ['png', 'jpg', 'jpeg', 'gif']
            if post['over_18']:
                data.remove(p)
            elif not post.get('url_overridden_by_dest'):
                data.remove(p)
            elif not any(post.get('url_overridden_by_dest').endswith(suffix) for suffix in suffixes):
                data.remove(p)

        self.hentai[alias.lower()] = data
        await ctx.send(f'Your waifu has been added with subreddit `r/{sub}`. See it with `$waifu {alias}`!')


def setup(bot):
    bot.add_cog(Hentai(bot))
