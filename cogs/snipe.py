from discord.ext import commands
import time
import discord
from humanize import naturaldelta
import re


class Snipe(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def snipe(self, ctx, amount: int = 1):
        query = 'SELECT * FROM snipes WHERE delete = $1 ORDER BY "id" DESC LIMIT $2'
        res = (await self.bot.db.fetch(query, True, amount))[-1]

        a = ctx.guild.get_member(res['user_id'])
        content = res['content']
        images = res['images']

        for swear in self.bot.swears:
            pattern = re.compile(re.escape(swear), re.IGNORECASE)
            content = pattern.sub(r'\*'*len(swear), content)

        embed = discord.Embed(
            description=content,
            color=a.color,
        ).set_author(
            name=str(a),
            icon_url=str(a.avatar_url_as(format='png'))
        ).set_footer(
            text=f'Deleted {naturaldelta(time.time() - res["time"])} ago\n'
                 f'Sent {naturaldelta(time.time() - res["sent"] + 3600 * 5)} ago'
        )
        if images:
            embed.set_image(url=images[0])
        await ctx.send(embed=embed)

    @commands.command()
    async def editsnipe(self, ctx, amount: int = 1):
        query = 'SELECT * FROM snipes WHERE delete = $1 ORDER BY "id" DESC LIMIT $2'
        res = (await self.bot.db.fetch(query, False, amount))[-1]
        content = res['content']

        for swear in self.bot.swears:
            pattern = re.compile(re.escape(swear), re.IGNORECASE)
            content = pattern.sub(r'\*'*len(swear), content)

        a = ctx.guild.get_member(res['user_id'])
        embed = discord.Embed(
            description=content + f'\n\n[Jump to Message]({res["url"]})',
            color=a.color,
        ).set_author(
            name=str(a),
            icon_url=str(a.avatar_url_as(format='png'))
        ).set_footer(
            text=f'Edited {naturaldelta(time.time() - res["time"])} ago\n'
        )
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_delete(self, msg):
        if msg.author.bot:
            return
        query = '''INSERT INTO snipes (user_id, content, time, sent, delete, images) 
                   VALUES ($1, $2, $3, $4, $5, $6)
                '''
        await self.bot.db.execute(
            query,
            msg.author.id,
            msg.content,
            int(time.time()),
            int(msg.created_at.timestamp()),
            True,
            [a.url for a in msg.attachments]
        )

    @commands.Cog.listener()
    async def on_message_edit(self, msg, msg2):
        if msg.author.bot:
            return
        query = '''INSERT INTO snipes (user_id, content, time, sent, url, delete) 
                   VALUES ($1, $2, $3, $4, $5, $6)
                '''
        await self.bot.db.execute(
            query,
            msg.author.id,
            msg.content,
            int(time.time()),
            int(msg.created_at.timestamp()),
            msg.jump_url,
            False
        )


def setup(bot):
    bot.add_cog(Snipe(bot))
