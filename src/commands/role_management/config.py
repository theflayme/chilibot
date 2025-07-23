from typing import Dict


class RoleManagementConfig:
    
    AVAILABLE_COMMANDS: Dict[str, str] = {
        'addform': 'Создание форм',
        'approvchannel': 'Настройка каналов',
        'giveapprov': 'Настройка ролей',
        'createcapt': 'Создание групп',
        'blacklistchannel': 'Канал отчетов',
        'blacklist': 'Черный список',
        'unblacklist': 'Удаление из ЧС'
    }
    
    COMMAND_EMOJIS: Dict[str, str] = {
        'addform': '📝',
        'approvchannel': '⚙️',
        'giveapprov': '👥',
        'createcapt': '📋',
        'blacklistchannel': '📢',
        'blacklist': '⛔',
        'unblacklist': '✅'
    }
    
    TIMEOUT: int = 300
    MAX_ROLES_PER_SELECT: int = 25
    BUTTONS_PER_ROW: int = 3
    MANAGEMENT_ROW: int = 3
    
    @classmethod
    def get_command_name(cls, command_key: str) -> str:
        return cls.AVAILABLE_COMMANDS.get(command_key, command_key)
    
    @classmethod
    def get_command_emoji(cls, command_key: str) -> str:
        return cls.COMMAND_EMOJIS.get(command_key, '❓')
    
    @classmethod
    def get_all_commands(cls) -> Dict[str, str]:
        return cls.AVAILABLE_COMMANDS.copy()
    
    @classmethod
    def get_all_emojis(cls) -> Dict[str, str]:
        return cls.COMMAND_EMOJIS.copy()