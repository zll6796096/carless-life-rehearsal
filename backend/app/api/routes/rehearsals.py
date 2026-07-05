from fastapi import APIRouter, HTTPException

from app.domain.models import LifeDiagnosis, RehearsalTask, RehearsalTaskList
from app.services.rehearsal.engine import generate_rehearsal_tasks

router = APIRouter(prefix="/rehearsals", tags=["rehearsals"])

_TASK_STORE: dict[str, RehearsalTask] = {}


@router.post("/generate", response_model=RehearsalTaskList)
def generate_rehearsals(diagnosis: LifeDiagnosis) -> RehearsalTaskList:
    tasks = generate_rehearsal_tasks(diagnosis)
    for task in tasks:
        _TASK_STORE[task.id] = task
    return RehearsalTaskList(tasks=tasks)


@router.get("/{task_id}", response_model=RehearsalTask)
def read_rehearsal(task_id: str) -> RehearsalTask:
    task = _TASK_STORE.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Rehearsal task not found")
    return task
