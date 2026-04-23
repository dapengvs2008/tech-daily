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

        # 先拉取最新代码，避免冲突
        pull_result = subprocess.run(["git", "pull", "--rebase"], capture_output=True, text=True)
        if pull_result.returncode != 0:
            print(f"  git pull 失败: {pull_result.stderr}")

        # 添加图片
        add_result = subprocess.run(["git", "add", image_path], capture_output=True, text=True)
        if add_result.returncode != 0:
            print(f"  git add 失败: {add_result.stderr}")
            return None

        # 提交
        timestamp = datetime.now(BJT).strftime("%Y-%m-%d %H:%M")
        commit_result = subprocess.run(
            ["git", "commit", "-m", f"auto: cover image {timestamp}"],
            capture_output=True, text=True
        )
        if commit_result.returncode != 0:
            print(f"  git commit 结果: {commit_result.stdout} {commit_result.stderr}")
            # 可能是没变化（nothing to commit），也算成功
            if "nothing to commit" not in commit_result.stdout:
                return None

        # 推送
        push_result = subprocess.run(["git", "push"], capture_output=True, text=True)
        if push_result.returncode != 0:
            print(f"  git push 失败: {push_result.stderr}")
            return None

        print(f"  git push 成功")
        ts = int(datetime.now().timestamp())
        url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{image_path}?t={ts}"
        print(f"  图片URL: {url}")
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


def _get_lunar_text(dt):
    """获取农历文字：'丙午年 · 马年 · 农历三月初七'。失败时返回空字符串。"""
    try:
        from lunar_python import Solar
        s = Solar.fromYmd(dt.year, dt.month, dt.day)
        l = s.getLunar()
        return f"{l.getYearInGanZhi()}年 · {l.getYearShengXiao()}年 · 农历{l.getMonthInChinese()}月{l.getDayInChinese()}"
    except Exception as e:
        print(f"  农历计算失败（非致命）: {e}")
        return ""


def generate_calendar_card(quote_text="", quote_author=""):
    now = datetime.now(BJT)
    year = now.strftime("%Y")
    month_cn_map = {1:"一月",2:"二月",3:"三月",4:"四月",5:"五月",6:"六月",
                    7:"七月",8:"八月",9:"九月",10:"十月",11:"十一月",12:"十二月"}
    month_cn = month_cn_map[now.month]
    month_en = now.strftime("%b") + "."  # Apr.
    day = now.strftime("%d").lstrip("0") or "0"
    weekday = WEEKDAY_CN[now.weekday()]
    lunar_text = _get_lunar_text(now)

    random.seed(now.strftime("%Y%m%d"))
    yi = random.choice(YI_OPTIONS)
    ji = random.choice(JI_OPTIONS)
    if not quote_text:
        quote_text = "预测未来的最好方式，就是去创造它。"
        quote_author = "艾伦·凯（计算机科学家）"

    # 颜色体系
    RED_MAIN = "#c0392b"   # 双线边框色
    RED_BLOCK = "#a02820"  # 顶部/底部红块填充色（稍深一档）
    PAPER = "#faf6ee"      # 米白纸底

    # 农历行（如果农历库不可用，这一行隐藏）
    lunar_html = ""
    if lunar_text:
        lunar_html = f'<p style="text-align:center;font-size:10px;color:#3e3e3e;font-weight:500;letter-spacing:1px;margin:0 0 14px;">{lunar_text}</p>'

    # 构造 HTML（微信兼容：全部 <section>/<p> + 内联样式）
    # 结构：wrap → outer-red → inner-gap → inner-red → content → 顶部红块/正文/底部红块
    return f"""
<section style="margin:32px auto 0;max-width:290px;">
<section style="background:{PAPER};padding:10px;box-sizing:border-box;box-shadow:0 2px 6px rgba(0,0,0,0.06),0 10px 30px rgba(0,0,0,0.1);">
<section style="background:{RED_MAIN};padding:2px;">
<section style="background:{PAPER};padding:5px;">
<section style="background:{RED_MAIN};padding:1px;">
<section style="background:{PAPER};">

<section style="display:flex;justify-content:space-between;align-items:center;padding:9px 16px;background:{RED_BLOCK};">
<p style="font-size:11px;color:#fff;font-weight:700;letter-spacing:1px;margin:0;">{year}</p>
<p style="font-size:12px;color:#fff;font-weight:700;letter-spacing:2px;margin:0;text-align:center;flex:1;">鹏眼观天下</p>
<p style="font-size:11px;color:#fff;font-weight:700;letter-spacing:1px;margin:0;">{month_cn}</p>
</section>

<section style="padding:6px 20px 8px;">
<section style="display:flex;align-items:flex-start;gap:2px;">
<span style="font-family:Georgia,'Times New Roman',serif;font-size:22px;font-style:italic;color:{RED_MAIN};font-weight:400;margin-top:14px;line-height:1;">{month_en}</span>
<span style="font-family:Georgia,serif;font-size:22px;color:{RED_MAIN};font-weight:300;margin-top:14px;margin-left:2px;margin-right:4px;line-height:1;">/</span>
<span style="font-family:Georgia,'Times New Roman',serif;font-size:96px;font-weight:900;color:{RED_MAIN};line-height:0.92;letter-spacing:-4px;">{day}</span>
</section>
<p style="text-align:center;font-size:17px;font-weight:700;color:#2c2c2c;letter-spacing:8px;margin:6px 0 4px;">{weekday}</p>
{lunar_html}
</section>

<section style="height:1px;background:{RED_MAIN};margin:0 16px;"></section>

<section style="display:flex;justify-content:center;gap:22px;padding:10px 12px;">
<p style="display:flex;align-items:center;gap:6px;font-size:13px;color:#2c2c2c;font-weight:600;margin:0;">
<span style="display:inline-flex;width:20px;height:20px;border-radius:50%;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:#fff;background:{RED_MAIN};">宜</span>
{yi}
</p>
<p style="display:flex;align-items:center;gap:6px;font-size:13px;color:#2c2c2c;font-weight:600;margin:0;">
<span style="display:inline-flex;width:20px;height:20px;border-radius:50%;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:#fff;background:#2c2c2c;">忌</span>
{ji}
</p>
</section>

<section style="height:1px;background:{RED_MAIN};margin:0 16px;"></section>

<section style="padding:14px 22px 14px;">
<p style="font-size:13px;color:#2c2c2c;line-height:1.9;margin:0 0 10px;text-align:justify;">"{quote_text}"</p>
<p style="font-size:12px;color:#3e3e3e;font-weight:500;text-align:right;margin:0;">—— {quote_author}</p>
</section>

<section style="display:flex;justify-content:space-between;align-items:center;padding:3px 16px;background:{RED_BLOCK};">
<p style="font-size:10px;color:#fff;font-weight:600;letter-spacing:1px;margin:0;">全球视野</p>
<p style="font-size:10px;color:#fff;font-weight:600;letter-spacing:1px;margin:0;">科技洞察</p>
</section>

</section>
</section>
</section>
</section>
</section>
"""


DISCLAIMER = """
<p style="font-size:12px;color:#9a9a9a;line-height:1.8;margin:32px 0 0;text-align:justify;">
素材来源于路透社、彭博社、TechCrunch、The Verge、Hacker News、CNBC 等国际主流科技媒体及网络公开报道，经 AI 辅助整理并由人工编辑审核。本文不代表任何立场，不构成任何投资建议。如有疏漏，欢迎留言指正。
</p>
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
    # 旧排版：从"三句话说清楚"块里提取（兼容保留）
    match = re.search(r'三句话说清楚</p>(.*?)</section>', html_text, re.DOTALL)
    if match:
        return re.sub(r'<[^>]+>', '', match.group(1)).strip()

    # 新排版（猫笔刀风格）：没有总结块，提取文末倒数几段作为"昨日要点"
    # 先去掉"（完）"以及它之后的内容
    text = re.sub(r'<p[^>]*>（完）</p>.*', '', html_text, flags=re.DOTALL)
    # 取所有正文段落
    paragraphs = re.findall(r'<p[^>]*font-size:\s*16px[^>]*>(.*?)</p>', text, re.DOTALL)
    # 去掉空段和分节符（省略号）
    clean = []
    for p in paragraphs:
        plain = re.sub(r'<[^>]+>', '', p).strip()
        if plain and '……' not in plain and len(plain) > 10:
            clean.append(plain)
    # 取最后 3-4 段作为"昨天结尾提到的"，给明天连续追踪用
    if clean:
        return "\n".join(clean[-4:])
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


# ===== AI 主题插图生成（豆包 Seedream 4.5） =====

# 电影感底板：无论今天是什么主题，这些参数都保持一致，确保视觉风格统一
CINEMATIC_BASE = (
    "电影级画面质感，冷色调为主（深蓝、海军蓝、深夜色调），"
    "局部暖色点缀（琥珀色/橙黄色灯光作为视觉锚点），"
    "景深层次丰富：前景主体清晰，中景发光元素，远景虚化的城市天际线，"
    "高对比度打光，体积光线，镜头光晕，赛博概念艺术风格，"
    "细节精致，科技感但不卡通化，像好莱坞科幻片开场镜头，"
    "写实摄影质感，8K超高清，电影比例 3:2 横版构图"
)

# 绝对不要出现的东西
NEGATIVE_STYLE = (
    "避免：卡通风格、幼稚可爱、Q版、矢量插画、粉色或紫色糖果色调、"
    "多个机器人小人、聊天气泡、emoji表情、漫画、简笔画、2D扁平化、"
    "文字或logo主导画面、拼贴风、学生习作感"
)


def generate_image_prompt(news_digest_text):
    """调用 DeepSeek，根据今日新闻摘要，生成一条豆包图像模型可用的中文 prompt。

    输入：简报全文（或前 1500 字）
    输出：一条完整的中文电影感 prompt，可直接丢给豆包 Seedream
    """
    meta_prompt = f"""你是一位电影海报概念艺术总监。下面是今天的科技新闻简报。

请从简报里**提取 2-3 个最具视觉冲击力的核心元素**，然后写一条中文 prompt，用于生成今日文章的主题插图。

## 元素提取规则

1. 优先选择有**具象视觉符号**的元素，如：
   - 科技公司 logo（Apple 苹果标志、Amazon 橙色箭头、NVIDIA 绿色、Google 彩色、OpenAI 六角形等）
   - 标志性产品（iPhone、Vision Pro、机器人、数据中心、芯片、服务器机架）
   - 有象征意义的动作（握手=合作、交棒=传承、砸钱=投资、城市天际线=产业版图）
2. **最多 3 个元素**，宁少勿多，避免画面杂乱
3. 避免抽象概念（"资本流动""算力竞争"这种——除非能给出具象物化的表达，如"发光的金色数据流"）

## Prompt 写作规则

1. **开头点明核心场景**，比如："在深夜的数据中心里，两只发光的手正在握手"
2. **中间展开元素细节**：每个元素用 1-2 句描述其在画面中的位置和形态
3. **最后加上统一的画面风格参数**（我会自动拼接，你不用管）
4. 全程中文，不要英文单词（除了科技公司英文名和产品名）
5. 不要有文字或文案在画面里
6. **控制在 120-180 字**

## 输出格式

直接输出 prompt 正文，不要任何解释、标题、前言、编号、引号。

## 今日简报

{news_digest_text[:1500]}"""

    try:
        resp = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"},
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": meta_prompt}],
                "max_tokens": 500,
                "temperature": 0.8,  # 创意类任务，稍微提高
            },
            timeout=60,
        )
        data = resp.json()
        if "choices" not in data:
            print(f"  图片 prompt 生成失败: {data}")
            return None
        core_prompt = data["choices"][0]["message"]["content"].strip()
        # 清理可能的 markdown 残留
        core_prompt = re.sub(r'^["""\'`]|["""\'`]$', '', core_prompt)
        core_prompt = re.sub(r'```.*?```', '', core_prompt, flags=re.DOTALL).strip()
        print(f"  核心 prompt: {core_prompt[:120]}...")

        # 拼接电影感底板
        full_prompt = f"{core_prompt}。{CINEMATIC_BASE}。{NEGATIVE_STYLE}"
        return full_prompt
    except Exception as e:
        print(f"  图片 prompt 生成异常: {e}")
        return None


def generate_cover_with_doubao_image(prompt_text, output_path="cover.png"):
    """调用豆包 Seedream 4.5 生成主题插图，保存为本地 PNG。

    返回本地文件路径，失败返回 None。
    """
    if not prompt_text:
        return None

    try:
        print(f"  正在请求豆包 Seedream 4.5...")
        resp = requests.post(
            "https://ark.cn-beijing.volces.com/api/v3/images/generations",
            headers={
                "Authorization": f"Bearer {DOUBAO_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "doubao-seedream-4-5-251128",
                "prompt": prompt_text,
                "size": "2K",              # 2K 足够公众号用，4K 更慢且费用高
                "response_format": "url",  # 返回图片 URL
                "watermark": False,        # 公众号用，不要水印
            },
            timeout=120,
        )
        data = resp.json()
        if "data" not in data or not data["data"]:
            print(f"  豆包图像返回异常: {data}")
            return None

        image_url = data["data"][0].get("url")
        if not image_url:
            print(f"  豆包图像 URL 为空: {data}")
            return None

        print(f"  豆包图像生成成功，正在下载...")
        img_resp = requests.get(image_url, timeout=60)
        if img_resp.status_code != 200:
            print(f"  图像下载失败: HTTP {img_resp.status_code}")
            return None

        with open(output_path, "wb") as f:
            f.write(img_resp.content)
        print(f"  主题插图已保存: {output_path} ({len(img_resp.content) // 1024} KB)")
        return output_path
    except Exception as e:
        print(f"  豆包图像生成异常: {e}")
        return None


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

    prompt = f"""你是一位资深且极其严谨的科技记者，同时你的行文风格师承财经公众号"猫笔刀"。请根据以下新闻素材整理科技日报初稿。

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

## 文风要求：猫笔刀式白话科技评论

**核心气质**：像一个懂行的朋友，坐在你对面一边喝茶一边给你讲今天科技圈发生了啥。不是新闻联播，也不是学术报告。

**六条硬性规则**：

1. **段落要短**——每个自然段不超过2句话。宁可多分段，不要写长段。
2. **句子要白**——能用大白话就不用书面语。删掉所有"毫无疑问""值得关注""标志着""本质是""预示着""综上所述"这种学生腔。
3. **有观点就亮**——点评不单独开"点评"模块，直接融进叙述里。看完事实紧接着说"其实这事儿是……"、"说白了就是……"、"你以为A，其实是B"。
4. **类比讲人话**——遇到专业概念，给一个生活化的比方。比如"算法稳定币"→"用另一个币的价格来托住这个币"；"AI基础设施"→"AI要跑起来背后要烧的那套东西"。
5. **用六个点顶左格分节**——不要用小标题切块。每说完一条新闻/一个话题，空一行顶格打六个中间点（`······`），再进入下一段。不要用省略号 `……`，要用六个独立的中点，且不居中、靠左顶格。
6. **结尾要有金句**——最后一句话要能让人停一下，有一点回味。不要写"让我们拭目以待""未来可期"这种套话。

## 结构要求

1. 筛选 3-5 条最重要的新闻（**强制最少 3 条，避免文章单薄**；不用凑够5-7条，宁缺毋滥但也不能只有 2 条）
2. 同一事件合并
3. 整篇文章像一条线讲下来，不要割裂成独立新闻块
4. 不要给每条新闻起小标题——直接用"先说A这件事""再看B这边""还有第三件事顺便说一下"这种口语过渡

### 标题与首段的关系（重要）

5. **标题和首段绝对不能复读。** 标题说了"围绕效率"，首段就不能再说"今天都围绕效率"——读者会觉得在绕圈子。
6. **首段必须从一个具体事实、场景或数字切入**，而不是先抛宏大结论。做法有三种任选：
   - **具体事实型**：直接甩出最炸的一条新闻的核心数字或动作。示例："SpaceX 昨晚砸了 600 亿美元，买下一家连 VC 都没见过的 AI 公司。"
   - **场景型**：像电影镜头一样切入。示例："昨天晚上硅谷有两家公司没睡。"
   - **对比型**：把今天的事和大家熟悉的事做反差。示例："一家 5000 人的公司，把一家十几万人的巨头逼到了墙角。"
7. **第二、三段再展开"今天这几件事有个共同点"的宏观判断**，让标题在这里才被暗暗揭晓。读者读到时是"哦原来是这样"的恍然大悟感，而不是"你这不刚说过吗"的冗余感。

### 其他结构规则

8. 每条新闻：事实描述（3-5个短段）→ 紧接着的观点分析（2-4个短段，融入叙述，不分开）
9. 全文用 `······` 分隔不同话题块（顶左格六点）
10. 结尾1-2段收束全篇，给一句有回味的金句
11. **文末必须输出"（完）"单独一行**——这是本栏目的签名式收尾，不能省略
12. 不要写"三句话说清楚"这种总结框
13. 最后另起一行输出名人名言，格式：今日名言：内容——作者（身份）

**额外输出：为今天的简报生成 5 个短话题标签**（4-8个汉字），格式：
今日标签：标签1 | 标签2 | 标签3 | 标签4 | 标签5

标签要求：每个标签精炼概括一条新闻的核心，便于读者一眼看懂。

## 字数要求（硬性下限）

**全文必须达到 1800 字以上**（不含名言和标签），理想区间 1800-2200 字。

这是硬性要求，不是建议。之前有几版出现过"宁缺勿滥"导致整篇只有 800 字的情况，这种短篇不符合公众号定位。

### 新闻少怎么办？（正确的展开方式）

如果今天值得写的新闻只有 2-3 件，**不是减少文字**，而是**把每件事写透**：

每件事可以从这几个角度展开（选 3-4 个即可达到足够字数）：
1. **事件陈述**：发生了什么，具体数字、主角、时间（2-3段）
2. **背景交代**：这件事之前行业里发生过什么，为什么这时点爆出来（2-3段）
3. **影响分析**：对谁有影响，影响几时见效（2-4段）
4. **类比释义**：用一个生活化比方帮读者理解（1-2段）
5. **历史对照**：类似的事以前发生过吗，上次是什么结果（可选，1-2段）
6. **观点收束**：说白了这事儿意味着什么（1-2段）

**禁止**为了凑字数写废话段、重复已说过的话、加"值得关注"这种虚词。
**鼓励**把每个观点讲具体、给类比、举小例子。

## 禁止事项

- 禁止使用任何 emoji 图标
- 禁止写"据XX报道"，直接陈述事实
- 禁止"炸锅""震惊""疯了""刷屏""沸腾"这类浮夸词
- 禁止"毫无疑问""显而易见""不言而喻"这类判断词
- 禁止"首先""其次""最后""综上所述"这种论文式连接词
- 禁止在结尾加"让我们拭目以待""未来可期""敬请期待"
- **禁止编造原文没有的媒体来源**（例如原文里没有《洛杉矶时报》，你就不能说"洛杉矶时报报道"）
- **禁止把"计划/有权/可能"写成"已经/拿下/完成"**——这是最严重的事实错误


来源翻译：TechCrunch→TechCrunch, Bloomberg→彭博社, Reuters→路透社, CNBC→CNBC, WSJ→华尔街日报, Hacker News→Hacker News

用纯文本输出，不要HTML标签，不要emoji，不要markdown加粗。

## 风格示例（仅供感受语气，内容无关）

---
过去24小时，科技圈连着抛出两件大事。

一件是库克宣布交棒，这是苹果2011年以来第一次换CEO。

另一件是亚马逊计划再给Anthropic砸250亿美元。

这两件事看起来一个在硬件一个在AI，但放一起看，其实是同一个故事的两面。

· · · · · ·

先说亚马逊这一刀。

250亿美元比很多国家一年的GDP还多。很多人第一反应是亚马逊钱多烧的慌。

其实完全不是。这笔钱的战略意义远大于财务回报，说白了就是在抢下一代AI的入场券。

打个比方你就明白了。

十几年前移动互联网刚起来的时候，巨头们抢的是什么？抢通信基站、抢数据中心，抢的都是上游入口。谁卡住上游谁就能收过路费。

现在云巨头和大模型公司深度绑定，干的是一模一样的事。
---

感受一下上面这种节奏：短段、口语、有观点、用类比、不端着。

新闻素材：
{news_text}"""

    try:
        resp = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"},
            json={"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "max_tokens": 6000},
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

## 七条红牌检查清单（必须逐条过）

### 红牌 1：计划 vs 已经（最严重）
文中每一个动词都要检查。原文说"有权""可能""计划""考虑"，初稿不能写成"已经""拿下""完成""收购了"。
示例：
- 原文"SpaceX 获得了以 600 亿美元收购 Cursor 的权利" → 初稿写"SpaceX 拿下了这家公司" ❌
- 正确改法：改成"SpaceX 获得了收购选择权"或"SpaceX 有权在今年晚些时候收购"
- 原文"考虑收购" → 初稿写"已收购" ❌

### 红牌 2：媒体来源真实性（严重）
初稿里每出现一个具体媒体名（《纽约时报》《华尔街日报》《洛杉矶时报》《彭博社》等），**必须在原始素材里找到匹配**。找不到的一律删除或改写为"据报道"。
示例：
- 原始素材里只有纽约时报的引用，但初稿写"《洛杉矶时报》此前也提到" → 这是来源幻觉 ❌
- 改法：删除这个来源，或改写为"此前也有报道指出"

### 红牌 3：主体张冠李戴
每个类比、引用、挤压关系，主体对象不能错。特别小心 A、B、C 三方故事里谁在挤压谁、谁在给谁压力。
示例：
- 原文"Cursor 被 Anthropic 的编程工具挤压" → 初稿误写"Anthropic 给谷歌带来压力" ❌（移花接木）
- 检查每个"对谁形成压力""逼谁怎么样"的表述，主体必须可追溯

### 红牌 4：数字归属和精度
员工数、估值、金额、百分比等具体数字：
- 必须在原始素材里找到对应
- 如果原始素材里有"约""大约""估计"等限定词，初稿也必须保留
- 不同数据源有不同估计时，不能直接取最大值
示例：
- 原文"Tracxn 估计约 5000 人，其他数据源估计 2500-3000 人" → 初稿写"总共只有大约 5000 名员工" ⚠️ 应改为"据第三方数据估计在 3000-5000 人之间"或"据 XX 数据约 5000 人"

### 红牌 5：因果关系推断
初稿是否添加了原文没有的因果推断？
示例：
- 原文说"SpaceX 获得收购权" + "马斯克承认 xAI 编程能力落后" → 初稿写"这笔交易跳过了 VC 流程" ❌（原文没这么说，实际 Cursor 还在和 VC 谈融资）

### 红牌 6：时态和数量模糊词
初稿有没有把模糊词改成了精确词？
- "几轮融资" ← 不能改成 "五轮融资"
- "最近几周" ← 不能改成 "上周"
- "大量员工" ← 不能改成 "数千员工"

### 红牌 7：引号里的话
初稿如果给人物加了引号，引号里的内容必须一字不差地在原始素材里出现过。

## 修改原则
- 发现红牌错误：**直接改正**为准确措辞
- 发现夸大描述：**改为谨慎表述**（加"据报道""约""可能""计划"等限定词）
- 发现**完全无法核实**的内容：**整段删除**（不要保留）
- 修改后**保持字数不要大幅下降**——如果删掉一段，需要在其他地方展开对应内容
- 保持文风和段落结构不变

## 输出要求

直接输出修正后的完整初稿。不要加任何"核查说明""修改理由"之类的元信息。保持原有的段落节奏、分节符 `······`、文末"（完）"、名言、标签。

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
            json={"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "max_tokens": 6000},
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
    prompt = f"""你是"鹏眼观天下"公众号主编，本账号的文风师承财经公众号"猫笔刀"：短段、白话、不端着。把已核查的初稿改写成一篇可以直接发到公众号的 HTML 文章。

## 最高原则：事实零改动
- 初稿说的所有事实一字不能改
- 初稿用的"据报道""可能"等措辞必须保留
- 不能加原文没有的事情
- 初稿的段落顺序和叙述逻辑尽量保持

## 字数保护（重要）

- **初稿字数多少，你润色后也要保持这个字数**
- **禁止大幅压缩**——润色不是精简，而是让语言更顺
- 如果初稿有 1800 字，润色后也必须保持 1800 字左右（±100 字可接受）
- 如果你觉得某段重复啰嗦，**不要删除**，而是改写成更清晰的表达
- 只有**明显的冗余句**（例如一段里重复说了两遍同一件事）可以删减

## 你可以做的
- 让口语更顺，砍掉任何残留的书面腔
- 补充类比让小白也看得懂（但事实必须来自初稿）
- 强化开头的悬念（用初稿已有的事实）
- 给结尾金句再打磨一下让它更抓人
- 对专业名词加一句大白话解释，而不是加括号注释

## 排版铁律（猫笔刀风格）

**一、绝对不要出现的东西**：
- 不要给新闻起小标题（蓝色标题、彩色标题都不行）
- 不要用蓝色引用框包"鹏眼点评"或任何其他内容
- 不要用任何背景色块、边框、圆角框来切分内容
- 不要用"三句话说清楚"这种总结框
- 不要 emoji、不要 markdown 加粗、不要 h1/h2/h3 标签
- 不要把正文分栏、分模块

**二、只允许使用的 HTML 元素**：
- `<p>` 段落（正文）
- `<p>` 段落（顶左格的六点分节符）
- `<p>` 段落（总标题）
- `<p>` 段落（文末的"（完）"）

**三、排版模板**：

总标题（黑色、加粗、不要蓝色）：
<p style="font-size:20px;font-weight:700;color:#2c2c2c;line-height:1.5;margin:0 0 24px;letter-spacing:0.3px;">总标题</p>

正文段落（每段1-2句话，不要长段）：
<p style="font-size:16px;color:#3e3e3e;line-height:1.9;margin:0 0 18px;letter-spacing:0.5px;text-align:justify;">段落内容</p>

分节符（每说完一个话题用一个，全文用3-5个，靠左顶格，不居中）：
<p style="font-size:16px;color:#b8b8b8;letter-spacing:8px;margin:28px 0 22px;line-height:1;">······</p>

**重要**：分节符必须用六个中文间隔符"·"（Unicode U+00B7），**不要用省略号 `……`**，因为省略号在不同字体下渲染会变成两坨粘在一起的点，视觉不整齐。分节符必须**靠左顶格**（`text-align` 默认 left，不要写 center），和正文左边对齐。

文末"（完）"：
<p style="font-size:15px;color:#9a9a9a;margin:32px 0 0;">（完）</p>

**四、结构要求**：

1. 总标题一行，紧接着空18-24px
2. 开头2-4个短段，抛出今天的事（不要引言框，就直接写）
3. 分节符六个中点 `······`
4. 每条新闻：若干短段事实 + 若干短段观点，全部是纯 `<p>` 段落，不要任何框
5. 每条新闻结束用 `······` 分节符
6. 结尾2-4段收束全文，给金句
7. 最后单独一个 `<p>（完）</p>`

## 禁止清单（再强调一次）

- 代码块、markdown加粗、h1/h2/h3、div 标签、section 标签、emoji、斜体
- 蓝色小标题、蓝色引用框、背景色块
- "鹏眼点评："这类栏目化标识
- "三句话说清楚"总结框
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
    # 猫笔刀风格分节符（顶左格六点，不居中）——统一常量，便于整体调整
    DIVIDER = '<p style="font-size:16px;color:#b8b8b8;letter-spacing:8px;margin:28px 0 22px;line-height:1;">······</p>'

    # 去掉代码围栏
    text = re.sub(r'```html\s*', '', text)
    text = re.sub(r'```\s*$', '', text)
    # markdown加粗 → 猫笔刀风格基本不用加粗
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    # 如果模型偶尔用了 h1-h6（违反规定），兜底转成正文段落（不是蓝色标题）
    text = re.sub(
        r'<h[1-6][^>]*>(.*?)</h[1-6]>',
        r'<p style="font-size:16px;color:#3e3e3e;line-height:1.9;margin:0 0 18px;letter-spacing:0.5px;">\1</p>',
        text,
    )
    # 把 <hr> 转成分节符（极少用，兜底）
    text = re.sub(r'<hr[^>]*/?>', DIVIDER, text)

    # ====== 分节符归一化（核心）======
    # 无论模型输出什么形式的分节符（省略号、居中六点、各种变体），
    # 全部归一化为顶左格六点。
    #
    # 匹配规则：一个独立的 <p> 标签，里面只有以下内容之一：
    #   - 省略号 …… 或 ……… 或更多
    #   - 英文省略号 ... 或 ......
    #   - 中间点 · 或 ··· 或 ······
    #   - 上述字符 + 空格的组合
    # 不管 <p> 上有没有 text-align:center、什么颜色、什么 letter-spacing，统统替换。
    text = re.sub(
        r'<p[^>]*>[\s·…\.\u2026\u2027\u00b7]+</p>',
        DIVIDER,
        text,
    )

    # 兜底清理：如果模型违反规定用了 section 带浅色背景（蓝框/灰框），去掉背景
    text = re.sub(
        r'<section[^>]*background:\s*#[ef0-9a-f]{3,6}[^>]*>',
        '<section>',
        text,
        flags=re.IGNORECASE,
    )
    # 兜底清理：如果模型用了 border-left 蓝色竖线，也清掉
    text = re.sub(
        r'<section[^>]*border-left:[^>]*>',
        '<section>',
        text,
        flags=re.IGNORECASE,
    )
    return text.strip()


def extract_main_subtitle(html_text):
    """从正文提取主副标题，用于封面"""
    # 兼容新旧两种字号：20px（新）和 22px（旧）
    match = re.search(r'font-size:\s*(?:20|22)px[^>]*>(.*?)</p>', html_text)
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

        # 生成主题插图（豆包 Seedream 4.5 AI 生图）
        print("=== 6/8 生成主题插图（豆包 Seedream 4.5） ===")
        main_title, sub_title = extract_main_subtitle(final)
        if not topics:
            topics = ["OpenAI动态", "AI竞争升级", "芯片与算力", "资本风向", "新技术落地"]
        print(f"  主标题: {main_title} / {sub_title}")
        print(f"  话题标签: {topics}")

        cover_url = None
        cover_path = None

        # 步骤 6.1: 根据文章内容生成图片 prompt
        print("  步骤 6.1: 生成图片 prompt...")
        # 从 draft（已核查的纯文本初稿）提取视觉元素，而不是用 HTML 版本
        image_prompt = generate_image_prompt(draft)

        # 步骤 6.2: 调用豆包 Seedream 4.5 生图
        if image_prompt:
            print("  步骤 6.2: 豆包 Seedream 4.5 生图...")
            cover_path = generate_cover_with_doubao_image(image_prompt, "cover.png")

        # 步骤 6.3: 失败时兜底到旧的 HTML 渲染封面
        if not cover_path:
            print("  豆包生图失败，回退到 HTML 渲染封面...")
            cover_path = generate_cover_png(main_title, sub_title, topics, "cover.png")

        # 步骤 6.4: 上传到 GitHub 拿 raw URL
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
