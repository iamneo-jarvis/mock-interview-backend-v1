from src.utils.api_validation import validate_api_data_nontech
import os
from dotenv import load_dotenv
from src.neoscreener.process_pipeline import *
from src.neoscreener.overall_feedback import OverallFeedbackPipeline
from src.neoscreener.logger import logger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.utils.db_ops import (insert_data_into_mysql, retrieve_student_course_info, update_section_wise_marks, update_student_questions)
from fastapi import BackgroundTasks
from src.utils.request_example import OveralFeedback
from src.neoscreener.process_pipeline import process_task
import uvicorn
from typing import List
import asyncio
import multiprocessing
from src.secrets.load_keys import LoadSecrets

# initialise app
app = FastAPI(
    title='Neo screener',
    description='Neo screener API for video based assessment auto evaluation.',
    version='2.0'
)

#Todo: Move all orgins to ENV
# define cors policy
origins = [
    'http://localhost',
    'http://localhost:8080',
    'http://localhost:3000',
    'http://localhost:5000',
]

@app.middleware("http")
async def add_security_headers(request, call_next):
    """
    Add security headers to the response
    :param request: Request object
    :param call_next: Next call back function
    """
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['POST'],
    allow_headers=['*'],
    expose_headers=['*'],
)
        
db_config = {
    'host':LoadSecrets('MY_SQL_HOST_ACC').get_env_value('MY_SQL_HOST_ACC'),
    'user':LoadSecrets('MY_SQL_USER_ACC').get_env_value('MY_SQL_USER_ACC'),
    'password':LoadSecrets('MY_SQL_PASSWORD_ACC').get_env_value('MY_SQL_PASSWORD_ACC'),
    'database':LoadSecrets('DATABASE').get_env_value('DATABASE'),
}
#REF : Please check with business on the response that we send. Since running as background proccess giving 200 will not be useful.
@app.post("/neo-screener")
async def screener(data: List[dict], background_tasks: BackgroundTasks):
    """
    API end point to accept the data and start the processing as a background task.
    """
    try:
        background_tasks.add_task(process_data, data)
        return {"message": "Data accepted and will be processed later"}
    except:
        logger.exception(f"Error processing data: {e}")
    


async def process_data(data: List[dict]):
    """
    This handles the asychronous processing of the tasks.
    """
    validation_status, message = validate_api_data_nontech(data=data)

    if validation_status:
        try:
            tasks = [process_task(doc) for doc in data]
            responses = await asyncio.gather(*tasks)
            status:bool = insert_data_into_mysql(json_array=responses, db_config=db_config)
            if status:
                # Call test-level-feedback after processing neo-screener tasks
                response_overall_feedback = retrieve_student_course_info(results=responses,db_config=db_config)
                await update_student_questions(results=responses, db_config=db_config)
                feedback_data = OveralFeedback(
                    user_id=response_overall_feedback['user_id'],  # Assuming you have this information in responses
                    test_id=response_overall_feedback['t_id'],  # Adjust according to your data structure
                    attempt_no=response_overall_feedback['attempt_no'],  # Adjust according to your data structure
                    course_id=response_overall_feedback['c_id']  # Adjust according to your data structure
                )
            await test_level_feedback(feedback_data)
            await update_section_wise_marks(db_config, feedback_data.test_id)
        except Exception as e:
            logger.exception(f"Error processing data: {e}")
    else:
        return {"message": f"Data is not up to the agreed format.\n{message}"}
    
@app.post('/test-level-feedback')
async def test_level_feedback(data:OveralFeedback)->None:
    try:
       # logger.info(f"STARTING OVERALL FEEDBACKKKKKKK {data}")
    #    OverallFeedbackPipeline.process_pipeline(data)
        result=OverallFeedbackPipeline(data.user_id,
                              data.test_id,
                             data.attempt_no,
                             data.course_id,
                             db_config)
        result.process_pipeline()
        return {"message": "Overall feedback processed successfully"}
    except Exception as e:
        logger.exception(f"Error processing data:{e}")


@app.get("/status")
async def root():
    return {"message": "Neo screener is running", "status": 200}


def run_uvicorn():
    config = uvicorn.Config("main:app", host="0.0.0.0", port=8080, log_level="info", reload=True,workers=(multiprocessing.cpu_count() * 2) + 1)
    server = uvicorn.Server(config)
    server.run()

if __name__ == "__main__":
    run_uvicorn()