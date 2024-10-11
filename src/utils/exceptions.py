from typing import Literal

class InvalidUrl(Exception):
    """
    A custom exception class to raise when the audio/video url is not in the right format.
    """
    def __init__(self,url:str=None,details:str=None):
        self.url = url
        self.message = f"URL provided is not of valid type: {self.url}"
        self.details = """
                The url must meet the url validation for being a signed url for any audio\
                video file.
                    """
        super().__init__(self.message)
    
    def __str__(self):
        error_str = super().__str__()
        if not self.details == None:
            error_str += f"\nError Details : {self.details}"
        return error_str

class ApiValidationException(Exception):
    """
    A custom exception to raise when the data provided to the API is not of the right format.
    """
    def __init__(self, api_data):
        self.api_data = api_data
        self.message = f"The provided API data is not with the agreed format: {self.api_data}"
        super().__init__(self.message)

class DBConfigException(Exception):
    """
    """
    def __init__(self):
        self.message = f"DB Configurations are missing."
        super().__init__(self.message)