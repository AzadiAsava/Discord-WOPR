from dataclasses import dataclass
import types
from typing import Type
from action import Action
from chatgpt import classify_intent
from dto import Message
from abc import abstractmethod

@dataclass
class Intent:
    name:str
    description:str
    @classmethod
    def get_description(cls) -> str:
        return cls.description
    @abstractmethod
    def get_action(self, message:Message) -> Action:
        pass

class TopicChangeIntent(Intent):
    def __init_subclass__(cls) -> None:
        return super().__init_subclass__()
    name:str = "Topic Change Intent"
    description:str = "An explicit request to change the topic, or an implict request to discuss something unrelated to what we have been discussing."
    def get_action(self, message: Message) -> Action:
        return super().get_action(message)

class NoOpIntent(Intent):
    name:str = "NoOp Intent"
    description:str = "None of the above."

class IntentClassifier:
    async def classify_intent(self, message : Message) -> Type[Intent]:
        possible_intents = Intent.__subclasses__()
        descriptions = [x.get_description() for x in possible_intents]
        intent_index = await classify_intent(descriptions, message.text)
        return possible_intents[intent_index]

        

