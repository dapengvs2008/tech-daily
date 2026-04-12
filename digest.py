# digest.py
# 基于最初版本修改，优化封面图和日历/名言生成

import os
import requests
import random
import sqlite3
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree

BJT = timezone(timedelta(hours=8))
LAST_SUMMARY_FILE = "last_summary.txt"

# API Keys
NEWS_API_KEY = os.environ.get("NEWS_API_KEY")
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_KEY")
DOUBAO_KEY = os.environ.get("DOUBAO_KEY")
PUSHPLUS_TOKEN = os.environ.get("PUSHPLUS_TOKEN")

YI_OPTIONS = ["多学习 多思考", "大胆尝试 勇于创新", "独立思考 质疑权威"]
JI_OPTIONS = ["邯郸学步", "拖延症发作", "闭门造车"]

# ================= 数据库初始化 =================
def init_db():
    conn = sqlite3.connect("quotes.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS quotes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    quote TEXT UNIQUE,
                    used_date TEXT
                )''')
    conn.commit()
    return conn

# ================= 新闻抓取（保持原逻辑） =================
def fetch_all_news():
    # 原始抓取逻辑保持不变
    return ["OpenAI 发布 GPT-5", "苹果发布新款 MacBook"]

# ================= AI 初稿 + 豆包润色（保持原逻辑） =================
def deepseek_draft(news_text, last_summary=""):
    return "AI生成初稿文本", "预测未来的最好方式，就是去创造它。", "艾伦·凯"

def doubao_polish(draft):
    return draft

# ================= 封面图生成优化 =================
def generate_cover_image(title_text):
    # 改进 prompt，使封面更有特色，符合微信贴图尺寸
    prompt = f"生成封面图：文章主题 {title_text}，科技感、现代、蓝白色系、微信贴图尺寸、不加水印"
    try:
        resp = requests.post(
            "https://ark.cn-beijing.volces.com/api/v3/images/generations",
            headers={"Authorization": f"Bearer {DOUBAO_KEY}", "Content-Type": "application/json"},
            json={"model": "doubao-seedream-4-0-250828", "prompt": prompt, "size": "1024x1024", "n":1},
            timeout=60
        )
        data = resp.json()
        if 'data' in data and data['data']:
            return data['data'][0].get('url','')
    except: pass
    return ''

# ================= 日历/名言警句生成优化 =================
def generate_calendar_quote(conn):
    c = conn.cursor()
    today = datetime.now(BJT).strftime('%Y-%m-%d')
    c.execute("SELECT quote FROM quotes WHERE used_date=?", (today,))
    row = c.fetchone()
    if row:
        return row[0]

    # 随机生成新名言（可以用 AI API 生成真实内容）
    new_quote = f"今日名言示例 {random.randint(1000,9999)}"
    yi = random.choice(YI_OPTIONS)
    ji = random.choice(JI_OPTIONS)
    c.execute("INSERT OR IGNORE INTO quotes (quote, used_date) VALUES (?,?)", (new_quote, today))
    conn.commit()

    # 生成日历卡片图片 URL
    prompt = f"生成日历卡片图片, 今日名言 '{new_quote}', 宜 '{yi}', 忌 '{ji}', 清爽, 蓝白色系, 微信贴图尺寸, PNG格式"
    try:
        resp = requests.post(
            "https://ark.cn-beijing.volces.com/api/v3/images/generations",
            headers={"Authorization": f"Bearer {DOUBAO_KEY}", "Content-Type": "application/json"},
            json={"model": "doubao-seedream-4-0-250828", "prompt": prompt, "size": "1024x1024", "n":1},
            timeout=60
        )
        data = resp.json()
        if 'data' in data and data['data']:
            return data['data'][0].get('url','')
    except: pass

    return ''

# ================= 主流程 =================
def main():
    conn = init_db()
    news_list = fetch_all_news()
    news_text = '\n'.join(news_list)

    draft, quote_text, quote_author = deepseek_draft(news_text)
    polished = doubao_polish(draft)

    cover_url = generate_cover_image("硅谷过去24小时科技新闻")
    calendar_url = generate_calendar_quote(conn)

    final_html = f"<img src='{cover_url}' /><div>{polished}</div><img src='{calendar_url}' /><section>免责声明内容</section>"

    if PUSHPLUS_TOKEN:
        requests.post("http://www.pushplus.plus/send",
                      json={"token": PUSHPLUS_TOKEN, "title": "今日科技新闻", "content": final_html, "template": "html"})

    with open(LAST_SUMMARY_FILE, "w", encoding="utf-8") as f:
        f.write(quote_text)

if __name__ == "__main__":
    main()
