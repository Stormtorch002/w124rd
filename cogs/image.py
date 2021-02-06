from discord.ext import commands, flags
from PIL import Image, ImageFont, ImageDraw, ImageOps
import aiohttp
from io import BytesIO
import discord
try:
    from cogs.level import border
except:
    pass
import textwrap
from colour import Color


pokemon_help = """Creates your own pokemon card!
To run this command, you need to provide flag arguments. All argument names start with `--`.

__The flags are:__
`--image`             
`--description`
`--weakness`
`--resistance`
`--retreat`
`--color`

*Only `--image` and `--description` are required.*

`--image` can be either a user OR an image URL.
`--description` is the main text of the card and includes attack info. **Attacks are separated with a semicolon**.
`--color` is the color of the text (defaults to white). Hex values are preferred.
`--weakness`, `--resistance`, and `--retreat` are all plain numbers that default to `0`.

**Example:** `$pokemon --image @Stormtorch --description Azusa laugh: stun your opponents for 5 minutes; Cringewarn: je moeder --color #c0ffee --resistance 69`
"""


class Images(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.font = './assets/fonts/sans.ttf'
        self.card = Image.open('./assets/images/pokemon.png')
        self.bed = Image.open('./assets/images/bed.png')
        self.default = Image.open('./assets/images/discord-logo.png')
        self.wtf = Image.open('./assets/images/wtf.png')
        self.wanted = Image.open('./assets/images/wanted.png')

    @commands.command()
    async def wanted(self, ctx, *, user: discord.User = None):
        if not user:
            user = ctx.author 
        
        data = BytesIO(await user.avatar_url_as(format='png').read())

        def executor():
            avatar = Image.open(data)
            avatar = avatar.convert(mode='RGBA')
            avatar = ImageOps.fit(avatar, (405-40, 497-215))
            copy = self.wanted.copy()
            copy.paste(avatar, (40, 215), avatar)

            buf = BytesIO()
            copy.save(buf, 'png')
            buf.seek(0)
            return buf 

        buffer = await self.bot.loop.run_in_executor(None, executor)
        await ctx.send(file=discord.File(fp=buffer, filename='wanted.png'))

    @commands.command()
    async def wtf(self, ctx, *, user: discord.User = None):
        if not user:
            user = ctx.author 

        data = BytesIO(await user.avatar_url_as(format='png').read())

        def executor():
            image = Image.open(data)
            image = image.convert(mode='RGBA')
            copy = self.wtf.copy()
            image = image.resize((42, 42))
            mask = Image.new("L", image.size, 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse([(0, 0), image.size], fill=255)
            copy.paste(image, (338, 193), mask)

            buf = BytesIO()
            copy.save(buf, 'png')
            buf.seek(0)
            return buf 

        buffer = await self.bot.loop.run_in_executor(None, executor)
        await ctx.send('credits to nemi', file=discord.File(fp=buffer, filename='LOLOL.png'))


    @commands.command()
    async def default(self, ctx, image_url=None):
        if not image_url:
            image = BytesIO(await ctx.author.avatar_url_as(format='png').read())
        else:
            try:
                user = await commands.UserConverter().convert(ctx, image_url)
                image = BytesIO(await user.avatar_url_as(format='png').read())
            except commands.BadArgument:
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(image_url) as resp:
                            if resp.status != 200:
                                return await ctx.send('The image URL you provided isnt working.')
                            image = BytesIO(await resp.read())
                except:
                    return await ctx.send('You need to provide EITHER a user or an image URL.')
        
        def executor(im):
            image = Image.open(im)
            image = ImageOps.fit(image, self.default.size)
            copy = self.default.copy()
            # draw = ImageDraw.Draw(copy)
            # draw.ellipse([(0, 0), copy.size], fill=(255, 255, 255, 255))
            pixels = copy.load() # create the pixel map
            pixels2 = image.load()
            for i in range(image.size[0]): # for every pixel:
                for j in range(image.size[1]):
                    if pixels[i, j][1] > 0:
                        # change to black if not red
                        pixels[i, j] = pixels2[i, j]
            buf = BytesIO()
            copy.save(buf, 'png')
            buf.seek(0)
            return buf

        buffer = await self.bot.loop.run_in_executor(None, executor, image)
        await ctx.send(file=discord.File(fp=buffer, filename='default.png'))

    @commands.command()
    async def bed(self, ctx, m1: discord.Member, m2: discord.Member = None):
        if not m2:
            m2 = m1
            m1 = ctx.author
        m1 = await m1.avatar_url_as(format='png').read()
        m2 = await m2.avatar_url_as(format='png').read()
        def executor(p1, p2):
            bed = self.bed.copy()
            m1 = Image.open(BytesIO(p1))
            m2 = Image.open(BytesIO(p2))
            m1, m2 = m1.convert(mode='RGBA'), m2.convert(mode='RGBA')
            m1 = m1.resize((250, 250))
            m2 = m2.resize((250, 250))

            mask = Image.new("L", m1.size, 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse([(0, 0), m1.size], fill=255)
            
            bed.paste(m1, (260, 380), mask)
            bed.paste(m2, (640, 400), mask)
            buffer = BytesIO()
            bed.save(buffer, 'png')
            buffer.seek(0)
            return buffer
        await ctx.send(file=discord.File(fp=await self.bot.loop.run_in_executor(None, executor, m1, m2), filename='bed.png'))

    @flags.command()
    @flags.add_flag('--image', nargs='+')
    @flags.add_flag('--description', nargs='+')
    @flags.add_flag('--weakness', type=int, default=0)
    @flags.add_flag('--resistance', type=int, default=0)
    @flags.add_flag('--retreat', type=int, default=0)
    @flags.add_flag('--color', '--colour', default=['#FFFFFF'], nargs='+')
    async def pokemon(self, ctx, **options):
        image = options.get('image')
        desc = options.get('description')
        weak = options.get('weakness')
        resis = options.get('resistance')
        retreat = options.get('retreat')
        color = ' '.join(options.get('color'))

        for x in (image, desc):
            if x is None:
                return await ctx.send('You must provide all of the following:\n\n'
                                      '`--image`\n`--description`')
        try:
            color = Color(color)
        except ValueError:
            return await ctx.send(f'`{color}` isn\'t a valid color.')
        rgb = tuple([int(255 * c) for c in color.rgb])
        image = ' '.join(image)
        desc = ' '.join(desc)

        try:
            user = await commands.UserConverter().convert(ctx, image)
            b = BytesIO(await user.avatar_url_as(format='png').read())
        except commands.BadArgument:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(image) as resp:
                        if resp.status != 200:
                            return await ctx.send('Invalid image URL provided.')
                        b = BytesIO(await resp.read())
            except:
                return await ctx.send('Invalid image URL provided.')

        def executor():
            with Image.open(b) as im:
                card = self.card.copy()
                im = ImageOps.fit(im, (344, 229))
                top_left = (38, 62)
                card.paste(im, top_left)

                draw = ImageDraw.Draw(card)
                font = ImageFont.truetype(self.font, 20)

                i = 315
                for ability in desc.split('; '):
                    wrapped = textwrap.wrap(ability, 35)
                    j = 0
                    for line in wrapped:
                        border(draw, (40, i + j), line, font, rgb, (0, 0, 0), 1)
                        j += 20
                    i += j - 20 + 40

                border(draw, (40, 508), str(weak), font, rgb, (0, 0, 0), 1)
                border(draw, (122, 508), str(resis), font, rgb, (0, 0, 0), 1)
                border(draw, (40, 548), str(retreat), font, rgb, (0, 0, 0), 1)

                buf = BytesIO()
                card.save(buf, 'PNG')
                buf.seek(0)
                return buf

        buffer = await self.bot.loop.run_in_executor(None, executor)
        await ctx.send(file=discord.File(fp=buffer, filename='card.png'))


def setup(bot):
    bot.add_cog(Images(bot))
    cmd = bot.get_command('pokemon')
    cmd.help = pokemon_help
