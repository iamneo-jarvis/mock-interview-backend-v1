import yaml
import os
from pathlib import Path
from src.neoscreener.logger import logger


def read_yaml(path_to_yaml: Path):
    """reads yaml file and returns

    Args:
        path_to_yaml (str): path like input

    Raises:
        ValueError: if yaml file is empty
        e: empty file

    Returns:
        ConfigBox: ConfigBox type
    """
    try:
        with open(path_to_yaml) as yaml_file:
            content = yaml.safe_load(yaml_file)
            logger.info(f"yaml file: {path_to_yaml} loaded successfully")
            return content
    except Exception as e:
        logger.exception(f"yaml file: {path_to_yaml} did not loaded successfully")
        raise e

@staticmethod
def make_dirs(paths:list[Path])->None:
    """
    Function to create passed directories.

    Args:
        paths:list[Path]

    Raises:
        - WinError : System access or Permission error
        - Exception : Generic Exception Class
    
    Returns : None
    """
    try:
        for path in paths:
            if not os.path.exists(path):
                os.makedirs(path,exist_ok=True)
    except Exception as e:
        logger.error(
            f"Exception occured in make_dirs: {e}"
        )
        raise e
    
@staticmethod
def delete_dirs(paths:list[Path])->None:
    """
    Method to delete a given lists of direcotry paths.

    Args:
        paths:list[Path]

    Raises:
        - WinError : System access or Permission error
        - Exception : Generic Exception Class
    
    Returns : None
    """
    try:
        for path in paths:
            if os.path.exists(path):
                os.remove(path)
    except Exception as e:
        logger.error(
            f"Exception occured in make_dirs: {e}"
        )
        raise e