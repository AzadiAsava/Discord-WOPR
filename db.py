from tinydb import TinyDB, Query
from typing import Optional
import jsonpickle

class Database:
    def __init__(self, db_path="db.json"):
        self.db = TinyDB(db_path, indent=4, separators=(',', ': '), ensure_ascii=False)
        self.db.serializer = lambda x: jsonpickle.encode(x)
        self.db.deserializer = lambda x: jsonpickle.decode(x)
        self.preferences = self.db.table("preferences")
        self.conversations = self.db.table("conversations")
        self.knowledge = self.db.table("knowledge")


    def get_preferences(self, user_id) -> Optional[dict]:
        query = Query()
        if not self.preferences.contains(query.user_id == user_id):
            return {}
        else:
            return self.preferences.search(query.user_id == user_id)[0].get("preferences", {})
        
    def get_preference(self, user_id, preference_name, default=None) -> Optional[str]:
        return self.get_preferences(user_id).get(preference_name, default)
    
    def set_preference(self, user_id, preference_name, preference_value):
        query = Query()
        if not self.preferences.contains(query.user_id == user_id):
            self.preferences.insert({"user_id": user_id, "preferences": {preference_name: preference_value}})
        else:
            preferences = self.preferences.search(query.user_id == user_id)[0].get("preferences", {})
            preferences[preference_name] = preference_value
            self.preferences.update({"preferences": preferences}, query.user_id == user_id)

    def delete_preference(self, user_id, preference_name):
        query = Query()
        if not self.preferences.contains(query.user_id == user_id):
            return
        else:
            preferences = self.preferences.search(query.user_id == user_id)[0].get("preferences", {})
            del preferences[preference_name]
            self.preferences.update({"preferences": preferences}, query.user_id == user_id)

    def get_conversations(self, user_id) -> Optional[dict]:
        query = Query()
        if not self.conversations.contains(query.user_id == user_id):
            return {}
        else:
            return self.conversations.search(query.user_id == user_id)[0].get("conversations", {})
    
    def get_conversation(self, user_id, conversation_id) -> Optional[dict]:
        return self.get_conversations(user_id).get(conversation_id, None)

    def set_conversation(self, user_id, conversation):
        if not self.conversations.contains(self.query.user_id == user_id):
            self.conversations.insert({"user_id": user_id, "conversations": {conversation.id: conversation}})
        else:
            conversations = self.conversations.search(self.query.user_id == user_id).get("conversations", {})
            conversations[conversation.id] = conversation
            self.conversations.update({"conversations": conversations}, self.query.user_id == user_id)

    def delete_conversation(self, user_id, conversation_id):
        if not self.conversations.contains(self.query.user_id == user_id):
            return
        else:
            conversations = self.conversations.search(self.query.user_id == user_id).get("conversations", {})
            del conversations[conversation_id]
            self.conversations.update({"conversations": conversations}, self.query.user_id == user_id)

    def set_current_conversation(self, user_id, conversation_id):
        if not self.conversations.contains(self.query.user_id == user_id):
            self.conversations.insert({"user_id": user_id, "current_conversation": conversation_id})
        else:
            self.conversations.update({"current_conversation": conversation_id}, self.query.user_id == user_id)

    def get_current_conversation(self, user_id) -> Optional[dict]:
        if not self.db.contains(self.query.user_id == user_id):
            return {}
        else:
            return self.get_conversation(user_id, self.db.search(self.query.user_id == user_id).get("current_conversation", None))
    
    def get_knowledge(self, user_id) -> Optional[dict]:
        query = Query()
        if not self.knowledge.contains(query.user_id == user_id):
            return {}
        else:
            return self.knowledge.search(query.user_id == user_id)[0].get("knowledge", {})
        
    def get_knowledge_item(self, user_id, knowledge_name, default=None) -> Optional[str]:
        return self.get_knowledge(user_id).get(knowledge_name, default)
    
    def set_knowledge_item(self, user_id, knowledge_name, knowledge_value):
        query = Query()
        if not self.knowledge.contains(query.user_id == user_id):
            self.knowledge.insert({"user_id": user_id, "knowledge": {knowledge_name: knowledge_value}})
        else:
            knowledge = self.knowledge.search(query.user_id == user_id)[0].get("knowledge", {})
            knowledge[knowledge_name] = knowledge_value
            self.knowledge.update({"knowledge": knowledge}, query.user_id == user_id)
    
    def delete_knowledge_item(self, user_id, knowledge_name):
        query = Query()
        if not self.knowledge.contains(query.user_id == user_id):
            return
        else:
            knowledge = self.knowledge.search(query.user_id == user_id)[0].get("knowledge", {})
            del knowledge[knowledge_name]
            self.knowledge.update({"knowledge": knowledge}, query.user_id == user_id)
    