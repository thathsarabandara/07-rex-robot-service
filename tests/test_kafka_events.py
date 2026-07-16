import pytest

from app.services.kafka_service import publish_kafka_event, test_events


@pytest.mark.asyncio
async def test_publish_kafka_event_serializes_payload():
    test_events.clear()
    
    payload = {
        "user_id": "user-abc",
        "details": {"reason": "test"}
    }
    
    await publish_kafka_event(
        topic="rex.robot.registered.v1",
        event_type="robot_registered",
        payload=payload
    )
    
    assert len(test_events) == 1
    topic, event_payload = test_events[0]
    
    assert topic == "rex.robot.registered.v1"
    assert event_payload["event_type"] == "robot_registered"
    assert event_payload["user_id"] == "user-abc"
    assert event_payload["details"]["reason"] == "test"
    assert "event_id" in event_payload
    assert "occurred_at" in event_payload
