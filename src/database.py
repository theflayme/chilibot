import json
import os
from dotenv import load_dotenv

load_dotenv()

class DatabaseManager:
    def __init__(self):
        self.settings_file = os.getenv('SETTINGS_FILE')
        self.applications_file = os.getenv('APPLICATIONS_FILE')
        self.owners_file = os.getenv('OWNERS_FILE')
        self.default_owners = os.getenv('DEFAULT_OWNERS').split(',')
        
        self.settings_cache = {}
        self.applications_cache = {}
        self.owners_cache = {}
        self.owners = []
        self.capts_cache = {}
    
    def _read_json_file(self, file_path):
        if not os.path.exists(file_path):
            return None
        try:
            with open(file_path, 'r') as f:
                content = f.read().strip()
                if not content:
                    return {}
                return json.loads(content)
        except (json.JSONDecodeError, PermissionError) as e:
            print(f"Ошибка при загрузке файла {file_path}: {e}")
            return {}
    
    def _write_json_file(self, file_path, data):
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            pass
    
    def init_owners(self):
        data = self._read_json_file(self.owners_file)
        if data is None:
            self.owners_cache = {
                'owners': self.default_owners,
                'approver_role_ids': {}
            }
            self._write_json_file(self.owners_file, self.owners_cache)
            self.owners = self.owners_cache.get('owners', [])
            return
        
        self.owners_cache = data
        if 'approver_role_ids' not in self.owners_cache:
            self.owners_cache['approver_role_ids'] = {}
        
        if isinstance(self.owners_cache.get('owners'), str):
            self.owners_cache['owners'] = [self.owners_cache['owners']]
        elif not isinstance(self.owners_cache.get('owners'), list):
            self.owners_cache['owners'] = self.default_owners
        
        self.owners = self.owners_cache.get('owners', self.default_owners)
        
        if data == {}:
            self.owners_cache = {
                'owners': self.default_owners,
                'approver_role_ids': {}
            }
            self.owners = self.owners_cache.get('owners', self.default_owners)
            self._write_json_file(self.owners_file, self.owners_cache)
    
    def load_owners(self):
        self.init_owners()
        return self.owners
    
    def is_owner(self, user_id):
        user_id_str = str(user_id)
        return user_id_str in self.owners
    
    def sync_approver_role(self):
        self.init_settings()
        self.init_owners()
        updated = False
        for guild_id in self.settings_cache:
            approver_role_id = self.settings_cache[guild_id].get('approver_role_id')
            if approver_role_id and self.owners_cache['approver_role_ids'].get(guild_id) != str(approver_role_id):
                self.owners_cache['approver_role_ids'][guild_id] = str(approver_role_id)
                updated = True
        if updated:
            self._write_json_file(self.owners_file, self.owners_cache)
    
    def init_settings(self):
        data = self._read_json_file(self.settings_file)
        if data is None:
            self.settings_cache = {}
            self._write_json_file(self.settings_file, self.settings_cache)
            return
        self.settings_cache = data
    
    def get_settings(self, guild_id):
        self.init_settings()
        guild_data = self.settings_cache.get(str(guild_id), {})
        return (
            guild_data.get('form_channel_id'),
            guild_data.get('approv_channel_id'),
            guild_data.get('approver_role_id'),
            guild_data.get('approved_role_id')
        )
    
    def save_settings(self, guild_id, form_channel_id=None, approv_channel_id=None, approver_role_id=None, approved_role_id=None):
        self.init_settings()
        guild_id_str = str(guild_id)
        if guild_id_str not in self.settings_cache:
            self.settings_cache[guild_id_str] = {}
        if form_channel_id is not None:
            self.settings_cache[guild_id_str]['form_channel_id'] = str(form_channel_id)
        if approv_channel_id is not None:
            self.settings_cache[guild_id_str]['approv_channel_id'] = str(approv_channel_id)
        if approver_role_id is not None:
            self.settings_cache[guild_id_str]['approver_role_id'] = str(approver_role_id)
        if approved_role_id is not None:
            self.settings_cache[guild_id_str]['approved_role_id'] = str(approved_role_id)
        
        self._write_json_file(self.settings_file, self.settings_cache)
        self.sync_approver_role()
    
    def init_applications(self):
        data = self._read_json_file(self.applications_file)
        if data is None:
            self.applications_cache = {}
            self._write_json_file(self.applications_file, self.applications_cache)
            return
        self.applications_cache = data
    
    def save_application(self, guild_id, channel_id, message_id, applicant_id, embed_data):
        self.init_applications()
        guild_id_str = str(guild_id)
        message_id_str = str(message_id)
        if guild_id_str not in self.applications_cache:
            self.applications_cache[guild_id_str] = {}
        self.applications_cache[guild_id_str][message_id_str] = {
            'channel_id': str(channel_id),
            'applicant_id': str(applicant_id),
            'embed_data': embed_data
        }
        self._write_json_file(self.applications_file, self.applications_cache)
    
    def remove_application(self, guild_id, message_id):
        self.init_applications()
        guild_id_str = str(guild_id)
        message_id_str = str(message_id)
        if guild_id_str in self.applications_cache and message_id_str in self.applications_cache[guild_id_str]:
            del self.applications_cache[guild_id_str][message_id_str]
            if not self.applications_cache[guild_id_str]:
                del self.applications_cache[guild_id_str]
            self._write_json_file(self.applications_file, self.applications_cache)
    
    def get_all_settings(self):
        self.init_settings()
        return self.settings_cache

    def save_capt(self, guild_id, channel_id, message_id, max_members, current_members=None):
        """Сохраняет информацию о капте"""
        self.init_settings()
        guild_id_str = str(guild_id)
        if 'capts' not in self.settings_cache:
            self.settings_cache['capts'] = {}
        if guild_id_str not in self.settings_cache['capts']:
            self.settings_cache['capts'][guild_id_str] = {}
        
        self.settings_cache['capts'][guild_id_str][str(message_id)] = {
            'channel_id': str(channel_id),
            'max_members': max_members,
            'current_members': current_members or []
        }
        self._write_json_file(self.settings_file, self.settings_cache)

    def get_capt(self, guild_id, message_id):
        """Получает информацию о капте"""
        self.init_settings()
        guild_id_str = str(guild_id)
        if 'capts' not in self.settings_cache or \
           guild_id_str not in self.settings_cache['capts'] or \
           str(message_id) not in self.settings_cache['capts'][guild_id_str]:
            return None
        return self.settings_cache['capts'][guild_id_str][str(message_id)]

    def add_member_to_capt(self, guild_id, message_id, member_id):
        """Добавляет участника в капт"""
        self.init_settings()
        capt = self.get_capt(guild_id, message_id)
        if not capt:
            return False
        
        if str(member_id) in capt['current_members']:
            return False
            
        capt['current_members'].append(str(member_id))
        self._write_json_file(self.settings_file, self.settings_cache)
        return True

    def remove_capt(self, guild_id, message_id):
        """Удаляет капт"""
        self.init_settings()
        guild_id_str = str(guild_id)
        if 'capts' in self.settings_cache and \
           guild_id_str in self.settings_cache['capts'] and \
           str(message_id) in self.settings_cache['capts'][guild_id_str]:
            del self.settings_cache['capts'][guild_id_str][str(message_id)]
            if not self.settings_cache['capts'][guild_id_str]:
                del self.settings_cache['capts'][guild_id_str]
            self._write_json_file(self.settings_file, self.settings_cache)
            return True
        return False

    def remove_member_from_capt(self, guild_id, message_id, member_id):
        """Удаляет участника из капта"""
        self.init_settings()
        capt = self.get_capt(guild_id, message_id)
        if not capt:
            return False
        
        member_id_str = str(member_id)
        if member_id_str not in capt['current_members']:
            return False
            
        capt['current_members'].remove(member_id_str)
        self._write_json_file(self.settings_file, self.settings_cache)
        return True

db = DatabaseManager()

settings_cache = db.settings_cache
applications_cache = db.applications_cache
owners_cache = db.owners_cache
OWNERS = db.owners

def init_owners():
    return db.init_owners()

def load_owners():
    return db.load_owners()

def is_owner(user_id):
    return db.is_owner(user_id)

def sync_approver_role():
    return db.sync_approver_role()

def init_settings():
    return db.init_settings()

def get_settings(guild_id):
    return db.get_settings(guild_id)

def save_settings(guild_id, form_channel_id=None, approv_channel_id=None, approver_role_id=None, approved_role_id=None):
    return db.save_settings(guild_id, form_channel_id, approv_channel_id, approver_role_id, approved_role_id)

def init_applications():
    return db.init_applications()

def save_application(guild_id, channel_id, message_id, applicant_id, embed_data):
    return db.save_application(guild_id, channel_id, message_id, applicant_id, embed_data)

def remove_application(guild_id, message_id):
    return db.remove_application(guild_id, message_id)

def get_all_settings():
    return db.get_all_settings()

def save_capt(guild_id, channel_id, message_id, max_members, current_members=None):
    return db.save_capt(guild_id, channel_id, message_id, max_members, current_members)

def get_capt(guild_id, message_id):
    return db.get_capt(guild_id, message_id)

def add_member_to_capt(guild_id, message_id, member_id):
    return db.add_member_to_capt(guild_id, message_id, member_id)

def remove_capt(guild_id, message_id):
    return db.remove_capt(guild_id, message_id)

def remove_member_from_capt(guild_id, message_id, member_id):
    return db.remove_member_from_capt(guild_id, message_id, member_id)