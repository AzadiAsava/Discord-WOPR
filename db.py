from __future__ import annotations
from tinydb import TinyDB, Query
from typing import List, Optional, Type, Any
import jsonpickle
from tinydb_serialization import Serializer
from tinydb_serialization import SerializationMiddleware
from tinydb.storages import JSONStorage
from dto import Conversation
from dto import User, UserConversation
from external_datasource import DataSource

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
        self.datasources = self.db.table("datasources")

    def get_preferences(self, user_id) -> dict:
        query = Query()
        if not self.preferences.contains(query.user_id == user_id):
            return {}
        else:
            return self.preferences.search(query.user_id == user_id)[0].get("preferences", {})
        
    def get_preference(self, user_id, preference_name, default=None) -> str:
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

    def get_datasources(self, user_id) -> dict[str, DataSource]:
        query = Query()
        if not self.datasources.contains(query.user_id == user_id):
            return {}
        else:
            return self.datasources.search(query.user_id == user_id)[0].get("datasources", {})
        
    def get_datasource(self, user_id, datasource_name) -> Optional[DataSource]:
        return self.get_datasources(user_id).get(datasource_name, None)
    
    def set_datasource(self, user_id, datasource):
        query = Query()
        if not self.datasources.contains(query.user_id == user_id):
            self.datasources.insert({"user_id": user_id, "datasources": {datasource.name: datasource}})
        else:
            datasources = self.datasources.search(query.user_id == user_id)[0].get("datasources", {})
            datasources[datasource.name] = datasource
            self.datasources.update({"datasources": datasources}, query.user_id == user_id)

    def delete_datasource(self, user_id, datasource_name):
        query = Query()
        if not self.datasources.contains(query.user_id == user_id):
            return
        else:
            datasources = self.datasources.search(query.user_id == user_id)[0].get("datasources", {})
            del datasources[datasource_name]
            self.datasources.update({"datasources": datasources}, query.user_id == user_id)

    def get_conversations(self, user : User) -> List[UserConversation]:
        query = Query()
        if not self.conversations.contains(query.user.id == user.id):
            return {}
        else:
            return self.conversations.search(query.user.id == user.id)[0].get("conversations", {})
    
    def get_conversation(self, user : User, conversation_id : str) -> Optional[Conversation]:
        query = Query()
        return self.conversations.get(query.user.id == user.id and query.conversation.id == conversation_id).get("conversation", None)

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

    def get_current_conversation(self, user_id) -> Optional[str]:
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