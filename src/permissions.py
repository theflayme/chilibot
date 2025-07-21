import discord
from discord import app_commands
from src.database import is_owner, init_owners, owners_cache

class PermissionChecker:
    def __init__(self):
        self.owners_cache = owners_cache
    
    async def check_approver(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return False
        
        if is_owner(interaction.user.id):
            return True
        
        init_owners()
        guild_id_str = str(interaction.guild_id)
        approver_role_id = self.owners_cache.get('approver_role_ids', {}).get(guild_id_str)
        
        if not approver_role_id:
            return False
        
        try:
            role = interaction.guild.get_role(int(approver_role_id))
            if role is None:
                return False
            return role in interaction.user.roles
        except ValueError:
            return False
    
    def requires_approver(self):
        async def predicate(interaction: discord.Interaction) -> bool:
            return is_owner(interaction.user.id) or await self.check_approver(interaction)
        return app_commands.check(predicate)

permission_checker = PermissionChecker()

async def check_approver(interaction: discord.Interaction):
    return await permission_checker.check_approver(interaction)

def requires_approver():
    return permission_checker.requires_approver()