from __future__ import annotations
from abc import abstractmethod
import asyncio
from collections import OrderedDict
from typing import AsyncGenerator, Tuple, Union, Optional
from chatgpt import extract_preferences, extract_urls, find_similar_conversations, get_is_request_to_change_topics, get_new_or_existing_conversation, get_wolfram_query, merge_conversations, get_completion
from chatgpt import extract_topic, summarize, summarize_knowledge
import wikipedia
from typing import Optional, Callable, List
import datetime
from uuid import uuid4

from wolframalpha_client import query_wolfram



wikipedia.set_lang("en")
def get_wiki_summary(topic : str) -> str:
    return wikipedia.summary(wikipedia.search(topic)[0])
def get_wiki_suggestion(topic : str) -> str:
    try:
        return "Wikipedia on " + topic + ": " + get_wiki_summary(topic)
    except wikipedia.exceptions.DisambiguationError as e:
        summary = ""
        for option in e.options[:5]:
            try:
                summary += "Wikipedia on " + option + ": " + get_wiki_summary(option) + "\n\n"
            except wikipedia.exceptions.DisambiguationError:
                continue
        return summary    
class Mode:
    def __init__(self, name : str, user : int = -1):
        self.name = name
        self.user = user
    @abstractmethod
    async def __call__(self, user : int, conversation : "Conversation", db : "Database") -> str:
        raise NotImplementedError(f"{type(self)} does not implement __call__.")
class DefaultMode(Mode):
    def __init__(self, user : int = -1):
        super().__init__("Default Mode", user)
    async def __call__(self, message : str, conversation : "Conversation", db : "Database") -> str:
        return message
class WikipediaMode(Mode):
    def __init__(self, user : int):
        super().__init__("Wikipedia Mode", user)
    async def __call__(self, message : str, conversation : "Conversation", db : "Database") -> str:
        topic = asyncio.run(extract_topic(message))
        summary = get_wiki_suggestion(topic)
        conversation.add_system("As a point of reference Wikipedia says the following about " + topic + " (may be off topic):\n" +  summary)
        return message

class MeanMode(Mode):
    def __init__(self, user : int):
        super().__init__("Mean Mode", user)
    async def __call__(self, message : str, conversation : "Conversation", db : "Database") -> str:
        conversation.add_system("Remember to be extra rude, insulting, and mean in your responses.")
        return message
    
import pytz
class DateTimeAwareMode(Mode):
    def __init__(self, user : int):
        super().__init__("DateTime Aware Mode", user)
    async def __call__(self, message : str, conversation : "Conversation", db : "Database") -> str:
        timezone = db.get_preference(self.user, "timezone", "America/New_York")
        formatted_time = datetime.datetime.now(pytz.timezone(timezone)).strftime("%m/%d/%Y, %I:%M:%S %p")
        conversation.set_system("datetime", "The current date and time is now " + formatted_time + ".")
        return message

class UserPreferenceAwareMode(Mode):
    def __init__(self, user : int):
        super().__init__("User Preference Aware Mode", user)    
    async def __call__(self, message : str, conversation : "Conversation", db : "Database") -> str:
        preferences = "Remember the following details in this conversation:\n"
        for key, value in db.get_preferences(self.user).items():
            preferences += key + ": " + value + "\n"
        conversation.set_system("preferences", preferences)
        return message

        
class DatasourceAwareMode(Mode):
    def __init__(self, user : int):
        super().__init__("Datasource Aware Mode", user)
    async def __call__(self, message : str, conversation : "Conversation", db : "Database") -> str:
        urls = await extract_urls(message)
        if len(urls) == 0:
            return message
        for url in urls:
            datasources = get_data_sources(url)
            if len(datasources) == 0:
                continue
            for datasource in datasources:
                for data in await datasource.query():
                    conversation.messages.extend([{"role":"user", "content": data[0] + " from " + url.get("url", "") + " says the following about " + url.get("query", "") + ":\n" + await summarize(data[1])}])
        return message
        
class KnowledgeAwareMode(Mode):
    def __init__(self, user : int, update_interval : int = 3):
        super().__init__("Knowledge Aware Mode", user)
        self.update_counter = 0
        self.update_interval = update_interval
    async def __call__(self, message : str, conversation : "Conversation", db : "Database") -> str:
        if self.update_counter >= self.update_interval:
            self.update_counter = 0
            conversations = db.get_conversations(self.user)
            for convo in conversations.values():
                if convo.id == conversation.id:
                    convo = conversation
                convo = await compress_conversation(convo)
                db.set_conversation(self.user, convo)
            summary = ""
            for i, convo in enumerate(conversations.values()):
                summary += "Conversation " + str(i) + ": " + convo.summary + "\n\n"
            similar = await find_similar_conversations(summary)
            while similar is not None:
                conversations = db.get_conversations(self.user)
                first_conversation = conversations[list(conversations.keys())[similar[0]]]
                second_conversation = conversations[list(conversations.keys())[similar[1]]]
                if first_conversation.id == conversation.id:
                    first_conversation = conversation
                if second_conversation.id == conversation.id:
                    second_conversation = conversation
                merged_conversation = await merge_conversations(str(first_conversation), str(second_conversation))
                first_conversation.messages = merged_conversation
                first_conversation.summary = await summarize(str(first_conversation))
                db.set_conversation(self.user, first_conversation)
                db.delete_conversation(self.user, second_conversation.id)
                conversations = db.get_conversations(self.user)
                summary = ""
                for i, convo in enumerate(conversations.values()):
                    summary += "Conversation " + str(i) + ": " + convo.summary + "\n\n"
                similar = await find_similar_conversations(summary)
                if second_conversation.id == conversation.id:
                    conversation = first_conversation
            db.set_knowledge(self.user, await summarize_knowledge(summary))
        self.update_counter += 1
        conversation.set_system("knowledge", "Remember the following details about the past in this conversation:\n" + db.get_knowledge(self.user))
        return message


class ConversationManager:
    def __init__(self, db : Database):
        self.conversations = {}
        self.db = db
    async def update_current_conversation(self, user : int, user_input : str) -> str:
        return await self.update_conversation(user, user_input)
    async def update_conversation(self, user : int, user_input : str, conversation : Optional[Conversation] = None) -> str:
        if conversation is None:
            conversation = self.get_current_conversation(user)
        if conversation is None:
            raise ValueError("No conversation found for user.")
        await conversation.add_user(user_input, self.db)
        content = await get_completion(conversation.get_conversation())
        conversation.add_assistant(content)
        conversation.summary = await summarize(str(conversation))
        self.db.set_conversation(user, conversation)
        return content
    def add_conversation(self, user: int, conversation : Conversation):
        self.db.set_conversation(user, conversation)    
    def get_conversations(self, user: int):
        return self.db.get_conversations(user)
    def get_conversation_summary(self, user) -> str:
        all_conversations = self.get_conversations(user)
        conversations = [f"{i}. {convo.summary}" for i, convo in enumerate(all_conversations.values(), start=0)]
        return "\n".join(conversations)    
    def get_current_conversation(self, user: int) -> Optional[Conversation]:
        current_conversation = self.db.get_current_conversation(user)
        conversations = self.get_conversations(user)
        if current_conversation is None or current_conversation not in conversations:
            self.switch_to_conversation(user, 0)
            current_conversation = self.db.get_current_conversation(user)
            if current_conversation is None:
                return None           
        return conversations[current_conversation]
    def delete_conversation(self, user: int, conversation: Conversation):
        self.db.delete_conversation(user, conversation.id)
    def set_conversation(self, user: int, conversation: Conversation):
        self.db.set_conversation(user, conversation)
    def switch_to_conversation(self, user: int, index: int):
        all_conversations = self.get_conversations(user)
        if index >= len(all_conversations):
            return
        self.db.set_current_conversation(user, all_conversations[list(all_conversations.keys())[index]].id)
    def start_new_conversation(self, user : int, system : str="You are a helpful AI assistant.", modes : Union[List[Mode], List[Callable]] = []):
        convo = Conversation(user, system, modes)
        self.add_conversation(user, convo)
        self.db.set_current_conversation(user, convo.id)
        return convo
    
async def compress_conversation(conversation : Conversation, keep_last:int=8) -> Conversation:
    if len(conversation.messages) <= keep_last * 1.5:
        return conversation
    revised_convo = await summarize(str(conversation))
    conversation.messages = [{"role":"system","content":"There was a part of conversation that was too long to display. Here is a summary of it:\n" + revised_convo}, *conversation.messages[-keep_last:]]
    conversation.summary = await summarize(str(conversation))
    return conversation

async def wolfram_query(query : str) -> Tuple[str, Optional[str]]:
    best_query = await get_wolfram_query(query)
    result = await query_wolfram(best_query)
    return best_query, result

async def echo_message(message : str, conversation : "Conversation", db : "Database") -> AsyncGenerator[str, None]:
    yield message

async def compute_math(message : str, conversation : "Conversation", db : "Database") -> AsyncGenerator[str, None]:
    query, result = await wolfram_query(message)
    if result is None:
        yield message
        raise StopIteration
    yield "I had said: " + message
    yield "Wolfram|Alpha, when asked asked about " + query + ", said: \"" + result + "\""
    yield "Please summarize what Wolfram|Alpha said about " + query + " for me."

async def external_query(message : str, conversation : "Conversation", db : "Database") -> AsyncGenerator[str, None]:
    yield message

def get_default_modes(user):
    modes = [
        DateTimeAwareMode(user),
        UserPreferenceAwareMode(user),
        KnowledgeAwareMode(user),
        DatasourceAwareMode(user),
    ]
    return modes

class ConversationChangeException(Exception):
    pass

async def topic_change(message : str, conversation : Conversation, db : Database) -> AsyncGenerator[str, None]:
    modes = get_default_modes(conversation.user)
    if len(db.get_conversations(conversation.user)) == 0:
        db.set_current_conversation(conversation.user, conversation.id)
        db.set_conversation(conversation.user, conversation)
    conversations = db.get_conversations(conversation.user)
    summaries = ""
    for i, convo in enumerate(conversations.values(), start=0):
        summaries += f"{i}. {convo.summary}\n"
    conversation_index = await get_new_or_existing_conversation(summaries, message)
    if conversation_index == -1:
        new_conversation = Conversation(conversation.user, "You are a helpful AI assistant.", modes)
        db.set_current_conversation(conversation.user, new_conversation.id)
        raise ConversationChangeException
    elif list(conversations.values())[conversation_index].id == conversation.id:
        yield message
        raise StopIteration
    else:
        db.set_current_conversation(conversation.user, list(conversations.values())[conversation_index].id)
        raise ConversationChangeException

async def remember(message : str, conversation : Conversation, db : Database) -> AsyncGenerator[str, None]:
    preferences = await extract_preferences(message)
    if len(preferences) == 0:
        yield message
        raise StopIteration
    for k,v in preferences.items():
        db.set_preference(conversation.user, k, v)
    yield "I'm about to ask you to remember something. I know you can't, but when I ask you to remember something, just say you will remember it and summarize it for me. DO NOT REMIND ME THAT YOU CAN'T ACTUALLY REMEMBER IT. Just say you will."
    yield message

async def forget(message : str, conversation : Conversation, db : Database) -> AsyncGenerator[str, None]:
    yield message

async def datasource_description(message : str, conversation : Conversation, db : Database) -> AsyncGenerator[str, None]:
    yield message

async def summarize_command(message : str, conversation : Conversation, db : Database) -> AsyncGenerator[str, None]:
    yield await summarize(message)

async def docker(message : str, conversation : Conversation, db : Database) -> AsyncGenerator[str, None]:
    yield "Booting up a docker container for you now."
    import docker
    client = docker.from_env()
    container : docker.DockerClient = client.containers.run(message, detach=True)
    container.start()
    container.wait()
    for line in container.logs(stream=True):
        yield line.decode("utf-8")

option_map : List[Tuple[str, Callable[...,AsyncGenerator[str, None]]]] = [
    ("None of the above.", echo_message),
    ("A request to compute something using math.", compute_math),
    ("A question that can be answered by an external datasource, or a request to get data from an external datasource.", external_query),
    ("A question ChatGPT can answer without any external knowledge.", echo_message),
    ("An explicit request to change topics.", topic_change),
    ("An explicit request to remember something.", remember),
    ("A description of an api or datasource that one might make a request against.", datasource_description),
    ("An explicit request to forget or no longer remember something.", forget),
    ("An agreement or disagreement like yes, no, sure, or ok.", echo_message),
    ("A pleasantry like Hello or How Are You?", echo_message),
    ("A request to write code, or a question about coding or programming.", echo_message),
    ("A summary or description of a news story or article abstract.", echo_message),
    ("Something having to do with docker or dockerfiles.", echo_message),
    ("A request or command to do something like run a script or execute a command on a linux terminal or run a command on a windows terminal.", echo_message),
    ("A list of data in need of structuring or text that might need summarizing.", summarize_command),
    ("A summary or description of a news story or article abstract.", echo_message),
    ("Something having to do with docker or dockerfiles.", docker)
    ]


from db import Database
