from discord.ext import commands
import traceback
import discord


class EH(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions) or isinstance(error, commands.MissingAnyRole):
            await ctx.send(f'You don\'t have enough perms to use this command ((')
        elif isinstance(error, commands.BadArgument) or \
                isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f'Incorrect usage! To see how to use this command, '
                           f'try `$help {ctx.command.qualified_name}`.')
        else:
            etype = type(error)
            trace = error.__traceback__
            lines = traceback.format_exception(etype, error, trace)
            traceback_text = ''.join(lines)
            embed = discord.Embed(
                title=f'Error in ${ctx.command.qualified_name}',
                url=ctx.message.jump_url,
                description=f'```py\n{traceback_text}```',
                color=ctx.author.color
            ).add_field(
                name='Channel', value=ctx.channel.mention
            ).add_field(
                name='User', value=ctx.author.mention
            )
            await self.bot.storch.send(embed=embed)


def setup(bot):
    bot.add_cog(EH(bot))
