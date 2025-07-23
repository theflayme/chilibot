"""
Реестр команд для регистрации и управления slash командами Discord
"""

from typing import Dict, Optional, List
import discord
from discord import app_commands
from .interfaces import ICommand, ICommandRegistry
from .command_factory import command_factory
from src.permissions import universal_permission_check


class CommandRegistry(ICommandRegistry):
    """Реестр команд бота"""
    
    def __init__(self, bot: discord.Client):
        self._bot = bot
        self._commands: Dict[str, ICommand] = {}
        self._slash_commands_config = self._get_slash_commands_config()
    
    def _get_slash_commands_config(self) -> Dict[str, dict]:
        """Конфигурация slash команд"""
        return {
            "addform": {
                "description": "📝 Создать форму для подачи заявок пользователями",
                "parameters": {
                    "channel": {
                        "type": discord.TextChannel,
                        "description": "Канал, где будет размещена форма для подачи заявок"
                    }
                }
            },
            "approvchannel": {
                "description": "⚙️ Установить или удалить канал для обработки заявок",
                "parameters": {
                    "channel": {
                        "type": discord.TextChannel,
                        "description": "Канал для заявок (оставьте пустым для удаления текущего канала)",
                        "required": False,
                        "default": None
                    }
                }
            },
            "giveapprov": {
                "description": "👥 Назначить роли для обработки заявок и выдачи при одобрении",
                "parameters": {
                    "approver": {
                        "type": discord.Role,
                        "description": "Роль, участники которой смогут одобрять/отклонять заявки"
                    },
                    "approved": {
                        "type": discord.Role,
                        "description": "Роль, которая будет выдана пользователю при одобрении заявки"
                    }
                }
            },
            "help": {
                "description": "❓ Показать список всех доступных команд бота",
                "parameters": {}
            },
            "sync": {
                "description": "🔄 Принудительно синхронизировать команды бота с Discord",
                "parameters": {}
            },
            "createcapt": {
                "description": "📋 Создать группу с ограниченным количеством участников и таймером",
                "parameters": {
                    "max_members": {
                        "type": int,
                        "description": "Максимальное количество участников в группе (от 2 до 50)"
                    },
                    "timer_minutes": {
                        "type": int,
                        "description": "Автозавершение через указанное время в минутах (1-1440, необязательно)",
                        "required": False,
                        "default": None
                    }
                }
            },
            "blacklistchannel": {
                "description": "📢 Установить канал для отчетов о блокировках",
                "parameters": {
                    "channel": {
                        "type": discord.TextChannel,
                        "description": "Канал для публикации отчетов о блокировках"
                    }
                }
            },
            "blacklist": {
                "description": "⛔ Добавить пользователя в черный список семей",
                "parameters": {
                    "user_id": {
                        "type": str,
                        "description": "ID пользователя (например: 1395845799174344776)"
                    },
                    "static_id_majestic": {
                        "type": str,
                        "description": "Игровой ID пользователя"
                    },
                    "reason": {
                        "type": str,
                        "description": "Причина добавления в черный список"
                    }
                }
            },
            "unblacklist": {
                "description": "⛔ Удалить пользователя из черного списка",
                "parameters": {
                    "user_id": {
                        "type": str,
                        "description": "ID пользователя для удаления из черного списка"
                    }
                }
            },
            "manageroles": {
                "description": "🔧 Управление ролями и функциями бота",
                "parameters": {}
            }
        }
    
    def register_command(self, command: ICommand) -> None:
        """Зарегистрировать команду"""
        self._commands[command.name] = command
    
    def get_command(self, name: str) -> Optional[ICommand]:
        """Получить команду по имени"""
        return self._commands.get(name)
    
    def get_all_commands(self) -> Dict[str, ICommand]:
        """Получить все команды"""
        return self._commands.copy()
    
    async def setup_slash_commands(self) -> None:
        """Настроить slash команды Discord"""
        
        # Создаем команды через фабрику
        command_types = command_factory.get_available_command_types()
        
        for command_type in command_types:
            try:
                command = command_factory.create_command(command_type, self._bot)
                self.register_command(command)
            except Exception as e:
                print(f"❌ Ошибка создания команды {command_type}: {e}")
        
        # Регистрируем slash команды
        await self._register_slash_commands()
        
    
    async def _register_slash_commands(self) -> None:
        """Регистрация slash команд в Discord"""
        for command_name, command in self._commands.items():
            if command_name in self._slash_commands_config:
                config = self._slash_commands_config[command_name]
                await self._create_slash_command(command, config)
    
    async def _create_slash_command(self, command: ICommand, config: dict) -> None:
        """Создать slash команду"""
        command_name = command.name
        description = config["description"]
        parameters = config.get("parameters", {})
        
        # Используем специфические обертки для каждого типа команд
        wrapper_func = self._create_command_wrapper(command, parameters)
        
        # Создаем slash команду
        slash_command = app_commands.Command(
            name=command_name,
            description=description,
            callback=wrapper_func
        )
        
        # Добавляем описания параметров
        if parameters:
            descriptions = {name: config["description"] for name, config in parameters.items()}
            slash_command = app_commands.describe(**descriptions)(slash_command)
        
        # Добавляем проверку разрешений
        slash_command = universal_permission_check()(slash_command)
        
        # Регистрируем команду в дереве
        self._bot.tree.add_command(slash_command)
            
    def _create_command_wrapper(self, command: ICommand, parameters: dict):
        """Создает обертку для команды с правильными аннотациями типов"""
        
        # Команды без параметров
        if not parameters:
            async def wrapper(interaction: discord.Interaction) -> None:
                await command.execute(interaction)
            return wrapper
        
        # Команды с одним каналом
        if len(parameters) == 1 and "channel" in parameters:
            param_config = parameters["channel"]
            if param_config.get("required", True):
                async def wrapper(interaction: discord.Interaction, channel: discord.TextChannel) -> None:
                    await command.execute(interaction, channel=channel)
            else:
                async def wrapper(interaction: discord.Interaction, channel: discord.TextChannel = None) -> None:
                    await command.execute(interaction, channel=channel)
            return wrapper
        
        # Команды с двумя ролями
        if len(parameters) == 2 and "approver" in parameters and "approved" in parameters:
            async def wrapper(interaction: discord.Interaction, approver: discord.Role, approved: discord.Role) -> None:
                await command.execute(interaction, approver=approver, approved=approved)
            return wrapper
        
        # Команда createcapt
        if "max_members" in parameters:
            if "timer_minutes" in parameters:
                async def wrapper(interaction: discord.Interaction, max_members: int, timer_minutes: int = None) -> None:
                    await command.execute(interaction, max_members=max_members, timer_minutes=timer_minutes)
            else:
                async def wrapper(interaction: discord.Interaction, max_members: int) -> None:
                    await command.execute(interaction, max_members=max_members)
            return wrapper
        
        # Команды blacklist
        if "static_id_majestic" in parameters:
            async def wrapper(interaction: discord.Interaction, user_id: str, static_id_majestic: str, reason: str) -> None:
                await command.execute(interaction, user_id=user_id, static_id_majestic=static_id_majestic, reason=reason)
            return wrapper
        
        # Команда unblacklist
        if "user_id" in parameters and len(parameters) == 1:
            async def wrapper(interaction: discord.Interaction, user_id: str) -> None:
                await command.execute(interaction, user_id=user_id)
            return wrapper
        
        # Fallback для неизвестных команд
        async def wrapper(interaction: discord.Interaction) -> None:
            await command.execute(interaction)
        return wrapper
    
    def unregister_command(self, name: str) -> bool:
        """Отменить регистрацию команды"""
        if name in self._commands:
            del self._commands[name]
            print(f"🗑️ Команда {name} удалена")
            return True
        return False
    
    def get_command_count(self) -> int:
        """Получить количество зарегистрированных команд"""
        return len(self._commands)
    
    def get_command_names(self) -> List[str]:
        """Получить список имен команд"""
        return list(self._commands.keys()) 