import logging

from aiokafka import AIOKafkaProducer

from app.config.settings import settings

logger = logging.getLogger(__name__)

producer: AIOKafkaProducer | None = None

async def init_kafka():
    global producer
    if settings.APP_ENV == "test":
        logger.info("Skipping Kafka initialization in test environment")
        return
    try:
        producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            client_id=settings.KAFKA_CLIENT_ID
        )
        await producer.start()
        logger.info("Kafka producer started successfully")
    except Exception as e:
        logger.error(f"Failed to start Kafka producer: {e}")

async def close_kafka():
    global producer
    if producer is not None:
        try:
            await producer.stop()
            logger.info("Kafka producer stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping Kafka producer: {e}")
        finally:
            producer = None

def get_kafka_producer() -> AIOKafkaProducer | None:
    return producer
