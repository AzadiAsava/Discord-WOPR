from chatgpt import send_to_ChatGPT
class Conversation:
    def __init__(self, user, system="You are a helpful AI assistant.", assistant=None, mode=lambda x: x):
        self.user = user
        self.messages = [
            {"role":"system","content":system}
        ]
        if assistant is not None:
            self.messages.append({"role":"assistant","content":assistant})
        self.mode = mode

    def add_user(self, user):
        user = self.mode(user)
        self.messages.append({"role":"user","content":user})
    def add_system(self, system):
        self.messages.append({"role":"system","content":system})
    def add_assistant(self, assistant):
        self.messages.append({"role":"assistant","content":assistant})
    def get_conversation(self):
        return self.messages
    def get_user(self):
        return self.user
    def get_system(self):
        return self.messages[0]["content"]
    def delete_last_message(self):
        self.messages.pop()
    def __str__(self):
        convo = ""
        for message in self.messages:
            convo += message["role"] + ": " + message["content"] + "\n"
        return convo
    def __len__(self):
        return len(self.messages)
    def __iter__(self):
        return iter(self.messages)
    def __getitem__(self, index):
        return self.messages[index]
    def __setitem__(self, index, value):
        self.messages[index] = value
    def __delitem__(self, index):
        del self.messages[index]
    def __add__(self, other):
        return Conversation(self.user, self.messages + other.messages)
    def __eq__(self, other):
        return self.messages == other.messages
    def __ne__(self, other):
        return self.user != other.user or self.messages != other.messages

class ConversationManager:
    def __init__(self):
        self.conversations = {}
    def update_current_conversation(self, user, user_input):
        return self.update_conversation(user, user_input)
    def update_conversation(self, user, user_input, conversation=None):
        if conversation is None:
            conversation = self.get_current_conversation(user)
        conversation.add_user(user_input)
        content = send_to_ChatGPT(conversation.get_conversation())
        conversation.add_assistant(content)
        return content
    def add_conversation(self, conversation):
        if conversation.get_user() not in self.conversations:
            self.conversations[conversation.get_user()] = []    
        self.conversations[conversation.get_user()].insert(0, conversation)
        return conversation
    def get_conversations(self, user):
        if user not in self.conversations:
            return []
        return self.conversations[user]
    def get_current_conversation(self, user):
        if user not in self.conversations:
            return self.start_new_conversation(user)
        return self.conversations[user][0]
    def delete_conversation(self, user, index):
        if user not in self.conversations:
            return
        del self.conversations[user][index]
    def switch_to_conversation(self, user, index):
        if user not in self.conversations:
            self.start_new_conversation(user)    
        else:
            convo = self.conversations[user].pop(index)
            self.conversations[user].insert(0, convo)
        return self.get_current_conversation(user)
    def start_new_conversation(self, user, system="You are a helpful AI assistant.", assistant=None, mode=lambda x : x):
        convo = Conversation(user, system, assistant=assistant, mode=mode)
        self.add_conversation(convo)
        return convo
    