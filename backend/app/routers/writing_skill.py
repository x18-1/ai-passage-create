"""Writing Skill routes."""

from fastapi import APIRouter, Depends

from app.deps import require_login
from app.schemas.common import BaseResponse
from app.schemas.user import LoginUserVO
from app.schemas.writing_skill import WritingSkillVO
from app.services.writing_skill_service import WritingSkillService


router = APIRouter(prefix="/writing-skills", tags=["写作 Skills"])


@router.get("", response_model=BaseResponse[list[WritingSkillVO]])
async def list_writing_skills(current_user: LoginUserVO = Depends(require_login)):
    return BaseResponse.success(data=WritingSkillService().list_skills())
