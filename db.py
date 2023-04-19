from __future__ import annotations
import discord
from tinydb import TinyDB, Query
from tinydb.queries import QueryInstance
from typing import List, Optional, Type, Any, Union
import jsonpickle
from tinydb_serialization import Serializer
from tinydb_serialization import SerializationMiddleware
from tinydb.storages import JSONStorage
from dto import Conversation
from dto import User, UserConversation
from external_datasource import DataSource

UserUnion = Union[User, discord.User]
class JSONSerializer(Serializer):
    OBJ_CLASS : Type[object] = object

    def encode(self, obj):
        return jsonpickle.encode(obj)

    def decode(self, s):
        return jsonpickle.decode(s)
 
from tinydb import TinyDB, Query

def get_user_query(user: UserUnion, query : Query = Query()) -> QueryInstance:
    return query.user_id == str(user.id)

def get_conversation_query(user: UserUnion, conversation_id : str, query = Query()) -> QueryInstance:
    user_query = get_user_query(user, query)
    return user_query and query.conversation_id == conversation_id
    
class Database:
    def __init__(self, db_path="db.json"):
        middleware = SerializationMiddleware(JSONStorage)
        middleware.register_serializer(JSONSerializer(), "jsonpickle")
        self.db = TinyDB(db_path, indent=4, separators=(',', ': '), ensure_ascii=False, storage=middleware) 
        self.preferences = self.db.table("preferences")
        self.conversations = self.db.table("conversations")
        self.current_conversation = self.db.table("current_conversation")
        self.knowledge = self.db.table("knowledge")
        self.datasources = self.db.table("datasources")

    def get_preferences(self, user : UserUnion) -> dict[str, str]:
        if not self.preferences.contains(get_user_query(user)):
            return {}
        else:
            return self.preferences.search(get_user_query(user))[0].get("preferences", {})
        
    def get_preference(self, user_id, preference_name, default=None) -> Optional[str]:
        return self.get_preferences(user_id).get(preference_name, default)
    
    def set_preference(self, user : UserUnion, preference_name, preference_value):
        if not self.preferences.contains(get_user_query(user)):
            self.preferences.insert({"user_id": str(user.id), "preferences": {preference_name: preference_value}})
        else:
            preferences = self.preferences.search(get_user_query(user))[0].get("preferences", {})
            preferences[preference_name] = preference_value
            self.preferences.update({"preferences": preferences}, get_user_query(user))

    def delete_preference(self, user : UserUnion, preference_name):
        if not self.preferences.contains(get_user_query(user)):
            return
        else:
            preferences = self.preferences.search(get_user_query(user))[0].get("preferences", {})
            del preferences[preference_name]
            self.preferences.update({"preferences": preferences}, get_user_query(user))

    def get_datasources(self, user : UserUnion) -> dict[str, DataSource]:
        if not self.datasources.contains(get_user_query(user)):
            return {}
        else:
            return self.datasources.search(get_user_query(user))[0].get("datasources", {})
        
    def get_datasource(self, user : UserUnion, datasource_name) -> Optional[DataSource]:
        return self.get_datasources(user).get(datasource_name, None)
    
    def set_datasource(self, user : UserUnion, datasource : DataSource):
        if not self.datasources.contains(get_user_query(user)):
            self.datasources.insert({"user_id": str(user.id), "datasources": {}})
        datasources = self.datasources.search(get_user_query(user))[0].get("datasources", {})
        datasources[datasource.name] = datasource
        self.datasources.update({"datasources": datasources}, get_user_query(user))

    def delete_datasource(self, user : UserUnion, datasource_name):

        if not self.datasources.contains(get_user_query(user)):
            return
        else:
            datasources = self.datasources.search(get_user_query(user))[0].get("datasources", {})
            del datasources[datasource_name]
            self.datasources.update({"datasources": datasources}, get_user_query(user))

    def get_conversations(self, user : UserUnion) -> List[Conversation]:
        result = self.conversations.search(get_user_query(user))
        return [r.get("conversation", None) for r in result]
    
    def get_conversation(self, user : UserUnion, conversation_id : str) -> Optional[Conversation]:
        result = self.conversations.get(get_conversation_query(user, conversation_id))
        if result is None:
            return None
        return result.get("conversation", None)    
    def set_conversation(self, user: UserUnion, conversation : Conversation):
        self.conversations.upsert(UserConversation(user_id=str(user.id), conversation=conversation, conversation_id=conversation.id).__dict__, get_conversation_query(user, conversation.id))

    def delete_conversation(self, user: UserUnion, conversation_id : str):
        return self.conversations.remove(get_conversation_query(user, conversation_id))

    def set_current_conversation(self, user: UserUnion, conversation : Conversation):
        self.current_conversation.upsert({"user_id":str(user.id), "conversation_id": conversation.id}, get_user_query(user))

    def get_current_conversation(self, user : UserUnion) -> Optional[Conversation]:
        if not self.current_conversation.contains(get_user_query(user)):
            return None
        conversation_id = self.current_conversation.search(get_user_query(user))[0].get("conversation_id", None)
        if conversation_id is None:
            return None
        return self.get_conversation(user, conversation_id)
    
    def get_knowledge(self, user : UserUnion) -> str:
        if not self.knowledge.contains(get_user_query(user)):
            return ""
        else:
            return self.knowledge.search(get_user_query(user))[0].get("knowledge", {})
        
    def set_knowledge(self, user : UserUnion, knowledge : str):
        self.knowledge.upsert({"user_id":str(user.id), "knowledge": knowledge}, get_user_query(user))