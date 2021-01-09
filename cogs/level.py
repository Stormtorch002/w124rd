from discord.ext import commands
from PIL import Image, ImageFont, ImageDraw, ImageOps, ImageEnhance
from io import BytesIO
from colour import Color
import time
import random
import discord
import aiohttp
import math


def border(draw: ImageDraw.ImageDraw, xy: tuple, text, font: ImageFont, fill: tuple, outline: tuple,
           thiccness: int):
    x, y = xy[0], xy[1]
    draw.text((x - thiccness, y - thiccness), text, font=font, fill=outline)
    draw.text((x + thiccness, y - thiccness), text, font=font, fill=outline)
    draw.text((x - thiccness, y + thiccness), text, font=font, fill=outline)
    draw.text((x + thiccness, y + thiccness), text, font=font, fill=outline)
    draw.text(xy=(x, y), text=text, fill=fill, font=font)


def get_xp(lvl: int):
    lvl += 1
    xp = 21 * lvl * (lvl - 1)
    return xp


def get_level(xp: int):
    lvl = int((1 + math.sqrt(1 + 8 * xp / 42)) / 2)
    return lvl - 1


class Levels(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.disabled_channels = (
            725095850446946344,
            728659433541861476,
            728659470150008913,
            725164675679125515,
            728716336527704085,
            728717757490921603,
            728722955013718037,
            730486347474796544,
            740227585014759444,
            743855545697566750,
            743881454068695041
        )
        self.leveled_roles = {
            0: 744608325001281566,
            1: 726131163743256596,
            2: 726131155664896046,
            4: 726131162862583828,
            6: 726131148480053339,
            8: 725460673953529936,
            10: 725136991951519774,
            12: 725117516887621703,
            14: 725117516493357087,
            16: 725117514043883550,
            18: 725117513821716481,
            20: 725117511414186005,
            22: 725117508939677746,
            24: 725117506439610390,
            26: 725117506401861693,
            28: 725117503491014789,
            30: 725117501545119784,
            35: 725117500966043659,
            40: 725117498491404353,
            45: 725117496255840306,
            50: 725117495958175815,
            55: 725117493990916137,
            60: 725117491621265479,
            65: 725117491373801570,
            70: 725117488693641276
        }
        self.xp_cooldowns = {}
        self.zerotwo = 'https://media.istockphoto.com/videos/abstract-grid-background-loop-video-id1171924854?s=640x640'
        self.bot.loop.create_task(self.get_bytes())
        self.bot.loop.create_task(self.fetch_xp())
        self.bot.xp = {}

    async def get_bytes(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(self.zerotwo) as resp:
                self.zerotwo = await resp.read()

    async def fetch_xp(self):
        res = await self.bot.db.fetch('SELECT user_id, total_xp FROM xp')
        for row in res:
            self.bot.xp[row['user_id']] = row['total_xp']

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild:
            return
        if message.channel.id not in self.disabled_channels and not message.author.bot:
            if message.author.id not in self.xp_cooldowns or self.xp_cooldowns[message.author.id] < time.time():
                if message.author.id not in self.bot.xp:
                    self.bot.xp[message.author.id] = 0
                    query = '''INSERT INTO xp (user_id, total_xp, color, image) 
                               VALUES ($1, $2, $3, $4)
                               ON CONFLICT (user_id)
                               DO NOTHING'''
                    await self.bot.db.execute(query, message.author.id, 0, '#c0ffee', self.zerotwo)
                else:
                    old_level = get_level(self.bot.xp[message.author.id])
                    increment = random.randint(3, 7)
                    self.bot.xp[message.author.id] += increment
                    new_level = get_level(self.bot.xp[message.author.id])

                    authorroles = [role.id for role in message.author.roles]
                    roles = {lvl: self.leveled_roles[lvl] for lvl in self.leveled_roles if lvl <= new_level}
                    if roles:
                        keys = list(roles.keys())
                        lvl = max(keys)
                        role = roles[lvl]
                        keys.remove(lvl)
                        if role not in authorroles:
                            role = message.guild.get_role(role)
                            await message.author.add_roles(role)
                        for lvl in keys:
                            role = roles[lvl]
                            if role in authorroles:
                                role = message.guild.get_role(role)
                                await message.author.remove_roles(role)

                    query = 'UPDATE xp SET total_xp = total_xp + $1 WHERE user_id = $2'
                    await self.bot.db.execute(query, increment, message.author.id)
                    self.xp_cooldowns[message.author.id] = time.time() + 30

                    if new_level >= 6:
                        role = message.guild.get_role(750444981449130092)
                        if role not in message.author.roles:
                            await message.author.add_roles(role)

                    if old_level != new_level:
                        msg = f'Congrats, {message.author.mention}! You made it to level **{new_level}**.'
                        if new_level == 6:
                            msg += f'\n\n*You can now send images here.*'
                        await message.channel.send(msg)

    @commands.group(name='rank', invoke_without_command=True)
    async def _rank(self, ctx, *, mem: discord.Member = None):
        """Checks your level, xp, and rank with your own customizable and sexy rank card.

        **Usage:** `$rank [member]`
        """

        m = mem if mem else ctx.author

        try:
            xp = self.bot.xp[m.id]
        except KeyError:
            return await ctx.send(f"`{m}` isn't enlisted in the server level system yet.")

        async with ctx.channel.typing():
            rank = sorted([self.bot.xp[user] for user in self.bot.xp.keys()], reverse=True).index(xp) + 1
            start = time.time()

            query = 'SELECT color, image FROM xp WHERE user_id = $1'
            res = await self.bot.db.fetchrow(query, m.id)
            color, im = res['color'], res['image']

            if im == self.zerotwo:
                tip = 'You can do `$rank image <image url>` to change your rank card image!'
            else:
                tip = ''

            mx = xp
            current_level = get_level(mx)
            nlr = nl = None

            for l in self.leveled_roles.keys():
                if l > current_level:
                    nlr = ctx.guild.get_role(self.leveled_roles[l])
                    nl = l
                    break

            next_level = current_level + 1
            current_level_xp, next_level_xp = get_xp(current_level), get_xp(next_level)
            progress, total_xp = mx - current_level_xp, next_level_xp - current_level_xp
            ratio = progress / total_xp

            avatar_data = await m.avatar_url.read()

            def process_image():
                # open
                with \
                        Image.open('./assets/images/template.png') as template, \
                        Image.open(BytesIO(avatar_data)) as av, \
                        Image.open('./assets/images/border.png') as circle, \
                        Image.open(BytesIO(im)) as image:

                    # resize
                    circle = circle.resize(size=(235, 235))
                    size = image.size
                    multiplier = 900 / size[0]
                    image = image.resize(size=(900, int(size[1] * multiplier)))
                    image = ImageOps.fit(image, size=(900, 240))
                    # darken
                    enhancer = ImageEnhance.Brightness(image)
                    image = enhancer.enhance(0.5)
                    template.paste(image, (20, 25))
                    x = int(365 * ratio) + 355

                    if m.color == discord.Color.default():
                        c = (255, 255, 255)
                    else:
                        c = m.color.to_rgb()

                    avatar_size = int(template.size[1] * 2 / 3)
                    av = av.resize((avatar_size, avatar_size))
                    av = av.convert(mode='RGBA')

                    im_a = Image.new("L", av.size, 0)
                    draw = ImageDraw.Draw(im_a)
                    draw.ellipse([(0, 0), av.size], fill=255)
                    template.paste(av, (40, 45), im_a)
                    draw = ImageDraw.Draw(template, mode='RGBA')
                    draw.rectangle([(355, 175), (720, 200)], fill=(169, 169, 169, 255), outline=(0, 0, 0, 255))
                    draw.rectangle([(355, 175), (x, 200)], fill=color, outline=(0, 0, 0, 255))
                    font = ImageFont.truetype('./assets/fonts/mono.ttf', 38)
                    size = font.getsize(str(current_level))[0]
                    x = 325 - size
                    draw.text(xy=(x, 170), font=font, fill=(255, 255, 255, 255), text=str(current_level))
                    draw.text(xy=(750, 170), font=font, fill=(255, 255, 255, 255), text=str(current_level + 1))
                    font = ImageFont.truetype('./assets/fonts/ubuntu.ttf', 38)
                    border(draw=draw, font=font, xy=(300, 110), text=f'Rank: ', fill=(255, 255, 255, 255),
                           outline=(0, 0, 0, 255), thiccness=2)
                    textlen = font.getsize("Rank: ")[0]
                    font = ImageFont.truetype('./assets/fonts/mono.ttf', 48)
                    border(xy=(410, 107), draw=draw, text=str(rank), font=font, fill=color, thiccness=2,
                           outline=(0, 0, 0, 255))
                    ranklen = font.getsize(str(rank))[0]
                    totallen = textlen + ranklen + 315

                    if len(m.display_name) > 12:

                        if len(m.display_name) > 19:
                            text = m.display_name[:18]
                        else:
                            text = m.display_name

                        font = ImageFont.truetype('./assets/fonts/ubuntu.ttf', 36)
                        border(draw=draw, xy=(300, 50), text=text, font=font, fill=(c[0], c[1], c[2], 255),
                               outline=(0, 0, 0, 255), thiccness=1)
                    else:
                        font = ImageFont.truetype('./assets/fonts/ubuntu.ttf', 45)
                        text = m.display_name
                        border(draw=draw, xy=(295, 50), text=text, font=font, fill=(c[0], c[1], c[2], 255),
                               outline=(0, 0, 0, 255), thiccness=1)

                    x = font.getsize(text)[0] + 315

                    if x < totallen:
                        x = totallen + 5

                    draw.rectangle(xy=[(x, 55), (x + 5, 150)], fill=(255, 255, 255, 255), outline=(0, 0, 0, 255))
                    font = ImageFont.truetype('./assets/fonts/ubuntu.ttf', 32)
                    border(xy=(x + 30, 65), draw=draw, font=font, text='LEVEL', fill=(255, 255, 255, 255),
                           thiccness=2, outline=(0, 0, 0, 255))
                    border(xy=(x + 30, 115), draw=draw, font=font, text='TOTAL XP:', fill=(255, 255, 255, 255),
                           thiccness=2, outline=(0, 0, 0, 255))
                    font = ImageFont.truetype('./assets/fonts/mono.ttf', 62)
                    border(xy=(x + 130, 47), font=font, draw=draw, text=str(current_level), thiccness=2,
                           outline=(0, 0, 0, 255), fill=color)
                    font = ImageFont.truetype('./assets/fonts/mono.ttf', 42)

                    if mx > 999:
                        member_xp = f'{round(mx / 1000, 1)}K'
                    else:
                        member_xp = str(mx)

                    border(xy=(x + 190, 112), font=font, draw=draw, text=member_xp, thiccness=2,
                           outline=(0, 0, 0, 255), fill=color)

                    if nlr:
                        role_color = nlr.color.to_rgb()
                        color_tuple = (role_color[0], role_color[1], role_color[2], 255)
                        role_name = nlr.name.split(' | ')[0]
                        levels_to = nl - current_level

                        if levels_to == 1:
                            s = ''
                        else:
                            s = 's'

                        font = ImageFont.truetype('./assets/fonts/mono.ttf', 35)
                        text = f'{progress}/{total_xp}'
                        border(draw=draw, font=font, thiccness=1, text=text, fill=color,
                               outline=(0, 0, 0, 255), xy=(300, 220))
                        size = font.getsize(text)[0]
                        text = f' XP | {levels_to} Level{s} to '
                        font = ImageFont.truetype("./assets/fonts/ubuntu.ttf", 30)
                        border(draw=draw, font=font, thiccness=1, text=text, fill=(255, 255, 255, 255),
                               outline=(0, 0, 0, 255), xy=(300 + size, 220))
                        text_length = font.getsize(text)[0]
                        border(draw=draw, font=font, thiccness=1, text=role_name, fill=color_tuple,
                               outline=(0, 0, 0, 255), xy=(260 + size + text_length, 220))
                    else:
                        font = ImageFont.truetype('./assets/fonts/mono.ttf', 35)
                        text = f'{progress}/{total_xp}'
                        border(draw=draw, font=font, thiccness=1, text=text, fill=color,
                               outline=(0, 0, 0, 255), xy=(300, 220))
                        size = font.getsize(text)[0]
                        text = ' XP to Next Level'
                        font = ImageFont.truetype("./assets/fonts/ubuntu.ttf", 30)
                        border(draw=draw, font=font, thiccness=1, text=text, fill=(255, 255, 255, 255),
                               outline=(0, 0, 0, 255), xy=(300 + size, 220))

                    template.paste(circle, (15, 18), circle)

                    buffer = BytesIO()
                    template.save(buffer, 'png')
                    buffer.seek(0)
                    return buffer

            bf = await self.bot.loop.run_in_executor(None, process_image)
            total = time.time() - start
            await ctx.send(f'Total: `{round(total, 3)}s`\n{tip}', file=discord.File(fp=bf, filename='rank.png'))

    @_rank.command()
    async def color(self, ctx, *, new_color):
        """Changes the main color of your rank card (text, XP bar). Please provide a hex for best results.

        **Usage:** `$rank color <color>`
        """
        try:
            new_color = Color(new_color)
        except ValueError:
            return await ctx.send(f'Could not make a color out of `{new_color}`.')

        h = new_color.hex_l
        query = '''INSERT INTO xp (user_id, total_xp, image, color) 
                   VALUES ($1, $2, $3, $4)
                   ON CONFLICT (user_id)
                   DO UPDATE
                   SET image = $3
                '''
        await self.bot.db.execute(query, ctx.author.id, 0, self.zerotwo, 'c0ffee')

        image = Image.new(mode='RGB', color=h, size=(128, 128))
        buffer = BytesIO()
        await self.bot.loop.run_in_executor(None, image.save, buffer, 'png')
        buffer.seek(0)
        await ctx.send(f'Changed your rank color to this:',
                       file=discord.File(fp=buffer, filename='color.png'))

    @_rank.command(aliases=['bg', 'background'])
    async def image(self, ctx, image_url=None):
        """Changes the background image of your rank card.
        You may provide a URL **or** attach an image file.

        Your image will be darkened by 50% when displayed using the `$rank` command.
        If your image is too tall, it will be cropped from the top and bottom evenly.

        **Usage:** `$rank image <image URL>`"""
        if image_url is None:
            if ctx.message.attachments:
                attachment = None
                for a in ctx.message.attachments:
                    if any(a.url.endswith(x) for x in ('.png', '.jpg', '.jpeg')):
                        attachment = a
                        break
                if not attachment:
                    return await ctx.send('None of the files attached were images.')
            else:
                return await ctx.send('Please provide an image URL or attach an image.')
            b = await attachment.read()
        else:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(image_url) as resp:
                        if resp.status != 200:
                            return await ctx.send('Something went wrong (( - try a different link.')
                        b = await resp.read()
            except:
                return await ctx.send('The image URL you provided wasn\'t working ((')

        query = '''INSERT INTO xp (user_id, total_xp, image, color) 
                   VALUES ($1, $2, $3, $4)
                   ON CONFLICT (user_id)
                   DO UPDATE
                   SET image = $3
                '''
        await self.bot.db.execute(query, ctx.author.id, 0, b, 'c0ffee')
        file = discord.File(fp=BytesIO(b), filename='background.png')
        await ctx.send('Your rank card has been updated!', file=file)

    @commands.command()
    async def levels(self, ctx, page: int = 1):
        """Shows the XP leaderboard."""

        if page < 1:
            return await ctx.send('The page must be 1 or greater.')

        sql = 'SELECT user_id, total_xp FROM xp ORDER BY xp DESC'
        res = await self.bot.db.fetch(sql)

        rows = [res[i:i + 12] for i in range(0, len(res), 12)]
        pages = len(rows)

        try:
            rows = rows[page - 1]
        except IndexError:
            return await ctx.send(f'Only `{pages}` pages exist in the leaderboard now.')

        embed = discord.Embed(title=f'Leaderboard for {ctx.guild.name}', color=ctx.author.color)
        embed.set_author(name=f'Page {page}', icon_url=str(ctx.guild.icon_url_as(format='png')))
        embed.set_footer(text=f'Page {page}/{pages}')

        for row in rows:
            member, xp = ctx.guild.get_member(row['user_id']), row['total_xp']
            rank = res.index(row) + 1
            lvl, name = get_level(xp), f'#{rank}'

            if member is not None:
                value = f'{member.mention}\n**Level:** `{lvl}`\n**Total XP:** `{xp}`'
                embed.add_field(name=name, value=value)
            else:
                member_id = row['user_id']
                name = f'#{rank} (Member Left Server)'
                member = f'<@{member_id}>'
                value = f'{member}\n**Level:** `{lvl}`\n**Total XP:** `{xp}`'
                embed.add_field(name=name, value=value)

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Levels(bot))
