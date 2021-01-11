from discord.ext import commands
import time
from cogs.utils.timeparser import TimeConverter
import asyncio
from humanize import precisedelta
import discord


class Reminder(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.dispatch())

    async def dispatch(self):
        res = await self.bot.db.fetch('SELECT id, user_id, time, reminder FROM reminders')
        for row in res:
            async def task():
                await asyncio.sleep(row['time'] - time.time())
                if await self.bot.db.fetchrow('SELECT id FROM reminders WHERE id = $1', row['id']):
                    user = self.bot.get_user(row['user_id'])
                    await user.send(f'**REMINDER:** {row["reminder"]}')
                    await self.bot.db.execute('DELETE FROM reminders WHERE id = $1', row['id'])

            self.bot.loop.create_task(task())

    @commands.command(aliases=['remind', 'remindme'])
    async def reminder(self, ctx, *, args):
        """Sets a reminder.
           I will DM you your reminder after the time specified.

           **Usage:** `$reminder <time> <reminder>`
        """
        length = await TimeConverter().convert(ctx, args)
        if length == 0:
            return await ctx.send('You didn\'t enter a valid amount of time... ((')

        text = ' '.join([word for word in args.split()
                         if len(word) == 1 or (not word[0].isdigit() and not word[1].isdigit())])
        text = text.rstrip(' in')
        t = int(time.time() + length)

        query = 'INSERT INTO reminders (user_id, time, reminder) VALUES ($1, $2, $3)'
        await self.bot.db.execute(query, ctx.author.id, t, text)

        async def task():
            await asyncio.sleep(length)
            await ctx.author.send(f'**REMINDER:** {text}')
            if await self.bot.db.fetchrow('DELETE FROM reminders WHERE time = $1 AND user_id = $2', t, ctx.author.id):
                await self.bot.db.execute('DELETE FROM reminders WHERE time = $1 AND user_id = $2', t, ctx.author.id)

        self.bot.loop.create_task(task())

        await ctx.send(f'I will remind you to `{text}` in {precisedelta(length)}!')

    @commands.command()
    async def reminders(self, ctx):
        """Lists all of your current active reminders."""
        res = await self.bot.db.fetch('SELECT reminder, time FROM reminders WHERE user_id = $1', ctx.author.id)
        if not res:
            return await ctx.send('You don\'t have any active reminders.')

        embed = discord.Embed(
            title='Your Reminders',
            color=ctx.author.color
        ).set_thumbnail(url='https://i.pinimg.com/originals/12/36/de/1236de5bbc669be9f9ccfbb58891e936.png')

        for row in res:
            delta = precisedelta(row['time'] - time.time())
            embed.add_field(name=row['reminder'], value=f'In {delta}', inline=False)

        await ctx.send(embed=embed)

    @commands.command(aliases=['removereminder', 'deletereminder', 'unremind', 'unremindme'])
    async def unreminder(self, ctx, *, reminder):
        query = 'SELECT reminder, id FROM reminders WHERE LOWER(reminder) = $1'
        res = await self.bot.db.fetchrow(query, reminder.lower())
        if not res:
            return await ctx.send(f'You don\'t have a reminder called `{reminder}`.')

        query = 'DELETE FROM reminders WHERE id = $1'
        await self.bot.db.execute(query, res['id'])
        await ctx.send(f'Your reminder to `{res["reminder"]}` has been removed.')


def setup(bot):
    bot.add_cog(Reminder(bot))
