from discord.ext import commands, tasks
import discord
import asyncio
import chess
import chess.svg
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM
from io import BytesIO
from prettytable import PrettyTable
import re
from humanize import precisedelta


def fmtbrd(board: chess.Board, color):
    flip = True if color == 'black' else False
    colors = {
        'square dark': '#769656',
        'sqaure light': '#eeeed2',
        'arrow green': '#2a52be',
        'arrow blue': '#2a52be',
        'arrow red': '#2a52be',
        'arrow yellow': '#2a52be'
    }
    try:
        last = board.peek().uci()
        arrows = [chess.svg.Arrow(chess.parse_square(last[0:2]), chess.parse_square(last[2:4]))]
        f = BytesIO(bytes(chess.svg.board(board, flipped=flip, colors=colors, arrows=arrows), encoding='utf-8'))
    except IndexError:
        f = BytesIO(bytes(chess.svg.board(board, flipped=flip, colors=colors), encoding='utf-8'))
    f.seek(0)
    new_f = BytesIO()
    drawing = svg2rlg(f)
    renderPM.drawToFile(drawing, new_f)
    new_f.seek(0)
    return discord.File(fp=new_f, filename='board.png')


class Chess(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.in_game = []
        self.pattern = re.compile('^[A-Ha-h][1-8][A-Ha-h][1-8]$')

    @commands.command(name='chess')
    async def _chess(self, ctx, user: discord.Member, *, fen=None):
        """Starts a chess game with another player.
           You may start with a custom position by providing a FEN at the end of the command.

           Games take place in DMs and all moves are made with Standard Algebraic Notation.

           **Usage:** `$chess <opponent> [FEN]`
        """
        if fen:
            try:
                board = chess.Board(fen)
            except ValueError:
                return await ctx.send('The custom FEN position you provided wasn\'t valid.')
        else:
            board = chess.Board()

        if ctx.author in self.in_game or user in self.in_game:
            return await ctx.send('Either you or the user you challenged is already in a game.')
        m = await ctx.send(f'{user.mention}, press the check mark to accept the chess match.')
        emoji = ('\u2705', '\u274e')
        [await m.add_reaction(e) for e in emoji]

        def check(p):
            return p.user_id == user.id and p.message_id == m.id and str(p.emoji) in emoji

        try:
            payload = await self.bot.wait_for('raw_reaction_add', timeout=30, check=check)
        except asyncio.TimeoutError:
            [await m.remove_reaction(e, self.bot) for e in emoji]
            return await ctx.send('You took too long to accept/decline the match.')

        if str(payload.emoji) == emoji[1]:
            return await ctx.send(f'{user.mention} declined the match.')

        await ctx.send('How long does each player have for the entire match? Enter a number in minutes.')

        def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel and msg.content.isdigit()

        try:
            m = await self.bot.wait_for('message', timeout=60, check=check)
        except asyncio.TimeoutError:
            return await ctx.send("You took too long to say a time, I have timeout'd.")

        seconds = int(m.content) * 60
        
        wleft = seconds
        bleft = seconds
        self.in_game.append(ctx.author)
        self.in_game.append(user)

        white = ctx.author
        black = user

        moves = PrettyTable()
        resign = ctx.prefix.lower() + 'resign'
        timer = ctx.prefix.lower() + 'timer'
        moves.field_names = ['White', 'Black']

        await white.send('Your turn first.', file=fmtbrd(board, 'white'))
        await black.send('You are black. White moves first.', file=fmtbrd(board, 'black'))

        await ctx.send('Head to DMs! Your game will be taking place there.\n\n'
                       f'`{ctx.prefix}resign` to resign\n'
                       f'`{ctx.prefix}timer` to check how much time left')

        async def wait_for():

            def check2(msg):
                return msg.author in (white, black) and not msg.guild and \
                       (msg.content.lower() == timer or msg.content.lower() == resign)

            while True:
                check2_msg = await self.bot.wait_for('message', check=check2)
                if check2_msg.author == white:
                    other = black 
                    o_left = bleft
                    u_left = wleft
                else:
                    u_left = bleft
                    o_left = wleft
                if check2_msg.content.lower() == timer:
                    await check2_msg.author.send(f'Your time left: `{u_left}`\nYour opponent time left: `{o_left}`')
                else:
                    self.in_game.remove(white)
                    self.in_game.remove(black)
                    await check2_msg.author.send('**You lost - Resignation**')
                    await other.send('**You won - Resignation**')
                    return

        task = self.bot.loop.create_task(wait_for())
        userd = False 
        oppd = False

        async def task2():
            while True:
                if black not in self.in_game or white not in self.in_game:
                    return 
                await asyncio.sleep(1)

                wleft -= 1
                bleft -= 1
                if wleft <= 0:
                    await white.send('**You lost - timeout**')
                    await black.send('**You won - timeout**')
                    self.in_game.remove(white)
                    self.in_game.remove(black)
                    return 
                if bleft <= 0:
                    await white.send('**You lost - timeout**')
                    await black.send('**You won - timeout**')
                    self.in_game.remove(white)
                    self.in_game.remove(black)
                    return 

        while True:
            if ctx.author in self.in_game and user in self.in_game:

                if board.turn:
                    left = wleft
                    user, opp = white, black
                else:
                    left = bleft
                    user, opp = black, white

                userd = True
                oppd = False

                def check(msg):
                    return msg.author.id == user.id and not msg.guild

                while True:
                    try:
                        m = await self.bot.wait_for('message', check=check, timeout=left)
                    except asyncio.TimeoutError:
                        task.cancel()
                        self.in_game.pop(user)
                        self.in_game.pop(opp)
                        await user.send('**You lost - Timeout**')
                        await opp.send('**You won - Timeout**')
                        return

                    try:
                        board.push_san(m.content)
                        userd = False
                        break
                    except ValueError:
                        await user.send('Not a legal move.\n'
                                        '- Check'
                                        '- Pin'
                                        '- Uppercase all pieces and lowercase all squares\n'
                                        '- More than one of the same piece could move to the square')

                if board.is_stalemate():
                    self.in_game.remove(user)
                    self.in_game.remove(opp)
                    task.cancel()
                    await user.send('**Draw - Stalemate**')
                    await opp.send('**Draw - Stalemate**')
                    return
                if board.is_checkmate():
                    self.in_game.remove(user)
                    self.in_game.remove(opp)
                    task.cancel()
                    await user.send('**You won - Checkmate**')
                    await opp.send('**You lost - Checkmate**')
                    return
                if board.is_insufficient_material():
                    self.in_game.remove(user)
                    self.in_game.remove(opp)
                    task.cancel()
                    await user.send('**Draw - Insufficient Material**')
                    await opp.send('**Draw - Insufficient Material**')
                    return
                if board.is_repetition(3):
                    self.in_game.remove(user)
                    self.in_game.remove(opp)
                    task.cancel()
                    await user.send('**Draw - Threefold Repetition**')
                    await opp.send('**Draw - Threefold Repetition**')
                    return
                if board.turn:
                    w_content = 'Your opponent moved. Your turn now.'
                    b_content = 'You moved. Waiting on your opponent.'
                else:
                    w_content = 'You moved. Waiting on your opponent.'
                    b_content = 'Your opponent moved. Your turn now.'
                await white.send(w_content, file=fmtbrd(board, 'white'))
                await black.send(b_content, file=fmtbrd(board, 'black'))
            else:
                return

    @_chess.error
    async def chess_error(self, ctx, error):
        raise error


def setup(bot):
    bot.add_cog(Chess(bot))
