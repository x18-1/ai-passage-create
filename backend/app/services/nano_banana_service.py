"""Nano Banana (Gemini 原生图片生成) 服务（第 5 期新增）"""

import logging
from typing import Optional
from google import genai
from google.genai import types

from app.config import settings
from app.constants.article import ArticleConstant
from app.models.enums import ImageMethodEnum
from app.services.image_search_service import ImageSearchService
from app.schemas.image import ImageData, ImageRequest

logger = logging.getLogger(__name__)

# 支持 image_size 参数的模型前缀（Gemini 3.x 系列）
_MODELS_WITH_IMAGE_SIZE = ("gemini-3",)


class NanoBananaService(ImageSearchService):
    """Nano Banana (Gemini 原生图片生成) 服务"""
    
    def __init__(self):
        self.api_key = settings.nano_banana_api_key
        self.model = settings.nano_banana_model
        self.aspect_ratio = settings.nano_banana_aspect_ratio
        self.image_size = settings.nano_banana_image_size
        self.client = genai.Client(api_key=self.api_key)
    
    async def search_image(self, keywords: str) -> Optional[str]:
        """此方法已废弃，请使用 get_image_data()"""
        return None
    
    async def get_image_data(self, request: ImageRequest) -> Optional[ImageData]:
        """获取图片数据"""
        prompt = request.get_effective_param(True)
        return await self.generate_image_data(prompt)
    
    async def generate_image_data(self, prompt: str) -> Optional[ImageData]:
        """
        根据提示词生成图片数据。
        
        Nano Banana 使用 generate_content 接口（非 Imagen 的 generate_images），
        图片以 inline_data 形式返回于 response.parts 中。
        
        Args:
            prompt: 生图提示词
            
        Returns:
            ImageData 包含图片字节数据，生成失败返回 None
        """
        try:
            model_name = self.model or "gemini-2.5-flash-image"
            
            # 构建 ImageConfig：仅 Gemini 3.x 支持 image_size
            image_config_kwargs: dict = {}
            if self.aspect_ratio:
                image_config_kwargs["aspect_ratio"] = self.aspect_ratio
            if self.image_size and model_name.startswith(_MODELS_WITH_IMAGE_SIZE):
                image_config_kwargs["image_size"] = self.image_size
            
            config = types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(**image_config_kwargs) if image_config_kwargs else None,
            )
            
            logger.info(f"Nano Banana 开始生成图片, model={model_name}, prompt={prompt}")
            
            response = self.client.models.generate_content(
                model=model_name,
                contents=[prompt],
                config=config,
            )
            
            # 从 parts 中找到 inline_data（图片数据）
            for part in response.parts:
                if part.inline_data is not None:
                    image_bytes = part.inline_data.data
                    mime_type = part.inline_data.mime_type or "image/png"
                    logger.info(
                        f"Nano Banana 图片生成成功, "
                        f"size={len(image_bytes)} bytes, mimeType={mime_type}"
                    )
                    return ImageData.from_bytes(image_bytes, mime_type)
            
            logger.error("Nano Banana 响应中未找到图片数据")
            return None
        except Exception as e:
            logger.error(f"Nano Banana 生成图片异常: {e}")
            return None
    
    def get_method(self) -> ImageMethodEnum:
        """获取图片服务类型"""
        return ImageMethodEnum.NANO_BANANA
    
    def get_fallback_image(self, position: int) -> str:
        """获取降级图片"""
        return ArticleConstant.PICSUM_URL_TEMPLATE.format(position)
