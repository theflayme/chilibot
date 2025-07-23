"""
Базовые классы для системы команд
"""

from typing import Any, Dict, Optional
import discord
from .interfaces import ICommand, ICommandHandler


class CommandHandler(ICommandHandler):
    """Базовый обработчик команд"""
    
    def __init__(self, bot: discord.Client):
        self._bot = bot
    
    async def handle_error(self, interaction: discord.Interaction, error_message: str) -> None:
        """Обработать ошибку команды"""
        if interaction.response.is_done():
            await interaction.followup.send(error_message, ephemeral=True)
        else:
            await interaction.response.send_message(error_message, ephemeral=True)
    
    async def validate_guild(self, interaction: discord.Interaction) -> bool:
        """Проверить, что команда выполняется на сервере"""
        if interaction.guild is None:
            await self.handle_error(interaction, "❌ Эта команда доступна только на сервере.")
            return False
        return True


class BaseCommand(CommandHandler, ICommand):
    """Базовый класс для команд бота"""
    
    def __init__(self, bot: discord.Client, name: str, description: str):
        super().__init__(bot)
        self._name = name
        self._description = description
    
    @property
    def name(self) -> str:
        """Имя команды"""
        return self._name
    
    @property 
    def description(self) -> str:
        """Описание команды"""
        return self._description
    
    async def validate(self, interaction: discord.Interaction) -> bool:
        """Базовая валидация команды"""
        return await self.validate_guild(interaction)
    
    async def execute(self, interaction: discord.Interaction, **kwargs) -> None:
        """Выполнить команду - должно быть переопределено в наследниках"""
        raise NotImplementedError("Метод execute должен быть реализован в наследнике")


class GuildCommand(BaseCommand):
    """Команда, которая требует выполнения на сервере"""
    
    async def validate(self, interaction: discord.Interaction) -> bool:
        """Проверить, что команда выполняется на сервере"""
        return await self.validate_guild(interaction)


class OwnerCommand(BaseCommand):
    """Команда только для владельцев бота"""
    
    async def validate(self, interaction: discord.Interaction) -> bool:
        """Проверить, что пользователь является владельцем"""
        from src.database_firebase import is_owner
        
        if not await super().validate(interaction):
            return False
            
        if not is_owner(interaction.user.id):
            await self.handle_error(interaction, "❌ Эта команда доступна только владельцам бота.")
            return False
            
        return True


class PermissionCommand(GuildCommand):
    """Команда с проверкой разрешений через систему ролей"""
    
    def __init__(self, bot: discord.Client, name: str, description: str, required_permission: str):
        super().__init__(bot, name, description)
        self._required_permission = required_permission
    
    @property
    def required_permission(self) -> str:
        """Требуемое разрешение для команды"""
        return self._required_permission
    
    async def validate(self, interaction: discord.Interaction) -> bool:
        """Проверить разрешения на выполнение команды"""
        if not await super().validate(interaction):
            return False
            
        from src.permissions import check_command_permission
        from src.database_firebase import is_owner
        
        # Владельцы имеют доступ ко всем командам
        if is_owner(interaction.user.id):
            return True
            
        # Проверяем разрешения роли
        has_permission = await check_command_permission(interaction, self._required_permission)
        if not has_permission:
            await self.handle_error(
                interaction, 
                f"❌ У вас нет прав для использования команды `/{self.name}`. Обратитесь к администрации."
            )
            return False
            
        return True 