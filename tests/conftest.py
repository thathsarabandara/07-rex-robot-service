import os
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


# Async Redis Mock classes defined early
class MockPipeline:
    def __init__(self, redis_mock):
        self.redis_mock = redis_mock
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
        
    def zremrangebyscore(self, key, min_val, max_val):
        pass
        
    def zcard(self, key):
        pass
        
    def zadd(self, key, mapping):
        pass
        
    def expire(self, key, seconds):
        pass
        
    def hset(self, key, mapping=None, **kwargs):
        if key not in self.redis_mock.store:
            self.redis_mock.store[key] = {}
        if mapping:
            self.redis_mock.store[key].update(mapping)
        return self

    async def execute(self):
        # count is index 1, return 1 to bypass rate limit
        return [0, 1, 1, True]

class MockAsyncRedis:
    def __init__(self):
        self.store = {}
        self.ttls = {}
        
    async def hgetall(self, key):
        return self.store.get(key, {})
        
    async def delete(self, key):
        self.store.pop(key, None)
        return 1
        
    async def hmset(self, key, mapping):
        self.store[key] = mapping
        return True
        
    async def hset(self, key, mapping=None, **kwargs):
        if key not in self.store:
            self.store[key] = {}
        if mapping:
            self.store[key].update(mapping)
        return 1
        
    async def expire(self, key, seconds):
        self.ttls[key] = seconds
        return True
        
    def pipeline(self, transaction=True):
        return MockPipeline(self)

mock_redis_instance = MockAsyncRedis()

# Override environment variables for testing before loading app config
os.environ["APP_ENV"] = "test"
os.environ["USER_JWT_SECRET_KEY"] = "test-user-secret"
os.environ["ROBOT_JWT_SECRET_KEY"] = "test-robot-secret"

# Setup Test Database (SQLite in-memory) defined early
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Eagerly override redis and database before any import loads them into local namespace
import app.config.redis
app.config.redis.redis_client = mock_redis_instance

import app.config.database
app.config.database.SessionLocal = TestingSessionLocal
app.config.database.engine = engine

# Now import the rest of app components
from app.config.database import Base, get_db
from app.config.settings import settings
from app.main import app as fastapi_app
from app.services.kafka_service import test_events
from app.services.mqtt_service import test_publications

@pytest.fixture(autouse=True)
def mock_redis():
    """Mock Redis client globally for tests, resetting state between tests."""
    mock_redis_instance.store.clear()
    mock_redis_instance.ttls.clear()
    return mock_redis_instance

@pytest.fixture(autouse=True)
def clear_event_mocks():
    """Reset the mock event and publication logs before each test."""
    test_events.clear()
    test_publications.clear()
    yield

@pytest.fixture(scope="function")
def db():
    """Fixture that initializes tables and returns a functional session."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db):
    """Fixture returning TestClient with db overrides."""
    def override_get_db():
        try:
            yield db
        finally:
            pass
            
    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(fastapi_app) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()

# Authentication Helpers
@pytest.fixture
def generate_user_jwt():
    def _generate(user_id: str = "user-123", email_verified: bool = True) -> str:
        payload = {
            "sub": user_id,
            "session_id": "session-123",
            "email_verified": email_verified,
            "iss": settings.USER_JWT_ISSUER,
            "aud": settings.USER_JWT_AUDIENCE,
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(seconds=3600)).timestamp())
        }
        return jwt.encode(payload, settings.USER_JWT_SECRET_KEY, algorithm=settings.USER_JWT_ALGORITHM)
    return _generate

@pytest.fixture
def generate_robot_jwt():
    def _generate(robot_id: str = "robot-123", token_type: str = "robot_access") -> str:
        payload = {
            "sub": robot_id,
            "type": token_type,
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(seconds=43200)).timestamp())
        }
        return jwt.encode(payload, settings.ROBOT_JWT_SECRET_KEY, algorithm=settings.ROBOT_JWT_ALGORITHM)
    return _generate
