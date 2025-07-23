"""
Views для интерфейса управления ролями
"""

import discord
from typing import List
from src.database_firebase import get_role_permissions
from .config import AVAILABLE_COMMANDS, COMMAND_EMOJIS, INTERFACE_CONFIG
from .role_buttons import CommandToggleButton, SavePermissionsButton, ResetPermissionsButton


class RolePermissionView(discord.ui.View):
    """View для выбора роли"""
    
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=INTERFACE_CONFIG['TIMEOUT'])
        self.guild = guild
        self.add_item(RoleSelect(guild))
    
    async def on_timeout(self):
        """Обработка таймаута"""
        for item in self.children:
            item.disabled = True


class RoleSelect(discord.ui.Select):
    """Селект для выбора роли"""
    
    def __init__(self, guild: discord.Guild):
        self.guild = guild
        
        # Создаем опции для ролей (исключаем @everyone и боты)
        options = []
        roles = sorted(
            [role for role in guild.roles if role.name != "@everyone" and not role.managed], 
            key=lambda r: r.position, 
            reverse=True
        )
        
        # Ограничиваем до максимального количества ролей (лимит Discord)
        for role in roles[:INTERFACE_CONFIG['MAX_ROLES_PER_SELECT']]:
            options.append(discord.SelectOption(
                label=role.name[:100],  # Ограничение Discord на длину label
                value=str(role.id),
                description=f"Участников: {len(role.members)}",
                emoji="🎭"
            ))
        
        if not options:
            options.append(discord.SelectOption(
                label="Нет доступных ролей",
                value="none",
                description="На сервере нет ролей для настройки"
            ))
        
        super().__init__(
            placeholder="Выберите роль для настройки разрешений...",
            options=options,
            min_values=1,
            max_values=1
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Обработка выбора роли"""
        if self.values[0] == "none":
            await interaction.response.send_message("❌ Нет доступных ролей для настройки.", ephemeral=True)
            return
        
        role_id = int(self.values[0])
        role = self.guild.get_role(role_id)
        
        if not role:
            await interaction.response.send_message("❌ Роль не найдена.", ephemeral=True)
            return
        
        # Создаем интерфейс настройки разрешений для выбранной роли
        view = CommandPermissionView(self.guild, role)
        embed = view.create_permissions_embed()
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class CommandPermissionView(discord.ui.View):
    """View для настройки разрешений команд"""
    
    def __init__(self, guild: discord.Guild, role: discord.Role):
        super().__init__(timeout=INTERFACE_CONFIG['TIMEOUT'])
        self.guild = guild
        self.role = role
        
        # Получаем текущие разрешения
        self.current_permissions = get_role_permissions(guild.id, role.id)
        
        # Добавляем кнопки для каждой команды
        self._add_command_buttons()
        
        # Добавляем кнопки управления
        self._add_management_buttons()
    
    def _add_command_buttons(self):
        """Добавить кнопки для команд"""
        commands = list(AVAILABLE_COMMANDS.items())
        
        for i, (command, description) in enumerate(commands):
            button = CommandToggleButton(
                command=command, 
                description=description, 
                enabled=command in self.current_permissions
            )
            button.row = i // INTERFACE_CONFIG['BUTTONS_PER_ROW']  # Распределяем по рядам
            self.add_item(button)
    
    def _add_management_buttons(self):
        """Добавить кнопки управления"""
        save_button = SavePermissionsButton()
        save_button.row = INTERFACE_CONFIG['MANAGEMENT_ROW']
        self.add_item(save_button)
        
        reset_button = ResetPermissionsButton()
        reset_button.row = INTERFACE_CONFIG['MANAGEMENT_ROW']
        self.add_item(reset_button)
    
    def create_permissions_embed(self) -> discord.Embed:
        """Создать embed с информацией о разрешениях"""
        embed = discord.Embed(
            title=f"🔧 Настройка разрешений для роли {self.role.name}",
            description=(
                f"Роль: {self.role.mention}\n"
                f"Участников с ролью: {len(self.role.members)}\n\n"
                "**Текущие разрешения:**\n"
            ),
            color=self.role.color if self.role.color != discord.Color.default() else 0x3498db
        )
        
        # Добавляем информацию о текущих разрешениях
        if self.current_permissions:
            permissions_text = ""
            for perm in self.current_permissions:
                if perm in AVAILABLE_COMMANDS:
                    emoji = COMMAND_EMOJIS.get(perm, '📋')
                    permissions_text += f"✅ {emoji} {AVAILABLE_COMMANDS[perm]}\n"
            embed.description += permissions_text if permissions_text else "❌ Нет разрешений"
        else:
            embed.description += "❌ Нет разрешений"
        
        # Добавляем инструкции
        embed.add_field(
            name="💡 Как использовать",
            value=(
                "• Нажимайте на кнопки команд для включения/выключения доступа\n"
                "• 🟢 = разрешено, 🔴 = запрещено\n"
                "• Нажмите **Сохранить**, чтобы применить изменения\n"
                "• **Сброс** удалит все разрешения для роли"
            ),
            inline=False
        )
        
        embed.set_footer(text=f"ID роли: {self.role.id}")
        return embed
    
    async def on_timeout(self):
        """Обработка таймаута"""
        for item in self.children:
            item.disabled = True 