from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
from datetime import datetime
from contextlib import asynccontextmanager
from rich.console import Console
import redis
import json
import uuid
import os

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

# Initialize rich console for logging
console = Console()

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

    # Get list of connected users
    def get_user_list(self):
        return list(self.active_connections.keys())

manager = ConnectionManager()

# Serve frontend HTML
@app.get("/", response_class=HTMLResponse)
async def read_root() -> HTMLResponse:
    return FileResponse('static/chat.html')

# Serve frontend JS
@app.get("/static/chat.js", response_class=HTMLResponse)
async def get_chat_js() -> HTMLResponse:
    return FileResponse('static/chat.js')

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
                # The user is joining the chat
                username = f"{message['username']}#{uuid.uuid4().hex[:6]}"
                await manager.connect(websocket, username)
                await websocket.send_text(f"Connected as {username}")
                await manager.broadcast(json.dumps({"content": f"{username} joined the chat", 
                                                    "timestamp": str(datetime.now()), 
                                                    "username": "system"}))
                for msg in chat_history:
                    await websocket.send_text(json.dumps(msg))
                console.log(f"{username} joined the chat.")
            else:
                # The user is sending a message
                chat_message = Message(
                    message_id  =len(chat_history) + 1,
                    timestamp   =str(datetime.now()),
                    username    =username,
                    content     =message["content"]
                )
                chat_history.append(dict(chat_message))
                redis_client.set(CHAT_HISTORY_KEY, json.dumps(chat_history))
                await manager.broadcast(json.dumps(dict(chat_message)))
                console.log(f"Message from {username}: {message['content']}")

                # Update user list that the new user has joined
                user_list_message = json.dumps({"content": "User list update", 
                                                "timestamp": str(datetime.now()), 
                                                "username": "system",
                                                "user_list": manager.get_user_list()})
                await manager.broadcast(user_list_message)

    # Handle WebSocket disconnect event
    except WebSocketDisconnect:
        if username:
            manager.disconnect(username)
            await manager.broadcast(json.dumps({"content": f"{username} left the chat", 
                                                "timestamp": str(datetime.now()), 
                                                "username": "system"}))
            console.log(f"{username} left the chat.")

            # Update the user list that one of the users has left
            user_list_message = json.dumps({"content": "User list update", 
                                            "timestamp": str(datetime.now()), 
                                            "username": "system",
                                            "user_list": manager.get_user_list()})
            await manager.broadcast(user_list_message)

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
