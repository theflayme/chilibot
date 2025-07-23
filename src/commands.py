"""
Устаревший модуль команд - весь функционал перенесен в новую архитектуру.
Файл сохранен для обратной совместимости, но будет удален в будущих версиях.

Используйте новую архитектуру:
- src/commands_new.py - настройка команд
- src/commands/ - модули команд
- src/core/ - базовая архитектура команд
"""

import discord
from discord import app_commands
from src.database_firebase import (
    get_settings, save_settings, init_owners, owners_cache, is_owner, save_capt,
    add_to_blacklist, get_blacklist, get_blacklist_report_channel
)
from src.permissions import requires_approver, requires_command_permission, check_command_permission, universal_permission_check
from src.views import FormMessageModal, CaptView


# Базовые классы для обратной совместимости (УСТАРЕЛИ)
class CommandHandler:
    """УСТАРЕЛ: используйте новую архитектуру в src/core/"""
    def __init__(self, bot):
        self._bot = bot
    
    async def _handle_error(self, interaction: discord.Interaction, error_message: str):
        if interaction.response.is_done():
            await interaction.followup.send(error_message, ephemeral=True)
        else:
            await interaction.response.send_message(error_message, ephemeral=True)


class BaseCommand(CommandHandler):
    """УСТАРЕЛ: используйте новую архитектуру в src/core/"""
    def __init__(self, bot):
        super().__init__(bot)
    
    async def _validate_guild(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            await self._handle_error(interaction, "❌ Эта команда доступна только на сервере.")
            return False
        return True