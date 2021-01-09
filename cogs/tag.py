from discord.ext import commands
from difflib import SequenceMatcher
import json
import discord


def is_similar(a, b):
    ratio = SequenceMatcher(None, a, b).ratio()
    if ratio > 0.69:
        return True
    else:
        return False


class Tag(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = self.bot.db
        self.names = []
        self.bot.loop.create_task(self.get_names())

    async def get_names(self):
        for row in await self.db.fetch('SELECT names FROM tags'):
            self.names += row['names']

    @commands.group(invoke_without_command=True)
    async def tag(self, ctx, *, name):
        """Sends a tag (shortcut to send a chunk of text) by its name.
           To make a tag, see `$help tag add`

           **Usage:** `$tag <name>`
        """
        name = name.lower()
        if name not in self.names:
            similar = [f'`  $tag {n}`' for n in self.names if is_similar(name, n)]
            if not similar:
                await ctx.send(f'The tag `{name}` wasn\'t found; no suggestions.')
            else:
                similar = '\n'.join(similar)
                await ctx.send(f'The tag `{name}` wasn\'t found; you might have wanted:\n\n'
                               f'{similar}')
            return

        query = 'SELECT id, text FROM tags WHERE $1 = ANY(names)'
        res = await self.db.fetchrow(query, name)
        text = res['text']
        if text.lower().startswith('embed: '):
            text = text.lstrip('embed: ')
            try:
                embed = discord.Embed.from_dict(json.loads(text))
            except json.JSONDecodeError as error:
                return await ctx.send(f'An error occured while parsing the JSON: ```{error}```')
            await ctx.send(embed=embed)
        else:
            await ctx.send(text)

        query = 'UPDATE tags SET uses = uses + 1 WHERE "id" = $1'
        await self.db.execute(query, res['id'])

    @tag.command(aliases=['create'])
    async def add(self, ctx, name, *, text):
        """Adds a tag to the server.
           A tag can send an embed if you start the response text with `embed: ` and provide a JSON.

           **Usage:** `$tag add "<name>" <response text>`
        """
        name = name.lower()
        if name in self.names:
            return await ctx.send(f'A tag name/alias called `{name}` already exists here. '
                                  f'Tags are case insensitive.')
        if len(name) > 64:
            return await ctx.send(f'The tag name must be 64 characters or under.')

        query = 'INSERT INTO tags (names, text, user_id, uses) VALUES (ARRAY[$1], $2, $3, 0)'
        await self.db.execute(query, name, text, ctx.author.id)
        self.names.append(name)

        await ctx.send(f'Your tag `{name}` has been created ))')

    @tag.command()
    async def alias(self, ctx, alias, *, name):
        """Adds another name for an existing tag.
           You must own the original tag or have admin to create an alias for it.

           **Usage:** `$tag alias "<alias>" <existing name>`
        """
        alias = alias.lower()
        name = name.lower()

        if alias in self.names:
            return await ctx.send(f'A tag name/alias called `{alias}` already exists here. '
                                  f'Tags are case insensitive.')
        if name not in self.names:
            return await ctx.send(f'A tag with name/alias `{name}` doesn\'t already exist. '
                                  f'To make a new tag, try `{ctx.prefix}tag add`.')

        query = 'SELECT user_id, id FROM tags WHERE $1 = ANY(names)'
        res = await self.db.fetchrow(query, name)

        if res['user_id'] != ctx.author.id and not ctx.author.guild_permissions.administrator:
            return await ctx.send('You must *own the tag* or *have admin* to add aliases to it.')

        query = 'UPDATE tags SET names = array_append(names, $1) WHERE "id" = $2'
        await self.db.execute(query, alias, res['id'])
        self.names.append(alias)

        await ctx.send(f'The alias `{alias}` has been added to your tag ))')

    @tag.command(aliases=['remove'])
    async def delete(self, ctx, *, name):
        """Deletes a tag.
           You must own the original tag or have admin to delete it.

           **Usage:** `$tag delete <name>`
        """
        name = name.lower()
        if name not in self.names:
            return await ctx.send(f'A tag with name/alias `{name}` doesn\'t exist here.')
        query = 'SELECT id, user_id, names FROM tags WHERE $1 = ANY(names)'

        res = await self.db.fetchrow(query, name)
        if res['user_id'] != ctx.author.id and not ctx.author.guild_permissions.administrator:
            return await ctx.send(f'You must *own the tag* or *have admin* to delete it.')

        await ctx.send(f'Would you like to:\n\n'
                       f'`1.` Delete this tag completely\n'
                       f'`2.` Delete only this name/alias.')

        def check(m):
            return m.channel == ctx.channel and m.author == ctx.author and m.content in ('1', '2')

        msg = await self.bot.wait_for('message', check=check)

        if msg.content == '1':
            query = 'DELETE FROM tags WHERE "id" = $1'
            await self.db.execute(query, res['id'])

            for name in res['names']:
                self.names.remove(name)
            await ctx.send(f'Your tag `{name}` and all aliases have been removed.')
        else:
            query = 'UPDATE tags SET names = array_remove(names, $1) WHERE "id" = $2'
            await self.db.execute(query, name, res['id'])

            self.names.remove(name)
            await ctx.send(f'The alias `{name}` on your tag has been removed.')

    @tag.command()
    async def info(self, ctx, *, name):
        """Gets info for a certain tag (creator, # of uses, rank)

           **Usage:** `$tag info <name>`
        """
        name = name.lower()

        if name not in self.names:
            return await ctx.send(f'A tag with name/alias `{name}` was not found.')

        query = 'SELECT names, text, user_id, uses, RANK () OVER (ORDER BY uses) "rank" ' \
                'FROM tags WHERE $1 = ANY(names)'
        res = await self.db.fetchrow(query, name)

        creator = self.bot.slounge.get_member(res['user_id'])
        res['names'].pop(0)

        embed = discord.Embed(
            title=f'$tag {name}',
            description=res['text'],
            color=creator.color
        ).add_field(
            name='Creator', value=creator.mention, inline=False
        ).add_field(
            name='Uses', value=f'`{res["uses"]}`', inline=False
        ).add_field(
            name='Rank', value=f'**#{res["rank"]}**', inline=False
        ).add_field(
            name='Aliases', value=', '.join(f'`{name}`' for name in res['names']), inline=False
        ).set_author(
            name=f'Tag by {creator}',
            icon_url=str(creator.avatar_url_as(format='gif' if creator.is_avatar_animated() else 'png'))
        )
        await ctx.send(embed=embed)

    @tag.command(aliases=['list'])
    async def all(self, ctx, user: discord.Member, page: int = 1):
        """Lists all the tags (ordered by usage). You can provide a user to only show tags for that user. If there
        are too many tags to show at once, multiple pages will be created and you can provide a page to go to.

           **Usage:** `$tag all [user] [page]`
        """
        if not user:
            res = await self.db.fetch('SELECT uses, names FROM tags ORDER BY uses DESC')
        else:
            query = 'SELECT uses, names FROM tags WHERE user_id = $1 ORDER BY uses DESC'
            res = await self.db.fetch(query, user.id)
        pag = commands.Paginator(prefix='', suffix='', max_size=420)

        i = 1
        for row in res:
            pag.add_line(f'**{i}.** `{row["names"][0]}` ({row["uses"]} uses)')
            i += 1
        pages = []
        i = 1
        for page in pag.pages:
            embed = discord.Embed(
                title=f'Tags - Page {i}/{len(pag.pages)}',
                description=page,
                color=ctx.author.color
            )
            pages.append(embed)
            i += 1
        try:
            page = pages[page - 1]
        except IndexError:
            return await ctx.send('That page doesn\'t exist ((')
        await ctx.send(embed=page)


def setup(bot):
    bot.add_cog(Tag(bot))
