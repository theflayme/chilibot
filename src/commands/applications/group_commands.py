"""
Команды для создания и управления группами
"""

import discord
import asyncio
from src.core.base_command import PermissionCommand
from src.database_firebase import save_capt, get_capt, remove_capt
from src.views import CaptView


class CreateCaptCommand(PermissionCommand):
    """Команда для создания групп с ограниченным количеством участников"""
    
    def __init__(self, bot: discord.Client):
        super().__init__(
            bot=bot,
            name="createcapt",
            description="📋 Создать группу с ограниченным количеством участников и таймером",
            required_permission="createcapt"
        )
    
    async def execute(self, interaction: discord.Interaction, max_members: int, timer_minutes: int = None, **kwargs) -> None:
        """Выполнить команду создания группы"""
        if not await self.validate(interaction):
            return
        
        # Валидация параметров
        if not self._validate_members_count(max_members):
            await self.handle_error(interaction, "❌ Количество участников должно быть от 2 до 50")
            return
        
        if timer_minutes is not None and not self._validate_timer(timer_minutes):
            await self.handle_error(interaction, "❌ Таймер должен быть от 1 до 1440 минут (24 часа)")
            return
        
        # Создаем группу
        embed = self._create_capt_embed(max_members, timer_minutes)
        view = CaptView(max_members, timer_minutes)
        message = await interaction.channel.send(embed=embed, view=view)
        
        # Сохраняем в базу данных
        save_capt(interaction.guild_id, interaction.channel_id, message.id, max_members, [], timer_minutes)
        
        # Если есть таймер, запускаем автоудаление
        if timer_minutes:
            await self._schedule_auto_deletion(interaction, message, timer_minutes)
        
        # Отправляем подтверждение
        success_msg = f"✅ Группа успешно создана!"
        if timer_minutes:
            success_msg += f" Автозавершение через {timer_minutes} мин."
        
        await interaction.response.send_message(success_msg, ephemeral=True, delete_after=0)
    
    def _validate_members_count(self, max_members: int) -> bool:
        """Проверить корректность количества участников"""
        return 2 <= max_members <= 50
    
    def _validate_timer(self, timer_minutes: int) -> bool:
        """Проверить корректность таймера"""
        return 1 <= timer_minutes <= 1440  # от 1 минуты до 24 часов
    
    def _create_capt_embed(self, max_members: int, timer_minutes: int = None) -> discord.Embed:
        """Создать embed для группы"""
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
        """Планирует завершение группы через указанное время"""
        
        async def auto_timeout():
            await asyncio.sleep(timer_minutes * 60)  # Конвертируем минуты в секунды
            
            try:
                # Проверяем, существует ли еще группа
                capt_info = get_capt(interaction.guild_id, message.id)
                if capt_info:
                    current_members = capt_info.get('current_members', [])
                    max_members = capt_info.get('max_members', 0)
                    
                    # Проверяем, заполнена ли группа
                    if len(current_members) >= max_members:
                        # Группа уже заполнена, ничего не делаем
                        return
                    
                    # Создаем embed о завершении времени
                    timeout_embed = self._create_timeout_embed(current_members, max_members)
                    
                    # Отправляем уведомление в канал
                    await message.channel.send(embed=timeout_embed)
                    
                    # Удаляем оригинальное сообщение группы
                    await message.delete()
                    
                    # Удаляем группу из базы данных
                    remove_capt(interaction.guild_id, message.id)
                    
            except Exception as e:
                print(f"Ошибка при завершении группы: {e}")
        
        # Запускаем задачу в фоне
        asyncio.create_task(auto_timeout())
    
    def _create_timeout_embed(self, current_members: list, max_members: int) -> discord.Embed:
        """Создать embed о завершении времени"""
        timeout_embed = discord.Embed(
            title="⏰ Время набора истекло!",
            description=f"Группа не была полностью сформирована.\nНабрано: **{len(current_members)}/{max_members}** участников",
            color=0xff6b35
        )
        
        # Добавляем список участников, если они есть
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