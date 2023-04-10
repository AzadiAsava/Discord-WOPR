from typing import Union, Optional
from chatgpt import send_to_ChatGPT
from chatgpt import extract_topic, summarize
import wikipedia
from typing import Optional, Callable, List, Dict, Any
import datetime
import jsonpickle
from uuid import uuid4


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
    def __init__(self, name : str, user : int = -1, conversation_manager : Optional["ConversationManager"] = None):
        self.name = name
        self.user = user
        self.conversation_manager = conversation_manager
    def __call__(self, _ : str) -> str:
        raise NotImplementedError(f"{type(self)} does not implement __call__.")
class DefaultMode(Mode):
    def __init__(self):
        super().__init__("Default Mode")
    def __call__(self, message : str) -> str:
        return message
class WikipediaMode(Mode):
    def __init__(self, user : int, conversation_manager : Optional["ConversationManager"] = None):
        if conversation_manager is None:
            raise ValueError("Wikipedia Mode requires a conversation_manager.")
        super().__init__("Wikipedia Mode", user, conversation_manager)
    def __call__(self, message : str) -> str:
        if self.conversation_manager is None:
            raise ValueError("Wikipedia Mode requires a conversation_manager.")
        topic = extract_topic(message)
        summary = get_wiki_suggestion(topic)
        self.conversation_manager.get_current_conversation(self.user).add_system("As a point of reference Wikipedia says the following about " + topic + " (may be off topic):\n" +  summary)
        return message

class MeanMode(Mode):
    def __init__(self, user : int, conversation_manager : Optional["ConversationManager"] = None):
        super().__init__("Mean Mode", user, conversation_manager)
    def __call__(self, message : str) -> str:
        if self.conversation_manager is None:
            raise ValueError("Mean Mode requires a conversation_manager.")
        self.conversation_manager.get_current_conversation(self.user).add_system("Remember to be extra rude, insulting, and mean in your responses.")
        return message

import pytz
class DateTimeAwareMode(Mode):
    def __init__(self, user : int, conversation_manager : Optional["ConversationManager"] = None, timezone : str = "America/Los_Angeles"):
        super().__init__("DateTime Aware Mode", user, conversation_manager)
        self.timezone = timezone
    def __call__(self, message : str) -> str:
        if self.conversation_manager is None:
            raise ValueError("DateTime Aware Mode requires a conversation_manager.")
        formatted_time = datetime.datetime.now(pytz.timezone(self.timezone)).strftime("%m/%d/%Y, %I:%M:%S %p")
        self.conversation_manager.get_current_conversation(self.user).add_system("The current date and time is now " + formatted_time + ".")
        return message

class UserPreferenceAwareMode(Mode):
    def __init__(self, user : int, conversation_manager : Optional["ConversationManager"] = None, param_loader : lambda : dict = lambda : {}):
        super().__init__("User Preference Aware Mode", user, conversation_manager)
        self.param_loader = param_loader
    def __call__(self, message : str) -> str:
        if self.conversation_manager is None:
            raise ValueError("User Preference Aware Mode requires a conversation_manager.")
        preferences = "Remember the following details in this conversation:\n"
        for key, value in self.param_loader().items():
            preferences += key + ": " + value + "\n"
        self.conversation_manager.get_current_conversation(self.user).add_system(preferences) 
        return message

class CompoundMode(Mode):
    def __init__(self, *modes : Union[Mode, Callable]):
        super().__init__("Compound Mode")
        self.modes = modes
    def __call__(self, message : str) -> str:
        for mode in self.modes:
            message = mode(message)
        return message

class Conversation:
    def __init__(self, user : int, system : str="You are a helpful AI assistant.", assistant : str="", modes : Union[List[Mode], List[Callable]] = []):
        self.user = user
        self.messages = [
            {"role":"system","content":system}
        ]
        if assistant != "":
            self.messages.append({"role":"assistant","content":assistant})
        self.modes = modes
        self.summary = "A conversation with a user that has not been summarized."
        self.id = str(uuid4())
    def add_user(self, user : str) -> None:
        for mode in self.modes:
            user = mode(user)
        self.messages.append({"role":"user","content":user})
    def add_system(self, system : str) -> None:
        self.messages.append({"role":"system","content":system})
    def add_assistant(self, assistant : str) -> None:
        self.messages.append({"role":"assistant","content":assistant})
    def get_conversation(self):
        return self.messages
    def get_user(self):
        return self.user
    def get_system(self):
        return self.messages[0]["content"]
    def delete_last_message(self):
        self.messages.pop()
    def __str__(self):
        convo = ""
        for message in self.messages:
            convo += message["role"] + ": " + message["content"] + "\n"
        return convo
    def __len__(self):
        return len(self.messages)
    def __iter__(self):
        return iter(self.messages)
    def __getitem__(self, index):
        return self.messages[index]
    def __setitem__(self, index, value):
        self.messages[index] = value
    def __delitem__(self, index):
        del self.messages[index]
    def __add__(self, other):
        return Conversation(self.user, self.messages + other.messages)
    def __eq__(self, other):
        return self.messages == other.messages
    def __ne__(self, other):
        return self.user != other.user or self.messages != other.messages
    


class ConversationManager:
    def __init__(self, db):
        self.conversations = {}
        self.db = db
    def update_current_conversation(self, user : int, user_input : str) -> str:
        return self.update_conversation(user, user_input)
    def update_conversation(self, user : int, user_input : str, conversation : Optional[Conversation] = None) -> str:
        if conversation is None:
            conversation = self.get_current_conversation(user)
        conversation.add_user(user_input)
        content = send_to_ChatGPT(conversation.get_conversation())
        conversation.add_assistant(content)
        conversation.summary = summarize(str(conversation))
        return content
    def add_conversation(self, conversation : Conversation) -> Conversation:
        if conversation.get_user() not in self.conversations:
            self.conversations[conversation.get_user()] = []    
        self.conversations[conversation.get_user()].insert(0, conversation)
        return conversation
    def get_conversations(self, user: int):
        if user not in self.conversations:
            return []
        return self.conversations[user]
    def get_conversation_summary(self, user) -> str:
        if user not in self.conversations:
            return "No conversations."
        conversations = [f"{i}. {convo.summary}\n" for i, convo in enumerate(self.conversations[user], start=0)]
        return "".join(conversations)    
    def get_current_conversation(self, user: int):
        if user not in self.conversations:
            return self.start_new_conversation(user)
        return self.conversations[user][0]
    def delete_conversation(self, user: int, index: int):
        if user not in self.conversations:
            return
        del self.conversations[user][index]
    def switch_to_conversation(self, user: int, index: int):
        if user not in self.conversations:
            self.start_new_conversation(user)    
        else:
            convo = self.conversations[user].pop(index)
            self.conversations[user].insert(0, convo)
        return self.get_current_conversation(user)
    def start_new_conversation(self, user : int, system : str="You are a helpful AI assistant.", assistant : str="", modes : Union[List[Mode], List[Callable]] = []):
        convo = Conversation(user, system, assistant=assistant, modes=modes)
        self.add_conversation(convo)
        return convo
    