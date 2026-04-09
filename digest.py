import os, json, re, requests, random
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree

NEWS_API_KEY   = os.environ["NEWS_API_KEY"]
DEEPSEEK_KEY   = os.environ["DEEPSEEK_API_KEY"]
PUSHPLUS_TOKEN = os.environ["PUSHPLUS_TOKEN"]

BJT = timezone(timedelta(hours=8))

# 科技名言库，每天随机选一条
TECH_QUOTES = [
    ("预测未来的最好方式，就是去创造它。", "艾伦·凯", "计算机科学家"),
    ("Stay hungry, stay foolish.", "史蒂夫·乔布斯", "苹果创始人"),
    ("任何足够先进的技术，都与魔法无异。", "亚瑟·克拉克", "科幻作家"),
    ("人工智能是人类最后的发明。", "尼克·博斯特罗姆", "哲学家"),
    ("最好的创业方式，是解决你自己遇到的问题。", "保罗·格雷厄姆", "Y Combinator 创始人"),
    ("如果你不感到尴尬，说明你发布得太晚了。", "里德·霍夫曼", "LinkedIn 创始人"),
    ("我们总是高估未来两年的变化，低估未来十年的变化。", "比尔·盖茨", "微软创始人"),
    ("创新区分了领导者和跟随者。", "史蒂夫·乔布斯", "苹果创始人"),
    ("大部分人高估了一年能做的事，低估了十年能做的事。", "比尔·盖茨", "微软创始人"),
    ("AI 不会取代人类，但会用 AI 的人会取代不用 AI 的人。", "黄仁勋", "英伟达 CEO"),
    ("快速行动，打破常规。", "马克·扎克伯格", "Meta CEO"),
    ("当一个行业即将被颠覆时，身在其中的人往往最后才察觉。", "克莱顿·克里斯坦森", "哈佛商学院教授"),
    ("不要因为走得太远，而忘记为什么出发。", "纪伯伦", "诗人"),
    ("软件正在吞噬世界。", "马克·安德森", "a16z 联合创始人"),
    ("真正的风险不是做得太多，而是做得太少。", "萨姆·奥特曼", "OpenAI CEO"),
    ("十年后你会因为没做的事而后悔，而不是因为做过的事。", "杰夫·贝索斯", "亚马逊创始人"),
    ("未来已来，只是分布不均匀。", "威廉·吉布森", "科幻作家"),
    ("最危险的事情不是人工智能有自己的意志，而是人类没有。", "尤瓦尔·赫拉利", "历史学家"),
    ("把每一天当作最后一天来过，有一天你会发现自己是对的。", "史蒂夫·乔布斯", "苹果创始人"),
    ("在一个变化越来越快的世界里，唯一的策略就是学习的速度比变化更快。", "埃里克·施密特", "谷歌前CEO"),
    ("我对 AI 的乐观，不是因为技术有多强，而是因为人类有多需要它。", "达里奥·阿莫代", "Anthropic CEO"),
    ("想象力比知识更重要。", "阿尔伯特·爱因斯坦", "物理学家"),
    ("第一步是确立一件事是可能的，然后概率就会发生。", "埃隆·马斯克", "特斯拉/SpaceX CEO"),
    ("伟大的产品不是被设计出来的，是被发现的。", "张一鸣", "字节跳动创始人"),
    ("所有的模型都是错的，但有些是有用的。", "乔治·博克斯", "统计学家"),
    ("技术是把双刃剑，但不拥抱它的代价更大。", "李开复", "创新工场创始人"),
    ("下一个大事件，永远看起来像玩具。", "克里斯·迪克森", "a16z 合伙人"),
    ("数据是新的石油。", "克莱夫·亨比", "数学家"),
    ("当你把世界上最聪明的人聚在一起，奇迹就会发生。", "拉里·佩奇", "谷歌联合创始人"),
    ("简洁是终极的复杂。", "达·芬奇", "文艺复兴巨匠"),
]

WEEKDAY_MAP = {
    0: "星 期 一", 1: "星 期 二", 2: "星 期 三",
    3: "星 期 四", 4: "星 期 五", 5: "星 期 六", 6: "星 期 日",
}

# 宜忌库
YI_OPTIONS = [
    "深度学习 拥抱变化", "大胆尝试 勇于创新", "独立思考 质疑权威",
    "专注执行 少刷手机", "跨界探索 打破边界", "复盘总结 持续迭代",
    "阅读论文 拓宽视野", "提出假设 验证想法", "协作共创 开放分享",
]
JI_OPTIONS = [
    "闭门造车", "盲目跟风", "纸上谈兵",
    "故步自封", "拖延症发作", "信息茧房",
    "过度优化", "完美主义", "只收藏不行动",
]


def generate_calendar_card():
    """自动生成每日日历卡片 HTML"""
    now = datetime.now(BJT)
    year = now.strftime("%Y")
    month_cn = f"{now.month}月"
    month_en = now.strftime("%b").capitalize()
    day = now.strftime("%d")
    weekday = WEEKDAY_MAP[now.weekday()]

    # 随机选名言、宜忌
    random.seed(now.strftime("%Y%m%d"))  # 每天固定随机种子，同一天多次运行结果一致
    quote_text, quote_author, quote_title = random.choice(TECH_QUOTES)
    yi = random.choice(YI_OPTIONS)
    ji = random.choice(JI_OPTIONS)

    card_html = f"""
<section style="margin-top:36px;width:100%;max-width:420px;margin-left:auto;margin-right:auto;">
<section style="background:linear-gradient(170deg,#0b1a3b 0%,#14305e 45%,#1a4080 100%);border-radius:16px;overflow:hidden;">

<section style="background:rgba(255,255,255,0.08);padding:14px 28px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid rgba(255,255,255,0.06);">
<p style="font-size:16px;font-weight:700;color:#fff;letter-spacing:3px;margin:0;">鹏眼观天下</p>
<p style="font-size:16px;font-weight:700;color:rgba(255,255,255,0.6);margin:0;font-family:sans-serif;">{month_cn} {month_en}</p>
</section>

<section style="padding:32px 28px 20px;text-align:center;">
<p style="font-size:18px;color:rgba(255,255,255,0.45);letter-spacing:6px;margin:0;font-family:sans-serif;">{year}</p>
<p style="font-size:120px;font-weight:900;color:#fff;line-height:1;margin:0;font-family:sans-serif;">{day}</p>
<p style="font-size:20px;color:rgba(255,255,255,0.55);letter-spacing:10px;margin:4px 0 20px;">{weekday}</p>

<section style="display:flex;justify-content:center;gap:36px;margin-bottom:24px;">
<p style="font-size:15px;color:rgba(255,255,255,0.7);margin:0;"><span style="font-size:13px;padding:3px 10px;border-radius:5px;font-weight:700;background:rgba(100,180,255,0.2);color:#7ab8ff;">宜</span> {yi}</p>
<p style="font-size:15px;color:rgba(255,255,255,0.7);margin:0;"><span style="font-size:13px;padding:3px 10px;border-radius:5px;font-weight:700;background:rgba(255,100,100,0.15);color:#ff8a8a;">忌</span> {ji}</p>
</section>
</section>

<section style="background:rgba(255,255,255,0.05);padding:24px 28px;border-top:1px solid rgba(255,255,255,0.06);">
<p style="font-size:18px;color:rgba(255,255,255,0.9);line-height:1.8;text-align:center;margin:0 0 12px;">"{quote_text}"</p>
<p style="font-size:14px;color:rgba(255,255,255,0.4);text-align:center;margin:0;">—— {quote_author}（{quote_title}）</p>
</section>

<section style="padding:14px 28px;display:flex;justify-content:space-between;font-size:12px;color:rgba(255,255,255,0.2);">
<p style="margin:0;">鹏眼观天下 · 每日科技简报</p>
<p style="margin:0;">全球视野 / 科技洞察</p>
</section>

</section>
</section>
"""
    return card_html


DISCLAIMER = """
<section style="margin-top:28px;padding:14px 16px;background:#f9f9f9;border-radius:6px;">
<p style="font-size:12px;color:#999;line-height:1.8;margin:0;">
<span style="color:#888;font-weight:bold;">免责声明</span><br/>
本文内容仅为科技行业资讯整理与个人分析，信息来源包括路透社、彭博社、TechCrunch、The Verge、Hacker News、CNBC等国际主流科技媒体的公开报道。本文不代表任何立场，不构成任何投资建议。如有疏漏，欢迎留言指正。
</p>
</section>
"""


def get_time_range():
    now_bjt = datetime.now(BJT)
    end_time = now_bjt.replace(hour=7, minute=0, second=0, microsecond=0)
    if now_bjt.hour < 7:
        end_time -= timedelta(days=1)
    start_time = end_time - timedelta(hours=24)
    return start_time, end_time


def fetch_google_news():
    """Google News RSS：主流科技媒体报道"""
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
                desc = ""
                if item.find("description") is not None:
                    desc = item.find("description").text or ""
                all_articles.append(f"[Google News] 来源: {source}\n标题: {title}\n发布时间: {pub_date}\n描述: {desc}")
        except Exception as e:
            print(f"Google News 抓取失败({q}): {e}")
    print(f"Google News 抓到 {len(all_articles)} 条")
    return all_articles


def fetch_newsapi():
    """NewsAPI：补充主流科技新闻"""
    start_time, end_time = get_time_range()
    from_date = start_time.strftime("%Y-%m-%dT%H:%M:%S")
    to_date = end_time.strftime("%Y-%m-%dT%H:%M:%S")
    try:
        resp = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": "(AI OR OpenAI OR Google OR Apple OR Nvidia OR Tesla OR Microsoft OR Meta OR startup OR funding) AND (launch OR release OR announce OR deal OR billion OR update)",
                "from": from_date,
                "to": to_date,
                "language": "en",
                "sortBy": "relevancy",
                "pageSize": 10,
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
                articles.append(
                    f"[NewsAPI] 来源: {source}\n标题: {a['title']}\n摘要: {a['description']}\n内容片段: {(a.get('content') or '')[:400]}"
                )
        print(f"NewsAPI 抓到 {len(articles)} 条")
        return articles
    except Exception as e:
        print(f"NewsAPI 抓取失败: {e}")
        return []


def fetch_hackernews():
    """Hacker News：技术社区热门话题"""
    try:
        resp = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=15)
        story_ids = resp.json()[:20]
        articles = []
        for sid in story_ids:
            try:
                item = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json", timeout=10).json()
                if not item or item.get("type") != "story":
                    continue
                title = item.get("title", "")
                score = item.get("score", 0)
                url = item.get("url", "")
                tech_keywords = ["ai", "gpt", "llm", "openai", "google", "apple", "nvidia", "tesla",
                                 "microsoft", "meta", "startup", "funding", "chip", "robot", "model",
                                 "launch", "release", "billion", "acquisition", "open source",
                                 "anthropic", "gemini", "claude", "copilot", "agent", "autonomous"]
                title_lower = title.lower()
                is_tech = any(kw in title_lower for kw in tech_keywords)
                if score >= 100 or is_tech:
                    domain = url.split("/")[2] if url and "/" in url else "news.ycombinator.com"
                    articles.append(f"[Hacker News] 来源: {domain}\n标题: {title}\n热度: {score}分\n链接: {url}")
                if len(articles) >= 8:
                    break
            except Exception:
                continue
        print(f"Hacker News 抓到 {len(articles)} 条")
        return articles
    except Exception as e:
        print(f"Hacker News 抓取失败: {e}")
        return []


def fetch_techcrunch_rss():
    """TechCrunch RSS：行业深度报道"""
    url = "https://techcrunch.com/feed/"
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        root = ElementTree.fromstring(resp.content)
        articles = []
        for item in root.findall(".//item")[:10]:
            title = item.find("title").text or ""
            pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
            desc = ""
            if item.find("description") is not None:
                raw_desc = item.find("description").text or ""
                desc = re.sub(r'<[^>]+>', '', raw_desc)[:300]
            articles.append(f"[TechCrunch] 来源: TechCrunch\n标题: {title}\n发布时间: {pub_date}\n描述: {desc}")
        print(f"TechCrunch 抓到 {len(articles)} 条")
        return articles
    except Exception as e:
        print(f"TechCrunch 抓取失败: {e}")
        return []


def clean_response(text):
    text = re.sub(r'```html\s*', '', text)
    text = re.sub(r'```\s*$', '', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(
        r'<h3[^>]*>(.*?)</h3>',
        r'<p style="font-size:18px;font-weight:bold;color:#1a73e8;line-height:1.5;margin:20px 0 10px;">\1</p>',
        text
    )
    text = re.sub(
        r'<hr[^>]*/?>',
        '<p style="border-top:1px solid #eee;margin:24px 0;height:0;"></p>',
        text
    )
    return text.strip()


def summarize(news_text):
    start_time, end_time = get_time_range()
    date_range = f"{start_time.strftime('%m月%d日 %H:%M')} ~ {end_time.strftime('%m月%d日 %H:%M')}（北京时间）"

    prompt = f"""你是"鹏眼观天下"公众号的首席科技编辑。把下面的英文科技新闻改写成一篇有洞察力、有连续性的中文硅谷科技深度简报。

📅 本期时间窗口：{date_range}

## 信源说明
新闻来自4个渠道，标注了[Google News][NewsAPI][Hacker News][TechCrunch]，请综合利用：
- Google News / NewsAPI：主流媒体报道，关注大事件
- Hacker News：技术社区热点，关注前沿技术和开发者关注的话题
- TechCrunch：行业深度，关注融资、创业、产品发布

## 风格定位
- 参照"36氪""极客公园""品玩"的科技报道风格
- 语言专业但不枯燥，有观点有态度
- 关注商业逻辑和行业影响，不只是罗列产品参数
- Hacker News 的热门话题如果有趣，可以单独作为一条写

## 核心要求

### 1. 内容组织
- 开头先用1-2句话概括"过去24小时硅谷最值得关注的事"
- 按重要性排列，最重磅的新闻放在最前面
- 同一事件的多条新闻合并为一条
- 只保留真正有价值的新闻（5-7条），不要凑数
- 如果 Hacker News 有高热度的有趣话题，可以作为"社区热议"单独写一条

### 2. 分类标签（在标题前用emoji标注）
- 🤖 AI与大模型
- 📱 消费科技
- 🚗 智能出行
- 💰 融资与并购
- 🏢 大厂动态
- 🔬 前沿技术
- 📊 财报与市场
- 🔥 社区热议（来自Hacker News的热门话题）

### 3. 每条新闻格式（微信公众号兼容HTML）

<section style="margin-bottom:8px;">
<p style="font-size:18px;font-weight:bold;color:#1a73e8;line-height:1.5;margin:0 0 10px;">【emoji分类 标题，有洞察力和冲击力】</p>
<p style="font-size:15px;color:#333;line-height:1.9;margin:0 0 10px;">据XX消息，xxxxxxx（直接写内容，1-3句话。只标注一个核心来源）</p>
<section style="background:#f0f7ff;padding:10px 14px;border-radius:6px;margin:0 0 8px;">
<p style="font-size:14px;color:#555;font-style:italic;line-height:1.9;margin:0;">💡 鹏眼点评：这件事为什么重要？对行业意味着什么？对普通用户/开发者/投资者有什么影响？</p>
</section>
</section>
<p style="border-top:1px solid #eee;margin:24px 0;height:0;"></p>

### 4. 来源翻译
TechCrunch→TechCrunch，The Verge→The Verge，Bloomberg→彭博社，Reuters→路透社，CNBC→CNBC，WSJ→华尔街日报，The Information→The Information，Wired→连线杂志，Hacker News→Hacker News

### 5. 结尾板块

<section style="background:#e8f0fe;padding:18px;border-radius:8px;margin-top:28px;">
<p style="font-size:18px;font-weight:bold;color:#1a73e8;margin:0 0 12px;">📌 今日科技圈要点</p>
<p style="font-size:14px;color:#555;line-height:1.9;margin:0 0 10px;">① <b>最值得关注的趋势</b>：xxxx</p>
<p style="font-size:14px;color:#555;line-height:1.9;margin:0 0 10px;">② <b>资本信号</b>：xxxx</p>
<p style="font-size:14px;color:#555;line-height:1.9;margin:0;">③ <b>明天看什么</b>：xxxx</p>
</section>

### 6. 严格禁止
- 不要用```代码块
- 不要用markdown的**加粗**语法，如需加粗用<b>标签
- 不要用<h1><h2><h3>标签，全部用<p>加内联style
- 不要用<div>标签，全部用<section>
- 不要加"每日简报"之类的大标题
- 不要在底部单独列来源行
- 不要加免责声明（代码会自动追加）
- 不要加日历卡片（代码会自动追加）

### 7. 开头引言格式
<section style="background:#f0f7ff;padding:14px 16px;border-left:4px solid #1a73e8;margin-bottom:28px;">
<p style="font-size:15px;color:#333;line-height:1.9;margin:0;">过去24小时硅谷科技圈核心看点概括，1-2句话</p>
</section>

新闻原文（来自4个信源，注意去重合并、按重要性排列）：
{news_text}"""

    resp = requests.post(
        "https://api.deepseek.com/chat/completions",
        headers={
            "Authorization": f"Bearer {DEEPSEEK_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 4000,
        },
        timeout=90,
    )
    data = resp.json()
    if "choices" not in data:
        print(f"DeepSeek error: {data}")
        return f"<p>AI 摘要生成失败：{data.get('error', data)}</p>"
    return clean_response(data["choices"][0]["message"]["content"])


def send_pushplus(title, content):
    resp = requests.post(
        "http://www.pushplus.plus/send",
        json={
            "token": PUSHPLUS_TOKEN,
            "title": title,
            "content": content,
            "template": "html",
        },
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

    print("1/4 Google News...")
    google_articles = fetch_google_news()
    print("2/4 NewsAPI...")
    newsapi_articles = fetch_newsapi()
    print("3/4 Hacker News...")
    hn_articles = fetch_hackernews()
    print("4/4 TechCrunch...")
    tc_articles = fetch_techcrunch_rss()

    all_articles = google_articles + newsapi_articles + hn_articles + tc_articles
    news_text = "\n\n".join(all_articles)

    if not news_text.strip():
        send_pushplus(title, "<p>今日暂无重大科技动态。</p>")
    else:
        print(f"共获取 {len(all_articles)} 条新闻")
        print("生成科技深度简报...")
        summary = summarize(news_text)
        # 自动追加免责声明 + 日历卡片
        calendar = generate_calendar_card()
        summary = summary + DISCLAIMER + calendar
        print("推送微信...")
        send_pushplus(title, summary)

    print("完成!")
