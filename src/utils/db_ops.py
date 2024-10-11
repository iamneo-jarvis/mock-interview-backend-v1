import mysql.connector
import json
import os
from src.neoscreener.logger import logger
import re
import logging
import json
import mysql.connector

async def update_section_wise_marks(db_config: dict, test_id: str) -> None:
    """
    Function to update the section_wise_marks field in the student_course table.

    Params:
        db_config: dict - database configuration
        test_id: str - the test ID from which to extract sections and question mappings.
    """
    try:
        # Connect to the database
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)

        # Fetch the template data for the given test
        query = f"""
            SELECT t.t_id, t.t_name, t.t_type, tt.template_data
            FROM tests t
            INNER JOIN test_templates tt ON tt.template_id = t.template_id
            WHERE t.t_id = %s
        """
        cursor.execute(query, (test_id,))
        test_template = cursor.fetchone()

        if not test_template:
            logger.error(f"No test template found for test_id: {test_id}")
            return

        # Parse the template_data
        template_data = json.loads(test_template['template_data'])

        # Iterate through the sections in the template data
        sections = template_data['sections']
        for section in sections:
            section_name = section['name']
            questions = [q for q in template_data['questions'] if q['sectionName'] == section_name]
            question_list = questions[0]['questionList'] if questions else []

            if not question_list:
                continue

            # Find corresponding student_question_id and marks for all questions in this section
            question_placeholders = ', '.join(['%s'] * len(question_list))
            query = f"""
                SELECT sq.s_question_id, sq.marks, sq.user_id, sq.c_id, sq.t_id, sq.attempt_no, sq.section_no
                FROM student_questions sq
                WHERE sq.q_id IN ({question_placeholders})
            """
            cursor.execute(query, tuple(question_list))
            student_questions = cursor.fetchall()

            # Group the results by user_id, c_id, t_id, attempt_no (to update for each student)
            grouped_data = {}
            for sq in student_questions:
                key = (sq['user_id'], sq['c_id'], sq['t_id'], sq['attempt_no'])
                if key not in grouped_data:
                    grouped_data[key] = {'marks_by_section': {}}

                # Accumulate marks for each section
                section_no = sq['section_no'] - 1  # Adjust for 0-based indexing
                if section_no not in grouped_data[key]['marks_by_section']:
                    grouped_data[key]['marks_by_section'][section_no] = 0
                grouped_data[key]['marks_by_section'][section_no] += sq['marks']

            # After accumulating the marks, update section_wise_marks for each student
            for (user_id, c_id, t_id, attempt_no), data in grouped_data.items():
                # Fetch the current section_wise_marks
                query = """
                    SELECT sc.section_wise_marks
                    FROM student_course sc
                    WHERE sc.user_id = %s AND sc.c_id = %s AND sc.t_id = %s AND sc.attempt_no = %s
                """
                cursor.execute(query, (user_id, c_id, t_id, attempt_no))
                student_course = cursor.fetchone()

                if not student_course:
                    logger.error(f"No student_course record found for user_id: {user_id}, c_id: {c_id}, t_id: {t_id}, attempt_no: {attempt_no}")
                    continue

                # Load the section_wise_marks JSON
                section_wise_marks = json.loads(student_course['section_wise_marks'])

                # Update the marks in the appropriate sections
                for section_no, total_marks in data['marks_by_section'].items():
                    if section_no < len(section_wise_marks):
                        section_wise_marks[section_no]['marks'] = total_marks

                # Update the section_wise_marks in the database
                update_query = """
                    UPDATE student_course
                    SET section_wise_marks = %s
                    WHERE user_id = %s AND c_id = %s AND t_id = %s AND attempt_no = %s
                """
                cursor.execute(update_query, (
                    json.dumps(section_wise_marks),
                    user_id,
                    c_id,
                    t_id,
                    attempt_no
                ))

        # Commit the transaction
        connection.commit()
        logger.info(f"Updated the student_course table with section_wise_marks for test_id {test_id}.")

    except mysql.connector.Error as err:
        logger.exception(f"MySQL Error: {err}")
    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

def insert_data_into_mysql(json_array: dict, db_config: dict) -> bool:
    """
    Function to perform insert/update in the video auto results table.
    
    Params : response header -> dict
             db_config -> dict
    """
    try:
        logger.info(f"DB Insert Initialised with data size, {len(json_array)} rows.")
        
        # Connect to your MySQL database using a context manager
        with mysql.connector.connect(**db_config) as connection:
            with connection.cursor() as cursor:
                # Bulk insert using executemany
                query = """INSERT INTO video_auto_results 
                            (transcription_id, s_question_id, q_id, video_link, transcription_text, answer_keywords, overall_score, q_subtype_id, answer_explanation, status, feedback) 
                        VALUES 
                            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            transcription_id = VALUES(transcription_id), 
                            s_question_id = VALUES(s_question_id), 
                            q_id = VALUES(q_id), 
                            video_link = VALUES(video_link), 
                            transcription_text = VALUES(transcription_text), 
                            answer_keywords = VALUES(answer_keywords), 
                            overall_score = VALUES(overall_score),
                            q_subtype_id = VALUES(q_subtype_id),
                            answer_explanation = VALUES(answer_explanation),
                            status = VALUES(status),
                            feedback = VALUES(feedback)
                        """
                values = []
                for entry in json_array:
                    feedback = entry.get('feedback', '[]')
                    overall_score = None
                    if isinstance(feedback, str):
                        try:
                            feedback_json = json.loads(feedback.strip())
                            if isinstance(feedback_json, list) and feedback_json:
                                feedback_dict = feedback_json[0] if isinstance(feedback_json[0], dict) else json.loads(feedback_json[0])
                                overall_score = feedback_dict.get('Rating', None)
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON in feedback: {feedback}")
                    values.append((
                        entry.get("transcription_id", None),
                        entry.get("s_question_id", None),
                        entry.get("q_id", None),
                        entry.get("video_link", None),
                        entry.get("transcription_text", None),
                        json.dumps(entry.get("answer_keywords", None)),
                        overall_score,
                        entry.get('q_subtype_id', None),
                        entry.get('answer_explanation', None),
                        entry.get('status', None),
                        entry.get('feedback', None)
                    ))
                cursor.executemany(query, values)

            # Commit the changes outside the inner 'with' block
            connection.commit()
            logger.info(f"DB Insert Completed with data size, {len(json_array)} rows.")
        return True
    except mysql.connector.Error as err:
        logger.exception(f"MySQL Error: {err}")
        # You might want to log the error or handle it appropriately
        return False
    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")
        return False

def retrieve_student_course_info(results: dict, db_config: dict) -> dict:
    """
    Function to retrieve the user_id, t_id, c_id, and attempt_no from the student_course table based on s_question_id.

    Params:
        s_question_id: int - the ID of the specific question
        db_config: dict - database configuration

    Returns:
        dict - a dictionary containing user_id, t_id, c_id, and attempt_no
    """
    try:
        with mysql.connector.connect(**db_config) as connection:
            with connection.cursor(dictionary=True) as cursor:
                for result in results:
                    s_question_id:int = result.get("s_question_id", None)
                    query = f"""
                        SELECT sq.user_id, sq.t_id, sq.c_id, sq.attempt_no
                        FROM student_questions sq
                        WHERE sq.s_question_id = {s_question_id}
                    """
                    cursor.execute(query)
                    result = cursor.fetchone()
                    print("result",result)
                    if result:
                        logger.info(f"Retrieved student_course info for s_question_id {s_question_id}")
                        return result
                    else:
                        logger.warning(f"No student_course information found for s_question_id {s_question_id}")
                        return {}
    except mysql.connector.Error as err:
        logger.exception(f"MySQL Error: {err}")
        return {}
    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")
        return {}


async def update_student_questions(results: dict, db_config: dict) -> None:
    """
    Performs the operation for updating the `student_questions` table for marks field.

    Params:
        results (dict): The response header containing student question data.
        db_config (dict): The database configuration for MySQL connection.
    """
    logger.info(f"Updating the `student_questions` table with {len(results)} rows.")
    
    try:
        # Establishing the MySQL connection
        with mysql.connector.connect(**db_config) as connection:
            with connection.cursor() as cursor:
                
                # Iterate over each result to update `student_questions`
                for result in results:
                    s_question_id = result.get("s_question_id")
                    
                    # Prepare the query with placeholders to avoid SQL injection
                    query = """
                    UPDATE student_questions AS sq
                    SET 
                        sq.marks = (
                            CASE 
                                WHEN EXISTS (SELECT 1 FROM video_auto_results WHERE s_question_id = %s AND overall_score IS NOT NULL) THEN
                                    (SELECT overall_score FROM video_auto_results WHERE s_question_id = %s)
                                ELSE
                                    0
                            END
                        ),
                        sq.state = (
                            CASE
                                WHEN EXISTS (SELECT 1 FROM video_auto_results WHERE s_question_id = %s AND overall_score IS NOT NULL) THEN
                                    IF ((SELECT overall_score FROM video_auto_results WHERE s_question_id = %s) = sq.q_total_marks, 1,
                                        IF ((SELECT overall_score FROM video_auto_results WHERE s_question_id = %s) = 0, 2, 4)
                                    )
                            END
                        )
                    WHERE sq.s_question_id = %s;
                    """
                    
                    # Execute the query with the correct parameters
                    cursor.execute(query, (s_question_id, s_question_id, s_question_id, s_question_id, s_question_id, s_question_id))
                    
                    logger.info(f"Updated student_questions table for s_question_id: {s_question_id}")
                
                # Commit the transaction
                connection.commit()
                
    except mysql.connector.Error as err:
        logger.exception(f"MySQL Error: {err}")
    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")


def update_student_course(results:dict,db_config:dict)->None:
    """
    Function to update the `student_course` table with feilds t_marks and section wise marks.
    
    Params : response header -> dict
             db_config -> dict
    """
    logger.info(f"Updating the student_course table.")
    try:
        with mysql.connector.connect(**db_config) as connection:
            with connection.cursor() as cursor:
                for result in results:
                    s_question_id:int = result.get("s_question_id", None)

                    query:str = f"""
                        UPDATE student_course sc
                        INNER JOIN student_questions sq ON sq.user_id = sc.user_id
                                                        AND sq.c_id = sc.c_id
                                                        AND sq.t_id = sc.t_id
                                                        AND sq.attempt_no = sc.attempt_no
                        SET
                            sc.t_marks = sc.t_marks + sq.marks,
                            sc.section_wise_marks = JSON_SET(
                                                        sc.section_wise_marks, 
                                                        CONCAT('$[', sq.section_no - 1, '].marks'), 
                                                        JSON_EXTRACT(sc.section_wise_marks, CONCAT('$[', sq.section_no - 1, '].marks')) + sq.marks
                                                    )
                        WHERE
                            sq.s_question_id = {s_question_id};
                    """
                    cursor.execute(query)
            connection.commit()
            logger.info(f"Updated the student_course table with t_marks and section_wise_marks for s_question_id {s_question_id}")
    except mysql.connector.Error as err:
        logger.exception(f"MySQL Error: {err}")
    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")

def get_questions_feedback(test_id:str|None,attempt_no:int|None,user_id:str|None,db_config:dict|None)->str:
    """
    """
    feedback_list = []
    try:
        with mysql.connector.connect(**db_config) as connector:
            with connector.cursor() as cursor:
                query:str = f"""
                select
                var.feedback
                from
                video_auto_results as var
                inner join student_questions sq on sq.s_question_id = var.s_question_id
                where
                sq.t_id = '{test_id}'
                and sq.attempt_no = {attempt_no}
                and sq.user_id = '{user_id}'
                and var.feedback is not null;
                """
                cursor.execute(query)
                results = cursor.fetchall()
                for result in results:
                    feedback_list.append(result[0])

        feedback_string = "\n".join(feedback_list)
        return feedback_string
    except Exception as e:
        raise e
    
# def trim_strings(obj):
#     if isinstance(obj, str):
#         return obj.strip()
#     elif isinstance(obj, list):
#         return [trim_strings(item) for item in obj]
#     elif isinstance(obj, dict):
#         return {key: trim_strings(value) for key, value in obj.items()}
#     return obj

def update_test_level(db_config: dict | None,
                      user_id: str | None,
                      t_id: str | None,
                      c_id: str | None,
                      attempt_no: str | None,
                      overall_feedback: str | None) -> None:
    """
    Update the overall feedback for a specific test attempt in the database, scaling the rating out of 10 into a score out of 30.

    Args:
        db_config (Optional[Dict[str, str]]): Database configuration dictionary.
        user_id (Optional[str]): User ID.
        t_id (Optional[str]): Test ID.
        c_id (Optional[str]): Course ID.
        attempt_no (Optional[str]): Attempt number.
        overall_feedback (Optional[str]): Overall feedback in JSON string format.

    Raises:
        Exception: If any error occurs during the process.
    """
    try:
        # Ensure overall_feedback is a string and not empty
        if isinstance(overall_feedback, str) and overall_feedback.strip():
            overall_feedback = overall_feedback.strip()
            
            # Parse the JSON string to a dictionary to access its contents
            try:
                overall_feedback_dict = json.loads(overall_feedback)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON for overall_feedback: {e}")
        else:
            raise ValueError("Overall feedback is either not a string or is empty")

        # Extract the overall rating
        overall_rating = overall_feedback_dict.get('overall_score')
        if isinstance(overall_rating, dict):
            overall_rating = overall_rating.get('Overall Rating')

        # Ensure the extracted overall_rating is numeric
        if not isinstance(overall_rating, (int, float)):
            raise ValueError("Overall rating should be a numeric value.")

        # Step 1: Connect to the database and retrieve t_total_marks
        connector = mysql.connector.connect(**db_config)
        cursor = connector.cursor()
        try:
            # Retrieve t_total_marks for the specific test
            select_query = """
            SELECT t_total_marks
            FROM student_course
            WHERE user_id = %s AND c_id = %s AND t_id = %s AND attempt_no = %s
            """
            cursor.execute(select_query, (user_id, c_id, t_id, attempt_no))
            result = cursor.fetchone()

            if result is None:
                raise ValueError("No matching record found for the given user, course, test, and attempt number.")

            t_total_marks = result[0]  # Assuming t_total_marks is the first (and only) column returned

            scaled_rating = (overall_rating / 10) * t_total_marks

            # Convert the feedback dictionary back to JSON string
            overall_feedback_json = json.dumps(overall_feedback_dict)

            # Step 3: Prepare the update query
            update_query = """
            UPDATE
                student_course
            SET
                overall_feedback = %s,
                t_marks = %s
            WHERE
                user_id = %s
                AND c_id = %s
                AND t_id = %s
                AND attempt_no = %s
            """

            # Execute the update query with scaled rating and JSON feedback
            cursor.execute(update_query, (overall_feedback_json, scaled_rating, user_id, c_id, t_id, attempt_no))

            # Commit the changes
            connector.commit()

        finally:
            cursor.close()
            connector.close()

    except Exception as e:
        raise Exception(f"Error updating test level feedback: {e}")

def trim_strings(data: dict) -> dict:
    """
    Recursively trim whitespace from all string values in a dictionary.

    Args:
        data (dict): The dictionary to trim.

    Returns:
        dict: The trimmed dictionary.
    """
    if isinstance(data, dict):
        return {k: trim_strings(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [trim_strings(item) for item in data]
    elif isinstance(data, str):
        return data.strip()
