# digest_image_bot.py
# 优化版公众号生成脚本：
# - 封面图 + 新闻点评 + 日历卡片改为图片形式
# - 保留原有内容逻辑和 AI 输出流程
# - 适合微信端阅读

import os
import re
import requests
import random
import subprocess
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree
from PIL import Image, ImageDraw, ImageFont
import textwrap

# ================= 配置 =================
NEWS_API_KEY = os.environ.get("NEWS_API_KEY")
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY")
DOUBAO_KEY = os.environ.get("DOUBAO_API_KEY")
PUSHPLUS_TOKEN = os.environ.get("PUSHPLUS_TOKEN")

FONT_PATH = "arial.ttf"  # 系统可用字体
IMG_WIDTH = 800
COVER_HEIGHT = 450
NEWS_HEIGHT = 225
CALENDAR_HEIGHT = 450
TITLE_COLOR = "#1a73e8"
TEXT_COLOR = "#333"
COMMENT_BG = "#e0f0ff"
CALENDAR_BG_TOP = "#cce5ff"
CALENDAR_BG_BOTTOM = "#f0f7ff"

BJT = timezone(timedelta(hours=8))

WEEKDAY_MAP = ["一","二","三","四","五","六","日"]
YI_OPTIONS = ["多学习 多思考", "大胆尝试 勇于创新", "独立思考 质疑权威"]
JI_OPTIONS = ["邯郸学步", "拖延症发作", "闭门造车"]

LAST_SUMMARY_FILE = "last_summary.txt"

# ================= 工具函数 =================
def draw_multiline(draw, text, font, x, y, max_width, fill):
    lines = []
    for paragraph in text.split("\n"):
        lines.extend(textwrap.wrap(paragraph, width=max_width))
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += font.getsize(line)[1] + 4
    return y

# ================= 图片生成 =================
def generate_cover_image(title):
    img = Image.new("RGB", (IMG_WIDTH, COVER_HEIGHT), color="#f0f7ff")
    draw = ImageDraw.Draw(img)
    font_title = ImageFont.truetype(FONT_PATH, 48)
    font_sub = ImageFont.truetype(FONT_PATH, 32)
    draw_multiline(draw, title, font_title, 40, 120, 30, TITLE_COLOR)
    draw.text((50, 350), "每日科技观察", font=font_sub, fill=TEXT_COLOR)
    path = "cover_image.png"
    img.save(path)
    return path

def generate_news_card(title, comment, idx):
    img = Image.new("RGB", (IMG_WIDTH, NEWS_HEIGHT), color=COMMENT_BG)
    draw = ImageDraw.Draw(img)
    font_title = ImageFont.truetype(FONT_PATH, 32)
    font_text = ImageFont.truetype(FONT_PATH, 24)
    draw_multiline(draw, title, font_title, 20, 20, 30, TITLE_COLOR)
    draw_multiline(draw, comment, font_text, 20, 100, 40, TEXT_COLOR)
    path = f"news_card_{idx}.png"
    img.save(path)
    return path

def generate_calendar_card(quote, yi=None, ji=None):
    if not yi: yi = random.choice(YI_OPTIONS)
    if not ji: ji = random.choice(JI_OPTIONS)
    img = Image.new("RGB", (IMG_WIDTH, CALENDAR_HEIGHT), color="#fff")
    draw = ImageDraw.Draw(img)
    font_title = ImageFont.truetype(FONT_PATH, 36)
    font_text = ImageFont.truetype(FONT_PATH, 24)
    now = datetime.now(BJT)
    draw.text((30,30), f"{now.month}月{now.day}日", font=font_title, fill="#c0392b")
    draw.text((30,90), f"星期{WEEKDAY_MAP[now.weekday()]}", font=font_text, fill=TEXT_COLOR)
    draw_multiline(draw, f"“{quote}”", font_text, 30, 150, 20, TEXT_COLOR)
    draw.text((30,300), f"宜: {yi}", font_text, fill="#1abc9c")
    draw.text((30,350), f"忌: {ji}", font_text, fill="#e74c3c")
    path = "calendar_card.png"
    img.save(path)
    return path

def combine_images(img_paths, output="final_article.png"):
    images = [Image.open(p) for p in img_paths]
    total_height = sum(img.height for img in images)
    combined = Image.new("RGB", (IMG_WIDTH, total_height), color="#fff")
    y_offset = 0
    for img in images:
        combined.paste(img, (0,y_offset))
        y_offset += img.height
    combined.save(output)
    print(f"公众号最终文章生成: {output}")

# ================= 核心流程 =================
def read_last_summary():
    try:
        with open(LAST_SUMMARY_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return content
    except FileNotFoundError:
        return ""

def save_summary(summary_text):
    with open(LAST_SUMMARY_FILE, "w", encoding="utf-8") as f:
        f.write(summary_text)

# 示例 AI 输出模拟
def get_ai_news():
    return [
        ("OpenAI 发布 GPT-5", "点评：你的工作助手可能更智能，也可能帮你节省很多写作时间。"),
        ("苹果发布新款 MacBook", "点评：对学生和办公族可能更省心，也许你下周就能看到上手体验。")
    ]

# ================= 主流程 =================
def main():
    # 1. 封面图
    cover = generate_cover_image("硅谷过去24小时科技新闻")
    
    # 2. AI 新闻生成
    news_items = get_ai_news()
    news_imgs = [generate_news_card(t,c,i) for i,(t,c) in enumerate(news_items)]
    
    # 3. 日历卡片
    calendar = generate_calendar_card("预测未来的最好方式，就是去创造它。")

    # 4. 拼接最终文章图片
    combine_images([cover]+news_imgs+[calendar])

if __name__ == "__main__":
    main()
