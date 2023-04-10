import wikipedia
from chatgpt import extract_topic
from typing import Optional
from conversation import ConversationManager
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
    def __init__(self, name : str, user : int, conversation_manager : Optional[ConversationManager] = None):
        self.name = name
        self.user = user
        self.conversation_manager = conversation_manager
    def __call__(self, _ : str) -> str:
        raise NotImplementedError("Mode.__call__ is not implemented.")
class DefaultMode(Mode):
    def __init__(self, user : int, conversation_manager : Optional[ConversationManager] = None):
        super().__init__("Default Mode", user, conversation_manager)
    def __call__(self, message : str) -> str:
        return message
class WikipediaMode(Mode):
    def __init__(self, user : int, conversation_manager : Optional[ConversationManager] = None):
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
