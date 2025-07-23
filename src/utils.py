import asyncio
import time
import os
from dotenv import load_dotenv
from src.database_firebase import applications_cache, remove_application

load_dotenv()


class ApplicationState:
    def __init__(self, user_id: int, timestamp: float):
        self._user_id = user_id
        self._timestamp = timestamp
    
    @property
    def user_id(self) -> int:
        return self._user_id
    
    @property
    def timestamp(self) -> float:
        return self._timestamp
    
    def is_expired(self, timeout: int) -> bool:
        return time.time() - self._timestamp > timeout


class StateStorage:
    def __init__(self):
        self._states = {}
    
    def add(self, message_id: int, state: ApplicationState) -> None:
        self._states[message_id] = state
    
    def remove(self, message_id: int) -> ApplicationState:
        return self._states.pop(message_id, None)
    
    def get(self, message_id: int) -> ApplicationState:
        return self._states.get(message_id)
    
    def get_all_items(self):
        return list(self._states.items())
    
    def pop(self, message_id: int) -> ApplicationState:
        return self._states.pop(message_id, None)


class StateCleanupService:
    def __init__(self, storage: StateStorage, timeout: int):
        self._storage = storage
        self._timeout = timeout
    
    def get_expired_states(self):
        expired_states = []
        for message_id, state in self._storage.get_all_items():
            if state.is_expired(self._timeout):
                expired_states.append(message_id)
        return expired_states
    
    def remove_expired_states(self):
        expired_message_ids = self.get_expired_states()
        for message_id in expired_message_ids:
            self._storage.pop(message_id)
            self._remove_from_applications_cache(message_id)
    
    def _remove_from_applications_cache(self, message_id: int):
        guild_id = self._find_guild_id_for_message(message_id)
        if guild_id:
            remove_application(guild_id, message_id)
    
    def _find_guild_id_for_message(self, message_id: int):
        cache = applications_cache()
        if cache and hasattr(cache, 'items'):
            return next((gid for gid, apps in cache.items() if message_id in apps), None)
        return None


class ApplicationStateManager:
    def __init__(self):
        self._timeout = int(os.getenv('APPLICATION_STATE_TIMEOUT', 3600))
        self._clear_interval = int(os.getenv('CLEAR_OLD_STATES_INTERVAL', 60))
        self._storage = StateStorage()
        self._cleanup_service = StateCleanupService(self._storage, self._timeout)
    
    def add_state(self, message_id: int, user_id: int) -> None:
        state = ApplicationState(user_id, time.time())
        self._storage.add(message_id, state)
    
    def remove_state(self, message_id: int) -> ApplicationState:
        return self._storage.remove(message_id)
    
    def get_state(self, message_id: int) -> ApplicationState:
        return self._storage.get(message_id)
    
    async def clear_old_states(self) -> None:
        while True:
            await asyncio.sleep(self._clear_interval)
            self._cleanup_service.remove_expired_states()


class ApplicationStateService:
    def __init__(self):
        self._manager = ApplicationStateManager()
    
    def add_state(self, message_id: int, user_id: int) -> None:
        self._manager.add_state(message_id, user_id)
    
    def remove_state(self, message_id: int) -> ApplicationState:
        return self._manager.remove_state(message_id)
    
    def get_state(self, message_id: int) -> ApplicationState:
        return self._manager.get_state(message_id)
    
    async def start_cleanup_task(self) -> None:
        await self._manager.clear_old_states()


_application_state_service = ApplicationStateService()


def get_application_state_service() -> ApplicationStateService:
    return _application_state_service


async def clear_old_states() -> None:
    await _application_state_service.start_cleanup_task()