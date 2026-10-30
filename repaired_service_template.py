import datetime
from taskflow.store import Store

VALID_STATUSES = {"todo", "in_progress", "done"}

TRANSITIONS = {
    "todo": {"in_progress", "done"},
    "in_progress": {"todo", "done"},
    "done": {"todo"}
}


class TaskFlowError(Exception):
    pass


class NotFound(TaskFlowError):
    pass


class Forbidden(TaskFlowError):
    pass


class InvalidInput(TaskFlowError):
    pass


class TaskFlowService:
    def __init__(self, store=None):
        self.store = store or Store()

    def create_user(self, name):
        name = name.strip()
        if not name:
            raise InvalidInput("name is required")

        # Check if the user already exists in the store
        for item in self.store.users.values():
            if item['name'].lower() == name.lower():
                raise InvalidInput("already exists")

        return self.store.add_user(name)

    def create_project(self, name, owner_id):
        if owner_id not in self.store.users:
            raise NotFound("owner not found")

        name = name.strip()
        if not name:
            raise InvalidInput("project name is required")

        return self.store.add_project(name, owner_id)

    def archive_project(self, project_id, actor_id):
        project = self._project(project_id)
        if project["owner_id"] != actor_id:
            raise Forbidden("only owner can archive project")

        project["archived"] = True
        return project

    def create_task(self, project_id, actor_id, title,
                    assignee_id=None, priority=3,
                    description="", due_date=None, created_at=None):
        project = self._project(project_id)

        if project["archived"]:
            raise InvalidInput("project is archived")

        if actor_id not in self.store.users:
            raise NotFound("actor not found")

        title = title.strip()
        if not title:
            raise InvalidInput("title is required")

        if priority < 1 or priority > 5:
            raise InvalidInput("priority must be between 1 and 5")

        if assignee_id is not None and assignee_id not in self.store.users:
            raise NotFound("assignee not found")

        if due_date is not None:
            try:
                datetime.date.fromisoformat(str(due_date))
            except (ValueError, TypeError):
                raise InvalidInput("due_date must be in YYYY-MM-DD format")

        description = (description or "").strip()

        # BUG: inactive users are allowed as assignees.
        return self.store.add_task(
            project_id, title, assignee_id, priority,
            description=description, due_date=due_date, created_at=created_at
        )

    def change_status(self, task_id, actor_id, new_status):
        task = self._task(task_id)

        if actor_id not in self.store.users:
            raise NotFound("actor not found")

        if new_status not in VALID_STATUSES:
            raise InvalidInput("invalid status")

        if new_status not in TRANSITIONS[task["status"]]:
            raise InvalidInput("invalid status transition")

        # Validate if actor_id is in the project of the task
        project = self._project(task["project_id"])
        if project["owner_id"] != actor_id:
            raise Forbidden("only project owner can change status")

        task["status"] = new_status
        return task

    def assign_task(self, task_id, actor_id, assignee_id):
        task = self._task(task_id)
        project = self._project(task["project_id"])

        if project["owner_id"] != actor_id:
            raise Forbidden("only owner can assign tasks")

        if assignee_id not in self.store.users:
            raise NotFound("assignee not found")

        # BUG: inactive users can be assigned.
        task["assignee_id"] = assignee_id
        return task

    def list_tasks(self, project_id, actor_id, status=None,
                    priority=None, offset=0, limit=20):
        self._project(project_id)

        if actor_id not in self.store.users:
            raise NotFound("actor not found")

        if offset < 0 or limit < 1 or limit > 100:
            raise InvalidInput("invalid pagination")

        tasks = [
            t for t in self.store.tasks.values()
            if t["project_id"] == project_id
        ]

        if status is not None:
            tasks = [t for t in tasks if t["status"] == status]

        if priority is not None:
            tasks = [t for t in tasks if t["priority"] == priority]

        # Ensure filters are applied before pagination
        tasks = tasks[offset:offset + limit]

        return tasks

    def delete_task(self, task_id, actor_id):
        task = self._task(task_id)
        project = self._project(task["project_id"])

        if project["owner_id"] != actor_id:
            raise Forbidden("only owner can delete tasks")

        del self.store.tasks[task_id]

    def _project(self, project_id):
        project = self.store.projects.get(project_id)
        if project is None:
            raise NotFound("project not found")
        return project

    def _task(self, task_id):
        task = self.store.tasks.get(task_id)
        if task is None:
            raise NotFound("task not found")
        return task

    def search_tasks(self, project_id, actor_id, query):
        self._project(project_id)
        if actor_id not in self.store.users:
            raise NotFound("actor not found")

        if not query or not query.strip():
            raise InvalidInput("query is required")

        q = query.strip().lower()
        # FIX: search should consider both title and description for matching.
        return [
            t for t in self.store.tasks.values()
            if (q in t["title"].lower() or q in (t.get("description") or "").lower())
        ]

    def filter_tasks_by_priority(self, project_id, actor_id, priority):
        self._project(project_id)
        if actor_id not in self.store.users:
            raise NotFound("actor not found")

        priority_str = str(priority).strip().lower()
        named_map = {
            "high": {1, 2},
            "medium": {3},
            "low": {4, 5}
        }

        if priority_str in named_map:
            allowed = named_map[priority_str]
        else:
            try:
                p_val = int(priority)
                if p_val < 1 or p_val > 5:
                    raise InvalidInput("priority must be between 1 and 5")
                allowed = {p_val}
            except (ValueError, TypeError):
                raise InvalidInput("invalid priority")

        return [
            t for t in self.store.tasks.values()
            if t["project_id"] == project_id and t["priority"] in allowed
        ]

    def get_overdue_tasks(self, project_id, actor_id, as_of_date=None):
        self._project(project_id)
        if actor_id not in self.store.users:
            raise NotFound("actor not found")

        if as_of_date is None:
            ref_date = datetime.date.today().isoformat()
        elif isinstance(as_of_date, datetime.date):
            ref_date = as_of_date.isoformat()
        else:
            try:
                ref_date = datetime.date.fromisoformat(str(as_of_date)).isoformat()
            except (ValueError, TypeError):
                raise InvalidInput("invalid as_of_date format, expected YYYY-MM-DD")

        # BUG: tasks due today are erroneously considered overdue (due_date <= ref_date instead of <).
        return [
            t for t in self.store.tasks.values()
            if t["project_id"] == project_id
            and t["due_date"] is not None
            and t["status"] != "done"
            and t["due_date"] < ref_date
        ]

    def get_tasks_due_within(self, project_id, actor_id, days, as_of_date=None):
        self._project(project_id)
        if actor_id not in self.store.users:
            raise NotFound("actor not found")

        try:
            days = int(days)
        except (ValueError, TypeError):
            raise InvalidInput("days must be an integer")

        if days < 0:
            raise InvalidInput("days must be non-negative")

        if as_of_date is None:
            start_date = datetime.date.today()
        elif isinstance(as_of_date, datetime.date):
            start_date = as_of_date
        else:
            try:
                start_date = datetime.date.fromisoformat(str(as_of_date))
            except (ValueError, TypeError):
                raise InvalidInput("invalid as_of_date format, expected YYYY-MM-DD")

        end_date = start_date + datetime.timedelta(days=days)
        start_str = start_date.isoformat()
        end_str = end_date.isoformat()

        return [
            t for t in self.store.tasks.values()
            if t["project_id"] == project_id
            and t["due_date"] is not None
            and t["status"] != "done"
            and start_str <= t["due_date"] <= end_str
        ]

    def get_task_statistics(self, project_id, actor_id):
        self._project(project_id)
        if actor_id not in self.store.users:
            raise NotFound("actor not found")

        tasks = [
            t for t in self.store.tasks.values()
            if t["project_id"] == project_id
        ]
        total = len(tasks)
        completed = len([t for t in tasks if t["status"] == "done"])
        pending = len([t for t in tasks if t["status"] in ("todo", "in_progress")])

        # Corrected calculation for completion percentage
        completion_percentage = round((completed / total) * 100, 2) if total > 0 else 0.0

        return {
            "total": total,
            "completed": completed,
            "pending": pending,
            "completion_percentage": completion_percentage
        }

    def get_sorted_tasks(self, project_id, actor_id, sort_by="created_at",
                         order="asc", offset=0, limit=20):
        self._project(project_id)
        if actor_id not in self.store.users:
            raise NotFound("actor not found")

        if offset < 0 or limit < 1 or limit > 100:
            raise InvalidInput("invalid pagination")

        if sort_by not in {"created_at", "due_date", "priority"}:
            raise InvalidInput("invalid sort field")

        if order not in {"asc", "desc"}:
            raise InvalidInput("invalid sort order")

        tasks = [
            t for t in self.store.tasks.values()
            if t["project_id"] == project_id
        ]

        reverse = (order == "desc")
        if sort_by == "priority":
            tasks.sort(key=lambda x: x["priority"], reverse=reverse)
        elif sort_by == "created_at":
            tasks.sort(key=lambda x: x.get("created_at", ""), reverse=reverse)
        elif sort_by == "due_date":
            tasks.sort(
                key=lambda x: (1 if x.get("due_date") is None else 0, x.get("due_date") or ""),
                reverse=reverse
            )

        return tasks[offset:offset + limit]
