
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
import asyncio
import json
import os
import secrets
import time
import aiohttp
from urllib.parse import urlencode

from src.database import (
    get_settings, save_settings, get_all_settings,
    applications_cache, owners_cache, init_owners,
    is_owner, OWNERS
)
from dotenv import load_dotenv
load_dotenv()
APPLICATIONS_FILE = os.getenv('APPLICATIONS_FILE')

app = FastAPI(title="Ili Chili Bot API", version="1.0.0")

# Настройка CORS для React приложения
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Discord OAuth Configuration
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "your_discord_client_id")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "your_discord_client_secret")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "http://localhost:3000/auth/callback")
DISCORD_API_ENDPOINT = "https://discord.com/api/v10"

# Хранилище для сессий (в реальном приложении используйте Redis или базу данных)
sessions = {}

# Модели данных
class DiscordAuthRequest(BaseModel):
    code: str

class SessionVerifyRequest(BaseModel):
    sessionId: str

class GuildSettings(BaseModel):
    guild_id: int
    form_channel_id: Optional[int] = None
    approv_channel_id: Optional[int] = None
    approver_role_id: Optional[int] = None
    approved_role_id: Optional[int] = None

class FormData(BaseModel):
    channel_id: int
    title: str
    description: str
    button_text: str = "Подать заявку"

class RoleConfig(BaseModel):
    guild_id: int
    approver_role_id: int
    approved_role_id: int

class BotStats(BaseModel):
    total_guilds: int
    total_applications: int
    pending_applications: int
    approved_applications: int
    rejected_applications: int

# Глобальная переменная для бота
bot_instance = None

def set_bot_instance(bot):
    """Устанавливает экземпляр бота для использования в API"""
    global bot_instance
    bot_instance = bot

def get_bot():
    """Получает экземпляр бота"""
    if bot_instance is None:
        raise HTTPException(status_code=503, detail="Бот не запущен")
    return bot_instance

# Discord OAuth functions
async def exchange_code_for_token(code: str) -> dict:
    """Обменивает код авторизации на токен доступа"""
    data = {
        'client_id': DISCORD_CLIENT_ID,
        'client_secret': DISCORD_CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': DISCORD_REDIRECT_URI,
    }
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(f'{DISCORD_API_ENDPOINT}/oauth2/token', data=data, headers=headers) as response:
            if response.status != 200:
                raise HTTPException(status_code=400, detail="Failed to exchange code for token")
            return await response.json()

async def get_user_info(access_token: str) -> dict:
    """Получает информацию о пользователе"""
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f'{DISCORD_API_ENDPOINT}/users/@me', headers=headers) as response:
            if response.status != 200:
                raise HTTPException(status_code=400, detail="Failed to get user info")
            return await response.json()

async def get_user_guilds(access_token: str) -> list:
    """Получает список серверов пользователя"""
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f'{DISCORD_API_ENDPOINT}/users/@me/guilds', headers=headers) as response:
            if response.status != 200:
                raise HTTPException(status_code=400, detail="Failed to get user guilds")
            return await response.json()

# Discord OAuth Endpoints
@app.get("/auth/discord/url")
async def get_discord_auth_url():
    """Получить URL для авторизации через Discord"""
    params = {
        'client_id': DISCORD_CLIENT_ID,
        'redirect_uri': DISCORD_REDIRECT_URI,
        'response_type': 'code',
        'scope': 'identify email guilds'
    }
    
    auth_url = f"https://discord.com/api/oauth2/authorize?{urlencode(params)}"
    return {"url": auth_url}

@app.get("/auth/discord/callback")
async def discord_callback(code: str = None, error: str = None):
    """Callback для Discord OAuth"""
    if error:
        return RedirectResponse(url=f"http://localhost:3000/auth/sign-in?error={error}")
    
    if not code:
        return RedirectResponse(url="http://localhost:3000/auth/sign-in?error=no_code")
    
    try:
        # Обмениваем код на токен
        token_data = await exchange_code_for_token(code)
        access_token = token_data['access_token']
        
        # Получаем информацию о пользователе
        user_info = await get_user_info(access_token)
        
        # Получаем серверы пользователя
        user_guilds = await get_user_guilds(access_token)
        
        # Создаем сессию
        session_id = secrets.token_urlsafe(32)
        sessions[session_id] = {
            'user': user_info,
            'guilds': user_guilds,
            'access_token': access_token,
            'created_at': time.time()
        }
        
        # Перенаправляем в popup callback
        callback_url = f"http://localhost:3000/auth/callback?session_id={session_id}"
        
        # Для popup callback, отправляем JavaScript который отправит сообщение родительскому окну
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Discord Auth Success</title>
        </head>
        <body>
            <script>
                if (window.opener) {{
                    window.opener.postMessage({{
                        success: true,
                        sessionId: '{session_id}',
                        user: {json.dumps(user_info)},
                        guilds: {json.dumps(user_guilds)}
                    }}, 'http://localhost:3000');
                    window.close();
                }} else {{
                    window.location.href = '{callback_url}';
                }}
            </script>
            <p>Авторизация прошла успешно. Если окно не закрылось автоматически, закройте его вручную.</p>
        </body>
        </html>
        """
        
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        return RedirectResponse(url=f"http://localhost:3000/auth/sign-in?error={str(e)}")

@app.post("/auth/verify")
async def verify_session(request: SessionVerifyRequest):
    """Проверить существующую сессию"""
    session_id = request.sessionId
    
    if session_id not in sessions:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    session_data = sessions[session_id]
    
    # Проверяем, не истекла ли сессия (24 часа)
    if time.time() - session_data['created_at'] > 86400:
        del sessions[session_id]
        raise HTTPException(status_code=401, detail="Session expired")
    
    return {
        'user': session_data['user'],
        'guilds': session_data['guilds']
    }

@app.post("/auth/refresh-guilds")
async def refresh_user_guilds(request: SessionVerifyRequest):
    """Обновить список серверов пользователя"""
    session_id = request.sessionId
    
    if session_id not in sessions:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    session_data = sessions[session_id]
    access_token = session_data['access_token']
    
    try:
        # Получаем обновленный список серверов
        user_guilds = await get_user_guilds(access_token)
        
        # Обновляем сессию
        sessions[session_id]['guilds'] = user_guilds
        
        return {'guilds': user_guilds}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/auth/logout")
async def logout_user(request: SessionVerifyRequest):
    """Выход из системы"""
    session_id = request.sessionId
    
    if session_id in sessions:
        del sessions[session_id]
    
    return {"message": "Logged out successfully"}

# API endpoints
@app.get("/api/status")
async def get_bot_status():
    """Получить статус бота"""
    try:
        bot = get_bot()
        return {
            "status": "online" if bot.is_ready() else "offline",
            "guilds": len(bot.guilds) if bot.guilds else 0,
            "user": {
                "id": bot.user.id if bot.user else None,
                "name": str(bot.user) if bot.user else None
            }
        }
    except:
        return {
            "status": "offline",
            "guilds": 0,
            "user": None
        }

@app.get("/api/guilds")
async def get_guilds():
    """Получить список серверов бота"""
    try:
        bot = get_bot()
        guilds = []
        for guild in bot.guilds:
            settings = get_settings(guild.id)
            guilds.append({
                "id": guild.id,
                "name": guild.name,
                "member_count": guild.member_count,
                "icon": str(guild.icon) if guild.icon else None,
                "configured": bool(settings)
            })
        return guilds
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/guilds/{guild_id}/settings")
async def get_guild_settings(guild_id: int):
    """Получить настройки сервера"""
    try:
        settings = get_settings(guild_id)
        if not settings:
            return {
                "guild_id": guild_id,
                "form_channel_id": None,
                "approv_channel_id": None,
                "approver_role_id": None,
                "approved_role_id": None
            }
        return settings
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/guilds/{guild_id}/settings")
async def update_guild_settings(guild_id: int, settings: GuildSettings):
    """Обновить настройки сервера"""
    try:
        save_settings(
            guild_id,
            form_channel_id=settings.form_channel_id,
            approv_channel_id=settings.approv_channel_id,
            approver_role_id=settings.approver_role_id,
            approved_role_id=settings.approved_role_id
        )
        return {"message": "Настройки обновлены успешно"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/guilds/{guild_id}/channels")
async def get_guild_channels(guild_id: int):
    """Получить список каналов сервера"""
    try:
        bot = get_bot()
        guild = bot.get_guild(guild_id)
        if not guild:
            raise HTTPException(status_code=404, detail="Сервер не найден")
        
        channels = []
        for channel in guild.text_channels:
            channels.append({
                "id": channel.id,
                "name": channel.name,
                "type": "text"
            })
        return channels
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/guilds/{guild_id}/roles")
async def get_guild_roles(guild_id: int):
    """Получить список ролей сервера"""
    try:
        bot = get_bot()
        guild = bot.get_guild(guild_id)
        if not guild:
            raise HTTPException(status_code=404, detail="Сервер не найден")
        
        roles = []
        for role in guild.roles:
            if role.name != "@everyone":  # Исключаем роль @everyone
                roles.append({
                    "id": role.id,
                    "name": role.name,
                    "color": str(role.color),
                    "position": role.position,
                    "mentionable": role.mentionable
                })
        return sorted(roles, key=lambda x: x["position"], reverse=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/guilds/{guild_id}/create-form")
async def create_application_form(guild_id: int, form_data: FormData):
    """Создать форму для подачи заявок"""
    try:
        bot = get_bot()
        guild = bot.get_guild(guild_id)
        if not guild:
            raise HTTPException(status_code=404, detail="Сервер не найден")
        
        channel = guild.get_channel(form_data.channel_id)
        if not channel:
            raise HTTPException(status_code=404, detail="Канал не найден")
        
        # Здесь будет логика создания формы
        # Пока возвращаем успешный ответ
        save_settings(guild_id, form_channel_id=form_data.channel_id)
        
        return {"message": "Форма создана успешно"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/applications")
async def get_all_applications():
    """Получить все заявки"""
    try:
        # Загружаем заявки из файла
        if not os.path.exists(APPLICATIONS_FILE):
            return []
        
        with open(APPLICATIONS_FILE, 'r', encoding='utf-8') as f:
            applications = json.load(f)
        
        # Преобразуем в список
        result = []
        for app_id, app_data in applications.items():
            result.append({
                "id": app_id,
                **app_data
            })
        
        return sorted(result, key=lambda x: x.get("timestamp", 0), reverse=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/applications/{guild_id}")
async def get_guild_applications(guild_id: int):
    """Получить заявки для конкретного сервера"""
    try:
        applications = await get_all_applications()
        guild_applications = [app for app in applications if app.get("guild_id") == guild_id]
        return guild_applications
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
async def get_bot_stats():
    """Получить статистику бота"""
    try:
        bot = get_bot()
        
        # Подсчитываем заявки
        applications = await get_all_applications()
        pending = len([app for app in applications if app.get("status") == "pending"])
        approved = len([app for app in applications if app.get("status") == "approved"])
        rejected = len([app for app in applications if app.get("status") == "rejected"])
        
        return {
            "total_guilds": len(bot.guilds) if bot.guilds else 0,
            "total_applications": len(applications),
            "pending_applications": pending,
            "approved_applications": approved,
            "rejected_applications": rejected
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sync-commands")
async def sync_bot_commands():
    """Синхронизировать команды бота"""
    try:
        bot = get_bot()
        synced = await bot.tree.sync()
        return {
            "message": f"Синхронизировано {len(synced)} команд",
            "commands": [cmd.name for cmd in synced]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 