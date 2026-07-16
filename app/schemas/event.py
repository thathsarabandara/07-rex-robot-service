from datetime import datetime

from pydantic import BaseModel


class RobotEventResponse(BaseModel):
    id: str
    robot_id: str
    event_type: str
    severity: str
    message: str
    metadata: dict | list | None
    occurred_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True
