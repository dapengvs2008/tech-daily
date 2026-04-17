import os, json, re, requests, random, subprocess, asyncio
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree
from html.parser import HTMLParser

NEWS_API_KEY   = os.environ["NEWS_API_KEY"]
DEEPSEEK_KEY   = os.environ["DEEPSEEK_API_KEY"]
DOUBAO_KEY     = os.environ["DOUBAO_API_KEY"]
PUSHPLUS_TOKEN = os.environ["PUSHPLUS_TOKEN"]
GITHUB_REPO    = os.environ.get("GITHUB_REPO", "dapengvs2008/tech-daily")

BJT = timezone(timedelta(hours=8))

WEEKDAY_MAP = {
    0: "Monday", 1: "Tuesday", 2: "Wednesday",
    3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday",
}
WEEKDAY_CN = {
    0: "星期一", 1: "星期二", 2: "星期三",
    3: "星期四", 4: "星期五", 5: "星期六", 6: "星期日",
}
YI_OPTIONS = [
    "多学习 多思考", "大胆尝试 勇于创新", "独立思考 质疑权威",
    "专注执行 少刷手机", "跨界探索 打破边界", "复盘总结 持续迭代",
    "阅读论文 拓宽视野", "提出假设 验证想法", "协作共创 开放分享",
]
JI_OPTIONS = [
    "邯郸学步", "盲目跟风", "纸上谈兵",
    "故步自封", "拖延症发作", "闭门造车",
    "过度优化", "完美主义", "只收藏不行动",
]


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.texts = []
        self.skip = False
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'nav', 'header', 'footer', 'aside'):
            self.skip = True
    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'nav', 'header', 'footer', 'aside'):
            self.skip = False
    def handle_data(self, data):
        if not self.skip:
            text = data.strip()
            if len(text) > 20:
                self.texts.append(text)

def extract_text_from_html(html_content, max_chars=2000):
    try:
        parser = TextExtractor()
        parser.feed(html_content)
        return "\n".join(parser.texts)[:max_chars]
    except Exception:
        return ""


def fetch_article_fulltext(url, max_chars=2000):
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            return ""
        return extract_text_from_html(resp.text, max_chars)
    except Exception:
        return ""


def enrich_articles_with_fulltext(articles, max_fetch=12):
    enriched = []
    fetch_count = 0
    for article in articles:
        if fetch_count < max_fetch:
            url_match = re.search(r'链接: (https?://\S+)', article)
            url = url_match.group(1) if url_match else ""
            if url and "news.google.com" not in url:
                fulltext = fetch_article_fulltext(url)
                if fulltext and len(fulltext) > 100:
                    article += f"\n【全文摘要】{fulltext}"
                    fetch_count += 1
                    print(f"    全文抓取成功: {url[:60]}...")
        enriched.append(article)
    return enriched


# ===== 封面模板 =====

COVER_TOPIC_COLORS = ["#1a73e8", "#0f9d58", "#f29900", "#7b1fa2", "#db4437", "#00acc1", "#ff6d00"]

def build_cover_html(main_title, sub_title, topics):
    """生成封面 HTML
    topics: 列表，每个元素是话题短标签（字符串）
    """
    # 分两行显示：前3个 / 后面的
    row1 = topics[:3]
    row2 = topics[3:5] if len(topics) >= 5 else topics[3:]

    def render_tag(text, color):
        return f'''
      <div style="background:#fff;border:1px solid #d0e1f7;padding:9px 14px;border-radius:20px;display:flex;align-items:center;gap:7px;">
        <div style="width:18px;height:18px;background:{color};border-radius:4px;flex-shrink:0;"></div>
        <span style="font-size:13px;color:#0c2340;font-weight:500;white-space:nowrap;">{text}</span>
      </div>'''

    row1_html = "\n".join(render_tag(t, COVER_TOPIC_COLORS[i]) for i, t in enumerate(row1))
    row2_html = "\n".join(render_tag(t, COVER_TOPIC_COLORS[i+3]) for i, t in enumerate(row2))

    return f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
body {{ margin:0; padding:0; font-family: "PingFang SC", "Microsoft YaHei", "Hiragino Sans GB", sans-serif; }}
</style>
</head>
<body>
<div style="width:960px;background:linear-gradient(135deg,#dde8f7 0%,#e8eff9 50%,#f0f4fb 100%);padding:40px 44px;box-sizing:border-box;">

  <div style="display:flex;align-items:center;justify-content:space-between;gap:20px;position:relative;z-index:2;">

    <div style="flex:1;">
      <div style="display:inline-block;background:#3a5783;color:#fff;padding:8px 18px;border-radius:4px;font-size:16px;font-weight:600;letter-spacing:1px;margin-bottom:18px;">过去24小时</div>
      <div style="font-size:44px;font-weight:900;color:#1a2d4f;line-height:1.2;margin:0 0 6px 0;letter-spacing:-1px;">{main_title}</div>
      <div style="font-size:44px;font-weight:900;color:#1a2d4f;line-height:1.2;margin:0;letter-spacing:-1px;">{sub_title}</div>
    </div>

    <div style="width:260px;flex-shrink:0;display:flex;align-items:center;justify-content:center;position:relative;height:180px;">

      <div style="position:absolute;top:0;left:0;width:42px;height:42px;background:#fff;border:2px solid #2563eb;border-radius:50%;display:flex;align-items:center;justify-content:center;z-index:3;">
        <span style="color:#2563eb;font-size:16px;font-weight:900;">&lt;/&gt;</span>
      </div>

      <div style="position:absolute;top:-6px;right:0;width:48px;height:48px;background:#1a2d4f;border-radius:10px;display:flex;align-items:center;justify-content:center;z-index:3;">
        <span style="color:#fff;font-size:18px;font-weight:700;letter-spacing:-0.5px;">AI</span>
      </div>

      <div style="position:absolute;bottom:0;left:0;width:42px;height:42px;background:#fff;border:2px solid #1a2d4f;border-radius:50%;display:flex;align-items:center;justify-content:center;z-index:3;">
        <div style="position:relative;width:22px;height:14px;">
          <div style="position:absolute;top:3px;left:0;width:22px;height:8px;background:#1a2d4f;border-radius:3px;"></div>
          <div style="position:absolute;top:0;left:3px;width:16px;height:7px;background:#1a2d4f;border-radius:3px 3px 0 0;"></div>
          <div style="position:absolute;bottom:-2px;left:2px;width:6px;height:6px;background:#fff;border:1.5px solid #1a2d4f;border-radius:50%;"></div>
          <div style="position:absolute;bottom:-2px;right:2px;width:6px;height:6px;background:#fff;border:1.5px solid #1a2d4f;border-radius:50%;"></div>
        </div>
      </div>

      <div style="position:absolute;bottom:0;right:0;width:42px;height:42px;background:#fff;border:2px solid #1a2d4f;border-radius:50%;display:flex;align-items:center;justify-content:center;z-index:3;">
        <div style="width:18px;height:20px;border:2.5px solid #1a2d4f;border-radius:3px 3px 0 0;border-bottom:none;position:relative;">
          <div style="position:absolute;bottom:-5px;left:-5px;width:23px;height:10px;background:#1a2d4f;border-radius:1px;"></div>
        </div>
      </div>

      <div style="position:relative;width:170px;height:118px;">
        <div style="width:170px;height:108px;background:#1a2d4f;border:4px solid #1a2d4f;border-radius:8px 8px 2px 2px;padding:8px;box-sizing:border-box;">
          <div style="background:#0d1b34;width:100%;height:100%;border-radius:3px;padding:8px 10px;box-sizing:border-box;">
            <div style="display:flex;flex-direction:column;gap:4px;">
              <div style="display:flex;gap:4px;align-items:center;">
                <div style="width:8px;height:3px;background:#ff6b6b;border-radius:1px;"></div>
                <div style="width:18px;height:3px;background:#5dd4b1;border-radius:1px;"></div>
                <div style="width:13px;height:3px;background:#4a90e2;border-radius:1px;"></div>
              </div>
              <div style="display:flex;gap:4px;align-items:center;">
                <div style="width:5px;height:3px;background:#5dd4b1;border-radius:1px;"></div>
                <div style="width:26px;height:3px;background:#4a90e2;border-radius:1px;"></div>
                <div style="width:10px;height:3px;background:#ff6b6b;border-radius:1px;"></div>
              </div>
              <div style="display:flex;gap:4px;align-items:center;">
                <div style="width:13px;height:3px;background:#ffc947;border-radius:1px;"></div>
                <div style="width:16px;height:3px;background:#5dd4b1;border-radius:1px;"></div>
              </div>
              <div style="display:flex;gap:4px;align-items:center;">
                <div style="width:8px;height:3px;background:#ff6b6b;border-radius:1px;"></div>
                <div style="width:10px;height:3px;background:#4a90e2;border-radius:1px;"></div>
                <div style="width:21px;height:3px;background:#5dd4b1;border-radius:1px;"></div>
              </div>
              <div style="display:flex;gap:4px;align-items:center;">
                <div style="width:18px;height:3px;background:#4a90e2;border-radius:1px;"></div>
                <div style="width:8px;height:3px;background:#ffc947;border-radius:1px;"></div>
              </div>
            </div>
            <div style="margin-top:8px;display:flex;align-items:center;gap:4px;">
              <div style="width:3px;height:10px;background:#5dd4b1;"></div>
              <div style="width:16px;height:3px;background:#fff;border-radius:1px;opacity:0.6;"></div>
            </div>
          </div>
        </div>
        <div style="width:184px;height:6px;background:#3a5783;border-radius:0 0 8px 8px;margin-left:-7px;"></div>
      </div>

    </div>
  </div>

  <div style="margin-top:30px;padding-top:24px;border-top:1px dashed #c5d7f0;position:relative;z-index:2;">
    <div style="display:flex;gap:12px;justify-content:center;margin-bottom:12px;">
{row1_html}
    </div>
    <div style="display:flex;gap:12px;justify-content:center;">
{row2_html}
    </div>
  </div>

</div>
</body>
</html>'''


# ===== Playwright 截图 =====

async def render_cover_image(html_content, output_path):
    """用 Playwright 把 HTML 渲染成 PNG 图片"""
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 960, "height": 600}, device_scale_factor=2)
        await page.set_content(html_content, wait_until="networkidle")
        # 自动计算内容高度
        element = await page.query_selector("body > div")
        if element:
            await element.screenshot(path=output_path, type="png")
        else:
            await page.screenshot(path=output_path, type="png", full_page=True)
        await browser.close()


def generate_cover_png(main_title, sub_title, topics, output_path="cover.png"):
    html = build_cover_html(main_title, sub_title, topics)
    try:
        asyncio.run(render_cover_image(html, output_path))
        print(f"  封面图已生成: {output_path}")
        return output_path
    except Exception as e:
        print(f"  封面图生成失败: {e}")
        return None


def commit_image_to_repo(image_path):
    """把图片 commit 到仓库，返回 raw URL"""
    try:
        subprocess.run(["git", "config", "user.name", "Tech Daily Bot"], check=False)
        subprocess.run(["git", "config", "user.email", "bot@tech-daily.com"], check=False)
        subprocess.run(["git", "add", image_path], check=False)
        # 使用时间戳作为提交信息，避免重复
        timestamp = datetime.now(BJT).strftime("%Y-%m-%d %H:%M")
        subprocess.run(["git", "commit", "-m", f"auto: cover image {timestamp}"], check=False)
        subprocess.run(["git", "push"], check=False)
        # 加上时间戳参数避免CDN缓存
        ts = int(datetime.now().timestamp())
        url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{image_path}?t={ts}"
        print(f"  图片已上传: {url}")
        return url
    except Exception as e:
        print(f"  图片上传失败: {e}")
        return None


# ===== 日历卡片 =====

LAST_SUMMARY_FILE = "last_summary.txt"
LAST_QUOTES_FILE = "last_quotes.txt"

def read_recent_quotes():
    try:
        with open(LAST_QUOTES_FILE, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
            print(f"  读取到 {len(lines)} 条历史名言")
            return lines[-7:]
    except FileNotFoundError:
        return []

def save_recent_quote(quote_text, quote_author):
    try:
        existing = read_recent_quotes()
        existing.append(f"{quote_text} —— {quote_author}")
        existing = existing[-7:]
        with open(LAST_QUOTES_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(existing))
        subprocess.run(["git", "add", LAST_QUOTES_FILE], check=False)
        subprocess.run(["git", "commit", "-m", "auto: update last quotes"], check=False)
        subprocess.run(["git", "push"], check=False)
        print(f"  今日名言已记录")
    except Exception as e:
        print(f"  保存名言失败: {e}")


def generate_calendar_card(quote_text="", quote_author=""):
    now = datetime.now(BJT)
    year = now.strftime("%Y")
    month_num = now.month
    month_en = now.strftime("%b").upper()
    day = now.strftime("%d")
    weekday = WEEKDAY_CN[now.weekday()]
    random.seed(now.strftime("%Y%m%d"))
    yi = random.choice(YI_OPTIONS)
    ji = random.choice(JI_OPTIONS)
    if not quote_text:
        quote_text = "预测未来的最好方式，就是去创造它。"
        quote_author = "艾伦·凯（计算机科学家）"

    return f"""
<section style="margin:32px auto 0;max-width:300px;">
<section style="background:#fff;border-radius:12px;overflow:hidden;border:1px solid #e8e8e8;">
<section style="background:#c0392b;padding:10px 18px;display:flex;justify-content:space-between;align-items:center;">
<p style="font-size:13px;font-weight:700;color:#fff;letter-spacing:2px;margin:0;">鹏眼观天下</p>
<p style="font-size:12px;font-weight:700;color:rgba(255,255,255,0.8);margin:0;">{month_num}月 {month_en}</p>
</section>
<section style="padding:28px 18px 20px;text-align:center;background:#fff;">
<p style="font-size:12px;color:#999;letter-spacing:4px;margin:0 0 4px;">{year}</p>
<p style="font-size:64px;font-weight:900;color:#c0392b;line-height:1;margin:4px 0 8px;font-family:Georgia,serif;">{day}</p>
<p style="font-size:14px;color:#666;letter-spacing:6px;margin:0 0 16px;">{weekday}</p>
<section style="display:flex;justify-content:center;gap:20px;margin-bottom:0;">
<p style="font-size:12px;color:#666;margin:0;"><span style="font-size:11px;padding:2px 6px;border-radius:4px;font-weight:700;background:#fef0f0;color:#c0392b;">宜</span> {yi}</p>
<p style="font-size:12px;color:#666;margin:0;"><span style="font-size:11px;padding:2px 6px;border-radius:4px;font-weight:700;background:#f0f0f0;color:#999;">忌</span> {ji}</p>
</section>
</section>
<section style="border-top:1px solid #f0f0f0;padding:18px 18px;background:#fafafa;">
<p style="font-size:13px;color:#333;line-height:1.8;text-align:center;margin:0 0 8px;">"{quote_text}"</p>
<p style="font-size:11px;color:#666;text-align:center;margin:0;">—— {quote_author}</p>
</section>
<section style="padding:8px 18px;display:flex;justify-content:space-between;font-size:10px;color:#999;">
<p style="margin:0;">鹏眼观天下</p>
<p style="margin:0;">全球视野 / 科技洞察</p>
</section>
</section>
</section>
"""


DISCLAIMER = """
<section style="margin-top:20px;padding:14px 16px;background:#f9f9f9;border-radius:6px;">
<p style="font-size:12px;color:#999;line-height:1.8;margin:0;">
<span style="color:#888;font-weight:bold;">免责声明</span><br/>
本文素材来源于路透社、彭博社、TechCrunch、The Verge、Hacker News、CNBC等国际主流科技媒体及网络公开报道，经AI辅助整理并由人工编辑审核。本文不代表任何立场，不构成任何投资建议。如有疏漏，欢迎留言指正。
</p>
</section>
"""


def read_last_summary():
    try:
        with open(LAST_SUMMARY_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                print(f"  读取到昨日总结 ({len(content)} 字)")
                return content
    except FileNotFoundError:
        pass
    print("  无昨日总结")
    return ""

def save_summary(summary_text):
    try:
        with open(LAST_SUMMARY_FILE, "w", encoding="utf-8") as f:
            f.write(summary_text)
        subprocess.run(["git", "add", LAST_SUMMARY_FILE], check=False)
        subprocess.run(["git", "commit", "-m", "auto: update last summary"], check=False)
        subprocess.run(["git", "push"], check=False)
        print(f"  今日总结已保存")
    except Exception as e:
        print(f"  保存总结失败: {e}")

def extract_summary_from_html(html_text):
    match = re.search(r'三句话说清楚</p>(.*?)</section>', html_text, re.DOTALL)
    if match:
        return re.sub(r'<[^>]+>', '', match.group(1)).strip()
    return ""


def get_time_range():
    now_bjt = datetime.now(BJT)
    end_time = now_bjt.replace(hour=6, minute=0, second=0, microsecond=0)
    if now_bjt.hour < 6:
        end_time -= timedelta(days=1)
    start_time = end_time - timedelta(hours=24)
    return start_time, end_time


def fetch_google_news():
    queries = [
        "AI+artificial+intelligence+OpenAI+Anthropic+when:1d",
        "Apple+OR+Google+OR+Nvidia+OR+Tesla+OR+Microsoft+OR+Meta+tech+when:1d",
        "Silicon+Valley+startup+funding+OR+acquisition+when:1d",
    ]
    all_articles = []
    seen_titles = set()
    for q in queries:
        url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
        try:
            resp = requests.get(url, timeout=15)
            root = ElementTree.fromstring(resp.content)
            for item in root.findall(".//item")[:8]:
                title = item.find("title").text or ""
                if title in seen_titles:
                    continue
                seen_titles.add(title)
                source = item.find("source").text if item.find("source") is not None else "unknown"
                pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
                link = item.find("link").text if item.find("link") is not None else ""
                desc = item.find("description").text if item.find("description") is not None else ""
                all_articles.append(f"[Google News] 来源: {source}\n标题: {title}\n时间: {pub_date}\n链接: {link}\n描述: {desc}")
        except Exception as e:
            print(f"Google News 失败({q}): {e}")
    print(f"Google News: {len(all_articles)} 条")
    return all_articles


def fetch_newsapi():
    start_time, end_time = get_time_range()
    try:
        resp = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": "(AI OR OpenAI OR Google OR Apple OR Nvidia OR Tesla OR Microsoft OR Meta OR startup OR funding) AND (launch OR release OR announce OR deal OR billion OR update)",
                "from": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
                "to": end_time.strftime("%Y-%m-%dT%H:%M:%S"),
                "language": "en", "sortBy": "relevancy", "pageSize": 10,
                "apiKey": NEWS_API_KEY,
            },
            timeout=15,
        )
        data = resp.json()
        if data.get("status") != "ok":
            print(f"NewsAPI 错误: {data}")
            return []
        articles = []
        for a in data.get("articles", []):
            if a.get("description"):
                source = a.get("source", {}).get("name", "unknown")
                article_url = a.get("url", "")
                articles.append(f"[NewsAPI] 来源: {source}\n标题: {a['title']}\n链接: {article_url}\n摘要: {a['description']}\n片段: {(a.get('content') or '')[:400]}")
        print(f"NewsAPI: {len(articles)} 条")
        return articles
    except Exception as e:
        print(f"NewsAPI 失败: {e}")
        return []


def fetch_hackernews():
    try:
        resp = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=15)
        story_ids = resp.json()[:20]
        articles = []
        tech_kw = ["ai", "gpt", "llm", "openai", "google", "apple", "nvidia", "tesla",
                   "microsoft", "meta", "startup", "funding", "chip", "robot", "model",
                   "launch", "release", "billion", "acquisition", "open source",
                   "anthropic", "gemini", "claude", "copilot", "agent", "autonomous"]
        for sid in story_ids:
            try:
                item = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json", timeout=10).json()
                if not item or item.get("type") != "story":
                    continue
                title = item.get("title", "")
                score = item.get("score", 0)
                url = item.get("url", "")
                if score >= 100 or any(kw in title.lower() for kw in tech_kw):
                    domain = url.split("/")[2] if url and "/" in url else "news.ycombinator.com"
                    articles.append(f"[Hacker News] 来源: {domain}\n标题: {title}\n热度: {score}分\n链接: {url}")
                if len(articles) >= 8:
                    break
            except Exception:
                continue
        print(f"Hacker News: {len(articles)} 条")
        return articles
    except Exception as e:
        print(f"Hacker News 失败: {e}")
        return []


def fetch_techcrunch_rss():
    try:
        resp = requests.get("https://techcrunch.com/feed/", timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        root = ElementTree.fromstring(resp.content)
        articles = []
        for item in root.findall(".//item")[:10]:
            title = item.find("title").text or ""
            pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
            link = item.find("link").text if item.find("link") is not None else ""
            desc = re.sub(r'<[^>]+>', '', item.find("description").text or "")[:300] if item.find("description") is not None else ""
            articles.append(f"[TechCrunch] 来源: TechCrunch\n标题: {title}\n时间: {pub_date}\n链接: {link}\n描述: {desc}")
        print(f"TechCrunch: {len(articles)} 条")
        return articles
    except Exception as e:
        print(f"TechCrunch 失败: {e}")
        return []


def deepseek_draft(news_text, last_summary="", recent_quotes=None):
    start_time, end_time = get_time_range()
    date_range = f"{start_time.strftime('%m月%d日 %H:%M')} ~ {end_time.strftime('%m月%d日 %H:%M')}（北京时间）"

    continuity = ""
    if last_summary:
        continuity = f"""
【连续追踪】昨天的简报结尾提到：
---
{last_summary}
---
如果今天的新闻里有昨天提到的内容的进展，请在对应新闻中自然提一句"昨天我们提到的XXX，今天有了新进展——"。
"""

    quotes_avoid = ""
    if recent_quotes:
        quotes_avoid = f"""
【名言去重】最近7天已经用过以下名言，请务必避开这些，推荐一句完全不同的：
{chr(10).join("- " + q for q in recent_quotes)}
"""

    prompt = f"""你是一位资深且极其严谨的科技记者。请根据以下新闻素材整理科技日报初稿。

时间窗口：{date_range}
{continuity}
{quotes_avoid}

## 第一原则：准确性高于一切

**宁可少写，不可写错。** 具体要求：

1. **只写原文明确说了的事**——如果原文只说了A，你不能推断出B
2. **看不懂就跳过**——仅有标题没有全文摘要且内容不明确的，直接跳过
3. **特别注意易混淆场景**：
   - "产品有漏洞" vs "产品能发现别人的漏洞"
   - "被起诉" vs "起诉别人"
   - "限制发布" vs "停止开发"
   - "计划" vs "已经"
4. **数据必须谨慎**——具体金额、百分比必须在原文找到对应

## 写作要求

1. 筛选 5-7 条有全文摘要支持的重要新闻
2. 同一事件合并
3. 按重要性排列
4. 每条包含：
   - 标题（事实陈述型，不夸张）
   - 事实描述（3-5句话，基于全文摘要展开细节）
   - 点评（2-3句话，有观点有分析，告诉读者和普通人的关系）
5. 不要使用任何emoji图标
6. 正文中不要写"据XX报道"，直接陈述事实
7. 开头写总标题（平实但吸引人，不要"炸锅""震惊""疯了"这类词）
8. 开头写1-2句引言概括今天核心看点
9. 结尾三句话总结：每句 2-3 行
10. 最后单独一行输出名人名言，格式：今日名言：内容——作者（身份）

**额外输出：为今天的简报生成 5 个短话题标签**（4-8个汉字），格式：
今日标签：标签1 | 标签2 | 标签3 | 标签4 | 标签5

标签要求：每个标签精炼概括一条新闻的核心，便于读者一眼看懂。

来源翻译：TechCrunch→TechCrunch, Bloomberg→彭博社, Reuters→路透社, CNBC→CNBC, WSJ→华尔街日报, Hacker News→Hacker News

用纯文本输出，不要HTML标签，不要emoji。

新闻素材：
{news_text}"""

    try:
        resp = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"},
            json={"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "max_tokens": 4500},
            timeout=120,
        )
        data = resp.json()
        if "choices" not in data:
            print(f"DeepSeek 错误: {data}")
            return None, "", "", []
        draft = data["choices"][0]["message"]["content"]
        print(f"DeepSeek 初稿生成完成 ({len(draft)} 字)")

        # 提取名言
        quote_text = ""
        quote_author = ""
        quote_match = re.search(r'今日名言[：:]\s*(.+?)——(.+)', draft)
        if quote_match:
            quote_text = quote_match.group(1).strip().strip('"').strip('\u201c').strip('\u201d')
            quote_author = quote_match.group(2).strip().split("\n")[0].strip()
            print(f"  今日名言: {quote_text} —— {quote_author}")
            draft = re.sub(r'今日名言[：:].*', '', draft).strip()

        # 提取标签
        topics = []
        tag_match = re.search(r'今日标签[：:]\s*(.+)', draft)
        if tag_match:
            tag_line = tag_match.group(1).strip().split("\n")[0]
            topics = [t.strip() for t in re.split(r'[|｜丨]', tag_line) if t.strip()]
            topics = topics[:5]
            print(f"  今日标签: {topics}")
            draft = re.sub(r'今日标签[：:].*', '', draft).strip()

        return draft, quote_text, quote_author, topics
    except Exception as e:
        print(f"DeepSeek 请求失败: {e}")
        return None, "", "", []


def deepseek_factcheck(draft, news_text):
    prompt = f"""你是严格的事实核查编辑。对照原始素材，找出初稿中不准确、夸大或推断过头的地方，输出修正后的完整初稿。

## 检查重点
1. 每条核心事实是否在原文中有对应
2. 是否混淆"有漏洞"和"能发现漏洞"这类关键词
3. 具体数据是否和原文一致
4. 是否把"可能"改成了"确定"
5. 是否添加了原文没有的因果关系

## 修改原则
- 发现事实错误：直接改正
- 发现夸大描述：改为准确措辞
- 发现无法核实的：整条删除

直接输出修正后的完整初稿，保持原有格式。

---

## 原始新闻素材
{news_text[:12000]}

---

## 待核查初稿
{draft}"""

    try:
        resp = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"},
            json={"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "max_tokens": 4000},
            timeout=120,
        )
        data = resp.json()
        if "choices" not in data:
            return draft
        corrected = data["choices"][0]["message"]["content"]
        print(f"  事实核查完成 ({len(corrected)} 字)")
        return corrected
    except Exception as e:
        print(f"  事实核查失败: {e}")
        return draft


def doubao_polish(draft):
    prompt = f"""你是"鹏眼观天下"公众号主编。把已核查的初稿改写成面向科技小白的公众号文章。

## 最高原则：事实零改动
- 初稿说的所有事实一字不能改
- 初稿用的"据报道""可能"等措辞必须保留
- 不能加原文没有的事情

你可以做的：
- 换更通俗的表达
- 给专业名词加括号解释（如："Anthropic（做Claude的公司，ChatGPT最大对手）"）
- 用生活化类比
- 增强开头钩子（用初稿已有的事实制造悬念）
- 保证内容充实（1500-2500字），不要删减事实细节

## 排版（微信公众号兼容HTML，内联样式，不要emoji）

总标题：
<p style="font-size:22px;font-weight:900;color:#1a1a1a;line-height:1.4;margin:0 0 20px;">总标题</p>

引言：
<section style="background:#f0f7ff;padding:14px 16px;border-left:4px solid #1a73e8;margin-bottom:28px;">
<p style="font-size:16px;color:#333;line-height:1.9;margin:0;">引言</p>
</section>

每条新闻：
<section style="margin-bottom:8px;">
<p style="font-size:18px;font-weight:bold;color:#1a73e8;line-height:1.5;margin:0 0 10px;">标题</p>
<p style="font-size:16px;color:#333;line-height:1.9;margin:0 0 10px;">正文</p>
<section style="background:#f0f7ff;padding:10px 14px;border-radius:6px;margin:0 0 8px;">
<p style="font-size:15px;color:#555;line-height:1.9;margin:0;">鹏眼点评</p>
</section>
</section>
<p style="border-top:1px solid #eee;margin:24px 0;height:0;"></p>

结尾：
<section style="background:#e8f0fe;padding:18px;border-radius:8px;margin-top:28px;">
<p style="font-size:18px;font-weight:bold;color:#1a73e8;margin:0 0 12px;">今天的科技圈，三句话说清楚</p>
<p style="font-size:15px;color:#555;line-height:1.9;margin:0 0 10px;">1. 最重要的一件事：xxxx</p>
<p style="font-size:15px;color:#555;line-height:1.9;margin:0 0 10px;">2. 钱往哪儿流：xxxx</p>
<p style="font-size:15px;color:#555;line-height:1.9;margin:0;">3. 接下来看什么：xxxx</p>
</section>

## 禁止
- 代码块、markdown加粗、h1/h2/h3、div标签、emoji、斜体
- 添加初稿没有的事实
- 正文标注新闻来源
- 标题用"炸锅""震惊"等浮夸词

初稿（已核查）：
{draft}"""

    try:
        resp = requests.post(
            "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
            headers={"Authorization": f"Bearer {DOUBAO_KEY}", "Content-Type": "application/json"},
            json={"model": "doubao-seed-2-0-pro-260215", "messages": [{"role": "user", "content": prompt}], "max_tokens": 6000},
            timeout=180,
        )
        data = resp.json()
        if "choices" not in data:
            print(f"豆包错误: {data}")
            return None
        result = data["choices"][0]["message"]["content"]
        print(f"豆包润色完成 ({len(result)} 字)")
        return result
    except Exception as e:
        print(f"豆包请求失败: {e}")
        return None


def clean_response(text):
    text = re.sub(r'```html\s*', '', text)
    text = re.sub(r'```\s*$', '', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'<h3[^>]*>(.*?)</h3>',
        r'<p style="font-size:18px;font-weight:bold;color:#1a73e8;line-height:1.5;margin:20px 0 10px;">\1</p>', text)
    text = re.sub(r'<hr[^>]*/?>',
        '<p style="border-top:1px solid #eee;margin:24px 0;height:0;"></p>', text)
    return text.strip()


def extract_main_subtitle(html_text):
    """从正文提取主副标题，用于封面"""
    match = re.search(r'font-size:22px[^>]*>(.*?)</p>', html_text)
    if match:
        title = re.sub(r'<[^>]+>', '', match.group(1)).strip()
        # 尝试拆分为主副标题
        for sep in ['，', '：', ' - ', '——', '：']:
            if sep in title:
                parts = title.split(sep, 1)
                return parts[0].strip(), parts[1].strip()
        # 没有分隔符，按长度拆分
        if len(title) > 10:
            mid = len(title) // 2
            return title[:mid], title[mid:]
        return title, "过去24小时精华"
    return "全球科技圈", "过去24小时精华"


def send_pushplus(title, content):
    resp = requests.post(
        "http://www.pushplus.plus/send",
        json={"token": PUSHPLUS_TOKEN, "title": title, "content": content, "template": "html"},
        timeout=15,
    )
    result = resp.json()
    if result.get("code") == 200:
        print("推送成功!")
    else:
        print(f"推送失败: {result}")


if __name__ == "__main__":
    now_bjt = datetime.now(BJT)
    today = now_bjt.strftime("%Y年%m月%d日")
    title = f"硅谷过去24小时发生了什么？| {today}"

    start_time, end_time = get_time_range()
    print(f"时间窗口: {start_time.strftime('%Y-%m-%d %H:%M')} ~ {end_time.strftime('%Y-%m-%d %H:%M')} BJT")

    print("=== 0/8 读取历史记录 ===")
    last_summary = read_last_summary()
    recent_quotes = read_recent_quotes()

    print("=== 1/8 抓取新闻 ===")
    print("  Google News...")
    google_articles = fetch_google_news()
    print("  NewsAPI...")
    newsapi_articles = fetch_newsapi()
    print("  Hacker News...")
    hn_articles = fetch_hackernews()
    print("  TechCrunch...")
    tc_articles = fetch_techcrunch_rss()

    all_articles = google_articles + newsapi_articles + hn_articles + tc_articles

    if not all_articles:
        send_pushplus(title, "<p>今日暂无重大科技动态。</p>")
        print("无新闻，已发送空报")
    else:
        print(f"  共 {len(all_articles)} 条新闻")

        print("=== 2/8 抓取新闻全文 ===")
        all_articles = enrich_articles_with_fulltext(all_articles, max_fetch=12)
        news_text = "\n\n".join(all_articles)

        print("=== 3/8 DeepSeek 生成初稿（严格模式） ===")
        draft, quote_text, quote_author, topics = deepseek_draft(news_text, last_summary, recent_quotes)

        if draft:
            print("=== 4/8 事实核查 ===")
            draft = deepseek_factcheck(draft, news_text)

            print("=== 5/8 豆包润色+排版 ===")
            polished = doubao_polish(draft)

            if polished:
                final = clean_response(polished)
            else:
                final = f"<p style='color:#999;font-size:12px;'>（初稿版本）</p>\n{draft}"
        else:
            final = "<p>AI 摘要生成失败。</p>"
            quote_text = ""
            quote_author = ""
            topics = []

        # 生成封面图
        print("=== 6/8 生成封面图 ===")
        main_title, sub_title = extract_main_subtitle(final)
        # 如果有标签就用，没有就用默认
        if not topics:
            topics = ["OpenAI动态", "AI竞争升级", "芯片与算力", "资本风向", "新技术落地"]
        print(f"  主标题: {main_title} / {sub_title}")
        print(f"  话题标签: {topics}")
        cover_path = generate_cover_png(main_title, sub_title, topics, "cover.png")
        cover_url = None
        if cover_path:
            cover_url = commit_image_to_repo(cover_path)
        if cover_url:
            cover_html = f'<section style="margin-bottom:28px;"><img src="{cover_url}" style="width:100%;border-radius:8px;" /></section>'
            final = cover_html + final
            print("  封面图已插入文章开头")
        else:
            print("  封面图生成失败，跳过")

        print("=== 7/8 生成日历卡片 ===")
        calendar = generate_calendar_card(quote_text, quote_author)
        final = final + calendar + DISCLAIMER

        print("=== 8/8 推送微信 ===")
        send_pushplus(title, final)

        # 保存历史
        print("=== 保存历史数据 ===")
        today_summary = extract_summary_from_html(final)
        if today_summary:
            save_summary(today_summary)
        if quote_text:
            save_recent_quote(quote_text, quote_author)

    print("全部完成!")
