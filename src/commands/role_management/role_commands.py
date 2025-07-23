"""
Команды для управления ролями и разрешениями
"""

import discord
from src.core.base_command import OwnerCommand
from .role_views import RolePermissionView


class ManageRolesCommand(OwnerCommand):
    """Команда управления ролями и разрешениями"""
    
    def __init__(self, bot: discord.Client):
        super().__init__(
            bot=bot,
            name="manageroles",
            description="🔧 Управление ролями и функциями бота"
        )
    
    async def execute(self, interaction: discord.Interaction, **kwargs) -> None:
        """Выполнить команду управления ролями"""
        if not await self.validate(interaction):
            return
        
        embed = discord.Embed(
            title="🔧 Управление доступом к командам по ролям",
            description=(
                "Выберите роль из списка ниже, чтобы настроить доступ к командам бота для этой роли.\n\n"
                "**Доступные команды для настройки:**\n"
                "📝 `/addform` - создание форм заявок\n"
                "⚙️ `/approvchannel` - настройка каналов\n"
                "👥 `/giveapprov` - настройка ролей\n"
                "📋 `/createcapt` - создание групп\n"
                "📢 `/blacklistchannel` - канал отчетов\n"
                "⛔ `/blacklist` - управление черным списком\n"
                "✅ `/unblacklist` - удаление из ЧС\n\n"
                "⚠️ Только владельцы бота могут использовать эту команду"
            ),
            color=0x3498db
        )
        
        view = RolePermissionView(interaction.guild)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True) 