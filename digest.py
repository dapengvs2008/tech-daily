import os, json, re, requests, random
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
<section style="margin:32px auto 0;max-width:360px;">
<section style="background:#fff;border-radius:12px;overflow:hidden;border:1px solid #e8e8e8;">
<section style="background:#c0392b;padding:10px 20px;display:flex;justify-content:space-between;align-items:center;">
<p style="font-size:14px;font-weight:700;color:#fff;letter-spacing:2px;margin:0;">鹏眼观天下</p>
<p style="font-size:13px;font-weight:700;color:rgba(255,255,255,0.8);margin:0;">{month_num}月 {month_en}</p>
</section>
<section style="padding:20px 20px 14px;text-align:center;background:#fff;">
<p style="font-size:13px;color:#999;letter-spacing:4px;margin:0;">{year}</p>
<p style="font-size:80px;font-weight:900;color:#c0392b;line-height:1;margin:4px 0;font-family:Georgia,serif;">{day}</p>
<p style="font-size:15px;color:#666;letter-spacing:4px;margin:0 0 12px;">{weekday}</p>
<section style="display:flex;justify-content:center;gap:24px;margin-bottom:4px;">
<p style="font-size:13px;color:#666;margin:0;"><span style="font-size:12px;padding:2px 8px;border-radius:4px;font-weight:700;background:#fef0f0;color:#c0392b;">宜</span> {yi}</p>
<p style="font-size:13px;color:#666;margin:0;"><span style="font-size:12px;padding:2px 8px;border-radius:4px;font-weight:700;background:#f0f0f0;color:#999;">忌</span> {ji}</p>
</section>
</section>
<section style="border-top:1px solid #f0f0f0;padding:14px 20px;background:#fafafa;">
<p style="font-size:14px;color:#333;line-height:1.7;text-align:center;margin:0 0 6px;">"{quote_text}"</p>
<p style="font-size:12px;color:#999;text-align:center;margin:0;">—— {quote_author}</p>
</section>
<section style="padding:8px 20px;display:flex;justify-content:space-between;font-size:11px;color:#ccc;">
<p style="margin:0;">鹏眼观天下</p>
<p style="margin:0;">全球视野 / 科技洞察</p>
</section>
</section>
</section>
"""


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


def deepseek_draft(news_text):
    start_time, end_time = get_time_range()
    date_range = f"{start_time.strftime('%m月%d日 %H:%M')} ~ {end_time.strftime('%m月%d日 %H:%M')}（北京时间）"

    prompt = f"""你是一位资深科技记者。请根据以下新闻素材，整理出一份科技日报初稿。

📅 时间窗口：{date_range}

要求：
1. 从所有新闻中筛选出最有价值的5-7条
2. 同一事件合并，多信源交叉验证
3. 按重要性排列
4. 每条包含：分类emoji + 标题、核心事实（1-3句）、分析点评（1-2句）
5. 如果某条新闻只有单一信源，标注"（单一信源，待验证）"
6. 涉及具体数据（金额、百分比等），如果不同信源不一致，取保守值并标注"约"
7. 开头写一个总标题，概括今天最重磅的事
8. 开头写1-2句引言概括今天核心看点
9. 结尾写"今日科技圈要点"：最值得关注的趋势、资本信号、明天看什么

分类emoji：
🤖AI与大模型 📱消费科技 🚗智能出行 💰融资与并购 🏢大厂动态 🔬前沿技术 📊财报与市场 🔥社区热议

来源翻译：TechCrunch→TechCrunch, Bloomberg→彭博社, Reuters→路透社, CNBC→CNBC, WSJ→华尔街日报, Hacker News→Hacker News

用纯文本输出，不要HTML标签。每条新闻格式：
---
分类emoji 标题
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
  好的示例："RISC-V（一种开源的芯片设计方案，类似安卓在手机系统里的角色）"
  不好的示例：直接写 "Anthropic发布了新模型"——读者不知道这是谁

### 多用生活化类比
  好的示例："AI模型蒸馏是什么意思？打个比方，你花了十个亿研发出一道招牌菜的配方，结果有人尝了一口就仿制出了八成味道——大概就是这个意思。"
  好的示例："Meta砸210亿买算力，相当于一口气买了一整栋写字楼的超级电脑。"
  不好的示例："Meta与CoreWeave签署算力基础设施合同"——太干了

### 告诉读者"这和你有什么关系"
  每条点评最后加一句和普通人相关的话：
  好的示例："对咱们普通用户来说，AI工具打价格战是好事，以后用ChatGPT可能更便宜。"
  好的示例："虽然听着离我们很远，但这种安全问题一旦出事，你的网银、社交账号都可能受影响。"

### 语气要求
- 像一个懂行的朋友在饭桌上给你讲今天看到的新鲜事
- 可以用"说白了""换句话说""你可以理解为"这类过渡
- 偶尔带点幽默："OpenAI这次也不装了，直接在文件里写'我怕对手抢生意'。"
- 不要用"赋能""生态""闭环""底层逻辑""范式转移"

## 第三：公众号排版
直接输出微信公众号兼容的HTML，所有样式内联。

总标题（要让不懂科技的人也想点进来）：
<p style="font-size:22px;font-weight:900;color:#1a1a1a;line-height:1.4;margin:0 0 20px;">总标题</p>

引言（一两句话勾起好奇心）：
<section style="background:#f0f7ff;padding:14px 16px;border-left:4px solid #1a73e8;margin-bottom:28px;">
<p style="font-size:15px;color:#333;line-height:1.9;margin:0;">引言内容</p>
</section>

每条新闻：
<section style="margin-bottom:8px;">
<p style="font-size:18px;font-weight:bold;color:#1a73e8;line-height:1.5;margin:0 0 10px;">【emoji 标题——用大白话，让人一看就懂】</p>
<p style="font-size:15px;color:#333;line-height:1.9;margin:0 0 10px;">正文（专业名词要加括号解释）</p>
<section style="background:#f0f7ff;padding:10px 14px;border-radius:6px;margin:0 0 8px;">
<p style="font-size:14px;color:#555;font-style:italic;line-height:1.9;margin:0;">💡 鹏眼点评：分析+和普通人的关系</p>
</section>
</section>
<p style="border-top:1px solid #eee;margin:24px 0;height:0;"></p>

结尾要点：
<section style="background:#e8f0fe;padding:18px;border-radius:8px;margin-top:28px;">
<p style="font-size:18px;font-weight:bold;color:#1a73e8;margin:0 0 12px;">📌 今天的科技圈，三句话说清楚</p>
<p style="font-size:14px;color:#555;line-height:1.9;margin:0 0 10px;">① <b>最重要的一件事</b>：xxxx（用大白话）</p>
<p style="font-size:14px;color:#555;line-height:1.9;margin:0 0 10px;">② <b>钱往哪儿流</b>：xxxx</p>
<p style="font-size:14px;color:#555;line-height:1.9;margin:0;">③ <b>接下来看什么</b>：xxxx</p>
</section>

## 严格禁止
- 不要用```代码块
- 不要用markdown的**加粗**，用<b>标签
- 不要用<h1><h2><h3>，用<p>加内联style
- 不要用<div>，用<section>
- 不要加免责声明和日历卡片（代码自动追加）
- 不要在底部单独列来源
- 专业名词不能不加解释直接出现

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

    print("=== 1/5 抓取新闻 ===")
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

        print("=== 2/5 DeepSeek 生成初稿 ===")
        draft = deepseek_draft(news_text)

        if draft:
            print("=== 3/5 豆包润色+校验+排版 ===")
            polished = doubao_polish(draft)

            if polished:
                final = clean_response(polished)
            else:
                print("  豆包失败，使用DeepSeek初稿")
                final = f"<p style='color:#999;font-size:12px;'>（本期为初稿版本，润色服务暂时不可用）</p>\n{draft}"
        else:
            final = "<p>AI 摘要生成失败，请检查 DeepSeek API。</p>"

        print("=== 4/5 生成日历卡片 ===")
        calendar = generate_calendar_card()
        final = final + DISCLAIMER + calendar

        print("=== 5/5 推送微信 ===")
        send_pushplus(title, final)

    print("全部完成!")
