import discord
from discord.ext import commands
import asyncio
import os

from dotenv import load_dotenv
load_dotenv()

from src.database import (
    init_settings,
    init_applications,
    init_owners,
    sync_approver_role,
    applications_cache,
    owners_cache
)
from src.views import ApplyButtonView, ApplicationView
from src.commands import setup_commands
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
        print(f'🤖 Бот {self.bot.user} запускается...')
        
        try:
            await self._initialize_data()
            print("✨ Инициализация данных завершена")
        except Exception as e:
            print(f"❌ Ошибка при инициализации данных: {e}")
        
        self._add_persistent_views()
        await self._restore_application_views()
        
        print(f'🎉 Бот {self.bot.user} готов к работе!')
        
        try:
            await self._setup_commands()
            print("⚙️ Команды успешно настроены")
        except Exception as e:
            print(f'❌ Ошибка при настройке команд: {e}')
        
        try:
            await self._sync_commands()
        except Exception as e:
            print(f'❌ Ошибка синхронизации команд: {e}')
        
        try:
            self._start_cleanup_task()
            print("🧹 Задача очистки старых состояний запущена")
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
        for guild_id, applications in applications_cache.items():
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                continue
            for message_id, app_data in applications.items():
                channel = guild.get_channel(int(app_data['channel_id']))
                if not channel:
                    continue
                
                try:
                    message = await channel.fetch_message(int(message_id))
                    if message.components and any(isinstance(c, discord.ui.Button) for row in message.components for c in row.children):
                        self.bot.add_view(ApplicationView(applicant_id=app_data['applicant_id'], message_id=message_id, guild_id=int(guild_id), bot=self.bot))
                        continue
                except discord.NotFound:
                    pass

                embed = self._create_embed_from_data(app_data['embed_data'])
                content = self._create_content(app_data, guild, guild_id)
                view = ApplicationView(applicant_id=app_data['applicant_id'], message_id=message_id, guild_id=int(guild_id), bot=self.bot)
                
                self.bot.add_view(view)
                await channel.send(content=content, embed=embed, view=view)
                await asyncio.sleep(0.1)

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
        approver_role_id = owners_cache.get('approver_role_ids', {}).get(guild_id)
        role = guild.get_role(int(approver_role_id)) if approver_role_id else None
        mention = role.mention if role else "@everyone"
        return f"{mention} <@{app_data['applicant_id']}>"

    async def _setup_commands(self):
        await setup_commands(self.bot)

    async def _sync_commands(self):
        print("🔄 Синхронизация команд с Discord...")
        synced = await self.bot.tree.sync()
        
        print(f'✅ Синхронизировано {len(synced)} slash команд:')
        for command in synced:
            command_emoji = {
                'addform': '📝',
                'approvchannel': '⚙️',
                'giveapprov': '👥',
                'checkroles': '🔍',
                'help': '❓',
                'sync': '🔄'
            }
            emoji = command_emoji.get(command.name, '🔹')
            print(f"  {emoji} /{command.name}: {command.description}")
        
        print("📝 Команды теперь доступны в интерфейсе Discord через '/'")

    def _start_cleanup_task(self):
        self.bot.loop.create_task(clear_old_states())

    async def _handle_command_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        if isinstance(error, discord.app_commands.MissingPermissions):
            await interaction.response.send_message("❌ У вас нет прав для выполнения этой команды.", ephemeral=True)
        elif isinstance(error, discord.app_commands.CommandOnCooldown):
            await interaction.response.send_message(f"⏰ Команда на перезарядке. Попробуйте через {error.retry_after:.2f} секунд.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Произошла ошибка при выполнении команды.", ephemeral=True)
            print(f"Ошибка команды: {error}")

    def run(self):
        self.bot.run(self.bot_token)

class Application:
    def __init__(self):
        self.bot_manager = BotManager()

    def run(self):
        print("🚀 Запуск бота...")
        self.bot_manager.run()

if __name__ == "__main__":
    app = Application()
    app.run()