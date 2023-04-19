from __future__ import annotations
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from action import Action
from dto import Message
from intent_classifier import Sendable
from db import Database
from chatgpt import get_git_repo_and_options
import os
from subprocess import Popen, PIPE

class GitCloneAction(Action):
    def __init__(self, repo : dict[str, str]):
        super().__init__("Git Clone Action", "Clone a git repository.")
        self.repo = repo
    async def __call__(self, message : Message, database : Database, sendable : Sendable) -> None:
        result = do_command(self.repo)
        if result:
            await sendable.send(result)
        else:
            await sendable.send("Successfully cloned into: " + self.repo["repo"])
            conversation = database.get_current_conversation(message.user)
            if conversation is None:
                raise ValueError("No conversation found.")
            conversation.add_system("A git repository called " + self.repo["repo"] + " has been cloned from " + self.repo["url"] + " with the options: " + self.repo["options"])
            database.set_conversation(message.user, conversation)

def invoke_at(path: str):
    def parameterized(func):
        def wrapper(*args, **kwargs):
            os.makedirs(path, exist_ok=True)
            cwd = os.getcwd()
            os.chdir(path)

            try:
                ret = func(*args, **kwargs)
            finally:
                os.chdir(cwd)

            return ret

        return wrapper

    return parameterized 

@invoke_at("scratch/git")
def do_command(command : dict[str, str]) -> str:
    if command["executable"] != "git":
        raise ValueError("Command is not a git command.")
    command_str = f"git {command['command']} {command['url']} {command['options']}"
    process = Popen(command_str, stdout=PIPE, stderr=PIPE, shell=True)
    stdout, stderr = process.communicate()
    if process.returncode!= 0:
        return f"Failed to execute {command['command']}.\n{stderr.decode('utf-8')}"
    else:
        return stdout.decode('utf-8')


#do_command({"executable": "git", "command": "clone", "url": "https://github.com/tsavo/image-processor", "options": ""})
