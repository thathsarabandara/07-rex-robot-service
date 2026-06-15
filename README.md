# 🤖 REX-47 Robot Service

> **Repository `07`** · The core backend service responsible for interfacing with the physical hardware, translating high-level autonomous commands into executable multi-joint kinematic sequences.

[![Platform](https://img.shields.io/badge/Platform-Backend-blue)]()
[![Language](https://img.shields.io/badge/Language-Python-3776AB?logo=python)]()
[![Framework](https://img.shields.io/badge/Framework-FastAPI-009688?logo=fastapi)]()
[![Hardware](https://img.shields.io/badge/Hardware-ESP32%20%7C%20I2C-FFB300)]()
[![Status](https://img.shields.io/badge/Status-Active%20Development-green)]()

---

## 📋 Table of Contents

- [Overview](#-what-is-this-repository)
- [Architecture](#-architecture)
- [Features](#-features)
- [Getting Started](#-getting-started)
- [Hardware Communication](#-hardware-communication)
- [Kinematics & Control](#-kinematics--control)
- [Dependencies](#-dependencies)
- [Related Repositories](#-related-repositories)

---

## 🧭 What Is This Repository?

This Python-based service is the **brain of the physical operation**. It bridges the gap between the high-level decision-making services (like the AI Agent Runtime) and the low-level embedded firmware (`02-rex-firmware`) running on the robot's microcontrollers.

**Key Highlights:**
- ✅ **Hardware Abstraction:** Exposes a clean REST and WebSocket API for manipulating servos, motors, and sensors without dealing with low-level I2C or PWM signals.
- ✅ **Inverse Kinematics (IK):** Translates target XYZ coordinates into specific joint angles for the robotic manipulator.
- ✅ **State Machine:** Maintains the current physical state, safety locks, and operational modes (Manual vs. Autonomous) of the robot.
- ✅ **High-Performance Asynchronous IO:** Built on FastAPI to handle concurrent command streams and WebSocket telemetry with minimal latency.

---

## 🏗️ Architecture

### Directory Structure

```
07-rex-robot-service/
├── src/
│   ├── api/                  ← FastAPI route handlers and dependency injection
│   ├── core/                 ← Configuration and environment variables
│   ├── hardware/             ← Serial, BLE, and Socket communication clients
│   ├── kinematics/           ← Mathematical models for forward/inverse kinematics
│   ├── state/                ← In-memory representation of robot physical state
│   ├── tasks/                ← Background workers for polling sensor data
│   └── main.py               ← FastAPI application entry point
├── .env.example              ← Environment variables template
├── docker-compose.yml        ← Local infrastructure setup
├── Dockerfile                ← Container build instructions
├── requirements.txt          ← Python dependencies
└── README.md                 ← This documentation
```

---

## 🎨 Features

### 🕹️ **Motion Control**

| Feature | Description |
|---------|-------------|
| **Direct Joint Control** | Fine-grained API to set exact angles for J1 through J6. |
| **Inverse Kinematics** | Coordinate-based movement (`moveTo(x, y, z)`). |
| **Path Interpolation** | Smooth trajectory generation to prevent jerky hardware movements. |

### 🛡️ **Safety & Hardware Management**

| Feature | Description |
|---------|-------------|
| **Emergency Stop (E-Stop)** | Hardware-level interrupt trigger to immediately halt all PWM signals. |
| **Collision Avoidance** | Pre-checks movement commands against physical bounding boxes to prevent self-collision. |
| **Hardware Health Checks** | Constant polling of servo temperatures and voltage drops. |

---

## 🚀 Getting Started

### Prerequisites

- **Python** ≥ 3.10
- **pip** and `virtualenv`
- Access to the local network or direct serial connection to the ESP32.

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/thathsarabandara/07-rex-robot-service.git
cd 07-rex-robot-service

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`

# 3. Install dependencies
pip install -r requirements.txt
```

### Environment Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

Configure the connection to the hardware (Serial or Network):

```env
# Server
PORT=5002
ENVIRONMENT=development

# Hardware Interface
CONNECTION_TYPE=SOCKET  # SERIAL or SOCKET
ESP32_IP=192.168.1.100
ESP32_PORT=8080
SERIAL_PORT=/dev/ttyUSB0
BAUD_RATE=115200
```

### Running the Application

```bash
# Start the uvicorn server with hot-reload
uvicorn src.main:app --reload --port 5002
```

---

## ⚙️ Hardware Communication

The service communicates with the `02-rex-firmware` via a custom JSON-based command protocol over either a TCP Socket (for Wi-Fi operation) or a direct Serial cable. 

**Example Command Payload:**
```json
{
  "cmd": "SET_JOINT",
  "payload": {
    "joint": "J1",
    "angle": 45,
    "speed": 80
  }
}
```

---

## 📦 Dependencies

### Core
- `fastapi` — Modern, fast (high-performance) web framework.
- `uvicorn` — ASGI web server implementation.
- `pydantic` — Data validation and settings management.

### Hardware & Math
- `pyserial` — Serial port access for direct hardware communication.
- `numpy` — Matrix math used extensively in Inverse Kinematics calculations.

---

## 🔗 Related Repositories

- [02-rex-firmware](../02-rex-firmware) — The C++ code running on the ESP32 that receives commands from this service.
- [05-rex-api-gateway](../05-rex-api-gateway) — Proxies external traffic to this service.
- [10-rex-navigation-engine](../10-rex-navigation-engine) — Sends pathing commands to this service.
