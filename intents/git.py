from __future__ import annotations
import sys
import os

from db import Database
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from abc import abstractmethod
from dataclasses import dataclass
from chatgpt import get_git_repo_and_options
from intent_classifier import Intent, IntentClassifier, Sendable, SubIntent
from action import Action, UpdateKnowledgeAction
from dto import Message
from typing import List
from actions.git import GitCloneAction
from intent_classifier import ConversationSummaryAction

@dataclass
class GitIntent(Intent):
    name:str="Git Intent"
    description:str="Looks like a command or request to invoke git or use git to do something in any way."
    async def get_actions(self, message: Message, database : Database, sendable : Sendable) -> List[Action]:
            await sendable.send("I think you want me to do something with Git. One moment please...")
            intent_classifier = IntentClassifier()
            intent = await intent_classifier.classify_intent(message, GitSubIntent.__subclasses__())
            actions = await intent().get_actions(message, database, sendable) # type: ignore
            return actions
@dataclass
class GitSubIntent(SubIntent):
    name:str = "Git Sub Intents."
    description:str = "Base class for Git Sub Intents."
    @abstractmethod
    async def get_actions(self, message:Message, database : Database, sendable : Sendable) -> List[Action]:
        raise NotImplementedError("Not implemented")
    
@dataclass
class GitCloneIntent(GitSubIntent):
    name:str="Git Clone Intent"
    description:str="An explicit command or request to clone a git repository."
    async def get_actions(self, message: Message, database : Database, sendable : Sendable) -> List[Action]:
        repo = await get_git_repo_and_options(message.text)
        if repo is None:
            return [] #TODO: return an error message
        return [GitCloneAction(repo), ConversationSummaryAction(), UpdateKnowledgeAction()]
        