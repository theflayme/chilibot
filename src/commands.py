import discord
from discord import app_commands
from src.database_firebase import (
    get_settings, save_settings, init_owners, owners_cache, is_owner, save_capt,
    add_to_blacklist, get_blacklist, get_blacklist_report_channel
)
from src.permissions import requires_approver, requires_command_permission, check_command_permission, universal_permission_check
from src.views import FormMessageModal, CaptView


class CommandHandler:
    def __init__(self, bot: discord.Client):
        self._bot = bot
    
    async def handle_error(self, interaction: discord.Interaction, error_message: str) -> None:
        if interaction.response.is_done():
            await interaction.followup.send(error_message, ephemeral=True)
        else:
            await interaction.response.send_message(error_message, ephemeral=True)
    
    @property
    def bot(self) -> discord.Client:
        return self._bot


class BaseCommand(CommandHandler):
    def __init__(self, bot: discord.Client):
        super().__init__(bot)
    
    async def validate_guild(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            await self.handle_error(interaction, "❌ Эта команда доступна только на сервере.")
            return False
        return True