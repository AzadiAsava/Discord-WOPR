from typing import AsyncGenerator, Callable, Generator, List, Optional, Tuple
import openai
import os
import re
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import yaml

# Create an instance of the SentimentIntensityAnalyzer object
analyzer = SentimentIntensityAnalyzer()

openai.api_key = os.getenv("OpenAIAPI-Token")
model_engine = "gpt-3.5-turbo"

def tries(times):
    def func_wrapper(f):
        async def wrapper(*args, **kwargs):
            for time in range(times):
                print('times:', time + 1)
                # noinspection PyBroadException
                try:
                    return await f(*args, **kwargs)
                except Exception as exc:
                    pass
            raise Exception('Failed too many times')
        return wrapper
    return func_wrapper

@tries(3)
async def get_completion(messages :list[dict[str,str]], model:str=model_engine, temperature:float=0.5) -> str:
    response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            temperature=temperature)
    if response is None:
        raise Exception("No response from OpenAI")
    return response.choices[0]['message']['content'] # type: ignore

async def extract_topic(message : str) -> str:
    convo = [
        {"role":"system","content":"You are a helpful AI assistant who knows how to extract a topic from a sentence for searching Wikipedia with. I will supply you with a sentence, and I want you to tell me, in quotes, a word or phrase suitible for searching Wikipedia with. Please supply only the singular thing to search in quotes. For example, if I say 'I want to search Wikipedia for the meaning of life', you should say 'meaning of life' and nothing else."},
        {"role":"user","content":"What is the topic being discussed here? \"" + message + "\" Please only supply the topic in quotes. Make sure to include the quotes and nothing else except the topic in quotes."}
    ]
    return (await get_completion(convo)).replace('"', '').replace("'", "").rstrip().lstrip()

async def summarize(conversation: str) -> str:
    convo = [
        {"role":"system","content":"You are a helpful AI assistant who knows how to create detailed summaries of content. I will supply you with some content, and I want you to tell me, in quotes, a summary of the conversation. Please supply as many important details in the summary as you can."},
        {"role":"user","content":"What is a highly detailed summary of this content? \"" + conversation[:3000] + "\" Please only supply the summary in quotes. Make sure to include the quotes and nothing else except the summary in quotes."}
    ]
    return (await get_completion(convo)).replace('"', '').replace("'", "").rstrip().lstrip()

async def summarize_data(data: str) -> str:
    convo = [
        {"role":"system","content":"You are a helpful AI assistant who knows how to create detailed summaries of content. I will supply you with some content, and I want you to tell me, in quotes, a summary of the conversation. Please supply as many important details in the summary as you can."},
        {"role":"user","content":"What is a highly detailed summary of this content? \"" + data[:3000] + "\" Please only supply the summary in quotes. Make sure to include the quotes and nothing else except the summary in quotes."}
    ]
    return (await get_completion(convo)).replace('"', '').replace("'", "").rstrip().lstrip()

def is_positive(message : str) -> bool:
    scores = analyzer.polarity_scores(message)
    return scores['compound'] > 0

async def get_is_request_to_change_topics(context : str, user_input : str) -> bool:
    convo = [
        {"role":"system","content":"You are a helpful AI assistant who knows how to identify if a sententce is a request to to talk about something were already discussing, or a change in topics. I will supply you with a sentence, and I want you to tell me, in quotes, if this is a request to change topics or not. Please supply an explnation for your answer. For example, if I say 'Can we talk about my dog instead?', you should say 'yes because it's asking to talk about a dog instead of the current topic', but if I say something context free, or related to what i was previously discussing, you should say 'no its on topic' and nothing else."},
        {"role":"system","content":"Previously I was talking about: " + context},
        {"role":"user","content":"Is this an explicit or obvious request to change topics? \"" + user_input + "\""}
    ]
    result = (await get_completion(convo)).replace('"', '').replace("'", "").rstrip().lstrip()
    return is_positive(result)

async def get_new_or_existing_conversation(old_conversations : str, user_input : str):
    convo = [
        {"role":"system","content":"You are a helpful AI assistant who knows how to identify if a question is related to a prior conversation, or if it is a new conversation. I will supply you with a conversation, and I want you to tell me, in quotes, if this is a new conversation or if it is related to a prior conversation. Please supply only the prior conversatyion in quotes, or say 'new conversation' if this is a new conversation. For example, if I say 'I want to know if this is a new conversation or related to a prior conversation', you should say 'new conversation' or 'The prior conversation about prior conversations.' and nothing else."},
        {"role":"system","content":"Here are the prior conversations:\n" + old_conversations},
        {"role":"user","content":"Is this a new conversation or related to a prior conversation? \"" + user_input + "\" Please only supply the prior conversation in quotes, or say 'new conversation' if this is a new conversation. Make sure to include the specific conversation number. I need the number, not the topic. For example, if I say 'I want to know if this is a new conversation or related to a prior conversation. Please give me the related conversation number, or 'new conversation' if this is a new conversation. Remember, I really want the number of the conversation, like 3 or 5."}
    ]
    result = (await get_completion(convo)).replace('"', '').replace("'", "").rstrip().lstrip()
    if "new conversation" in result.lower() and re.search(r"\d+", result) is None:
        return -1
    number = re.search(r"\d+", result)
    if number is None:
        return -1
    return int(number.group(0))

async def summarize_knowledge(conversation_summary: str) -> str:
    convo = [
        {"role":"system","content":"You are a helpful AI assistant who knows how to summarize a series of conversations into a knowledge base. I will supply you with a list of summaries of prior conversations we have had, and I want you to write a paragraph or three containing the key datapoints from all the conversations. Make sure to include key datapoints from all the conversations."},
        {"role":"system","content":"Here are the summaries of prior conversations:\n" + conversation_summary},
        {"role":"user","content":"What is the knowledge base of our prior conversations? Please write a paragraph or three containing the key datapoints from all the conversations. Make sure to include key datapoints from all the conversations."}
    ]
    return (await get_completion(convo)).replace('"', '').replace("'", "").rstrip().lstrip()

async def find_similar_conversations(conversations : str) -> Optional[Tuple[int, int]]:
    convo = [
        {"role":"system","content":"You are a helpful AI assistant who knows how to find similar conversations. I will supply you with a list of conversations, and I want you to tell me, in quotes, if there are any conversations that are discussing related topics. Please supply the conversation by number, for example, 'Conversations 2 and 4 are simiar, and 7 and 3 are similar.' and nothing else."},
        {"role":"system","content":"Here are the conversations in question:\n" + conversations},
        {"role":"user","content":"Is there any similar conversation that are discussing related topics? Please list the conversation by number, for example, 'Conversations 2 and 4 are simiar."}
    ]
    result = (await get_completion(convo)).replace('"', '').replace("'", "").rstrip().lstrip()
    #find 2 numbers
    numbers = re.findall(r"\d+", result)
    if len(numbers) < 2:
        return None
    return int(numbers[0]), int(numbers[1])

import re
import json
async def merge_conversations(conversation1 : str, conversation2 : str) -> list[dict[str,str]]:
    convo = [
        {"role":"system","content":"You are a helpful AI assistant who knows how to merge two conversations. I will supply you with two conversations, and I want you to make up a new conversation that merges the two conversations into a single conversation."},
        {"role":"user","content":"Here are the two conversations to merge:"},
        {"role":"user","content":"Conversation 1:\n\n" + conversation1},
        {"role":"user","content":"Conversation 2:\n\n" + conversation2},
        {"role":"user","content":"Please produce a new conversation that merges the two conversations into a single conversation."}
    ]
    result = (await get_completion(convo)).replace('"', '').replace("'", "").rstrip().lstrip()
    print(result)
    result = [ {"role":x[0].strip().lower(), "content":x[1].strip()} for x in [ x.split(":") for x in result.split("\n") if x.strip() != "" and ":" in x and ("assistant" in x.lower() or "user" in x.lower() or "system" in x.lower()) ] ]
    return result

async def get_wolfram_query(query : str) -> str:
    convo = [
        {"role":"system","content":"You are a helpful AI assistant capable of converting conversatioal summaries and follow up questions into a query suitible for Wolfram Alpha."},
        {"role":"user","content":"Please convert the following into a query suitible for sending to WolframAlpha: " + query}
    ]
    return (await get_completion(convo)).replace('"', '').replace("'", "").rstrip().lstrip()

async def extract_urls(query : str) -> List[dict[str,str]]:
    convo = [
        {"role":"system","content":"You are a helpful ai assistant who knows how to given a message, guess the url i should be querying, and make a good query for that specific url as to what I should search it for. You will take the message i give you, and you will tell me what url i should query, and what query I should search that url for given that message. Remember to take into account the nature of the website when answering the question."},
        {"role":"user","content":f"Your first example is, \"{query}\" What is the url of the company or brand mentioned there, or what urls might be relevant what is being discussed, ignoring any questions or statements that don't make sense, and what should i query them for specifically in quotes? I just want the url and the query, please dont mention what I should not search for or the reasoning. Do NOT put the url in quotes, as that will only confuse me. Format your response in yaml, with an array of NAME, URL and QUERY pairs."}         
    ]
    result = (await get_completion(convo)).replace('"', '').replace("'", "").rstrip().lstrip()
    
    try:
        result = result.split("```")[1]
        if result.lower().startswith("yaml"):
            result = result[4:]
        result = yaml.load(result, Loader=yaml.Loader)
        output = []
        for i in result:
            out = {"context":query}
            for k, v in i.items():
                value = v.replace('"', '').replace("'", "").rstrip().lstrip().replace("\\", "")
                if "site:" in value:
                    value = value[:value.index("site:")].strip()
                out[k.lower()] = value
            output.append(out)
        return output
    except:
        return []
    
async def extract_datasource(query : str) -> Optional[dict[str,str]]:
    convo = [
        {"role":"system","content":"You are a software engineer responsible for designing a web API interface based on a plain text description. Your goal is to take a description of a web API, including its URL and endpoints, and create a YAML map that includes all the relevant parameters specified. For example, if you were given the following plain text description: \"I have an API for searching Google at google.com, and it has a search API at /search which takes a query parameter q and returns results in JSON format\", your output would be a YAML map that includes the following information:\n```yaml\nurl: \"https://google.com\"\nendpoints:\n  - path: \"/search\"\n    method: \"GET\"\n    query_params:\n      - name: \"q\"\n        required: true\n    response_format: \"json\"\n```\n"},
        {"role":"user","content":f"Your first example is, \"{query}\" Please write a YAML map for this datasource."}
    ]
    result = (await get_completion(convo)).replace('"', '').replace("'", "").rstrip().lstrip()
    try:
        result = result.split("```")[1]
        if result.lower().startswith("yaml"):
            result = result[4:]
        result = yaml.load(result, Loader=yaml.Loader)
        out = {"context":query}
        for k, v in result.items():
            value = v.replace('"', '').replace("'", "").rstrip().lstrip().replace("\\", "")
            if "site:" in value:
                value = value[:value.index("site:")].strip()
            out[k.lower()] = value
        return out
    except:
        return None

async def classify_intent(categories : List[str], query : str, context: str) -> int:
    convo = [ 
        {"role":"assistant", "content": "For context: " + context},
        {"role":"system", "content": "You are a classification agent that knows how to classify text into EXACTLY ONE of a list of options listed, or \"None of the above.\" if it doesnt match any of the listed options."},
        {"role":"system", "content":"For example if the choice was 2, you would reply with ```yaml\n2: Choice 2\n``` and nothing else."},
        {"role":"user", "content": "Here's the list of possible options:"},
        ] + [{"role": "user", "content": f"{i}: {j}"} for i, j in enumerate(categories)] + \
        [{"role": "user", "content": f'Please classify this as one of the above options listed: "{query}". Make sure you block quote the output as YAML as a map keyed by the option number and ONLY GIGE ONE ANSWER. You should avoid "None of the above" if the answer is close.'}]

    result = await get_completion(convo, temperature=0)
    try:
        return int(re.findall(r"\d+", result)[0])
    except:
        return 0

async def extract_preferences(message) -> dict[str,str]:
    convo = [
        {"role":"system","content":"You are a helpful AI assistant capable of taking a message and extracting a key/value set of preferences and giving the value back as YAML."},
        {"role":"system","content":"""For example, if I were to say to you, "Remember to always call me Sir, and my Birthday is 10/10/1990" you would say:
```yaml
"My name": "Sir"
"My birthday": "10/10/1990"
"Always call me": "Sir"
```"""},
        {"role":"user","content":"Please convert the following into a YAML map of preferences: " + message}
    ]
    result = (await get_completion(convo))
    try:
        result = result.split("```")[1]
        if result.lower().startswith("yaml"):
            result = result[4:]
        result = yaml.load(result, Loader=yaml.Loader)
        return result
    except:
        return {}
    
async def remove_change_of_topic(message : str) -> str:
    convo = [
        {"role":"system", "content":"You are a helpful AI assistant who knows how to take a a statement or request to discuss a specific topic or change a topic, and reword the request to eliminate the request to change the topic and any mentions of \"instead\", leaving only the subject as a new request or statement."},
        {"role":"system", "content":"For example, if I say to you, \"Can we discuss Queen Elizabeth instead of talking about this? Did she die according to Wikipedia?\", you would reply with,\n```yaml\nDid Queen Elizabeth die accoring to Wikipedia?```\n and nothing else. If it doesnt mention a topic change just quote it directly as your reply. Output the new request as a YAML string."},
        {"role":"user", "content":"Please reformat this to not include the mention of change of topic: \"" + message + "\". Remember to output the result as a YAML string, and don't use words like \"instead\" in your reply."}
    ]
    result = await get_completion(convo)
    try:
        result = result.split("```")[1]
        if result.lower().startswith("yaml"):
            result = result[4:]
        result=result.strip()
        return result
    except:
        return message
        
async def get_git_repo_and_options(message) -> dict[str,str]:
    convo = [
        {"role":"system","content":"You are a helpful AI assistant who knows how to extract git urls from requests to do things with git, as well as the associated git command and options required to pull off the request, and return the results as a blockquoted yaml map."},
        {"role":"system","content":"""For example, if i said, "Please clone the stable branch of https://github.com/Significant-Gravitas/Auto-GPT" you would reply:
```yaml
repo: Auto-GPT
executable: git
command: clone
url: https://github.com/Significant-Gravitas/Auto-GPT
options: --branch stable
```
"""},
        {"role":"user","content":"Please convert the following into a YAML map: " + message}
    ]
    result = (await get_completion(convo))
    try:
        result = result.split("```")[1]
        if result.lower().startswith("yaml"):
            result = result[4:]
        result = yaml.load(result, Loader=yaml.Loader)
        return result
    except:
        return {}
