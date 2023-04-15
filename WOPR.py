import asyncio
import datetime
from typing import Optional
import discord
from discord import app_commands, SelectMenu, SelectOption
import openai
import os
from conversation import ConversationManager, DatasourceAwareMode, compress_conversation
import json
from conversation import get_wiki_summary, KnowledgeAwareMode, DateTimeAwareMode, UserPreferenceAwareMode
from chatgpt import get_is_request_to_change_topics, get_new_or_existing_conversation, merge_conversations, summarize, summarize_knowledge, find_similar_conversations
from db import Database
import wikipedia

openai.api_key = os.environ.get("OpenAIAPI-Token")
model_engine = "gpt-3.5-turbo"

db = Database("db.json")

intents = discord.Intents(messages=True, guilds=True, message_content=True, members=True, guild_reactions=True, dm_reactions=True, presences=True, reactions=True, typing=True, voice_states=True, webhooks=True)
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
conversation_manager = ConversationManager(db)

commands = json.load(open("commands.json", "r"))

def get_default_modes(user):
    modes = [
        DateTimeAwareMode(user),
        UserPreferenceAwareMode(user),
        KnowledgeAwareMode(user),
        DatasourceAwareMode(user),
    ]
    return modes

def get_preference(user, preference, default="") -> Optional[str]:
    return db.get_preference(user, preference, default)

def get_preferences(user: int) -> dict:
    return db.get_preferences(user)

def set_preference(user : int, preference, value) -> None:
    db.set_preference(user, preference, value)

def remove_preference(user, preference):
    db.delete_preference(user, preference)

def split_into_chunks(text, chunk_size=2000):
    chunks = []
    while len(text) > chunk_size:
        last_space = text[:chunk_size].rfind(" ")
        chunks.append(text[:last_space])
        text = text[last_space+1:]
    chunks.append(text)
    return chunks

async def send(channel, text):
    for chunk in split_into_chunks(text):
        await channel.send(chunk)

async def begin_wikipedia_conversation(user, topic, channel):
    conversation_manager.start_new_conversation(user, "You are a helpful AI assistant who knows everything Wikipedia says and more, so please answer any of my questions factually based on what Wikipedia says and knowing what you know.", modes=get_default_modes(user)) 
    response = await conversation_manager.update_current_conversation(user, topic)
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

time_zones = {
    "Etc/GMT+12": "International Date Line West (UTC-12)",
    "Pacific/Midway": "Midway Island (UTC-11)",
    "Pacific/Honolulu": "Hawaii Standard Time (UTC-10)",
    "America/Anchorage": "Alaska Standard Time (UTC-9)",
    "America/Los_Angeles": "Pacific Standard Time (UTC-8)",
    "America/Denver": "Mountain Standard Time (UTC-7)",
    "America/Chicago": "Central Standard Time (UTC-6)",
    "America/New_York": "Eastern Standard Time (UTC-5)",
    "America/Halifax": "Atlantic Standard Time (UTC-4)",
    "America/Sao_Paulo": "Brasília Time (UTC-3)",
    "Atlantic/South_Georgia": "South Georgia Time (UTC-2)",
    "Etc/UTC": "Coordinated Universal Time (UTC)",
    "Europe/London": "Greenwich Mean Time (UTC+0)",
    "Europe/Berlin": "Central European Time (UTC+1)",
    "Europe/Helsinki": "Eastern European Time (UTC+2)",
    "Europe/Moscow": "Moscow Standard Time (UTC+3)",
    "Asia/Dubai": "Gulf Standard Time (UTC+4)",
    "Asia/Kolkata": "Indian Standard Time (UTC+5:30)",
    "Asia/Dhaka": "Bangladesh Time (UTC+6)",
    "Asia/Rangoon": "Myanmar Time (UTC+6:30)",
    "Asia/Bangkok": "Indochina Time (UTC+7)",
    "Asia/Shanghai": "China Standard Time (UTC+8)",
    "Asia/Tokyo": "Japan Standard Time (UTC+9)",
    "Australia/Brisbane": "Australian Eastern Standard Time (UTC+10)",
    "Pacific/Auckland": "New Zealand Standard Time (UTC+12)"
}

@tree.command(name="summary", description="Get a summary of your conversations")
async def summary_command(interaction):
    await interaction.response.send_message(conversation_manager.get_conversation_summary(interaction.user.id))

@tree.command(name="knowledge", description="Get a summary of your knowledge")
async def knowledge_command(interaction):
    await interaction.response.defer()
    await interaction.followup.send(summarize_knowledge(conversation_manager.get_conversation_summary(interaction.user.id)))

@tree.command(name="similar", description="Get a summary of your similar conversations")
async def similar_command(interaction):
    await interaction.response.defer()
    await interaction.followup.send(await find_similar_conversations(conversation_manager.get_conversation_summary(interaction.user.id)) or "No similar conversations found.")

@tree.command(name="compress", description="Compresses your conversations")
async def compress_command(interaction):
    await interaction.response.defer()
    conversations = list(conversation_manager.get_conversations(interaction.user.id).values())
    for conversation in conversations:
        conversation = await compress_conversation(conversation)
        conversation_manager.set_conversation(interaction.user.id, conversation)
    await interaction.followup.send(f"Compressed conversations: {len(conversations)}")
        

@tree.command(name="merge", description="Merge two conversations")
async def merge_command(interaction, c1: int, c2: int):
    await interaction.response.defer()
    async def merge():
        conversations = list(conversation_manager.get_conversations(interaction.user.id).values())
        first_conversation = conversations[c1]
        second_conversation = conversations[c2]
        merged = await merge_conversations(str(first_conversation), str(second_conversation))
        first_conversation.messages = merged
        first_conversation.summary = await summarize(str(first_conversation))
        conversation_manager.set_conversation(interaction.user.id, first_conversation)
        conversation_manager.delete_conversation(interaction.user.id, second_conversation)
        await interaction.followup.send(f"Merged conversations {c1} and {c2}")
    asyncio.create_task(merge())

@tree.command(name="remember", description="Sets a preference for the AI to always remember")
async def always_command(interaction, preference: str, value: str):
    set_preference(interaction.user.id, preference, value)
    await interaction.response.send_message(f"Preference {preference} set to {value}")

@tree.command(name="forget", description="Forgets a preference")
async def forget_command(interaction):
    view = discord.ui.View()
    view.add_item(discord.ui.Select(placeholder="Preference", options=[SelectOption(label=preference + ": " + value, value=preference) for preference, value in get_preferences(interaction.user.id).items()]))
    await interaction.response.defer()
    message = await interaction.followup.send("Please choose a preference to forget:", view=view)
    async def respond_to_select(user, message):
        interaction = await client.wait_for("interaction", check=lambda i: i.user == user and i.data is not None and i.message == message and len(i.data.get("values", [])) > 0)
        if interaction.data is None or interaction.message is None or len(interaction.data.get("values", [])) == 0:
            return
        preference = interaction.data.get("values", [])[0]
        remove_preference(interaction.user, preference)
        await interaction.response.edit_message(content=f"Preference {preference} forgotten", view=None)
    asyncio.create_task(respond_to_select(interaction.user, message))

@tree.command(name="timezone", description="Sets your timezone for the datetime command")
async def timezone_command(interaction):
    view = discord.ui.View()
    view.add_item(discord.ui.Select(placeholder="Select timezone", options=[SelectOption(label=value, value=key) for key, value in time_zones.items()]))
    await interaction.response.defer()
    message = await interaction.followup.send("Please choose your timezone:", view=view)
    async def respond_to_select(user, message, id):
        interaction = await client.wait_for("interaction", check=lambda i: i.user == user and i.data is not None and i.message == message and len(i.data.get("values", [])) > 0)
        if interaction.data is None or interaction.message is None or len(interaction.data.get("values", [])) == 0:
            return
        timezone = interaction.data.get("values", [])[0]
        await interaction.message.edit(content="Your timezone has been set to: " + time_zones[timezone], view=None)
        set_preference(user.id, "timezone", str(timezone))
    asyncio.create_task(respond_to_select(interaction.user, message, id))

@tree.command(name="wiki", description="Searches Wikipedia for a summary of a topic")
async def wiki_command(interaction, topic: str):
    await interaction.response.defer()
    try:
        get_wiki_summary(topic)
        await begin_wikipedia_conversation(interaction.user, "Summarize the Wikipedia article on: " + topic, interaction.channel)
    except wikipedia.exceptions.DisambiguationError as e:
        view = discord.ui.View()
        view.add_item(discord.ui.Select(options=[SelectOption(label=option, value=option) for option in e.options[:25]], placeholder="Select an option"))
        message = await interaction.followup.send("Please choose one of the following options:", view=view)
        async def respond_to_select(user, message):
            interaction = await client.wait_for("interaction", check=lambda i: i.user == user and i.message == message and i.data is not None and len(i.data.get("values", [])) > 0)
            if interaction.data is None:
                return
            topic = interaction.data.get("values", [])[0]
            await message.edit(content="Consulting Wikipedia on: " + topic + "...", view=None)
            await begin_wikipedia_conversation(user, "Summarize the wikipedia article on: " + topic, message.channel)
        asyncio.create_task(respond_to_select(interaction.user, message))

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
    response = await conversation_manager.update_current_conversation(interaction.user, "Go ahead and start by giving me the candle-lighting time and havdalah times for this coming Shabbat (Jewish Sabbath) in New York City.")
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
                conversation_manager.start_new_conversation(interaction.user.id, system)
                response = await conversation_manager.update_current_conversation(interaction.user.id, user)
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
    async def handle_request():
        modes = get_default_modes(message.author.id)
        if len(conversation_manager.get_conversations(message.author.id)) == 0:
            conversation_manager.start_new_conversation(message.author.id, modes=modes)
        else:
            topic_change = await get_is_request_to_change_topics(conversation_manager.get_current_conversation(message.author.id).summary, message.content)
            if topic_change:
                conversation = await get_new_or_existing_conversation(conversation_manager.get_conversation_summary(message.author.id), message.content)
                if conversation == -1:
                    conversation_manager.start_new_conversation(message.author.id, modes=modes)
                elif conversation == 0:
                    pass
                else:
                    conversation_manager.switch_to_conversation(message.author.id, conversation)
        content = await conversation_manager.update_current_conversation(message.author.id, message.content)
        await send(message.channel, content)
    asyncio.create_task(handle_request())

token = os.environ.get("Discord-Token", None)
if token is None:
    raise ValueError("No Discord token found in the environment variables. Please set the environment variable 'Discord-Token' to your Discord bot token.")
client.run(token)
