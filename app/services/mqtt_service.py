import json
import logging

import aiomqtt

from app.config.settings import settings

logger = logging.getLogger(__name__)

# Global persistent client
mqtt_client: aiomqtt.Client | None = None
test_publications: list[tuple[str, dict, int | None]] = []

async def init_mqtt_client():
    """Start the global MQTT client."""
    global mqtt_client
    if settings.APP_ENV == "test":
        logger.info("Skipping MQTT initialization in test environment")
        return
    try:
        mqtt_client = aiomqtt.Client(
            hostname=settings.MQTT_HOST,
            port=settings.MQTT_PORT,
            username=settings.MQTT_USERNAME,
            password=settings.MQTT_PASSWORD,
            timeout=settings.MQTT_KEEPALIVE_SECONDS
        )
        await mqtt_client.__aenter__()
        logger.info("MQTT client connected and initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize MQTT client: {e}")
        mqtt_client = None

async def close_mqtt_client():
    """Shut down the global MQTT client."""
    global mqtt_client
    if mqtt_client is not None:
        try:
            await mqtt_client.__aexit__(None, None, None)
            logger.info("MQTT client disconnected successfully")
        except Exception as e:
            logger.error(f"Error disconnecting MQTT client: {e}")
        finally:
            mqtt_client = None

async def publish_mqtt_message(topic: str, payload: dict, qos: int | None = None):
    """Publish a command message to the MQTT broker."""
    if qos is None:
        qos = settings.MQTT_COMMAND_QOS
        
    if settings.APP_ENV == "test":
        test_publications.append((topic, payload, qos))
        logger.info(f"[Test MQTT Mock] Published to {topic} (QoS {qos}): {payload}")
        return
        
    if mqtt_client is None:
        logger.warning(f"MQTT client is offline. Bypassed message on {topic}")
        return
        
    try:
        await mqtt_client.publish(topic, payload=json.dumps(payload), qos=qos)
    except Exception as e:
        logger.error(f"Failed to publish to MQTT topic {topic}: {e}")
