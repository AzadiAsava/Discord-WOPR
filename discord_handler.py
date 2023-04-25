from typing import Union
import discord
from db import Database
from dto import Conversation, Message
from message_handler import MessageHandler

from sendable import Sendable
from action import ConversationCompletionAction

DiscordSendableType = Union[discord.Webhook, discord.abc.Messageable]

class DiscordSendable(Sendable):
    def __init__(self, sendable: DiscordSendableType):
        self.sendable = sendable
    async def send(self, message: str):
        await self.sendable.send(message)

class DiscordHandler(MessageHandler):
    async def handle_discord_message(self, message: discord.Message, database: Database, sendable : DiscordSendableType):
        if isinstance(sendable, discord.Interaction):
            await self.handle_discord_interaction(Message.from_message(message), database, sendable)
        else:
            await self.handle_message(Message.from_message(message), database, DiscordSendable(sendable))

    async def handle_discord_interaction(self, message: Message, database: Database, interaction: discord.Interaction):
        try:
            await interaction.response.defer()
            await interaction.delete_original_response()
        except Exception:
            pass 
        return await self.handle_message(message, database, DiscordSendable(interaction.followup))
    
