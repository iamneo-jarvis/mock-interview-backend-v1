from dotenv import load_dotenv
import os

# Initialize env_path
env_path = None
load_dotenv()
node_env = os.getenv('NODE_ENV')
if node_env == 'development':
    env_path = 'DEV_ENV_PATH'
elif node_env == 'production':
    env_path = 'PROD_ENV_PATH'
else:
    raise ValueError("NODE_ENV is not set or is invalid. Please set it to 'development' or 'production'.")

load_dotenv(dotenv_path=os.environ.get(env_path))

class LoadSecrets:
    def __init__(self, env_name: str) -> None:
        self.env_name = env_name
        env_value = os.getenv(self.env_name)
        print(f"ENV VALUE: {env_value}")

    def get_env_value(self, key_name: str):
        return os.getenv(key_name)