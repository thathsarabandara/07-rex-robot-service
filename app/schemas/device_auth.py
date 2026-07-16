from pydantic import BaseModel


class DeviceAuthenticateRequest(BaseModel):
    robot_id: str
    robot_secret: str
    firmware_version: str | None = None

class DeviceMQTTInfo(BaseModel):
    host: str
    port: int
    tls: bool
    client_id: str

class DeviceAuthenticateResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    access_token_expires_in: int
    refresh_token_expires_in: int
    mqtt: DeviceMQTTInfo

class DeviceRefreshRequest(BaseModel):
    refresh_token: str
