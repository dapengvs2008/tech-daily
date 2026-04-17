import os, json, re, requests, random, subprocess
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree
from html.parser import HTMLParser

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

LAST_SUMMARY_FILE = "last_summary.txt"
LAST_QUOTES_FILE = "last_quotes.txt"
MAX_RECENT_QUOTES = 7


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


def extract_text_from_html(html_content, max_chars=1500):
    try:
        parser = TextExtractor()
        parser.feed(html_content)
        full_text = "\n".join(parser.texts)
        return full_text[:max_chars]
    except Exception:
        return ""


def fetch_article_fulltext(url, max_chars=1500):
    try:
        resp = requests.get(url, timeout=10, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        if resp.status_code != 200:
            return ""
        return extract_text_from_html(resp.text, max_chars)
    except Exception:
        return ""


def enrich_articles_with_fulltext(articles, max_fetch=10):
    enriched = []
    fetch_count = 0
    for article in articles:
        if fetch_count < max_fetch:
            url_match = re.search(r'链接: (https?://\S+)', article)
            url = ""
            if url_match:
                url = url_match.group(1)
            if url and "news.google.com" not in url:
                fulltext = fetch_article_fulltext(url)
                if fulltext and len(fulltext) > 100:
                    article += f"\n【全文摘要】{fulltext}"
                    fetch_count += 1
                    print(f"    全文抓取成功: {url[:60]}... ({len(fulltext)}字)")
        enriched.append(article)
    return enriched


def read_recent_quotes():
    try:
        with open(LAST_QUOTES_FILE, "r", encoding="utf-8") as f:
            quotes = [line.strip() for line in f.readlines() if line.strip()]
            return quotes[-MAX_RECENT_QUOTES:]
    except FileNotFoundError:
        return []


def save_recent_quote(quote_text):
    try:
        quotes = read_recent_quotes()
        quotes.append(quote_text)
        quotes = quotes[-MAX_RECENT_QUOTES:]
        with open(LAST_QUOTES_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(quotes))
        subprocess.run(["git", "add", LAST_QUOTES_FILE], check=False)
        subprocess.run(["git", "commit", "-m", "auto: update recent quotes"], check=False)
        subprocess.run(["git", "push"], check=False)
        print(f"  名言已加入去重列表")
    except Exception as e:
        print(f"  保存名言失败: {e}")


def generate_calendar_card(quote_text="", quote_author=""):
    now = datetime.now(BJT)
    year = now.strftime("%Y")
    month_num = now.month
    month_en = now.strftime("%b").upper()
    day = now.strftime("%d")
    weekday = WEEKDAY_MAP[now.weekday()]
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
        subprocess.run(["git", "config", "user.name", "Tech Daily Bot"], check=False)
        subprocess.run(["git", "config", "user.email", "bot@tech-daily.com"], check=False)
        subprocess.run(["git", "add", LAST_SUMMARY_FILE], check=False)
        subprocess.run(["git", "commit", "-m", "auto: update last summary"], check=False)
        subprocess.run(["git", "push"], check=False)
        print(f"  今日总结已保存")
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


def generate_cover_image(title_text):
    prompt = f"A clean flat illustration about: {title_text}. Blue and white color scheme, modern minimalist tech style. Elements: circuits, chips, robots, data streams, rockets. NO TEXT, NO WORDS, NO LETTERS, NO WATERMARKS anywhere in the image. No human faces. Horizontal composition, professional and futuristic."
    try:
        resp = requests.post(
            "https://ark.cn-beijing.volces.com/api/v3/images/generations",
            headers={"Authorization": f"Bearer {DOUBAO_KEY}", "Content-Type": "application/json"},
            json={"model": "doubao-seedream-4-0-250828", "prompt": prompt, "size": "1024x1024", "n": 1},
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
                return f"data:image/png;base64,{b64}"
        print(f"封面图生成失败: {data}")
        return None
    except Exception as e:
        print(f"封面图请求失败: {e}")
        return None


def deepseek_draft(news_text, last_summary="", recent_quotes=None):
    start_time, end_time = get_time_range()
    date_range = f"{start_time.strftime('%m月%d日 %H:%M')} ~ {end_time.strftime('%m月%d日 %H:%M')}（北京时间）"

    continuity = ""
    if last_summary:
        continuity = f"""
【昨日回顾】如果今天的新闻里有相关进展，请在对应新闻中提一句"昨天我们提到的XXX，今天有了新进展——"：
{last_summary}
"""

    quote_avoid = ""
    if recent_quotes:
        quote_avoid = f"\n【避开以下最近用过的名言】：\n" + "\n".join(recent_quotes)

    prompt = f"""你是一位严谨的科技记者。请根据以下新闻素材，整理出一份准确的科技日报初稿。

时间窗口：{date_range}
{continuity}{quote_avoid}

## 核心原则：宁缺毋滥，准确优先

1. **只写你100%确定的内容**。如果某条新闻的信息不充分（只有标题、没有全文、或者表述模糊），宁可跳过这条，也不要自己脑补细节。

2. **区分"事实"和"推断"**：
   - 只写新闻素材中明确说到的内容
   - 不要自己补充"这意味着""这说明""预计"等推断性内容作为事实
   - 点评部分可以有分析，但必须基于明确的事实

3. **易混淆场景特别注意**：
   - "产品本身有漏洞" vs "产品能发现别人系统的漏洞"
   - "被起诉" vs "起诉别人"
   - "限制发布" vs "停止开发"
   - "考虑退出" vs "已经退出"
   - "计划投资" vs "已经投资"
   - "达成协议" vs "正在谈判"
   如果新闻素材中表述不清晰，用"据悉""有消息称"等模糊措辞，并在末尾标注"（细节待确认）"

4. **带【全文摘要】的新闻优先选用**。只有标题和短描述的新闻，如果涉及敏感话题（诉讼、安全、政府行动、并购金额），除非全文摘要能确认细节，否则不要写进简报。

5. **数据保守处理**：
   - 金额、百分比、排名等，不同信源不一致时取保守值
   - 涉及具体数字时加"约""超过"等限定词
   - 没明确数字的不要自己估算

## 写作要求

1. 筛选最重要、最确定的 4-6 条新闻（不是越多越好，准确比数量重要）
2. 同一事件合并
3. 按重要性排列
4. 每条包含：标题（事实陈述型，不夸张）、事实描述（只写确定的）、点评（基于事实的分析）
5. 不要使用任何emoji图标
6. 正文中不要写"据XX报道"，直接陈述事实
7. 开头写一个总标题（平实准确，不要用"炸锅""震惊""疯了"这类词）
8. 开头写1-2句引言概括今天核心看点（保守措辞）
9. 结尾写三句话总结：最重要的一件事、钱往哪儿流、接下来看什么

## 名言要求

最后单独一行输出一句和今天内容主题最相关的名人名言，格式为：今日名言：内容——作者（身份）
**务必避开【避开以下最近用过的名言】中的内容**，选择不同的名言。

来源翻译：TechCrunch→TechCrunch, Bloomberg→彭博社, Reuters→路透社, CNBC→CNBC, WSJ→华尔街日报, Hacker News→Hacker News

用纯文本输出，不要HTML标签，不要emoji。每条新闻格式：
---
标题
xxxxx（只写确定的事实）
点评：xxxxx
---

新闻素材：
{news_text}"""

    try:
        resp = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"},
            json={"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "max_tokens": 3000},
            timeout=120,
        )
        data = resp.json()
        if "choices" not in data:
            print(f"DeepSeek 错误: {data}")
            return None, "", ""
        draft = data["choices"][0]["message"]["content"]
        print(f"DeepSeek 初稿生成完成 ({len(draft)} 字)")

        quote_text = ""
        quote_author = ""
        quote_match = re.search(r'今日名言[：:]\s*(.+?)——(.+)', draft)
        if quote_match:
            quote_text = quote_match.group(1).strip().strip('"').strip('\u201c').strip('\u201d')
            quote_author = quote_match.group(2).strip()
            print(f"  今日名言: {quote_text} —— {quote_author}")
            draft = re.sub(r'今日名言[：:].*', '', draft).strip()

        return draft, quote_text, quote_author
    except Exception as e:
        print(f"DeepSeek 请求失败: {e}")
        return None, "", ""


def doubao_factcheck(draft, news_text):
    prompt = f"""你是一位严格的事实核查编辑。请对照【原始新闻素材】，审核【初稿】中每条新闻的事实准确性。

你的任务：
1. 逐条检查初稿中的每个事实陈述是否有原始素材支持
2. 找出推断性、夸大或不准确的表述
3. 发现易混淆的错误（例如"有漏洞"vs"能发现漏洞"、"被起诉"vs"起诉别人"）
4. 输出修正后的初稿

【修正原则】
- 原始素材没有明确说的内容，要么删掉，要么改为"据悉""据报道"等模糊措辞
- 具体数字如果和素材不一致，改成素材中的数字
- 明显错误直接修正
- 如果某条新闻整体不准确或信息不足，可以整条删掉
- 保持原初稿的格式结构（总标题、引言、各条新闻、三句话总结）

【原始新闻素材】
{news_text[:8000]}

【初稿】
{draft}

请直接输出修正后的完整初稿（保持纯文本格式，不要加说明或评论）。"""

    try:
        resp = requests.post(
            "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
            headers={"Authorization": f"Bearer {DOUBAO_KEY}", "Content-Type": "application/json"},
            json={"model": "doubao-seed-2-0-pro-260215", "messages": [{"role": "user", "content": prompt}], "max_tokens": 3500},
            timeout=180,
        )
        data = resp.json()
        if "choices" not in data:
            print(f"豆包核查错误: {data}")
            return draft
        result = data["choices"][0]["message"]["content"]
        print(f"豆包事实核查完成 ({len(result)} 字)")
        return result
    except Exception as e:
        print(f"豆包核查失败: {e}，使用原初稿")
        return draft


def doubao_polish(draft):
    prompt = f"""你是"鹏眼观天下"公众号的主编。请把已通过事实核查的初稿改写成面向普通读者的公众号文章。

读者画像：普通人，上班族、大学生、宝妈、小老板，对科技感兴趣但不是从业者。

## 改写原则

### 严守事实底线
- 绝对不要添加初稿中没有的事实、数据、人物、事件
- 只做语言润色和结构优化
- 如果某个表述不确定，宁可用"据报道""有消息称"等谨慎措辞

### 面向小白
- 每个专业名词/公司名第一次出现时，加一句大白话解释
  示例："Anthropic（做Claude AI的那家公司，ChatGPT最大的对手）"
- 用生活化类比解释复杂概念
- 每条点评最后加一句"这和你有什么关系"

### 开头钩子
  引言用悬念或好奇心钩住读者，但要基于真实信息，不要夸张

### 标题要求
  - 平实但吸引人，不要"炸锅""震惊""疯了""核弹级"
  - 标题必须准确反映内容，不能标题党

### 语气
- 像懂行朋友在聊天
- 用"说白了""换句话说""你可以理解为"
- 不要用"赋能""生态""闭环""底层逻辑""范式转移"
- 不要emoji

## 排版要求

直接输出微信公众号兼容的HTML，所有样式内联。不要使用任何emoji。

总标题：
<p style="font-size:22px;font-weight:900;color:#1a1a1a;line-height:1.4;margin:0 0 20px;">总标题</p>

引言：
<section style="background:#f0f7ff;padding:14px 16px;border-left:4px solid #1a73e8;margin-bottom:28px;">
<p style="font-size:16px;color:#333;line-height:1.9;margin:0;">引言</p>
</section>

每条新闻：
<section style="margin-bottom:8px;">
<p style="font-size:18px;font-weight:bold;color:#1a73e8;line-height:1.5;margin:0 0 10px;">标题——大白话，不要emoji</p>
<p style="font-size:16px;color:#333;line-height:1.9;margin:0 0 10px;">正文（专业名词加括号解释）</p>
<section style="background:#f0f7ff;padding:10px 14px;border-radius:6px;margin:0 0 8px;">
<p style="font-size:15px;color:#555;line-height:1.9;margin:0;">鹏眼点评：分析+和普通人的关系</p>
</section>
</section>
<p style="border-top:1px solid #eee;margin:24px 0;height:0;"></p>

结尾要点：
<section style="background:#e8f0fe;padding:18px;border-radius:8px;margin-top:28px;">
<p style="font-size:18px;font-weight:bold;color:#1a73e8;margin:0 0 12px;">今天的科技圈，三句话说清楚</p>
<p style="font-size:15px;color:#555;line-height:1.9;margin:0 0 10px;">1. 最重要的一件事：xxxx</p>
<p style="font-size:15px;color:#555;line-height:1.9;margin:0 0 10px;">2. 钱往哪儿流：xxxx</p>
<p style="font-size:15px;color:#555;line-height:1.9;margin:0;">3. 接下来看什么：xxxx</p>
</section>

## 严格禁止
- 添加初稿中没有的事实
- 代码块、markdown语法
- h1 h2 h3标签、div标签
- 任何emoji
- 免责声明和日历卡片（代码自动追加）
- 正文中标注来源
- 斜体

核查后的初稿：
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
            print(f"豆包润色错误: {data}")
            return None
        result = data["choices"][0]["message"]["content"]
        print(f"豆包润色完成 ({len(result)} 字)")
        return result
    except Exception as e:
        print(f"豆包润色失败: {e}")
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

    print("=== 0/9 读取历史记录 ===")
    last_summary = read_last_summary()
    recent_quotes = read_recent_quotes()
    if recent_quotes:
        print(f"  已读取最近{len(recent_quotes)}条名言用于去重")

    print("=== 1/9 抓取新闻 ===")
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

        print("=== 2/9 抓取新闻全文 ===")
        all_articles = enrich_articles_with_fulltext(all_articles, max_fetch=10)
        news_text = "\n\n".join(all_articles)

        print("=== 3/9 DeepSeek 生成初稿（保守模式）===")
        draft, quote_text, quote_author = deepseek_draft(news_text, last_summary, recent_quotes)

        if draft:
            print("=== 4/9 豆包独立事实核查 ===")
            draft = doubao_factcheck(draft, news_text)

            print("=== 5/9 豆包润色+排版 ===")
            polished = doubao_polish(draft)

            if polished:
                final = clean_response(polished)
            else:
                print("  豆包润色失败，使用核查后初稿")
                final = f"<p style='color:#999;font-size:12px;'>（本期为初稿版本，润色服务暂时不可用）</p>\n{draft}"
        else:
            final = "<p>AI 摘要生成失败，请检查 DeepSeek API。</p>"
            quote_text = ""
            quote_author = ""

        print("=== 6/9 生成封面图 ===")
        article_title = extract_title(final)
        print(f"  封面主题: {article_title}")
        cover_url = generate_cover_image(article_title)
        if cover_url:
            cover_html = f'<section style="margin-bottom:28px;"><img src="{cover_url}" style="width:100%;border-radius:8px;" /></section>'
            final = cover_html + final

        print("=== 7/9 生成日历卡片 ===")
        if quote_text:
            print(f"  今日名言: {quote_text}")
        calendar = generate_calendar_card(quote_text, quote_author)

        final = final + calendar + DISCLAIMER

        print("=== 8/9 推送微信 ===")
        send_pushplus(title, final)

        print("=== 9/9 保存历史记录 ===")
        today_summary = extract_summary_from_html(final)
        if today_summary:
            save_summary(today_summary)
        if quote_text:
            save_recent_quote(quote_text)

    print("全部完成!")
