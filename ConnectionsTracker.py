'''Written by Cael Shoop.'''

import os
import json
import random
import discord
import datetime
from dotenv import load_dotenv
from discord import app_commands, Intents, Client, File, Interaction
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


class ConnectionsTrackerClient(Client):
    FILENAME = 'info.json'

    class Player():
        def __init__(self, name):
            self.name = name
            self.score = 0
            self.winCount = 0
            self.registered = True
            self.completedToday = False
            self.succeededToday = False
            self.filePath = ''


    def __init__(self, intents):
        super(ConnectionsTrackerClient, self).__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.text_channel = 0
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
                        self.text_channel = secondField['text_channel']
                        print(f'{get_log_time()}> Got text channel id of {self.text_channel}')
                    elif firstField == 'puzzle_number':
                        self.puzzle_number = secondField['puzzle_number']
                        print(f'{get_log_time()}> Got day number of {self.puzzle_number}')
                    elif firstField == 'scored_today':
                        self.scored_today = secondField['scored_today']
                        print(f'{get_log_time()}> Got scored today value of {self.scored_today}')
                    else:
                        load_player = self.Player(firstField)
                        load_player.winCount = secondField['winCount']
                        load_player.score = secondField['score']
                        load_player.registered = secondField['registered']
                        load_player.completedToday = secondField['completedToday']
                        load_player.succeededToday = secondField['succeededToday']
                        playerExists = False
                        for player in self.players:
                            if load_player.name == player.name:
                                playerExists = True
                        if not playerExists:
                            self.players.append(load_player)
                        print(f'{get_log_time()}> Loaded player {load_player.name} - '
                                f'wins: {load_player.winCount}, '
                                f'score: {load_player.score}, '
                                f'registered: {load_player.registered}, '
                                f'completed: {load_player.completedToday}, '
                                f'succeeded: {load_player.succeededToday}')
                print(f'{get_log_time()}> Successfully loaded {self.FILENAME}')


    def write_json_file(self):
        data = {}
        data['text_channel'] = {'text_channel': self.text_channel}
        data['puzzle_number'] = {'puzzle_number': self.puzzle_number}
        data['scored_today'] = {'scored_today': self.scored_today}
        for player in self.players:
            data[player.name] = {'winCount': player.winCount,
                                    'score': player.score,
                                    'registered': player.registered,
                                    'completedToday': player.completedToday,
                                    'succeededToday': player.succeededToday}
        json_data = json.dumps(data)
        print(f'{get_log_time()}> Writing {self.FILENAME}')
        with open(self.FILENAME, 'w+', encoding='utf-8') as file:
            file.write(json_data)


    async def process(self, message: discord.Message, player: Player):
        try:
            parseMsg = []
            for line in message.content:
                if 'Puzzle #' in line:
                    print(f'{get_log_time()}> player.name submitted results for puzzle #{line.split("#")[1]}')
                    puzzleNum = int(line.split('#')[1])
                    if puzzleNum != self.puzzle_number:
                        await message.channel.send_message(f'The current puzzle # is {self.puzzle_number}. Your submission for puzzle #{puzzleNum} has not been accepted.')
                        return
                elif '🟪' in line or '🟩' in line or '🟦' in line or '🟨' in line:
                    parseMsg.append(line)
            player.score = 0
            gotYellow = False
            gotGreen = False
            gotBlue = False
            gotPurple = False
            weight = 6
            for guess in parseMsg:
                if '🟨🟨🟨🟨' in guess:
                    gotYellow = True
                    player.score += weight # + difficulty tweak
                elif '🟩🟩🟩🟩' in guess:
                    gotGreen = True
                    player.score += weight + 1
                elif '🟦🟦🟦🟦' in guess:
                    gotBlue = True
                    player.score += weight + 2
                elif '🟪🟪🟪🟪' in guess:
                    gotPurple = True
                    player.score += weight + 3
                weight -= 1
            if gotYellow and gotGreen and gotBlue and gotPurple:
                player.succeededToday = True
            print(f'{get_log_time()}> Player {player.name} - score: {player.score}, succeeded: {player.succeededToday}')

            player.completedToday = True
            client.write_json_file()
            if player.succeededToday:
                await message.channel.send(f'{message.author.name} made all the connections with a score of {player.score}.\n')
            else:
                await message.channel.send(f'{message.author.name} did not make all the connections with a score of {player.score}.\n')
        except:
            print(f'{get_log_time()}> User {player.name} submitted invalid result message')
            await message.channel.send(f'{player.name}, you sent a Connections results message with invalid syntax. Please try again.')


    def tally_scores(self):
        if not self.players:
            print('No players to score')
            return

        print(f'{get_log_time()}> Tallying scores')
        winners = [] # list of winners - the one/those with the lowest score
        losers = [] # list of losers - people who didn't successfully guess the word
        results = [] # list of strings - the scoreboard to print out
        results.append('CONNECTIONS COMPLETE!\n\n**SCOREBOARD:**\n')

        self.write_json_file()
        return results + losers

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
async def on_message(message: discord.Message):
    # message is from this bot or not in dedicated text channel
    if message.channel.id != client.text_channel or message.author == client.user or client.scored_today:
        return

    if 'Connections' in message.content and 'Puzzle #' in message.content and ('🟨' in message.content or '🟩' in message.content or '🟦' in message.content or '🟪' in message.content):
        await message.delete()
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

        # set channel
        client.text_channel = int(message.channel.id)
        client.write_json_file()

        # process player's results
        await client.process(message, player)

    for player in client.players:
        if player.registered and (not player.completedToday or player.filePath == ''):
            return
    scoreboard = ''
    for line in client.tally_scores():
        scoreboard += line
    await message.channel.send(scoreboard)


@client.tree.command(name='register', description='Register for Connections tracking.')
async def register_command(interaction: Interaction):
    client.text_channel = int(interaction.channel.id)
    client.write_json_file()
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
    client.text_channel = int(interaction.channel.id)
    client.write_json_file()
    players_copy = client.players.copy()
    response = ''
    playerFound = False
    for player in players_copy:
        if player.name.strip() == interaction.user.name.strip():
            if player.registered:
                player.registered = False
                print(f'{get_log_time()}> Deregistered user {player.name}')
                response += 'You have been deregistered for Connections tracking.'
            else:
                client.players.remove(player)
                print(f'{get_log_time()}> Deleted data for user {player.name}')
                response += 'Your saved data has been deleted for Connections tracking.'
            client.write_json_file()
            playerFound = True
    if not playerFound:
        print(f'{get_log_time()}> Non-existant user {interaction.user.name.strip()} attempted to deregister')
        response += 'You have no saved data for Connections tracking.'
    await interaction.response.send_message(response)


@tasks.loop(seconds=1)
async def midnight_call():
    if not client.players:
        return

    channel = client.get_channel(int(client.text_channel))
    hour, minute = get_time()
    if client.sent_warning and hour == 23 and minute == 1:
        client.sent_warning = False
    if not client.sent_warning and not client.scored_today and hour == 23 and minute == 0:
        warning = ''
        for player in client.players:
            if player.registered and not player.completedToday:
                user = discord.utils.get(client.users, name=player.name)
                warning += f'{user.mention} '
        if warning != '':
            await channel.send(f'{warning}, you have one hour left to do the Connections!')
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
                user = discord.utils.get(client.users, name=player.name)
                if user:
                    shamed += f'{user.mention} '
                else:
                    print(f'{get_log_time()}> Failed to mention user {player.name}')
        if shamed != '':
            await channel.send(f'SHAME ON {shamed} FOR NOT DOING THE CONNECTIONS!')
        scoreboard = ''
        for line in client.tally_scores():
            scoreboard += line
        await channel.send(scoreboard)
        for player in client.players:
            if player.registered and player.filePath != '':
                await channel.send(content=f'__{player.name}:__', file=File(player.filePath))
                try:
                    os.remove(player.filePath)
                except OSError as e:
                    print(f'Error deleting {player.filePath}: {e}')
                player.filePath = ''

    client.scored_today = False
    everyone = ''
    for player in client.players:
        player.score = 0
        player.completedToday = False
        player.succeededToday = False
        user = discord.utils.get(client.users, name=player.name)
        if user:
            if player.registered:
                everyone += f'{user.mention} '
        else:
            print(f'{get_log_time()}> Failed to mention user {player.name}')
    await channel.send(f'{everyone}\nIt\'s time to find the Connections #{self.puzzle_number}!\nhttps://www.nytimes.com/games/connections')

client.run(discord_token)
