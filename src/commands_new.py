import discord
from src.core import CommandRegistry


class CommandSetup:
    def __init__(self, bot: discord.Client):
        self.bot = bot
        self.registry = None
    
    async def setup_commands(self) -> CommandRegistry:
        self.registry = CommandRegistry(self.bot)
        await self.registry.setup_slash_commands()
        return self.registry


class LegacyCommandSetup:
    def __init__(self, command_setup: CommandSetup):
        self.command_setup = command_setup
    
    async def setup_commands_legacy(self) -> CommandRegistry:
        return await self.command_setup.setup_commands()


class AvailableCommandsProvider:
    @staticmethod
    def get_available_commands():
        from src.commands.role_management.config import RoleManagementConfig
        return RoleManagementConfig.get_all_commands()


class CommandsModule:
    def __init__(self, bot: discord.Client):
        self.command_setup = CommandSetup(bot)
        self.legacy_setup = LegacyCommandSetup(self.command_setup)
        self.commands_provider = AvailableCommandsProvider()
    
    async def setup_commands(self) -> CommandRegistry:
        return await self.command_setup.setup_commands()
    
    async def setup_commands_legacy(self) -> CommandRegistry:
        return await self.legacy_setup.setup_commands_legacy()
    
    def get_available_commands(self):
        return self.commands_provider.get_available_commands()


__all__ = [
    'CommandsModule',
    'CommandSetup',
    'LegacyCommandSetup',
    'AvailableCommandsProvider'
]