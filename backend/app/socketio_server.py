"""
Socket.IO server for KissanFlow real-time queue updates.
Uses AsyncRedisManager for pub/sub across multiple workers.
"""
import os
import socketio

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
REDIS_ENABLED = os.environ.get("REDIS_ENABLED", "false").lower() in {"1", "true", "yes"}

# AsyncRedisManager connects in a background listener, so an unavailable Redis
# server cannot be detected by wrapping its constructor in try/except.
client_manager = socketio.AsyncRedisManager(REDIS_URL) if REDIS_ENABLED else None
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    client_manager=client_manager,
    logger=False,
    engineio_logger=False,
)

# Track socket_id -> user_id mappings in memory
_socket_user_map: dict[str, str] = {}


@sio.event
async def connect(sid: str, environ: dict, auth: dict | None = None):
    user_id = (auth or {}).get("user_id")
    if user_id:
        _socket_user_map[sid] = user_id
    print(f"[SocketIO] Client connected: {sid} (user: {user_id})")


@sio.event
async def disconnect(sid: str):
    _socket_user_map.pop(sid, None)
    print(f"[SocketIO] Client disconnected: {sid}")


@sio.event
async def join_centre(sid: str, data: dict):
    """Staff/Officer joins a centre room to receive queue updates and alerts."""
    centre_id = data.get("centre_id")
    if centre_id:
        await sio.enter_room(sid, f"centre-{centre_id}")
        print(f"[SocketIO] {sid} joined room centre-{centre_id}")


@sio.event
async def leave_centre(sid: str, data: dict):
    centre_id = data.get("centre_id")
    if centre_id:
        await sio.leave_room(sid, f"centre-{centre_id}")


@sio.event
async def join_farmer(sid: str, data: dict):
    """Farmer joins their personal room to receive position updates."""
    booking_id = data.get("booking_id")
    if booking_id:
        await sio.enter_room(sid, f"farmer-{booking_id}")
        print(f"[SocketIO] {sid} joined room farmer-{booking_id}")


@sio.event
async def leave_farmer(sid: str, data: dict):
    booking_id = data.get("booking_id")
    if booking_id:
        await sio.leave_room(sid, f"farmer-{booking_id}")


async def emit_queue_updated(centre_id: str, queue_data: list):
    """Emit updated queue list to all clients in a centre room."""
    await sio.emit("queue:updated", {"queue": queue_data}, room=f"centre-{centre_id}")


async def emit_your_turn(booking_id: str, message: str = "Your turn has come"):
    """Notify a specific farmer that it's their turn."""
    await sio.emit(
        "queue:your-turn",
        {"message": message, "booking_id": booking_id},
        room=f"farmer-{booking_id}",
    )


async def emit_alert_new(centre_id: str, alert_data: dict):
    """Emit a new alert to all clients in a centre room."""
    await sio.emit("alert:new", alert_data, room=f"centre-{centre_id}")
