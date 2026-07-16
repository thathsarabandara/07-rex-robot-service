import json
import logging
import uuid
from datetime import datetime, timezone

from app.config.kafka import get_kafka_producer
from app.config.settings import settings

logger = logging.getLogger(__name__)

# Mock list for tracking events during testing
test_events: list[tuple[str, dict]] = []

async def publish_kafka_event(topic: str, event_type: str, payload: dict):
    """Serialize and dispatch event payload to Kafka topic."""
    event_payload = {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "event_version": 1,
        "occurred_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        **payload
    }
    
    if settings.APP_ENV == "test":
        test_events.append((topic, event_payload))
        logger.info(f"[Test Kafka Mock] Published to {topic}: {event_payload}")
        return
        
    producer = get_kafka_producer()
    if producer is None:
        logger.warning(f"Kafka producer offline. Dropped event on {topic}: {event_payload}")
        return
        
    try:
        value_bytes = json.dumps(event_payload).encode("utf-8")
        await producer.send_and_wait(topic, value_bytes)
        logger.info(f"Published Kafka event on {topic}")
    except Exception as e:
        logger.error(f"Failed to send Kafka event on {topic}: {e}")
