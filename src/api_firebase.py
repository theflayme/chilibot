from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import firebase_admin
from firebase_admin import credentials, firestore
import json
import os

class GuildSettings(BaseModel):
    form_channel_id: Optional[str] = None
    approv_channel_id: Optional[str] = None
    approver_role_id: Optional[str] = None
    approved_role_id: Optional[str] = None
    blacklist_report_channel_id: Optional[str] = None

class Application(BaseModel):
    channel_id: str
    applicant_id: str
    embed_data: Dict[str, Any]

class Capt(BaseModel):
    channel_id: str
    max_members: int
    current_members: List[str] = []

class BlacklistEntry(BaseModel):
    reason: str
    reporter_id: str
    timestamp: str
    static_id: Optional[str] = None

class FirebaseManager:
    def __init__(self):
        self._db = None
        self._initialize_firebase()
    
    def _initialize_firebase(self):
        if not firebase_admin._apps:
            cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH', 'chiliili-firebase.json')
            if os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
        self._db = firestore.client()
    
    @property
    def db(self):
        return self._db

class BaseRepository:
    def __init__(self, firebase_manager: FirebaseManager):
        self._firebase_manager = firebase_manager
    
    @property
    def db(self):
        return self._firebase_manager.db

class GuildSettingsRepository(BaseRepository):
    def __init__(self, firebase_manager: FirebaseManager):
        super().__init__(firebase_manager)
        self._collection_name = 'guild_settings'
    
    def get_settings(self, guild_id: str) -> Dict[str, Any]:
        doc_ref = self.db.collection(self._collection_name).document(guild_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return {}
        
        settings = doc.to_dict()
        settings.pop('created_at', None)
        settings.pop('updated_at', None)
        return settings
    
    def update_settings(self, guild_id: str, settings: GuildSettings) -> Dict[str, str]:
        doc_ref = self.db.collection(self._collection_name).document(guild_id)
        current_doc = doc_ref.get()
        
        update_data = {}
        if settings.form_channel_id is not None:
            update_data['form_channel_id'] = settings.form_channel_id
        if settings.approv_channel_id is not None:
            update_data['approv_channel_id'] = settings.approv_channel_id
        if settings.approver_role_id is not None:
            update_data['approver_role_id'] = settings.approver_role_id
        if settings.approved_role_id is not None:
            update_data['approved_role_id'] = settings.approved_role_id
        if settings.blacklist_report_channel_id is not None:
            update_data['blacklist_report_channel_id'] = settings.blacklist_report_channel_id
        
        update_data['updated_at'] = firestore.SERVER_TIMESTAMP
        
        if not current_doc.exists:
            update_data['created_at'] = firestore.SERVER_TIMESTAMP
            doc_ref.set(update_data)
        else:
            doc_ref.update(update_data)
        
        return {"status": "success"}
    
    def get_all_settings(self) -> Dict[str, Any]:
        settings_ref = self.db.collection(self._collection_name)
        docs = settings_ref.stream()
        
        all_settings = {}
        for doc in docs:
            settings = doc.to_dict()
            settings.pop('created_at', None)
            settings.pop('updated_at', None)
            all_settings[doc.id] = settings
        
        return all_settings

class ApplicationsRepository(BaseRepository):
    def __init__(self, firebase_manager: FirebaseManager):
        super().__init__(firebase_manager)
        self._collection_name = 'applications'
    
    def get_guild_applications(self, guild_id: str) -> Dict[str, Any]:
        applications_ref = self.db.collection(self._collection_name)
        query = applications_ref.where('guild_id', '==', guild_id)
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
    
    def create_application(self, guild_id: str, message_id: str, application: Application) -> Dict[str, str]:
        doc_ref = self.db.collection(self._collection_name).document(f"{guild_id}_{message_id}")
        doc_ref.set({
            'guild_id': guild_id,
            'message_id': message_id,
            'channel_id': application.channel_id,
            'applicant_id': application.applicant_id,
            'embed_data': application.embed_data,
            'created_at': firestore.SERVER_TIMESTAMP
        })
        
        return {"status": "success"}
    
    def delete_application(self, guild_id: str, message_id: str) -> Dict[str, str]:
        doc_ref = self.db.collection(self._collection_name).document(f"{guild_id}_{message_id}")
        doc_ref.delete()
        
        return {"status": "success"}

class CaptsRepository(BaseRepository):
    def __init__(self, firebase_manager: FirebaseManager):
        super().__init__(firebase_manager)
        self._collection_name = 'capts'
    
    def get_capt(self, guild_id: str, message_id: str) -> Dict[str, Any]:
        doc_ref = self.db.collection(self._collection_name).document(f"{guild_id}_{message_id}")
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Capt not found")
        
        data = doc.to_dict()
        return {
            'channel_id': data['channel_id'],
            'max_members': data['max_members'],
            'current_members': data.get('current_members', [])
        }
    
    def create_capt(self, guild_id: str, message_id: str, capt: Capt) -> Dict[str, str]:
        doc_ref = self.db.collection(self._collection_name).document(f"{guild_id}_{message_id}")
        doc_ref.set({
            'guild_id': guild_id,
            'message_id': message_id,
            'channel_id': capt.channel_id,
            'max_members': capt.max_members,
            'current_members': capt.current_members,
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP
        })
        
        return {"status": "success"}
    
    def delete_capt(self, guild_id: str, message_id: str) -> Dict[str, str]:
        doc_ref = self.db.collection(self._collection_name).document(f"{guild_id}_{message_id}")
        doc_ref.delete()
        
        return {"status": "success"}
    
    def add_member(self, guild_id: str, message_id: str, member_id: str) -> Dict[str, str]:
        doc_ref = self.db.collection(self._collection_name).document(f"{guild_id}_{message_id}")
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Capt not found")
        
        data = doc.to_dict()
        current_members = data.get('current_members', [])
        
        if member_id not in current_members:
            current_members.append(member_id)
            doc_ref.update({
                'current_members': current_members,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
        
        return {"status": "success"}
    
    def remove_member(self, guild_id: str, message_id: str, member_id: str) -> Dict[str, str]:
        doc_ref = self.db.collection(self._collection_name).document(f"{guild_id}_{message_id}")
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Capt not found")
        
        data = doc.to_dict()
        current_members = data.get('current_members', [])
        
        if member_id in current_members:
            current_members.remove(member_id)
            doc_ref.update({
                'current_members': current_members,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
        
        return {"status": "success"}

class BlacklistRepository(BaseRepository):
    def __init__(self, firebase_manager: FirebaseManager):
        super().__init__(firebase_manager)
        self._collection_name = 'blacklist'
    
    def get_guild_blacklist(self, guild_id: str) -> Dict[str, Any]:
        blacklist_ref = self.db.collection(self._collection_name)
        query = blacklist_ref.where('guild_id', '==', guild_id)
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
    
    def add_to_blacklist(self, guild_id: str, user_id: str, entry: BlacklistEntry) -> Dict[str, str]:
        doc_ref = self.db.collection(self._collection_name).document(f"{guild_id}_{user_id}")
        doc_ref.set({
            'guild_id': guild_id,
            'user_id': user_id,
            'reason': entry.reason,
            'reporter_id': entry.reporter_id,
            'timestamp': entry.timestamp,
            'static_id': entry.static_id,
            'created_at': firestore.SERVER_TIMESTAMP
        })
        
        return {"status": "success"}
    
    def remove_from_blacklist(self, guild_id: str, user_id: str) -> Dict[str, str]:
        doc_ref = self.db.collection(self._collection_name).document(f"{guild_id}_{user_id}")
        doc_ref.delete()
        
        return {"status": "success"}

class OwnersRepository(BaseRepository):
    def __init__(self, firebase_manager: FirebaseManager):
        super().__init__(firebase_manager)
        self._collection_name = 'owners'
    
    def get_owners(self) -> Dict[str, List[str]]:
        owners_ref = self.db.collection(self._collection_name)
        docs = owners_ref.stream()
        
        owners = []
        for doc in docs:
            owners.append(doc.id)
        
        return {"owners": owners}
    
    def add_owner(self, user_id: str) -> Dict[str, str]:
        doc_ref = self.db.collection(self._collection_name).document(user_id)
        doc = doc_ref.get()
        
        if doc.exists:
            raise HTTPException(status_code=400, detail="Owner already exists")
        
        doc_ref.set({
            'added_at': firestore.SERVER_TIMESTAMP
        })
        
        return {"status": "success"}
    
    def remove_owner(self, user_id: str) -> Dict[str, str]:
        doc_ref = self.db.collection(self._collection_name).document(user_id)
        doc_ref.delete()
        
        return {"status": "success"}

class APIService:
    def __init__(self):
        self._firebase_manager = FirebaseManager()
        self._guild_settings_repo = GuildSettingsRepository(self._firebase_manager)
        self._applications_repo = ApplicationsRepository(self._firebase_manager)
        self._capts_repo = CaptsRepository(self._firebase_manager)
        self._blacklist_repo = BlacklistRepository(self._firebase_manager)
        self._owners_repo = OwnersRepository(self._firebase_manager)
    
    @property
    def guild_settings(self):
        return self._guild_settings_repo
    
    @property
    def applications(self):
        return self._applications_repo
    
    @property
    def capts(self):
        return self._capts_repo
    
    @property
    def blacklist(self):
        return self._blacklist_repo
    
    @property
    def owners(self):
        return self._owners_repo

class DiscordBotAPI:
    def __init__(self):
        self._app = FastAPI(title="Discord Bot Firebase API", description="API для работы с Firebase Firestore")
        self._service = APIService()
        self._setup_middleware()
        self._setup_routes()
    
    def _setup_middleware(self):
        self._app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def _setup_routes(self):
        @self._app.get("/")
        async def root():
            return {"message": "Discord Bot Firebase API is running"}

        @self._app.get("/guilds/{guild_id}/settings")
        async def get_guild_settings(guild_id: str):
            try:
                return self._service.guild_settings.get_settings(guild_id)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Ошибка получения настроек: {str(e)}")

        @self._app.put("/guilds/{guild_id}/settings")
        async def update_guild_settings(guild_id: str, settings: GuildSettings):
            try:
                return self._service.guild_settings.update_settings(guild_id, settings)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Ошибка обновления настроек: {str(e)}")

        @self._app.get("/guilds")
        async def get_all_guilds():
            try:
                return self._service.guild_settings.get_all_settings()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Ошибка получения настроек: {str(e)}")

        @self._app.get("/guilds/{guild_id}/applications")
        async def get_guild_applications(guild_id: str):
            try:
                return self._service.applications.get_guild_applications(guild_id)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Ошибка получения заявок: {str(e)}")

        @self._app.post("/guilds/{guild_id}/applications/{message_id}")
        async def create_application(guild_id: str, message_id: str, application: Application):
            try:
                return self._service.applications.create_application(guild_id, message_id, application)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Ошибка создания заявки: {str(e)}")

        @self._app.delete("/guilds/{guild_id}/applications/{message_id}")
        async def delete_application(guild_id: str, message_id: str):
            try:
                return self._service.applications.delete_application(guild_id, message_id)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Ошибка удаления заявки: {str(e)}")

        @self._app.get("/guilds/{guild_id}/capts/{message_id}")
        async def get_capt(guild_id: str, message_id: str):
            try:
                return self._service.capts.get_capt(guild_id, message_id)
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Ошибка получения капты: {str(e)}")

        @self._app.post("/guilds/{guild_id}/capts/{message_id}")
        async def create_capt(guild_id: str, message_id: str, capt: Capt):
            try:
                return self._service.capts.create_capt(guild_id, message_id, capt)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Ошибка создания капты: {str(e)}")

        @self._app.delete("/guilds/{guild_id}/capts/{message_id}")
        async def delete_capt(guild_id: str, message_id: str):
            try:
                return self._service.capts.delete_capt(guild_id, message_id)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Ошибка удаления капты: {str(e)}")

        @self._app.post("/guilds/{guild_id}/capts/{message_id}/members/{member_id}")
        async def add_member_to_capt(guild_id: str, message_id: str, member_id: str):
            try:
                return self._service.capts.add_member(guild_id, message_id, member_id)
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Ошибка добавления участника: {str(e)}")

        @self._app.delete("/guilds/{guild_id}/capts/{message_id}/members/{member_id}")
        async def remove_member_from_capt(guild_id: str, message_id: str, member_id: str):
            try:
                return self._service.capts.remove_member(guild_id, message_id, member_id)
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Ошибка удаления участника: {str(e)}")

        @self._app.get("/guilds/{guild_id}/blacklist")
        async def get_guild_blacklist(guild_id: str):
            try:
                return self._service.blacklist.get_guild_blacklist(guild_id)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Ошибка получения черного списка: {str(e)}")

        @self._app.post("/guilds/{guild_id}/blacklist/{user_id}")
        async def add_to_blacklist(guild_id: str, user_id: str, entry: BlacklistEntry):
            try:
                return self._service.blacklist.add_to_blacklist(guild_id, user_id, entry)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Ошибка добавления в черный список: {str(e)}")

        @self._app.delete("/guilds/{guild_id}/blacklist/{user_id}")
        async def remove_from_blacklist(guild_id: str, user_id: str):
            try:
                return self._service.blacklist.remove_from_blacklist(guild_id, user_id)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Ошибка удаления из черного списка: {str(e)}")

        @self._app.get("/owners")
        async def get_owners():
            try:
                return self._service.owners.get_owners()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Ошибка получения владельцев: {str(e)}")

        @self._app.post("/owners/{user_id}")
        async def add_owner(user_id: str):
            try:
                return self._service.owners.add_owner(user_id)
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Ошибка добавления владельца: {str(e)}")

        @self._app.delete("/owners/{user_id}")
        async def remove_owner(user_id: str):
            try:
                return self._service.owners.remove_owner(user_id)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Ошибка удаления владельца: {str(e)}")
    
    @property
    def app(self):
        return self._app

bot_api = DiscordBotAPI()
app = bot_api.app