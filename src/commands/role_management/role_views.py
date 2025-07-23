import discord
from typing import List
from src.database_firebase import get_role_permissions
from .config import RoleManagementConfig
from .role_buttons import CommandToggleButton, SavePermissionsButton, ResetPermissionsButton


class RolePermissionView(discord.ui.View):
    
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=RoleManagementConfig.TIMEOUT)
        self.guild = guild
        self.add_item(RoleSelect(guild))
    
    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


class RoleSelect(discord.ui.Select):
    
    def __init__(self, guild: discord.Guild):
        self.guild = guild
        
        options = self._create_role_options()
        
        super().__init__(
            placeholder="Выберите роль для настройки разрешений...",
            options=options,
            min_values=1,
            max_values=1
        )
    
    def _create_role_options(self) -> List[discord.SelectOption]:
        options = []
        roles = self._get_filtered_roles()
        
        for role in roles[:RoleManagementConfig.MAX_ROLES_PER_SELECT]:
            options.append(self._create_role_option(role))
        
        if not options:
            options.append(self._create_no_roles_option())
        
        return options
    
    def _get_filtered_roles(self) -> List[discord.Role]:
        return sorted(
            [role for role in self.guild.roles if role.name != "@everyone" and not role.managed], 
            key=lambda r: r.position, 
            reverse=True
        )
    
    def _create_role_option(self, role: discord.Role) -> discord.SelectOption:
        return discord.SelectOption(
            label=role.name[:100],
            value=str(role.id),
            description=f"Участников: {len(role.members)}",
            emoji="🎭"
        )
    
    def _create_no_roles_option(self) -> discord.SelectOption:
        return discord.SelectOption(
            label="Нет доступных ролей",
            value="none",
            description="На сервере нет ролей для настройки"
        )
    
    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message("❌ Нет доступных ролей для настройки.", ephemeral=True)
            return
        
        role_id = int(self.values[0])
        role = self.guild.get_role(role_id)
        
        if not role:
            await interaction.response.send_message("❌ Роль не найдена.", ephemeral=True)
            return
        
        view = CommandPermissionView(self.guild, role)
        embed = view.create_permissions_embed()
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class CommandPermissionView(discord.ui.View):
    
    def __init__(self, guild: discord.Guild, role: discord.Role):
        super().__init__(timeout=RoleManagementConfig.TIMEOUT)
        self.guild = guild
        self.role = role
        self.current_permissions = get_role_permissions(guild.id, role.id)
        self._config = RoleManagementConfig()
        
        self._add_command_buttons()
        self._add_management_buttons()
    
    def _add_command_buttons(self):
        commands = list(self._config.get_all_commands().items())
        
        for i, (command, description) in enumerate(commands):
            button = CommandToggleButton(
                command=command, 
                description=description, 
                enabled=command in self.current_permissions
            )
            button.row = i // RoleManagementConfig.BUTTONS_PER_ROW
            self.add_item(button)
    
    def _add_management_buttons(self):
        save_button = SavePermissionsButton()
        save_button.row = RoleManagementConfig.MANAGEMENT_ROW
        self.add_item(save_button)
        
        reset_button = ResetPermissionsButton()
        reset_button.row = RoleManagementConfig.MANAGEMENT_ROW
        self.add_item(reset_button)
    
    def create_permissions_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"🔧 Настройка разрешений для роли {self.role.name}",
            description=self._create_embed_description(),
            color=self._get_embed_color()
        )
        
        embed.add_field(
            name="💡 Как использовать",
            value=self._get_usage_instructions(),
            inline=False
        )
        
        embed.set_footer(text=f"ID роли: {self.role.id}")
        return embed
    
    def _create_embed_description(self) -> str:
        base_description = (
            f"Роль: {self.role.mention}\n"
            f"Участников с ролью: {len(self.role.members)}\n\n"
            "**Текущие разрешения:**\n"
        )
        
        permissions_text = self._get_permissions_text()
        return base_description + permissions_text
    
    def _get_permissions_text(self) -> str:
        if not self.current_permissions:
            return "❌ Нет разрешений"
        
        permissions_text = ""
        available_commands = self._config.get_all_commands()
        
        for perm in self.current_permissions:
            if perm in available_commands:
                emoji = self._config.get_command_emoji(perm)
                permissions_text += f"✅ {emoji} {available_commands[perm]}\n"
        
        return permissions_text if permissions_text else "❌ Нет разрешений"
    
    def _get_embed_color(self) -> int:
        return self.role.color.value if self.role.color != discord.Color.default() else 0x3498db
    
    def _get_usage_instructions(self) -> str:
        return (
            "• Нажимайте на кнопки команд для включения/выключения доступа\n"
            "• 🟢 = разрешено, 🔴 = запрещено\n"
            "• Нажмите **Сохранить**, чтобы применить изменения\n"
            "• **Сброс** удалит все разрешения для роли"
        )
    
    async def on_timeout(self):
        for item in self.children:
            item.disabled = True