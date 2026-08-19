# -*- coding: utf-8 -*-
"""将演示截图合成为 GIF 动图（作品集用）。"""
from PIL import Image, ImageDraw, ImageFont
import os, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS = os.path.join(BASE, "screenshots")
OUT = os.path.join(SHOTS, "demo-chain.gif")

frames_src = [
    ("docs/architecture.png", "IntDevTools 架构 · AI 辅助研发交付链"),
    ("screenshots/demo-step1.png", "① 需求导入 · AI 辅助评估（开发等级 L2）"),
    ("screenshots/demo-step2.png", "② AI 设计审查 · 发现 3 项（人工确认）"),
    ("screenshots/demo-step3.png", "③ AI 生成评价基准 · 14 项清单"),
    ("screenshots/demo-step4.png", "④ 知识沉淀 · 闭环复用"),
    ("docs/architecture.png", "需求导入 → 审查 → 评价基准 → 知识沉淀"),
]

def font(size):
    for fp in (r"C:\Windows\Fonts\msyhbd.ttc", r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\arialbd.ttf"):
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return ImageFont.load_default()

frames = []
for rel, caption in frames_src:
    img = Image.open(os.path.join(BASE, rel)).convert("RGB")
    img = img.resize((1152, 720), Image.LANCZOS)
    canvas = Image.new("RGB", (1152, 792), (11, 18, 32))
    canvas.paste(img, (0, 40))
    draw = ImageDraw.Draw(canvas)
    f = font(26)
    # caption bar
    draw.rectangle([0, 0, 1152, 40], fill=(16, 26, 46))
    draw.text((24, 8), caption, font=f, fill=(34, 211, 238))
    frames.append(canvas)

frames[0].save(OUT, save_all=True, append_images=frames[1:], duration=2200, loop=0, optimize=False)
print("GIF written:", OUT, os.path.getsize(OUT) // 1024, "KB")

