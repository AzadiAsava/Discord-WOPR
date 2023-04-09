import discord
from discord import app_commands
import datetime
import openai
import os
from conversation import ConversationManager
import json

openai.api_key = os.environ.get("OpenAIAPI-Token")
model_engine = "gpt-3.5-turbo"

intents = discord.Intents(messages=True, guilds=True, message_content=True)
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
conversation_manager = ConversationManager()

commands = json.load(open("commands.json", "r"))

for command in commands:
    def command_maker(system, user):
        async def interaction(interaction):
            await interaction.response.defer()
            conversation_manager.start_new_conversation(interaction.user, system)
            response = conversation_manager.update_current_conversation(interaction.user, user)
            await interaction.followup.send(response)
        return interaction
    tree.add_command(discord.app_commands.Command(name=command["command"], description=command["description"], callback=command_maker(command["system"], command["user"])))

    
@tree.command(name = "now", description = "Displays current date and time") #Add the guild ids in which the slash command will appear. If it should be in all, remove the argument, but note that it will take some time (up to an hour) to register the command if it's for all guilds.
async def now_command(interaction):
    now = datetime.datetime.now()
    nowstr = now.strftime('%m-%d-%Y-%H:%M:%S')
    await interaction.response.send_message(nowstr)

@tree.command(name = "new", description = "Clears the current conversation's context") #Add the guild ids in which the slash command will appear. If it should be in all, remove the argument, but note that it will take some time (up to an hour) to register the command if it's for all guilds.
async def new_command(interaction):    
    conversation_manager.start_new_conversation(interaction.user)
    await interaction.response.send_message("New context created.")


@tree.command(name = "shab", description = "Displays Shabbat times") #Add the guild ids in which the slash command will appear. If it should be in all, remove the argument, but note that it will take some time (up to an hour) to register the command if it's for all guilds.
async def shab_command(interaction):
    await interaction.response.defer()
    now = datetime.datetime.now()
    nowstr = now.strftime('%m-%d-%Y-%H:%M:%S')
    prompt = 'The current date is' + nowstr  + '. You are a sophisticated language model capable of calculating the candle-lighting time and havdalah times for this coming Shabbat (Jewish Sabbath) in New York City. Candle lighting time is 18 minutes prior to sunset, and havdalah is at the time that three stars are visible in the night sky. Please display the output in the following format: On Friday, [date of upcoming erev Shabbat], Shabbat candle-lighting time will be at [time]. Havdalah time will be at [time] on Saturday, [date of the end of the upcoming Shabbat]." Please only display the requested format.'
    conversation_manager.start_new_conversation(interaction.user, prompt)
    response = conversation_manager.update_current_conversation(interaction.user, "Go ahead and start by giving me the candle-lighting time and havdalah times for this coming Shabbat (Jewish Sabbath) in New York City.")
    await interaction.followup.send(response)

@tree.command(name='sync', description='Owner only')
async def sync(interaction: discord.Interaction):
    await interaction.response.defer()
    await tree.sync()
    await interaction.followup.send('Synced.')

@tree.command(name='reload', description='Owner only')
async def reload(interaction: discord.Interaction):
    await interaction.response.defer()
    commands = json.load(open("commands.json", "r"))
    for command in commands:
        def command_maker(system, user):
            async def interaction(interaction):
                await interaction.response.defer()
                conversation_manager.start_new_conversation(interaction.user, system)
                response = conversation_manager.update_current_conversation(interaction.user, user)
                await interaction.followup.send(response)
            return interaction
        tree.add_command(discord.app_commands.Command(name=command["command"], description=command["description"], callback=command_maker(command["system"], command["user"])))
    await tree.sync()
    await interaction.followup.send('Reloaded.')

@client.event
async def on_ready():
    print('Logged in as {0.user}'.format(client))
    await tree.sync()

@client.event
async def on_message(message): 
    if message.author == client.user:
        return
    if message.author.bot:
        return
    content = conversation_manager.update_current_conversation(message.author, message.content)
    await message.channel.send(content)
      
token = os.environ.get("Discord-Token", None)
if token is None:
    raise ValueError("No Discord token found in the environment variables. Please set the environment variable 'Discord-Token' to your Discord bot token.")
client.run(token)
