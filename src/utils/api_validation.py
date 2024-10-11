from jsonschema import validate, ValidationError
from src.neoscreener.logger import logger
    
def validate_api_data_nontech(data):
    logger.info(
        f"Validating the API request data."
    )
    # Define the JSON schema for the expected data structure
    schema = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "s_question_id": {"type": "integer"},
            "q_id": {"type": "string"},
            "video_url": {"type": "string", "format": "uri"},
            "question": {"type": "string"}
        },
        "required": ["s_question_id", "q_id", "video_url", "question"]
    }
}
    try:
        # Validate the received data against the schema
        validate(data, schema)
        logger.info(
        f"Validated the API request data."
        )
        return True, "API data Validation successful"  # Validation successful
    except ValidationError as e:
        logger.exception(e)
        return False, str(e)  # Validation failed with error message
    
    # [level][date&time][thread/worker id][request-id][filename][funcname][line no]:[msg]