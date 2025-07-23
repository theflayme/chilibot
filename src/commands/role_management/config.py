"""
Конфигурация для модуля управления ролями
"""

from typing import Dict

# Список доступных команд для настройки разрешений
AVAILABLE_COMMANDS: Dict[str, str] = {
    'addform': 'Создание форм',
    'approvchannel': 'Настройка каналов',
    'giveapprov': 'Настройка ролей',
    'createcapt': 'Создание групп',
    'blacklistchannel': 'Канал отчетов',
    'blacklist': 'Черный список',
    'unblacklist': 'Удаление из ЧС'
}

# Эмодзи для команд
COMMAND_EMOJIS: Dict[str, str] = {
    'addform': '📝',
    'approvchannel': '⚙️', 
    'giveapprov': '👥',
    'createcapt': '📋',
    'blacklistchannel': '📢',
    'blacklist': '⛔',
    'unblacklist': '✅'
}

# Настройки интерфейса
INTERFACE_CONFIG = {
    'TIMEOUT': 300,  # Таймаут для View в секундах
    'MAX_ROLES_PER_SELECT': 25,  # Максимум ролей в селекте (лимит Discord)
    'BUTTONS_PER_ROW': 3,  # Количество кнопок в ряду
    'MANAGEMENT_ROW': 3  # Ряд для кнопок управления
} 