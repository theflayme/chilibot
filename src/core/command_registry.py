from typing import Dict, Optional, List
import discord
from discord import app_commands
import json
import os
from .interfaces import ICommand, ICommandRegistry
from .command_factory import command_factory
from src.permissions import universal_permission_check


class SlashCommandConfigLoader:
    
    @staticmethod
    def load_config() -> Dict[str, dict]:
        config_path = os.path.join(os.path.dirname(__file__), 'slash_config.json')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return SlashCommandConfigLoader._parse_parameter_types(config)
        except FileNotFoundError:
            print(f"❌ Файл конфигурации {config_path} не найден!")
            return {}
        except json.JSONDecodeError as e:
            print(f"❌ Ошибка парсинга JSON: {e}")
            return {}
    
    @staticmethod
    def _parse_parameter_types(config: Dict[str, dict]) -> Dict[str, dict]:
        for command_name, command_config in config.items():
            if 'parameters' in command_config:
                for param_name, param_config in command_config['parameters'].items():
                    if param_config.get('type') == 'TextChannel':
                        param_config['type'] = discord.TextChannel
                    elif param_config.get('type') == 'Role':
                        param_config['type'] = discord.Role
                    elif param_config.get('type') == 'int':
                        param_config['type'] = int
                    elif param_config.get('type') == 'str':
                        param_config['type'] = str
        return config


class CommandWrapperFactory:
    
    @staticmethod
    def create_wrapper(command: ICommand, parameters: dict):
        if not parameters:
            return CommandWrapperFactory._create_no_params_wrapper(command)
        
        if len(parameters) == 1 and "channel" in parameters:
            return CommandWrapperFactory._create_channel_wrapper(command, parameters)
        
        if len(parameters) == 2 and "approver" in parameters and "approved" in parameters:
            return CommandWrapperFactory._create_role_pair_wrapper(command)
        
        if "max_members" in parameters:
            return CommandWrapperFactory._create_max_members_wrapper(command, parameters)
        
        if "static_id_majestic" in parameters:
            return CommandWrapperFactory._create_blacklist_wrapper(command)
        
        if "user_id" in parameters and len(parameters) == 1:
            return CommandWrapperFactory._create_user_id_wrapper(command)
        
        return CommandWrapperFactory._create_no_params_wrapper(command)
    
    @staticmethod
    def _create_no_params_wrapper(command: ICommand):
        async def wrapper(interaction: discord.Interaction) -> None:
            await command.execute(interaction)
        return wrapper
    
    @staticmethod
    def _create_channel_wrapper(command: ICommand, parameters: dict):
        param_config = parameters["channel"]
        if param_config.get("required", True):
            async def wrapper(interaction: discord.Interaction, channel: discord.TextChannel) -> None:
                await command.execute(interaction, channel=channel)
        else:
            async def wrapper(interaction: discord.Interaction, channel: discord.TextChannel = None) -> None:
                await command.execute(interaction, channel=channel)
        return wrapper
    
    @staticmethod
    def _create_role_pair_wrapper(command: ICommand):
        async def wrapper(interaction: discord.Interaction, approver: discord.Role, approved: discord.Role) -> None:
            await command.execute(interaction, approver=approver, approved=approved)
        return wrapper
    
    @staticmethod
    def _create_max_members_wrapper(command: ICommand, parameters: dict):
        if "timer_minutes" in parameters:
            async def wrapper(interaction: discord.Interaction, max_members: int, timer_minutes: int = None) -> None:
                await command.execute(interaction, max_members=max_members, timer_minutes=timer_minutes)
        else:
            async def wrapper(interaction: discord.Interaction, max_members: int) -> None:
                await command.execute(interaction, max_members=max_members)
        return wrapper
    
    @staticmethod
    def _create_blacklist_wrapper(command: ICommand):
        async def wrapper(interaction: discord.Interaction, user_id: str, static_id_majestic: str, reason: str) -> None:
            await command.execute(interaction, user_id=user_id, static_id_majestic=static_id_majestic, reason=reason)
        return wrapper
    
    @staticmethod
    def _create_user_id_wrapper(command: ICommand):
        async def wrapper(interaction: discord.Interaction, user_id: str) -> None:
            await command.execute(interaction, user_id=user_id)
        return wrapper


class SlashCommandBuilder:
    
    def __init__(self, bot: discord.Client):
        self._bot = bot
    
    def create_slash_command(self, command: ICommand, config: dict) -> None:
        command_name = command.name
        description = config["description"]
        parameters = config.get("parameters", {})
        
        wrapper_func = CommandWrapperFactory.create_wrapper(command, parameters)
        
        slash_command = app_commands.Command(
            name=command_name,
            description=description,
            callback=wrapper_func
        )
        
        if parameters:
            descriptions = {name: config["description"] for name, config in parameters.items()}
            slash_command = app_commands.describe(**descriptions)(slash_command)
        
        slash_command = universal_permission_check()(slash_command)
        
        self._bot.tree.add_command(slash_command)


class CommandRegistry(ICommandRegistry):
    
    def __init__(self, bot: discord.Client):
        self._bot = bot
        self._commands: Dict[str, ICommand] = {}
        self._slash_commands_config = SlashCommandConfigLoader.load_config()
        self._slash_command_builder = SlashCommandBuilder(bot)
    
    def register_command(self, command: ICommand) -> None:
        self._commands[command.name] = command
    
    def get_command(self, name: str) -> Optional[ICommand]:
        return self._commands.get(name)
    
    def get_all_commands(self) -> Dict[str, ICommand]:
        return self._commands.copy()
    
    async def setup_slash_commands(self) -> None:
        self._create_commands_from_factory()
        await self._register_slash_commands()
    
    def _create_commands_from_factory(self) -> None:
        command_types = command_factory.get_available_command_types()
        
        for command_type in command_types:
            try:
                command = command_factory.create_command(command_type, self._bot)
                self.register_command(command)
            except Exception as e:
                print(f"❌ Ошибка создания команды {command_type}: {e}")
    
    async def _register_slash_commands(self) -> None:
        for command_name, command in self._commands.items():
            if command_name in self._slash_commands_config:
                config = self._slash_commands_config[command_name]
                self._slash_command_builder.create_slash_command(command, config)
    
    def unregister_command(self, name: str) -> bool:
        if name in self._commands:
            del self._commands[name]
            print(f"🗑️ Команда {name} удалена")
            return True
        return False
    
    def get_command_count(self) -> int:
        return len(self._commands)
    
    def get_command_names(self) -> List[str]:
        return list(self._commands.keys())