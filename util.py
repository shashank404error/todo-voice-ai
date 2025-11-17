from datetime import datetime, timezone

def post_process(ai_response: dict)->dict:
    action = ai_response.get('action')
    if action == 'create':
        task = ai_response.get('task')
        if not isinstance(task, dict):
            task = {}
            ai_response['task'] = task
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        if now.endswith('+00:00'):
            now = now.replace('+00:00', 'Z')
        task['scheduled_time'] = now

    if check_if_task_failed(ai_response):
           return modify_task(ai_response) 

    return ai_response

def check_if_task_failed(ai_response: dict)-> bool:
    action = ai_response.get('action')
    if action == 'delete' or action == 'schedule' or action == 'fetch':
        task = ai_response.get('task')
        matched_indexes = task.get('matched_indexes')
        if len(matched_indexes)==0:
            return True
    return False

def modify_task(ai_response: dict)->dict:
    action = ai_response.get('action')
    if action == 'delete':
        ai_response["action"] = "none"
        ai_response["message"] = "Sorry, I didn't catch that. Could you please repeat it?"
    if action == 'schedule':
        ai_response["action"] = "none"
        ai_response["message"] = "Sorry, I didn't catch which meeting you're referring to. Could you please repeat that?"
    if action == 'fetch':
        ai_response["action"] = "none"
        ai_response["message"] = "I couldn't find any meeting with that description. Could you please provide more details?"        
    return  ai_response