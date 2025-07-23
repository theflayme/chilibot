import discord
from src.database_firebase import save_role_permissions, remove_role_permissions
from .config import RoleManagementConfig


class CommandToggleButton(discord.ui.Button):
    
    def __init__(self, command: str, description: str, enabled: bool):
        self.command = command
        self.enabled = enabled
        
        style = discord.ButtonStyle.success if enabled else discord.ButtonStyle.primary
        emoji = "🟢" if enabled else "🔴"
        
        super().__init__(
            label=description,
            style=style,
            emoji=emoji,
            custom_id=f"toggle_{command}"
        )
    
    def toggle_state(self):
        self.enabled = not self.enabled
        self.style = discord.ButtonStyle.success if self.enabled else discord.ButtonStyle.primary
        self.emoji = "✅" if self.enabled else "🔴"
    
    def update_view_permissions(self):
        view = self.view
        if self.enabled and self.command not in view.current_permissions:
            view.current_permissions.append(self.command)
        elif not self.enabled and self.command in view.current_permissions:
            view.current_permissions.remove(self.command)
    
    async def callback(self, interaction: discord.Interaction):
        self.toggle_state()
        self.update_view_permissions()
        
        embed = self.view.create_permissions_embed()
        await interaction.response.edit_message(embed=embed, view=self.view)


class SavePermissionsButton(discord.ui.Button):
    
    def __init__(self):
        super().__init__(
            label="Сохранить",
            style=discord.ButtonStyle.primary,
            emoji="💾"
        )
    
    async def send_success_message(self, interaction: discord.Interaction):
        permissions_text = ', '.join(self.view.current_permissions) if self.view.current_permissions else 'Нет разрешений'
        await interaction.response.send_message(
            f"✅ Разрешения для роли {self.view.role.mention} успешно сохранены!\n"
            f"Сохранено: {permissions_text}",
            ephemeral=True
        )
    
    async def send_error_message(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "❌ Ошибка при сохранении разрешений. Проверьте консоль для подробностей.",
            ephemeral=True
        )
    
    async def callback(self, interaction: discord.Interaction):
        view = self.view
        success = save_role_permissions(view.guild.id, view.role.id, view.current_permissions)
        
        if success:
            await self.send_success_message(interaction)
        else:
            await self.send_error_message(interaction)


class ResetPermissionsButton(discord.ui.Button):
    
    def __init__(self):
        super().__init__(
            label="Сброс",
            style=discord.ButtonStyle.secondary,
            emoji="🗑️"
        )
    
    def reset_command_buttons(self):
        for item in self.view.children:
            if isinstance(item, CommandToggleButton):
                item.enabled = False
                item.style = discord.ButtonStyle.primary
                item.emoji = "🔴"
    
    async def send_error_message(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "❌ Ошибка при сбросе разрешений.",
            ephemeral=True
        )
    
    async def callback(self, interaction: discord.Interaction):
        view = self.view
        success = remove_role_permissions(view.guild.id, view.role.id)
        
        if success:
            view.current_permissions.clear()
            self.reset_command_buttons()
            
            embed = view.create_permissions_embed()
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await self.send_error_message(interaction)