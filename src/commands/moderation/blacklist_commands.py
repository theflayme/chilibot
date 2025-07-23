import discord
from typing import Tuple, Optional
from src.core.base_command import PermissionCommand
from src.database_firebase import (
    save_settings, 
    add_to_blacklist, 
    get_blacklist_report_channel,
    is_blacklisted,
    remove_from_blacklist
)


class BlacklistChannelCommand(PermissionCommand):
    
    def __init__(self, bot: discord.Client):
        super().__init__(
            bot=bot,
            name="blacklistchannel",
            description="📢 Установить канал для отчетов о блокировках",
            required_permission="blacklistchannel"
        )
    
    async def execute(self, interaction: discord.Interaction, channel: discord.TextChannel, **kwargs) -> None:
        if not await self.validate(interaction):
            return
        
        save_settings(interaction.guild_id, blacklist_report_channel_id=channel.id)
        await interaction.response.send_message(
            f"✅ Канал для отчетов о блокировках установлен: {channel.mention}", 
            ephemeral=True
        )


class BlacklistCommand(PermissionCommand):
    
    def __init__(self, bot: discord.Client):
        super().__init__(
            bot=bot,
            name="blacklist",
            description="⛔ Добавить пользователя в черный список семей",
            required_permission="blacklist"
        )
    
    async def execute(self, interaction: discord.Interaction, user_id: str, static_id_majestic: str, reason: str, **kwargs) -> None:
        if not await self.validate(interaction):
            return

        report_channel = await self._get_report_channel(interaction)
        if not report_channel:
            return

        user, member = await self._find_user_and_member(interaction, user_id)
        if not user or not member:
            return

        add_to_blacklist(interaction.guild_id, user.id, reason, interaction.user.id, static_id_majestic)
        
        embed = self._create_blacklist_embed(user, static_id_majestic, reason, interaction.user)
        await report_channel.send(embed=embed)
        
        await self._ban_user(interaction, member, user, reason)
    
    async def _get_report_channel(self, interaction: discord.Interaction) -> Optional[discord.TextChannel]:
        report_channel_id = get_blacklist_report_channel(interaction.guild_id)
        if not report_channel_id:
            await self.handle_error(
                interaction, 
                "❌ Сначала установите канал для отчетов с помощью команды /blacklistchannel"
            )
            return None

        report_channel = interaction.guild.get_channel(int(report_channel_id))
        if not report_channel:
            await self.handle_error(
                interaction, 
                "❌ Канал для отчетов не найден. Пожалуйста, переустановите его с помощью команды /blacklistchannel"
            )
            return None
        
        return report_channel
    
    async def _find_user_and_member(self, interaction: discord.Interaction, user_id: str) -> Tuple[Optional[discord.User], Optional[discord.Member]]:
        try:
            user = await self._bot.fetch_user(int(user_id))
            if not user:
                await self.handle_error(interaction, f"❌ Пользователь с ID {user_id} не найден.")
                return None, None
            
            member = await interaction.guild.fetch_member(user.id)
            if not member:
                await self.handle_error(interaction, f"❌ Пользователь с ID {user_id} не найден на сервере.")
                return None, None
                
            return user, member
            
        except (ValueError, discord.NotFound):
            await self.handle_error(interaction, f"❌ Пользователь с ID {user_id} не найден.")
            return None, None
        except discord.HTTPException:
            await self.handle_error(interaction, "❌ Ошибка при поиске пользователя.")
            return None, None
    
    def _create_blacklist_embed(self, user: discord.User, static_id_majestic: str, reason: str, moderator: discord.User) -> discord.Embed:
        embed = discord.Embed(
            title="⛔ Черный список семьи",
            description="Пользователь добавлен в черный список семей",
            color=0xFF0000
        )
        
        embed.add_field(
            name="👤 Пользователь",
            value=f"{user.mention} ({user.name}#{user.discriminator})\nID: {user.id}",
            inline=False
        )

        embed.add_field(
            name="🎮 Игровой StaticID",
            value=f"#{static_id_majestic}",
            inline=False
        )
        
        embed.add_field(
            name="📝 Причина",
            value=reason,
            inline=False
        )
        
        embed.add_field(
            name="👮 Модератор",
            value=f"{moderator.mention} ({moderator.name}#{moderator.discriminator})",
            inline=False
        )
        
        return embed
    
    async def _ban_user(self, interaction: discord.Interaction, member: discord.Member, user: discord.User, reason: str):
        try:
            bot_member = interaction.guild.get_member(self._bot.user.id)
            if not bot_member.guild_permissions.ban_members:
                await interaction.response.send_message(
                    "⚠️ Пользователь добавлен в черный список, но у бота нет прав на бан участников.", 
                    ephemeral=True
                )
                return
            
            if member.top_role >= bot_member.top_role:
                await interaction.response.send_message(
                    "⚠️ Пользователь добавлен в черный список, но у бота недостаточно прав для бана этого пользователя (иерархия ролей).", 
                    ephemeral=True
                )
                return
            
            await interaction.guild.ban(user, reason=f"Добавлен в черный список: {reason}")
            await interaction.response.send_message(
                f"✅ Пользователь {user.mention} добавлен в черный список и забанен.", 
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "⚠️ Пользователь добавлен в черный список, но у меня недостаточно прав для бана.", 
                ephemeral=True
            )
        except discord.HTTPException:
            await interaction.response.send_message(
                "⚠️ Пользователь добавлен в черный список, но произошла ошибка при бане.", 
                ephemeral=True
            )


class UnblacklistCommand(PermissionCommand):
    
    def __init__(self, bot: discord.Client):
        super().__init__(
            bot=bot,
            name="unblacklist",
            description="⛔ Удалить пользователя из черного списка",
            required_permission="unblacklist"
        )
    
    async def execute(self, interaction: discord.Interaction, user_id: str, **kwargs) -> None:
        if not await self.validate(interaction):
            return
        
        try:
            user_id_int = int(user_id)
        except ValueError:
            await self.handle_error(interaction, "❌ Неверный формат ID пользователя. Используйте числовой ID.")
            return
        
        if not is_blacklisted(interaction.guild_id, user_id_int):
            await self.handle_error(interaction, f"❌ Пользователь с ID {user_id} не находится в черном списке.")
            return
        
        success = remove_from_blacklist(interaction.guild_id, user_id_int)
        if not success:
            await self.handle_error(interaction, "❌ Произошла ошибка при удалении пользователя из черного списка.")
            return
        
        user_display = await self._get_user_display(user_id_int)
        
        await self._send_removal_report(interaction, user_id, user_display)
        
        await interaction.response.send_message(
            f"✅ Пользователь {user_display} удален из черного списка.", 
            ephemeral=True
        )
    
    async def _get_user_display(self, user_id: int) -> str:
        try:
            user = await self._bot.fetch_user(user_id)
            return f"{user.mention} ({user.name}#{user.discriminator})"
        except (discord.NotFound, discord.HTTPException):
            return f"ID: {user_id}"
    
    async def _send_removal_report(self, interaction: discord.Interaction, user_id: str, user_display: str):
        try:
            report_channel_id = get_blacklist_report_channel(interaction.guild_id)
            if not report_channel_id:
                return
            
            report_channel = interaction.guild.get_channel(int(report_channel_id))
            if not report_channel:
                return
            
            embed = discord.Embed(
                title="✅ Удаление из черного списка",
                description="Пользователь удален из черного списка семей",
                color=0x00FF00
            )
            
            embed.add_field(
                name="👤 Пользователь",
                value=user_display,
                inline=False
            )
            
            embed.add_field(
                name="👮 Модератор",
                value=f"{interaction.user.mention} ({interaction.user.name}#{interaction.user.discriminator})",
                inline=False
            )
            
            embed.set_footer(text=f"ID пользователя: {user_id}")
            
            await report_channel.send(embed=embed)
            
        except Exception:
            pass