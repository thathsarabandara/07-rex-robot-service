from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.middleware.auth import get_current_user_id
from app.schemas.configuration import RobotConfigurationResponse, RobotConfigurationUpdateRequest
from app.services.configuration_service import get_robot_configuration, update_robot_configuration
from app.utils.ownership import verify_robot_ownership

router = APIRouter(prefix="/robots", tags=["Configurations"])

@router.get("/{robot_id}/config", response_model=RobotConfigurationResponse)
async def get_config(
    robot_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Retrieve robot configuration settings."""
    verify_robot_ownership(db, robot_id, user_id)
    return get_robot_configuration(db, robot_id)

@router.put("/{robot_id}/config", response_model=RobotConfigurationResponse)
async def update_config(
    robot_id: str,
    request: RobotConfigurationUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Update robot configuration settings, increment version, and notify device via MQTT."""
    robot = verify_robot_ownership(db, robot_id, user_id)
    config = update_robot_configuration(
        db=db,
        robot=robot,
        update_data=request.dict()
    )
    return config
