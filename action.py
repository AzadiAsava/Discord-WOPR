from __future__ import annotations
from abc import abstractmethod
from dataclasses import dataclass


@dataclass
class Action:
    name:str
    description:str
    @abstractmethod
    async def __call__(self, message : Message, database : Database, sendable : Sendable) -> None:
        pass

class ConversationCompletionAction(Action):
    def __init__(self):
        super().__init__("Conversation Completion Action", "Complete the current conversation and send the completion.")
    async def __call__(self, message : Message, database : Database, sendable : Sendable) -> None:
        conversation = database.get_current_conversation(message.user)
        if conversation is None:
            conversation = Conversation.new_conversation()
        preferences = database.get_preferences(message.user)
        if preferences is not None:
            preference_summary = "\n".join([k + ": " + v for k, v in preferences.items()])
            conversation.set_system("I have the following preferences:\n" + preference_summary)
        if conversation.summary is not None:
            conversation.set_system("Here's a summary of the conversation so far:\n" + conversation.summary)
        if database.get_knowledge(message.user) is not None:
            conversation.set_system("Here's a summary of the knowledge I have:\n" + database.get_knowledge(message.user))
        conversation.add_user(message.text)
        database.set_conversation(message.user, conversation)
        completion = await chatgpt.get_completion(conversation.get_conversation())
        conversation.add_assistant(completion)
        database.set_conversation(message.user, conversation)
        await sendable.send(completion)
class ConversationSummaryAction(Action):
    def __init__(self):
        super().__init__("Conversation Summary Action", "Set a summary of the current conversation on it.")
    async def __call__(self, message : Message, database : Database, sendable : Sendable) -> None:
        conversation = database.get_current_conversation(message.user)
        if conversation is None:
            return
        conversation.summary = await chatgpt.summarize(str(conversation))
        database.set_conversation(message.user, conversation)
        
class UpdateKnowledgeAction(Action):
    def __init__(self):
        super().__init__("Update Knowledge Action", "Update the knowledge base of the user.")
    async def __call__(self, message : Message, database : Database, sendable : Sendable) -> None:
        conversations = database.get_conversations(message.user)
        summaries = ""
        for i, convo in enumerate(conversations, start=0):
            summaries += f"{i}. {convo.summary}\n"
        knowledge = await chatgpt.summarize_knowledge(summaries)
        database.set_knowledge(message.user, knowledge)
        
class ConversationChangeException(Exception):
    pass
class ChangeCurrentConversationAction(Action):
    def __init__(self):
        super().__init__("Change Current Conversation Action", "Change the current conversation.")
    async def __call__(self, message : Message, database : Database, sendable : Sendable) -> None:
        conversation = database.get_current_conversation(message.user)
        if conversation is None:
            conversation = Conversation.new_conversation()
            database.set_conversation(message.user, conversation)
            database.set_current_conversation(message.user, conversation)
        conversations = database.get_conversations(message.user)
        summaries = ""
        for i, convo in enumerate(conversations, start=0):
            summaries += f"{i}. {convo.summary}\n"
        conversation_index = await chatgpt.get_new_or_existing_conversation(summaries, message.text)
        try:
            if conversation_index == -1:
                new_conversation = Conversation.new_conversation()
                database.set_conversation(message.user, new_conversation)
                database.set_current_conversation(message.user, new_conversation)
                await sendable.send("I think this is a new conversation. One moment please...")
                raise ConversationChangeException
            elif conversations[conversation_index].id == conversation.id:
                return
            else:
                await sendable.send("Im changing topics to a prior conversation. One moment please...")
                database.set_current_conversation(message.user, conversations[conversation_index])
                raise ConversationChangeException
        except:
            return

class RememberAction(Action):
    def __init__(self): 
        super().__init__("Remember Action", "An explicit request to remember something or keep something in mind for later.")
    async def __call__(self, message : Message, database : Database, sendable : Sendable) -> None:
        preference = await chatgpt.extract_preferences(message.text)
        if preference is None:
            await sendable.send("I don't understand what you're asking me to remember.")
            return
        for k, v in preference.items():
            database.set_preference(message.user, k, v)
            await sendable.send(f"{k} is now {v}.")
        response = await chatgpt.get_completion([{"role":"system","content":"You are a helpful assistant."},{"role":"user","content":"I need a response to this that says I will remember these things: \n" + str(message.text) + "\nPlease blockquote the reply as a YAML blockquote starting with ```yaml\n```"}])
        await sendable.send(response.split("```yaml")[1].split("```")[0].strip())

from intent_classifier import Sendable
from db import Database
from dto import Conversation, Message
import chatgpt
