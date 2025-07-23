from typing import Any, Dict, Optional
import discord
from .interfaces import ICommand, ICommandHandler


class CommandHandler(ICommandHandler):
    
    def __init__(self, bot: discord.Client):
        self._bot = bot
    
    async def handle_error(self, interaction: discord.Interaction, error_message: str) -> None:
        if interaction.response.is_done():
            await interaction.followup.send(error_message, ephemeral=True)
        else:
            await interaction.response.send_message(error_message, ephemeral=True)
    
    async def validate_guild(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            await self.handle_error(interaction, "❌ Эта команда доступна только на сервере.")
            return False
        return True


class BaseCommand(CommandHandler, ICommand):
    
    def __init__(self, bot: discord.Client, name: str, description: str):
        super().__init__(bot)
        self._name = name
        self._description = description
    
    @property
    def name(self) -> str:
        return self._name
    
    @property 
    def description(self) -> str:
        return self._description
    
    async def validate(self, interaction: discord.Interaction) -> bool:
        return await self.validate_guild(interaction)
    
    async def execute(self, interaction: discord.Interaction, **kwargs) -> None:
        raise NotImplementedError("Метод execute должен быть реализован в наследнике")


class GuildCommand(BaseCommand):
    
    async def validate(self, interaction: discord.Interaction) -> bool:
        return await self.validate_guild(interaction)


class OwnerCommand(BaseCommand):
    
    async def validate(self, interaction: discord.Interaction) -> bool:
        from src.database_firebase import is_owner
        
        if not await super().validate(interaction):
            return False
            
        if not is_owner(interaction.user.id):
            await self.handle_error(interaction, "❌ Эта команда доступна только владельцам бота.")
            return False
            
        return True


class PermissionCommand(GuildCommand):
    
    def __init__(self, bot: discord.Client, name: str, description: str, required_permission: str):
        super().__init__(bot, name, description)
        self._required_permission = required_permission
    
    @property
    def required_permission(self) -> str:
        return self._required_permission
    
    async def validate(self, interaction: discord.Interaction) -> bool:
        if not await super().validate(interaction):
            return False
            
        from src.permissions import check_command_permission
        from src.database_firebase import is_owner
        
        if is_owner(interaction.user.id):
            return True
            
        has_permission = await check_command_permission(interaction, self._required_permission)
        if not has_permission:
            await self.handle_error(
                interaction, 
                f"❌ У вас нет прав для использования команды `/{self.name}`. Обратитесь к администрации."
            )
            return False
            
        return True 