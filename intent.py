from abc import abstractmethod
from typing import List, TypeVar, Union
from action import Action, ChangeCurrentConversationAction, ConversationCompletionAction, ConversationSummaryAction, RememberAction, UpdateKnowledgeAction
from db import Database
from dto import Message
from sendable import Sendable

class Intent():
    @staticmethod
    @abstractmethod
    def get_descriptions() -> List[str]:
        pass
    @staticmethod
    @abstractmethod
    async def get_actions(message:Message, database : Database, sendable : Sendable) -> List[Action]:
        pass

class SubIntent():
    @staticmethod
    @abstractmethod
    def get_descriptions() -> List[str]:
        pass
    @staticmethod
    @abstractmethod
    async def get_actions(message:Message, database : Database, sendable : Sendable) -> List[Action]:
        pass

IntentType = Union[TypeVar("Intent", bound=Intent), TypeVar("SubIntent", bound=SubIntent)]

class TopicChangeIntent(Intent):
    @staticmethod
    def get_descriptions() -> List[str]:
        return ["An explicit request to change the topic.", "An implict request to discuss something unrelated to what we have been discussing."]
    @staticmethod
    async def get_actions(message: Message, database : Database, sendable : Sendable) -> List[Action]:
        return [ChangeCurrentConversationAction(), UpdateKnowledgeAction(), ConversationCompletionAction(), ConversationSummaryAction()]
class NoOpIntent(Intent):
    @staticmethod
    def get_descriptions() -> List[str]:
        return ["None of the above."]
    @staticmethod
    async def get_actions(message: Message, database : Database, sendable : Sendable) -> List[Action]:
        return [ConversationCompletionAction(), ConversationSummaryAction()]

class PleasantryIntent(NoOpIntent):
    @staticmethod
    def get_descriptions() -> List[str]:
        return ["Just a greeting, affirmation, platitude, or pleasantry and nothing more.", "A frieldly greeting or pleasantry."]

class InquiryIntent(NoOpIntent):
    @staticmethod
    def get_descriptions() -> List[str]:
        return ["A question or comment, specifically about what just happened.", "A question or comment regarding what was just discussed.", "Something that was relevant to the conversation we have been having."]

class RememberIntent(Intent):
    @staticmethod
    def get_descriptions() -> List[str]:
        return ["An explicit request to remember a detail or a set of details.","An explicit request to keep something in mind or to note something for the future."]
    @staticmethod
    async def get_actions(message: Message, database : Database, sendable : Sendable) -> List[Action]:
        return [RememberAction()]
        
