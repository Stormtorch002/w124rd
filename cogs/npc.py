from discord.ext import commands
import aiohttp
import discord
import asyncio


class NPC(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = self.bot.db
        self.webhook = None
        self.session = None
        self.webhooks = {
            725164675679125515: 796591431980285984,
            725093929481142292: 750402737530732615
        }

    @commands.command()
    async def replay(self, ctx, channel: discord.TextChannel, msg_1: int, msg_2: int):
        """Replays a conversation between two message IDs provided.
           The messages will be sent by webhooks as if it were in real time.

           **Usage:** `$replay <first message ID> <last message ID>`
        """
        try:
            msg_1 = await channel.fetch_message(msg_1)
            msg_2 = await channel.fetch_message(msg_2)
        except discord.NotFound:
            return await ctx.send('One or more of the message IDs provided were invalid.')

        webhook = self.webhooks[ctx.channel.id]
        msgs = await channel.history(before=msg_2.created_at, after=msg_1.created_at).flatten()
        await webhook.send(msg_1.content,
                           avatar_url=str(msg_1.author.avatar_url_as(format='png')),
                           username=msg_1.author.display_name,
                           allowed_mentions=self.bot.allowed_mentions)
        for i in range(len(msgs)):
            msg = msgs[i]
            if not msg.content:
                continue
            if i == 0:
                await asyncio.sleep((msg.created_at - msg_1.created_at).total_seconds())
            else:
                await asyncio.sleep((msg.created_at - msgs[i - 1].created_at).total_seconds())
            await webhook.send(msg.content,
                               avatar_url=str(msg.author.avatar_url_as(format='png')),
                               username=msg.author.display_name,
                               allowed_mentions=self.bot.allowed_mentions)
        await ctx.send('Done!')

    @commands.group(invoke_without_command=True)
    async def npc(self, ctx, alias, *, message):
        """Sends a message using a custom webhook, or NPC.
        NPCs can only be used in general.
        You can add/remove NPCs with the listed subcommands.

        **Usage:** `$npc <alias> <message>`"""
        res = await self.db.fetchrow('SELECT avatar_url, username FROM npcs WHERE alias = $1', alias.lower())
        if not res:
            return await ctx.send(f'There isn\'t an NPC with alias `{alias}`.')
        if ctx.channel.id not in self.webhooks:
            return await ctx.send('NPCs can only be used in bot-cmds and general.')
        await self.webhooks[ctx.channel.id].send(
            message,
            avatar_url=res['avatar_url'],
            username=res['username'],
            allowed_mentions=self.bot.allowed_mentions
        )
        await ctx.message.delete()

    @npc.command(aliases=['create'])
    async def add(self, ctx, alias, username, pfp=None):
        """Adds an NPC.

           **Usage:** `$npc add <alias> <username> <pfp url>`"""
        if await self.db.fetchrow('SELECT id FROM npcs WHERE alias = $1', alias.lower()):
            return await ctx.send(f'Alias `{alias}` already in use.')
        if len(alias) > 16:
            return await ctx.send('Alias must be 16 characters or lower.')
        if len(username) > 32:
            return await ctx.send('Username must be 32 characters or lower.')
        if pfp:
            try:
                async with self.session.get(pfp) as resp:
                    if resp.status != 200:
                        return await ctx.send('The profile image link isn\'t working.')
            except aiohttp.InvalidURL:
                return await ctx.send('The profile image link isn\'t a valid URL.')
            avatar = pfp
        else:
            avatar = ''
        query = 'INSERT INTO npcs (user_id, username, avatar_url, alias) VALUES ($1, $2, $3, $4)'
        await self.db.execute(query, ctx.author.id, username, avatar, alias.lower())
        await ctx.send('Your NPC has been created!')

    @npc.command(aliases=['remove'])
    async def delete(self, ctx, *, alias):
        """Deletes an NPC.
           You must own the NPC or have Admin to delete it.

           **Usage:** `$npc delete <alias>`"""
        res = await self.db.fetchrow('SELECT user_id, username FROM npcs WHERE alias = $1', alias.lower())
        if not res:
            return await ctx.send(f'An NPC with alias `{alias}` doesn\'t exist.')
        if res['user_id'] != ctx.author.id and not ctx.author.guild_permissions.administrator:
            return await ctx.send('You have to either own the NPC or be Admin to delete it.')
        query = 'DELETE FROM npcs WHERE alias = $1'
        await self.db.execute(query, alias.lower())
        await ctx.send(f'Successfully deleted NPC `{res["username"]}`.')


def setup(bot):
    bot.add_cog(NPC(bot))
