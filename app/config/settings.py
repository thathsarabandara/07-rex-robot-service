from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "rex-robot-service"
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = True

    # MySQL
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_DATABASE: str = "rex_robot"
    MYSQL_USER: str = "rex_user"
    MYSQL_PASSWORD: str = "change-me"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/1"

    # User JWT
    USER_JWT_SECRET_KEY: str = "change-me"
    USER_JWT_ALGORITHM: str = "HS256"
    USER_JWT_ISSUER: str = "rex-auth-service"
    USER_JWT_AUDIENCE: str = "rex-platform"

    # Robot JWT
    ROBOT_JWT_SECRET_KEY: str = "change-me"
    ROBOT_JWT_ALGORITHM: str = "HS256"
    ROBOT_ACCESS_TOKEN_EXPIRE_HOURS: int = 12
    ROBOT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # MQTT
    MQTT_HOST: str = "localhost"
    MQTT_PORT: int = 1883
    MQTT_USERNAME: str = "rex_robot_service"
    MQTT_PASSWORD: str = "change-me"
    MQTT_TLS_ENABLED: bool = False
    MQTT_KEEPALIVE_SECONDS: int = 30
    MQTT_COMMAND_QOS: int = 1

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_CLIENT_ID: str = "rex-robot-service"

    # Auth Service
    AUTH_SERVICE_URL: str = "http://rex-auth-service:8000"

    # Lease and controls
    CONTROL_LEASE_EXPIRE_SECONDS: int = 10
    JOYSTICK_COMMAND_TIMEOUT_MS: int = 500
    MAX_WEBSOCKET_MESSAGES_PER_SECOND: int = 30

    # Heartbeats
    DEFAULT_HEARTBEAT_INTERVAL_SECONDS: int = 5
    DEFAULT_HEARTBEAT_TIMEOUT_SECONDS: int = 20

    GHCR_IMAGE: str = "ghcr.io/OWNER/07-rex-robot-service"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def database_url(self) -> str:
        return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"

settings = Settings()
