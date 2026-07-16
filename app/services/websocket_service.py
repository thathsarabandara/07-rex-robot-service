import json
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Mapping from robot_id -> set of active WebSockets
        self.active_connections: dict[str, set[WebSocket]] = {}

    async def connect(self, robot_id: str, websocket: WebSocket):
        """Accept WebSocket connection and store it."""
        await websocket.accept()
        if robot_id not in self.active_connections:
            self.active_connections[robot_id] = set()
        self.active_connections[robot_id].add(websocket)
        logger.info(f"WebSocket client connected to robot {robot_id}")

    def disconnect(self, robot_id: str, websocket: WebSocket):
        """Remove WebSocket connection."""
        if robot_id in self.active_connections:
            self.active_connections[robot_id].discard(websocket)
            if not self.active_connections[robot_id]:
                del self.active_connections[robot_id]
        logger.info(f"WebSocket client disconnected from robot {robot_id}")

    async def broadcast(self, robot_id: str, message: dict):
        """Broadcast a JSON message to all WebSocket connections of a robot."""
        connections = self.active_connections.get(robot_id, set())
        if not connections:
            return
            
        payload = json.dumps(message)
        for connection in list(connections):
            try:
                await connection.send_text(payload)
            except Exception as e:
                logger.warning(f"Error sending message to client: {e}")
                # Clean up stale connection
                self.disconnect(robot_id, connection)

manager = ConnectionManager()

async def broadcast_to_robot(robot_id: str, message: dict):
    """Global helper to broadcast message to a robot's WebSocket clients."""
    await manager.broadcast(robot_id, message)
