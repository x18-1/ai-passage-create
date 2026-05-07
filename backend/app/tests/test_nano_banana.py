import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.services.nano_banana_service import NanoBananaService

OUTPUT_FILE = Path(__file__).parent / "test_output.png"
PROMPT = "A minimalist illustration of a futuristic city skyline at sunset, purple and orange gradient sky, clean vector art style"


async def main():
    svc = NanoBananaService()
    print(f"model={svc.model}, aspect_ratio={svc.aspect_ratio}")
    print(f"prompt={PROMPT}\n")

    result = await svc.generate_image_data(PROMPT)

    if result:
        OUTPUT_FILE.write_bytes(result.data)
        print(f"✅ 成功！大小: {len(result.data)} bytes，mime: {result.mime_type}")
        print(f"   已保存: {OUTPUT_FILE}")
    else:
        print("❌ 生成失败，返回 None")


asyncio.run(main())
