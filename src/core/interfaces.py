"""
Интерфейсы для системы команд бота
Обеспечивают расширяемость и соблюдение принципов ООП
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import discord


class ICommand(ABC):
    """Интерфейс команды бота"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Имя команды"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Описание команды"""
        pass
    
    @abstractmethod
    async def execute(self, interaction: discord.Interaction, **kwargs) -> None:
        """Выполнить команду"""
        pass
    
    @abstractmethod
    async def validate(self, interaction: discord.Interaction) -> bool:
        """Проверить возможность выполнения команды"""
        pass


class ICommandHandler(ABC):
    """Интерфейс обработчика команд"""
    
    @abstractmethod
    async def handle_error(self, interaction: discord.Interaction, error_message: str) -> None:
        """Обработать ошибку команды"""
        pass
    
    @abstractmethod
    async def validate_guild(self, interaction: discord.Interaction) -> bool:
        """Проверить, что команда выполняется на сервере"""
        pass


class ICommandRegistry(ABC):
    """Интерфейс реестра команд"""
    
    @abstractmethod
    def register_command(self, command: ICommand) -> None:
        """Зарегистрировать команду"""
        pass
    
    @abstractmethod
    def get_command(self, name: str) -> Optional[ICommand]:
        """Получить команду по имени"""
        pass
    
    @abstractmethod
    def get_all_commands(self) -> Dict[str, ICommand]:
        """Получить все команды"""
        pass
    
    @abstractmethod
    async def setup_slash_commands(self) -> None:
        """Настроить slash команды Discord"""
        pass


class ICommandFactory(ABC):
    """Интерфейс фабрики команд"""
    
    @abstractmethod
    def create_command(self, command_type: str, bot: discord.Client, **kwargs) -> ICommand:
        """Создать команду указанного типа"""
        pass
    
    @abstractmethod
    def register_command_type(self, command_type: str, command_class: type) -> None:
        """Зарегистрировать тип команды"""
        pass


class IPermissionManager(ABC):
    """Интерфейс менеджера разрешений"""
    
    @abstractmethod
    async def check_permission(self, interaction: discord.Interaction, command_name: str) -> bool:
        """Проверить разрешение на выполнение команды"""
        pass
    
    @abstractmethod
    async def has_role_permission(self, guild_id: int, role_id: int, command_name: str) -> bool:
        """Проверить разрешение роли на команду"""
        pass
    
    @abstractmethod
    async def set_role_permissions(self, guild_id: int, role_id: int, permissions: List[str]) -> bool:
        """Установить разрешения для роли"""
        pass


class IModuleManager(ABC):
    """Интерфейс менеджера модулей"""
    
    @abstractmethod
    def load_module(self, module_name: str) -> None:
        """Загрузить модуль"""
        pass
    
    @abstractmethod
    def unload_module(self, module_name: str) -> None:
        """Выгрузить модуль"""
        pass
    
    @abstractmethod
    def reload_module(self, module_name: str) -> None:
        """Перезагрузить модуль"""
        pass
    
    @abstractmethod
    def get_loaded_modules(self) -> List[str]:
        """Получить список загруженных модулей"""
        pass 