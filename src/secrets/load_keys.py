from dotenv import load_dotenv
import os

class LoadSecret:
    _instance = None
    file_name = '.env.development'
    def __new__(cls, env_file='.env.development' if os.getenv('NODE_ENV') == 'development' else '.env.production'):
        if cls._instance is None:
            cls._instance = super(LoadSecret, cls).__new__(cls)
            load_dotenv(env_file)  # Load .env file once
        return cls._instance

    def get_secret(self, key, default=None):
        return os.getenv(key, default)