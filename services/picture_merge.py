import os
from PIL import Image

def overlay_image(base_path: str, overlay_paths: list[str], save_path: str = "output/combined.jpg", alpha: int = 120):
    # 1. 원본 이미지 열기
    base = Image.open(base_path).convert("RGBA")

    # 2. 오버레이 이미지들 열고 합성
    for overlay_path in overlay_paths:
        if not os.path.exists(overlay_path):
            print(f"{overlay_path} 없음 - 건너뜀")
            continue
        overlay = Image.open(overlay_path).convert("RGBA")
        overlay.putalpha(alpha)  # 투명도 설정
        base = Image.alpha_composite(base, overlay)

    # 3. 저장
    base_rgb = base.convert("RGB")
    base_rgb.save(save_path, "JPEG")
    print(f"합성 이미지 저장 완료: {save_path}")