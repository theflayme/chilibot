"""
Команда синхронизации
"""

import discord
from src.core.base_command import OwnerCommand


class SyncCommand(OwnerCommand):
    """Команда синхронизации slash команд с Discord"""
    
    def __init__(self, bot: discord.Client):
        super().__init__(
            bot=bot,
            name="sync",
            description="🔄 Принудительно синхронизировать команды бота с Discord"
        )
    
    async def execute(self, interaction: discord.Interaction, **kwargs) -> None:
        """Выполнить команду синхронизации"""
        if not await self.validate(interaction):
            return
            
        await interaction.response.defer(ephemeral=True)
        
        synced = await self._bot.tree.sync()
        embed = self._create_sync_embed(synced)
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    def _create_sync_embed(self, synced: list) -> discord.Embed:
        """Создать embed результата синхронизации"""
        embed = discord.Embed(
            title="✅ Синхронизация завершена",
            description=f"Успешно синхронизировано **{len(synced)}** команд:",
            color=0x00ff00
        )
        
        command_list = "\n".join([f"🔹 /{cmd.name}" for cmd in synced])
        embed.add_field(
            name="Синхронизированные команды:",
            value=command_list if command_list else "Нет команд",
            inline=False
        )
        
        embed.set_footer(text="Команды обновлены в интерфейсе Discord")
        return embed 