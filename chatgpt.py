import openai
import os

openai.api_key = os.getenv("OpenAIAPI-Token")
model_engine = "gpt-3.5-turbo"
def send_to_ChatGPT(messages, model=model_engine):
    response = openai.ChatCompletion.create(
            model=model_engine,
            messages=messages)
    return response.choices[0]['message']['content']

def extract_topic(message):
    convo = [
        {"role":"system","content":"You are a helpful AI assistant who knows how to extract a topic from a sentence for searching Wikipedia with. I will supply you with a sentence, and I want you to tell me, in quotes, a word or phrase suitible for searching Wikipedia with. Please syppu only the singular thing to search in quotes. For example, if I say 'I want to search Wikipedia for the meaning of life', you should say 'meaning of life' and nothing else."},
        {"role":"user","content":"What is the topic being discussed here? \"" + message + "\" Please only supply the topic in quotes. Make sure to include the quotes and nothing else except the topic in quotes."}
    ]
    return send_to_ChatGPT(convo).replace('"', '').replace("'", "").rstrip().lstrip()
