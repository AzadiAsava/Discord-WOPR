from __future__ import annotations
from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import AsyncGenerator, List, Optional, Union
from uuid import uuid4
import discord

@dataclass
class Message:
    user:User
    text:str
    context:str
    channel:Optional[Channel]
    guild:Optional[Guild]
    followup:List[str]
    datetime:datetime
    discord_message_id:int
    id:str = str(uuid4().hex)
    @staticmethod
    def from_message(message : discord.Message, context : str) -> Message:
        if isinstance(message.author, discord.User):
            #cast the author to a discord.user
            user = User.from_discord_user(message.author)
            return Message(user,
                       message.content,
                       context,
                       Channel.from_discord_channel(message.channel), 
                       Guild.from_discord_guild(message.guild),
                       [],
                       message.created_at,
                       message.id)
        elif isinstance(message.author, discord.Member):
            user = User.from_discord_user(message.author._user)
            return Message(user,
                       message.content,
                       context,
                       Channel.from_discord_channel(message.channel), 
                       Guild.from_discord_guild(message.guild),
                       [],
                       message.created_at,
                       message.id)
        else:
            raise NotImplementedError("Not implemented")
        

@dataclass
class Channel:
    id:str
    @staticmethod
    def from_discord_channel(channel : discord.abc.MessageableChannel) -> Channel:
        return Channel(
            id=str(channel.id),
        )
    def get_discord_channel(self, discord_client:discord.Client) -> Optional[Union[discord.abc.PrivateChannel, discord.Thread, discord.VoiceChannel, discord.StageChannel, discord.ForumChannel, discord.TextChannel, discord.CategoryChannel]]:
        return discord_client.get_channel(int(self.id))
@dataclass
class Guild:
    id:str
    name:str
    @staticmethod
    def from_discord_guild(guild:Optional[discord.Guild]) -> Optional[Guild]:
        if guild is None:
            return None
        return Guild(
            id=str(guild.id),
            name=guild.name
        )
    def get_discord_guild(self, discord_client:discord.Client) -> Optional[discord.Guild]:
        return discord_client.get_guild(int(self.id))
@dataclass
class User:
    id:str
    name:str
    display_name:str
    discriminator:str
    avatar:Optional[discord.Asset]
    bot:bool
    system:bool
    @staticmethod
    def from_discord_user(user:discord.User) -> User:
        return User(
            id=str(user.id),
            name=user.name,
            display_name=user.display_name,
            discriminator=user.discriminator,
            avatar=user.avatar,
            bot=user.bot,
            system=user.system
        )
    def get_discord_user(self, discord_client:discord.Client) -> Optional[discord.User]:
        return discord_client.get_user(int(self.id))
    
@dataclass
class Conversation:
    system:dict[str,str]
    messages:List[dict[str, str]]
    summary:str
    id:str = str(uuid4().hex)
    @staticmethod
    def new_conversation(system:str = "You are a helpful AI assistant.") -> Conversation:
        return Conversation({"system":system},[], "The start of a brand new conversation")
    def set_system(self, system : str, message : str = "") -> None:
        self.system = {"name":system,"message":message}
    def delete_system(self, system : str) -> None:
        del self.system[system]
    def get_conversation(self) -> List[dict[str, str]]:
        messages = [{"role":"system","content":value} for value in self.system.values()]
        messages.extend(self.messages)
        return messages
    def add_user(self, user : str) -> None:
        self.messages.append({"role":"user","content":user})
    def add_system(self, system : str) -> None:
        self.messages.append({"role":"system","content":system})
    def add_assistant(self, assistant : str) -> None:
        self.messages.append({"role":"assistant","content":assistant})
    def delete_last_message(self) -> None:
        self.messages.pop()
    def __str__(self) -> str:
        convo = ""
        for message in self.messages:
            convo += message["role"] + ": " + message["content"] + "\n"
        return convo

@dataclass
class UserValues:
    user:User
    values:dict[str,str]
    def get_value(self, key : str) -> str:
        return self.values[key]
    def set_value(self, key : str, value : str) -> None:
        self.values[key] = value
    def delete_value(self, key : str) -> None:
        del self.values[key]
    def __str__(self) -> str:
        value = ""
        for key in self.values:
            value += key + ": " + self.values[key] + "\n"
        return value

class UserSettings(UserValues):
    pass

class UserPreferences(UserValues):
    pass

@dataclass
class UserConversation:
    user_id:str
    conversation:Conversation
@dataclass
class UserCurrentConversation:
    user_id:str
    conversation_id:str

@dataclass
class DataSource:
    id:str
    name:str
    url:str
    roles:List[str]
    @abstractmethod
    async def query(self, query : str, context:Optional[dict[str,str]]) -> AsyncGenerator[str, None]:
        pass

@dataclass
class ExternalDataSource(DataSource):
    endpoints:List[Endpoint]
    
@dataclass
class QueryParam:
    name:str
    required:bool
    default:Optional[str]
    parameter_type:str
    roles:List[str]

@dataclass
class Endpoint:
    name: str
    path: str
    query_params: List[QueryParam]
    response_format: str
    method: str
    roles: List[str]

