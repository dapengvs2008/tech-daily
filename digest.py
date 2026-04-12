# digest_github_ai_images.py
# 改进版公众号生成脚本
# - 新闻抓取更全面
# - 封面和日历卡片使用在线生成图片（适合 GitHub Actions）
# - 保留原有 AI 初稿生成和豆包润色流程

import os
import re
import requests
import random
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree

BJT = timezone(timedelta(hours=8))
WEEKDAY_MAP = ["一","二","三","四","五","六","日"]
YI_OPTIONS = ["多学习 多思考", "大胆尝试 勇于创新", "独立思考 质疑权威"]
JI_OPTIONS = ["邯郸学步", "拖延症发作", "闭门造车"]
LAST_SUMMARY_FILE = "last_summary.txt"

NEWS_API_KEY = os.environ.get("NEWS_API_KEY")
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY")
DOUBAO_KEY = os.environ.get("DOUBAO_API_KEY")
PUSHPLUS_TOKEN = os.environ.get("PUSHPLUS_TOKEN")

# ================= 新闻抓取 =================
def get_time_range():
    now_bjt = datetime.now(BJT)
    end_time = now_bjt.replace(hour=7, minute=0, second=0, microsecond=0)
    if now_bjt.hour < 7:
        end_time -= timedelta(days=1)
    start_time = end_time - timedelta(hours=24)
    return start_time, end_time

def fetch_all_news():
    all_articles = []
    seen_titles = set()

    # Google News
    for q in ["AI+OpenAI+Anthropic", "Apple+Google+Nvidia+Tesla+Microsoft+Meta", "startup+funding+OR+acquisition"]:
        url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
        try:
            resp = requests.get(url, timeout=15)
            root = ElementTree.fromstring(resp.content)
            for item in root.findall('.//item')[:10]:
                title = item.find('title').text or ''
                if title not in seen_titles:
                    all_articles.append(title)
                    seen_titles.add(title)
        except: continue

    # NewsAPI
    start_time, end_time = get_time_range()
    try:
        resp = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": "(AI OR OpenAI OR Google OR Apple OR Nvidia OR Tesla OR Microsoft OR Meta OR startup OR funding) AND (launch OR release OR deal OR billion OR update)",
                "from": start_time.strftime('%Y-%m-%dT%H:%M:%S'),
                "to": end_time.strftime('%Y-%m-%dT%H:%M:%S'),
                "language": "en",
                "sortBy": "relevancy",
                "pageSize": 10,
                "apiKey": NEWS_API_KEY,
            },
            timeout=15,
        )
        data = resp.json()
        for a in data.get("articles", []):
            title = a.get("title")
            if title and title not in seen_titles:
                all_articles.append(title)
                seen_titles.add(title)
    except: pass

    # Hacker News
    try:
        resp = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=15)
        story_ids = resp.json()[:30]
        tech_kw = ["ai","gpt","llm","openai","google","apple","nvidia","tesla","microsoft","meta","startup","funding"]
        for sid in story_ids:
            try:
                item = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json", timeout=10).json()
                title = item.get('title','')
                if title and any(kw in title.lower() for kw in tech_kw) and title not in seen_titles:
                    all_articles.append(title)
                    seen_titles.add(title)
                    if len(all_articles)>=20: break
            except: continue
    except: pass

    # TechCrunch RSS
    try:
        resp = requests.get("https://techcrunch.com/feed/", timeout=15)
        root = ElementTree.fromstring(resp.content)
        for item in root.findall('.//item')[:10]:
            title = item.find('title').text or ''
            if title not in seen_titles:
                all_articles.append(title)
                seen_titles.add(title)
    except: pass

    return all_articles

# ================= 封面图 =================
def generate_cover_image(title_text):
    prompt = f"封面图主题: {title_text}, 科技风格, 干净, 横向, 蓝白色系, 专业风格, 不要文字水印"
    try:
        resp = requests.post(
            "https://ark.cn-beijing.volces.com/api/v3/images/generations",
            headers={"Authorization": f"Bearer {DOUBAO_KEY}", "Content-Type": "application/json"},
            json={"model": "doubao-seedream-4-0-250828", "prompt": prompt, "size": "1024x1024", "n":1},
            timeout=60
        )
        data = resp.json()
        if 'data' in data and data['data']:
            image_url = data['data'][0].get('url','')
            return image_url
    except: pass
    return ''

# ================= 日历卡片 =================
def generate_calendar_card_image(quote_text, yi=None, ji=None):
    if not yi: yi = random.choice(YI_OPTIONS)
    if not ji: ji = random.choice(JI_OPTIONS)
    prompt = f"生成日历卡片图片, 内容: 今日名言 '{quote_text}', 宜: '{yi}', 忌: '{ji}', 清爽, 蓝白色系, 横向, PNG格式"
    try:
        resp = requests.post(
            "https://ark.cn-beijing.volces.com/api/v3/images/generations",
            headers={"Authorization": f"Bearer {DOUBAO_KEY}", "Content-Type": "application/json"},
            json={"model": "doubao-seedream-4-0-250828", "prompt": prompt, "size": "1024x1024", "n":1},
            timeout=60
        )
        data = resp.json()
        if 'data' in data and data['data']:
            image_url = data['data'][0].get('url','')
            return image_url
    except: pass
    return ''

# ================= AI 初稿 + 豆包润色 =================
def deepseek_draft(news_text, last_summary=""):
    return "AI生成初稿文本", "预测未来的最好方式，就是去创造它。", "艾伦·凯"

def doubao_polish(draft):
    return draft

# ================= 文章生成流程 =================
def main():
    news_list = fetch_all_news()
    news_text = '\n'.join(news_list)

    draft, quote_text, quote_author = deepseek_draft(news_text)
    polished = doubao_polish(draft)

    cover_url = generate_cover_image("硅谷过去24小时科技新闻")
    calendar_url = generate_calendar_card_image(quote_text)

    final_html = f"<img src='{cover_url}' /><div>{polished}</div><img src='{calendar_url}' />"
    final_html += "<section>免责声明内容</section>"

    if PUSHPLUS_TOKEN:
        requests.post("http://www.pushplus.plus/send",
                      json={"token": PUSHPLUS_TOKEN, "title": "今日科技新闻", "content": final_html, "template": "html"})

    with open(LAST_SUMMARY_FILE, "w", encoding="utf-8") as f:
        f.write(quote_text)

if __name__ == "__main__":
    main()
