import discord
from discord import app_commands
from src.database_firebase import is_owner, init_owners, owners_cache, get_role_permissions


class PermissionChecker:
    def __init__(self):
        self._owners_cache = None
    
    def _update_cache(self):
        init_owners()
        self._owners_cache = owners_cache()
    
    def _get_guild_id_string(self, guild_id: int) -> str:
        return str(guild_id)
    
    def _get_approver_role_id(self, guild_id_str: str) -> str:
        if not self._owners_cache:
            return None
        return self._owners_cache.get('approver_role_ids', {}).get(guild_id_str)
    
    def _validate_guild(self, interaction: discord.Interaction) -> bool:
        return interaction.guild is not None
    
    def _is_owner(self, user_id: int) -> bool:
        return is_owner(user_id)
    
    def _get_role(self, guild: discord.Guild, role_id: str) -> discord.Role:
        try:
            return guild.get_role(int(role_id))
        except ValueError:
            return None
    
    def _user_has_role(self, user: discord.Member, role: discord.Role) -> bool:
        return role in user.roles
    
    async def check_approver(self, interaction: discord.Interaction) -> bool:
        if not self._validate_guild(interaction):
            return False
        
        if self._is_owner(interaction.user.id):
            return True
        
        self._update_cache()
        guild_id_str = self._get_guild_id_string(interaction.guild_id)
        approver_role_id = self._get_approver_role_id(guild_id_str)
        
        if not approver_role_id:
            return False
        
        role = self._get_role(interaction.guild, approver_role_id)
        if role is None:
            return False
        
        return self._user_has_role(interaction.user, role)
    
    async def check_command_permission(self, interaction: discord.Interaction, command_name: str) -> bool:
        if not self._validate_guild(interaction):
            return False
        
        if self._is_owner(interaction.user.id):
            return True
        
        user_roles = [role.id for role in interaction.user.roles]
        
        for role_id in user_roles:
            permissions = get_role_permissions(interaction.guild_id, role_id)
            if command_name in permissions:
                return True
        
        return await self.check_approver(interaction)
    
    def requires_approver(self):
        async def predicate(interaction: discord.Interaction) -> bool:
            return self._is_owner(interaction.user.id) or await self.check_approver(interaction)
        return app_commands.check(predicate)
    
    def requires_command_permission(self, command_name: str):
        async def predicate(interaction: discord.Interaction) -> bool:
            return await self.check_command_permission(interaction, command_name)
        return app_commands.check(predicate)


class PermissionService:
    def __init__(self):
        self._permission_checker = PermissionChecker()
    
    async def check_approver(self, interaction: discord.Interaction) -> bool:
        return await self._permission_checker.check_approver(interaction)
    
    async def check_command_permission(self, interaction: discord.Interaction, command_name: str) -> bool:
        return await self._permission_checker.check_command_permission(interaction, command_name)
    
    def requires_approver(self):
        return self._permission_checker.requires_approver()
    
    def requires_command_permission(self, command_name: str):
        return self._permission_checker.requires_command_permission(command_name)


class UniversalPermissionChecker:
    def __init__(self, permission_service: PermissionService):
        self._permission_service = permission_service
        self._always_allowed_commands = ['help']
        self._owner_only_commands = ['sync', 'manageroles']
    
    def _is_always_allowed(self, command_name: str) -> bool:
        return command_name in self._always_allowed_commands
    
    def _is_owner_only(self, command_name: str) -> bool:
        return command_name in self._owner_only_commands
    
    async def _check_permission_predicate(self, interaction: discord.Interaction) -> bool:
        command_name = interaction.command.name if interaction.command else "unknown"
        
        if self._is_always_allowed(command_name):
            return True
            
        if self._is_owner_only(command_name):
            return is_owner(interaction.user.id)
        
        return await self._permission_service.check_command_permission(interaction, command_name)
    
    def get_check_decorator(self):
        return app_commands.check(self._check_permission_predicate)


_permission_service = PermissionService()
_universal_checker = UniversalPermissionChecker(_permission_service)


async def check_approver(interaction: discord.Interaction) -> bool:
    return await _permission_service.check_approver(interaction)


async def check_command_permission(interaction: discord.Interaction, command_name: str) -> bool:
    return await _permission_service.check_command_permission(interaction, command_name)


def requires_approver():
    return _permission_service.requires_approver()


def requires_command_permission(command_name: str):
    return _permission_service.requires_command_permission(command_name)


def universal_permission_check():
    return _universal_checker.get_check_decorator()