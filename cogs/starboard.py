from discord.ext import commands 
import discord 


class Starboard(commands.Cog):

    def __init__(self, bot):
        self.bot = bot 

    async def starboard(self, payload):
        star = '\U00002b50'
        if str(payload.emoji) == star:
            msg = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
            reaction = discord.utils.find(lambda r: str(r.emoji) == star, msg.reactions)

            query = 'SELECT id, embed_id FROM starboard WHERE msg_id = $1'
            res = await self.bot.db.fetchrow(query, payload.message_id)

            starch = self.bot.get_channel(804004543179522118)

            if not res:
                if reaction.count >= 3:
                    if not msg.embeds:
                        embed = discord.Embed(
                            color=msg.author.color,
                            description=msg.content,
                            title=f'{reaction.count} \\{star}',
                            url=msg.jump_url
                        ).set_author(
                            name=str(msg.author),
                            icon_url=str(msg.author.avatar_url_as(format='png')),
                            url=msg.jump_url
                        ).add_field(
                            name='\u200b',
                            value=f'[**Jump to Message**]({msg.jump_url})'
                        )
                        for a in msg.attachments:
                            if any(a.url.endswith(s) for s in ['.png', '.gif', '.jpeg', '.jpg']):
                                embed.set_image(url=msg.attachments[0].url)
                                break 
                    else:
                        embed = msg.embeds[0]
                        embed.title = f'{reaction.count} \\{star}'
                        embed.url = msg.jump_url 
                        embed.add_field(
                            name='\u200b',
                            value=f'[**Jump to Message**]({msg.jump_url})'
                        )
                        embed.set_footer(text='')
                    m = await starch.send(embed=embed)
                    query = 'INSERT INTO starboard(embed_id, msg_id) VALUES ($1, $2)'
                    await self.bot.db.execute(query, m.id, msg.id)
            else:
                try:
                    msg = (await starch.fetch_message(res['embed_id']))
                except discord.NotFound:
                    query = 'DELETE FROM starboard WHERE id = $1'
                    await self.bot.db.execute(query, res['id'])
                    return 

                embed = msg.embeds[0]
                embed.title = f'{reaction.count} \\{star}'
                await msg.edit(embed=embed)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        await self.starboard(payload)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        await self.starboard(payload)
            
            
def setup(bot):
    bot.add_cog(Starboard(bot))
