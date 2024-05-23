# redis-websocket-groupchat
**A small example of live chatting room with Python FastAPI + WebSocket + Redis**

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![JavaScript](https://img.shields.io/badge/javascript-%23323330.svg?style=for-the-badge&logo=javascript&logoColor=%23F7DF1E)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Redis](https://img.shields.io/badge/redis-%23DD0031.svg?style=for-the-badge&logo=redis&logoColor=white)

![screenshot](./_readme_pictures/websocket_redis_chat.png)

### How to run
Very simple. Hit `uvicorn server:app --reload` and access to URL shown on the FastAPI console. Set your own nickname and start chatting with other users(sessions). This doesn't use cookies or something for simplicity.