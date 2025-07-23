import discord
from src.core.base_command import BaseCommand
from src.database_firebase import is_owner
from src.permissions import check_command_permission


class HelpCommand(BaseCommand):
    
    def __init__(self, bot: discord.Client):
        super().__init__(
            bot=bot,
            name="help",
            description="🔍 Получить подробную справку по всем функциям и возможностям бота"
        )
    
    async def execute(self, interaction: discord.Interaction, **kwargs) -> None:
        view = HelpView(interaction)
        embed = await view.get_main_page()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class HelpView(discord.ui.View):
    def __init__(self, interaction: discord.Interaction):
        super().__init__(timeout=300)
        self.interaction = interaction
        self.current_page = "main"
        self.is_owner_user = is_owner(interaction.user.id)
    
    async def get_main_page(self) -> discord.Embed:
        embed = discord.Embed(
            title="🌟 Центр помощи и документации",
            description="Исследуйте все возможности бота через удобную навигацию по категориям:",
            color=0x2f3136
        )
        
        categories = []
        
        # Базовый функционал доступен всем
        categories.append("⚡ **Базовый функционал**")
        categories.append("   └ Основные инструменты управления")
        
        # Заявочная система
        if await self._has_application_commands():
            categories.append("")
            categories.append("📋 **Заявочная система**")
            categories.append("   └ Автоматизация процесса подачи и обработки заявок")
        
        # Командообразование
        if await self._has_group_commands():
            categories.append("")
            categories.append("👥 **Командообразование**")
            categories.append("   └ Инструменты для создания и управления группами")
        
        # Система безопасности
        if await self._has_moderation_commands():
            categories.append("")
            categories.append("🛡️ **Система безопасности**")
            categories.append("   └ Контроль доступа и модерация")
        
        # Панель администратора
        if self.is_owner_user:
            categories.append("")
            categories.append("⚙️ **Панель администратора**")
            categories.append("   └ Расширенные настройки для владельцев")
        
        embed.add_field(
            name="📂 Доступные разделы:",
            value="\n".join(categories),
            inline=False
        )
        
        embed.add_field(
            name="💡 Руководство по использованию:",
            value=(
                "• Выберите нужную категорию кнопками внизу\n"
                "• Команды вызываются через `/` в любом канале\n"
                "• За технической поддержкой обращайтесь к администрации"
            ),
            inline=False
        )
        
        return embed
    async def get_management_page(self) -> discord.Embed:
        embed = discord.Embed(
            title="⚡ Базовый функционал",
            color=0x2f3136
        )
        
        management_commands = []
        
        if self.is_owner_user:
            management_commands.extend([
                "**`/manageroles`** 🎯",
                "└ Гибкая настройка системы ролей и прав доступа",
                "└ *Полный контроль над разрешениями бота*",
                ""
            ])
        
        management_commands.extend([
            "**`/help`** 🔍",
            "└ Интерактивная справочная система",
            "└ *Всегда актуальная документация по командам*"
        ])
        
        management_value = "\n".join(management_commands)
        embed.add_field(
            name="Доступные команды:",
            value=management_value,
            inline=False
        )
        
        return embed
    
    async def get_application_page(self) -> discord.Embed:
        embed = discord.Embed(
            title="📝 Система заявок и одобрений",
            color=0x2f3136
        )
        
        application_commands = []
        
        if await check_command_permission(self.interaction, 'addform'):
            application_commands.extend([
                "**`/addform`** 📋",
                "└ Создание интерактивной формы подачи заявок",
                "└ *Генерация модального окна с полями ввода*"
            ])
        
        if await check_command_permission(self.interaction, 'approvchannel'):
            if application_commands:
                application_commands.append("")
            application_commands.extend([
                "**`/approvchannel`** ⚙️",
                "└ Назначение канала для обработки заявок",
                "└ *Настройка места рассмотрения поданных форм*"
            ])
        
        if await check_command_permission(self.interaction, 'giveapprov'):
            if application_commands:
                application_commands.append("")
            application_commands.extend([
                "**`/giveapprov`** 👥",
                "└ Конфигурация ролей системы одобрений",
                "└ *Назначение модераторов и одобренных ролей*"
            ])
        
        if application_commands:
            application_value = "\n".join(application_commands)
            embed.add_field(
                name="Доступные команды:",
                value=application_value,
                inline=False
            )
        else:
            embed.add_field(
                name="Доступные команды:",
                value="❌ У вас нет доступа к командам этой категории",
                inline=False
            )
        
        return embed
    
    async def get_group_page(self) -> discord.Embed:
        embed = discord.Embed(
            title="📋 Организация и группировка",
            color=0x2f3136
        )
        
        if await check_command_permission(self.interaction, 'createcapt'):
            embed.add_field(
                name="Доступные команды:",
                value=(
                    "**`/createcapt`** 👑\n"
                    "└ Формирование команд с лимитом участников\n"
                    "└ *Создание групп от 2 до 50 человек*\n"
                    "└ *Автоматическое управление составом*\n"
                    "└ *Таймер автозавершения (1-1440 минут)*"
                ),
                inline=False
            )
        else:
            embed.add_field(
                name="Доступные команды:",
                value="❌ У вас нет доступа к командам этой категории",
                inline=False
            )
        
        return embed
    
    async def get_moderation_page(self) -> discord.Embed:
        embed = discord.Embed(
            title="⚔️ Модерация и безопасность",
            color=0x2f3136
        )
        
        moderation_commands = []
        
        if await check_command_permission(self.interaction, 'blacklistchannel'):
            moderation_commands.extend([
                "**`/blacklistchannel`** 📢",
                "└ Назначение канала для отчетов о блокировках",
                "└ *Настройка уведомлений о черном списке*"
            ])
        
        if await check_command_permission(self.interaction, 'blacklist'):
            if moderation_commands:
                moderation_commands.append("")
            moderation_commands.extend([
                "**`/blacklist`** ⛔",
                "└ Добавление пользователя в черный список",
                "└ *Блокировка по Discord ID и игровому ID*"
            ])
        
        if await check_command_permission(self.interaction, 'unblacklist'):
            if moderation_commands:
                moderation_commands.append("")
            moderation_commands.extend([
                "**`/unblacklist`** ✅",
                "└ Удаление пользователя из черного списка",
                "└ *Разблокировка по идентификатору*"
            ])
        
        if moderation_commands:
            moderation_value = "\n".join(moderation_commands)
            embed.add_field(
                name="Доступные команды:",
                value=moderation_value,
                inline=False
            )
        else:
            embed.add_field(
                name="Доступные команды:",
                value="❌ У вас нет доступа к командам этой категории",
                inline=False
            )
        
        return embed
    
    async def get_owner_page(self) -> discord.Embed:
        embed = discord.Embed(
            title="👑 Администрирование бота",
            color=0x2f3136
        )
        
        embed.add_field(
            name="Доступные команды:",
            value=(
                "**`/sync`** 🔄\n"
                "└ Принудительная синхронизация команд\n"
                "└ *Обновление команд в интерфейсе Discord*\n"
                "└ ⚠️ **Только для владельцев бота**"
            ),
            inline=False
        )
        
        return embed
    
    async def _has_application_commands(self) -> bool:
        return (await check_command_permission(self.interaction, 'addform') or
                await check_command_permission(self.interaction, 'approvchannel') or
                await check_command_permission(self.interaction, 'giveapprov'))
    
    async def _has_group_commands(self) -> bool:
        return await check_command_permission(self.interaction, 'createcapt')
    
    async def _has_moderation_commands(self) -> bool:
        return (await check_command_permission(self.interaction, 'blacklistchannel') or
                await check_command_permission(self.interaction, 'blacklist') or
                await check_command_permission(self.interaction, 'unblacklist'))
    
    @discord.ui.button(label="🏠 Главная", style=discord.ButtonStyle.secondary, row=0)
    async def main_page_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = "main"
        embed = await self.get_main_page()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="🔧 Управление", style=discord.ButtonStyle.primary, row=0)
    async def management_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = "management"
        embed = await self.get_management_page()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="📝 Заявки", style=discord.ButtonStyle.primary, row=0)
    async def application_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._has_application_commands():
            await interaction.response.send_message("❌ У вас нет доступа к командам этой категории", ephemeral=True)
            return
        
        self.current_page = "application"
        embed = await self.get_application_page()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="📋 Группы", style=discord.ButtonStyle.primary, row=1)
    async def group_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._has_group_commands():
            await interaction.response.send_message("❌ У вас нет доступа к командам этой категории", ephemeral=True)
            return
        
        self.current_page = "group"
        embed = await self.get_group_page()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="⚔️ Модерация", style=discord.ButtonStyle.primary, row=1)
    async def moderation_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._has_moderation_commands():
            await interaction.response.send_message("❌ У вас нет доступа к командам этой категории", ephemeral=True)
            return
        
        self.current_page = "moderation"  
        embed = await self.get_moderation_page()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="👑 Админ", style=discord.ButtonStyle.danger, row=1)
    async def owner_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.is_owner_user:
            await interaction.response.send_message("❌ Эта категория доступна только владельцам бота", ephemeral=True)
            return
        
        self.current_page = "owner"
        embed = await self.get_owner_page()
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.interaction.user.id
    
    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        
        try:
            await self.interaction.edit_original_response(view=self)
        except:
            pass