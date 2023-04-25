from action import ConversationChangeException, ConversationCompletionAction
from db import Database
from dto import Message
from intent import Intent
from intent_classifier import IntentClassifier
from sendable import Sendable
import chatgpt

class MessageHandler:
    def __init__(self):
        self.custom_handlers = {}
        self.intent_classifier = IntentClassifier()

    async def handle_message(self, message: Message, database: Database, sendable: Sendable):
        if message.user.id in self.custom_handlers:
            await self.custom_handlers[message.user.id](message, database, sendable)
            del self.custom_handlers[message.user.id]
            return
        intents = await self.intent_classifier.classify_intent(message, Intent.__subclasses__())
        actions = [action for intent in intents for action in await intent.get_actions(message, database, sendable)]
        for action in actions:
            try:
                await action(message, database, sendable)
            except ConversationChangeException:
                message.text = await chatgpt.remove_change_of_topic(message.text)
                await self.handle_message(message, database, sendable)
    

