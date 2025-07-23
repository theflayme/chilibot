"""
Новая система команд с использованием модульной архитектуры
Этот файл заменит старый commands.py
"""

import discord
from src.core import CommandRegistry


async def setup_commands(bot: discord.Client) -> CommandRegistry:
    """
    Настройка системы команд с использованием новой архитектуры
    
    Args:
        bot: Экземпляр Discord бота
        
    Returns:
        CommandRegistry: Настроенный реестр команд
    """
    
    # Создаем реестр команд
    registry = CommandRegistry(bot)
    
    # Настраиваем slash команды
    await registry.setup_slash_commands()
    
    return registry


# Для обратной совместимости с main.py
async def setup_commands_legacy(bot: discord.Client):
    """
    Обертка для обратной совместимости
    """
    return await setup_commands(bot)


def get_available_commands():
    """
    Получить список доступных команд для настройки разрешений
    Используется в модуле управления ролями
    """
    from src.commands.role_management.config import AVAILABLE_COMMANDS
    return AVAILABLE_COMMANDS


# Экспортируем для обратной совместимости
__all__ = [
    'setup_commands',
    'setup_commands_legacy', 
    'get_available_commands'
] 