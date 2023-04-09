import wikipedia
from chatgpt import extract_topic
wikipedia.set_lang("en")

def get_wiki_summary(topic):
    return wikipedia.summary(wikipedia.search(topic)[0])
def get_wiki_suggestion(topic):
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
    def __init__(self, name, user, conversation_manager):
        self.name = name
        self.user = user
        self.conversation_manager = conversation_manager
class WikipediaMode(Mode):
    def __init__(self, user, conversation_manager):
        super().__init__("Wikipedia Mode", user, conversation_manager)
    def __call__(self, message):
        topic = extract_topic(message)
        print(topic)
        summary = get_wiki_suggestion(topic)
        print(summary)
        self.conversation_manager.get_current_conversation(self.user).add_system("As a point of reference Wikipedia says the following about " + topic + " (may be off topic):\n" +  summary)
        return message
