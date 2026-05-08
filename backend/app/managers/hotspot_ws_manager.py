"""热点 WebSocket 连接管理器"""

import json
import logging
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class HotspotWsManager:
    def __init__(self):
        self._connections: set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.add(ws)
        logger.info("热点 WebSocket 连接建立，当前连接数=%s", len(self._connections))

    def disconnect(self, ws: WebSocket) -> None:
        self._connections.discard(ws)
        logger.info("热点 WebSocket 连接断开，当前连接数=%s", len(self._connections))

    async def broadcast(self, message: dict) -> None:
        if not self._connections:
            return
        data = json.dumps(message, ensure_ascii=False, default=str)
        dead: set[WebSocket] = set()
        for ws in list(self._connections):
            try:
                await ws.send_text(data)
            except Exception:
                dead.add(ws)
        self._connections -= dead


# 模块级单例
hotspot_ws_manager = HotspotWsManager()
