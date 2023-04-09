import discord
from discord import app_commands
import datetime
import openai
import os
from conversation import ConversationManager
import json
import wikipedia
import asyncio
from modes import WikipediaMode

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

def get_wiki_suggestions(topic):
    wikipedia.set_lang("en")
    try:
        return get_wiki_summary(topic)
    except wikipedia.exceptions.DisambiguationError as e:
        return get_wiki_summary(e.options[0])

async def begin_wikipedia_conversation(user, topic, summary, channel):
    conversation_manager.start_new_conversation(user, "You are a helpful AI assistant who knows everything Wikipedia says and more, so please answer any of my questions factually based on what Wikipedia says and knowing what you know.", mode=WikipediaMode(user, conversation_manager))
    response = conversation_manager.update_current_conversation(user, topic)
    await send(channel, response)  

for command in commands:
    def command_maker(system, user):
        async def interaction(interaction):
            await interaction.response.defer()
            conversation_manager.start_new_conversation(interaction.user, system)
            response = conversation_manager.update_current_conversation(interaction.user, user)
            await send(interaction.followup, response)
        return interaction
    tree.add_command(discord.app_commands.Command(name=command["command"], description=command["description"], callback=command_maker(command["system"], command["user"])))

num_map = {10:'\u0030\ufe0f\u20e3',1:'\u0031\ufe0f\u20e3',2:'\u0032\ufe0f\u20e3',3:'\u0033\ufe0f\u20e3',4:'\u0034\ufe0f\u20e3',5:'\u0035\ufe0f\u20e3',6:'\u0036\ufe0f\u20e3',7:'\u0037\ufe0f\u20e3',8:'\u0038\ufe0f\u20e3',9:'\u0039\ufe0f\u20e3'}
inv_map = {v: k for k, v in num_map.items()}

@tree.command(name="wiki", description="Searches Wikipedia for a summary of a topic")
async def wiki_command(interaction, topic: str):
    await interaction.response.defer()
    try:
        summary = get_wiki_summary(topic)
        await begin_wikipedia_conversation(interaction.user, topic, summary, interaction.channel)
    except wikipedia.exceptions.DisambiguationError as e:
        if len(e.options) > 10:
            e.options = e.options[:10]
        options = "\n".join([f"{i}. {option}" for i, option in enumerate(e.options, start=1)])
        await interaction.followup.send("Please choose one of the following options:")
        message = await interaction.followup.send(options)
        for i in range(1, len(e.options)+1):
            await message.add_reaction(num_map[i])
        async def await_reaction(option_list):
            reaction, _ = await client.wait_for('reaction_add', check=lambda reaction, user: user == interaction.user and reaction.message == message and reaction.emoji in inv_map)
            if reaction.emoji not in inv_map:
                return
            num = inv_map[reaction.emoji]
            option = option_list[num-1]
            await interaction.channel.send(f"One moment please, consulting Wikipedia about {option}...")
            summary = get_wiki_suggestions(option)
            await begin_wikipedia_conversation(interaction.user, option, summary, interaction.channel)
        asyncio.create_task(await_reaction(e.options))
        return
    
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
