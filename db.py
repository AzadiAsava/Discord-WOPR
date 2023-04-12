from __future__ import annotations
from tinydb import TinyDB, Query
from typing import Optional, Type
import jsonpickle
from tinydb_serialization import Serializer
from tinydb_serialization import SerializationMiddleware
from tinydb.storages import JSONStorage
from conversation import Conversation

class JSONSerializer(Serializer):
    OBJ_CLASS : Type[object] = object

    def encode(self, obj):
        return jsonpickle.encode(obj)

    def decode(self, s):
        return jsonpickle.decode(s)
    
    
class Database:
    def __init__(self, db_path="db.json"):
        middleware = SerializationMiddleware(JSONStorage)
        middleware.register_serializer(JSONSerializer(), "jsonpickle")
        self.db = TinyDB(db_path, indent=4, separators=(',', ': '), ensure_ascii=False, storage=middleware) 
        self.preferences = self.db.table("preferences")
        self.conversations = self.db.table("conversations")
        self.knowledge = self.db.table("knowledge")


    def get_preferences(self, user_id) -> dict:
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

    def get_conversations(self, user_id) -> dict:
        query = Query()
        if not self.conversations.contains(query.user_id == user_id):
            return {}
        else:
            return self.conversations.search(query.user_id == user_id)[0].get("conversations", {})
    
    def get_conversation(self, user_id, conversation_id) -> Optional[Conversation]:
        return self.get_conversations(user_id).get(conversation_id, None)

    def set_conversation(self, user_id, conversation):
        query = Query()
        if not self.conversations.contains(query.user_id == user_id):
            self.conversations.insert({"user_id": user_id, "conversations": {conversation.id: conversation}})
        else:
            conversations = self.conversations.search(query.user_id == user_id)[0].get("conversations", {})
            conversations[conversation.id] = conversation
            self.conversations.update({"conversations": conversations}, query.user_id == user_id)

    def delete_conversation(self, user_id, conversation_id):
        query = Query()
        if not self.conversations.contains(query.user_id == user_id):
            return
        else:
            conversations = self.conversations.search(query.user_id == user_id)[0].get("conversations", {})
            del conversations[conversation_id]
            self.conversations.update({"conversations": conversations}, query.user_id == user_id)

    def set_current_conversation(self, user_id, conversation_id):
        query = Query()
        if not self.db.contains(query.user_id == user_id):
            self.db.insert({"user_id": user_id, "current_conversation": conversation_id})
        else:
            self.db.update({"current_conversation": conversation_id}, query.user_id == user_id)

    def get_current_conversation(self, user_id) -> Optional[dict]:
        query = Query()
        if not self.db.contains(query.user_id == user_id):
            return None
        else:
            return self.db.search(query.user_id == user_id)[0].get("current_conversation", None)
        
    def get_knowledge(self, user_id) -> str:
        query = Query()
        if not self.knowledge.contains(query.user_id == user_id):
            return ""
        else:
            return self.knowledge.search(query.user_id == user_id)[0].get("knowledge", {})
        
    def set_knowledge(self, user_id, knowledge: str):
        query = Query()
        if not self.knowledge.contains(query.user_id == user_id):
            self.knowledge.insert({"user_id": user_id, "knowledge": knowledge})
        else:
            self.knowledge.update({"knowledge": knowledge}, query.user_id == user_id)