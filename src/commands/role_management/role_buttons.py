"""
Кнопки для интерфейса управления ролями
"""

import discord
from src.database_firebase import save_role_permissions, remove_role_permissions
from .config import AVAILABLE_COMMANDS


class CommandToggleButton(discord.ui.Button):
    """Кнопка переключения разрешения команды"""
    
    def __init__(self, command: str, description: str, enabled: bool):
        self.command = command
        self.enabled = enabled
        
        # Определяем стиль и эмодзи
        style = discord.ButtonStyle.success if enabled else discord.ButtonStyle.primary
        emoji = "🟢" if enabled else "🔴"
        
        super().__init__(
            label=description,
            style=style,
            emoji=emoji,
            custom_id=f"toggle_{command}"
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Обработка переключения разрешения"""
        # Переключаем состояние
        old_enabled = self.enabled
        self.enabled = not self.enabled
        
        # Обновляем внешний вид кнопки
        self.style = discord.ButtonStyle.success if self.enabled else discord.ButtonStyle.primary
        self.emoji = "✅" if self.enabled else "🔴"
        
        # Обновляем разрешения в view
        view = self.view
        if self.enabled and self.command not in view.current_permissions:
            view.current_permissions.append(self.command)
        elif not self.enabled and self.command in view.current_permissions:
            view.current_permissions.remove(self.command)
        
        # Обновляем embed
        embed = view.create_permissions_embed()
        await interaction.response.edit_message(embed=embed, view=view)


class SavePermissionsButton(discord.ui.Button):
    """Кнопка сохранения разрешений"""
    
    def __init__(self):
        super().__init__(
            label="Сохранить",
            style=discord.ButtonStyle.primary,
            emoji="💾"
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Обработка сохранения разрешений"""
        view = self.view
        
        # Сохраняем разрешения в базу данных
        success = save_role_permissions(view.guild.id, view.role.id, view.current_permissions)
        
        if success:
            await interaction.response.send_message(
                f"✅ Разрешения для роли {view.role.mention} успешно сохранены!\n"
                f"Сохранено: {', '.join(view.current_permissions) if view.current_permissions else 'Нет разрешений'}",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ Ошибка при сохранении разрешений. Проверьте консоль для подробностей.",
                ephemeral=True
            )


class ResetPermissionsButton(discord.ui.Button):
    """Кнопка сброса разрешений"""
    
    def __init__(self):
        super().__init__(
            label="Сброс",
            style=discord.ButtonStyle.secondary,
            emoji="🗑️"
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Обработка сброса разрешений"""
        view = self.view
        
        # Очищаем все разрешения
        success = remove_role_permissions(view.guild.id, view.role.id)
        
        if success:
            # Обновляем локальные данные
            view.current_permissions.clear()
            
            # Обновляем все кнопки
            for item in view.children:
                if isinstance(item, CommandToggleButton):
                    item.enabled = False
                    item.style = discord.ButtonStyle.primary
                    item.emoji = "🔴"
            
            # Обновляем embed
            embed = view.create_permissions_embed()
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await interaction.response.send_message(
                "❌ Ошибка при сбросе разрешений.",
                ephemeral=True
            ) 