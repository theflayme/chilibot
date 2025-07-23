import discord
from src.core.base_command import PermissionCommand
from src.database_firebase import save_settings
from src.views import FormMessageModal


class AddFormCommand(PermissionCommand):
    
    def __init__(self, bot: discord.Client):
        super().__init__(
            bot=bot,
            name="addform",
            description="📝 Создать форму для подачи заявок пользователями",
            required_permission="addform"
        )
    
    async def execute(self, interaction: discord.Interaction, channel: discord.TextChannel, **kwargs) -> None:
        if not await self.validate(interaction):
            return
        
        save_settings(interaction.guild_id, form_channel_id=channel.id)
        await interaction.response.send_modal(FormMessageModal(channel_id=channel.id))


class ApprovalChannelCommand(PermissionCommand):
    
    def __init__(self, bot: discord.Client):
        super().__init__(
            bot=bot,
            name="approvchannel",
            description="⚙️ Установить или удалить канал для обработки заявок",
            required_permission="approvchannel"
        )
    
    async def execute(self, interaction: discord.Interaction, channel: discord.TextChannel = None, **kwargs) -> None:
        if not await self.validate(interaction):
            return
        
        save_settings(interaction.guild_id, approv_channel_id=channel.id if channel else None)
        
        if channel:
            await interaction.response.send_message(f"✅ Канал для заявок установлен: {channel.mention}", ephemeral=True)
        else:
            await interaction.response.send_message("✅ Канал для заявок удален.", ephemeral=True)


class GiveApprovalCommand(PermissionCommand):
    
    def __init__(self, bot: discord.Client):
        super().__init__(
            bot=bot,
            name="giveapprov",
            description="👥 Назначить роли для обработки заявок и выдачи при одобрении",
            required_permission="giveapprov"
        )
    
    async def execute(self, interaction: discord.Interaction, approver: discord.Role, approved: discord.Role, **kwargs) -> None:
        if not await self.validate(interaction):
            return
        
        save_settings(
            interaction.guild_id,
            approver_role_id=approver.id,
            approved_role_id=approved.id
        )
        
        embed = self._create_roles_embed(approver, approved)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    def _create_roles_embed(self, approver: discord.Role, approved: discord.Role) -> discord.Embed:
        embed = discord.Embed(
            title="✅ Роли настроены",
            description="Система ролей для заявок успешно настроена:",
            color=0x00ff00
        )
        embed.add_field(
            name="🛡️ Роль модераторов", 
            value=f"{approver.mention}\n*Может одобрять/отклонять заявки*", 
            inline=False
        )
        embed.add_field(
            name="🎯 Роль при одобрении", 
            value=f"{approved.mention}\n*Выдается при одобрении заявки*", 
            inline=False
        )
        return embed