from app.config.settings import settings


def get_mqtt_config():
    return {
        "hostname": settings.MQTT_HOST,
        "port": settings.MQTT_PORT,
        "username": settings.MQTT_USERNAME,
        "password": settings.MQTT_PASSWORD,
        "timeout": settings.MQTT_KEEPALIVE_SECONDS,
        "tls": settings.MQTT_TLS_ENABLED,
    }
