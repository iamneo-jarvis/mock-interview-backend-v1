import os
import sys
import logging

logging_str = '[%(asctime)s: %(levelname)s: %(module)s - line %(lineno)d: %(message)s]'

log_dir = 'logs'

log_filepath = os.path.join(log_dir,'running_logs.log')
os.makedirs(log_dir,exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format=logging_str,

    handlers=[
        logging.FileHandler(log_filepath), # saving log in the specified folder path
        logging.StreamHandler(sys.stdout) # printing log in terminal
    ]
)

logger = logging.getLogger('neoprescreener')