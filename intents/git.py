from __future__ import annotations
import sys
import os
from db import Database
from intent import Intent, NoOpIntent, SubIntent
from sendable import Sendable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from abc import abstractmethod
from dataclasses import dataclass
from chatgpt import get_git_repo_and_options
from intent_classifier import IntentClassifier
from action import Action
from dto import Message
from typing import List
from actions.git import GitCloneAction

@dataclass
class GitIntent(Intent):
    @staticmethod
    def get_descriptions() -> List[str]:
        return ["Something to do with git."]
    @staticmethod
    async def get_actions(message: Message, database : Database, sendable : Sendable) -> List[Action]:
        await sendable.send("I think you want me to do something with Git. One moment please...")
        intent_classifier = IntentClassifier()
        intent = await intent_classifier.classify_intent(message, GitSubIntent.__subclasses__())
        actions = await intent().get_actions(message, database, sendable) # type: ignore
        return actions
@dataclass
class GitSubIntent(SubIntent):
    @staticmethod
    def get_descriptions() -> List[str]:
        return ["Base class for Git Sub Intents."]
    @abstractmethod
    @staticmethod
    async def get_actions(message:Message, database : Database, sendable : Sendable) -> List[Action]:
        raise NotImplementedError("Not implemented")
    
@dataclass
class GitCloneIntent(GitSubIntent):
    @staticmethod
    def get_descriptions() -> List[str]:
        return ["An explicit command or request to clone a git repository."]
    @staticmethod
    async def get_actions(message: Message, database : Database, sendable : Sendable) -> List[Action]:
        repo = await get_git_repo_and_options(message.text)
        if repo is None:
            return [] #TODO: return an error message
        return [GitCloneAction(repo)] + await NoOpIntent.get_actions(message, database, sendable)
        