# A simple group chat application using FastAPI websocket and Redis

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
from datetime import datetime
from contextlib import asynccontextmanager
from rich.console import Console
import redis
import json
import uuid

# Define a message model
class Message(BaseModel):
    message_id: int
    username: str
    timestamp: str
    content: str

# Create a FastAPI app
app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect to Redis
redis_client = redis.Redis(host='localhost', port=6379, db=0)

# Load chat history on server start
CHAT_HISTORY_KEY = 'chat_history'
if redis_client.exists(CHAT_HISTORY_KEY):
    chat_history = json.loads(redis_client.get(CHAT_HISTORY_KEY))
else:
    chat_history = []

# Connection manager to keep track of active connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    # Connect a new user
    async def connect(self, websocket: WebSocket, username: str):
        self.active_connections[username] = websocket

    # Disconnect a user
    def disconnect(self, username: str):
        if username in self.active_connections:
            del self.active_connections[username]

    # Broadcast a message to all active connections
    async def broadcast(self, message: str):
        for connection in self.active_connections.values():
            await connection.send_text(message)

manager = ConnectionManager()

# Return minimal frontend
@app.get("/", response_class=HTMLResponse)
async def read_root() -> HTMLResponse:
    return HTMLResponse(open("index.html", "r").read())

# Join the group chat via WebSocket
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    username = None
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            if "username" in message:
                username = f"{message['username']}#{uuid.uuid4().hex[:6]}"
                await manager.connect(websocket, username)
                await websocket.send_text(f"Connected as {username}")
                await manager.broadcast(json.dumps({"content": f"{username} joined the chat", 
                                                    "timestamp": str(datetime.utcnow()), 
                                                    "username": "system"}))
                for msg in chat_history:
                    await websocket.send_text(json.dumps(msg))
            else:
                chat_message = Message(
                    message_id  =len(chat_history) + 1,
                    timestamp   =str(datetime.now()),
                    username    =username,
                    content     =message["content"]
                )
                chat_history.append(dict(chat_message))
                redis_client.set(CHAT_HISTORY_KEY, json.dumps(chat_history))
                await manager.broadcast(json.dumps(dict(chat_message)))

    # Handle WebSocket disconnect
    except WebSocketDisconnect:
        if username:
            manager.disconnect(username)
            await manager.broadcast(json.dumps({"content": f"{username} left the chat", 
                                                "timestamp": str(datetime.utcnow()), 
                                                "username": "system"}))

# Save chat history to Redis on server shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    redis_client.set(CHAT_HISTORY_KEY, json.dumps(chat_history))

app.router.lifespan_context = lifespan

# Run the FastAPI app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)