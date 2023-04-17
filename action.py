from __future__ import annotations
from abc import abstractmethod
from dataclasses import dataclass

import discord
from db import Database
from dto import Message

@dataclass
class ActionClassifier:
    name: str
    description: str
    @abstractmethod
    async def __call__(self, message: Message) -> Action:
        pass

@dataclass
class Action:
    name: str
    description: str
    @classmethod
    def get_description(cls) -> str:
        return cls.description
    @abstractmethod
    async def __call__(self, message: Message, database: Database, discord_client : discord.Client) -> None:
        pass

@dataclass
class TopicChangeAction(Action):
    name: str ="Topic Change"
    description: str = "An explicit request for a change in topic."
    async def __call__(self, message: Message, database: Database, discord_client : discord.Client) -> None:
        if len(database.get_conversations(message,user)) == 0:
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
