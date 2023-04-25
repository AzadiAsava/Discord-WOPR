from __future__ import annotations
from dataclasses import dataclass
from typing import List, Type, TypeVar, Union
from abc import abstractmethod
import discord

Sendable = Union[discord.Webhook, discord.abc.Messageable]


@dataclass
class Describable:
    name: str
    description: str
    @classmethod
    def get_description(cls) -> str:
        return cls.description
@dataclass
class Intent(Describable):
    def __init__(self, name : str, description : str):
        super().__init__(name, description)
    @abstractmethod
    async def get_actions(self, message:Message, database : Database, sendable : Sendable) -> List[Action]:
        pass

@dataclass
class SubIntent(Describable):
    def __init__(self, name : str, description : str):
        super().__init__(name, description)
    @abstractmethod
    async def get_actions(self, message:Message, database : Database, sendable : Sendable) -> List[Action]:
        pass

IntentType = Union[TypeVar("Intent", bound=Intent), TypeVar("SubIntent", bound=SubIntent)]

class TopicChangeIntent(Intent):
    name:str="Topic Change Intent"
    description:str="An explicit request to change the topic, or an implict request to discuss something unrelated to what we have been discussing."
    def __init__(self):
        pass
    async def get_actions(self, message: Message, database : Database, sendable : Sendable) -> List[Action]:
        return [ChangeCurrentConversationAction(), UpdateKnowledgeAction(), ConversationCompletionAction(), ConversationSummaryAction()]
class NoOpIntent(Intent):
    name:str = "NoOp Intent"
    description:str = "None of the above"
    def __init__(self):
        pass
    @staticmethod
    async def get_actions(message: Message, database : Database, sendable : Sendable) -> List[Action]:
        return [ConversationCompletionAction(), ConversationSummaryAction()]

class PleasantryIntent(NoOpIntent):
    name:str = "Pleasantry Intent"
    description:str = "Just a greeting, affirmation, platitude, or pleasantry and nothing more."


class InquiryIntent(NoOpIntent):
    name:str = "Inquiry Intent"
    description:str = "A question or inquiry, specifically about what just happened, was just discussed, what was just done, or something that was relevant to the conversation we have been having where some action was performed."


class RememberIntent(Intent):
    name:str = "Remember Intent"
    description:str = "An explicit request to remember a set of details, and the very specific details to remember. (It MUST include the word \"remember\")"
    def __init__(self):
        pass
    async def get_actions(self, message: Message, database : Database, sendable : Sendable) -> List[Action]:
        return [RememberAction()]
        

class IntentClassifier:
    async def classify_intent(self, message : Message, intents : List[IntentType]) -> Type[IntentType]:
        descriptions = [x.get_description() for x in intents]
        intent_index = await classify_intent(descriptions, message.text, message.context)
        return intents[intent_index]



@dataclass
class MessageHandler:
    intent_classifier:IntentClassifier = IntentClassifier()
    async def handle_interaction(self, message : Message, database : Database, interaction : discord.Interaction):
        try:
            await interaction.response.defer()
            await interaction.delete_original_response()
        except:
            pass
        intent_type = await self.intent_classifier.classify_intent(message, Intent.__subclasses__())
        intent = type(intent_type)()
        actions = await intent.get_actions(message, database, interaction.followup)
        try:
            for action in actions:
                await action(message, database, interaction.followup)
        except ConversationChangeException:
            message.text = await remove_change_of_topic(message.text)
            await self.handle_message(message, database, interaction.followup)

    async def handle_message(self, message: Message, database : Database, sendable : Sendable):
        intent_type = await self.intent_classifier.classify_intent(message, Intent.__subclasses__())
        intent = intent_type() # type: ignore
        actions = await intent.get_actions(message, database, sendable)
        try:
            for action in actions:
                await action(message, database, sendable)
        except ConversationChangeException:
            message.text = await remove_change_of_topic(message.text)
            await self.handle_message(message, database, sendable)

    async def send_conversation_for_completion(self, message: Message, database: Database, sendable: Sendable):
        await ConversationCompletionAction()(message, database, sendable)

from action import Action, ChangeCurrentConversationAction, ConversationChangeException, ConversationCompletionAction, ConversationSummaryAction, RememberAction, UpdateKnowledgeAction
from chatgpt import classify_intent, remove_change_of_topic
from dto import Message
from db import Database
import intents.git
