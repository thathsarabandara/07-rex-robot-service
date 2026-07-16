from datetime import datetime

from pydantic import BaseModel


class CommandResponse(BaseModel):
    id: str
    robot_id: str
    issued_by_user_id: str | None
    command_type: str
    payload: dict | list | None
    status: str
    priority: int
    expires_at: datetime | None
    acknowledged_at: datetime | None
    completed_at: datetime | None
    failure_reason: str | None
    created_at: datetime

    class Config:
        from_attributes = True
