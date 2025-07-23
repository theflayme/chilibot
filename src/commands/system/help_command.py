import discord
from src.core.base_command import BaseCommand
from src.database_firebase import is_owner
from src.permissions import check_command_permission


class HelpCommand(BaseCommand):
    """Команда справки по боту"""
    
    def __init__(self, bot: discord.Client):
        super().__init__(
            bot=bot,
            name="help",
            description="❓ Показать список всех доступных команд бота"
        )
    
    async def execute(self, interaction: discord.Interaction, **kwargs) -> None:
        """Выполнить команду справки"""
        embed = await self._create_help_embed(interaction)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def _create_help_embed(self, interaction: discord.Interaction) -> discord.Embed:
        """Создать embed справки"""
        embed = discord.Embed(
            title="📋 Справочник команд бота",
            color=0x2f3136
        )
        
        # Проверяем права пользователя
        is_owner_user = is_owner(interaction.user.id)
        
        # Основные команды управления
        await self._add_management_commands(embed, is_owner_user)
        
        # Система заявок
        await self._add_application_commands(embed, interaction)
        
        # Организация групп
        await self._add_group_commands(embed, interaction)
        
        # Модерация и безопасность
        await self._add_moderation_commands(embed, interaction)
        
        # Команды для владельцев
        if is_owner_user:
            self._add_owner_commands(embed)
        
        # Справочная информация
        self._add_help_info(embed, is_owner_user)
        
        return embed
    
    async def _add_management_commands(self, embed: discord.Embed, is_owner_user: bool):
        """Добавить команды управления"""
        management_commands = []
        
        # /manageroles доступна только владельцам
        if is_owner_user:
            management_commands.extend([
                "┃ **`/manageroles`** 🎛️                                         ┃",
                "┃ └ Комплексное управление ролями и разрешениями  ┃",
                "┃ └ *Настройка доступа к функциям бота*           ┃",
                "┣"
            ])
        
        # /help доступна всем
        management_commands.extend([
            "┃ **`/help`** ❓                                            ┃",
            "┃ └ Отображение данной справки                     ┃",
            "┃ └ *Доступно всем участникам сервера*             ┃"
        ])
        
        if management_commands:
            management_value = "┏\n" + "\n".join(management_commands) + "\n┗"
            embed.add_field(
                name="🔧 **ОСНОВНОЕ УПРАВЛЕНИЕ**",
                value=management_value,
                inline=False
            )
    
    async def _add_application_commands(self, embed: discord.Embed, interaction: discord.Interaction):
        """Добавить команды системы заявок"""
        application_commands = []
        
        if await check_command_permission(interaction, 'addform'):
            application_commands.extend([
                "┃ **`/addform`** 📋                                          ┃",
                "┃ └ Создание интерактивной формы подачи заявок     ┃",
                "┃ └ *Генерация модального окна с полями ввода*     ┃"
            ])
        
        if await check_command_permission(interaction, 'approvchannel'):
            if application_commands:
                application_commands.append("┣")
            application_commands.extend([
                "┃ **`/approvchannel`** ⚙️                                   ┃",
                "┃ └ Назначение канала для обработки заявок         ┃",
                "┃ └ *Настройка места рассмотрения поданных форм*   ┃"
            ])
        
        if await check_command_permission(interaction, 'giveapprov'):
            if application_commands:
                application_commands.append("┣")
            application_commands.extend([
                "┃ **`/giveapprov`** 👥                                      ┃",
                "┃ └ Конфигурация ролей системы одобрений           ┃",
                "┃ └ *Назначение модераторов и одобренных ролей*    ┃"
            ])
        
        if application_commands:
            application_value = "┏\n" + "\n".join(application_commands) + "\n┗"
            embed.add_field(
                name="📝 **СИСТЕМА ЗАЯВОК И ОДОБРЕНИЙ**",
                value=application_value,
                inline=False
            )
    
    async def _add_group_commands(self, embed: discord.Embed, interaction: discord.Interaction):
        """Добавить команды группировки"""
        if await check_command_permission(interaction, 'createcapt'):
            embed.add_field(
                name="📋 **ОРГАНИЗАЦИЯ И ГРУППИРОВКА**",
                value=(
                    "┏\n"
                    "┃ **`/createcapt`** 👑                                      ┃\n"
                    "┃ └ Формирование команд с лимитом участников       ┃\n"
                    "┃ └ *Создание групп от 2 до 50 человек*            ┃\n"
                    "┃ └ *Автоматическое управление составом*           ┃\n"
                    "┃ └ *Таймер автозавершения (1-1440 минут)*       ┃\n"
                    "┗"
                ),
                inline=False
            )
    
    async def _add_moderation_commands(self, embed: discord.Embed, interaction: discord.Interaction):
        """Добавить команды модерации"""
        moderation_commands = []
        
        if await check_command_permission(interaction, 'blacklistchannel'):
            moderation_commands.extend([
                "┃ **`/blacklistchannel`** 📢                       ",
                "┃ └ Назначение канала для отчетов о блокировках    ",
                "┃ └ *Настройка уведомлений о черном списке*        "
            ])
        
        if await check_command_permission(interaction, 'blacklist'):
            if moderation_commands:
                moderation_commands.append("┣")
            moderation_commands.extend([
                "┃ **`/blacklist`** ⛔                              ",
                "┃ └ Добавление пользователя в черный список        ",
                "┃ └ *Блокировка по Discord ID и игровому ID*       "
            ])
        
        if await check_command_permission(interaction, 'unblacklist'):
            if moderation_commands:
                moderation_commands.append("┣")
            moderation_commands.extend([
                "┃ **`/unblacklist`** ✅                            ",
                "┃ └ Удаление пользователя из черного списка        ",
                "┃ └ *Разблокировка по идентификатору*              "
            ])
        
        if moderation_commands:
            moderation_value = "┏\n" + "\n".join(moderation_commands) + "\n┗"
            embed.add_field(
                name="⚔️ **МОДЕРАЦИЯ И БЕЗОПАСНОСТЬ**",
                value=moderation_value,
                inline=False
            )
    
    def _add_owner_commands(self, embed: discord.Embed):
        """Добавить команды для владельцев"""
        embed.add_field(
            name="👑 **АДМИНИСТРИРОВАНИЕ БОТА**",
            value=(
                "┏\n"
                "┃ **`/sync`** 🔄                                  \n"
                "┃ └ Принудительная синхронизация команд            \n"
                "┃ └ *Обновление команд в интерфейсе Discord*       \n"
                "┃ └ ⚠️ **Только для владельцев бота**              \n"
                "┗"
            ),
            inline=False
        )
    
    def _add_help_info(self, embed: discord.Embed, is_owner_user: bool):
        """Добавить справочную информацию"""
        info_text = [
            "┏",
            "┃ ⌨️  Используйте `/` в чате для вызова команд     ",
            "┃ 🆘 При проблемах обращайтесь к администрации     "
        ]
        
        if is_owner_user:
            info_text.insert(2, "┃ ⚙️  Настройте доступ через `/manageroles`        ")
        else:
            info_text.insert(2, "┃ 🔐 Доступ к командам настраивает администрация   ")
        
        info_text.append("┗")
        
        embed.add_field(
            name="💡 **СПРАВОЧНАЯ ИНФОРМАЦИЯ**",
            value="\n".join(info_text),
            inline=False
        ) 