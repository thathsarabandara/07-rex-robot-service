from datetime import datetime

from pydantic import BaseModel


class ClaimRequest(BaseModel):
    robot_id: str
    robot_secret: str

class ClaimedRobotDetail(BaseModel):
    id: str
    name: str
    status: str
    owner_user_id: str
    claimed_at: datetime

class ClaimResponse(BaseModel):
    message: str
    robot: ClaimedRobotDetail

class UnpairResponse(BaseModel):
    message: str
    robot_id: str
    status: str

class CredentialsRotateResponse(BaseModel):
    message: str
    robot_id: str
    robot_secret: str
