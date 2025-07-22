import discord
from discord import app_commands
from src.database import (
    get_settings, save_settings, init_owners, owners_cache, is_owner, save_capt,
    add_to_blacklist, get_blacklist, get_blacklist_report_channel
)
from src.permissions import requires_approver
from src.views import FormMessageModal, CaptView


class CommandHandler:
    def __init__(self, bot):
        self.bot = bot
    
    async def handle_error(self, interaction: discord.Interaction, error_message: str):
        if interaction.response.is_done():
            await interaction.followup.send(error_message, ephemeral=True)
        else:
            await interaction.response.send_message(error_message, ephemeral=True)


class BaseCommand(CommandHandler):
    def __init__(self, bot):
        super().__init__(bot)
    
    async def validate_guild(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            await self.handle_error(interaction, "❌ Эта команда доступна только на сервере.")
            return False
        return True


class AddFormCommand(BaseCommand):
    @requires_approver()
    async def execute(self, interaction: discord.Interaction, channel: discord.TextChannel):
        try:
            if not await self.validate_guild(interaction):
                return
            
            save_settings(interaction.guild_id, form_channel_id=channel.id)
            await interaction.response.send_modal(FormMessageModal(channel_id=channel.id))
        except Exception as e:
            await self.handle_error(interaction, "❌ Произошла ошибка при выполнении команды. Пожалуйста, попробуйте снова.")
            print(f"Ошибка в команде addform: {e}")


class ApprovalChannelCommand(BaseCommand):
    @requires_approver()
    async def execute(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        try:
            if not await self.validate_guild(interaction):
                return
            
            save_settings(interaction.guild_id, approv_channel_id=channel.id if channel else None)
            
            if channel:
                await interaction.response.send_message(f"✅ Канал для заявок установлен: {channel.mention}", ephemeral=True)
            else:
                await interaction.response.send_message("✅ Канал для заявок удален.", ephemeral=True)
        except Exception as e:
            await self.handle_error(interaction, "❌ Произошла ошибка при выполнении команды. Пожалуйста, попробуйте снова.")
            print(f"Ошибка в команде approvchannel: {e}")


class GiveApprovalCommand(BaseCommand):
    @requires_approver()
    async def execute(self, interaction: discord.Interaction, approver: discord.Role, approved: discord.Role):
        try:
            if not await self.validate_guild(interaction):
                return
            
            save_settings(
                interaction.guild_id,
                approver_role_id=approver.id,
                approved_role_id=approved.id
            )
            
            embed = self._create_roles_embed(approver, approved)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await self.handle_error(interaction, "❌ Произошла ошибка при выполнении команды. Пожалуйста, попробуйте снова.")
            print(f"Ошибка в команде giveapprov: {e}")
    
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


class CheckRolesCommand(BaseCommand):
    @requires_approver()
    async def execute(self, interaction: discord.Interaction):
        try:
            if not await self.validate_guild(interaction):
                return
                
            init_owners()
            guild_id_str = str(interaction.guild_id)
            approver_role_id = owners_cache.get('approver_role_ids', {}).get(guild_id_str)
            
            embed = discord.Embed(
                title="🔍 Проверка ролей",
                color=0x3498db
            )
            
            self._add_moderator_role_field(embed, interaction.guild, approver_role_id)
            
            form_channel_id, approv_channel_id, approver_role_id_from_settings, approved_role_id, blacklist_report_channel_id = get_settings(interaction.guild_id)
            
            self._add_approved_role_field(embed, interaction.guild, approved_role_id)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await self.handle_error(interaction, "❌ Произошла ошибка при выполнении команды.")
            print(f"Ошибка в команде checkroles: {e}")
    
    def _add_moderator_role_field(self, embed: discord.Embed, guild: discord.Guild, approver_role_id: str):
        if approver_role_id:
            role = guild.get_role(int(approver_role_id))
            if role:
                embed.add_field(
                    name="🛡️ Роль модераторов", 
                    value=f"```diff\n+ {role.name}\n```\n📋 **ID:** `{approver_role_id}`\n👤 **Упоминание:** {role.mention}\n📊 **Участников с ролью:** {len(role.members)}", 
                    inline=False
                )
            else:
                embed.add_field(
                    name="🛡️ Роль модераторов", 
                    value=f"```diff\n- Роль удалена или недоступна\n```\n🆔 **Последний известный ID:** `{approver_role_id}`\n⚠️ **Статус:** Требует переназначения", 
                    inline=False
                )
        else:
            embed.add_field(
                name="🛡️ Роль модераторов", 
                value="```yaml\nСтатус: Не настроена\n```\n🔧 **Действие:** Используйте `/giveapprov` для настройки", 
                inline=False
            )
    
    def _add_approved_role_field(self, embed: discord.Embed, guild: discord.Guild, approved_role_id: str):
        if approved_role_id:
            approved_role = guild.get_role(int(approved_role_id))
            if approved_role:
                embed.add_field(
                    name="🎯 Роль при одобрении", 
                    value=f"```diff\n+ {approved_role.name}\n```\n📋 **ID:** `{approved_role_id}`\n👤 **Упоминание:** {approved_role.mention}\n📊 **Участников с ролью:** {len(approved_role.members)}", 
                    inline=False
                )
            else:
                embed.add_field(
                    name="🎯 Роль при одобрении", 
                    value=f"```diff\n- Роль удалена или недоступна\n```\n🆔 **Последний известный ID:** `{approved_role_id}`\n⚠️ **Статус:** Требует переназначения", 
                    inline=False
                )
        else:
            embed.add_field(
                name="🎯 Роль при одобрении", 
                value="```yaml\nСтатус: Не настроена\n```\n🔧 **Действие:** Используйте `/giveapprov` для настройки", 
                inline=False
            )


class HelpCommand(CommandHandler):
    async def execute(self, interaction: discord.Interaction):
        try:
            embed = self._create_help_embed(interaction)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await self.handle_error(interaction, "❌ Произошла ошибка при выполнении команды.")
            print(f"Ошибка в команде help: {e}")
    
    def _create_help_embed(self, interaction: discord.Interaction) -> discord.Embed:
        embed = discord.Embed(
            title="📋 Команды бота",
            description="Список всех доступных команд:",
            color=0x3498db
        )
        
        commands_data = [
            ("📝 /addform", "Создать форму для подачи заявок\n*Требует права модератора*"),
            ("⚙️ /approvchannel", "Установить канал для обработки заявок\n*Требует права модератора*"),
            ("👥 /giveapprov", "Настроить роли для системы заявок\n*Требует права модератора*"),
            ("🔍 /checkroles", "Проверить настройки ролей\n*Требует права модератора*"),
            ("📋 /createcapt", "Создать группу с ограниченным количеством участников\n*Требует права модератора*"),
            ("📢 /blacklistchannel", "Установить канал для отчетов о блокировках\n*Требует права модератора*"),
            ("⛔ /blacklist", "Добавить пользователя в черный список семей по ID и игровому ID\n*Требует права модератора*"),
            ("📝 /showblacklist", "Показать черный список семей\n*Требует права модератора*"),
            ("❓ /help", "Показать это сообщение\n*Доступно всем*")
        ]
        
        for name, value in commands_data:
            embed.add_field(name=name, value=value, inline=False)
        
        if is_owner(interaction.user.id):
            embed.add_field(
                name="🔄 /sync",
                value="Принудительно синхронизировать команды\n*Только для владельцев бота*",
                inline=False
            )
        
        embed.set_footer(text="Используйте '/' в чате для вызова команд")
        return embed


class SyncCommand(CommandHandler):
    async def execute(self, interaction: discord.Interaction):
        try:
            if not is_owner(interaction.user.id):
                await self.handle_error(interaction, "❌ Эта команда доступна только владельцам бота.")
                return
            
            await interaction.response.defer(ephemeral=True)
            
            try:
                synced = await self.bot.tree.sync()
                embed = self._create_sync_embed(synced)
                await interaction.followup.send(embed=embed, ephemeral=True)
                print(f"✅ Команды синхронизированы вручную пользователем {interaction.user}")
                
            except Exception as e:
                await interaction.followup.send(f"❌ Ошибка при синхронизации команд: {str(e)}", ephemeral=True)
                print(f"❌ Ошибка синхронизации: {e}")
                
        except Exception as e:
            await self.handle_error(interaction, "❌ Произошла ошибка при выполнении команды.")
            print(f"Ошибка в команде sync: {e}")
    
    def _create_sync_embed(self, synced: list) -> discord.Embed:
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


class CreateCaptCommand(BaseCommand):
    @requires_approver()
    async def execute(self, interaction: discord.Interaction, max_members: int):
        try:
            if not await self.validate_guild(interaction):
                return
            
            if not self._validate_members_count(max_members):
                await self.handle_error(interaction, "❌ Количество участников должно быть от 1 до 25")
                return
            
            embed = self._create_capt_embed(max_members)
            view = CaptView(max_members)
            message = await interaction.channel.send(embed=embed, view=view)
            
            save_capt(interaction.guild_id, interaction.channel_id, message.id, max_members, [])
            await interaction.response.send_message("✅ Группа успешно создана!", ephemeral=True, delete_after=0)
            
        except Exception as e:
            await self.handle_error(interaction, "❌ Произошла ошибка при выполнении команды.")
            print(f"Ошибка в команде createcapt: {e}")
    
    def _validate_members_count(self, max_members: int) -> bool:
        return 1 <= max_members <= 25
    
    def _create_capt_embed(self, max_members: int) -> discord.Embed:
        return discord.Embed(
            title="📋 Группа",
            description=f"Участники (0/{max_members}):\n\nНажмите кнопку ниже, чтобы присоединиться к группе.",
            color=0x3498db
        )


class BlacklistChannelCommand(BaseCommand):
    @requires_approver()
    async def execute(self, interaction: discord.Interaction, channel: discord.TextChannel):
        try:
            if not await self.validate_guild(interaction):
                return
            
            save_settings(interaction.guild_id, blacklist_report_channel_id=channel.id)
            await interaction.response.send_message(f"✅ Канал для отчетов о блокировках установлен: {channel.mention}", ephemeral=True)
            
        except Exception as e:
            await self.handle_error(interaction, "❌ Произошла ошибка при выполнении команды.")
            print(f"Ошибка в команде blacklistchannel: {e}")


class BlacklistCommand(BaseCommand):
    @requires_approver()
    async def execute(self, interaction: discord.Interaction, user_id: str, static_id_majestic: str, reason: str):
        try:
            if not await self.validate_guild(interaction):
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
            
        except Exception as e:
            await self.handle_error(interaction, "❌ Произошла ошибка при выполнении команды.")
            print(f"Ошибка в команде blacklist: {e}")
    
    async def _get_report_channel(self, interaction: discord.Interaction):
        report_channel_id = get_blacklist_report_channel(interaction.guild_id)
        if not report_channel_id:
            await self.handle_error(interaction, "❌ Сначала установите канал для отчетов с помощью команды /blacklistreport")
            return None

        report_channel = interaction.guild.get_channel(int(report_channel_id))
        if not report_channel:
            await self.handle_error(interaction, "❌ Канал для отчетов не найден. Пожалуйста, переустановите его с помощью команды /blacklistreport")
            return None
        
        return report_channel
    
    async def _find_user_and_member(self, interaction: discord.Interaction, user_id: str):
        try:
            user = await self.bot.fetch_user(int(user_id))
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
        except discord.HTTPException as e:
            await self.handle_error(interaction, f"❌ Ошибка при поиске пользователя: {str(e)}")
            return None, None
    
    def _create_blacklist_embed(self, user: discord.User, static_id_majestic: str, reason: str, moderator: discord.User) -> discord.Embed:
        embed = discord.Embed(
            title="⛔ Новая запись в черном списке",
            description=f"Пользователь добавлен в черный список семей",
            color=0xFF0000
        )
        
        embed.add_field(
            name="👤 Пользователь",
            value=f"{user.mention} ({user.name}#{user.discriminator})\nID: {user.id}",
            inline=False
        )

        embed.add_field(
            name="🎮 Игровой StaticID",
            value=f"{static_id_majestic}",
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
            # Проверяем права бота для бана
            bot_member = interaction.guild.get_member(self.bot.user.id)
            if not bot_member.guild_permissions.ban_members:
                await interaction.response.send_message(f"⚠️ Пользователь добавлен в черный список, но у бота нет прав на бан участников.", ephemeral=True)
                print(f"❌ Нет прав для бана пользователя {user.id}")
                return
            
            # Проверяем, может ли бот забанить этого пользователя (проверка иерархии ролей)
            if member.top_role >= bot_member.top_role:
                await interaction.response.send_message(f"⚠️ Пользователь добавлен в черный список, но у бота недостаточно прав для бана этого пользователя (иерархия ролей).", ephemeral=True)
                print(f"❌ Недостаточно прав для бана пользователя {user.id} (иерархия ролей)")
                return
            
            print(f"🔨 Попытка забанить пользователя {user.id} ({user.name}#{user.discriminator})")
            
            # Банимр пользователя (это автоматически удаляет его с сервера)
            await interaction.guild.ban(user, reason=f"Добавлен в черный список: {reason}")
            print(f"✅ Пользователь {user.id} успешно забанен")
            await interaction.response.send_message(f"✅ Пользователь {user.mention} добавлен в черный список и забанен.", ephemeral=True)
        except discord.Forbidden as e:
            print(f"❌ Недостаточно прав для бана пользователя {user.id}: {e}")
            await interaction.response.send_message(f"⚠️ Пользователь добавлен в черный список, но у меня недостаточно прав для бана.", ephemeral=True)
        except discord.HTTPException as e:
            print(f"❌ HTTP ошибка при бане пользователя {user.id}: {e}")
            await interaction.response.send_message(f"⚠️ Пользователь добавлен в черный список, но произошла ошибка при бане: {str(e)}", ephemeral=True)


class ShowBlacklistCommand(BaseCommand):
    @requires_approver()
    async def execute(self, interaction: discord.Interaction):
        try:
            if not await self.validate_guild(interaction):
                return
            
            blacklist = get_blacklist(interaction.guild_id)
            
            if not blacklist:
                await interaction.response.send_message("📝 Черный список пуст.", ephemeral=True)
                return
            
            embed = await self._create_blacklist_embed(blacklist)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await self.handle_error(interaction, "❌ Произошла ошибка при выполнении команды.")
            print(f"Ошибка в команде showblacklist: {e}")
    
    async def _create_blacklist_embed(self, blacklist: dict) -> discord.Embed:
        embed = discord.Embed(
            title="📝 Черный список семей",
            description="Список пользователей в черном списке:",
            color=0xFF0000
        )
        
        for user_id, data in blacklist.items():
            user = await self.bot.fetch_user(int(user_id))
            reporter = await self.bot.fetch_user(int(data['reporter_id']))
            
            field_value = f"**ID:** {user_id}\n**Причина:** {data['reason']}\n**Добавил:** {reporter.name}#{reporter.discriminator}"
            
            if 'static_id_majestic' in data:
                field_value += f"\n**Игровой ID:** {data['static_id_majestic']}"
            
            embed.add_field(
                name=f"👤 {user.name}#{user.discriminator}",
                value=field_value,
                inline=False
            )
        
        return embed


class CommandRegistry:
    def __init__(self, bot):
        self.bot = bot
        self.commands = {
            'addform': AddFormCommand(bot),
            'approvchannel': ApprovalChannelCommand(bot),
            'giveapprov': GiveApprovalCommand(bot),
            'checkroles': CheckRolesCommand(bot),
            'help': HelpCommand(bot),
            'sync': SyncCommand(bot),
            'createcapt': CreateCaptCommand(bot),
            'blacklist': BlacklistCommand(bot),
            'showblacklist': ShowBlacklistCommand(bot),
            'blacklistchannel': BlacklistChannelCommand(bot)
        }
    
    def register_all(self):
        @self.bot.tree.command(
            name="addform", 
            description="📝 Создать форму для подачи заявок пользователями"
        )
        @app_commands.describe(
            channel="Канал, где будет размещена форма для подачи заявок"
        )
        async def addform(interaction: discord.Interaction, channel: discord.TextChannel):
            await self.commands['addform'].execute(interaction, channel)

        @self.bot.tree.command(
            name="approvchannel", 
            description="⚙️ Установить или удалить канал для обработки заявок"
        )
        @app_commands.describe(
            channel="Канал для заявок (оставьте пустым для удаления текущего канала)"
        )
        async def approvchannel(interaction: discord.Interaction, channel: discord.TextChannel = None):
            await self.commands['approvchannel'].execute(interaction, channel)

        @self.bot.tree.command(
            name="giveapprov", 
            description="👥 Назначить роли для обработки заявок и выдачи при одобрении"
        )
        @app_commands.describe(
            approver="Роль, участники которой смогут одобрять/отклонять заявки",
            approved="Роль, которая будет выдана пользователю при одобрении заявки"
        )
        async def giveapprov(interaction: discord.Interaction, approver: discord.Role, approved: discord.Role):
            await self.commands['giveapprov'].execute(interaction, approver, approved)

        @self.bot.tree.command(
            name="checkroles", 
            description="🔍 Проверить настройки ролей и их наличие на сервере"
        )
        async def checkroles(interaction: discord.Interaction):
            await self.commands['checkroles'].execute(interaction)

        @self.bot.tree.command(
            name="help", 
            description="❓ Показать список всех доступных команд бота"
        )
        async def help_command(interaction: discord.Interaction):
            await self.commands['help'].execute(interaction)

        @self.bot.tree.command(
            name="sync",
            description="🔄 Принудительно синхронизировать команды бота с Discord"
        )
        async def sync_commands(interaction: discord.Interaction):
            await self.commands['sync'].execute(interaction)

        @self.bot.tree.command(
            name="createcapt",
            description="📋 Создать группу с ограниченным количеством участников"
        )
        @app_commands.describe(
            max_members="Максимальное количество участников в группе (от 2 до 25)"
        )
        async def createcapt(interaction: discord.Interaction, max_members: int):
            await self.commands['createcapt'].execute(interaction, max_members)

        @self.bot.tree.command(
            name="blacklistchannel",
            description="📢 Установить канал для отчетов о блокировках"
        )
        @app_commands.describe(
            channel="Канал для публикации отчетов о блокировках"
        )
        async def blacklistchannel(interaction: discord.Interaction, channel: discord.TextChannel):
            await self.commands['blacklistchannel'].execute(interaction, channel)

        @self.bot.tree.command(
            name="blacklist",
            description="⛔ Добавить пользователя в черный список семей"
        )
        @app_commands.describe(
            user_id="ID пользователя (например: 1395845799174344776)",
            static_id_majestic="Игровой ID пользователя",
            reason="Причина добавления в черный список"
        )
        async def blacklist(interaction: discord.Interaction, user_id: str, static_id_majestic: str, reason: str):
            await self.commands['blacklist'].execute(interaction, user_id, static_id_majestic, reason)

        @self.bot.tree.command(
            name="showblacklist",
            description="📝 Показать черный список семей"
        )
        async def showblacklist(interaction: discord.Interaction):
            await self.commands['showblacklist'].execute(interaction)

        print("📋 Все команды зарегистрированы успешно")


async def setup_commands(bot):
    registry = CommandRegistry(bot)
    registry.register_all()