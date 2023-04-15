from __future__ import annotations
from abc import abstractmethod
import os
from typing import List, Tuple
from bs4 import BeautifulSoup
import pynytimes
from torch import cosine_similarity
from wolframalpha import Client as WolframAlphaClient
import wikipedia
from Levenshtein import distance
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import requests

from chatgpt import extract_urls
class DataSource:
    def __init__(self, name, url, query, context):
        self.name = name
        self.url = url
        self.query_str = query
        self.context = context
    @abstractmethod
    async def query(self : DataSource) -> List[Tuple[str, str]]:
        raise NotImplementedError


class WikipediaDataSource(DataSource):
    def __init__(self, name, url, query, context):
        super().__init__("Wikipedia", "https://en.wikipedia.org", query, context)
        self.wiki = wikipedia
        self.wiki.set_lang("en")
    def get_wiki_summary(self, topic : str) -> str:
        return wikipedia.summary(wikipedia.search(topic)[0])
    def get_wiki_suggestion(self, topic : str) -> str:
        try:
            return self.get_wiki_summary(topic)
        except wikipedia.exceptions.DisambiguationError as e:
            summary = ""
            for option in e.options[:5]:
                try:
                    summary += self.get_wiki_summary(option) + "\n\n"
                except wikipedia.exceptions.DisambiguationError:
                    continue
            return summary 
    async def query(self) -> List[Tuple[str, str]]:
        return [("Wikipedia", self.get_wiki_suggestion(self.query_str))]
class WolframAlphaDataSource(DataSource):
    def __init__(self, name, url, query, context):
        super().__init__("Wolfram|Alpha", "https://www.wolframalpha.com", query, context)
        self.client = WolframAlphaClient(os.environ.get("WolframAlpha-App-ID"))
    async def query(self) -> List[Tuple[str, str]]:
        # Send the query to Wolfram|Alpha and get the response
        res = self.client.query(self.query_str)
        try:
            if res["didyoumeans"] is not None:
                print(res["didyoumeans"])
                query = " ".join(x["#text"] for x in res["didyoumeans"]["didyoumean"])
                res = self.client.query(self.query_str)
        except:
            pass
        # Extract the plaintext result from the response
        try:
            res = next(res.results)
            if res.text is not None:
                return [("Wolfram|Alpha", res.text)]
            else:
                return [("Wolfram|Alpha", res.subpod.img.src)]
        except:
            return []
        
def get_data_from_url(url) -> str:
    res = requests.get(url)
    if res.status_code != 200:
        return ""
    navigation_elements = ["nav", "header", "footer", "aside", "html", "head", "meta", "link", "script", "style"]
    non_navigation_text = []
    soup = BeautifulSoup(res.content, "html.parser")
    for tag in soup.find_all(text=True):
        if tag.parent.name not in navigation_elements:
            non_navigation_text.append(tag.strip())
    return "\n".join(non_navigation_text)

class ExternalDataSource(DataSource):
    def __init__(self, name, url, query, context):
        super().__init__(name, url, query, context)
        self.url = url
    async def query(self) -> List[Tuple[str, str]]:
        # Send the query to the external source and get the response
        return [(self.name, get_data_from_url(self.url))]
class NewYorkTimesDataSource(DataSource):
    def __init__(self, name, url, query, context):
        super().__init__("New York Times", "https://www.nytimes.com", query, context)
        self.nytimes = pynytimes.NYTAPI(os.environ.get("NYTimes-API_Key", ""), parse_dates=True)
    async def query(self) -> List[Tuple[str, str]]:
        # Send the query to the external source and get the response
        res = self.nytimes.article_search(query=self.query_str)
        return [("New York Times", "\n".join([x["abstract"] for x in res["response"]["docs"]]))]
class GoogleNewsDataSource(DataSource):
    def __init__(self, name, url, query, context):
        super().__init__("Google News", "https://news.google.com", query, context)
    async def query(self) -> List[Tuple[str, str]]:
        # Send the query to the external source and get the response
        res = requests.get("https://news.google.com/rss/search?q=" + self.query_str)
        if res.status_code != 200:
            return []
        soup = BeautifulSoup(res.content, "html.parser")
        return [("Google News", "\n".join([x.text for x in soup.find_all("description")]))]

class GoogleSearchDataSource(DataSource):
    def __init__(self, name, url, query, context):
        super().__init__("Google Search", "https://www.google.com", query, context)
    async def query(self) -> List[Tuple[str, str]]:
        # Send the query to the external source and get the response
        res = requests.get("https://www.google.com/search?q=" + self.query_str)
        if res.status_code!= 200:
            return []
        soup = BeautifulSoup(res.content, "html.parser")
        return [("Google Search", "\n".join([x.text for x in soup.find_all("h3")]))]

def jaccard_similarity(str1, str2):
    set1 = set(str1.split())
    set2 = set(str2.split())
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return intersection / union

def like(string1, string2, threshold_lev=5, threshold_jac=0.4, threshold_cos=0.6):
    string1 = string1.lower().strip().replace("https://", "").replace("http://", "").replace("www.", "").replace(" ", "")
    string1 = "".join(x for x in string1 if x.isalnum())
    string2 = string2.lower().strip().replace("https://", "").replace("http://", "").replace("www.", "").replace(" ", "")
    string2 = "".join(x for x in string2 if x.isalnum())
    if string1.startswith("the"):
        string1 = string1[4:]
    if string2.startswith("the"):
        string2 = string2[4:]
    if len(string1) == 0 or len(string2) == 0:
        return False
    if string1 == string2:
        return True
    if string1[:6] in string2 or string2[:6] in string1:
        return True
    # Levenshtein distance
    lev_distance = distance(string1, string2)
    if lev_distance > threshold_lev:
        return False

    # Jaccard similarity
    jaccard_sim = jaccard_similarity(string1, string2)
    if jaccard_sim < threshold_jac:
        return False

    vectorizer = CountVectorizer()
    X = vectorizer.fit_transform([string1, string2])
    Y = vectorizer.fit_transform([string2, string1])
    cosine_sim = cosine_similarity(X, Y)[0][1]
    if cosine_sim < threshold_cos:
        return False
    return True

def like_any(string_list, query_string):
    for string in string_list:
        if like(query_string, string):
            return string
    return False
    
def get_data_sources(query) -> List[DataSource]:
    data_sources = []
    for data_source in DataSource.__subclasses__():
        if data_source == ExternalDataSource:
            continue
        data_source = data_source(query.get("name"), query.get("url"), query.get("query"), query.get("context"))
        if like(data_source.name, query.get("name")) or like(data_source.url, query.get("url") or like(data_source.name, query.get("url")) or like(data_source.url, query.get("name"))):
            data_sources.append(data_source)
    if len(data_sources) == 0:
        data_sources.append(ExternalDataSource(query.get("name"), query.get("url"), query.get("query"), query.get("context")))
    return data_sources
        