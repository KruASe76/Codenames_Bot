import discord
from discord.ext import commands
import os, json, sqlite3, random, time, re, inspect, pprint
import generation as gen

# Setting defaults
game_logo_link = 'https://cdn.discordapp.com/attachments/797224818763104317/845081822329176114/codenames_logo.jpg'
game_logo_path = os.path.join(os.getcwd(), 'images', 'codenames_logo.jpg')

ENTER = '\n'
ALPHABET = 'ABCDEFGHIJKLMNOPQSTUVWXYZ' # Without letter R
REACTION_ALPHABET = '🇦🇧🇨🇩🇪🇫🇬🇭🇮🇯🇰🇱🇲🇳🇴🇵🇶🇸🇹🇺🇻🇼🇽🇾🇿' # Without R too

# Getting the settings and the database
with open(os.path.join(os.getcwd(), 'settings.json'), 'r') as settings_file:
    settings = json.load(settings_file)

base = sqlite3.connect(os.path.join(os.getcwd(), 'base.db'))
cursor = base.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS guilds (id int primary key, prefix text, players text, team1 text, team2 text, dark null)')
cursor.execute('CREATE TABLE IF NOT EXISTS players (id int primary key, games int, games_cap int, wins int, wins_cap int)')

# cursor.execute('INSERT INTO guilds VALUES (?,?,?,?,?,?)', (795556636748021770, '-', '', '', '', False))

# Creating bot
def get_prefix(bot, message):
    if message.guild:
        cursor.execute('SELECT prefix FROM guilds WHERE id=?', [(message.guild.id)])
        return cursor.fetchone()[0]
    else:
        return '!'

bot = commands.Bot(command_prefix = get_prefix, help_command = None, owner_id = 689766059712315414)

# Checks
is_chief = commands.check(lambda ctx: ctx.message.author.id == bot.owner_id)

# Events
@bot.event
async def on_ready():
    await bot.change_presence(activity = discord.Activity(type=discord.ActivityType.watching, name='codenames.me'))

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        pass
    elif isinstance(error, commands.CheckFailure):
        await ctx.reply(embed = discord.Embed(
            title = ':no_entry_sign: Forbidden',
            colour = discord.Colour(int('8d08d2', 16))
        ))
    else:
        raise error

@bot.event
async def on_guild_join(guild):
    cursor.execute('INSERT INTO guilds VALUES (?,?,?,?,?,?)', (guild.id, 'cdn ', '', '', '', False))

# Help
@bot.command()
async def help(ctx, command=''):
    prefix = bot.command_prefix(bot, ctx.message)

    if command:
        comm = bot.get_command(command)
        if not comm:
            title = 'Error'
            desc = 'Command not found'
        else:
            title = comm.cog_name[:-1]

            comm_info = inspect.getfullargspec(comm._callback)
            arg_list = comm_info.args[2:]
            default_args = list(comm_info.defaults) if comm_info.defaults else []
            names = [comm.name] + [alias for alias in comm.aliases]
            name = '{' + '|'.join(names) + '}'
            args = []
            while len(arg_list) > len(default_args):
                args.append(f'<{arg_list[0]}>')
                arg_list.pop(0)
            for ind, arg in enumerate(arg_list):
                if arg == 'is_final':
                    continue
                args.append(f'[{arg}={default_args[ind]}]')
            desc = f"**`{prefix}{name}{' ' if args else ''}{' '.join(args)}`**{ENTER*2 + comm.help if comm.help else ''}"

        help_embed = discord.Embed(
            title = title,
            description = desc,
            colour = discord.Colour(int('8d08d2', 16))
        )

    else:
        help_embed = discord.Embed(
            title = 'Command list',
            colour = discord.Colour(int('8d08d2', 16))
        )
        help_embed.set_thumbnail(url = game_logo_link)

        for cog_name, cog in dict(bot.cogs).items():
            cog_comms = []
            for comm in cog.get_commands():
                brief = comm.brief if comm.brief else comm.help
                cog_comms.append(f"**`{prefix}{comm.name}`**{' - ' + brief if brief else ''}")
            help_embed.add_field(name=cog_name, value='\n'.join(cog_comms), inline=False)
        
        help_embed.add_field(
            name = '⁣',
            value = f'To learn a more detailed description of the command, type\n**`{prefix}help [command]`**',
            inline = False
        )

    await ctx.reply(embed = help_embed)

# Cogs
class GameCommands(commands.Cog, name = 'Game Commands'):
    '''They are used to play (wow, so unpredictable)'''
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.command(aliases=['register', 'reg', 'r'], brief='Registrates the user for the game',
        help="Registrates the user for the game.\nIf you won't enter the team number it will be selected randomly."
    )
    async def ready(self, ctx, team_number:int = 0):
        cursor.execute('SELECT players, team1, team2 FROM guilds WHERE id=?', [(ctx.guild.id)])
        players, team1, team2 = map(lambda s: list(map(int, s.split())), cursor.fetchone())
        players = [await self.bot.fetch_user(id) for id in players]
        team1 = [await self.bot.fetch_user(id) for id in team1]
        team2 = [await self.bot.fetch_user(id) for id in team2]

        if ctx.author not in players and ctx.author not in team1 and ctx.author not in team2:
            if not team_number:
                players.append(ctx.author)
            elif team_number == 1:
                team1.append(ctx.author)
            elif team_number == 2:
                team2.append(ctx.author)
            else:
                await ctx.reply(embed = discord.Embed(
                    title = 'Invalid team number',
                    description = "There are only 2 teams in the game.\nSelect one of them or don't type the number to shuffle randomly",
                    colour = discord.Colour(int('8d08d2', 16))
                ))
            cursor.execute('SELECT id FROM players')
            if ctx.author.id not in [tup[0] for tup in cursor.fetchall()]:
                cursor.execute('INSERT INTO players VALUES (?,?,?,?)', (ctx.author.id, 0, 0, 0, 0))
            
            await ctx.message.add_reaction('✅')
        else:
            await ctx.reply(embed = discord.Embed(
                title = "You're already in player list",
                description = 'Do you want to quit the game? (y/n)',
                colour = discord.Colour(int('8d08d2', 16))
            ))

            reply = await self.bot.wait_for('message', check=lambda msg: msg.content.lower() in ['y', 'n'] and msg.author == ctx.author and msg.channel == ctx.channel)
            if reply.content.lower() == 'y':
                if reply.author in players:
                    players.remove(reply.author)
                elif reply.author in team1:
                    team1.remove(reply.author)
                elif reply.author in team2:
                    team2.remove(reply.author)
                await reply.add_reaction('✅')
            else:
                await reply.add_reaction('🆗')
        
        players_id = [str(p.id) for p in players]
        team1_id = [str(p.id) for p in team1]
        team2_id = [str(p.id) for p in team2]
        cursor.execute(
            'UPDATE guilds SET players=?, team1=?, team2=? WHERE id=?',
            (' '.join(players_id), ' '.join(team1_id), ' '.join(team2_id), ctx.guild.id)
        )
    
    @commands.command(name='players', aliases=['ps'], help='Shows registrated players')
    async def show_players(self, ctx, is_final=False):
        async with ctx.typing():
            cursor.execute('SELECT players, team1, team2 FROM guilds WHERE id=?', [(ctx.guild.id)])
            players, team1, team2 = map(lambda s: list(map(int, s.split())), cursor.fetchone())
            players = [await self.bot.fetch_user(id) for id in players]
            team1 = [await self.bot.fetch_user(id) for id in team1]
            team2 = [await self.bot.fetch_user(id) for id in team2]

            players_embed = discord.Embed(title='Final player list' if is_final else 'Player_list', colour=discord.Colour(int('8d08d2', 16)))
            if team1:
                players_embed.add_field(name='Team 1', value='\n'.join([p.mention for p in team1]))
            if players:
                players_embed.add_field(name='No Team', value='\n'.join([p.mention for p in players]))
            if team2:
                players_embed.add_field(name='Team 2', value='\n'.join([p.mention for p in team2]))

            if players or team1 or team2:
                await ctx.reply(embed = players_embed)
            else:
                await ctx.reply(embed = discord.Embed(
                    title = 'Player_list',
                    description = 'Nobody is ready to play :no_good:',
                    colour = discord.Colour(int('8d08d2', 16))
                ))

    @commands.command(aliases=['s'], brief='Starts the game',
        help='Starts the game.\nIf there are players without a team they will be evenly distributed among the teams.'
    )
    async def start(self, ctx):
        async with ctx.typing():
            cursor.execute('SELECT players, team1, team2 FROM guilds WHERE id=?', [(ctx.guild.id)])
            players, team1, team2 = map(lambda s: list(map(int, s.split())), cursor.fetchone())
            players = [await self.bot.fetch_user(id) for id in players]
            team1 = [await self.bot.fetch_user(id) for id in team1]
            team2 = [await self.bot.fetch_user(id) for id in team2]

            # Dividing players into two teams randomly
            if players:
                random.shuffle(players)
                for member in players:
                    if len(team1) <= len(team2):
                        team1.append(member)
                    else:
                        team2.append(member)
                    players.remove(member)
            
            if len(team1) < 2 or len(team2) < 2:
                await ctx.reply(embed = discord.Embed(
                    title = 'Error',
                    description = 'There are not enough players.\nIt has to be at least 2 players in each team.',
                    colour = discord.Colour(int('8d08d2', 16))
                ))
                return
            
            if len(team1) > 25 or len(team2) > 25:
                await ctx.reply(embed = discord.Embed(
                    title = 'Error',
                    description = 'There are too much players.\nIt has **not** to be more than 25 players in each team.',
                    colour = discord.Colour(int('8d08d2', 16))
                ))
                return
            
            players_id = [str(p.id) for p in players]
            team1_id = [str(p.id) for p in team1]
            team2_id = [str(p.id) for p in team2]
            cursor.execute(
                'UPDATE guilds SET players=?, team1=?, team2=? WHERE id=?',
                (' '.join(players_id), ' '.join(team1_id), ' '.join(team2_id), ctx.guild.id)
            )
            
            final_show = self.bot.get_command('players')
            await final_show.__call__(ctx, is_final=True)
        time.sleep(2)

        choosing_dict = {
            'en': {
                'std':      'Original English dictionary (400 words)',
                'duet':     'Original Duet dictionary (400 words)',
                'deep':     'Original Deep Undercover dictionary (18+, 390 words)',
                'denull':   "deNULL's dictionary (763 words)",
                'denull18': "deNULL's dictionary (18+, 1081 words)",
                'all':      'All English dictionaries (18+, 1139 words)',
                'esp':      'Esperanto'
            },
            'ru': {
                'std':      'Стандартный словарь из локализации GaGa Games (400 слов)',
                'deep':     'Словарь версии Deep Undercover, GaGa Games (18+, 390 слов)',
                'pard':     'Словарь от Pard (302 слова)',
                'vpupkin':  'Словарь от vpupkin (396 слов, много топонимов)',
                'zav':      'Словарь от Ивана Заворина (2272 частых слов)',
                'denull':   'Словарь от deNULL (636 слов, немного топонимса)',
                'denull18': 'Словарь от deNULL (18+, 1014 слов)',
                'all':      'Все словари вместе (1058 слов)',
                'esp':      'Esperanto'
            }
        }

        await ctx.send(embed = discord.Embed(
            title = 'Select language',
            description = '**en** - English\n**ru** - Russian\n\nType answer in the following message',
            colour = discord.Colour(int('8d08d2', 16))
        ))
        language = await self.bot.wait_for('message', check=lambda msg: msg.content.lower() in list(choosing_dict.keys()) and msg.channel == ctx.channel)
        language = language.content.lower()

        choose_dict_msg = [f'**{key}** - {val}' for key, val in choosing_dict[language].items()]
        await ctx.send(embed = discord.Embed(
            title = 'Select dictionary',
            description = '\n'.join(choose_dict_msg) + '\n\nType answer in the following message',
            colour = discord.Colour(int('8d08d2', 16))
        ))
        game_dict_name = await self.bot.wait_for('message', check=lambda msg: msg.content.lower() in list(choosing_dict[language].keys()) and msg.channel == ctx.channel)
        game_dict_name = game_dict_name.content.lower()


        cap_choosing_list = [f'**{ALPHABET[ind]}** - {player.mention}' for ind, player in enumerate(team1)]
        await ctx.send(embed = discord.Embed(
            title = 'RED team: Captain selecting',
            description = '**R** - Random captain\n\n' + '\n'.join(cap_choosing_list) + '\n\nYou have 10 seconds to react',
            colour = discord.Colour(int('ff6450', 16))
        ))
        async for msg in ctx.channel.history():
            if msg.author == bot.user:
                break
        await msg.add_reaction('🇷')
        for ind, player in enumerate(team1):
            await msg.add_reaction(REACTION_ALPHABET[ind])
        
        time.sleep(10)
        async for msg in ctx.channel.history(): # Have to get the message object again with reactions in it
            if msg.author == bot.user:
                break
        reactions = msg.reactions
        reactions.sort(key = lambda r: r.count, reverse = True)
        for reaction in reactions: # getting max_count with checking if it is a required emoji
            if reaction.me:
                max_count = reaction.count
                break
        winner_reactions = []
        for reaction in reactions:
            if reaction.count < max_count:
                break
            if reaction.me: # not appending outsider emojies
                winner_reactions.append(reaction.emoji)
        
        if '🇷' in winner_reactions:
            team1_cap = random.choice(team1)
        else:
            potential_caps = []
            for emoji in winner_reactions:
                ind = REACTION_ALPHABET.index(emoji)
                potential_caps.append(team1[ind])
            team1_cap = random.choice(potential_caps)
        team1_pl = team1.copy()
        team1_pl.remove(team1_cap)

        await ctx.send(embed = discord.Embed(
            title = 'RED team: Captain selected',
            description = f'Your captain is {team1_cap.mention}!',
            colour = discord.Colour(int('ff6450', 16))
        ))

        # The same code for team2_cap
        cap_choosing_list = [f'**{ALPHABET[ind]}** - {player.mention}' for ind, player in enumerate(team2)]
        await ctx.send(embed = discord.Embed(
            title = 'BLUE team: Captain selecting',
            description = '**R** - Random captain\n\n' + '\n'.join(cap_choosing_list) + '\n\nYou have 10 seconds to react',
            colour = discord.Colour(int('50bbff', 16))
        ))
        async for msg in ctx.channel.history():
            if msg.author == bot.user:
                break
        await msg.add_reaction('🇷')
        for ind, player in enumerate(team2):
            await msg.add_reaction(REACTION_ALPHABET[ind])
        
        time.sleep(10)
        async for msg in ctx.channel.history(): # Have to get the message object again with reactions in it
            if msg.author == bot.user:
                break
        reactions = msg.reactions
        reactions.sort(key = lambda r: r.count, reverse = True)
        for reaction in reactions: # getting max_count and removing outsider reactions with the same or more count than max_count
            if reaction.me:
                max_count = reaction.count
                break
            else:
                reactions.remove(reaction)
        winner_reactions = []
        for reaction in reactions:
            if reaction.count < max_count:
                break
            winner_reactions.append(reaction.emoji)
        
        if '🇷' in winner_reactions:
            team2_cap = random.choice(team2)
        else:
            potential_caps = []
            for emoji in winner_reactions:
                ind = REACTION_ALPHABET.index(emoji)
                potential_caps.append(team2[ind])
            team2_cap = random.choice(potential_caps)
        team2_pl = team2.copy()
        team2_pl.remove(team2_cap)

        await ctx.send(embed = discord.Embed(
            title = 'BLUE team: Captain selected',
            description = f'Your captain is {team2_cap.mention}!',
            colour = discord.Colour(int('50bbff', 16))
        ))


        await ctx.send(embed = discord.Embed(
            title = 'GAME STARTED!',
            colour = discord.Colour(int('8d08d2', 16))
        ))
        
        # notifying everyone in direct messages
        await team1_cap.send(embed = discord.Embed(
            title = 'Game started',
            description = "**You're the captain of the RED team**\n\nYour teammates are:\n" + '\n'.join([p.mention for p in team1_pl]),
            colour = discord.Colour(int('ff6450', 16))
        ))
        for player in team1_pl:
            team1_pl_without = team1_pl.copy() # Team1 player list without recipient of the message
            team1_pl_without.remove(player)
            player.send(embed = discord.Embed(
                title = 'Game started',
                description = f"**You're the member of the RED team**\n\nThe captain of your team is {team1_cap.mention}\nYour teammates are:\n" + '\n'.join([p.mention for p in team1_pl_without]),
                colour = discord.Colour(int('ff6450', 16))
            ))
        
        await team2_cap.send(embed = discord.Embed(
            title = 'Game started',
            description = "**You're the captain of the BLUE team**\n\nYour teammates are:\n" + '\n'.join([p.mention for p in team2_pl]),
            colour = discord.Colour(int('50bbff', 16))
        ))
        for player in team2_pl:
            team2_pl_without = team2_pl.copy() # Team2 player list without recipient of the message
            team2_pl_without.remove(player)
            player.send(embed = discord.Embed(
                title = 'Game started',
                description = f"**You're the member of the BLUE team**\n\nThe captain of your team is {team2_cap.mention}\nYour teammates are:\n" + '\n'.join([p.mention for p in team2_pl_without]),
                colour = discord.Colour(int('50bbff', 16))
            ))

        uhd = gen.UltraHD()
        cursor.execute('SELECT dark FROM guilds WHERE id=?', [(ctx.guild.id)])
        col = gen.Colors(cursor.fetchone()[0])

        team1_words, team2_words, endgame_word, other_words, opened_words = gen.words(
            lang=language, dict_name=game_dict_name
        )
        available_words = list(set(team1_words + team2_words + [endgame_word] + other_words) - set(opened_words)) # endgame_word is a single word

        if len(team1_words) > len(team2_words):
            first_move_color = 'RED'
            first_move_cap = team1_cap
            first_move_pl = team1_pl
            first_move_words = team1_words
            second_move_color = 'BLUE'
            second_move_cap = team2_cap
            second_move_pl = team2_pl
            second_move_words = team2_words
        else:
            first_move_color = 'BLUE'
            first_move_cap = team2_cap
            first_move_pl = team2_pl
            first_move_words = team2_words
            second_move_color = 'RED'
            second_move_cap = team1_cap
            second_move_pl = team1_pl
            second_move_words = team1_words

        game = True
        while game: # Mainloop
            gen.field(uhd, col, team1_words, team2_words, endgame_word, other_words, opened_words)
            cap_field = discord.File(open(os.path.join('images', 'cap_field.png'), 'rb'))
            pl_field = discord.File(open(os.path.join('images', 'pl_field.png'), 'rb'))
            
            await ctx.send(file = pl_field)
            await ctx.send(embed = discord.Embed(
                title = 'Waiting for move',
                description = f'Captain of **{first_move_color}** team',
                colour = discord.Colour(int('ff6450' if first_move_color=='RED' else '50bbff', 16))
            ))

            await first_move_cap.send(file = cap_field)
            await second_move_cap.send(file = cap_field)
            await first_move_cap.send(embed = discord.Embed(
                title = 'This is your move turn',
                description = f"Type a word and a number like {'**`cow 3`**' if language=='en' else '**`корова 3`**'} in the following message",
                colour = discord.Colour(int('ff6450' if first_move_color=='RED' else '50bbff', 16))
            ))
            move_msg = await self.bot.wait_for('message', check=lambda msg: re.fullmatch(r'.+ \d+', msg.content) and not msg.content.endswith(' 0') != ' 0' and msg.channel == first_move_cap.dm_channel)
            move = move_msg.content
            word_count = int(move.split()[1])
            await first_move_cap.send(embed = discord.Embed(
                title = 'Move accepted',
                colour = discord.Colour(int('ff6450' if first_move_color=='RED' else '50bbff', 16))
            ))
            await ctx.send(embed = discord.Embed(
                title = f'Captain of **{first_move_color}** team moved',
                description = f'The move contains:\n**`{move}`**',
                colour = discord.Colour(int('ff6450' if first_move_color=='RED' else '50bbff', 16))
            ))

            await ctx.send(embed = discord.Embed(
                title = 'Waiting for move',
                description = f'Players of **{first_move_color}** team\n\n Type words you want to open in the following messages. If you want to break the move type **`0`**',
                colour = discord.Colour(int('ff6450' if first_move_color=='RED' else '50bbff', 16))
            ))
            while word_count >= 0: # >= because of the rule that players can open one more word than their captain said
                move_msg = await self.bot.wait_for('message', check=lambda msg: (msg.content.lower() in available_words or msg.content == '0') and msg.channel == ctx.channel and msg.author in first_move_pl)
                move = move_msg.content.lower()
                if move == '0':
                    move_msg.add_reaction('🆗')
                    break
                
                opened_words.append(move)
                available_words.remove(move)
                gen.field(uhd, col, team1_words, team2_words, endgame_word, other_words, opened_words)
                cap_field = discord.File(open(os.path.join('images', 'cap_field.png'), 'rb'))
                pl_field = discord.File(open(os.path.join('images', 'pl_field.png'), 'rb'))

                if move in other_words:
                    await move_msg.reply(embed = discord.Embed(
                        title = 'Miss',
                        description = "Unfortunately, this word **doesn't belong to any team**",
                        colour = discord.Colour(int('ffffff', 16))
                    ))
                    await first_move_cap.send(embed = discord.Embed(
                        title = 'Miss',
                        description = f"Your team opened the word **`{move}`** that **doesn't belong to any team**",
                        colour = discord.Colour(int('ffffff', 16))
                    ))
                    await second_move_cap.send(embed = discord.Embed(
                        title = 'Lucky!',
                        description = f"The opponent team opened the word **`{move}`** that **doesn't belong to any team**",
                        colour = discord.Colour(int('ffffff', 16))
                    ))
                elif move in second_move_words:
                    await move_msg.reply(embed = discord.Embed(
                        title = 'Miss',
                        description = "Unfortunately, this word **belongs to the opponent team**",
                        colour = discord.Colour(int('ff6450' if second_move_color=='RED' else '50bbff', 16))
                    ))
                    await first_move_cap.send(embed = discord.Embed(
                        title = 'Miss',
                        description = f"Your team opened the word **`{move}`** that **belongs to the opponent team**",
                        colour = discord.Colour(int('ff6450' if second_move_color=='RED' else '50bbff', 16))
                    ))
                    await second_move_cap.send(embed = discord.Embed(
                        title = 'Lucky!',
                        description = f"The opponent team opened the word **`{move}`** that **belongs to your team**",
                        colour = discord.Colour(int('ff6450' if second_move_color=='RED' else '50bbff', 16))
                    ))
                    await ctx.send(file = pl_field)
                    await first_move_cap.send(file = cap_field)
                    await second_move_cap.send(file = cap_field)
                    break
                elif move == endgame_word:
                    await move_msg.reply(embed = discord.Embed(
                        title = 'Miss',
                        description = "Unfortunately, this word **is an endgame one**",
                        colour = discord.Colour(int('444444', 16))
                    ))
                    await first_move_cap.send(embed = discord.Embed(
                        title = 'Miss',
                        description = f"Your team opened the word **`{move}`** that **is an endgame one**",
                        colour = discord.Colour(int('444444', 16))
                    ))
                    await second_move_cap.send(embed = discord.Embed(
                        title = 'Lucky!',
                        description = f"The opponent team opened the word **`{move}`** that **is an endgame one**",
                        colour = discord.Colour(int('444444', 16))
                    ))
                    await ctx.send(file = pl_field)
                    await first_move_cap.send(file = cap_field)
                    await second_move_cap.send(file = cap_field)
                    await ctx.send(embed = discord.Embed(
                        title = 'Game over!',
                        description = f'**{second_move_color} team won!**\n{first_move_color} team opened an endgame word.',
                        colour = discord.Colour(int('ff6450' if second_move_color=='RED' else '50bbff', 16))
                    ))
                    await first_move_cap.send(embed = discord.Embed(
                        title = 'Your team lost!',
                        description = 'Better luck in the next game!',
                        colour = discord.Colour(int('ff6450' if second_move_color=='RED' else '50bbff', 16))
                    ))
                    cursor.execute('SELECT games, games_cap FROM players WHERE id=?', first_move_cap.id)
                    cursor.execute(
                        'UPDATE players SET games=?, games_cap=? WHERE id=?',
                        (cursor.fetchone()[0]+1, cursor.fetchone()[1]+1, first_move_cap.id)
                    )
                    for player in first_move_pl:
                        await player.send(embed = discord.Embed(
                            title = 'Your team lost!',
                            description = 'Better luck in the next game!',
                            colour = discord.Colour(int('ff6450' if second_move_color=='RED' else '50bbff', 16))
                        ))
                        cursor.execute('SELECT games FROM players WHERE id=?', player.id)
                        cursor.execute('UPDATE players SET games=? WHERE id=?', (cursor.fetchone()[0]+1, player.id))
                    await second_move_cap.send(embed = discord.Embed(
                        title = 'Your team won!',
                        description = 'Keep it up!',
                        colour = discord.Colour(int('ff6450' if second_move_color=='RED' else '50bbff', 16))
                    ))
                    cursor.execute('SELECT games, games_cap, wins, wins_cap FROM players WHERE id=?', second_move_cap.id)
                    cursor.execute(
                        'UPDATE players SET games=?, games_cap=?, wins=?, wins_cap=? WHERE id=?',
                        (cursor.fetchone()[0]+1, cursor.fetchone()[1]+1, cursor.fetchone()[2]+1, cursor.fetchone()[3]+1, second_move_cap.id)
                    )
                    for player in second_move_pl:
                        await player.send(embed = discord.Embed(
                            title = 'Your team won!',
                            description = 'Keep it up!',
                            colour = discord.Colour(int('ff6450' if second_move_color=='RED' else '50bbff', 16))
                        ))
                        cursor.execute('SELECT games, games_cap, wins FROM players WHERE id=?', player.id)
                        cursor.execute(
                            'UPDATE players SET games=?, games_cap=?, wins=? WHERE id=?',
                            (cursor.fetchone()[0]+1, cursor.fetchone()[1]+1, cursor.fetchone()[2]+1, player.id)
                        )

                    game = False
                    break
                else:
                    await move_msg.reply(embed = discord.Embed(
                        title = 'Success',
                        description = "You guessed!",
                        colour = discord.Colour(int('ff6450' if first_move_color=='RED' else '50bbff', 16))
                    ))
                    await first_move_cap.send(embed = discord.Embed(
                        title = 'Success',
                        description = f"Your team guessed the word **`{move}`** that **belongs to your team**!",
                        colour = discord.Colour(int('ff6450' if first_move_color=='RED' else '50bbff', 16))
                    ))
                    await second_move_cap.send(embed = discord.Embed(
                        title = 'Opponent success',
                        description = f"The opponent team guessed the word **`{move}`** that **belongs to opponent's team**",
                        colour = discord.Colour(int('ff6450' if first_move_color=='RED' else '50bbff', 16))
                    ))
                await ctx.send(file = pl_field)
                await first_move_cap.send(file = cap_field)
                await second_move_cap.send(file = cap_field)
            
            if not game: # checking if the game is over if it is so after first team move
                break
            
            gen.field(uhd, col, team1_words, team2_words, endgame_word, other_words, opened_words)
            cap_field = discord.File(open(os.path.join('images', 'cap_field.png'), 'rb'))
            pl_field = discord.File(open(os.path.join('images', 'pl_field.png'), 'rb'))
            
            await ctx.send(file = pl_field)
            await ctx.send(embed = discord.Embed(
                title = 'Waiting for move',
                description = f'Captain of **{second_move_color}** team',
                colour = discord.Colour(int('ff6450' if second_move_color=='RED' else '50bbff', 16))
            ))

            await first_move_cap.send(file = cap_field)
            await second_move_cap.send(file = cap_field)
            await second_move_cap.send(embed = discord.Embed(
                title = 'This is your move turn',
                description = f"Type a word and a number like {'**`cow 3`**' if language=='en' else '**`корова 3`**'} in the following message",
                colour = discord.Colour(int('ff6450' if second_move_color=='RED' else '50bbff', 16))
            ))
            move_msg = await self.bot.wait_for('message', check=lambda msg: re.fullmatch(r'.+ \d+', msg.content) and not msg.content.endswith(' 0') != ' 0' and msg.channel == second_move_cap.dm_channel)
            move = move_msg.content
            word_count = int(move.split()[1])
            await second_move_cap.send(embed = discord.Embed(
                title = 'Move accepted',
                colour = discord.Colour(int('ff6450' if second_move_color=='RED' else '50bbff', 16))
            ))
            await ctx.send(embed = discord.Embed(
                title = f'Captain of **{second_move_color}** team moved',
                description = f'The move contains:\n**`{move}`**',
                colour = discord.Colour(int('ff6450' if second_move_color=='RED' else '50bbff', 16))
            ))

            await ctx.send(embed = discord.Embed(
                title = 'Waiting for move',
                description = f'Players of **{second_move_color}** team\n\n Type words you want to open in the following messages. If you want to break the move type **`0`**',
                colour = discord.Colour(int('ff6450' if second_move_color=='RED' else '50bbff', 16))
            ))
            while word_count >= 0: # >= because of the rule that players can open one more word than their captain said
                move_msg = await self.bot.wait_for('message', check=lambda msg: (msg.content.lower() in available_words or msg.content == '0') and msg.channel == ctx.channel and msg.author in second_move_pl)
                move = move_msg.content.lower()
                if move == '0':
                    move_msg.add_reaction('🆗')
                    break
                
                opened_words.append(move)
                available_words.remove(move)
                gen.field(uhd, col, team1_words, team2_words, endgame_word, other_words, opened_words)
                cap_field = discord.File(open(os.path.join('images', 'cap_field.png'), 'rb'))
                pl_field = discord.File(open(os.path.join('images', 'pl_field.png'), 'rb'))

                if move in other_words:
                    await move_msg.reply(embed = discord.Embed(
                        title = 'Miss',
                        description = "Unfortunately, this word **doesn't belong to any team**",
                        colour = discord.Colour(int('ffffff', 16))
                    ))
                    await second_move_cap.send(embed = discord.Embed(
                        title = 'Miss',
                        description = f"Your team opened the word **`{move}`** that **doesn't belong to any team**",
                        colour = discord.Colour(int('ffffff', 16))
                    ))
                    await first_move_cap.send(embed = discord.Embed(
                        title = 'Lucky!',
                        description = f"The opponent team opened the word **`{move}`** that **doesn't belong to any team**",
                        colour = discord.Colour(int('ffffff', 16))
                    ))
                elif move in first_move_words:
                    await move_msg.reply(embed = discord.Embed(
                        title = 'Miss',
                        description = "Unfortunately, this word **belongs to the opponent team**",
                        colour = discord.Colour(int('ff6450' if first_move_color=='RED' else '50bbff', 16))
                    ))
                    await second_move_cap.send(embed = discord.Embed(
                        title = 'Miss',
                        description = f"Your team opened the word **`{move}`** that **belongs to the opponent team**",
                        colour = discord.Colour(int('ff6450' if first_move_color=='RED' else '50bbff', 16))
                    ))
                    await first_move_cap.send(embed = discord.Embed(
                        title = 'Lucky!',
                        description = f"The opponent team opened the word **`{move}`** that **belongs to your team**",
                        colour = discord.Colour(int('ff6450' if first_move_color=='RED' else '50bbff', 16))
                    ))
                    await ctx.send(file = pl_field)
                    await first_move_cap.send(file = cap_field)
                    await second_move_cap.send(file = cap_field)
                    break
                elif move == endgame_word:
                    await move_msg.reply(embed = discord.Embed(
                        title = 'Miss',
                        description = "Unfortunately, this word **is an endgame one**",
                        colour = discord.Colour(int('444444', 16))
                    ))
                    await second_move_cap.send(embed = discord.Embed(
                        title = 'Miss',
                        description = f"Your team opened the word **`{move}`** that **is an endgame one**",
                        colour = discord.Colour(int('444444', 16))
                    ))
                    await first_move_cap.send(embed = discord.Embed(
                        title = 'Lucky!',
                        description = f"The opponent team opened the word **`{move}`** that **is an endgame one**",
                        colour = discord.Colour(int('444444', 16))
                    ))
                    await ctx.send(file = pl_field)
                    await first_move_cap.send(file = cap_field)
                    await second_move_cap.send(file = cap_field)
                    await ctx.send(embed = discord.Embed(
                        title = 'Game over!',
                        description = f'**{first_move_color} team won!**\n{second_move_color} team opened an endgame word.',
                        colour = discord.Colour(int('ff6450' if first_move_color=='RED' else '50bbff', 16))
                    ))
                    await second_move_cap.send(embed = discord.Embed(
                        title = 'Your team lost!',
                        description = 'Better luck in the next game!',
                        colour = discord.Colour(int('ff6450' if first_move_color=='RED' else '50bbff', 16))
                    ))
                    cursor.execute('SELECT games, games_cap FROM players WHERE id=?', second_move_cap.id)
                    cursor.execute(
                        'UPDATE players SET games=?, games_cap=? WHERE id=?',
                        (cursor.fetchone()[0]+1, cursor.fetchone()[1]+1, second_move_cap.id)
                    )
                    for player in second_move_pl:
                        await player.send(embed = discord.Embed(
                            title = 'Your team lost!',
                            description = 'Better luck in the next game!',
                            colour = discord.Colour(int('ff6450' if first_move_color=='RED' else '50bbff', 16))
                        ))
                        cursor.execute('SELECT games FROM players WHERE id=?', player.id)
                        cursor.execute('UPDATE players SET games=? WHERE id=?', (cursor.fetchone()[0]+1, player.id))
                    await first_move_cap.send(embed = discord.Embed(
                        title = 'Your team won!',
                        description = 'Keep it up!',
                        colour = discord.Colour(int('ff6450' if first_move_color=='RED' else '50bbff', 16))
                    ))
                    cursor.execute('SELECT games, games_cap, wins, wins_cap FROM players WHERE id=?', first_move_cap.id)
                    cursor.execute(
                        'UPDATE players SET games=?, games_cap=?, wins=?, wins_cap=? WHERE id=?',
                        (cursor.fetchone()[0]+1, cursor.fetchone()[1]+1, cursor.fetchone()[2]+1, cursor.fetchone()[3]+1, first_move_cap.id)
                    )
                    for player in first_move_pl:
                        await player.send(embed = discord.Embed(
                            title = 'Your team won!',
                            description = 'Keep it up!',
                            colour = discord.Colour(int('ff6450' if first_move_color=='RED' else '50bbff', 16))
                        ))
                        cursor.execute('SELECT games, games_cap, wins FROM players WHERE id=?', player.id)
                        cursor.execute(
                            'UPDATE players SET games=?, games_cap=?, wins=? WHERE id=?',
                            (cursor.fetchone()[0]+1, cursor.fetchone()[1]+1, cursor.fetchone()[2]+1, player.id)
                        )

                    game = False
                    break
                else:
                    await move_msg.reply(embed = discord.Embed(
                        title = 'Success',
                        description = "You guessed!",
                        colour = discord.Colour(int('ff6450' if second_move_color=='RED' else '50bbff', 16))
                    ))
                    await second_move_cap.send(embed = discord.Embed(
                        title = 'Success',
                        description = f"Your team guessed the word **`{move}`** that **belongs to your team**!",
                        colour = discord.Colour(int('ff6450' if second_move_color=='RED' else '50bbff', 16))
                    ))
                    await first_move_cap.send(embed = discord.Embed(
                        title = 'Opponent success',
                        description = f"The opponent team guessed the word **`{move}`** that **belongs to opponent's team**",
                        colour = discord.Colour(int('ff6450' if second_move_color=='RED' else '50bbff', 16))
                    ))
                await ctx.send(file = pl_field)
                await first_move_cap.send(file = cap_field)
                await second_move_cap.send(file = cap_field)
        
    @commands.command()
    async def demo_start(self, ctx):
        cursor.execute('SELECT players, team1, team2 FROM guilds WHERE id=?', [(ctx.guild.id)])
        players, team1, team2 = map(lambda s: list(map(int, s.split())), cursor.fetchone())
        players = [await self.bot.fetch_user(id) for id in players]
        team1 = [await self.bot.fetch_user(id) for id in team1]
        team2 = [await self.bot.fetch_user(id) for id in team2]

        choosing_dict = {
            'en': {
                'std': 'Original English dictionary (400 words)',
                'duet': 'Original Duet dictionary (400 words)',
                'deep': 'Original Deep Undercover dictionary (18+, 390 words)',
                'denull': "deNULL's dictionary (763 words)",
                'denull18': "deNULL's dictionary (18+, 1081 words)",
                'all': 'All English dictionaries (18+, 1139 words)',
                'esp': 'Esperanto'
            },
            'ru': {
                'std': 'Стандартный словарь из локализации GaGa Games (400 слов)',
                'deep': 'Словарь версии Deep Undercover, GaGa Games (18+, 390 слов)',
                'pard': 'Словарь от Pard (302 слова)',
                'vpupkin': 'Словарь от vpupkin (396 слов, много топонимов)',
                'zav': 'Словарь от Ивана Заворина (2272 частых слов)',
                'denull': 'Словарь от deNULL (636 слов, немного топонимса)',
                'denull18': 'Словарь от deNULL (18+, 1014 слов)',
                'all': 'Все словари вместе (1058 слов)',
                'esp': 'Esperanto'
            }
        }

        await ctx.send(embed = discord.Embed(
            title = 'Select language',
            description = '**en** - English\n**ru** - Russian\n\nType answer in the following message',
            colour = discord.Colour(int('8d08d2', 16))
        ))
        language = await self.bot.wait_for('message', check=lambda msg: msg.content.lower().startswith(tuple(choosing_dict.keys())) and msg.channel == ctx.channel)
        language = language.content.lower()

        dict_choose_list = [f'**{key}** - {val}' for key, val in choosing_dict[language].items()]
        await ctx.send(embed = discord.Embed(
            title = 'Select dictionary',
            description = '\n'.join(dict_choose_list),
            colour = discord.Colour(int('8d08d2', 16))
        ))
        dictionary = await self.bot.wait_for('message', check=lambda msg: msg.content.lower().startswith(tuple(choosing_dict[language].keys())) and msg.channel == ctx.channel)

        await ctx.send(embed = discord.Embed(
            title = 'GAME STARTED!',
            colour = discord.Colour(int('8d08d2', 16))
        ))

        await ctx.send(embed = discord.Embed(
            description = "Team 1 - **RED** blocks\nTeam 2 - **BLUE** blocks",
            colour = discord.Colour(int('8d08d2', 16))
        ))
        await ctx.send(file = discord.File(open('images\\pl1.png', 'rb'))) #players pic
        await ctx.send(embed = discord.Embed(
            title = "Move turn",
            description = "Captain of **Team 1 (Red)**",
            colour = discord.Colour(int('8d08d2', 16))
        ))

        me = await self.bot.fetch_user(689766059712315414)

        await me.send(embed = discord.Embed(
            title = 'You are the captain of **Team 1 (Red)**',
            description = 'You have been muted in the game voice channel',
            colour = discord.Colour(int('8d08d2', 16))
        ))
        await me.send(embed = discord.Embed(
            title = 'This is your move turn',
            description = 'In the following message type the word and the number like **`корова 3`**',
            colour = discord.Colour(int('8d08d2', 16))
        ))
        await me.send(file = discord.File(open('images\\cap1.png', 'rb'))) #cap pic

        cap_move = await self.bot.wait_for('message', check=lambda msg: msg.author == me) # работа 2
        cap_move = cap_move.content.lower()

        await ctx.send(embed = discord.Embed(
            title = '**Team1 (Red)** captain have moved',
            description = f'Move contains a word and a number:\n**`{cap_move}`**\n\nThis is other players of **Team 1 (Red)** to move. Please enter words that you want to open. You can enter no more than {int(cap_move[-1]) + 1} words. To finish move, enter **`-`**.',
            colour = discord.Colour(int('8d08d2', 16))
        ))

        pl_move1 = await self.bot.wait_for('message', check=lambda msg: msg.channel == ctx.channel) # прибор
        pl_move1 = pl_move1.content.lower()

        await ctx.send(embed = discord.Embed(
            title = 'Success',
            descroption = 'You have guessed!',
            colour = discord.Colour(int('8d08d2', 16))
        ))
        await ctx.send(file = discord.File(open('images\\pl2.png', 'rb'))) #pl pic 2

        await me.send(embed = discord.Embed(
            title = 'Success',
            description = f'Your teammate have guessed the word **`{pl_move1}`**!',
            colour = discord.Colour(int('8d08d2', 16))
        ))

        pl_move2 = await self.bot.wait_for('message', check=lambda msg: msg.channel == ctx.channel) # проводник
        pl_move2 = pl_move2.content.lower()

        await ctx.send(embed = discord.Embed(
            title = 'Miss',
            description = 'Unfortunately, this word belongs to the other team. Move of your team is finished.',
            colour = discord.Colour(int('8d08d2', 16))
        ))
        await ctx.send(file = discord.File(open('images\\pl3.png', 'rb'))) #pl pic 3

        await me.send(embed = discord.Embed(
            title = 'Miss',
            description = f'Your teammate have entered the word **`{pl_move2}`** that belongs to the other team',
            colour = discord.Colour(int('8d08d2', 16))
        ))

        await ctx.send(embed = discord.Embed(
            title = "Move turn",
            description = "Captain of **Team 2 (Blue)**",
            colour = discord.Colour(int('8d08d2', 16))
        ))


class SettingCommands(commands.Cog, name = 'Setting Commands'):
    '''Changes the bot's defaults'''
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.command(aliases=['pre'], help="Changes the bot's prefix")
    async def prefix(self, ctx, new_prefix):
        cursor.execute('UPDATE guilds SET prefix=? WHERE id=?', (new_prefix, ctx.guild.id))
        await ctx.message.add_reaction('✅')
    
    @commands.command(brief='[SOON] Sets field image dark mode', help='[SOON] Sets field image dark mode.\nNote: endgame word will be drawn on a white card')
    async def dark(self, ctx):
        cursor.execute('SELECT dark FROM guilds WHERE id=?', [(ctx.guild.id)])
        dark = cursor.fetchone()[0]

        await ctx.send(embed = discord.Embed(
            title = 'Dark mode',
            description = f"Field dark mode is now **{'ON' if dark else 'OFF'}**.\nDo you want to switch it **{'OFF' if dark else 'ON'}**? (y/n)",
            colour = discord.Colour(int('8d08d2', 16))
        ))
        reply = await self.bot.wait_for('message', check=lambda msg: msg.content.lower() in ['y', 'n'] and msg.author == ctx.author and msg.channel == ctx.channel)

        if reply.content.lower() == 'y':
            dark = not dark
            cursor.execute('UPDATE guilds SET dark=? WHERE id=?', (dark, ctx.guild.id))
            await reply.add_reaction('✅')
        else:
            await reply.add_reaction('🆗')

    @commands.command(help='Just a kill')
    @is_chief
    async def kill(self, ctx): # temprorary command
        with open('settings.json', 'w') as settings_file:
            json.dump(settings, settings_file, indent=4)
        base.commit()
        base.close()
        await ctx.message.add_reaction('✅')
        exit()


# Last setting & Starting
bot.add_cog(GameCommands(bot))
bot.add_cog(SettingCommands(bot))

bot.run(settings['token'])