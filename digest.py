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
        lunar_html = f'<p style="text-align:center;font-size:10px;color:#3e3e3e;font-weight:500;letter-spacing:1px;margin:0 0 8px;">{lunar_text}</p>'

    # 构造 HTML（微信兼容：全部 <section>/<p> + 内联样式）
    # 结构：wrap → outer-red → inner-gap → inner-red → content → 顶部红块/正文/底部红块
    return f"""
<section style="margin:32px auto 0;max-width:290px;">
<section style="background:{PAPER};padding:10px;box-sizing:border-box;box-shadow:0 2px 6px rgba(0,0,0,0.06),0 10px 30px rgba(0,0,0,0.1);">
<section style="background:{RED_MAIN};padding:2px;">
<section style="background:{PAPER};padding:5px;">
<section style="background:{RED_MAIN};padding:1px;">
<section style="background:{PAPER};">

<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{RED_BLOCK};border-collapse:collapse;"><tr><td height="24" width="25%" style="padding:0 0 0 16px;line-height:24px;vertical-align:middle;text-align:left;font-size:11px;color:#fff;font-weight:700;letter-spacing:1px;">{year}</td><td height="24" width="50%" style="line-height:24px;vertical-align:middle;text-align:center;font-size:12px;color:#fff;font-weight:700;letter-spacing:2px;">鹏眼观天下</td><td height="24" width="25%" style="padding:0 16px 0 0;line-height:24px;vertical-align:middle;text-align:right;font-size:11px;color:#fff;font-weight:700;letter-spacing:1px;">{month_cn}</td></tr></table>

<section style="padding:4px 20px 6px;">
<section style="display:flex;align-items:flex-start;gap:2px;">
<span style="font-family:Georgia,'Times New Roman',serif;font-size:19px;font-style:italic;color:{RED_MAIN};font-weight:400;margin-top:12px;line-height:1;">{month_en}</span>
<span style="font-family:Georgia,serif;font-size:19px;color:{RED_MAIN};font-weight:300;margin-top:12px;margin-left:2px;margin-right:4px;line-height:1;">/</span>
<span style="font-family:Georgia,'Times New Roman',serif;font-size:80px;font-weight:900;color:{RED_MAIN};line-height:0.92;letter-spacing:-3px;">{day}</span>
</section>
<p style="text-align:center;font-size:15px;font-weight:700;color:#2c2c2c;letter-spacing:6px;margin:4px 0 2px;">{weekday}</p>
{lunar_html}
</section>

<section style="height:1px;background:{RED_MAIN};margin:0 16px;"></section>

<section style="display:flex;justify-content:center;gap:22px;padding:8px 12px;">
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

<section style="padding:10px 22px 10px;">
<p style="font-size:13px;color:#2c2c2c;line-height:1.75;margin:0 0 8px;text-align:justify;">"{quote_text}"</p>
<p style="font-size:12px;color:#3e3e3e;font-weight:500;text-align:right;margin:0;">—— {quote_author}</p>
</section>

<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{RED_BLOCK};border-collapse:collapse;"><tr><td height="12" width="50%" style="padding:0 0 0 16px;line-height:12px;vertical-align:middle;text-align:left;font-size:8px;color:#fff;font-weight:600;letter-spacing:1px;">全球视野</td><td height="12" width="50%" style="padding:0 16px 0 0;line-height:12px;vertical-align:middle;text-align:right;font-size:8px;color:#fff;font-weight:600;letter-spacing:1px;">科技洞察</td></tr></table>

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
    """Google News RSS - 返回 dict 列表"""
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
                source = item.find("source").text if item.find("source") is not None else "Google News"
                pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
                link = item.find("link").text if item.find("link") is not None else ""
                desc = item.find("description").text if item.find("description") is not None else ""
                all_articles.append({
                    "title": title.strip(),
                    "url": link.strip(),
                    "summary": re.sub(r"<[^>]+>", "", desc).strip()[:400],
                    "source": source,
                    "pub_time": pub_date,
                    "lang": "en",
                })
        except Exception as e:
            print(f"Google News 失败({q}): {e}")
    print(f"Google News: {len(all_articles)} 条")
    return all_articles


def fetch_newsapi():
    """NewsAPI - 返回 dict 列表"""
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
                source = a.get("source", {}).get("name", "NewsAPI")
                articles.append({
                    "title": a.get("title", "").strip(),
                    "url": a.get("url", ""),
                    "summary": (a.get("description", "") + " " + (a.get("content") or "")[:300]).strip()[:500],
                    "source": source,
                    "pub_time": a.get("publishedAt", ""),  # ISO 格式
                    "lang": "en",
                })
        print(f"NewsAPI: {len(articles)} 条")
        return articles
    except Exception as e:
        print(f"NewsAPI 失败: {e}")
        return []


def fetch_hackernews():
    """Hacker News - 返回 dict 列表"""
    try:
        resp = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=15)
        story_ids = resp.json()[:20]
        articles = []
        tech_kw = ["ai", "gpt", "llm", "openai", "google", "apple", "nvidia", "tesla",
                   "microsoft", "meta", "startup", "funding", "chip", "robot", "model",
                   "launch", "release", "billion", "acquisition", "open source",
                   "anthropic", "gemini", "claude", "copilot", "agent", "autonomous"]
        now_ts = datetime.now(BJT).timestamp()
        for sid in story_ids:
            try:
                item = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json", timeout=10).json()
                if not item or item.get("type") != "story":
                    continue
                title = item.get("title", "")
                score = item.get("score", 0)
                url = item.get("url", "") or f"https://news.ycombinator.com/item?id={sid}"
                hn_time = item.get("time", 0)  # Unix 时间戳
                # 转成 RFC 822 格式（和其他源一致）
                pub_dt = datetime.fromtimestamp(hn_time, tz=BJT) if hn_time else None
                pub_str = pub_dt.strftime("%a, %d %b %Y %H:%M:%S %z") if pub_dt else ""
                if score >= 100 or any(kw in title.lower() for kw in tech_kw):
                    domain = url.split("/")[2] if url and "/" in url else "news.ycombinator.com"
                    articles.append({
                        "title": title.strip(),
                        "url": url,
                        "summary": f"Hacker News 热度 {score} 分。",
                        "source": f"HN/{domain}",
                        "pub_time": pub_str,
                        "lang": "en",
                    })
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
    """TechCrunch RSS - 返回 dict 列表"""
    try:
        resp = requests.get("https://techcrunch.com/feed/", timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        root = ElementTree.fromstring(resp.content)
        articles = []
        for item in root.findall(".//item")[:10]:
            title = item.find("title").text or ""
            pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
            link = item.find("link").text if item.find("link") is not None else ""
            desc = re.sub(r'<[^>]+>', '', item.find("description").text or "")[:400] if item.find("description") is not None else ""
            articles.append({
                "title": title.strip(),
                "url": link.strip(),
                "summary": desc.strip(),
                "source": "TechCrunch",
                "pub_time": pub_date,
                "lang": "en",
            })
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
    # 防御：输入为空时直接返回 None，避免下游崩溃
    if not news_digest_text or not isinstance(news_digest_text, str):
        print("  图片 prompt 生成跳过：输入为空")
        return None

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


# ============================================================================
# ===== v11 核心：国内 RSS 源抓取 =====
# ============================================================================

def fetch_ithome():
    """IT 之家 RSS 抓取"""
    print("抓取 IT之家 RSS...")
    try:
        resp = requests.get(
            "https://www.ithome.com/rss/",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=20,
        )
        resp.encoding = "utf-8"
        items = re.findall(
            r"<item>\s*<title><!\[CDATA\[(.*?)\]\]></title>\s*"
            r"<link>(.*?)</link>\s*"
            r"<description><!\[CDATA\[(.*?)\]\]></description>\s*"
            r"(?:<pubDate>(.*?)</pubDate>)?",
            resp.text,
            re.DOTALL,
        )
        articles = []
        for title, link, desc, pubdate in items[:30]:
            articles.append({
                "title": title.strip(),
                "url": link.strip(),
                "summary": re.sub(r"<[^>]+>", "", desc).strip()[:300],
                "source": "IT之家",
                "pub_time": pubdate.strip() if pubdate else "",
                "lang": "zh",
            })
        print(f"  IT之家 抓到 {len(articles)} 条")
        return articles
    except Exception as e:
        print(f"  IT之家 抓取失败: {e}")
        return []


def fetch_jiqizhixin():
    """机器之心 RSS 抓取"""
    print("抓取 机器之心 RSS...")
    try:
        resp = requests.get(
            "https://www.jiqizhixin.com/rss",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=20,
        )
        resp.encoding = "utf-8"
        items = re.findall(
            r"<item>\s*<title>(.*?)</title>\s*"
            r"<link>(.*?)</link>\s*"
            r"(?:<description>(.*?)</description>)?\s*"
            r"(?:<pubDate>(.*?)</pubDate>)?",
            resp.text,
            re.DOTALL,
        )
        articles = []
        for title, link, desc, pubdate in items[:30]:
            t = re.sub(r"<!\[CDATA\[|\]\]>", "", title).strip()
            d = re.sub(r"<!\[CDATA\[|\]\]>|<[^>]+>", "", desc or "").strip()[:300]
            articles.append({
                "title": t,
                "url": link.strip(),
                "summary": d,
                "source": "机器之心",
                "pub_time": pubdate.strip() if pubdate else "",
                "lang": "zh",
            })
        print(f"  机器之心 抓到 {len(articles)} 条")
        return articles
    except Exception as e:
        print(f"  机器之心 抓取失败: {e}")
        return []


def fetch_36kr():
    """36kr RSS 抓取"""
    print("抓取 36kr RSS...")
    try:
        resp = requests.get(
            "https://36kr.com/feed",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=20,
        )
        resp.encoding = "utf-8"
        items = re.findall(
            r"<item>\s*<title>(.*?)</title>\s*"
            r"<link>(.*?)</link>\s*"
            r"(?:<description>(.*?)</description>)?\s*"
            r"(?:<pubDate>(.*?)</pubDate>)?",
            resp.text,
            re.DOTALL,
        )
        articles = []
        for title, link, desc, pubdate in items[:30]:
            t = re.sub(r"<!\[CDATA\[|\]\]>", "", title).strip()
            d = re.sub(r"<!\[CDATA\[|\]\]>|<[^>]+>", "", desc or "").strip()[:300]
            articles.append({
                "title": t,
                "url": link.strip(),
                "summary": d,
                "source": "36kr",
                "pub_time": pubdate.strip() if pubdate else "",
                "lang": "zh",
            })
        print(f"  36kr 抓到 {len(articles)} 条")
        return articles
    except Exception as e:
        print(f"  36kr 抓取失败: {e}")
        return []


# ============================================================================
# ===== v11 核心：时间过滤 =====
# ============================================================================

def parse_pubdate_to_bjt(pubdate_str):
    """各种 pubDate 字符串 → datetime（带 BJT 时区）"""
    if not pubdate_str:
        return None
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(pubdate_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=BJT)
        return dt.astimezone(BJT)
    except Exception:
        try:
            # 备用：ISO 格式
            dt = datetime.fromisoformat(pubdate_str.replace("Z", "+00:00"))
            return dt.astimezone(BJT)
        except Exception:
            return None


def is_within_hours(pubdate_str, hours=24, now=None):
    """是否在过去 N 小时内（默认 24h）"""
    now = now or datetime.now(BJT)
    pub = parse_pubdate_to_bjt(pubdate_str)
    if pub is None:
        return False  # 解析失败的丢弃，宁缺勿滥
    delta = now - pub
    return timedelta(0) <= delta <= timedelta(hours=hours)


def relative_time(pubdate_str, now=None):
    """转成 '3小时前' 这种相对时间显示"""
    now = now or datetime.now(BJT)
    pub = parse_pubdate_to_bjt(pubdate_str)
    if pub is None:
        return ""
    delta = now - pub
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return "刚刚"
    if seconds < 3600:
        return f"{seconds // 60}分钟前"
    if seconds < 86400:
        return f"{seconds // 3600}小时前"
    if seconds < 86400 * 2:
        return "昨天"
    return f"{seconds // 86400}天前"


def filter_by_time(articles, hours=24, fallback_hours=36, min_count=8):
    """严格 24h 过滤；如果不足 min_count 条，自动放宽到 fallback_hours"""
    now = datetime.now(BJT)
    filtered = [a for a in articles if is_within_hours(a.get("pub_time", ""), hours, now)]
    if len(filtered) < min_count and hours < fallback_hours:
        print(f"  24h 内仅 {len(filtered)} 条，放宽到 {fallback_hours}h...")
        filtered = [a for a in articles if is_within_hours(a.get("pub_time", ""), fallback_hours, now)]
    print(f"  时间过滤后剩 {len(filtered)} 条")
    return filtered


# ============================================================================
# ===== v11 核心：DeepSeek 整理新闻（替代 draft + factcheck + polish 三层）=====
# ============================================================================

def deepseek_organize_news(articles):
    """让 DeepSeek 把抓来的新闻整理成结构化 JSON。

    输入：抓取到的新闻列表
    输出：dict，三个板块的新闻列表
        {
            "international": [{title, summary, source, url, pub_time}, ...],
            "domestic": [...],
            "big_names": [...],
            "headline": "今日要闻总标题"
        }
    """
    # 拼接素材
    news_blocks = []
    for i, a in enumerate(articles, 1):
        news_blocks.append(
            f"[{i}] 【{a['source']}】({a.get('lang','zh')}) "
            f"{a.get('pub_time','')}\n"
            f"标题：{a['title']}\n"
            f"链接：{a['url']}\n"
            f"摘要：{a.get('summary','')}"
        )
    news_text = "\n\n".join(news_blocks)

    prompt = f"""你是科技日报的编辑。下面是过去 24 小时抓取的新闻原始素材。请整理成可以直接发布的科技日报。

## 你的任务（只做这些，不要做别的）

1. **筛选**：从素材里挑出 8-15 条**真正重要**的科技新闻（去掉重复、广告、低质内容）
2. **翻译**：英文新闻翻译成中文（标题和摘要都翻译）
3. **改写标题**（仅改写不准确或太长的）：
   - 中文新闻：保留原标题（除非有夸张词如"炸锅""血洗"，要改成中性表达）
   - 英文新闻：翻译成"主体：核心动作或观点"格式（如"黄仁勋：英伟达卖的是 token"）
4. **改写摘要**：每条 80-150 字，**只用原文事实，禁止添加任何观点、推断、评论**
5. **分类**：把每条新闻归到下面三个板块之一：
   - `international`（国际要闻）：发生在中国大陆以外的事
   - `domestic`（国内动态）：中国大陆公司、国内政策、国内市场
   - `big_names`（大佬观点）：知名人物的言论、表态、采访（黄仁勋、马斯克、奥特曼、库克、雷军、余承东等）
6. **取一个总标题**：用极客公园式的标题，有冲突感、有信息量，20-30 字
7. **生成 5 个话题标签**：4-8 个汉字，每个概括一条新闻

## 严格要求

- **不写任何评论**：你不是在写社论，是在做新闻编辑
- **不加任何"分析认为""值得关注""引发热议"** 这类编辑感受的话
- **保留时态**：原文说"将"就不能写成"已经"；原文说"或将"就不能写成"已经"
- **保留来源**：每条都标注 source（IT之家/机器之心/36kr/TechCrunch 等）
- **去重**：如果两条新闻讲同一件事（特别是国内外报道同一事件），合并成一条
- **质量优于数量**：宁可只挑 8 条精品，也不要凑数

## 输出格式（严格 JSON，不要任何额外文字）

```json
{{
  "headline": "今日要闻总标题",
  "topics": ["标签1", "标签2", "标签3", "标签4", "标签5"],
  "international": [
    {{
      "title": "改写后的标题",
      "summary": "80-150字摘要",
      "source": "TechCrunch",
      "url": "https://...",
      "pub_time": "原 pubDate 字符串"
    }}
  ],
  "domestic": [...],
  "big_names": [...]
}}
```

## 原始素材（共 {len(articles)} 条）

{news_text}
"""

    print(f"DeepSeek 整理新闻中（输入 {len(articles)} 条）...")
    try:
        resp = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"},
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 8000,
                "response_format": {"type": "json_object"},
            },
            timeout=180,
        )
        data = resp.json()
        if "choices" not in data:
            print(f"DeepSeek 错误: {data}")
            return None
        content = data["choices"][0]["message"]["content"]
        # 清理 markdown 代码围栏（即使要求 JSON 也偶尔会出现）
        content = re.sub(r"^```json\s*|\s*```$", "", content.strip())
        result = json.loads(content)
        print(f"  整理完成：国际 {len(result.get('international', []))} / "
              f"国内 {len(result.get('domestic', []))} / "
              f"大佬 {len(result.get('big_names', []))}")
        return result
    except Exception as e:
        print(f"DeepSeek 整理失败: {e}")
        return None


# ============================================================================
# ===== v11 核心：HTML 模板拼接（替代 doubao_polish）=====
# ============================================================================

def render_news_item(item, now=None):
    """渲染单条新闻为 HTML（含小标题、摘要、来源 + 时间）"""
    now = now or datetime.now(BJT)
    title = item.get("title", "").strip()
    summary = item.get("summary", "").strip()
    source = item.get("source", "")
    pub_time = item.get("pub_time", "")
    rel_t = relative_time(pub_time, now) if pub_time else ""
    meta = f"来源：{source}"
    if rel_t:
        meta += f" · {rel_t}"

    return f"""
<section style="margin:0 0 26px;">
<p style="font-size:17px;font-weight:700;color:#222;line-height:1.45;margin:0 0 10px;border-left:4px solid #c0392b;padding-left:12px;">{title}</p>
<p style="font-size:15px;color:#3e3e3e;line-height:1.85;margin:0 0 8px;text-align:justify;">{summary}</p>
<p style="font-size:12px;color:#9a9a9a;margin:0;">{meta}</p>
</section>
"""


def render_section_header(label_zh, label_en):
    """渲染板块大标题（如"国际要闻 BREAKING NEWS"）"""
    return f"""
<section style="margin:36px 0 22px;text-align:center;">
<p style="display:inline-block;font-size:18px;font-weight:700;color:#222;letter-spacing:1px;margin:0;padding:0 16px;background:#fff;position:relative;">
{label_zh}
<span style="display:block;font-size:11px;color:#c0392b;letter-spacing:3px;margin-top:4px;">{label_en}</span>
</p>
<div style="border-top:2px solid #c0392b;margin-top:-32px;height:0;position:relative;z-index:-1;"></div>
</section>
"""


def render_remind_block(items):
    """渲染开头的"要闻提示"目录"""
    if not items:
        return ""
    list_html = "".join(
        f'<p style="font-size:14px;color:#3e3e3e;line-height:1.9;margin:0 0 6px;padding-left:24px;text-indent:-24px;">{i+1}. {item.get("title","")}</p>'
        for i, item in enumerate(items[:8])
    )
    return f"""
<section style="margin:24px 0 32px;padding:18px 16px;background:#faf6ee;border-left:4px solid #c0392b;">
<p style="font-size:16px;font-weight:700;color:#c0392b;letter-spacing:2px;margin:0 0 12px;">要闻提示 · NEWS REMIND</p>
{list_html}
</section>
"""


def build_news_html(organized, now=None):
    """把整理好的结构化数据 → 完整公众号 HTML（雷锋网+极客公园风格）"""
    now = now or datetime.now(BJT)
    headline = organized.get("headline", "今日科技要闻")

    # 三个板块
    intl = organized.get("international", [])
    dom = organized.get("domestic", [])
    big = organized.get("big_names", [])

    # 头部：总标题 + 日期
    weekday_cn = WEEKDAY_CN[now.weekday()]
    date_str = now.strftime("%Y年%m月%d日") + f" · {weekday_cn}"

    parts = [
        f'<p style="font-size:21px;font-weight:800;color:#1a1a1a;line-height:1.4;margin:0 0 6px;">{headline}</p>',
        f'<p style="font-size:13px;color:#9a9a9a;margin:0 0 4px;letter-spacing:1px;">{date_str}</p>',
    ]

    # 要闻提示（合并所有板块取前 8 条）
    all_items = intl + dom + big
    parts.append(render_remind_block(all_items))

    # 国际要闻
    if intl:
        parts.append(render_section_header("国际要闻", "BREAKING NEWS"))
        for item in intl:
            parts.append(render_news_item(item, now))

    # 国内动态
    if dom:
        parts.append(render_section_header("国内动态", "DOMESTIC NEWS"))
        for item in dom:
            parts.append(render_news_item(item, now))

    # 大佬观点
    if big:
        parts.append(render_section_header("大佬观点", "BIG NAMES"))
        for item in big:
            parts.append(render_news_item(item, now))

    return "\n".join(parts)


def extract_titles_from_organized(organized):
    """从整理后的数据提取主副标题（用于豆包封面图 prompt）"""
    headline = organized.get("headline", "今日科技圈")
    # 拆主副
    for sep in ["，", "：", " - ", "——"]:
        if sep in headline:
            parts = headline.split(sep, 1)
            return parts[0].strip(), parts[1].strip()
    if len(headline) > 12:
        mid = len(headline) // 2
        return headline[:mid], headline[mid:]
    return headline, "过去24小时科技要闻"


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

    print("=== 0/7 读取历史 ===")
    recent_quotes = read_recent_quotes()  # 仅日历卡名言去重需要

    print("=== 1/7 抓取新闻（4 国外源 + 3 国内源）===")
    print("  Google News...")
    google_articles = fetch_google_news()
    print("  NewsAPI...")
    newsapi_articles = fetch_newsapi()
    print("  Hacker News...")
    hn_articles = fetch_hackernews()
    print("  TechCrunch...")
    tc_articles = fetch_techcrunch_rss()

    # 国内三大源
    ithome_articles = fetch_ithome()
    jqzx_articles = fetch_jiqizhixin()
    kr36_articles = fetch_36kr()

    all_articles = (
        google_articles + newsapi_articles + hn_articles + tc_articles
        + ithome_articles + jqzx_articles + kr36_articles
    )
    print(f"  原始共 {len(all_articles)} 条")

    print("=== 2/7 时间过滤（24小时硬约束，不足放宽到36h）===")
    all_articles = filter_by_time(all_articles, hours=24, fallback_hours=36, min_count=8)

    if not all_articles:
        send_pushplus(title, "<p>过去24小时暂无重要科技动态。</p>")
        print("无新闻，已发送空报")
    else:
        print("=== 3/7 DeepSeek 整理新闻（无评论模式）===")
        organized = deepseek_organize_news(all_articles)

        if organized:
            print("=== 4/7 模板拼接 HTML ===")
            now_for_render = datetime.now(BJT)
            final = build_news_html(organized, now_for_render)
            topics = organized.get("topics", [])
        else:
            final = "<p>AI 整理失败。</p>"
            organized = {"headline": "今日科技要闻", "topics": []}
            topics = []

        # 生成主题封面图
        print("=== 5/7 生成主题封面图（豆包 Seedream 4.5）===")
        main_title, sub_title = extract_titles_from_organized(organized)
        if not topics:
            topics = ["AI动态", "芯片算力", "国内创投", "海外巨头", "新品发布"]
        print(f"  主标题: {main_title} / {sub_title}")
        print(f"  话题标签: {topics}")

        cover_url = None
        cover_path = None

        if organized:
            # 用 organized 数据为豆包生图 prompt 提供素材
            digest_for_image = json.dumps(organized, ensure_ascii=False)[:2000]
            print("  步骤 5.1: 生成图片 prompt...")
            image_prompt = generate_image_prompt(digest_for_image)
            if image_prompt:
                print("  步骤 5.2: 豆包 Seedream 4.5 生图...")
                cover_path = generate_cover_with_doubao_image(image_prompt, "cover.png")

        if not cover_path:
            print("  豆包生图失败或跳过，回退到 HTML 渲染封面...")
            cover_path = generate_cover_png(main_title, sub_title, topics, "cover.png")

        if cover_path:
            cover_url = commit_image_to_repo(cover_path)

        if cover_url:
            cover_html = f'<section style="margin-bottom:24px;"><img src="{cover_url}" style="width:100%;border-radius:8px;" /></section>'
            final = cover_html + final
            print("  封面图已插入文章开头")
        else:
            print("  封面图生成失败，跳过")

        # 日历卡（保留品牌资产，名言用历史去重）
        print("=== 6/7 生成日历卡片 ===")
        # 简单从历史名言池随机一句不重复的（保留 v10 逻辑的简化版）
        quote_text = ""
        quote_author = ""
        # 不依赖 AI 生成名言：用预置池子轮换
        DEFAULT_QUOTES = [
            ("预测未来的最好方式，就是去创造它。", "艾伦·凯（计算机科学家）"),
            ("我们构建的系统，最终会暴露出构建者的优先级。", "布莱恩·克里斯蒂安（作家）"),
            ("技术是一种权力，而权力需要制衡。", "蒂姆·伯纳斯-李（万维网发明者）"),
            ("简单是终极的复杂。", "达·芬奇"),
            ("好的设计，是把复杂的事变简单。", "乔布斯"),
            ("我们高估了短期的变化，低估了长期的革命。", "罗伊·阿玛拉"),
        ]
        random.seed(datetime.now(BJT).strftime("%Y%m%d"))
        # 选一句最近 7 天没用过的
        for q_text, q_author in random.sample(DEFAULT_QUOTES, len(DEFAULT_QUOTES)):
            if q_text not in (recent_quotes or []):
                quote_text, quote_author = q_text, q_author
                break
        if not quote_text:
            quote_text, quote_author = DEFAULT_QUOTES[0]

        calendar = generate_calendar_card(quote_text, quote_author)
        final = final + calendar + DISCLAIMER

        print("=== 7/7 推送微信 ===")
        send_pushplus(title, final)

        # 仅记录名言去重，不再做内容连续追踪
        if quote_text:
            save_recent_quote(quote_text, quote_author)

    print("全部完成!")
