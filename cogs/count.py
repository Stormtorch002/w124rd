from discord.ext import commands
from num2words import num2words


class Count(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.counting_id = 728716336527704085
        self.last_msg = None

    async def send_count(self, res, msg):
        if res:
            sent = []
            for row in res:
                query = 'UPDATE counts SET "count" = "count" + 1 WHERE "id" = $1'
                await self.bot.db.execute(query, row['id'])
                text = row['msg'].replace('{count}', str(row['count'] + 1))
                text = text.replace('{ordinal}', num2words(row['count'], to='ordinal_num'))
                sent.append(text)
            if sent:
                await msg.channel.send('\n\n'.join(sent))

    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.author.bot:
            return

        query = 'SELECT id, msg, "count" FROM counts WHERE POSITION(word IN $1) > 0 AND user_id = $2'
        res = await self.bot.db.fetch(query, f' {msg.content.lower()} ', msg.author.id)
        await self.send_count(res, msg)
        query = 'SELECT id, msg, "count" FROM counts WHERE POSITION(word IN $1) > 0 AND global = $2'
        res = await self.bot.db.fetch(query, f' {msg.content.lower()} ', True)
        if res:
            for row in res:
                await self.bot.db.execute('UPDATE counts SET count = count + 1 WHERE id = $1', row['id'])

    @commands.command()
    async def addcount(self, ctx, word, *, msg):
        """Adds a count for yourself.
           You need to provide a custom message for when I send your count.

           - Use `{count}` as a placeholder for the actual number.
           - Use `{ordinal}` as a placeholder for the suffixed number (1*st*, 69*th*)

           For example: `$addcount "lol" this is the {ordinal} time i said lol`

           **Usage:** `$addcount "<word>" <custom message>`.
        """
        word = word.lower()
        query = 'SELECT id FROM counts WHERE user_id = $1 AND word = $2'
        if await self.bot.db.fetchrow(query, ctx.author.id, word):
            return await ctx.send(f'You already have a `{word}` count. Counts are case insensitive.')
        query = 'INSERT INTO counts (user_id, word, count, msg, global) VALUES ($1, $2, $3, $4, $5)'
        await self.bot.db.execute(query, ctx.author.id, word, 0, msg, False)
        await ctx.send(f'Your `{word}` count has been added ))')

    @commands.command(aliases=['removecount'])
    async def deletecount(self, ctx, *, word):
        """Deletes an existing count that you have.

           **Usage:** `$deletecount <word>`
        """
        word = word.lower()
        query = 'SELECT id FROM counts WHERE user_id = $1 AND word = $2'
        if not await self.bot.db.fetchrow(query, ctx.author.id, word):
            return await ctx.send(f'You don\'t have a `{word}` count.')

        query = 'DELETE FROM counts WHERE word = $1 AND user_id = $2'
        await self.bot.db.execute(query, word, ctx.author.id)
        await ctx.send(f'Your `{word}` count has been removed.')


def setup(bot):
    bot.add_cog(Count(bot))
