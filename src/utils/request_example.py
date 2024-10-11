from pydantic import BaseModel,UUID4
from typing import List,Dict

class response(BaseModel):
    s_question_id: int = None # from api payload
    transcription_id:UUID4 = None # from api -> need column in db to store -> insert ops
    question: str = None # read from db
    answer: str = None # from api payload
    video_link: str = None # from api payload
    transcription:str = None # from api to insert into db
    answer_keywords:List[str] = None # from api payload
    regex_match:Dict[str,float] = None # from api to insert into db
    word_frequency_match:Dict[str,float] = None # from api to insert into db
    lexical_match:Dict[str,Dict[str,float]] = None # from api to insert into db
    overall_skill_wise_match:Dict[str,float] = None # from api to insert into db
    overall_match:float = None # from api to insert into db

class health_check(BaseModel):
    redis_health:str=None
    assemblyAi_health:str=None

class OveralFeedback(BaseModel):
    user_id:str
    test_id:str
    attempt_no:int
    course_id:str

class neo_screener(BaseModel):
    s_question_id: int
    q_id: str
    video_url: str
    vas_subtype_id: int
    question: str