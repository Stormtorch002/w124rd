from discord.ext import commands, flags
from PIL import Image, ImageFont, ImageDraw


class Images(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @flags.command()
    @flags.add_flag('--name')
    async def pokemon(self, ctx, ):