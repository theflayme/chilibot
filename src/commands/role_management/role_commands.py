import discord
from src.core.base_command import OwnerCommand
from .role_views import RolePermissionView
from .config import RoleManagementConfig


class ManageRolesCommand(OwnerCommand):
    
    def __init__(self, bot: discord.Client):
        super().__init__(
            bot=bot,
            name="manageroles",
            description="🔧 Управление ролями и функциями бота"
        )
        self._config = RoleManagementConfig()
    
    def _create_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🔧 Управление доступом к командам по ролям",
            description=self._get_description(),
            color=0x3498db
        )
        return embed
    
    def _get_description(self) -> str:
        commands_list = self._format_commands_list()
        return (
            "Выберите роль из списка ниже, чтобы настроить доступ к командам бота для этой роли.\n\n"
            "**Доступные команды для настройки:**\n"
            f"{commands_list}\n\n"
            "⚠️ Только владельцы бота могут использовать эту команду"
        )
    
    def _format_commands_list(self) -> str:
        commands = []
        for command_key, command_name in self._config.get_all_commands().items():
            emoji = self._config.get_command_emoji(command_key)
            commands.append(f"{emoji} `/{command_key}` - {command_name}")
        return "\n".join(commands)
    
    def _create_view(self, guild: discord.Guild) -> RolePermissionView:
        return RolePermissionView(guild)
    
    async def execute(self, interaction: discord.Interaction, **kwargs) -> None:
        if not await self.validate(interaction):
            return
        
        embed = self._create_embed()
        view = self._create_view(interaction.guild)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)