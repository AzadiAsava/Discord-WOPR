from __future__ import annotations
from abc import abstractmethod
import inspect
import os
from typing import AsyncGenerator, List, Optional
from bs4 import BeautifulSoup
import pynytimes
from wolframalpha import Client as WolframAlphaClient
import wikipedia
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import requests

class DataSource:
    def __init__(self, name : str, url : str, roles : List[str]):
        self.name = name
        self.url = url
        self.role = roles
    @abstractmethod
    async def query(self, query : str, context:Optional[dict[str,str]]) -> AsyncGenerator[str, None]:
        pass

class SpecializedDataSource(DataSource):
    def __init__(self, name : str, url : str, roles : List[str]):
        super().__init__(name, url, roles)
    @abstractmethod
    async def get_query(self, query : str, context:Optional[dict[str,str]]) -> AsyncGenerator[str, None]:
        pass
class QueryParam:
    def __init__(self, name, required : bool = True, parameter_type: str = "", default : Optional[str] = None):
        self.name = name
        self.required = required
        self.parameter_type = parameter_type
        self.default = default
class Endpoint:
    def __init__(self, name : str, path : str, query_params : List[QueryParam] = [], method = "GET", response_format : str = "html", role : str = "default"):
        self.name = name
        self.path = path
        self.query_params = query_params
        self.response_format = response_format
        self.method = method
        self.role = role

class ExternalDataSource(DataSource):
    def __init__(self, name : str, url : str, roles : List[str], endpoints : List[Endpoint]):
        super().__init__(name, url, roles)
        self.endpoints = endpoints
    async def query(self, query:str, context:Optional[dict[str, str]], roles : List[str] = ["search"]) -> AsyncGenerator[str, None]:
        relevant_endpoints = [endpoint for endpoint in self.endpoints if endpoint.role in roles]
        for endpoint in relevant_endpoints:
            url = self.url + endpoint.path + "?"
            params = []
            for param in endpoint.query_params:
                if param.parameter_type == "query":
                    params.extend([param.name + "=" + query])
                    continue
                if context is not None and param.name in context:
                    params.extend([param.name + "=" + str(context[param.name])])
                    continue
                if param.required and param.default is not None:
                    params.extend([param.name + "=" + param.default])
                    continue
                if param.required:
                    raise ValueError("Missing required parameter: " + param.name)
                if param.default is not None:
                    params.extend([param.name + "=" + param.default])
                    continue
                params.extend([param.name])
            url += "&".join(params)
            if endpoint.method == "GET":
                response = requests.get(url)
            elif endpoint.method == "POST":
                response = requests.post(url, json=context, headers={"Content-Type": "application/json"})
            else:
                raise ValueError("Invalid method: " + endpoint.method)
            if response.status_code == 200:
                content = response.content.decode("utf-8")
                if endpoint.response_format == "html":
                    soup = BeautifulSoup(content, "html.parser")
                    for element in soup.find_all():
                        if element.parent.name in ["nav", "header", "footer", "aside", "html", "head", "meta", "link", "script", "style"]:
                            continue
                        yield element.strip()
                else:
                    yield content
            else:
                continue
        raise StopIteration
  
class WikipediaDataSource(SpecializedDataSource):
    def __init__(self):
        super().__init__("Wikipedia", "https://en.wikipedia.org", ["search", "reference"])
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
    async def query(self, query: str, context: Optional[dict[str,str]] = None) -> AsyncGenerator[str, None]:
        #TODO: Get this to yield all topic summaries.
        yield self.get_wiki_suggestion(query)
        
class WolframAlphaDataSource(SpecializedDataSource):
    def __init__(self):
        super().__init__("Wolfram|Alpha", "https://www.wolframalpha.com", ["compute", "research"])
        self.client = WolframAlphaClient(os.environ.get("WolframAlpha-App-ID"))
    async def query(self, query: str, context: Optional[dict[str,str]] = None) -> AsyncGenerator[str, None]:
        res = self.client.query(query)
        try:
            if res["didyoumeans"] is not None:
                print(res["didyoumeans"])
                query = " ".join(x["#text"] for x in res["didyoumeans"]["didyoumean"])
                res = self.client.query(query)
        except:
            pass
        # Extract the plaintext result from the response
        try:
            res = next(res.results)
            if res.text is not None:
                yield res.text
            else:
                yield res.subpod.img.src
        except:
            raise StopIteration
        
def get_text_from_html(html) -> str:
    navigation_elements = ["nav", "header", "footer", "aside", "html", "head", "meta", "link", "script", "style"]
    non_navigation_text = []
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(text=True):
        if tag.parent.name not in navigation_elements:
            non_navigation_text.append(tag.strip())
    return "\n".join(non_navigation_text)

class NewYorkTimesDataSource(DataSource):
    def __init__(self):
        super().__init__("New York Times", "https://www.nytimes.com", ["search", "news"])
        self.nytimes = pynytimes.NYTAPI(os.environ.get("NYTimes-API_Key", ""), parse_dates=True)
    async def query(self, query: str, context : Optional[dict[str,str]] = None) -> AsyncGenerator[str, None]:
        # Send the query to the external source and get the response
        res = self.nytimes.article_search(query=query)    
        for x in res:
            yield x["abstract"]
        raise StopIteration    
class GoogleNewsDataSource(DataSource):
    def __init__(self):
        super().__init__("Google News", "https://news.google.com", ["news"])
    async def query(self, query: str, context: Optional[dict[str,str]] = None) -> AsyncGenerator[str, None]:
        # Send the query to the external source and get the response
        res = requests.get("https://news.google.com/search?q=" + query)
        if res.status_code!= 200:
            raise StopIteration("Could not get a response from Google News: " + str(res.status_code))
        soup = BeautifulSoup(res.content, "html.parser")
        for x in soup.find_all("div", class_="g"):
            yield x.text
        raise StopIteration
    
class GoogleSearchDataSource(DataSource):
    def __init__(self):
        super().__init__("Google Search", "https://www.google.com", ["search"])
    async def query(self, query: str, context: Optional[dict[str,str]] = None) -> AsyncGenerator[str, None]:
        # Send the query to the external source and get the response
        res = requests.get("https://www.google.com/search?q=" + query)
        if res.status_code != 200:
            raise StopIteration("Could not get a response from Google: " + str(res.status_code))
        soup = BeautifulSoup(res.content, "html.parser")
        for x in soup.find_all("h3"):
            yield x.text
        raise StopIteration

def get_jaccard_similarity(str1 : str, str2 : str, threshold_jac :float=0.4) -> bool:
    set1 = set(str1.split())
    set2 = set(str2.split())
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return intersection / union >= threshold_jac

def get_cosine_similarity(string1: str, string2: str, threshold_cos: float) -> bool:
    vectorizer = CountVectorizer()
    vectors = vectorizer.fit_transform([string1, string2])
    cosine_sim = cosine_similarity(vectors)[0][1]
    return cosine_sim >= threshold_cos

def like(string1:str, string2:str, threshold_jac : float = 0.4, threshold_cos : float = 0.6):
    # Remove unnecessary characters and convert to lowercase
    string1 = ''.join(c for c in string1 if c.isalnum() or c.isspace()).lower().strip()
    string2 = ''.join(c for c in string2 if c.isalnum() or c.isspace()).lower().strip()
    # Remove common prefixes
    if string1.startswith("the"):
        string1 = string1[4:]
    if string2.startswith("the"):
        string2 = string2[4:]
    # Return False if either string is empty
    if not string1 or not string2:
        return False
    # Return True if strings are identical
    if string1 == string2:
        return True
    # Check for substring match
    if string1[:6] in string2 or string2[:6] in string1:
        return True
    # Calculate Jaccard similarity
    return get_jaccard_similarity(string1, string2, threshold_jac) or get_cosine_similarity(string1, string2, threshold_cos)

def get_specialized_data_sources(datasource_type) -> List[SpecializedDataSource]:
    return [type(ds)() for ds in SpecializedDataSource.__subclasses__() if not inspect.signature(ds).parameters and type(ds)().type == datasource_type]
