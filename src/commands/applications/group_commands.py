import discord
import asyncio
from src.core.base_command import PermissionCommand
from src.database_firebase import save_capt, get_capt, remove_capt
from src.views import CaptView


class CreateCaptCommand(PermissionCommand):
    
    def __init__(self, bot: discord.Client):
        super().__init__(
            bot=bot,
            name="createcapt",
            description="📋 Создать группу с ограниченным количеством участников и таймером",
            required_permission="createcapt"
        )
        self.MIN_MEMBERS = 2
        self.MAX_MEMBERS = 50
        self.MIN_TIMER = 1
        self.MAX_TIMER = 1440
    
    async def execute(self, interaction: discord.Interaction, max_members: int, timer_minutes: int = None, **kwargs) -> None:
        if not await self.validate(interaction):
            return
        
        if not self._validate_members_count(max_members):
            await self.handle_error(interaction, "❌ Количество участников должно быть от 2 до 50")
            return
        
        if timer_minutes is not None and not self._validate_timer(timer_minutes):
            await self.handle_error(interaction, "❌ Таймер должен быть от 1 до 1440 минут (24 часа)")
            return
        
        embed = self._create_capt_embed(max_members, timer_minutes)
        view = CaptView(max_members, timer_minutes)
        message = await interaction.channel.send(embed=embed, view=view)
        
        save_capt(interaction.guild_id, interaction.channel_id, message.id, max_members, [], timer_minutes)
        
        if timer_minutes:
            await self._schedule_auto_deletion(interaction, message, timer_minutes)
        
        success_msg = f"✅ Группа успешно создана!"
        if timer_minutes:
            success_msg += f" Автозавершение через {timer_minutes} мин."
        
        await interaction.response.send_message(success_msg, ephemeral=True, delete_after=0)
    
    def _validate_members_count(self, max_members: int) -> bool:
        return self.MIN_MEMBERS <= max_members <= self.MAX_MEMBERS
    
    def _validate_timer(self, timer_minutes: int) -> bool:
        return self.MIN_TIMER <= timer_minutes <= self.MAX_TIMER
    
    def _create_capt_embed(self, max_members: int, timer_minutes: int = None) -> discord.Embed:
        embed = discord.Embed(
            title="📋 Группа",
            color=0x3498db
        )
        
        description = f"Участники (0/{max_members}):\n\nНажмите кнопку ниже, чтобы присоединиться к группе."
        
        if timer_minutes:
            description += f"\n\n⏰ Автозавершение через **{timer_minutes} минут**"
        
        embed.description = description
        return embed
    
    async def _schedule_auto_deletion(self, interaction: discord.Interaction, message: discord.Message, timer_minutes: int):
        auto_timeout_handler = AutoTimeoutHandler(self, interaction, message, timer_minutes)
        await auto_timeout_handler.schedule()
    
    def _create_timeout_embed(self, current_members: list, max_members: int) -> discord.Embed:
        timeout_embed = discord.Embed(
            title="⏰ Время набора истекло!",
            description=f"Группа не была полностью сформирована.\nНабрано: **{len(current_members)}/{max_members}** участников",
            color=0xff6b35
        )
        
        if current_members:
            members_list = ""
            for i, member_id in enumerate(current_members, 1):
                members_list += f"**{i}.** <@{member_id}>\n"
            
            timeout_embed.add_field(
                name="👥 Участники, которые подались:",
                value=members_list,
                inline=False
            )
        else:
            timeout_embed.add_field(
                name="👥 Участники:",
                value="*Никто не подался*",
                inline=False
            )
        
        timeout_embed.set_footer(text="Группа была закрыта по истечению времени")
        return timeout_embed


class AutoTimeoutHandler:
    
    def __init__(self, command: CreateCaptCommand, interaction: discord.Interaction, message: discord.Message, timer_minutes: int):
        self.command = command
        self.interaction = interaction
        self.message = message
        self.timer_minutes = timer_minutes
    
    async def schedule(self):
        asyncio.create_task(self._execute_timeout())
    
    async def _execute_timeout(self):
        await asyncio.sleep(self.timer_minutes * 60)
        
        try:
            capt_info = get_capt(self.interaction.guild_id, self.message.id)
            if capt_info:
                current_members = capt_info.get('current_members', [])
                max_members = capt_info.get('max_members', 0)
                
                if len(current_members) >= max_members:
                    return
                
                timeout_embed = self.command._create_timeout_embed(current_members, max_members)
                await self.message.channel.send(embed=timeout_embed)
                await self.message.delete()
                remove_capt(self.interaction.guild_id, self.message.id)
                
        except Exception as e:
            print(f"Ошибка при завершении группы: {e}")