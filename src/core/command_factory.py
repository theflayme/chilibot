import discord
from .interfaces import ICommand, ICommandFactory
from .base_command import BaseCommand


class CommandFactory(ICommandFactory):
    
    def __init__(self):
        self._command_types = {}
        self._register_default_commands()
    
    def _register_default_commands(self):
        from src.commands.system import HelpCommand, SyncCommand
        from src.commands.role_management import ManageRolesCommand
        from src.commands.applications import (
            AddFormCommand, 
            ApprovalChannelCommand, 
            GiveApprovalCommand,
            CreateCaptCommand
        )
        from src.commands.moderation import (
            BlacklistCommand,
            UnblacklistCommand, 
            BlacklistChannelCommand
        )
        
        self.register_command_type("help", HelpCommand)
        self.register_command_type("sync", SyncCommand)
        self.register_command_type("manageroles", ManageRolesCommand)
        self.register_command_type("addform", AddFormCommand)
        self.register_command_type("approvchannel", ApprovalChannelCommand)
        self.register_command_type("giveapprov", GiveApprovalCommand)
        self.register_command_type("createcapt", CreateCaptCommand)
        self.register_command_type("blacklist", BlacklistCommand)
        self.register_command_type("unblacklist", UnblacklistCommand)
        self.register_command_type("blacklistchannel", BlacklistChannelCommand)
    
    def register_command_type(self, command_type: str, command_class: ICommand) -> None:
        if not issubclass(command_class, BaseCommand):
            raise TypeError(f"Command class {command_class} must inherit from BaseCommand")
        
        self._command_types[command_type] = command_class
    
    def create_command(self, command_type: str, bot: discord.Client, **kwargs) -> ICommand:
        if command_type not in self._command_types:
            raise ValueError(f"Unknown command type: {command_type}")
        
        command_class = self._command_types[command_type]
        
        try:
            command = command_class(bot, **kwargs)
            return command
        except Exception as e: 
            raise
    
    def get_available_command_types(self) -> list:
        return list(self._command_types.keys())
    
    def is_command_type_registered(self, command_type: str) -> bool:
        return command_type in self._command_types


command_factory = CommandFactory()