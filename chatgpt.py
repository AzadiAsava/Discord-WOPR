import openai
import os
import re
from nltk.sentiment.vader import SentimentIntensityAnalyzer

# Create an instance of the SentimentIntensityAnalyzer object
analyzer = SentimentIntensityAnalyzer()

openai.api_key = os.getenv("OpenAIAPI-Token")
model_engine = "gpt-3.5-turbo"
def send_to_ChatGPT(messages, model=model_engine):
    response = openai.ChatCompletion.create(
            model=model,
            messages=messages)
    if response is None:
        raise Exception("No response from OpenAI")
    return response.choices[0]['message']['content'] # type: ignore

def extract_topic(message : str) -> str:
    convo = [
        {"role":"system","content":"You are a helpful AI assistant who knows how to extract a topic from a sentence for searching Wikipedia with. I will supply you with a sentence, and I want you to tell me, in quotes, a word or phrase suitible for searching Wikipedia with. Please supply only the singular thing to search in quotes. For example, if I say 'I want to search Wikipedia for the meaning of life', you should say 'meaning of life' and nothing else."},
        {"role":"user","content":"What is the topic being discussed here? \"" + message + "\" Please only supply the topic in quotes. Make sure to include the quotes and nothing else except the topic in quotes."}
    ]
    return send_to_ChatGPT(convo).replace('"', '').replace("'", "").rstrip().lstrip()

def summarize(conversation: str) -> str:
    convo = [
        {"role":"system","content":"You are a helpful AI assistant who knows how to summarize a conversation. I will supply you with a conversation, and I want you to tell me, in quotes, a summary of the conversation. Please supply only the summary in quotes. For example, if I say 'I want to summarize this conversation', you should say 'This conversation is about a topic.' and nothing else."},
        {"role":"user","content":"What is the summary of this conversation? \"" + conversation + "\" Please only supply the summary in quotes. Make sure to include the quotes and nothing else except the summary in quotes."}
    ]
    return send_to_ChatGPT(convo).replace('"', '').replace("'", "").rstrip().lstrip()

def is_positive(message : str) -> bool:
    scores = analyzer.polarity_scores(message)
    return scores['compound'] > 0

def get_is_request_to_change_topics(context, user_input : str) -> bool:
    convo = [
        {"role":"system","content":"You are a helpful AI assistant who knows how to identify if a sententce is a request to to talk about something were already discussing, or a change in topics. I will supply you with a sentence, and I want you to tell me, in quotes, if this is a request to change topics or not. Please supply an explnation for your answer. For example, if I say 'Can we talk about my dog instead?', you should say 'yes because it's asking to talk about a dog instead of the current topic', but if I say something context free, or related to what i was previously discussing, you should say 'no its on topic' and nothing else."},
        {"role":"system","content":"Previously I was talking about: " + context},
        {"role":"user","content":"Is this an explicit or obvious request to change topics? \"" + user_input + "\""}
    ]
    result = send_to_ChatGPT(convo).replace('"', '').replace("'", "").rstrip().lstrip()
    return is_positive(result)

def get_new_or_existing_conversation(old_conversations, user_input):
    convo = [
        {"role":"system","content":"You are a helpful AI assistant who knows how to identify if a question is related to a prior conversation, or if it is a new conversation. I will supply you with a conversation, and I want you to tell me, in quotes, if this is a new conversation or if it is related to a prior conversation. Please supply only the prior conversatyion in quotes, or say 'new conversation' if this is a new conversation. For example, if I say 'I want to know if this is a new conversation or related to a prior conversation', you should say 'new conversation' or 'The prior conversation about prior conversations.' and nothing else."},
        {"role":"system","content":"Here are the prior conversations:\n" + old_conversations},
        {"role":"user","content":"Is this a new conversation or related to a prior conversation? \"" + user_input + "\" Please only supply the prior conversation in quotes, or say 'new conversation' if this is a new conversation. Make sure to include the specific conversation number. I need the number, not the topic. For example, if I say 'I want to know if this is a new conversation or related to a prior conversation. Please give me the related conversation number, or 'new conversation' if this is a new conversation. Remember, I really want the number of the conversation, like 3 or 5."}
    ]
    result = send_to_ChatGPT(convo).replace('"', '').replace("'", "").rstrip().lstrip()
    if "new conversation" in result.lower() and re.search(r"\d+", result) is None:
        return -1
    number = re.search(r"\d+", result)
    if number is None:
        return -1
    return int(number.group(0))
