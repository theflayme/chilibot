import asyncio
import time
import os
from dotenv import load_dotenv
from src.database import applications_cache, remove_application

load_dotenv()

class ApplicationStateManager:
    def __init__(self):
        self.application_states = {}
        self.timeout = int(os.getenv('APPLICATION_STATE_TIMEOUT', 3600))
        self.clear_interval = int(os.getenv('CLEAR_OLD_STATES_INTERVAL', 60))
    
    def add_state(self, message_id, user_id):
        self.application_states[message_id] = (user_id, time.time())
    
    def remove_state(self, message_id):
        return self.application_states.pop(message_id, None)
    
    def get_state(self, message_id):
        return self.application_states.get(message_id)
    
    async def clear_old_states(self):
        while True:
            await asyncio.sleep(self.clear_interval)
            current_time = time.time()
            to_remove = []
            for message_id, (user_id, timestamp) in list(self.application_states.items()):
                if current_time - timestamp > self.timeout:
                    to_remove.append(message_id)
            for message_id in to_remove:
                self.application_states.pop(message_id, None)
                guild_id = next((gid for gid, apps in applications_cache.items() if message_id in apps), None)
                if guild_id:
                    remove_application(guild_id, message_id)

application_state_manager = ApplicationStateManager()

async def clear_old_states():
    await application_state_manager.clear_old_states()