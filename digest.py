import os, json, re, requests, random, base64, subprocess
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree

NEWS_API_KEY   = os.environ["NEWS_API_KEY"]
DEEPSEEK_KEY   = os.environ["DEEPSEEK_API_KEY"]
DOUBAO_KEY     = os.environ["DOUBAO_API_KEY"]
PUSHPLUS_TOKEN = os.environ["PUSHPLUS_TOKEN"]

BJT = timezone(timedelta(hours=8))

WEEKDAY_MAP = {
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
TECH_QUOTES = [
    ("模仿并不丢人，模仿是为了超越。", "马化腾（腾讯创始人）"),
    ("预测未来的最好方式，就是去创造它。", "艾伦·凯（计算机科学家）"),
    ("Stay hungry, stay foolish.", "史蒂夫·乔布斯（苹果创始人）"),
    ("任何足够先进的技术，都与魔法无异。", "亚瑟·克拉克（科幻作家）"),
    ("最好的创业方式，是解决你自己遇到的问题。", "保罗·格雷厄姆（YC创始人）"),
    ("我们总是高估两年的变化，低估十年的变化。", "比尔·盖茨（微软创始人）"),
    ("创新区分了领导者和跟随者。", "史蒂夫·乔布斯（苹果创始人）"),
    ("AI不会取代人类，但会用AI的人会取代不用的人。", "黄仁勋（英伟达CEO）"),
    ("快速行动，打破常规。", "马克·扎克伯格（Meta CEO）"),
    ("软件正在吞噬世界。", "马克·安德森（a16z创始人）"),
    ("真正的风险不是做得太多，而是做得太少。", "萨姆·奥特曼（OpenAI CEO）"),
    ("未来已来，只是分布不均匀。", "威廉·吉布森（科幻作家）"),
    ("想象力比知识更重要。", "爱因斯坦（物理学家）"),
    ("第一步是确立一件事是可能的，然后概率就会发生。", "埃隆·马斯克（特斯拉CEO）"),
    ("下一个大事件，永远看起来像玩具。", "克里斯·迪克森（a16z合伙人）"),
    ("简洁是终极的复杂。", "达·芬奇（文艺复兴巨匠）"),
    ("伟大的产品不是被设计出来的，是被发现的。", "张一鸣（字节跳动创始人）"),
    ("技术是把双刃剑，但不拥抱它的代价更大。", "李开复（创新工场创始人）"),
    ("把每天当作最后一天来过，终有一天你会对的。", "史蒂夫·乔布斯（苹果创始人）"),
    ("数据是新的石油。", "克莱夫·亨比（数学家）"),
]


def generate_calendar_card():
    now = datetime.now(BJT)
    year = now.strftime("%Y")
    month_num = now.month
    month_en = now.strftime("%b").upper()
    day = now.strftime("%d")
    weekday = WEEKDAY_MAP[now.weekday()]
    random.seed(now.strftime("%Y%m%d"))
    quote_text, quote_author = random.choice(TECH_QUOTES)
    yi = random.choice(YI_OPTIONS)
    ji = random.choice(JI_OPTIONS)

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
本文内容仅为科技行业资讯整理与个人分析，信息来源包括路透社、彭博社、TechCrunch、The Verge、Hacker News、CNBC等国际主流科技媒体的公开报道。本文不代表任何立场，不构成任何投资建议。如有疏漏，欢迎留言指正。
</p>
</section>
"""


# ===== 连续性追踪：读取/保存前一天的总结 =====

LAST_SUMMARY_FILE = "last_summary.txt"

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
        # Git commit 保存到仓库
        subprocess.run(["git", "config", "user.name", "Tech Daily Bot"], check=False)
        subprocess.run(["git", "config", "user.email", "bot@tech-daily.com"], check=False)
        subprocess.run(["git", "add", LAST_SUMMARY_FILE], check=False)
        subprocess.run(["git", "commit", "-m", "auto: update last summary"], check=False)
        subprocess.run(["git", "push"], check=False)
        print(f"  昨日总结已保存并推送到仓库")
    except Exception as e:
        print(f"  保存总结失败: {e}")

def extract_summary_from_html(html_text):
    match = re.search(r'三句话说清楚</p>(.*?)</section>', html_text, re.DOTALL)
    if match:
        text = re.sub(r'<[^>]+>', '', match.group(1))
        return text.strip()
    return ""


def get_time_range():
    now_bjt = datetime.now(BJT)
    end_time = now_bjt.replace(hour=7, minute=0, second=0, microsecond=0)
    if now_bjt.hour < 7:
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
                desc = item.find("description").text if item.find("description") is not None else ""
                all_articles.append(f"[Google News] 来源: {source}\n标题: {title}\n时间: {pub_date}\n描述: {desc}")
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
                articles.append(f"[NewsAPI] 来源: {source}\n标题: {a['title']}\n摘要: {a['description']}\n片段: {(a.get('content') or '')[:400]}")
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
                    articles.append(f"[Hacker News] 来源: {domain}\n标题: {title}\n热度: {score}分")
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
            desc = re.sub(r'<[^>]+>', '', item.find("description").text or "")[:300] if item.find("description") is not None else ""
            articles.append(f"[TechCrunch] 来源: TechCrunch\n标题: {title}\n时间: {pub_date}\n描述: {desc}")
        print(f"TechCrunch: {len(articles)} 条")
        return articles
    except Exception as e:
        print(f"TechCrunch 失败: {e}")
        return []


def generate_cover_image(title_text):
    prompt = f"A clean flat illustration about: {title_text}. Blue and white color scheme, modern minimalist tech style. Elements: circuits, chips, robots, data streams, rockets. NO TEXT, NO WORDS, NO LETTERS, NO WATERMARKS anywhere in the image. No human faces. Horizontal composition, professional and futuristic."

    try:
        resp = requests.post(
            "https://ark.cn-beijing.volces.com/api/v3/images/generations",
            headers={"Authorization": f"Bearer {DOUBAO_KEY}", "Content-Type": "application/json"},
            json={
                "model": "doubao-seedream-4-0-250828",
                "prompt": prompt,
                "size": "1296x720",
                "n": 1,
            },
            timeout=60,
        )
        data = resp.json()
        if "data" in data and len(data["data"]) > 0:
            image_url = data["data"][0].get("url", "")
            if image_url:
                print(f"封面图生成成功: {image_url[:80]}...")
                return image_url
            b64 = data["data"][0].get("b64_json", "")
            if b64:
                print("封面图生成成功 (base64)")
                return f"data:image/png;base64,{b64}"
        print(f"封面图生成失败: {data}")
        return None
    except Exception as e:
        print(f"封面图请求失败: {e}")
        return None


def deepseek_draft(news_text, last_summary=""):
    start_time, end_time = get_time_range()
    date_range = f"{start_time.strftime('%m月%d日 %H:%M')} ~ {end_time.strftime('%m月%d日 %H:%M')}（北京时间）"

    continuity = ""
    if last_summary:
        continuity = f"""
【重要】昨天的简报结尾提到了以下内容，如果今天的新闻里有相关进展，请在对应新闻中提一句"昨天我们提到的XXX，今天有了新进展——"，形成连续追踪感：
---
{last_summary}
---
"""

    prompt = f"""你是一位资深科技记者。请根据以下新闻素材，整理出一份科技日报初稿。

时间窗口：{date_range}
{continuity}
要求：
1. 从所有新闻中筛选出最有价值的5-7条
2. 同一事件合并，多信源交叉验证
3. 按重要性排列
4. 每条包含：标题、核心事实（1-3句）、分析点评（1-2句）
5. 不要使用任何emoji图标
6. 如果某条新闻只有单一信源，标注"（单一信源，待验证）"
7. 涉及具体数据，不同信源不一致时取保守值并标注"约"
8. 开头写一个总标题（吸引人但不夸张，不要用"炸锅""震惊""疯了"这类词）
9. 开头写1-2句引言概括今天核心看点
10. 结尾写三句话总结：最重要的一件事、钱往哪儿流、接下来看什么
11. 如果昨天的"接下来看什么"在今天有了进展，务必在相关新闻中回顾提及

来源翻译：TechCrunch→TechCrunch, Bloomberg→彭博社, Reuters→路透社, CNBC→CNBC, WSJ→华尔街日报, Hacker News→Hacker News

用纯文本输出，不要HTML标签，不要emoji。每条新闻格式：
---
标题
据XX消息，xxxxx
点评：xxxxx
---

新闻素材：
{news_text}"""

    try:
        resp = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"},
            json={"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "max_tokens": 3000},
            timeout=90,
        )
        data = resp.json()
        if "choices" not in data:
            print(f"DeepSeek 错误: {data}")
            return None
        draft = data["choices"][0]["message"]["content"]
        print(f"DeepSeek 初稿生成完成 ({len(draft)} 字)")
        return draft
    except Exception as e:
        print(f"DeepSeek 请求失败: {e}")
        return None


def doubao_polish(draft):
    prompt = f"""你是"鹏眼观天下"公众号的主编。你的读者是普通人——可能是上班族、大学生、宝妈、小老板，他们对科技感兴趣但不是从业者，很多专业名词他们不懂。你的任务是把初稿改写成"让不懂科技的人也能看得津津有味"的公众号文章。

## 第一：事实校验
- 检查初稿中是否有逻辑矛盾或不合理信息
- 标注了"单一信源，待验证"的内容，用谨慎措辞（"据报道""有消息称"）
- 发现明显错误直接修正或删除

## 第二：面向科技小白的改写（最重要！）

### 核心原则：像给朋友科普一样写
- 你的读者没听过 Anthropic、RISC-V、CoreWeave 这些名字
- 每个专业名词/公司名第一次出现时，加一句大白话解释
  好的示例："Anthropic（就是做Claude的那家公司，ChatGPT最大的对手）"
  不好的示例：直接写 "Anthropic发布了新模型"——读者不知道这是谁

### 多用生活化类比
  好的示例："AI模型蒸馏是什么意思？打个比方，你花了十个亿研发出一道招牌菜的配方，结果有人尝了一口就仿制出了八成味道——大概就是这个意思。"

### 告诉读者"这和你有什么关系"
  每条点评最后加一句和普通人相关的话

### 连续追踪
  如果初稿中有"昨天我们提到"这类回顾内容，一定保留并自然地融入正文，让读者感受到"这个号一直在跟踪事件进展"

### 开头钩子（非常重要！）
  引言部分要用悬念、反差或好奇心来钩住读者
  好的示例："你敢信吗？做ChatGPT的公司，今天居然公开说'我怕对手'。"
  不好的示例："今天科技圈发生了几件大事。"

### 标题要求
  - 吸引人但不浮夸，不要用"炸锅""震惊""疯了""核弹级"
  - 用具体信息引发好奇心

### 语气要求
- 像一个懂行的朋友在饭桌上给你讲新鲜事
- 可以用"说白了""换句话说""你可以理解为"
- 偶尔带点幽默但不油腻
- 不要用"赋能""生态""闭环""底层逻辑""范式转移"
- 不要使用任何emoji图标

## 第三：公众号排版
直接输出微信公众号兼容的HTML，所有样式内联。不要使用任何emoji。

总标题：
<p style="font-size:22px;font-weight:900;color:#1a1a1a;line-height:1.4;margin:0 0 20px;">总标题</p>

引言（钩子）：
<section style="background:#f0f7ff;padding:14px 16px;border-left:4px solid #1a73e8;margin-bottom:28px;">
<p style="font-size:15px;color:#333;line-height:1.9;margin:0;">引言——让人忍不住往下看</p>
</section>

每条新闻：
<section style="margin-bottom:8px;">
<p style="font-size:18px;font-weight:bold;color:#1a73e8;line-height:1.5;margin:0 0 10px;">标题——大白话，不要emoji</p>
<p style="font-size:15px;color:#333;line-height:1.9;margin:0 0 10px;">正文（专业名词加括号解释）</p>
<section style="background:#f0f7ff;padding:10px 14px;border-radius:6px;margin:0 0 8px;">
<p style="font-size:14px;color:#555;font-style:italic;line-height:1.9;margin:0;">鹏眼点评：分析+和普通人的关系</p>
</section>
</section>
<p style="border-top:1px solid #eee;margin:24px 0;height:0;"></p>

结尾要点：
<section style="background:#e8f0fe;padding:18px;border-radius:8px;margin-top:28px;">
<p style="font-size:18px;font-weight:bold;color:#1a73e8;margin:0 0 12px;">今天的科技圈，三句话说清楚</p>
<p style="font-size:14px;color:#555;line-height:1.9;margin:0 0 10px;">1. 最重要的一件事：xxxx</p>
<p style="font-size:14px;color:#555;line-height:1.9;margin:0 0 10px;">2. 钱往哪儿流：xxxx</p>
<p style="font-size:14px;color:#555;line-height:1.9;margin:0;">3. 接下来看什么：xxxx</p>
</section>

## 严格禁止
- 不要用代码块
- 不要用markdown加粗语法，用<b>标签
- 不要用h1 h2 h3标签，用p加内联style
- 不要用div标签，用section
- 不要使用任何emoji图标
- 不要加免责声明和日历卡片（代码自动追加）
- 不要在底部单独列来源
- 专业名词不能不加解释直接出现
- 标题不要浮夸词汇

初稿内容：
{draft}"""

    try:
        resp = requests.post(
            "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
            headers={"Authorization": f"Bearer {DOUBAO_KEY}", "Content-Type": "application/json"},
            json={"model": "doubao-seed-2-0-pro-260215", "messages": [{"role": "user", "content": prompt}], "max_tokens": 4000},
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


def extract_title(html_text):
    match = re.search(r'font-size:22px[^>]*>(.*?)</p>', html_text)
    if match:
        title = re.sub(r'<[^>]+>', '', match.group(1))
        return title.strip()
    return "科技行业每日速递"


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

    # 0. 读取昨日总结
    print("=== 0/7 读取昨日总结 ===")
    last_summary = read_last_summary()

    # 1. 抓取新闻
    print("=== 1/7 抓取新闻 ===")
    print("  Google News...")
    google_articles = fetch_google_news()
    print("  NewsAPI...")
    newsapi_articles = fetch_newsapi()
    print("  Hacker News...")
    hn_articles = fetch_hackernews()
    print("  TechCrunch...")
    tc_articles = fetch_techcrunch_rss()

    all_articles = google_articles + newsapi_articles + hn_articles + tc_articles
    news_text = "\n\n".join(all_articles)

    if not news_text.strip():
        send_pushplus(title, "<p>今日暂无重大科技动态。</p>")
        print("无新闻，已发送空报")
    else:
        print(f"  共 {len(all_articles)} 条新闻")

        # 2. DeepSeek 初稿（带昨日总结）
        print("=== 2/7 DeepSeek 生成初稿 ===")
        draft = deepseek_draft(news_text, last_summary)

        if draft:
            # 3. 豆包润色
            print("=== 3/7 豆包润色+校验+排版 ===")
            polished = doubao_polish(draft)

            if polished:
                final = clean_response(polished)
            else:
                print("  豆包失败，使用DeepSeek初稿")
                final = f"<p style='color:#999;font-size:12px;'>（本期为初稿版本，润色服务暂时不可用）</p>\n{draft}"
        else:
            final = "<p>AI 摘要生成失败，请检查 DeepSeek API。</p>"

        # 4. 生成封面图
        print("=== 4/7 生成封面图 ===")
        article_title = extract_title(final)
        print(f"  封面主题: {article_title}")
        cover_url = generate_cover_image(article_title)
        if cover_url:
            cover_html = f'<section style="margin-bottom:20px;"><img src="{cover_url}" style="width:100%;border-radius:8px;" /></section>'
            final = cover_html + final
            print("  封面图已插入文章开头")
        else:
            print("  封面图生成失败，跳过")

        # 5. 日历卡片
        print("=== 5/7 生成日历卡片 ===")
        calendar = generate_calendar_card()

        # 6. 拼接：正文 + 日历卡片 + 免责声明（免责在最后）
        final = final + calendar + DISCLAIMER

        # 7. 推送
        print("=== 6/7 推送微信 ===")
        send_pushplus(title, final)

        # 8. 保存今日总结供明天使用
        print("=== 7/7 保存今日总结 ===")
        today_summary = extract_summary_from_html(final)
        if today_summary:
            save_summary(today_summary)
        else:
            print("  未提取到总结内容，跳过保存")

    print("全部完成!")
