from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import discord


class ICommand(ABC):
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        pass
    
    @abstractmethod
    async def execute(self, interaction: discord.Interaction, **kwargs) -> None:
        pass
    
    @abstractmethod
    async def validate(self, interaction: discord.Interaction) -> bool:
        pass


class ICommandHandler(ABC):
    
    @abstractmethod
    async def handle_error(self, interaction: discord.Interaction, error_message: str) -> None:
        pass
    
    @abstractmethod
    async def validate_guild(self, interaction: discord.Interaction) -> bool:
        pass


class ICommandRegistry(ABC):
    
    @abstractmethod
    def register_command(self, command: ICommand) -> None:
        pass
    
    @abstractmethod
    def get_command(self, name: str) -> Optional[ICommand]:
        pass
    
    @abstractmethod
    def get_all_commands(self) -> Dict[str, ICommand]:
        pass
    
    @abstractmethod
    async def setup_slash_commands(self) -> None:
        pass


class ICommandFactory(ABC):
    
    @abstractmethod
    def create_command(self, command_type: str, bot: discord.Client, **kwargs) -> ICommand:
        pass
    
    @abstractmethod
    def register_command_type(self, command_type: str, command_class: type) -> None:
        pass


class IPermissionManager(ABC):
    
    @abstractmethod
    async def check_permission(self, interaction: discord.Interaction, command_name: str) -> bool:
        pass
    
    @abstractmethod
    async def has_role_permission(self, guild_id: int, role_id: int, command_name: str) -> bool:
        pass
    
    @abstractmethod
    async def set_role_permissions(self, guild_id: int, role_id: int, permissions: List[str]) -> bool:
        pass


class IModuleManager(ABC):
    
    @abstractmethod
    def load_module(self, module_name: str) -> None:
        pass
    
    @abstractmethod
    def unload_module(self, module_name: str) -> None:
        pass
    
    @abstractmethod
    def reload_module(self, module_name: str) -> None:
        pass
    
    @abstractmethod
    def get_loaded_modules(self) -> List[str]:
        pass