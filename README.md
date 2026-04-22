# REX Robot Identity Server

A comprehensive FastAPI-based service for robot identification, device authentication, and IoT security. This server provides secure machine JWT token generation, device fingerprinting, and robot lifecycle management.

## Features

### 🤖 Robot Identity Management
- **Unique Robot Identity** (`robot_id`): Each robot gets a unique identifier
- **Serial Number Tracking**: Hardware-backed robot identification
- **Robot Status Management**: ACTIVE, INACTIVE, SUSPENDED, DEACTIVATED states
- **Firmware Version Tracking**: Monitor robot software versions

### 🔐 Secure Machine Authentication
- **JWT-based Authentication**: Secure token generation for robots
- **Machine JWT**: Access and refresh tokens with configurable expiry
- **Session Management**: Track active robot sessions
- **Token Revocation**: Logout and session termination

### 👁️ Device Fingerprinting
- **Multi-factor Hardware Identification**:
  - Hardware ID
  - MAC Address
  - CPU Information
  - OS Information
  - System UUID
- **HMAC-SHA256 Hashing**: Cryptographically secure fingerprint generation
- **Fingerprint Verification**: Validate device authenticity on each login
- **Strength Assessment**: Evaluate fingerprint component quality

### 📱 Device Management
- **Multi-Device Support**: Primary, secondary, sensor, actuator, and edge compute devices
- **MAC Address Registration**: Hardware-backed device tracking
- **Device Activation/Deactivation**: Control device access
- **Public Key Management**: Asymmetric key storage for devices

### 📊 Security Audit Trail
- **Login Attempt Tracking**: Record all authentication attempts
- **Success/Failure Monitoring**: Track successful and failed logins
- **IP Address Logging**: Network-level audit trail
- **Fingerprint Verification Counts**: Monitor device verification attempts

## Architecture

```
rex-identity-server/
├── app/
│   ├── models/          # SQLAlchemy database models
│   ├── routes/          # FastAPI endpoints
│   ├── services/        # Business logic layer
│   ├── security/        # Cryptographic utilities
│   ├── utils/           # Helper functions
│   ├── config.py        # Configuration management
│   ├── database.py      # Database setup
│   ├── schemas.py       # Pydantic models
│   └── main.py          # FastAPI application
├── tests/               # Test suite
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables
└── README.md            # This file
```

## API Endpoints

### Robot Management
- `POST /api/robots/register` - Register a new robot
- `GET /api/robots/{robot_identifier}` - Get robot details
- `GET /api/robots` - List all robots
- `POST /api/robots/{robot_identifier}/heartbeat` - Record heartbeat
- `POST /api/robots/{robot_identifier}/activate` - Activate robot
- `POST /api/robots/{robot_identifier}/deactivate` - Deactivate robot

### Device Management
- `POST /api/devices/{robot_identifier}/register` - Register device
- `GET /api/devices/{robot_identifier}` - Get robot devices
- `GET /api/devices/detail/{device_identifier}` - Get device details
- `POST /api/devices/{device_identifier}/deactivate` - Deactivate device

### Authentication
- `POST /api/auth/login` - Authenticate robot and issue tokens
- `POST /api/auth/refresh` - Refresh access token
- `POST /api/auth/logout` - Logout and revoke session

### Device Fingerprinting
- `POST /api/fingerprints/register/{robot_identifier}` - Register fingerprint
- `GET /api/fingerprints/{robot_identifier}` - Get robot fingerprints
- `GET /api/fingerprints/detail/{fingerprint_hash}` - Get fingerprint details
- `POST /api/fingerprints/verify/{robot_identifier}` - Verify fingerprint
- `POST /api/fingerprints/strength` - Check fingerprint strength

### Health
- `GET /api/health/` - Health check
- `GET /api/health/ready` - Readiness check

## Installation

### Prerequisites
- Python 3.9+
- PostgreSQL 12+ (or SQLite for development)
- pip

### Setup

1. **Clone the repository**
```bash
cd rex-identity-server
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
# Copy and edit .env file
cp .env.example .env
# Edit .env with your settings
```

5. **Initialize database**
```bash
# For PostgreSQL, ensure database exists
createdb rex_identity

# Create tables
python -c "from app.database import Base, engine; Base.metadata.create_all(bind=engine)"
```

## Running the Server

### Development
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production
```bash
gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker
```

### With Docker
```bash
docker build -t rex-identity-server .
docker run -p 8000:8000 rex-identity-server
```

## Testing

### Run tests
```bash
pytest tests/
```

### Run tests with coverage
```bash
pytest tests/ --cov=app --cov-report=html
```

### Run specific test file
```bash
pytest tests/test_robots.py -v
```

## Usage Examples

### 1. Register a Robot
```bash
curl -X POST http://localhost:8000/api/robots/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "REX-001",
    "model": "REX-Pro-v2",
    "serial_number": "REX-SN-20240422-001",
    "firmware_version": "2.1.0",
    "description": "Home Assistant Robot",
    "location": "Living Room"
  }'
```

### 2. Register Device
```bash
curl -X POST http://localhost:8000/api/devices/REX-001/register \
  -H "Content-Type: application/json" \
  -d '{
    "device_type": "ROBOT_PRIMARY",
    "name": "REX-PRIMARY-ETH0",
    "mac_address": "00:1A:2B:3C:4D:5E",
    "public_key": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"
  }'
```

### 3. Robot Login (Authenticate)
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "robot_id": "REX-001",
    "fingerprint": {
      "hardware_id": "hw-001",
      "mac_address": "00:1A:2B:3C:4D:5E",
      "cpu_info": "ARM Cortex-A72",
      "os_info": "Ubuntu 22.04 LTS",
      "system_uuid": "550e8400-e29b-41d4-a716-446655440000"
    }
  }'
```

### 4. Refresh Token
```bash
curl -X POST http://localhost:8000/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

### 5. Robot Heartbeat
```bash
curl -X POST http://localhost:8000/api/robots/REX-001/heartbeat \
  -H "Content-Type: application/json" \
  -d '{
    "robot_id": "REX-001",
    "status": "OPERATIONAL",
    "metadata": {
      "battery_level": 85,
      "cpu_usage": 45,
      "memory_usage": 60
    }
  }'
```

## Configuration

### Environment Variables
```
# Application
APP_NAME=REX Identity Server
DEBUG=True
ENVIRONMENT=development

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/rex_identity

# JWT
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRES=3600
JWT_REFRESH_TOKEN_EXPIRES=2592000

# Device Fingerprinting
DEVICE_FINGERPRINT_SALT=your-salt-change-in-production
FINGERPRINT_ALGORITHM=sha256

# Security
ARGON2_TIME_COST=2
ARGON2_MEMORY_COST=65536
ARGON2_PARALLELISM=4

# CORS
CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]
```

## Security Considerations

### JWT Tokens
- **Access Tokens**: Short-lived (default 1 hour), used for API access
- **Refresh Tokens**: Long-lived (default 30 days), used to obtain new access tokens
- Tokens include:
  - Robot ID
  - Device ID (if applicable)
  - JWT ID (JTI) for tracking
  - Expiry time
  - Issuer and audience information

### Device Fingerprinting
- Uses HMAC-SHA256 for secure hashing
- Components: Hardware ID, MAC address, CPU info, OS info, System UUID
- Fingerprints are verified on every login
- Verification count tracks device activity

### Password and Key Security
- Uses Argon2 for password hashing (configurable parameters)
- Public keys stored in database for asymmetric operations
- Cryptographically secure random token generation

### Audit Trail
- All login attempts recorded (success/failure)
- IP addresses logged for network-level auditing
- Fingerprint verification tracked
- Session management with revocation support

## Deployment

### PostgreSQL Setup
```bash
# Create user and database
createuser robot_user
createdb rex_identity -O robot_user
```

### Nginx Configuration Example
```nginx
upstream rex_identity {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name identity.example.com;

    location / {
        proxy_pass http://rex_identity;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## API Documentation

Once running, access interactive API documentation:
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

## Database Schema

The service uses SQLAlchemy ORM with the following tables:
- **robots**: Robot entities
- **devices**: IoT devices associated with robots
- **device_fingerprints**: Hardware fingerprint records
- **authentication_sessions**: Active/revoked JWT sessions
- **login_attempts**: Audit trail of login attempts

## Performance Optimization

- Database connection pooling (10 connections, 20 overflow)
- Index on frequently queried fields (robot_id, device_id, fingerprint_hash)
- JWT token verification using HMAC
- CORS middleware for efficient browser requests

## Troubleshooting

### Common Issues

**Database Connection Error**
```
ensure DATABASE_URL is correct and database exists
```

**JWT Token Errors**
```
verify JWT_SECRET_KEY is set and consistent across restarts
check token expiry time
```

**Fingerprint Mismatch**
```
ensure all fingerprint components match exactly
verify MAC address format
```

## License

Proprietary - REX Development Team

## Support

For issues and support, contact: support@rex-robotics.com
