import discord
from discord import app_commands
import datetime
import openai
import os
from conversation import ConversationManager
import json
import wikipedia
import asyncio

openai.api_key = os.environ.get("OpenAIAPI-Token")
model_engine = "gpt-3.5-turbo"

intents = discord.Intents(messages=True, guilds=True, message_content=True, members=True, guild_reactions=True, dm_reactions=True, presences=True, reactions=True, typing=True, voice_states=True, webhooks=True)
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
conversation_manager = ConversationManager()

commands = json.load(open("commands.json", "r"))

def split_into_chunks(text, chunk_size=2000):
    # Split text into chunks of size chunk_size bt keeping whole words
    chunks = []
    while len(text) > chunk_size:
        last_space = text[:chunk_size].rfind(" ")
        chunks.append(text[:last_space])
        text = text[last_space+1:]
    chunks.append(text)
    return chunks

async def send(channel, text):
    # Send text to channel, splitting it into chunks if necessary
    for chunk in split_into_chunks(text):
        await channel.send(chunk)


def get_wiki_summary(topic):
    wikipedia.set_lang("en")
    return wikipedia.summary(wikipedia.search(topic)[0])
    

for command in commands:
    def command_maker(system, user):
        async def interaction(interaction):
            await interaction.response.defer()
            conversation_manager.start_new_conversation(interaction.user, system)
            response = conversation_manager.update_current_conversation(interaction.user, user)
            await interaction.followup.send(response)
        return interaction
    tree.add_command(discord.app_commands.Command(name=command["command"], description=command["description"], callback=command_maker(command["system"], command["user"])))
    

num_map = {10: '0️⃣', 1: '1️⃣', 2: '2️⃣', 3: '3️⃣', 4: '4️⃣', 5: '5️⃣', 6: '6️⃣',7: '7️⃣',8: '8️⃣', 9: '9️⃣' }
inv_map = {v: k for k, v in num_map.items()}

@tree.command(name="wiki", description="Searches Wikipedia for a summary of a topic")
async def wiki_command(interaction, topic: str):
    await interaction.response.defer()
    try:
        summary = get_wiki_summary(topic)
    except wikipedia.exceptions.DisambiguationError as e:
        if len(e.options) > 10:
            e.options = e.options[:10]
        options = ""
        i = 1
        for option in e.options:
            options += str(i) + ". " + option + "\n"
            i = i + 1
        await interaction.followup.send("I'm not sure what you mean. Please choose one of the following options:")
        message = await interaction.channel.send(options)
        i = 1
        for option in e.options:
            await message.add_reaction(num_map[i])
            i = i + 1
        async def await_reaction(option_list):
            reaction, user = await client.wait_for('reaction_add', check=lambda reaction, user: user == interaction.user and reaction.message == message)
            num = inv_map[reaction.emoji]
            option = option_list[num-1]
            await interaction.channel.send("One moment please, consulting Wikipedia about " + option + "...")
            summary = get_wiki_summary(option)
            conversation_manager.start_new_conversation(interaction.user, "Wikipedia says the following about " +  option + ": " +  summary + "\n You are a helpful AI assistant who knows everything Wikipedia said and more, so please answer any of my questions factually based on what Wikipedia says and knowing what you know.")
            response = conversation_manager.update_current_conversation(interaction.user, "Please briefly summarize what Wikipedia said about " + option + ", then offer to engage in a discussion on the topic as an expert.")
            await send(interaction.channel, response)
        asyncio.create_task(await_reaction(e.options))
        return
    conversation_manager.start_new_conversation(interaction.user, "Wikipedia says the following about " + topic + ": " +  summary + "\n You are a helpful AI assistant who knows everything Wikipedia said and more, so please answer any of my questions factually based on what Wikipedia says and knowing what you know.")
    response = conversation_manager.update_current_conversation(interaction.user, "Please briefly summarize what Wikipedia said about " + topic + ", then offer to engage in a discussion on the topic as an expert.")
    await send(interaction.followup, response)

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
    await tree.sync(guild=interaction.guild)
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
