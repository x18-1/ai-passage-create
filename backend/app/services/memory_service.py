"""Long-term memory service."""

from datetime import datetime
from typing import Any

from app.schemas.memory import MemoryCreateRequest, MemoryUpdateRequest, MemoryVO


STAGE_MEMORY_TYPES = {
    "title": {"style", "platform", "topic", "constraint"},
    "outline": {"style", "platform", "topic", "constraint"},
    "content": {"style", "platform", "topic", "constraint"},
    "image": {"visual", "platform", "topic", "constraint"},
}


class MemoryService:
    def __init__(self, db):
        self.db = db

    async def create_memory(self, request: MemoryCreateRequest, login_user) -> int:
        return await self.db.execute(
            query="""
                INSERT INTO user_memory (userId, memoryType, title, content, weight, source, isActive)
                VALUES (:userId, :memoryType, :title, :content, :weight, 'manual', 1)
            """,
            values={
                "userId": login_user.id,
                "memoryType": request.memory_type,
                "title": request.title.strip(),
                "content": request.content.strip(),
                "weight": request.weight,
            },
        )

    async def list_memories(self, user_id: int, memory_type: str | None = None) -> list[MemoryVO]:
        values: dict[str, Any] = {"userId": user_id}
        type_filter = ""
        if memory_type:
            type_filter = "AND memoryType = :memoryType"
            values["memoryType"] = memory_type

        rows = await self.db.fetch_all(
            query=f"""
                SELECT id, userId, memoryType, title, content, weight, source, isActive, createTime, updateTime
                FROM user_memory
                WHERE userId = :userId AND isDelete = 0 {type_filter}
                ORDER BY weight DESC, updateTime DESC
            """,
            values=values,
        )
        return [self._to_vo(row) for row in rows]

    async def list_for_stage(self, user_id: int, stage: str) -> list[MemoryVO]:
        allowed_types = STAGE_MEMORY_TYPES.get(stage, set())
        if not allowed_types:
            return []
        memories = await self.list_memories(user_id)
        return [
            memory
            for memory in memories
            if memory.is_active and memory.memory_type in allowed_types
        ]

    async def update_memory(self, memory_id: int, request: MemoryUpdateRequest, user_id: int) -> bool:
        fields = request.model_dump(by_alias=True, exclude_none=True)
        if not fields:
            return True

        assignments = []
        values: dict[str, Any] = {"id": memory_id, "userId": user_id, "updateTime": datetime.now()}
        for field, value in fields.items():
            assignments.append(f"{field} = :{field}")
            values[field] = value.strip() if isinstance(value, str) else value
        assignments.append("updateTime = :updateTime")

        result = await self.db.execute(
            query=f"""
                UPDATE user_memory
                SET {", ".join(assignments)}
                WHERE id = :id AND userId = :userId AND isDelete = 0
            """,
            values=values,
        )
        return bool(result is not None)

    async def toggle_memory(self, memory_id: int, user_id: int) -> bool:
        row = await self.db.fetch_one(
            query="""
                SELECT id, isActive
                FROM user_memory
                WHERE id = :id AND userId = :userId AND isDelete = 0
            """,
            values={"id": memory_id, "userId": user_id},
        )
        if not row:
            return False

        next_active = 0 if self._get(row, "isActive") else 1
        await self.db.execute(
            query="""
                UPDATE user_memory
                SET isActive = :isActive, updateTime = :updateTime
                WHERE id = :id AND userId = :userId
            """,
            values={
                "isActive": next_active,
                "updateTime": datetime.now(),
                "id": memory_id,
                "userId": user_id,
            },
        )
        return bool(next_active)

    async def delete_memory(self, memory_id: int, user_id: int) -> bool:
        await self.db.execute(
            query="""
                UPDATE user_memory
                SET isDelete = 1, updateTime = :updateTime
                WHERE id = :id AND userId = :userId
            """,
            values={"id": memory_id, "userId": user_id, "updateTime": datetime.now()},
        )
        return True

    def _to_vo(self, row) -> MemoryVO:
        return MemoryVO(
            id=self._get(row, "id"),
            userId=self._get(row, "userId"),
            memoryType=self._get(row, "memoryType"),
            title=self._get(row, "title"),
            content=self._get(row, "content"),
            weight=self._get(row, "weight"),
            source=self._get(row, "source"),
            isActive=bool(self._get(row, "isActive")),
            createTime=self._get(row, "createTime"),
            updateTime=self._get(row, "updateTime"),
        )

    def _get(self, row, key: str):
        try:
            return row[key]
        except TypeError:
            return getattr(row, key)
