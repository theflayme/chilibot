import subprocess
import time
import os
import signal
import sys
import requests
from threading import Thread
from dotenv import load_dotenv

load_dotenv()

class ServerConfig:
    def __init__(self):
        self._host = os.getenv('API_HOST', '127.0.0.1')
        self._port = int(os.getenv('API_PORT', '8000'))
        self._database_mode = os.getenv('DATABASE_MODE', 'firebase')
    
    @property
    def host(self):
        return self._host
    
    @property
    def port(self):
        return self._port
    
    @property
    def database_mode(self):
        return self._database_mode
    
    @property
    def url(self):
        return f"http://{self._host}:{self._port}"
    
    def get_api_module(self):
        if self._database_mode == 'firebase':
            return "src.api_firebase:app"
        return "src.api:app"
    
    def get_expected_message(self):
        if self._database_mode == 'firebase':
            return "Discord Bot Firebase API is running"
        return "Discord Bot API is running"


class ProcessManager:
    def __init__(self):
        self._process = None
    
    def start_process(self, command):
        self._process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
    
    def stop_process(self):
        if self._process:
            os.kill(self._process.pid, signal.SIGTERM)
            self._process = None
    
    @property
    def is_active(self):
        return self._process is not None


class ServerValidator:
    def __init__(self, config):
        self._config = config
    
    def wait_for_server(self, timeout=30, interval=1):
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self._check_server_response():
                return True
            time.sleep(interval)
        return False
    
    def _check_server_response(self):
        try:
            response = requests.get(self._config.url)
            if response.status_code == 200:
                response_data = response.json()
                expected_message = self._config.get_expected_message()
                return response_data.get('message') == expected_message
        except requests.exceptions.ConnectionError:
            pass
        return False
    
    def is_server_running(self):
        try:
            response = requests.get(self._config.url)
            return response.status_code == 200
        except requests.exceptions.ConnectionError:
            return False


class APIServerManager:
    def __init__(self):
        self._config = ServerConfig()
        self._process_manager = ProcessManager()
        self._validator = ServerValidator(self._config)

    def start(self):
        if self._validator.is_server_running():
            return
        
        command = self._build_command()
        self._process_manager.start_process(command)
        self._validator.wait_for_server()

    def _build_command(self):
        python_executable = sys.executable
        api_module = self._config.get_api_module()
        
        return [
            python_executable, "-m", "uvicorn", api_module,
            "--host", self._config.host,
            "--port", str(self._config.port)
        ]

    def stop(self):
        self._process_manager.stop_process()

    def is_running(self):
        return self._validator.is_server_running()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()