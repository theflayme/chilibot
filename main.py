import discord
from discord.ext import commands
import asyncio
import os

from dotenv import load_dotenv
load_dotenv()

from src.database_firebase import (
    init_settings,
    init_applications,
    init_owners,
    sync_approver_role,
    applications_cache,
    owners_cache
)
from src.views import ApplyButtonView, ApplicationView
from src.commands_new import CommandsModule
from src.utils import clear_old_states

class BotManager:
    def __init__(self):
        self.intents = discord.Intents.default()
        self.bot_token = os.getenv('BOT_TOKEN')
        self.bot = commands.Bot(command_prefix='/', intents=self.intents)
        self._setup_events()

    def _setup_events(self):
        @self.bot.event
        async def on_ready():
            await self._handle_ready()

        @self.bot.tree.error
        async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
            await self._handle_command_error(interaction, error)

    async def _handle_ready(self):
        try:
            await self._initialize_data()
        except Exception as e:
            print(f"❌ Ошибка при инициализации данных: {e}")
        
        self._add_persistent_views()
        await self._restore_application_views()
        
        try:
            await self._setup_commands()
        except Exception as e:
            print(f'❌ Ошибка при настройке команд: {e}')
        
        try:
            await self._sync_commands()
        except Exception as e:
            print(f'❌ Ошибка синхронизации команд: {e}')
        
        try:
            self._start_cleanup_task()
        except Exception as e:
            print(f'❌ Ошибка при запуске задачи очистки: {e}')

    async def _initialize_data(self):
        init_settings()
        init_applications()
        init_owners()
        sync_approver_role()

    def _add_persistent_views(self):
        self.bot.add_view(ApplyButtonView(self.bot))

    async def _restore_application_views(self):
        try:
            app_cache = applications_cache()
            
            if not app_cache:
                return
            
            for guild_id, applications in app_cache.items():
                guild = self.bot.get_guild(int(guild_id))
                if not guild:
                    continue
                
                for message_id, app_data in applications.items():
                    channel = guild.get_channel(int(app_data['channel_id']))
                    if not channel:
                        print(f"⚠️ Канал не найден для заявки {message_id}, пропускаем")
                        continue
                    
                    try:
                        message = await channel.fetch_message(int(message_id))
                        
                        # Проверяем, обработана ли заявка (есть ли поле "Рассмотрел заявку" в embed)
                        is_processed = False
                        if message.embeds:
                            embed = message.embeds[0]
                            for field in embed.fields:
                                if "Рассмотрел заявку" in field.name:
                                    is_processed = True
                                    break
                        
                        # Восстанавливаем view только для необработанных заявок
                        if not is_processed:
                            view = ApplicationView(
                                applicant_id=app_data['applicant_id'], 
                                message_id=message_id, 
                                guild_id=int(guild_id), 
                                bot=self.bot
                            )
                            self.bot.add_view(view)
                            print(f"✅ Восстановлено view для заявки {message_id}")
                        else:
                            print(f"⚠️ Заявка {message_id} уже обработана модератором")
                        
                    except discord.NotFound:
                        print(f"⚠️ Сообщение заявки {message_id} не найдено в чате")
                        
                    except discord.Forbidden:
                        print(f"⚠️ Нет доступа к каналу для заявки {message_id}")
                        
                    except Exception as e:
                        print(f"❌ Ошибка при проверке сообщения {message_id}: {e}")
                        
                    await asyncio.sleep(0.1)
                        
        except Exception as e:
            print(f"❌ Критическая ошибка восстановления заявок: {e}")
            import traceback
            traceback.print_exc()

    def _create_embed_from_data(self, embed_data):
        embed = discord.Embed(
            title=embed_data['title'],
            description=embed_data.get('description'),
            color=embed_data['color']
        )
        if embed_data.get('thumbnail'):
            embed.set_thumbnail(url=embed_data['thumbnail']['url'])
        for field in embed_data['fields']:
            embed.add_field(name=field['name'], value=field['value'], inline=field['inline'])
        if embed_data.get('footer'):
            embed.set_footer(text=embed_data['footer']['text'])
        return embed

    def _create_content(self, app_data, guild, guild_id):
        guild_id_str = str(guild_id)
        owner_data = owners_cache()
        approver_role_id = owner_data.get('approver_role_ids', {}).get(guild_id_str)
        role = guild.get_role(int(approver_role_id)) if approver_role_id else None
        mention = role.mention if role else "@everyone"
        return f"{mention} <@{app_data['applicant_id']}>"

    async def _setup_commands(self):
        commands_module = CommandsModule(self.bot)
        await commands_module.setup_commands()

    async def _sync_commands(self):
        synced = await self.bot.tree.sync()

    def _start_cleanup_task(self):
        self.bot.loop.create_task(clear_old_states())

    async def _handle_command_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        if interaction.response.is_done():
            print(f"Interaction уже обработан: {error}")
            return
            
        if isinstance(error, discord.app_commands.MissingPermissions):
            await interaction.response.send_message("❌ У вас нет прав для выполнения этой команды.", ephemeral=True)
        elif isinstance(error, discord.app_commands.CommandOnCooldown):
            await interaction.response.send_message(f"⏰ Команда на перезарядке. Попробуйте через {error.retry_after:.2f} секунд.", ephemeral=True)
        elif isinstance(error, discord.app_commands.CheckFailure):
            command_name = interaction.command.name if interaction.command else "unknown"
            
            from src.database_firebase import is_owner
            
            if command_name in ['sync', 'manageroles'] and not is_owner(interaction.user.id):
                await interaction.response.send_message("❌ Эта команда доступна только владельцам бота.", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ У вас нет прав для использования команды `/{command_name}`. Обратитесь к администрации.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Произошла ошибка при выполнении команды.", ephemeral=True)
            print(f"Ошибка команды: {error}")

    def run(self):
        self.bot.run(self.bot_token)

class Application:
    def __init__(self):
        self.bot_manager = BotManager()

    def run(self):
        self.bot_manager.run()

if __name__ == "__main__":
    app = Application()
    app.run()