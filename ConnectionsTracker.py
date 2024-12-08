'''Written by Cael Shoop.'''

import os
import json
import logging
import asyncio
import datetime
from dotenv import load_dotenv
from typing import Literal
from discord import app_commands, Intents, Embed, Color, Client, Message, Interaction, TextChannel, utils, Activity, ActivityType
from discord.ext import tasks

load_dotenv()

# Logger setup
logger = logging.getLogger("Connections Tracker")
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(fmt='[Connections] [%(asctime)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

file_handler = logging.FileHandler('connections.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)


def get_score(player):
    return player.score


def get_wins(player):
    return player.winCount


def get_con_submissions(player):
    return player.submissionCount


def get_tot_guesses(player):
    return player.totalGuessCount


def get_cons(player):
    return player.connectionCount


def get_sub_cons(player):
    return player.subConnectionCount


def get_mistakes(player):
    return player.mistakeCount


def get_win_percent(player):
    return ((player.winCount / player.submissionCount) * 100)


def get_avg_guesses(player):
    return (player.totalGuessCount / player.submissionCount)


def get_average_mistakes(player):
    return (player.mistakeCount / player.submissionCount)


def get_completion_percent(player):
    return ((player.connectionCount / player.submissionCount) * 100)


class ConnectionsTrackerClient(Client):
    FILENAME = 'info.json'

    class Player():
        def __init__(self, name):
            self.name = name
            self.score = 0
            self.winCount = 0
            self.connectionCount = 0
            self.subConnectionCount = 0
            self.mistakeCount = 0
            self.submissionCount = 0
            self.totalGuessCount = 0
            self.registered = True
            self.silenced = False
            self.completedToday = False
            self.succeededToday = False

    def __init__(self, intents):
        super(ConnectionsTrackerClient, self).__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.text_channel: TextChannel
        self.puzzle_number = 0
        self.last_scored = datetime.datetime.now().astimezone() - datetime.timedelta(days=1)
        self.scored_today = False
        self.sent_warning = False
        self.midnight_called = False
        self.players = []

    def read_json_file(self):
        if os.path.exists(self.FILENAME):
            with open(self.FILENAME, 'r', encoding='utf-8') as file:
                logger.info(f'Reading {self.FILENAME}')
                data = json.load(file)
                for firstField, secondField in data.items():
                    if firstField == 'text_channel':
                        self.text_channel = self.get_channel(int(secondField['text_channel']))
                        logger.info(f'Got text channel id of {self.text_channel.id}')
                    elif firstField == 'puzzle_number':
                        self.puzzle_number = secondField['puzzle_number']
                        logger.info(f'Got day number of {self.puzzle_number}')
                    elif firstField == 'last_scored':
                        self.last_scored = datetime.datetime.fromisoformat(secondField['last_scored'])
                        logger.info(f'Got last scored datetime of {self.last_scored.isoformat()}')
                    elif firstField == 'scored_today':
                        self.scored_today = secondField['scored_today']
                        logger.info(f'Got scored today value of {self.scored_today}')
                    else:
                        player_exists = False
                        for player in self.players:
                            if firstField == player.name:
                                player_exists = True
                                break
                        if not player_exists:
                            load_player = self.Player(firstField)
                            load_player.winCount = secondField['winCount']
                            load_player.connectionCount = secondField['connectionCount']
                            load_player.subConnectionCount = secondField['subConnectionCount']
                            load_player.mistakeCount = secondField['mistakeCount']
                            load_player.submissionCount = secondField['submissionCount']
                            load_player.totalGuessCount = secondField['totalGuessCount']
                            load_player.score = secondField['score']
                            load_player.registered = secondField['registered']
                            load_player.silenced = secondField['silenced']
                            load_player.completedToday = secondField['completedToday']
                            load_player.succeededToday = secondField['succeededToday']
                            self.players.append(load_player)
                            logger.info(f'Loaded player {load_player.name}\n'
                                        f'\t\t\twins: {load_player.winCount}\n'
                                        f'\t\t\tconnections: {load_player.connectionCount}\n'
                                        f'\t\t\tsubConnections: {load_player.subConnectionCount}\n'
                                        f'\t\t\tmistakes: {load_player.mistakeCount}\n'
                                        f'\t\t\tsubmissions: {load_player.submissionCount}\n'
                                        f'\t\t\ttotalGuesses: {load_player.totalGuessCount}\n'
                                        f'\t\t\tscore: {load_player.score}\n'
                                        f'\t\t\tregistered: {load_player.registered}\n'
                                        f'\t\t\tsilenced: {load_player.silenced}\n'
                                        f'\t\t\tcompleted: {load_player.completedToday}\n'
                                        f'\t\t\tsucceeded: {load_player.succeededToday}')
                logger.info(f'Successfully loaded {self.FILENAME}')

    def write_json_file(self):
        data = {}
        data['text_channel'] = {'text_channel': self.text_channel.id}
        data['puzzle_number'] = {'puzzle_number': self.puzzle_number}
        data['last_scored'] = {'last_scored': self.last_scored.isoformat()}
        data['scored_today'] = {'scored_today': self.scored_today}
        for player in self.players:
            data[player.name] = {'winCount': player.winCount,
                                 'connectionCount': player.connectionCount,
                                 'subConnectionCount': player.subConnectionCount,
                                 'submissionCount': player.submissionCount,
                                 'mistakeCount': player.mistakeCount,
                                 'totalGuessCount': player.totalGuessCount,
                                 'score': player.score,
                                 'registered': player.registered,
                                 'silenced': player.silenced,
                                 'completedToday': player.completedToday,
                                 'succeededToday': player.succeededToday}
        json_data = json.dumps(data, indent=4)
        logger.info(f'Writing {self.FILENAME}')
        with open(self.FILENAME, 'w+', encoding='utf-8') as file:
            file.write(json_data)

    def get_scoreboard_embed(self, scoreboard: list):
        embed = Embed(title=f"Scoreboard for Connections #{self.puzzle_number}",
                      color=Color.green())
        for score in scoreboard:
            embed.add_field(name=score[0], value=score[1], inline=False)
        return embed

    async def process(self, message: Message, player: Player):
        try:
            parseMsg = []
            for line in message.content.split('\n'):
                if 'Puzzle #' in line:
                    logger.info(f'{player.name} submitted results for puzzle #{line.split("#")[1]}')
                    puzzleNum = int(line.split('#')[1])
                    if puzzleNum != self.puzzle_number:
                        await message.channel.send(f'The current puzzle # is {self.puzzle_number}. Your submission for puzzle #{puzzleNum} has not been accepted.')
                        return
                elif '🟪' in line or '🟩' in line or '🟦' in line or '🟨' in line:
                    parseMsg.append(line)
            player.submissionCount += 1
            subConnectionsToday = 0
            player.score = 0
            gotYellow = False
            gotGreen = False
            gotBlue = False
            gotPurple = False
            for guess in parseMsg:
                player.totalGuessCount += 1
                if '🟨🟨🟨🟨' in guess:
                    gotYellow = True
                    await message.add_reaction('🟨')
                    player.subConnectionCount += 1
                    subConnectionsToday += 1
                    player.score += 1  # difficulty tweak
                elif '🟩🟩🟩🟩' in guess:
                    gotGreen = True
                    await message.add_reaction('🟩')
                    player.subConnectionCount += 1
                    subConnectionsToday += 1
                    player.score += 2
                elif '🟦🟦🟦🟦' in guess:
                    gotBlue = True
                    await message.add_reaction('🟦')
                    player.subConnectionCount += 1
                    subConnectionsToday += 1
                    player.score += 3
                elif '🟪🟪🟪🟪' in guess:
                    gotPurple = True
                    await message.add_reaction('🟪')
                    player.subConnectionCount += 1
                    subConnectionsToday += 1
                    player.score += 4
                else:
                    player.mistakeCount += 1
            if gotYellow and gotGreen and gotBlue and gotPurple:
                player.connectionCount += 1
                player.succeededToday = True
            logger.info(f'Player {player.name} - score: {player.score}, succeeded: {player.succeededToday}')

            player.completedToday = True
            client.write_json_file()
            if player.score == 0:
                await message.add_reaction('0️⃣')
            elif player.score == 1:
                await message.add_reaction('1️⃣')
            elif player.score == 2:
                await message.add_reaction('2️⃣')
            elif player.score == 3:
                await message.add_reaction('3️⃣')
            elif player.score == 4:
                await message.add_reaction('4️⃣')
            elif player.score == 5:
                await message.add_reaction('5️⃣')
            elif player.score == 6:
                await message.add_reaction('6️⃣')
            elif player.score == 7:
                await message.add_reaction('7️⃣')
            elif player.score == 8:
                await message.add_reaction('8️⃣')
            elif player.score == 9:
                await message.add_reaction('9️⃣')
            elif player.score == 10:
                await message.add_reaction('🔟')
            if player.succeededToday:
                await message.add_reaction('👍')
            else:
                await message.add_reaction('👎')
        except Exception:
            logger.info(f'User {player.name} submitted invalid result message')
            await message.channel.send(f'{player.name}, you sent a Connections results message with invalid syntax. Please try again.')

    def tally_scores(self) -> str:
        if not self.players or self.scored_today:
            return ''

        logger.info(f'Tallying scores for puzzle #{self.puzzle_number}')
        connections_players = []  # list of players who are registered and completed the connections
        winners = []  # list of winners - the one/those with the highest score
        scoreboard = []
        placeCounter = 0

        for player in self.players:
            if player.registered and player.completedToday:
                connections_players.append(player)
        connections_players.sort(key=get_score, reverse=True)

        if connections_players[0].score > 0:
            for player in connections_players.copy():
                if player.score == connections_players[0].score:
                    player.winCount += 1
                    winners.append(player)
                else:
                    break

        prevScore = -1
        for player in connections_players:
            if player.score != prevScore:
                placeCounter += 1
            prevScore = player.score
            title = f"{placeCounter}. ({player.score} points)"
            if player.winCount == 1:
                subResult = f"{player.name} (1 win)"
            else:
                subResult = f"{player.name} ({player.winCount} wins)"
            scoreboard.append([title, subResult])
        return scoreboard

    async def setup_hook(self):
        await self.tree.sync()


discord_token = os.getenv('DISCORD_TOKEN')
client = ConnectionsTrackerClient(intents=Intents.all())


@client.event
async def on_ready():
    client.read_json_file()
    if not warning_call.is_running():
        warning_call.start()
    if not midnight_call.is_running():
        midnight_call.start()
    await client.change_presence(activity=Activity(type=ActivityType.playing, name="Connections"))
    logger.info(f'{client.user} has connected to Discord!')


@client.event
async def on_message(message: Message):
    # message is from this bot or not in dedicated text channel
    if message.channel.id != client.text_channel.id or message.author.bot or client.scored_today:
        return

    if 'Connections' in message.content and 'Puzzle #' in message.content and ('🟨' in message.content or '🟩' in message.content or '🟦' in message.content or '🟪' in message.content):
        # no registered players
        if not client.players:
            await message.channel.send(f'{message.author.mention}, there are no registered players! Please register and resend your results to be the first.')
            return
        # find player in memory
        player: client.Player
        foundPlayer = False
        for player_it in client.players:
            if message.author.name == player_it.name:
                foundPlayer = True
                player = player_it
        # player is not registered
        if not foundPlayer:
            await message.channel.send(f'{message.author.name}, you are not registered! Please register and resend your results.')
            return
        # player has already sent results
        if player.completedToday:
            logger.info(f'{player.name} tried to resubmit results')
            await message.channel.send(f'{player.name}, you have already submitted your results today.')
            return

        client.write_json_file()

        # process player's results
        await client.process(message, player)

    for player in client.players:
        if player.registered and not player.completedToday:
            return
    if not client.scored_today:
        client.scored_today = True
        client.last_scored = datetime.datetime.now()
        client.write_json_file()
        scoreboard = client.tally_scores()
        embed = client.get_scoreboard_embed(scoreboard)
        await client.text_channel.send(embed=embed)


@client.tree.command(name='register', description='Register for Connections tracking.')
async def register_command(interaction: Interaction):
    response = ''
    playerFound = False
    for player in client.players:
        if interaction.user.name.strip() == player.name.strip():
            if player.registered:
                logger.info(f'User {interaction.user.name.strip()} attempted to re-register for tracking')
                response += 'You are already registered for Connections tracking!\n'
            else:
                logger.info(f'Registering user {interaction.user.name.strip()} for tracking')
                player.registered = True
                client.write_json_file()
                response += 'You have been registered for Connections tracking.\n'
            playerFound = True
    if not playerFound:
        logger.info(f'Registering user {interaction.user.name.strip()} for tracking')
        player_obj = client.Player(interaction.user.name.strip())
        client.players.append(player_obj)
        client.write_json_file()
        response += 'You have been registered for Connections tracking.\n'
    await interaction.response.send_message(response)


@client.tree.command(name='deregister', description='Deregister from Connections tracking. Use twice to delete saved data.')
async def deregister_command(interaction: Interaction):
    players_copy = client.players.copy()
    response = ''
    playerFound = False
    for player in players_copy:
        if player.name.strip() == interaction.user.name.strip():
            if player.registered:
                player.registered = False
                logger.info(f'Deregistered user {player.name}')
                response += 'You have been deregistered for Connections tracking. Deregistering a second time will delete your saved data.'
            else:
                client.players.remove(player)
                logger.info(f'Deleted data for user {player.name}')
                response += 'Your saved data has been deleted for Connections tracking.'
            client.write_json_file()
            playerFound = True
    if not playerFound:
        logger.info(f'Non-existant user {interaction.user.name.strip()} attempted to deregister')
        response += 'You have no saved data for Connections tracking.'
    if not client.players:
        client.scored_today = False
    await interaction.response.send_message(response)


@client.tree.command(name='silenceping', description='Stop sending a daily warning ping to a specific user.')
@app_commands.describe(username='Username of the person to silence pings for. Blank will apply it to whoever enters the command.')
@app_commands.describe(silence='Whether to silence (true) or unsilence (false) daily reminder pings for a specific user.')
async def silenceping_command(interaction: Interaction, username: str = None, silence: bool = True):
    if not username:
        username = interaction.user.name
    for player in client.players:
        if player.name.lower() == username.lower():
            if player.silenced and silence:
                await interaction.response.send_message(f'One hour warning ping already silenced for {player.name}.')
                return
            elif not player.silenced and not silence:
                await interaction.response.send_message(f'One hour warning ping already enabled for {player.name}.')
                return
            player.silenced = silence
            if silence:
                await interaction.response.send_message(f'Silenced one hour warning ping for {player.name}.')
            else:
                await interaction.response.send_message(f'Enabled one hour warning ping for {player.name}.')
            return
    await interaction.response(f'Could not find {player.name}.\n\n__Existing players:__\n' + "\n".join([player.name for player in client.players]))


@client.tree.command(name='bind', description='Set this channel as the text channel for Connections Tracker.')
async def bind_command(interaction: Interaction):
    try:
        client.text_channel = interaction.channel
        client.write_json_file()
        await interaction.response.send_message(f'Successfully set text channel for Connections Tracker to {interaction.channel.name}!')
    except Exception as e:
        logger.info(f'Failed to set text channel or write json during bind command: {e}')
        await interaction.response.send_message(f'Failed to set text channel or save config: {e}')


@client.tree.command(name='stats', description='Show stats for all players.')
@app_commands.describe(sort_by='Select the stat you want to sort by.')
@app_commands.describe(show_x_players='Only show the first x number of players.')
async def stats_command(interaction: Interaction,
                        sort_by: Literal['Win %', 'Wins', 'Submissions', 'Avg. Guesses', 'Total Guesses', 'Completion %', 'Connections', 'Subconnections', 'Mistakes %', 'Mistakes'] = 'Win %',
                        show_x_players: int = -1,
                        show_unregistered: bool = False):
    players_copy = client.players.copy()
    if show_x_players < 1:
        show_x_players = len(players_copy)

    if sort_by == 'Win %':
        players_copy.sort(key=get_win_percent, reverse=True)
    elif sort_by == 'Wins':
        players_copy.sort(key=get_wins, reverse=True)
    elif sort_by == 'Submissions':
        players_copy.sort(key=get_con_submissions, reverse=True)
    elif sort_by == 'Avg. Guesses':
        players_copy.sort(key=get_avg_guesses, reverse=True)
    elif sort_by == 'Total Guesses':
        players_copy.sort(key=get_tot_guesses, reverse=True)
    elif sort_by == 'Completion %':
        players_copy.sort(key=get_completion_percent, reverse=True)
    elif sort_by == 'Connections':
        players_copy.sort(key=get_cons, reverse=True)
    elif sort_by == 'Subconnections':
        players_copy.sort(key=get_sub_cons, reverse=True)
    elif sort_by == 'Mistake %':
        players_copy.sort(key=get_average_mistakes)
    elif sort_by == 'Mistakes':
        players_copy.sort(key=get_mistakes)

    embeds = [Embed(title="Connections Stats", color=Color.green())]
    if show_x_players > len(players_copy):
        show_x_players = len(players_copy)
    for player in players_copy:
        if show_x_players <= 0:
            break
        if not show_unregistered and not player.registered:
            continue
        show_x_players -= 1
        embed = Embed(title=f"{player.name}")
        embed.add_field(name="Registered", value=f"{player.registered}", inline=False)
        win_percent = round(get_win_percent(player), ndigits=2)
        embed.add_field(name="Win Percentage", value=f"{win_percent} % of submissions", inline=False)
        embed.add_field(name="Total Wins", value=f"{player.winCount}", inline=False)
        embed.add_field(name="Submissions", value=f"{player.submissionCount}", inline=False)
        average_guesses = round(get_avg_guesses(player), ndigits=2)
        embed.add_field(name="Average Guesses", value=f"{average_guesses} per submission", inline=False)
        embed.add_field(name="Total Guesses", value=f"{player.totalGuessCount}", inline=False)
        completion_percent = round(get_completion_percent(player), ndigits=2)
        embed.add_field(name="Completion Percentage", value=f"{completion_percent} % of submissions", inline=False)
        embed.add_field(name="Total Successful Connections", value=f"{player.connectionCount}", inline=False)
        embed.add_field(name="Total Successful Subconnections", value=f"{player.subConnectionCount}", inline=False)
        average_mistakes = round(get_average_mistakes(player), ndigits=2)
        embed.add_field(name="Average Mistakes", value=f"{average_mistakes} per submission", inline=False)
        embed.add_field(name="Total Mistakes", value=f"{player.mistakeCount}", inline=False)
        embeds.append(embed)
    await interaction.response.send_message(embeds=embeds, ephemeral=True)


async def warning():
    if not client.players or client.sent_warning or client.scored_today:
        return
    logger.info('It is 23:00, warning registered players who are not silenced and have not submitted results')
    warning = ''
    for player in client.players:
        if player.registered and not player.completedToday and not player.silenced:
            user = utils.get(client.users, name=player.name)
            warning += f'{user.mention} '
    if warning != '':
        await client.text_channel.send(f'{warning}, you have one hour left to do the Connections!')
    client.sent_warning = True


@tasks.loop(hours=24)
async def warning_call():
    await warning()


@warning_call.before_loop
async def before_warning_call():
    await client.wait_until_ready()
    now = datetime.datetime.now().astimezone()
    hr_before_midnight = now.replace(hour=23, minute=0, second=0, microsecond=0)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
    # Send warning if we passed 2300 and the bot wasn't running
    if hr_before_midnight < now and now < midnight and not client.scored_today and not client.sent_warning:
        logger.info('It is after 23:00 but before midnight, sending warning')
        await warning()
        hr_before_midnight += datetime.timedelta(days=1)
    seconds_until_2300 = (hr_before_midnight - now).total_seconds()
    logger.info(f'Sleeping for {seconds_until_2300} seconds until 23:00 {hr_before_midnight.isoformat()}')
    await asyncio.sleep(seconds_until_2300)


async def score():
    try:
        shamed = ''
        for player in client.players:
            if player.registered and not player.completedToday:
                user = utils.get(client.users, name=player.name)
                if user:
                    shamed += f'{user.mention} '
                else:
                    logger.info(f'Failed to mention user {player.name}')
        if shamed != '':
            await client.text_channel.send(f'SHAME ON {shamed} FOR NOT DOING THE CONNECTIONS!')
        client.last_scored = datetime.datetime.now()
        scoreboard = client.tally_scores()
        embed = client.get_scoreboard_embed(scoreboard)
        await client.text_channel.send(embed=embed)
    except Exception as e:
        logger.exception(f'Error while scoring: {e}')


async def update():
    try:
        client.scored_today = False
        client.sent_warning = False
        everyone = ''
        for player in client.players:
            player.score = 0
            player.completedToday = False
            player.succeededToday = False
            user = utils.get(client.users, name=player.name)
            if user:
                if player.registered:
                    everyone += f'{user.mention} '
            else:
                logger.info(f'Failed to mention user {player.name}')
        client.puzzle_number += 1
        embed = Embed(title=f"It's time to find the Connections #{client.puzzle_number}!",
                      description="[Connections](https://www.nytimes.com/games/connections)",
                      color=Color.blue())
        embed.set_thumbnail(url="https://static01.nyt.com/images/2023/08/25/crosswords/alpha-connections-icon-original/alpha-connections-icon-original-smallSquare252.png?format=pjpg&quality=75&auto=webp&disable=upscale")
        embed.set_footer(text="Created by Cubic Sphere")
        await client.text_channel.send(content=f"{everyone}", embed=embed)
    except Exception as e:
        logger.exception(f'Error while sending out midnight message: {e}')
    client.write_json_file()


@tasks.loop(hours=24)
async def midnight_call():
    if not client.players:
        return
    while datetime.datetime.now().astimezone().date() == client.last_scored.date():
        await asyncio.sleep(1)
    logger.info('It is midnight, sending daily scoreboard if unscored and then mentioning registered players')
    if not client.scored_today:
        await score()
    await update()


@midnight_call.before_loop
async def before_midnight_call():
    await client.wait_until_ready()
    now = datetime.datetime.now().astimezone()
    # Update if the date changed and the bot wasn't running
    if client.last_scored.date() < now.date() and not client.scored_today:
        logger.info('Last scored date is before today and we have not yet scored today')
        await update()
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
    seconds_until_midnight = (midnight - now).total_seconds()
    logger.info(f'Sleeping for {seconds_until_midnight} seconds until midnight {midnight.isoformat()}')
    await asyncio.sleep(seconds_until_midnight)


client.run(discord_token)
