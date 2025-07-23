import discord
import firebase_admin
from firebase_admin import credentials, firestore
import json
import os
import time
from typing import Optional, Dict, List, Any
from dotenv import load_dotenv
import asyncio
import threading

load_dotenv()

class FirebaseManager:
    def __init__(self):
        self._db = None
        self._default_owners = os.getenv('DEFAULT_OWNERS', '').split(',')
        self._owners = []
        self._initialized = False
        self._init_firebase()

    def _init_firebase(self):
        try:
            if not firebase_admin._apps:
                cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH', 'chiliili-firebase.json')
                
                if not os.path.exists(cred_path):
                    return
                
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
            
            self._db = firestore.client()
            self._initialized = True
            
        except Exception as e:
            self._initialized = False

    def _ensure_initialized(self):
        return self._initialized

    def load_owners(self):
        if not self._ensure_initialized():
            return self._default_owners
        
        try:
            owners_ref = self._db.collection('owners')
            docs = owners_ref.stream()
            
            owners = []
            for doc in docs:
                owners.append(doc.id)
            
            if not owners:
                for owner_id in self._default_owners:
                    if owner_id.strip():
                        self._add_owner(owner_id.strip())
                        owners.append(owner_id.strip())
            
            self._owners = owners
            return owners
            
        except Exception as e:
            return self._default_owners

    def _add_owner(self, user_id: str):
        try:
            self._db.collection('owners').document(user_id).set({
                'added_at': firestore.SERVER_TIMESTAMP
            })
        except Exception as e:
            pass

    def is_owner(self, user_id):
        if not self._owners:
            self.load_owners()
        return str(user_id) in self._owners

    def get_settings(self, guild_id):
        if not self._ensure_initialized():
            return (None, None, None, None, None)
        
        try:
            doc_ref = self._db.collection('guild_settings').document(str(guild_id))
            doc = doc_ref.get()
            
            if not doc.exists:
                return (None, None, None, None, None)
            
            settings = doc.to_dict()
            return (
                settings.get('form_channel_id'),
                settings.get('approv_channel_id'),
                settings.get('approver_role_id'),
                settings.get('approved_role_id'),
                settings.get('blacklist_report_channel_id')
            )
            
        except Exception as e:
            return (None, None, None, None, None)

    def save_settings(self, guild_id, form_channel_id=None, approv_channel_id=None,
                     approver_role_id=None, approved_role_id=None, blacklist_report_channel_id=None):
        if not self._ensure_initialized():
            return
        
        try:
            doc_ref = self._db.collection('guild_settings').document(str(guild_id))
            
            current_doc = doc_ref.get()
            current_settings = current_doc.to_dict() if current_doc.exists else {}
            
            update_data = {}
            if form_channel_id is not None:
                update_data['form_channel_id'] = str(form_channel_id)
            if approv_channel_id is not None:
                update_data['approv_channel_id'] = str(approv_channel_id)
            if approver_role_id is not None:
                update_data['approver_role_id'] = str(approver_role_id)
            if approved_role_id is not None:
                update_data['approved_role_id'] = str(approved_role_id)
            if blacklist_report_channel_id is not None:
                update_data['blacklist_report_channel_id'] = str(blacklist_report_channel_id)
            
            update_data['updated_at'] = firestore.SERVER_TIMESTAMP
            
            if not current_doc.exists:
                update_data['created_at'] = firestore.SERVER_TIMESTAMP
                doc_ref.set(update_data)
            else:
                doc_ref.update(update_data)
                
        except Exception as e:
            pass

    def get_all_settings(self):
        if not self._ensure_initialized():
            return {}
        
        try:
            settings_ref = self._db.collection('guild_settings')
            docs = settings_ref.stream()
            
            all_settings = {}
            for doc in docs:
                all_settings[doc.id] = doc.to_dict()
            
            return all_settings
            
        except Exception as e:
            return {}

    def save_application(self, guild_id, channel_id, message_id, applicant_id, embed_data):
        if not self._ensure_initialized():
            print(f"❌ Firebase не инициализирован для save_application")
            return
        
        try:
            doc_ref = self._db.collection('applications').document(f"{guild_id}_{message_id}")
            doc_ref.set({
                'guild_id': str(guild_id),
                'channel_id': str(channel_id),
                'message_id': str(message_id),
                'applicant_id': str(applicant_id),
                'embed_data': embed_data,
                'created_at': firestore.SERVER_TIMESTAMP
            })
            
            print(f"✅ Заявка сохранена: guild_id={guild_id}, applicant_id={applicant_id}, message_id={message_id}")
            
        except Exception as e:
            print(f"❌ Ошибка сохранения заявки: {e}")

    def remove_application(self, guild_id, message_id):
        if not self._ensure_initialized():
            print(f"❌ Firebase не инициализирован для remove_application")
            return
        
        try:
            doc_ref = self._db.collection('applications').document(f"{guild_id}_{message_id}")
            doc_ref.delete()
            
            print(f"✅ Заявка удалена: guild_id={guild_id}, message_id={message_id}")
            
        except Exception as e:
            print(f"❌ Ошибка удаления заявки: {e}")

    def get_guild_applications(self, guild_id):
        if not self._ensure_initialized():
            return {}
        
        try:
            applications_ref = self._db.collection('applications')
            query = applications_ref.where('guild_id', '==', str(guild_id))
            docs = query.stream()
            
            applications = {}
            for doc in docs:
                data = doc.to_dict()
                applications[data['message_id']] = {
                    'channel_id': data['channel_id'],
                    'applicant_id': data['applicant_id'],
                    'embed_data': data['embed_data']
                }
            
            return applications
            
        except Exception as e:
            print(f"❌ Ошибка в get_guild_applications: {e}")
            return {}

    def save_capt(self, guild_id, channel_id, message_id, max_members, current_members=None, timer_minutes=None):
        if not self._ensure_initialized():
            return
        
        try:
            doc_ref = self._db.collection('capts').document(f"{guild_id}_{message_id}")
            data = {
                'guild_id': str(guild_id),
                'channel_id': str(channel_id),
                'message_id': str(message_id),
                'max_members': max_members,
                'current_members': current_members or [],
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            
            if timer_minutes is not None:
                import time
                data['timer_minutes'] = timer_minutes
                data['expires_at'] = time.time() + (timer_minutes * 60)
            
            doc_ref.set(data)
            
        except Exception as e:
            pass

    def get_capt(self, guild_id, message_id):
        if not self._ensure_initialized():
            return None
        
        try:
            doc_ref = self._db.collection('capts').document(f"{guild_id}_{message_id}")
            doc = doc_ref.get()
            
            if not doc.exists:
                return None
            
            data = doc.to_dict()
            return {
                'channel_id': data['channel_id'],
                'max_members': data['max_members'],
                'current_members': data.get('current_members', []),
                'timer_minutes': data.get('timer_minutes'),
                'expires_at': data.get('expires_at')
            }
            
        except Exception as e:
            return None

    def add_member_to_capt(self, guild_id, message_id, member_id):
        if not self._ensure_initialized():
            return False
        
        try:
            doc_ref = self._db.collection('capts').document(f"{guild_id}_{message_id}")
            doc = doc_ref.get()
            
            if not doc.exists:
                return False
            
            data = doc.to_dict()
            current_members = data.get('current_members', [])
            
            if str(member_id) not in current_members:
                current_members.append(str(member_id))
                doc_ref.update({
                    'current_members': current_members,
                    'updated_at': firestore.SERVER_TIMESTAMP
                })
            
            return True
            
        except Exception as e:
            return False

    def remove_member_from_capt(self, guild_id, message_id, member_id):
        if not self._ensure_initialized():
            return False
        
        try:
            doc_ref = self._db.collection('capts').document(f"{guild_id}_{message_id}")
            doc = doc_ref.get()
            
            if not doc.exists:
                return False
            
            data = doc.to_dict()
            current_members = data.get('current_members', [])
            
            if str(member_id) in current_members:
                current_members.remove(str(member_id))
                doc_ref.update({
                    'current_members': current_members,
                    'updated_at': firestore.SERVER_TIMESTAMP
                })
            
            return True
            
        except Exception as e:
            return False

    def remove_capt(self, guild_id, message_id):
        if not self._ensure_initialized():
            return False
        
        try:
            doc_ref = self._db.collection('capts').document(f"{guild_id}_{message_id}")
            doc_ref.delete()
            return True
            
        except Exception as e:
            return False

    def add_to_blacklist(self, guild_id, user_id, reason, reporter_id, static_id=None):
        if not self._ensure_initialized():
            return False
        
        try:
            doc_ref = self._db.collection('blacklist').document(f"{guild_id}_{user_id}")
            doc_ref.set({
                'guild_id': str(guild_id),
                'user_id': str(user_id),
                'reason': reason,
                'reporter_id': str(reporter_id),
                'timestamp': str(int(time.time())),
                'static_id': static_id,
                'created_at': firestore.SERVER_TIMESTAMP
            })
            return True
            
        except Exception as e:
            return False

    def remove_from_blacklist(self, guild_id, user_id):
        if not self._ensure_initialized():
            return False
        
        try:
            doc_ref = self._db.collection('blacklist').document(f"{guild_id}_{user_id}")
            doc_ref.delete()
            return True
            
        except Exception as e:
            return False

    def is_blacklisted(self, guild_id, user_id):
        if not self._ensure_initialized():
            return False
        
        try:
            doc_ref = self._db.collection('blacklist').document(f"{guild_id}_{user_id}")
            doc = doc_ref.get()
            return doc.exists
            
        except Exception as e:
            return False

    def get_blacklist(self, guild_id):
        if not self._ensure_initialized():
            return {}
        
        try:
            blacklist_ref = self._db.collection('blacklist')
            query = blacklist_ref.where(filter=('guild_id', '==', str(guild_id)))
            docs = query.stream()
            
            blacklist = {}
            for doc in docs:
                data = doc.to_dict()
                blacklist[data['user_id']] = {
                    'reason': data['reason'],
                    'reporter_id': data['reporter_id'],
                    'timestamp': data['timestamp'],
                    'static_id': data.get('static_id')
                }
            
            return blacklist
            
        except Exception as e:
            return {}

    def get_blacklist_report_channel(self, guild_id):
        settings = self.get_settings(guild_id)
        return settings[4] if settings and len(settings) > 4 else None

    def has_pending_application(self, guild_id, applicant_id):
        """Проверяет, есть ли у пользователя активная заявка на сервере"""
        if not self._ensure_initialized():
            print(f"❌ Firebase не инициализирован для has_pending_application")
            return False
        
        try:
            applications_ref = self._db.collection('applications')
            # Используем правильный синтаксис для запроса
            query = applications_ref.where('guild_id', '==', str(guild_id)).where('applicant_id', '==', str(applicant_id))
            docs = list(query.stream())
            
            print(f"🔍 Проверка заявки: guild_id={guild_id}, applicant_id={applicant_id}, найдено документов: {len(docs)}")
            
            return len(docs) > 0
            
        except Exception as e:
            print(f"❌ Ошибка в has_pending_application: {e}")
            return False

    def has_pending_application_alternative(self, guild_id, applicant_id):
        """Альтернативная проверка заявок через get_guild_applications"""
        try:
            applications = self.get_guild_applications(guild_id)
            for message_id, app_data in applications.items():
                if app_data['applicant_id'] == str(applicant_id):
                    print(f"✅ Найдена активная заявка: message_id={message_id}, applicant_id={applicant_id}")
                    return True
            
            print(f"🔍 Активных заявок не найдено для applicant_id={applicant_id} на сервере {guild_id}")
            return False
            
        except Exception as e:
            print(f"❌ Ошибка в has_pending_application_alternative: {e}")
            return False

    async def has_pending_application_with_message_check(self, guild_id, applicant_id, bot):
        """Проверка заявок с дополнительной проверкой существования сообщения в чате"""
        try:
            applications = self.get_guild_applications(guild_id)
            
            for message_id, app_data in applications.items():
                if app_data['applicant_id'] == str(applicant_id):
                    # Проверяем, существует ли сообщение в чате
                    try:
                        guild = bot.get_guild(int(guild_id))
                        if guild:
                            channel = guild.get_channel(int(app_data['channel_id']))
                            if channel:
                                message = await channel.fetch_message(int(message_id))
                                # Проверяем, обработана ли заявка (есть ли поле "Рассмотрел заявку" в embed)
                                is_processed = False
                                if message.embeds:
                                    embed = message.embeds[0]
                                    for field in embed.fields:
                                        if "Рассмотрел заявку" in field.name:
                                            is_processed = True
                                            break
                                
                                if not is_processed:
                                    print(f"✅ Найдена активная заявка в чате: message_id={message_id}, applicant_id={applicant_id}")
                                    return True
                                else:
                                    print(f"⚠️ Заявка найдена, но уже обработана модератором: message_id={message_id}")
                            else:
                                print(f"⚠️ Канал не найден для заявки: channel_id={app_data['channel_id']}")
                        else:
                            print(f"⚠️ Сервер не найден: guild_id={guild_id}")
                    except discord.NotFound:
                        print(f"⚠️ Сообщение заявки не найдено в чате: message_id={message_id}")
                        # Сообщение удалено - заявка больше не активна
                        continue
                    except discord.Forbidden:
                        print(f"⚠️ Нет доступа к каналу: channel_id={app_data['channel_id']}")
                        # Не можем проверить - считаем заявку активной на всякий случай
                        return True
                    except Exception as e:
                        print(f"❌ Ошибка проверки сообщения {message_id}: {e}")
                        # В случае ошибки считаем заявку активной
                        return True
            
            print(f"🔍 Активных заявок не найдено для applicant_id={applicant_id} на сервере {guild_id}")
            return False
            
        except Exception as e:
            print(f"❌ Ошибка в has_pending_application_with_message_check: {e}")
            return False

    def save_role_permissions(self, guild_id, role_id, permissions):
        """Сохраняет разрешения для роли"""
        if not self._ensure_initialized():
            print(f"❌ Firebase не инициализирован для save_role_permissions")
            return False
        
        try:
            doc_ref = self._db.collection('role_permissions').document(f"{guild_id}_{role_id}")
            doc_ref.set({
                'guild_id': str(guild_id),
                'role_id': str(role_id),
                'permissions': permissions,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            return True
            
        except Exception as e:
            print(f"❌ Ошибка при сохранении разрешений: {e}")
            return False

    def get_role_permissions(self, guild_id, role_id):
        """Получает разрешения для роли"""
        if not self._ensure_initialized():
            print(f"❌ Firebase не инициализирован для get_role_permissions")
            return []
        
        try:
            doc_ref = self._db.collection('role_permissions').document(f"{guild_id}_{role_id}")
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                permissions = data.get('permissions', [])
                return permissions
            else:
                return []
            
        except Exception as e:
            print(f"❌ Ошибка при загрузке разрешений: {e}")
            return []

    def get_all_role_permissions(self, guild_id):
        """Получает все разрешения ролей для сервера"""
        if not self._ensure_initialized():
            return {}
        
        try:
            permissions_ref = self._db.collection('role_permissions')
            query = permissions_ref.where(filter=('guild_id', '==', str(guild_id)))
            docs = query.stream()
            
            result = {}
            for doc in docs:
                data = doc.to_dict()
                result[data['role_id']] = data.get('permissions', [])
            
            return result
            
        except Exception as e:
            return {}

    def remove_role_permissions(self, guild_id, role_id):
        """Удаляет разрешения для роли"""
        if not self._ensure_initialized():
            return False
        
        try:
            doc_ref = self._db.collection('role_permissions').document(f"{guild_id}_{role_id}")
            doc_ref.delete()
            return True
            
        except Exception as e:
            return False

    @property
    def settings(self):
        try:
            return self.get_all_settings()
        except Exception as e:
            return {}

    @property
    def applications(self):
        if not self._ensure_initialized():
            return {}
        
        try:
            applications_ref = self._db.collection('applications')
            docs = applications_ref.stream()
            
            result = {}
            for doc in docs:
                data = doc.to_dict()
                guild_id = data['guild_id']
                message_id = data['message_id']
                
                if guild_id not in result:
                    result[guild_id] = {}
                
                result[guild_id][message_id] = {
                    'channel_id': data['channel_id'],
                    'applicant_id': data['applicant_id'],
                    'embed_data': data['embed_data']
                }
            
            return result
            
        except Exception as e:
            return {}

    @property
    def owner_data(self):
        if not self._ensure_initialized():
            return {
                'owners': self._default_owners,
                'approver_role_ids': {}
            }
        
        try:
            owners = self.load_owners()
            settings = self.get_all_settings()
            
            approver_roles = {}
            if settings:
                for guild_id, guild_settings in settings.items():
                    if isinstance(guild_settings, dict) and guild_settings.get('approver_role_id'):
                        approver_roles[guild_id] = guild_settings['approver_role_id']
            
            return {
                'owners': owners,
                'approver_role_ids': approver_roles
            }
            
        except Exception as e:
            return {
                'owners': self._default_owners,
                'approver_role_ids': {}
            }

    @property
    def owner_list(self):
        return self._owners

    def sync_approver_role(self):
        pass


class CacheManager:
    def __init__(self, firebase_manager: FirebaseManager):
        self._firebase_manager = firebase_manager
        self._settings_cache = None
        self._applications_cache = None
        self._owners_cache = None
        self._owners_list = None

    def clear_cache(self):
        self._settings_cache = None
        self._applications_cache = None
        self._owners_cache = None
        self._owners_list = None

    def get_settings_cache(self):
        if self._settings_cache is None:
            self._settings_cache = self._firebase_manager.settings
        return self._settings_cache

    def get_applications_cache(self):
        if self._applications_cache is None:
            self._applications_cache = self._firebase_manager.applications
        return self._applications_cache

    def get_owners_cache(self):
        if self._owners_cache is None:
            self._owners_cache = self._firebase_manager.owner_data
        return self._owners_cache

    def get_owners_list(self):
        if self._owners_list is None:
            self._owners_list = self._firebase_manager.owner_list
        return self._owners_list

    def refresh_owners_cache(self):
        self._owners_cache = None
        self._owners_list = None
        self._firebase_manager.load_owners()


firebase_db = FirebaseManager()
cache_manager = CacheManager(firebase_db)

def clear_cache():
    cache_manager.clear_cache()

def get_settings_cache():
    return cache_manager.get_settings_cache()

def get_applications_cache():
    return cache_manager.get_applications_cache()

def get_owners_cache():
    return cache_manager.get_owners_cache()

def get_owners_list():
    return cache_manager.get_owners_list()

def settings_cache():
    return get_settings_cache()

def applications_cache():
    return get_applications_cache()

def owners_cache():
    return get_owners_cache()

def OWNERS():
    return get_owners_list()

def init_owners():
    result = firebase_db.load_owners()
    cache_manager._owners_cache = None
    cache_manager._owners_list = None
    return result

def load_owners():
    return firebase_db.load_owners()

def refresh_owners_cache():
    cache_manager.refresh_owners_cache()

def is_owner(user_id):
    return firebase_db.is_owner(user_id)

def sync_approver_role():
    return firebase_db.sync_approver_role()

def init_settings():
    return firebase_db.get_all_settings()

def get_settings(guild_id):
    return firebase_db.get_settings(guild_id)

def save_settings(guild_id, form_channel_id=None, approv_channel_id=None,
                 approver_role_id=None, approved_role_id=None, blacklist_report_channel_id=None):
    result = firebase_db.save_settings(guild_id, form_channel_id, approv_channel_id,
                                      approver_role_id, approved_role_id, blacklist_report_channel_id)
    
    if approver_role_id is not None:
        refresh_owners_cache()
    
    return result

def init_applications():
    return firebase_db.applications

def save_application(guild_id, channel_id, message_id, applicant_id, embed_data):
    return firebase_db.save_application(guild_id, channel_id, message_id, applicant_id, embed_data)

def remove_application(guild_id, message_id):
    return firebase_db.remove_application(guild_id, message_id)

def get_all_settings():
    return firebase_db.get_all_settings()

def save_capt(guild_id, channel_id, message_id, max_members, current_members=None, timer_minutes=None):
    return firebase_db.save_capt(guild_id, channel_id, message_id, max_members, current_members, timer_minutes)

def get_capt(guild_id, message_id):
    return firebase_db.get_capt(guild_id, message_id)

def add_member_to_capt(guild_id, message_id, member_id):
    return firebase_db.add_member_to_capt(guild_id, message_id, member_id)

def remove_capt(guild_id, message_id):
    return firebase_db.remove_capt(guild_id, message_id)

def remove_member_from_capt(guild_id, message_id, member_id):
    return firebase_db.remove_member_from_capt(guild_id, message_id, member_id)

def add_to_blacklist(guild_id, user_id, reason, reporter_id, static_id=None):
    return firebase_db.add_to_blacklist(guild_id, user_id, reason, reporter_id, static_id)

def remove_from_blacklist(guild_id, user_id):
    return firebase_db.remove_from_blacklist(guild_id, user_id)

def is_blacklisted(guild_id, user_id):
    return firebase_db.is_blacklisted(guild_id, user_id)

def get_blacklist(guild_id):
    return firebase_db.get_blacklist(guild_id)

def get_blacklist_report_channel(guild_id):
    return firebase_db.get_blacklist_report_channel(guild_id)

def has_pending_application(guild_id, applicant_id):
    try:
        result = firebase_db.has_pending_application(guild_id, applicant_id)
        if result:
            return True
    except Exception as e:
        print(f"❌ Основной метод проверки заявок не сработал: {e}")
    
    try:
        return firebase_db.has_pending_application_alternative(guild_id, applicant_id)
    except Exception as e:
        print(f"❌ Альтернативный метод проверки заявок не сработал: {e}")
        return False

async def has_pending_application_with_bot(guild_id, applicant_id, bot):
    return await firebase_db.has_pending_application_with_message_check(guild_id, applicant_id, bot)

def save_role_permissions(guild_id, role_id, permissions):
    return firebase_db.save_role_permissions(guild_id, role_id, permissions)

def get_role_permissions(guild_id, role_id):
    return firebase_db.get_role_permissions(guild_id, role_id)

def get_all_role_permissions(guild_id):
    return firebase_db.get_all_role_permissions(guild_id)

def remove_role_permissions(guild_id, role_id):
    return firebase_db.remove_role_permissions(guild_id, role_id)