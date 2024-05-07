'''Written by Cael Shoop.'''

import os
import json
import datetime
from dotenv import load_dotenv
from typing import Literal
from discord import app_commands, Intents, Client, Message, Interaction, TextChannel, utils
from discord.ext import tasks

load_dotenv()


def get_time():
    ct = str(datetime.datetime.now())
    hour = int(ct[11:13])
    minute = int(ct[14:16])
    return hour, minute


def get_log_time():
    time = datetime.datetime.now().astimezone()
    output = ''
    if time.hour < 10:
        output += '0'
    output += f'{time.hour}:'
    if time.minute < 10:
        output += '0'
    output += f'{time.minute}:'
    if time.second < 10:
        output += '0'
    output += f'{time.second}'
    return output


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
    return ((player.totalGuessCount / player.submissionCount) * 100)
def get_mistake_percent(player):
    return ((player.mistakeCount / player.submissionCount) * 100)
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
        self.scored_today = False
        self.sent_warning = False
        self.midnight_called = False
        self.players = []


    def read_json_file(self):
        if os.path.exists(self.FILENAME):
            with open(self.FILENAME, 'r', encoding='utf-8') as file:
                print(f'{get_log_time()}> Reading {self.FILENAME}')
                data = json.load(file)
                for firstField, secondField in data.items():
                    if firstField == 'text_channel':
                        self.text_channel = self.get_channel(int(secondField['text_channel']))
                        print(f'{get_log_time()}> Got text channel id of {self.text_channel.id}')
                    elif firstField == 'puzzle_number':
                        self.puzzle_number = secondField['puzzle_number']
                        print(f'{get_log_time()}> Got day number of {self.puzzle_number}')
                    elif firstField == 'scored_today':
                        self.scored_today = secondField['scored_today']
                        print(f'{get_log_time()}> Got scored today value of {self.scored_today}')
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
                            load_player.completedToday = secondField['completedToday']
                            load_player.succeededToday = secondField['succeededToday']
                            self.players.append(load_player)
                            print(f'{get_log_time()}> Loaded player {load_player.name}\n'
                                f'\t\t\twins: {load_player.winCount}\n'
                                f'\t\t\tconnections: {load_player.connectionCount}\n'
                                f'\t\t\tsubConnections: {load_player.subConnectionCount}\n'
                                f'\t\t\tmistakes: {load_player.mistakeCount}\n'
                                f'\t\t\tsubmissions: {load_player.submissionCount}\n'
                                f'\t\t\ttotalGuesses: {load_player.totalGuessCount}\n'
                                f'\t\t\tscore: {load_player.score}\n'
                                f'\t\t\tregistered: {load_player.registered}\n'
                                f'\t\t\tcompleted: {load_player.completedToday}\n'
                                f'\t\t\tsucceeded: {load_player.succeededToday}')
                print(f'{get_log_time()}> Successfully loaded {self.FILENAME}')


    def write_json_file(self):
        data = {}
        data['text_channel'] = {'text_channel': self.text_channel.id}
        data['puzzle_number'] = {'puzzle_number': self.puzzle_number}
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
                                 'completedToday': player.completedToday,
                                 'succeededToday': player.succeededToday}
        json_data = json.dumps(data, indent=4)
        print(f'{get_log_time()}> Writing {self.FILENAME}')
        with open(self.FILENAME, 'w+', encoding='utf-8') as file:
            file.write(json_data)


    async def process(self, message: Message, player: Player):
        try:
            parseMsg = []
            for line in message.content.split('\n'):
                if 'Puzzle #' in line:
                    print(f'{get_log_time()}> {player.name} submitted results for puzzle #{line.split("#")[1]}')
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
                    player.score += 1 # difficulty tweak
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
            print(f'{get_log_time()}> Player {player.name} - score: {player.score}, succeeded: {player.succeededToday}')

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
        except:
            print(f'{get_log_time()}> User {player.name} submitted invalid result message')
            await message.channel.send(f'{player.name}, you sent a Connections results message with invalid syntax. Please try again.')


    def tally_scores(self):
        if not self.players or self.scored_today:
            return ''

        print(f'{get_log_time()}> Tallying scores for puzzle #{self.puzzle_number}')
        connections_players = [] # list of players who are registered and completed the connections
        winners = [] # list of winners - the one/those with the highest score
        losers = [] # list of losers - those who didn't win
        results = [] # list of strings - the scoreboard to print out
        results.append(f'CONNECTIONS #{self.puzzle_number} COMPLETE!\n\n**SCOREBOARD:**\n')
        placeCounter = 2

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
        else:
            placeCounter = 1

        for player in connections_players:
            subResult = ''
            if player in winners:
                subResult = f'1. {player.name} '
            else:
                subResult = f'{placeCounter}. {player.name} '
                placeCounter += 1
            if player.winCount == 1:
                subResult += '(1 win) '
            else:
                subResult += f'({player.winCount} wins) '
            if player.succeededToday:
                subResult += 'got the connections '
                if player in winners:
                    subResult += 'and wins '
            else:
                subResult += 'did not get all of the subconnections '
                if player in winners:
                    subResult += 'but wins '
            subResult += f'with a score of {player.score}'
            if player in winners:
                subResult += '!\n'
            else:
                subResult += '.\n'
            results.append(subResult)

        self.scored_today = True
        self.write_json_file()
        return results

    async def setup_hook(self):
        await self.tree.sync()


discord_token = os.getenv('DISCORD_TOKEN')
client = ConnectionsTrackerClient(intents=Intents.all())


@client.event
async def on_ready():
    client.read_json_file()
    checkScored = True
    if not midnight_call.is_running():
        midnight_call.start()
    print(f'{get_log_time()}> {client.user} has connected to Discord!')


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
            print(f'{get_log_time()}> {player.name} tried to resubmit results')
            await message.channel.send(f'{player.name}, you have already submitted your results today.')
            return

        client.write_json_file()

        # process player's results
        await client.process(message, player)

    for player in client.players:
        if player.registered and not player.completedToday:
            return
    if not client.scored_today:
        scoreboard = ''
        for line in client.tally_scores():
            scoreboard += line
        await message.channel.send(scoreboard)


@client.tree.command(name='register', description='Register for Connections tracking.')
async def register_command(interaction: Interaction):
    response = ''
    playerFound = False
    for player in client.players:
        if interaction.user.name.strip() == player.name.strip():
            if player.registered:
                print(f'{get_log_time()}> User {interaction.user.name.strip()} attempted to re-register for tracking')
                response += 'You are already registered for Connections tracking!\n'
            else:
                print(f'{get_log_time()}> Registering user {interaction.user.name.strip()} for tracking')
                player.registered = True
                client.write_json_file()
                response += 'You have been registered for Connections tracking.\n'
            playerFound = True
    if not playerFound:
        print(f'{get_log_time()}> Registering user {interaction.user.name.strip()} for tracking')
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
                print(f'{get_log_time()}> Deregistered user {player.name}')
                response += 'You have been deregistered for Connections tracking. Deregistering a second time will delete your saved data.'
            else:
                client.players.remove(player)
                print(f'{get_log_time()}> Deleted data for user {player.name}')
                response += 'Your saved data has been deleted for Connections tracking.'
            client.write_json_file()
            playerFound = True
    if not playerFound:
        print(f'{get_log_time()}> Non-existant user {interaction.user.name.strip()} attempted to deregister')
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
                await interaction.response.send_message(f'Daily ping already silenced for {player.name}.')
                return
            elif not player.silenced and not silence:
                await interaction.response.send_message(f'Daily ping already enabled for {player.name}.')
                return
            player.silenced = silence
            if silence:
                await interaction.response.send_message(f'Silenced daily ping for {player.name}.')
            else:
                await interaction.response.send_message(f'Enabled daily ping for {player.name}.')
            return
    await interaction.response(f'Could not find {player.name}.\n\n__Existing players:__\n' + "\n".join([player.name for player in client.players]))


@client.tree.command(name='bind', description='Set this channel as the text channel for Connections Tracker.')
async def bind_command(interaction: Interaction):
    try:
        client.text_channel = interaction.channel
        client.write_json_file()
        await interaction.response.send_message(f'Successfully set text channel for Connections Tracker to {interaction.channel.name}!')
    except Exception as e:
        print(f'{get_log_time()}> Failed to set text channel or write json during bind command: {e}')
        await interaction.response.send_message(f'Failed to set text channel or save config: {e}')


@client.tree.command(name='stats', description='Show stats for all players.')
@app_commands.describe(sort_by='Select the stat you want to sort by.')
@app_commands.describe(show_x_players='Only show the first x number of players.')
async def stats_command(interaction: Interaction, sort_by:Literal['Win %', 'Wins', 'Submissions', 'Avg. Guesses', 'Total Guesses', 'Completion %', 'Connections', 'Subconnections', 'Mistakes %', 'Mistakes'] = 'Win %', show_x_players:int = -1):
    players_copy = client.players.copy()
    if show_x_players < 1:
        show_x_players = len(players_copy)

    if show_x_players == len(players_copy):
        stats = f'Sorting all players by {sort_by}:\n'
    else:
        stats = f'Sorting top {show_x_players} players by {sort_by}:\n'
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
        players_copy.sort(key=get_mistake_percent)
    elif sort_by == 'Mistakes':
        players_copy.sort(key=get_mistakes)

    if show_x_players > len(players_copy):
        show_x_players = len(players_copy)
    for player in players_copy:
        if show_x_players <= 0:
            break
        show_x_players -= 1
        stats += f'{player.name}\n'
        win_percent = round(get_win_percent(player), ndigits=2)
        stats += f'\t{win_percent} Win %\n'

        if player.winCount == 1:
            stats += f'\t1 Win\n'
        else:
            stats += f'\t{player.winCount} Wins\n'

        if player.submissionCount == 1:
            stats += f'\t1 Submission\n'
        else:
            stats += f'\t{player.submissionCount} Submissions\n'

        avg_guesses = round(get_avg_guesses(player), ndigits=2)
        stats += f'\t{avg_guesses} Average Guesses per Submission\n'

        if player.totalGuessCount == 1:
            stats += f'\t1 Total guess\n'
        else:
            stats += f'\t{player.totalGuessCount} Total guesses\n'

        completion_percent = round(get_completion_percent(player), ndigits=2)
        stats += f'\t{completion_percent} Completion %\n'

        if player.connectionCount == 1:
            stats += f'\t1 Successful connection\n'
        else:
            stats += f'\t{player.connectionCount} Successful connections\n'

        if player.subConnectionCount == 1:
            stats += f'\t1 Successful subconnection\n'
        else:
            stats += f'\t{player.subConnectionCount} Successful subconnections\n'

        mistake_percent = round(get_mistake_percent(player), ndigits=2)
        stats += f'\t{mistake_percent} Mistake %\n'

        if player.mistakeCount == 1:
            stats += f'\t1 Mistake\n'
        else:
            stats += f'\t{player.mistakeCount} Mistakes\n'

    await interaction.response.send_message(stats)


@tasks.loop(seconds=1)
async def midnight_call():
    if not client.players:
        return

    hour, minute = get_time()
    if client.sent_warning and hour == 23 and minute == 1:
        client.sent_warning = False
    if not client.sent_warning and not client.scored_today and hour == 23 and minute == 0:
        warning = ''
        for player in client.players:
            if player.registered and not player.completedToday and not player.silenced:
                user = utils.get(client.users, name=player.name)
                warning += f'{user.mention} '
        if warning != '':
            await client.text_channel.send(f'{warning}, you have one hour left to do the Connections!')
        client.sent_warning = True

    if client.midnight_called and hour == 0 and minute == 1:
        client.midnight_called = False
        client.write_json_file()
    if client.midnight_called or hour != 0 or minute != 0:
        return
    client.midnight_called = True

    print(f'{get_log_time()}> It is midnight, sending daily scoreboard if unscored and then mentioning registered players')

    if not client.scored_today:
        shamed = ''
        for player in client.players:
            if player.registered and not player.completedToday:
                user = utils.get(client.users, name=player.name)
                if user:
                    shamed += f'{user.mention} '
                else:
                    print(f'{get_log_time()}> Failed to mention user {player.name}')
        if shamed != '':
            await client.text_channel.send(f'SHAME ON {shamed} FOR NOT DOING THE CONNECTIONS!')
        scoreboard = ''
        for line in client.tally_scores():
            scoreboard += line
        await client.text_channel.send(scoreboard)

    client.scored_today = False
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
            print(f'{get_log_time()}> Failed to mention user {player.name}')
    client.puzzle_number += 1
    await client.text_channel.send(f'{everyone}\nIt\'s time to find the Connections #{client.puzzle_number}!\nhttps://www.nytimes.com/games/connections')
    client.write_json_file()


client.run(discord_token)
