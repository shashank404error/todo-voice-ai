import json
from datetime import datetime
from typing import List, Optional

class Task:
    def __init__(self, index: int, title: str, description: str = "", scheduled_time: Optional[datetime] = None):
        self.index = index
        self.title = title
        self.description = description
        self.scheduled_time = scheduled_time

    def to_dict(self):
        return {
            "index": self.index,
            "title": self.title,
            "description": self.description,
            "scheduled_time": self.scheduled_time.isoformat() if self.scheduled_time else ""
        }


class TodoStore:
    def __init__(self):
        self.tasks: List[Task] = []
        self.next_index = 0

    def create_task(self, title: str, description: str = "", scheduled_time: str = "") -> dict:
        dt = None
        if scheduled_time:
            try:
                dt = datetime.fromisoformat(scheduled_time.replace("Z", "+00:00"))
            except:
                pass

        task = Task(
            index=self.next_index,
            title=title,
            description=description,
            scheduled_time=dt,
        )

        self.tasks.append(task)
        self.next_index += 1

        return {"status": "created", "task": task.to_dict()}

    def fetch_task(self, index: int) -> dict:
        for t in self.tasks:
            if t.index == index:
                return {"status": "fetched", "task": t.to_dict()}
        return {"error": f"Task {index} not found"}

    def delete_task(self, index: int) -> dict:
        for t in self.tasks:
            if t.index == index:
                self.tasks.remove(t)
                return {"status": "deleted", "index": index}
        return {"error": f"Task {index} not found"}

    def schedule_task(self, index: int, schedule_time: str) -> dict:
        try:
            dt = datetime.fromisoformat(schedule_time.replace("Z", "+00:00"))
        except Exception:
            return {"error": "Invalid scheduled_time (must be RFC3339)"}

        for t in self.tasks:
            if t.index == index:
                t.scheduled_time = dt
                return {"status": "scheduled", "task": t.to_dict()}

        return {"error": f"Task {index} not found"}

    def fetch_all_tasks(self) -> dict:
        return {"status": "fetched", "tasks": [t.to_dict() for t in self.tasks]}

def fetch_task_indexes(ai_response: dict,store: TodoStore) -> dict:
        fetched_task = []
        taskObj = ai_response.get("task")
        for i in taskObj.get("matched_indexes"):
            ft = store.fetch_task(i)
            t = ft.get("task")
            fetched_task.append(t)
        return {"status": "fetched", "task": fetched_task}

def handle_action(json_data: dict, store: TodoStore):
    action = json_data.get("action")
    task_obj = json_data.get("task", {})

    if action == "create":
        return store.create_task(
            title=task_obj.get("title", ""),
            description=task_obj.get("description", ""),
            scheduled_time=task_obj.get("scheduled_time", "")
        )

    elif action == "fetch":
        taskObj = json_data.get("task")
        for i in taskObj.get("matched_indexes"):
            store.fetch_task(i)
        return {"status": "fetched", "index": task_obj.get("index")}

    elif action == "delete":
        taskObj = json_data.get("task")
        for i in taskObj.get("matched_indexes"):
            store.delete_task(i)
        return {"status": "deleted", "index": task_obj.get("index")}

    elif action == "schedule":
        return store.schedule_task(
            index=task_obj.get("index"),
            schedule_time=task_obj.get("scheduled_time", "")
        )

    else:
        return {"message": "no action taken"}
