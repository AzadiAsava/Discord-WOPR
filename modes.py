import wikipedia
from conversation import Conversation
import openai

def get_wiki_summary(topic):
    wikipedia.set_lang("en")
    return wikipedia.summary(wikipedia.search(topic)[0])
def get_wiki_suggestion(topic):
    wikipedia.set_lang("en")
    try:
        return get_wiki_summary(topic)
    except wikipedia.exceptions.DisambiguationError as e:
        return get_wiki_summary(e.options[0])
    
def extract_topic(message):
    # Extract the topic from a message
    convo = Conversation(None, "You are a helpful AI assistant who knows how to extract a topic from a sentence for searching Wikipedia with. I will supply you with a sentence, and I want you to tell me, in quotes, a word or phrase suitible for searching Wikipedia with. Please syppu only the singular thing to search in quotes. For example, if I say 'I want to search Wikipedia for the meaning of life', you should say 'meaning of life' and nothing else.")
    convo.add_user(message)
    return send_to_ChatGPT(convo).replace('"', '').replace("'", "").rstrip().lstrip()

def send_to_ChatGPT(convo):
    response = openai.ChatCompletion.create(
            model='gpt-3.5-turbo',
            messages=convo.get_conversation())
    return response.choices[0]['message']['content']
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
        summary = get_wiki_suggestion(topic)
        print(summary)
        self.conversation_manager.get_current_conversation(self.user).add_system("As a point of reference Wikipedia says the following about " + topic + " (may be off topic): " +  summary)
        return message
