import discord
from discord import app_commands
from src.database import get_settings, save_settings, init_owners, owners_cache, is_owner, save_capt
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

class AddFormCommand(CommandHandler):
    @requires_approver()
    async def execute(self, interaction: discord.Interaction, channel: discord.TextChannel):
        try:
            if interaction.guild is None:
                await self.handle_error(interaction, "❌ Эта команда доступна только на сервере.")
                return
            
            save_settings(interaction.guild_id, form_channel_id=channel.id)
            await interaction.response.send_modal(FormMessageModal(channel_id=channel.id))
        except Exception as e:
            await self.handle_error(interaction, "❌ Произошла ошибка при выполнении команды. Пожалуйста, попробуйте снова.")
            print(f"Ошибка в команде addform: {e}")

class ApprovalChannelCommand(CommandHandler):
    @requires_approver()
    async def execute(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        try:
            if interaction.guild is None:
                await self.handle_error(interaction, "❌ Эта команда доступна только на сервере.")
                return
            
            save_settings(interaction.guild_id, approv_channel_id=channel.id if channel else None)
            
            if channel:
                await interaction.response.send_message(f"✅ Канал для заявок установлен: {channel.mention}", ephemeral=True)
            else:
                await interaction.response.send_message("✅ Канал для заявок удален.", ephemeral=True)
        except Exception as e:
            await self.handle_error(interaction, "❌ Произошла ошибка при выполнении команды. Пожалуйста, попробуйте снова.")
            print(f"Ошибка в команде approvchannel: {e}")

class GiveApprovalCommand(CommandHandler):
    @requires_approver()
    async def execute(self, interaction: discord.Interaction, approver: discord.Role, approved: discord.Role):
        try:
            if interaction.guild is None:
                await self.handle_error(interaction, "❌ Эта команда доступна только на сервере.")
                return
            
            save_settings(
                interaction.guild_id,
                approver_role_id=approver.id,
                approved_role_id=approved.id
            )
            
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
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await self.handle_error(interaction, "❌ Произошла ошибка при выполнении команды. Пожалуйста, попробуйте снова.")
            print(f"Ошибка в команде giveapprov: {e}")

class CheckRolesCommand(CommandHandler):
    @requires_approver()
    async def execute(self, interaction: discord.Interaction):
        try:
            if interaction.guild is None:
                await self.handle_error(interaction, "❌ Эта команда доступна только на сервере.")
                return
                
            init_owners()
            guild_id_str = str(interaction.guild_id)
            approver_role_id = owners_cache.get('approver_role_ids', {}).get(guild_id_str)
            
            embed = discord.Embed(
                title="🔍 Проверка ролей",
                color=0x3498db
            )
            
            if approver_role_id:
                role = interaction.guild.get_role(int(approver_role_id))
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
            
            form_channel_id, approv_channel_id, approver_role_id_from_settings, approved_role_id = get_settings(interaction.guild_id)
            
            if approved_role_id:
                approved_role = interaction.guild.get_role(int(approved_role_id))
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
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await self.handle_error(interaction, "❌ Произошла ошибка при выполнении команды.")
            print(f"Ошибка в команде checkroles: {e}")

class HelpCommand(CommandHandler):
    async def execute(self, interaction: discord.Interaction):
        try:
            embed = discord.Embed(
                title="📋 Команды бота",
                description="Список всех доступных команд:",
                color=0x3498db
            )
            
            embed.add_field(
                name="📝 /addform",
                value="Создать форму для подачи заявок\n*Требует права модератора*",
                inline=False
            )
            
            embed.add_field(
                name="⚙️ /approvchannel",
                value="Установить канал для обработки заявок\n*Требует права модератора*",
                inline=False
            )
            
            embed.add_field(
                name="👥 /giveapprov",
                value="Настроить роли для системы заявок\n*Требует права модератора*",
                inline=False
            )
            
            embed.add_field(
                name="🔍 /checkroles",
                value="Проверить настройки ролей\n*Требует права модератора*",
                inline=False
            )
            
            embed.add_field(
                name="📋 /createcapt",
                value="Создать группу с ограниченным количеством участников\n*Требует права модератора*",
                inline=False
            )
            
            embed.add_field(
                name="❓ /help",
                value="Показать это сообщение\n*Доступно всем*",
                inline=False
            )
            
            if is_owner(interaction.user.id):
                embed.add_field(
                    name="🔄 /sync",
                    value="Принудительно синхронизировать команды\n*Только для владельцев бота*",
                    inline=False
                )
            
            embed.set_footer(text="Используйте '/' в чате для вызова команд")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await self.handle_error(interaction, "❌ Произошла ошибка при выполнении команды.")
            print(f"Ошибка в команде help: {e}")

class SyncCommand(CommandHandler):
    async def execute(self, interaction: discord.Interaction):
        try:
            if not is_owner(interaction.user.id):
                await self.handle_error(interaction, "❌ Эта команда доступна только владельцам бота.")
                return
            
            await interaction.response.defer(ephemeral=True)
            
            try:
                synced = await self.bot.tree.sync()
                
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
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                print(f"✅ Команды синхронизированы вручную пользователем {interaction.user}")
                
            except Exception as e:
                await interaction.followup.send(f"❌ Ошибка при синхронизации команд: {str(e)}", ephemeral=True)
                print(f"❌ Ошибка синхронизации: {e}")
                
        except Exception as e:
            await self.handle_error(interaction, "❌ Произошла ошибка при выполнении команды.")
            print(f"Ошибка в команде sync: {e}")

class CreateCaptCommand(CommandHandler):
    @requires_approver()
    async def execute(self, interaction: discord.Interaction, max_members: int):
        try:
            if interaction.guild is None:
                await self.handle_error(interaction, "❌ Эта команда доступна только на сервере.")
                return
            
            if max_members < 1:
                await self.handle_error(interaction, "❌ Минимальное количество участников: 1")
                return
            
            if max_members > 25:
                await self.handle_error(interaction, "❌ Максимальное количество участников: 25")
                return
            
            embed = discord.Embed(
                title="📋 Группа",
                description=f"Участники (0/{max_members}):\n\nНажмите кнопку ниже, чтобы присоединиться к группе.",
                color=0x3498db
            )
            
            view = CaptView(max_members)
            message = await interaction.channel.send(embed=embed, view=view)
            
            # Сохраняем информацию о капте
            save_capt(interaction.guild_id, interaction.channel_id, message.id, max_members, [])
            
            # Отправляем подтверждение и сразу удаляем его
            await interaction.response.send_message("✅ Группа успешно создана!", ephemeral=True, delete_after=0)
            
        except Exception as e:
            await self.handle_error(interaction, "❌ Произошла ошибка при выполнении команды.")
            print(f"Ошибка в команде createcapt: {e}")

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
            'createcapt': CreateCaptCommand(bot)
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

        print("📋 Все команды зарегистрированы успешно")

async def setup_commands(bot):
    registry = CommandRegistry(bot)
    registry.register_all()