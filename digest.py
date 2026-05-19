"""
科技日报 digest.py · v13.0-day2.1
=========================
v13.0 阶段二「换源」工程进行中。本文件为 Day 2.1 补丁。

v13.0 Day 2.1 改动(基于 Day 2 推送日志暴露的问题):
  1. IT之家/机器之心 RSS 抓取改用 ElementTree 标准 XML 解析
     - 原因:5/19 推送日志显示这两个源都抓到 0 条
     - 根因:原代码用纯正则匹配 <item>,RSS 格式有任何变化都会失败
     - 修复:换成 ElementTree.fromstring + findall(".//item")
  2. 历史查重阈值从 60% → 75%
     - 原因:误杀今日新闻"Sam Altman beat Elon Musk in court. Now ..."和"英伟达财报前夜黄仁勋戴尔访谈"
     - 修复:阈值放宽,只有完全相同关键词集合才判重
  3. NewsNow 每源 limit 20 → 30
     - 目的:让 4 个 NewsNow 源贡献的素材从 80 条 → 120 条
     - 给 DeepSeek 更大选择空间

v13.0 Day 2 改动(继承):
  1. Prompt 严格化「方案 A 边界」(修复 v13.0-day1.1 推送中的英文照搬问题)
     - 媒体名前置叙述/新闻标题/媒体报道描述 → 必须全部中译
     - 唯一保留英文原文的情况:具体人物原话(有引号),用「中译。原文:'EN'」格式
     - 加入 PBS / NYT / TechCrunch 错误案例的反面示例
  2. 新增 3 个 AI 公司官方源:
     - OpenAI 官方博客 RSS: openai.com/news/rss.xml
     - Google DeepMind 博客 RSS: deepmind.google/blog/rss.xml
     - Anthropic 官方公告: HTML 解析 anthropic.com/news(无 RSS,容错设计)
  3. 主流程素材池接入 3 个新源,lang="en",走方案 A 中译

v13.0 Day 1.1 改动(继承):
  - 新增 DISABLE_COVER_IMAGE 环境变量(暂停封面图)

v13.0 Day 1 改动(继承):
  - NEWSNOW_SOURCES 重构(踢 cls-hot/jin10,加 wallstreetcn-news)
  - PRIORITY_SOURCES 同步更新

v13.0 路线图:
  Day 1: ✓ NewsNow 源配置
  Day 1.1: ✓ 封面图开关
  Day 2: ✓ Prompt 修复 + AI 公司官方源(本文件)
  Day 3: 接 NVIDIA / Tesla / Apple 官方 + 量子位 / 新智元 / 虎嗅
  Day 4: 端到端测试 + 微调
  Day 5: 踢掉旧源(Google News / NewsAPI / Hacker News / TechCrunch)

v12.5.1 补丁(继承):
  1. 来源黑名单扩充:加 MSN/Yahoo News/新浪/网易/搜狐 等聚合器
  2. 多源拼接强制全量列:整合 2+ 素材时,所有真实信源都列出 (CNBC、财联社)
  3. 引语完整摘抄铁律:禁止截断引语,即使 50 字也要全文(防 v12.5 截断 Barry Diller 那种)
  4. 主谓关系核查铁律(新增铁律 4):防 SpaceX/Anthropic 主谓颠倒
  5. 字数下限改为摘抄项下限(方案 B):头条 5+ 事实,普通 3+ 事实,
     素材不足允许短,严禁用废话凑数

v12.5 关键升级:
  1. 防过期热点污染:last_titles.txt 持久化 7 天历史标题,双重查重
  2. _normalize_pub_time 兜底修复:解析失败时返回空字符串
  3. 标题改为 3 事件并列格式:「事件1; 事件2; 事件3」
  4. 新增今日头条板块(headline_event):1 条最重磅事件深度
  5. 新增要闻提示精选(top_news_titles):DeepSeek 输出 7-8 条精选短标题
  6. Prompt 重写为"严守事实三铁律"版本
  7. max_tokens:22000 → 32000
  8. 来源括号修正:写真实信源
  9. 英文源处理(方案 A):中译事实陈述,引语用「中译。原文:'EN'」格式

v12.4 保留特性:
  - 选题导向规则(车企不报销量、美股巨头报 AI 维度)
  - DSLR 真实摄影感封面 prompt(豆包 Seedream 4.5)
  - 日历卡 + 宜忌四字标签
  - NewsNow 中文一手快讯 + 跨源事实验证

英文源保留:Google News + NewsAPI + Hacker News + TechCrunch
中文源保留:IT之家 RSS + 机器之心 RSS + 36氪 RSS
中文源(NewsNow)保留:财联社 + 华尔街见闻 + 金十 + IT之家热门 + 36氪快讯
(注:阶段二 v13.0 会换源,本期 v12.5.1 暂不动)

环境变量:
  NEWS_API_KEY        NewsAPI 密钥(保留)
  DEEPSEEK_API_KEY    DeepSeek 密钥
  DOUBAO_API_KEY      豆包 Seedream 密钥
  PUSHPLUS_TOKEN      PushPlus 推送 token
  GITHUB_REPO         GitHub 仓库(默认 dapengvs2008/tech-daily)
  NEWSNOW_BASE_URL    NewsNow 实例 URL(默认 https://newsnow-dz3.pages.dev)
"""

import os, json, re, requests, random, subprocess, asyncio
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree
from html.parser import HTMLParser

# ============================================================
# 环境变量
# ============================================================
NEWS_API_KEY   = os.environ["NEWS_API_KEY"]
DEEPSEEK_KEY   = os.environ["DEEPSEEK_API_KEY"]
DOUBAO_KEY     = os.environ["DOUBAO_API_KEY"]
PUSHPLUS_TOKEN = os.environ["PUSHPLUS_TOKEN"]
GITHUB_REPO    = os.environ.get("GITHUB_REPO", "dapengvs2008/tech-daily")
NEWSNOW_BASE_URL = os.environ.get("NEWSNOW_BASE_URL", "https://newsnow-dz3.pages.dev")

# v13.0-day1.1 新增：封面图开关
# 设为 "1"/"true"/"yes"(大小写不敏感) 即跳过封面图整段（不调豆包、不 HTML 兜底）
# 未设或设为其他值 → 保持原有行为（生成封面图）
DISABLE_COVER_IMAGE = os.environ.get("DISABLE_COVER_IMAGE", "").strip().lower() in ("1", "true", "yes", "on")

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
    "勤学", "思考", "尝试", "创新", "质疑",
    "专注", "跨界", "复盘", "迭代", "阅读",
    "假设", "验证", "协作", "开源", "分享",
    "求真", "深耕", "破局", "精进", "复利",
]
JI_OPTIONS = [
    "盲从", "拖延", "内耗", "焦虑", "空想",
    "敷衍", "守旧", "封闭", "完美主义", "凑数",
    "刷屏", "硬撑", "跟风", "浅尝", "讳疾",
]


# ============================================================
# v11 原有：HTML 文本提取（保留不动）
# ============================================================
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
    """v11 保留：对部分文章抓取全文供 DeepSeek 整理使用"""
    enriched = []
    fetch_count = 0
    for article in articles:
        if isinstance(article, str):
            enriched.append(article)
            continue
        # v12 改动：直接修改 dict
        if fetch_count < max_fetch:
            url = article.get("url", "")
            if url and "news.google.com" not in url:
                fulltext = fetch_article_fulltext(url)
                if fulltext and len(fulltext) > 100:
                    article["fulltext"] = fulltext
                    fetch_count += 1
        enriched.append(article)
    return enriched

# ============================================================
# v11 原有：HTML 封面模板（兜底用，豆包失败时启用）
# 完整保留 v11 实现，未做改动
# ============================================================

COVER_TOPIC_COLORS = ["#1a73e8", "#0f9d58", "#f29900", "#7b1fa2", "#db4437", "#00acc1", "#ff6d00"]


def build_cover_html(main_title, sub_title, topics):
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


# ============================================================
# v11 原有：Playwright 截图（保留不动）
# ============================================================
async def render_cover_image(html_content, output_path):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 960, "height": 600}, device_scale_factor=2)
        await page.set_content(html_content, wait_until="networkidle")
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
    """v11 保留不动：把图片 commit 到仓库，返回 raw URL"""
    try:
        subprocess.run(["git", "config", "user.name", "Tech Daily Bot"], check=False)
        subprocess.run(["git", "config", "user.email", "bot@tech-daily.com"], check=False)
        pull_result = subprocess.run(["git", "pull", "--rebase"], capture_output=True, text=True)
        if pull_result.returncode != 0:
            print(f"  git pull 失败: {pull_result.stderr}")
        add_result = subprocess.run(["git", "add", image_path], capture_output=True, text=True)
        if add_result.returncode != 0:
            print(f"  git add 失败: {add_result.stderr}")
            return None
        timestamp = datetime.now(BJT).strftime("%Y-%m-%d %H:%M")
        commit_result = subprocess.run(
            ["git", "commit", "-m", f"auto: cover image {timestamp}"],
            capture_output=True, text=True
        )
        if commit_result.returncode != 0:
            if "nothing to commit" not in commit_result.stdout:
                return None
        push_result = subprocess.run(["git", "push"], capture_output=True, text=True)
        if push_result.returncode != 0:
            print(f"  git push 失败: {push_result.stderr}")
            return None
        print(f"  git push 成功")
        ts = int(datetime.now().timestamp())
        url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{image_path}?t={ts}"
        return url
    except Exception as e:
        print(f"  图片上传失败: {e}")
        return None

# ============================================================
# v11 原有：日历卡、农历、文件存储（保留不动）
# ============================================================
LAST_SUMMARY_FILE = "last_summary.txt"
LAST_QUOTES_FILE = "last_quotes.txt"
LAST_TITLES_FILE = "last_titles.txt"  # v12.5 新增：保存最近 7 天报道过的新闻标题（每行一条）


def read_recent_titles():
    """读取最近 7 天报道过的新闻标题，用于过滤已报道的过期热点。
    
    返回 dict：
      'normalized': set，每个元素是标题归一化形式（精确匹配用）
      'keywords': list，每个元素是该标题的关键词集合（模糊匹配用）
    """
    try:
        with open(LAST_TITLES_FILE, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
            normalized = set()
            keywords_list = []
            for line in lines:
                # 跳过日期分隔行
                if line.startswith("==="):
                    continue
                normalized.add(_normalize_title(line))
                kw = _extract_title_keywords(line)
                if kw:
                    keywords_list.append(kw)
            print(f"  读取到 {len(normalized)} 条历史报道标题（用于查重）")
            return {'normalized': normalized, 'keywords': keywords_list}
    except FileNotFoundError:
        print(f"  无历史标题文件（首次运行）")
        return {'normalized': set(), 'keywords': []}
    except Exception as e:
        print(f"  读取历史标题失败: {e}")
        return {'normalized': set(), 'keywords': []}


def _normalize_title(title):
    """标题归一化：去空白+全小写+去标点，用于精确匹配"""
    import re as _re
    s = (title or "").strip().lower()
    s = _re.sub(r"[\s,。、，：:；;！!？?\"'\u201c\u201d\u2018\u2019「」【】《》()（）\[\]\-—_]+", "", s)
    return s


def _extract_title_keywords(title):
    """从标题中提取核心词集合（实体名+关键动词），用于模糊匹配
    
    例如：
      'Meta 收购 Manus 被叫停' → {'meta', 'manus', '收购', '叫停'}
      '中国叫停 Meta 收购 Manus' → {'meta', 'manus', '收购', '叫停', '中国'}
    两者交集 4/5 ≥ 0.8 视为同一事件
    """
    import re as _re
    s = (title or "").strip().lower()
    # 抽取英文单词、中文公司名、核心动词
    # 已知重要实体词（可扩展）
    KEY_ENTITIES = [
        'openai', 'anthropic', 'claude', 'chatgpt', 'gpt', 'gemini', 'sora',
        'google', 'apple', 'meta', 'microsoft', 'nvidia', 'amazon', 'tesla',
        'deepseek', 'manus', 'kimi', 'qwen', 'doubao',
        # 版本号识别（用于"DeepSeek V4 发布" / "DeepSeek-V4 上线"匹配）
        'v3', 'v4', 'v5', 'gpt-5', 'gpt-6', 'claude4', 'claude5',
        '阿里', '腾讯', '字节', '百度', '华为', '小米', '比亚迪', '蔚来', '理想', '小鹏',
        '宇树', '智谱', '月之暗面', 'minimax', '商汤', '科大讯飞', '寒武纪',
        '苹果', '谷歌', '微软', '英伟达', '亚马逊', '特斯拉',
        '马斯克', '奥特曼', '黄仁勋', '库克', '皮查伊', '纳德拉', '扎克伯格', '梁文锋',
        '雷军', '何小鹏', '李斌', '李想', '王传福', '余承东', '李彦宏',
        '发改委', '商务部', '网信办', '工信部', 'fcc', 'sec', 'cfius',
        # 动作类（同义词组）
        '收购', '并购', '叫停', '禁止', '阻止', '撤销',
        '发布', '上线', '推出', '官宣', '开源', '正式发布',
        '融资', '估值', 'ipo', '上市', '股价',
        '裁员', '诉讼', '起诉', '签署', '合作', '投资', '入股',
        'mac', 'iphone', 'ipad', '芯片', '财报',
    ]
    
    found = set()
    for kw in KEY_ENTITIES:
        if kw in s:
            found.add(kw)
    
    return found


def _is_similar_title(title_a_keywords, title_b_keywords, threshold=0.6):
    """判断两个标题的关键词集合是否足够相似（同一事件）"""
    if not title_a_keywords or not title_b_keywords:
        return False
    intersection = title_a_keywords & title_b_keywords
    smaller = min(len(title_a_keywords), len(title_b_keywords))
    if smaller == 0:
        return False
    overlap_ratio = len(intersection) / smaller
    return overlap_ratio >= threshold and len(intersection) >= 2


def save_today_titles(today_titles):
    """把今天报道过的新闻标题追加到历史文件，并清理 7 天前的旧记录。"""
    try:
        today_str = datetime.now(BJT).strftime("%Y-%m-%d")
        # 读旧文件，按日期分组保留最近 7 天
        existing_lines = []
        try:
            with open(LAST_TITLES_FILE, "r", encoding="utf-8") as f:
                existing_lines = [l.rstrip() for l in f.readlines()]
        except FileNotFoundError:
            pass
        
        # 按日期块切分
        blocks = []  # 每个 block = (date_str, [titles])
        current_date = None
        current_titles = []
        for line in existing_lines:
            if line.startswith("=== ") and line.endswith(" ==="):
                if current_date:
                    blocks.append((current_date, current_titles))
                current_date = line[4:-4].strip()
                current_titles = []
            elif line.strip():
                current_titles.append(line.strip())
        if current_date:
            blocks.append((current_date, current_titles))
        
        # 仅保留最近 6 天的旧块（今天加上去就是 7 天）
        from datetime import datetime as _dt
        kept_blocks = []
        for date_str, titles in blocks:
            try:
                d = _dt.strptime(date_str, "%Y-%m-%d").date()
                today_d = _dt.strptime(today_str, "%Y-%m-%d").date()
                days_ago = (today_d - d).days
                if 0 <= days_ago <= 6 and date_str != today_str:
                    kept_blocks.append((date_str, titles))
            except Exception:
                continue
        
        # 写新文件
        out_lines = []
        for date_str, titles in kept_blocks:
            out_lines.append(f"=== {date_str} ===")
            out_lines.extend(titles)
            out_lines.append("")
        out_lines.append(f"=== {today_str} ===")
        out_lines.extend(today_titles)
        
        with open(LAST_TITLES_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(out_lines))
        
        subprocess.run(["git", "add", LAST_TITLES_FILE], check=False)
        subprocess.run(["git", "commit", "-m", f"auto: update last titles {today_str}"], check=False)
        subprocess.run(["git", "push"], check=False)
        print(f"  已保存今日 {len(today_titles)} 条标题到历史记录")
    except Exception as e:
        print(f"  保存今日标题失败: {e}")


def filter_by_recent_titles(articles, recent_titles_data):
    """过滤掉标题已经在最近 7 天报道过的文章（防止热点过期新闻反复出现）。
    
    args:
        articles: list of dict
        recent_titles_data: dict with 'normalized' (set of normalized titles) 
                           and 'keywords' (list of keyword sets)
    
    returns:
        filtered articles
    """
    if not recent_titles_data or (not recent_titles_data.get('normalized') and not recent_titles_data.get('keywords')):
        return articles
    
    normalized_set = recent_titles_data.get('normalized', set())
    keywords_list = recent_titles_data.get('keywords', [])
    
    kept = []
    skipped_count = 0
    skipped_samples = []
    for a in articles:
        title = a.get("title", "")
        norm = _normalize_title(title)
        kw_set = _extract_title_keywords(title)
        
        # 精确匹配
        if norm and norm in normalized_set:
            skipped_count += 1
            if len(skipped_samples) < 5:
                skipped_samples.append(f"{title[:40]} (精确)")
            continue
        
        # 关键词模糊匹配
        is_dup = False
        if kw_set:
            for old_kw in keywords_list:
                if _is_similar_title(kw_set, old_kw):
                    is_dup = True
                    break
        if is_dup:
            skipped_count += 1
            if len(skipped_samples) < 5:
                skipped_samples.append(f"{title[:40]} (模糊)")
            continue
        
        kept.append(a)
    
    if skipped_count > 0:
        print(f"  历史查重过滤掉 {skipped_count} 条已报道过的新闻")
        for s in skipped_samples:
            print(f"    - {s}")
    return kept


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
    try:
        from lunar_python import Solar
        s = Solar.fromYmd(dt.year, dt.month, dt.day)
        l = s.getLunar()
        return f"{l.getYearInGanZhi()}年 · {l.getYearShengXiao()}年 · 农历{l.getMonthInChinese()}月{l.getDayInChinese()}"
    except Exception as e:
        print(f"  农历计算失败（非致命）: {e}")
        return ""


def generate_calendar_card(quote_text="", quote_author=""):
    """v11 原有日历卡，保留不动。
    
    注意：日历卡顶部和底部红块写死了"鹏眼观天下"+"全球视野/科技洞察"。
    这是品牌物料，不需要因公众号改名而动——读者会通过封面图和推送标题感知品牌。
    如果你确定要改，搜 generate_calendar_card 找到模板替换即可。
    """
    now = datetime.now(BJT)
    year = now.strftime("%Y")
    month_cn_map = {1:"一月",2:"二月",3:"三月",4:"四月",5:"五月",6:"六月",
                    7:"七月",8:"八月",9:"九月",10:"十月",11:"十一月",12:"十二月"}
    month_cn = month_cn_map[now.month]
    month_en = now.strftime("%b") + "."
    day = now.strftime("%d").lstrip("0") or "0"
    weekday = WEEKDAY_CN[now.weekday()]
    lunar_text = _get_lunar_text(now)

    random.seed(now.strftime("%Y%m%d"))
    yi = random.choice(YI_OPTIONS)
    ji = random.choice(JI_OPTIONS)
    if not quote_text:
        quote_text = "预测未来的最好方式，就是去创造它。"
        quote_author = "艾伦·凯（计算机科学家）"

    RED_MAIN = "#c0392b"
    RED_BLOCK = "#a02820"
    PAPER = "#faf6ee"

    lunar_html = ""
    if lunar_text:
        lunar_html = f'<p style="text-align:center;font-size:10px;color:#3e3e3e;font-weight:500;letter-spacing:1px;margin:0 0 8px;">{lunar_text}</p>'

    return f"""
<section style="margin:32px auto 0;max-width:320px;">
<section style="background:{PAPER};padding:11px;box-sizing:border-box;box-shadow:0 2px 6px rgba(0,0,0,0.06),0 10px 30px rgba(0,0,0,0.1);">
<section style="background:{RED_MAIN};padding:2px;">
<section style="background:{PAPER};padding:6px;">
<section style="background:{RED_MAIN};padding:1px;">
<section style="background:{PAPER};">

<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{RED_BLOCK};border-collapse:collapse;"><tr><td height="26" width="25%" style="padding:0 0 0 18px;line-height:26px;vertical-align:middle;text-align:left;font-size:12px;color:#fff;font-weight:700;letter-spacing:1px;">{year}</td><td height="26" width="50%" style="line-height:26px;vertical-align:middle;text-align:center;font-size:13px;color:#fff;font-weight:700;letter-spacing:2px;">鹏眼观天下</td><td height="26" width="25%" style="padding:0 18px 0 0;line-height:26px;vertical-align:middle;text-align:right;font-size:12px;color:#fff;font-weight:700;letter-spacing:1px;">{month_cn}</td></tr></table>

<section style="padding:6px 22px 8px;">
<section style="display:flex;align-items:flex-start;gap:2px;">
<span style="font-family:Georgia,'Times New Roman',serif;font-size:21px;font-style:italic;color:{RED_MAIN};font-weight:400;margin-top:14px;line-height:1;">{month_en}</span>
<span style="font-family:Georgia,serif;font-size:21px;color:{RED_MAIN};font-weight:300;margin-top:14px;margin-left:2px;margin-right:5px;line-height:1;">/</span>
<span style="font-family:Georgia,'Times New Roman',serif;font-size:88px;font-weight:900;color:{RED_MAIN};line-height:0.92;letter-spacing:-3px;">{day}</span>
</section>
<p style="text-align:center;font-size:17px;font-weight:700;color:#2c2c2c;letter-spacing:6px;margin:6px 0 3px;">{weekday}</p>
{lunar_html}
</section>

<section style="height:1px;background:{RED_MAIN};margin:0 18px;"></section>

<section style="display:flex;justify-content:center;gap:20px;padding:10px 10px;">
<p style="display:flex;align-items:center;gap:6px;font-size:14px;color:#2c2c2c;font-weight:600;margin:0;white-space:nowrap;">
<span style="display:inline-flex;width:20px;height:20px;border-radius:50%;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:#fff;background:{RED_MAIN};flex-shrink:0;">宜</span>
{yi}
</p>
<p style="display:flex;align-items:center;gap:6px;font-size:14px;color:#2c2c2c;font-weight:600;margin:0;white-space:nowrap;">
<span style="display:inline-flex;width:20px;height:20px;border-radius:50%;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:#fff;background:#2c2c2c;flex-shrink:0;">忌</span>
{ji}
</p>
</section>

<section style="height:1px;background:{RED_MAIN};margin:0 18px;"></section>

<section style="padding:12px 24px 12px;">
<p style="font-size:14px;color:#2c2c2c;line-height:1.75;margin:0 0 9px;text-align:justify;">"{quote_text}"</p>
<p style="font-size:13px;color:#3e3e3e;font-weight:500;text-align:right;margin:0;">—— {quote_author}</p>
</section>

<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{RED_BLOCK};border-collapse:collapse;"><tr><td height="14" width="50%" style="padding:0 18px 0 18px;line-height:14px;vertical-align:middle;text-align:left;font-size:9px;color:#fff;font-weight:600;letter-spacing:1px;">全球视野</td><td height="14" width="50%" style="padding:0 18px 0 0;line-height:14px;vertical-align:middle;text-align:right;font-size:9px;color:#fff;font-weight:600;letter-spacing:1px;">科技洞察</td></tr></table>

</section>
</section>
</section>
</section>
</section>
"""


DISCLAIMER = """
<p style="font-size:12px;color:#9a9a9a;line-height:1.8;margin:32px 0 0;text-align:justify;">
素材来源于路透社、彭博社、TechCrunch、The Verge、Hacker News、CNBC、财联社、华尔街见闻、金十数据、IT之家、机器之心、36氪 等国内外主流科技媒体及网络公开报道，经 AI 辅助整理并由人工编辑审核。本文不代表任何立场，不构成任何投资建议。如有疏漏，欢迎留言指正。
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


# ============================================================
# v12.5 新增：last_titles.txt 持久化（防过期热点污染）
# 文件格式：每行 "YYYY-MM-DD\t标题"
# 保留最近 7 天的标题，防止已报道过的事件再次推送
# ============================================================

def read_last_titles(days=7):
    """读取最近 N 天报道过的标题列表
    
    返回：set（已报道过的标题字符串集合，全部去除前后空格）
    """
    today = datetime.now(BJT).date()
    cutoff = today - timedelta(days=days)
    titles = set()
    try:
        with open(LAST_TITLES_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or "\t" not in line:
                    continue
                date_str, title = line.split("\t", 1)
                try:
                    line_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                    if line_date >= cutoff:
                        titles.add(title.strip())
                except ValueError:
                    continue
        print(f"  读取到最近 {days} 天历史标题 {len(titles)} 条（过期热点防护）")
    except FileNotFoundError:
        print(f"  历史标题文件不存在，首次运行")
    except Exception as e:
        print(f"  读取历史标题失败: {e}")
    return titles


def save_today_titles(titles):
    """把今日报道过的标题追加到历史记录文件，并裁剪到 7 天
    
    titles: list[str] 今日实际推送的所有新闻标题
    """
    if not titles:
        return
    today = datetime.now(BJT).date()
    today_str = today.strftime("%Y-%m-%d")
    cutoff = today - timedelta(days=7)
    
    # 读出现有文件，过滤掉 7 天前的旧记录
    kept_lines = []
    try:
        with open(LAST_TITLES_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or "\t" not in line:
                    continue
                date_str, title = line.split("\t", 1)
                try:
                    line_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                    if line_date >= cutoff:
                        kept_lines.append(line)
                except ValueError:
                    continue
    except FileNotFoundError:
        pass
    
    # 追加今日标题
    for title in titles:
        title = title.strip()
        if title:
            kept_lines.append(f"{today_str}\t{title}")
    
    try:
        with open(LAST_TITLES_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(kept_lines) + "\n")
        subprocess.run(["git", "add", LAST_TITLES_FILE], check=False)
        subprocess.run(["git", "commit", "-m", "auto: update last titles"], check=False)
        subprocess.run(["git", "push"], check=False)
        print(f"  历史标题已更新，共保留 {len(kept_lines)} 条（7 天窗口）")
    except Exception as e:
        print(f"  保存历史标题失败: {e}")


# ============================================================
# v12.5 新增：双重查重函数（精确匹配 + 关键词集合模糊匹配）
# ============================================================

# 实体词词典：用于模糊匹配两个标题是否讲同一件事
# 命中相同的关键实体 ≥ 60% → 视作重复
KEYWORD_VOCAB = {
    # AI 公司
    "openai", "anthropic", "deepseek", "claude", "chatgpt", "gpt-4", "gpt-5", "gpt-5.5",
    "gemini", "llama", "qwen", "kimi", "doubao", "豆包", "通义", "文心", "混元",
    "manus", "moonshot", "智谱", "百川",
    # 模型版本号
    "v1", "v2", "v3", "v3.5", "v3.2", "v4", "v4.5", "v5", "v5.5",
    # 大公司
    "苹果", "apple", "谷歌", "google", "微软", "microsoft", "亚马逊", "amazon",
    "meta", "facebook", "特斯拉", "tesla", "英伟达", "nvidia", "amd", "intel",
    "字节", "腾讯", "阿里", "百度", "华为", "小米", "京东", "美团", "拼多多",
    "理想", "小鹏", "蔚来", "比亚迪", "宁德时代",
    # 关键动词
    "发布", "推出", "上线", "收购", "融资", "ipo", "上市", "财报", "辞职", "离职",
    "叫停", "禁止", "起诉", "和解", "宣布",
    # 其他
    "苹果", "openai", "manus", "agent", "robotaxi", "fsd",
}


def _extract_keywords(title):
    """从标题提取关键实体词（小写化，去标点）"""
    if not title:
        return set()
    s = title.lower()
    # 简单分词：把所有标点替换成空格，按空格切
    s = re.sub(r"[^\w\u4e00-\u9fff]+", " ", s)
    tokens = set(s.split())
    # 只保留在词典里的关键词
    return tokens & KEYWORD_VOCAB


def is_duplicate_with_history(title, history_titles, threshold=0.75):
    """判断 title 是否和历史标题重复
    
    1. 精确匹配（去空格后字符串完全相同）
    2. 关键词模糊匹配（实体词集合相似度 ≥ threshold）
    
    v13.0-day2.1: 阈值从 0.6 → 0.75
    原因:0.6 太严格,把"马斯克诉 OpenAI 案被驳回(昨日已报)"和
    "Sam Altman beat Elon Musk in court. Now ..."(今日新转折)误判成同一事件,
    导致新事件被过滤。提高到 0.75 后,只有"完全相同关键词集合"才会判重复。
    
    返回 (is_dup, matched_history_title or None)
    """
    if not title:
        return False, None
    title_clean = title.strip()
    
    # 精确匹配
    if title_clean in history_titles:
        return True, title_clean
    
    # 关键词模糊匹配
    title_kw = _extract_keywords(title_clean)
    if len(title_kw) < 2:  # 关键词太少不可信，跳过模糊匹配
        return False, None
    
    for hist_title in history_titles:
        hist_kw = _extract_keywords(hist_title)
        if len(hist_kw) < 2:
            continue
        common = title_kw & hist_kw
        # 相似度 = 公共关键词数 / 较小集合的大小
        smaller = min(len(title_kw), len(hist_kw))
        if smaller > 0 and len(common) / smaller >= threshold:
            return True, hist_title
    
    return False, None


def filter_articles_against_history(articles, history_titles):
    """过滤掉与历史标题重复的文章
    
    返回 (filtered_articles, removed_count, removed_examples)
    """
    if not history_titles:
        return articles, 0, []
    
    filtered = []
    removed_examples = []
    for art in articles:
        title = art.get("title", "")
        is_dup, matched = is_duplicate_with_history(title, history_titles)
        if is_dup:
            if len(removed_examples) < 5:
                removed_examples.append((title[:40], matched[:40]))
            continue
        filtered.append(art)
    
    removed = len(articles) - len(filtered)
    if removed > 0:
        print(f"  ⚠ 过滤掉 {removed} 条与最近 7 天报道重复的文章")
        for cur, hist in removed_examples:
            print(f"    × 当前: {cur}  ← 历史: {hist}")
    return filtered, removed, removed_examples


def get_time_range():
    now_bjt = datetime.now(BJT)
    end_time = now_bjt.replace(hour=6, minute=0, second=0, microsecond=0)
    if now_bjt.hour < 6:
        end_time -= timedelta(days=1)
    start_time = end_time - timedelta(hours=24)
    return start_time, end_time

# ============================================================
# v11 原有：英文源 4 个（保留不动）
# Google News + NewsAPI + Hacker News + TechCrunch
# ============================================================

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
                    "pub_time": a.get("publishedAt", ""),
                    "lang": "en",
                })
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
                url = item.get("url", "") or f"https://news.ycombinator.com/item?id={sid}"
                hn_time = item.get("time", 0)
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


# ============================================================
# v13.0 Day 2 新增：AI 公司官方源 3 个
# OpenAI / Google DeepMind 走标准 RSS
# Anthropic 无 RSS,需要解析 anthropic.com/news HTML 页面
# 所有三个源 lang="en",DeepSeek 按方案 A 中译处理
# ============================================================

def fetch_openai_blog():
    """OpenAI 官方博客 RSS(一手公告:模型发布、政策、研究、合作)"""
    print("抓取 OpenAI 官方博客 RSS...")
    try:
        resp = requests.get(
            "https://openai.com/news/rss.xml",
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        root = ElementTree.fromstring(resp.content)
        articles = []
        for item in root.findall(".//item")[:15]:
            title_el = item.find("title")
            pub_el = item.find("pubDate")
            link_el = item.find("link")
            desc_el = item.find("description")
            
            title = (title_el.text or "").strip() if title_el is not None else ""
            pub_date = (pub_el.text or "").strip() if pub_el is not None else ""
            link = (link_el.text or "").strip() if link_el is not None else ""
            desc = ""
            if desc_el is not None and desc_el.text:
                desc = re.sub(r'<[^>]+>', '', desc_el.text)[:400].strip()
            
            if not title:
                continue
            
            articles.append({
                "title": title,
                "url": link,
                "summary": desc,
                "source": "OpenAI 官方博客",
                "pub_time": pub_date,
                "lang": "en",
            })
        print(f"OpenAI 官方博客: {len(articles)} 条")
        return articles
    except Exception as e:
        print(f"OpenAI 官方博客失败: {type(e).__name__}: {e}")
        return []


def fetch_deepmind_blog():
    """Google DeepMind 官方博客 RSS(AI 研究进展、模型发布)"""
    print("抓取 Google DeepMind 官方博客 RSS...")
    try:
        resp = requests.get(
            "https://deepmind.google/blog/rss.xml",
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        root = ElementTree.fromstring(resp.content)
        articles = []
        for item in root.findall(".//item")[:15]:
            title_el = item.find("title")
            pub_el = item.find("pubDate")
            link_el = item.find("link")
            desc_el = item.find("description")
            
            title = (title_el.text or "").strip() if title_el is not None else ""
            pub_date = (pub_el.text or "").strip() if pub_el is not None else ""
            link = (link_el.text or "").strip() if link_el is not None else ""
            desc = ""
            if desc_el is not None and desc_el.text:
                desc = re.sub(r'<[^>]+>', '', desc_el.text)[:400].strip()
            
            if not title:
                continue
            
            articles.append({
                "title": title,
                "url": link,
                "summary": desc,
                "source": "Google DeepMind",
                "pub_time": pub_date,
                "lang": "en",
            })
        print(f"Google DeepMind: {len(articles)} 条")
        return articles
    except Exception as e:
        print(f"Google DeepMind 失败: {type(e).__name__}: {e}")
        return []


def fetch_anthropic_news():
    """Anthropic 官方公告(无 RSS,解析 anthropic.com/news HTML)
    
    设计原则:
    - 这是 Day 2 最有难度的源,失败概率最高
    - 抓不到时静默返回空列表,不影响其他源
    - HTML 结构变化时优雅退化
    """
    print("抓取 Anthropic 官方公告 HTML...")
    try:
        resp = requests.get(
            "https://www.anthropic.com/news",
            timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
            },
        )
        if resp.status_code != 200:
            print(f"Anthropic 公告页 HTTP {resp.status_code}")
            return []
        
        html = resp.text
        articles = []
        
        # 策略 1:寻找 /news/xxx 的链接(Anthropic 用 /news/ 作为新闻 URL 前缀)
        # 匹配 href="/news/xxx" 之后跟着的标题文本
        # 用宽松的正则,容忍 HTML 结构变化
        pattern = r'<a[^>]+href="(/news/[^"]+)"[^>]*>(.*?)</a>'
        matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
        
        seen_urls = set()
        for url_path, content_html in matches:
            # 去重(同一 URL 可能在页面多处出现)
            if url_path in seen_urls:
                continue
            
            # 提取纯文本标题(去 HTML 标签)
            title = re.sub(r'<[^>]+>', ' ', content_html)
            title = re.sub(r'\s+', ' ', title).strip()
            
            # 过滤太短或太长的(显然不是标题)
            if len(title) < 10 or len(title) > 200:
                continue
            
            # 过滤明显是导航/分类的(如"All news"、"Research"等)
            if title.lower() in ("all news", "research", "policy", "product", "company", "see all"):
                continue
            
            seen_urls.add(url_path)
            full_url = "https://www.anthropic.com" + url_path
            
            articles.append({
                "title": title,
                "url": full_url,
                "summary": "",  # HTML 抓取拿不到 summary,留空让 DeepSeek 根据 title 处理
                "source": "Anthropic 官方公告",
                "pub_time": "",  # HTML 抓取拿不到精确发布时间
                "lang": "en",
            })
            
            # 最多保留 10 条最新公告
            if len(articles) >= 10:
                break
        
        print(f"Anthropic 官方公告: {len(articles)} 条")
        return articles
    except Exception as e:
        print(f"Anthropic 官方公告失败: {type(e).__name__}: {e}")
        return []


# ============================================================
# v11 原有：国内 RSS 源 3 个（保留不动）
# IT之家 + 机器之心 + 36氪
# ============================================================

def fetch_ithome():
    """IT 之家 RSS(v13.0-day2.1 改用 ElementTree 标准 XML 解析,更鲁棒)"""
    print("抓取 IT之家 RSS...")
    try:
        resp = requests.get(
            "https://www.ithome.com/rss/",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=20,
        )
        resp.encoding = "utf-8"
        root = ElementTree.fromstring(resp.content)
        articles = []
        for item in root.findall(".//item")[:30]:
            title_el = item.find("title")
            link_el = item.find("link")
            desc_el = item.find("description")
            pub_el = item.find("pubDate")
            
            title = (title_el.text or "").strip() if title_el is not None else ""
            link = (link_el.text or "").strip() if link_el is not None else ""
            desc = ""
            if desc_el is not None and desc_el.text:
                # 去 HTML 标签和 CDATA 残留
                desc = re.sub(r"<[^>]+>", "", desc_el.text).strip()[:300]
            pub_date = (pub_el.text or "").strip() if pub_el is not None else ""
            
            if not title:
                continue
            
            articles.append({
                "title": title,
                "url": link,
                "summary": desc,
                "source": "IT之家",
                "pub_time": pub_date,
                "lang": "zh",
            })
        print(f"  IT之家 抓到 {len(articles)} 条")
        return articles
    except Exception as e:
        print(f"  IT之家 抓取失败: {type(e).__name__}: {e}")
        return []


def fetch_jiqizhixin():
    """机器之心 RSS(v13.0-day2.1 改用 ElementTree 标准 XML 解析,更鲁棒)"""
    print("抓取 机器之心 RSS...")
    try:
        resp = requests.get(
            "https://www.jiqizhixin.com/rss",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=20,
        )
        resp.encoding = "utf-8"
        root = ElementTree.fromstring(resp.content)
        articles = []
        for item in root.findall(".//item")[:30]:
            title_el = item.find("title")
            link_el = item.find("link")
            desc_el = item.find("description")
            pub_el = item.find("pubDate")
            
            title = (title_el.text or "").strip() if title_el is not None else ""
            link = (link_el.text or "").strip() if link_el is not None else ""
            desc = ""
            if desc_el is not None and desc_el.text:
                desc = re.sub(r"<[^>]+>", "", desc_el.text).strip()[:300]
            pub_date = (pub_el.text or "").strip() if pub_el is not None else ""
            
            if not title:
                continue
            
            articles.append({
                "title": title,
                "url": link,
                "summary": desc,
                "source": "机器之心",
                "pub_time": pub_date,
                "lang": "zh",
            })
        print(f"  机器之心 抓到 {len(articles)} 条")
        return articles
    except Exception as e:
        print(f"  机器之心 抓取失败: {type(e).__name__}: {e}")
        return []


def fetch_36kr():
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

# ============================================================
# v12 新增：NewsNow 中文一手快讯（5 个源）
# ============================================================
# 财联社+华尔街见闻+金十+IT之家热门+36氪快讯
# 与 v11 的 IT之家/36氪 RSS 互补：v11 抓发文 RSS，NewsNow 抓热门榜
# ============================================================

NEWSNOW_SOURCES = [
    # v13.0 Day 1 改动:踢掉热门榜,改用快讯流/最新流
    # 之前:cls-hot, wallstreetcn-quick, jin10, ithome, 36kr-quick
    # 现在:wallstreetcn-news + wallstreetcn-quick(双国际科技+财经快讯),保留 ithome/36kr-quick(国内科技快讯)
    # 踢掉的:cls-hot(A 股热门,过期严重) jin10(外汇宏观,跟科技无关)
    {"id": "wallstreetcn-news",  "name": "华尔街见闻",    "lang": "zh"},  # 实时一手财经科技流(已实测)
    {"id": "wallstreetcn-quick", "name": "华尔街见闻快讯", "lang": "zh"},  # 财经快讯(快、短)
    {"id": "ithome",             "name": "IT之家",        "lang": "zh"},  # 消费科技
    {"id": "36kr-quick",         "name": "36氪快讯",      "lang": "zh"},  # 创业/互联网
]


def fetch_newsnow_source(source_id, source_name, limit=30):
    """从 NewsNow API 抓取单个源
    
    返回标准 dict 列表（与 v11 其他 fetch_xxx 函数保持一致）
    """
    url = f"{NEWSNOW_BASE_URL}/api/s"
    try:
        resp = requests.get(
            url,
            params={"id": source_id},
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        resp.raise_for_status()
        payload = resp.json()
    except Exception as e:
        print(f"  [{source_name}] 抓取失败: {e}")
        return []
    
    items = payload.get("items") or payload.get("data") or []
    if not items:
        print(f"  [{source_name}] 返回空（可能反爬变化）")
        return []
    
    articles = []
    for raw in items[:limit]:
        title = (raw.get("title") or "").strip()
        if not title:
            continue
        
        # NewsNow 各源时间字段不一：pubDate/time/extra.date/created_at
        pub_time = (
            raw.get("pubDate") or
            raw.get("time") or
            (raw.get("extra") or {}).get("date") or
            raw.get("created_at") or
            ""
        )
        # NewsNow 经常返回 ISO 格式，转成 RFC 822 与其他源一致
        pub_time = _normalize_pub_time(pub_time)
        
        articles.append({
            "title": title,
            "url": raw.get("url") or raw.get("mobileUrl") or "",
            "summary": (raw.get("description") or raw.get("desc") or raw.get("content") or "").strip()[:400],
            "source": source_name,
            "pub_time": pub_time,
            "lang": "zh",
        })
    
    print(f"  [{source_name}] 抓到 {len(articles)} 条")
    return articles


def _normalize_pub_time(t):
    """把各种格式时间字符串统一成 RFC 822（与 v11 其他源一致）
    
    v12.5 修复：无法解析的 pub_time 必须返回空字符串，让时间过滤丢弃，
    避免把奇怪的字符串原样返回导致下游误判为"在 24h 内"。
    """
    if not t:
        return ""
    
    if isinstance(t, (int, float)):
        # 时间戳（毫秒或秒）
        if t > 1e12:
            t = t / 1000  # 毫秒转秒
        try:
            dt = datetime.fromtimestamp(t, tz=BJT)
            return dt.strftime("%a, %d %b %Y %H:%M:%S %z")
        except Exception:
            return ""
    
    s = str(t).strip()
    if not s:
        return ""
    
    # 尝试 1：ISO 8601 格式
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.strftime("%a, %d %b %Y %H:%M:%S %z")
    except Exception:
        pass
    
    # 尝试 2：RFC 822 格式（先解析能否成功）
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(s)
        if dt is not None:
            return s  # 已是合法 RFC 822
    except Exception:
        pass
    
    # 尝试 3：纯数字字符串当成时间戳
    try:
        ts = float(s)
        if ts > 1e12:
            ts = ts / 1000
        dt = datetime.fromtimestamp(ts, tz=BJT)
        return dt.strftime("%a, %d %b %Y %H:%M:%S %z")
    except Exception:
        pass
    
    # v12.5 关键修复：所有解析都失败时返回空字符串而非原值
    # 让 is_within_hours() 直接判定为不在窗口内，过滤掉
    return ""


def fetch_all_newsnow():
    """抓取所有 NewsNow 源"""
    print("抓取 NewsNow 中文一手快讯...")
    all_articles = []
    for src in NEWSNOW_SOURCES:
        articles = fetch_newsnow_source(src["id"], src["name"])
        all_articles.extend(articles)
    print(f"NewsNow 共 {len(all_articles)} 条")
    return all_articles


# ============================================================
# v12 新增：时间过滤（v11 已有，沿用并优化）
# ============================================================

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
            dt = datetime.fromisoformat(pubdate_str.replace("Z", "+00:00"))
            return dt.astimezone(BJT)
        except Exception:
            return None


def is_within_hours(pubdate_str, hours=24, now=None):
    now = now or datetime.now(BJT)
    pub = parse_pubdate_to_bjt(pubdate_str)
    if pub is None:
        return False
    delta = now - pub
    return timedelta(0) <= delta <= timedelta(hours=hours)


def relative_time(pubdate_str, now=None):
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
    now = datetime.now(BJT)
    filtered = [a for a in articles if is_within_hours(a.get("pub_time", ""), hours, now)]
    if len(filtered) < min_count and hours < fallback_hours:
        print(f"  24h 内仅 {len(filtered)} 条，放宽到 {fallback_hours}h...")
        filtered = [a for a in articles if is_within_hours(a.get("pub_time", ""), fallback_hours, now)]
    print(f"  时间过滤后剩 {len(filtered)} 条")
    return filtered


# ============================================================
# v12 新增：三元组预去重
# ============================================================
# 解决场景：财联社+IT之家热门+Google News 都报道同一事件（如阿里HappyHorse发布）
# 在送给 DeepSeek 整理前，先把同事件的多条合并成一组，让 DeepSeek 能看到完整上下文
# 这样 DeepSeek 能写出"据财联社、IT之家、TechCrunch多家媒体报道..."这种立体内容
# ============================================================

# 已知公司/产品名映射（用于实体识别）
KNOWN_ENTITIES = [
    "OpenAI", "Anthropic", "Claude", "ChatGPT", "Sora", "Gemini",
    "Google", "DeepMind", "Microsoft", "Apple", "苹果",
    "Meta", "Facebook", "Instagram", "WhatsApp",
    "Nvidia", "英伟达", "AMD", "Intel", "Qualcomm",
    "Tesla", "特斯拉", "Musk", "马斯克", "Altman", "奥特曼",
    "黄仁勋", "库克", "雷军", "余承东", "李彦宏", "张一鸣",
    "阿里", "Alibaba", "通义", "千问", "Qwen", "HappyHorse",
    "腾讯", "Tencent", "混元", "QClaw",
    "字节", "ByteDance", "豆包", "Doubao", "Seedance",
    "百度", "Baidu", "文心",
    "DeepSeek", "Kimi", "月之暗面", "智谱", "百川", "MiniMax", "阶跃星辰",
    "宇树", "Unitree", "小米", "理想", "蔚来", "比亚迪", "华为", "小鹏",
    "Manus", "Butterfly Effect",
    "国家发改委", "网信办", "工信部", "美国商务部",
]

# 已知动作映射（中英文同义合并）
ACTION_GROUPS = [
    {"收购", "并购", "acquire", "acquisition", "merger"},
    {"投资", "融资", "invest", "funding", "fundraise", "round"},
    {"发布", "推出", "上线", "launch", "release", "unveil", "announce"},
    {"叫停", "禁止", "封杀", "ban", "block", "halt", "prohibit"},
    {"终止", "解约", "退出", "terminate", "end", "exit"},
    {"合作", "结盟", "partner", "partnership", "collaborate"},
    {"起诉", "诉讼", "sue", "lawsuit", "litigation"},
    {"开源", "open source", "open-source"},
    {"裁员", "layoff", "lay off"},
    {"上市", "IPO"},
]


def _extract_entity(text):
    """从标题/摘要中找出最早出现的已知实体"""
    text_lower = text.lower()
    earliest = None
    earliest_pos = len(text)
    for entity in KNOWN_ENTITIES:
        pos = text_lower.find(entity.lower())
        if pos >= 0 and pos < earliest_pos:
            earliest_pos = pos
            earliest = entity
    return earliest


def _extract_action(text):
    """从标题/摘要中找出最早出现的已知动作"""
    text_lower = text.lower()
    earliest = None
    earliest_pos = len(text)
    for group in ACTION_GROUPS:
        for action in group:
            pos = text_lower.find(action.lower())
            if pos >= 0 and pos < earliest_pos:
                earliest_pos = pos
                # 用 group 的第一个作为规范化代表
                earliest = next(iter(sorted(group)))
                break
    return earliest


def _is_same_event(a, b, time_window_hours=24):
    """判断两条文章是否同一事件（实体+动作+时间窗）
    
    判断规则：
      1. 实体必须相同（核心）
      2. 时间在窗口内
      3. 动作匹配 → 同事件
      4. 动作不匹配但同实体 → 用标题关键名词重叠度判断
         （处理 Meta acquire Manus / Meta 叫停 Manus 这种同事件不同动作环节）
    """
    text_a = a["title"] + " " + a.get("summary", "")
    text_b = b["title"] + " " + b.get("summary", "")
    
    # 实体必须匹配
    e_a = _extract_entity(text_a)
    e_b = _extract_entity(text_b)
    if not e_a or not e_b:
        return False
    if e_a != e_b:
        return False
    
    # 时间窗内
    t_a = parse_pubdate_to_bjt(a.get("pub_time", ""))
    t_b = parse_pubdate_to_bjt(b.get("pub_time", ""))
    if t_a and t_b:
        if abs((t_a - t_b).total_seconds()) > time_window_hours * 3600:
            return False
    
    # 动作匹配 → 直接同事件
    act_a = _extract_action(text_a)
    act_b = _extract_action(text_b)
    if act_a and act_b and act_a == act_b:
        return True
    
    # 动作不匹配但同实体：检查是否有第二个共同实体
    # （如"Meta-Manus"两个实体都共享，说明是同事件链）
    e_a2 = _extract_entity(text_a.replace(e_a, "", 1))
    e_b2 = _extract_entity(text_b.replace(e_b, "", 1))
    if e_a2 and e_b2 and e_a2 == e_b2:
        return True
    
    # 默认：仅一个共同实体 + 动作不同 → 不算同事件
    return False


def cluster_articles(articles, time_window_hours=24):
    """三元组聚类：把同事件的文章合并到一个簇
    
    返回 list of dict：
      {
        "primary": 主文章（用于 DeepSeek 的核心材料）,
        "all": 该事件下的所有文章（含其他源）,
        "sources": 涉及的来源列表 ["财联社", "IT之家", "TechCrunch"]
      }
    """
    clusters = []
    for article in articles:
        matched = None
        for c in clusters:
            if _is_same_event(article, c["primary"], time_window_hours):
                matched = c
                break
        
        if matched:
            matched["all"].append(article)
            if article["source"] not in matched["sources"]:
                matched["sources"].append(article["source"])
        else:
            clusters.append({
                "primary": article,
                "all": [article],
                "sources": [article["source"]],
            })
    
    return clusters


def merge_clusters_to_articles(clusters):
    """把聚类后的事件簇展开为给 DeepSeek 用的材料列表
    
    每个簇取主文章，但额外附上"另据 X、Y 也报道"的多源标记
    """
    merged = []
    for c in clusters:
        primary = dict(c["primary"])  # 复制
        if len(c["all"]) > 1:
            # 多源命中：把其他源的摘要也合并进来作为补充材料
            other_summaries = []
            for other in c["all"][1:5]:  # 最多取 5 个源
                if other["source"] != primary["source"]:
                    s = (other.get("summary") or "")[:150]
                    if s:
                        other_summaries.append(f"【{other['source']}】{s}")
            if other_summaries:
                primary["summary"] = (primary.get("summary") or "") + "\n\n" + "\n".join(other_summaries)
            primary["multi_source_count"] = len(c["all"])
            primary["all_sources"] = c["sources"]
        merged.append(primary)
    return merged

# ============================================================
# v12 核心：DeepSeek 整理新闻（雷锋网风格深度编辑）
# ============================================================
# 相对 v11 的根本变化：
#   1. 角色从"新闻编辑（纯事实搬运）"升级为"科技日报深度编辑"
#   2. 允许 1-2 句轻微解读（这意味着.../背后的深层原因是...）
#   3. 摘要长度 80-150 字 → 头条 200-300 字 / 普通 120-180 字
#   4. 强制要求"客观事实对比"（如"史上第三大""超过 OpenAI 8800 亿估值"）
#   5. 强制要求"事件脉络"：TOP 新闻附 1-2 句时间线串联
#   6. 多源命中的事件作为重要性信号（不再要求写进摘要）
# ============================================================

DEEPSEEK_ORGANIZE_PROMPT = """你是一名经验丰富的科技新闻编辑，从事 7×24 时事整理工作。

## 你的任务

把下面 24 小时内抓取的科技新闻原始素材，整理成一份**事实准确、信息密度高、可信度强**的科技日报。

公众号定位：科技为主，参考雷峰早报的板块结构，但**严守事实，不补背景、不点评、不外推**。

## 输出 6 个板块（v12.5 新结构）

1. `headline`（总标题）：**3 个最重磅事件用「; 」分隔的并列长标题**，每个事件 8-15 字，必须包含具体动词或具体数字。**适度使用感叹号（每个事件最多 1 个）**，但禁止"炸裂、暴涨、突袭、紧急、震惊"等强情绪词。
   ✅ 示例：「OpenAI 自研手机敲定 2027 量产；iPhone Air 卖崩到 70 万台；谷歌市值反超苹果」
   ❌ 反例：「重磅！OpenAI 突袭硬件圈！iPhone Air 暴跌 90%！谷歌炸裂反杀苹果！」（过度情绪化）

2. `topics`（5 个话题标签）：每个 4-8 个汉字，概括当日 5 个最重要议题

3. `top_news_titles`（**v12.5 新增：要闻提示**）：**7-8 条短标题列表**，从今日全部素材里挑出最重要的 7-8 条，每条 15-30 字。这是"快读区"，让读者扫一眼就知道今天发生了什么。**不要写摘要，只要标题**。

4. `headline_event`（**v12.5 新增：今日头条**）：**1 条最重磅事件的深度展开**，200-400 字。从素材里选 1 个最重磅、最具象的事件，按"严守事实三铁律"展开。

5. `international`（国际要闻）：**5-6 条**，发生在中国大陆以外的事

6. `domestic`（国内动态）：**5-6 条**，中国大陆公司、政策、市场

7. `big_names`（大佬观点）：**2-3 条**，知名人物（黄仁勋、马斯克、奥特曼、库克、雷军、余承东、李彦宏等）的言论、表态、采访

**总条数目标：12-15 条事件**（去掉头条和要闻提示重叠）。素材足够时尽量满载。

## 严守事实三铁律（v12.5 核心原则，必须遵守）

### 铁律 1：不补背景

只用素材原文里的字面信息，**绝对禁止**基于训练数据补充常识、背景、解释、行业知识、历史事件。
- ❌ 错误："这是 Meta 史上第三大收购，仅次于 WhatsApp 和 Scale AI"（训练数据补的，素材里没有）
- ❌ 错误："Anthropic 二级市场估值已超越 OpenAI 的 8800 亿美元"（除非素材里明确写了"超越 OpenAI"）
- ✅ 正确：只写素材里给的数字、时间、人物、动作

### 铁律 2：引语原文照搬,且不允许截断(v12.5.1 强化)

人物原话、官方表态、数字、人名、机构名、产品名 必须从素材原文中**精准摘取**，不能改字、不能换词、不能润色。

**v12.5.1 关键强化:引语必须完整摘抄,即使长达 50 字也要全文,禁止截断**:
- ✅ 正确:素材原文是「Barry Diller 表示:'信任无关紧要,在 AGI 真正到来之前,我们需要的是护栏。'」→ 输出全文
- ❌ 错误:把上句缩写成「他表示:'信任无关紧要。'」← 截断了重要的下半句
- ❌ 错误:在引语中插入省略号代替原文 ← 不允许

**判断方法**:在引号「"」之内的原话,从开头第一个字到最后标点(句号/问号/感叹号),全部照搬,任何字都不能省。

- ✅ 正确：素材是"黄仁勋表示'AI 是新的工业革命'" → 输出"黄仁勋表示：'AI 是新的工业革命。'"
- ❌ 错误：把原话改写成"黄仁勋认为 AI 将引领新工业时代"

### 铁律 3：不点评、不外推

禁止使用"这意味着"、"分析人士认为"、"市场普遍预期"、"业内人士指出"、"值得关注"、"引发热议"、"无疑"等不在素材原文里的连接词。**只陈述事实，不下结论**。

- ❌ 错误："这意味着英伟达将巩固其 AI 芯片霸主地位"（外推）
- ❌ 错误："分析认为该收购将改变行业格局"（点评）
- ❌ 错误："值得关注的是..."（编辑感受词，无意义）
- ✅ 正确：只陈述"英伟达完成了某动作"，至于这意味着什么、读者自己判断

### 铁律 4：主谓关系必须与素材原文完全一致(v12.5.1 新增)

写每条新闻的第一句前,**必须先弄清:谁是主语,谁是宾语,动词是什么**。**严禁颠倒主谓关系**。

**典型错误案例(v12.5 实际推送中已出现)**:
- 素材原文:"SpaceX 与 Anthropic 达成协议,SpaceX 将使用 Anthropic 的 AI 服务"
- ❌ 错误输出:"Anthropic 宣布与 SpaceX 达成协议,将使用 SpaceX 的数据中心" ← **主谓完全颠倒**
- ✅ 正确输出:"SpaceX 与 Anthropic 达成协议,SpaceX 将使用 Anthropic 的 AI 服务"

**核查步骤**(每条新闻在输出前必须自检):
1. 谁主动发起这个动作? → 主语
2. 谁是这个动作的接受方? → 宾语
3. 动词是"使用"、"收购"、"投资"还是"出售"、"被收购"、"被投资"?
4. 数字归属:32 亿美元是谁出的钱?是收购金额还是投资金额?
5. 如果搞不清,**宁可不写这条新闻,也不要主谓颠倒**

**特别警惕的反向模式**:
- "A 与 B 达成 X 协议" — 先看清是 A→B 还是 B→A
- "A 将向 B 投资 X 美元" — 先看清是 A 给 B 钱,还是反过来
- "A 收购 B" — 谁吃了谁
- "A 拒绝 B 的提议" — 谁拒绝谁
- "A 起诉 B" — 谁告谁

### 关键句提取（允许的"整合"方式）

可以从素材原文里**摘抄 2-4 个关键句**，通过简单连接词（"然后"、"根据"、"数据显示"）拼成一段。摘抄时**不改字**，只调整顺序和加连接词。

- 关键句包括：具体数字、人物原话、官方表态、政策内容、产品参数

## 每条新闻的写作规范

### 1. 标题改写
- **中文新闻**：保留原标题（除非有"炸锅"、"血洗"等夸张词，要改成中性表达）
- **英文新闻**：翻译成"主体：核心动作"格式（如"黄仁勋：英伟达卖的是 token"）
- 标题不超过 30 字

### 2. 摘要长度与摘抄要求(v12.5.1 改为"摘抄项下限")

**核心原则:不强制字数,但必须达到摘抄项下限**。字数随素材丰富度自然展开,不允许为凑字数加废话。

- **`headline_event`(今日头条)**:必须包含 **5 个以上具体事实**(数字/时间/人名/产品名/动作)。字数自然到 200-400 字。
- **普通条目**:必须包含 **3 个以上具体事实**(数字/时间/人名/产品名/动作)。字数自然到 80-300 字。
- **`top_news_titles`(要闻提示)**:只用标题,不要摘要。

**"具体事实"的定义**(v12.5.1):
- 具体数字(金额、百分比、用户数、产能、估值、销量)
- 具体时间(YYYY 年 M 月 D 日,或"5 月 6 日")
- 具体人名/职位(CEO 张三、副总裁 John Doe)
- 具体产品名/版本号(GPT-5.2、iPhone Air、混元 Hy3)
- 具体动作(收购/发布/起诉/投资/裁员)
- 具体地点/机构(美国工厂、SEC、上海)

**素材太单薄时怎么办**:
- 如果素材原文里能摘抄的具体事实不足 3 个 → **允许摘要写得短**(50-80 字也可以)
- **绝对禁止**用以下方式凑字数:
  - 加"这意味着..."、"分析认为..."(违反铁律 3)
  - 加"该公司近年来在 AI 领域持续布局..."(违反铁律 1,补背景)
  - 把同一事实换三种说法重复
  - 加无意义的修饰词("这一重要消息"、"备受关注")

**字数自检流程**:
- 写完后数一下摘要里有几个具体事实
- 不足 3 个 → 看素材原文还能摘什么 → 还摘不到 → 那就保持短摘要
- 达到 3 个 → 即使只有 80 字也合格

### 3. 第一句必须包含
- 具体时间（YYYY 年 M 月 D 日 / 5 月 X 日 消息）
- 事件主语（谁）
- 核心动词（做了什么）
- 具体数字（如果素材里有）

### 4. 摘要写作风格
**纯事实陈述**：摘要必须直接以事实开头，**禁止**"据 X 报道"、"据 CNBC、Bloomberg 报道"、"根据多家媒体报道"等写法。

❌ 错误示范：
- "据 CNBC、Bloomberg 等多家媒体报道，Anthropic 正与投资者洽谈..."
- "据 TechCrunch 报道，软银集团正在组建一家机器人公司..."

✅ 正确示范：
- "Anthropic 正与投资者洽谈新一轮融资，估值在 8500 亿至 9000 亿美元之间..."
- "软银集团正在组建一家机器人公司，专门用于建设数据中心..."

**消息来源已在底部独立标注（"来源：CNBC"），开头不要再重复说谁报道的。直接进入事实。**

### 5. 数据准确性铁律
- **金额、估值、时间、百分比**必须与原文完全一致
- 不知道精确数字时不要瞎编（如"约"、"近"、"可能"是允许的）
- **绝对禁止**：自行计算或推断数字（如把 25 亿美元换算成"约 178 亿元人民币"——这是猜的）

### 6. 来源标注（v12.5 修正）
每条新闻必须保留 source 字段。**括号里写素材原文里实际出现的真实信源**，**禁止**写"雷峰网"、"36氪综合报道"等聚合器名称。

可用信源（按可信度排序）：
- 高可信：(新华社) (央视新闻) (人民日报) (澎湃新闻) (第一财经) (中证报)
- 中高：(财联社) (华尔街见闻) (金十数据) (IT之家) (机器之心) (钛媒体)
- 海外官方：(NVIDIA Newsroom) (Apple Newsroom) (Tesla IR) (OpenAI 官方博客) (Anthropic 公告)
- 海外媒体：(CNBC) (Bloomberg) (Reuters) (TechCrunch) (The Verge) (The Information)

**禁止使用以下聚合器/二手源(v12.5.1 扩充)**：
- 二手聚合器：(快科技)、(cnBeta)、(MSN)、(Yahoo News)、(Yahoo!)、(新浪科技)、(新浪财经)、(网易科技)、(搜狐科技)
- 社交平台：(微博)、(知乎)、(X)、(Twitter)
- 不明自媒体：(自媒体公众号)、(某科技博主)、(数码博主)
- 国外聚合器：(MSN News)、(Google News)、(Apple News)
**判断方法**：如果你"知道"这家媒体本身做的是新闻聚合(转载别家内容)而非原创报道，就不能写它，要追到它转载的真正原始信源。

### 6.1 多源拼接的来源标注(v12.5.1 新增)

如果一条新闻整合了 **2 个或以上素材**，**所有素材的真实信源都必须在括号里列出**，用顿号分隔:

✅ 正确示例：
- (CNBC、财联社) ← 国际公司发布 + A 股反应,两个不同源拼接
- (IT之家、机器之心) ← 中文科技媒体多源
- (Reuters、Bloomberg、华尔街见闻) ← 三源拼接

❌ 错误示例：
- 拼接了 CNBC + 财联社的内容,只标 (CNBC) ← 漏掉财联社,违规
- 拼接了 3 个源,只标 (综合报道) ← 不允许写"综合报道",必须列具体源

**判断方法**：如果摘要里出现"A 股xx股反应""中国市场反应""国内媒体跟进报道"等中文媒体专属内容，那它必然不是 CNBC/Bloomberg 等英文媒体的原文，必有第二个中文信源，必须列出。

## 选题导向规则（保留 v12.4 规则）

### 1. 国内车企（理想/蔚来/小鹏/比亚迪/小米/华为/极氪/AITO/方程豹/MG等）：禁止报道单纯销量数据
- ❌ 错误选题："理想 4 月交付 X 万辆"、"比亚迪 4 月销量出炉"、"小米 SU7 月销 X 万"
- ❌ 错误选题：销量榜排名、交付增长率、市占率纯数据
- ✅ 优先选题：智能驾驶（FSD/NOA/城市领航/L3 落地）、自研芯片、AI 大模型上车、座舱系统、整车 OS、电池技术（800V/全固态）、自研激光雷达、人形机器人布局
- ✅ 大佬发言：何小鹏/雷军/李想/王传福对智驾/AI/芯片的观点（不是销量话术）
- 简单说：**只关注汽车的"科技含量"，不关注它的"商业表现"**

### 2. 美股科技巨头（苹果/微软/谷歌/Meta/亚马逊/英伟达/特斯拉/博通/英特尔/AMD等）：必须包含 AI 维度信息
报道这些公司的财报/业绩/股价时，**必须挖掘出 AI 维度**：
- AI 资本开支具体数字（如"谷歌 AI 资本开支 2000 亿美元"）
- AI 业务收入贡献（如"AI 推动云业务季度营收首次突破 200 亿美元"）
- AI 战略表态（如"皮查伊：算力瓶颈仍限制公司增长"）
- AI 产品进展（GPT/Gemini/Claude/Copilot 用户数、企业渗透）

**股价影响要客观评价**：
- ✅ 允许的客观陈述："消息公布后 X 公司股价盘后下跌 3%"、"超出市场预期 2 个百分点，引发盘前上涨"
- ✅ 允许的客观对比："该估值已超过 OpenAI 当前 8800 亿美元"、"创该公司近一年最大单日涨幅"
- ❌ 禁止主观预测："股价将持续上涨"、"长期看好"、"值得布局"
- ❌ 禁止情绪化词汇："血洗"、"翻车"、"炸锅"、"暴涨"——改为中性的"下跌"、"下挫"、"走高"、"上涨"
- ❌ 禁止投资建议：任何形式的"建议买入/卖出/持有"

## 严格要求

- **不写社论**：不要"未来可期"、"值得期待"、"影响深远"这种空话
- **保持时态**：原文"将"就不能写成"已经"
- **保持中性**：不站队，不评价
- **去重**：两条新闻讲同一件事的合并成一条
- **数量与质量并重**：12-15 条，国内板块 5-6 条
- **大佬观点板块特殊要求**：原文必须**确实是 X 说的话**，不能把媒体解读当成大佬本人观点

## ⚠️ 新闻新鲜度铁律（v12.5 强化）

### 1. 只能用我提供的素材，绝对禁止使用你的训练知识自行补充事件
- 如果素材里没有某条新闻，**绝对不要凭训练记忆把它写出来**
- 即使你"知道"某个大事件（如某模型发布、某收购被叫停等），如果素材里没有，就**不要写**
- 每条新闻都必须能在素材里找到对应的 [编号] 来源，否则禁止生成

### 2. 警惕过期热点新闻渗透
今天是 {TODAY}（北京时间）。请重点警惕这类陷阱：
- 素材标题里出现"DeepSeek V4 发布"、"V4 上线"、"V4 预览"等：**这是 4 月 24 日的旧闻，必须排除**
- 素材标题里出现"Meta 收购 Manus 被叫停"、"发改委叫停 Meta"、"Manus 项目禁止"等：**这是 4 月 27 日的旧闻，必须排除**
- 素材标题里出现"V3 发布"、"V3.2"等更早的版本号事件：必须排除
- **判断方法**：如果某条新闻的核心事件你"觉得已经听过好几天了"，它就是过期热点，请排除
- **保留原则**：宁可数量不足 12 条，也不要为了凑数而选过期新闻

### 3. 选题优先级
- ✅ 优先：今天/昨天发生的具体事件（财报发布、新品上线、签约公告、官方表态）
- ✅ 优先：素材中明确写了"今日"、"刚刚"、"4月30日"、"5月1日"等近期时间词的
- ⚠️ 谨慎：素材中没有具体日期、只有"近期"、"日前"的——可能是过期热点
- ❌ 排除：素材中明显是 4 天前以上的事件（无论它在素材中如何被频繁提及）

## 英文素材处理（方案 A：中译，但仅人物原话保英文）

处理英文素材（OpenAI 博客 / Anthropic 公告 / Google DeepMind / NVIDIA / Apple / Tesla / TechCrunch / Reuters / CNBC / The New York Times / Bloomberg / PBS / The Information 等）时：

### 必须中译的内容（v13.0 Day 2 严格化）

1. **媒体名前置叙述**：所有"据X报道"、"X称"等媒体描述必须全部中译，**禁止照搬英文报道句**
   - ❌ 错误：`The New York Times 称 "Before Mass Layoffs, Meta Reassigns 7,000 Workers to Focus on A.I."`
   - ❌ 错误：`PBS 报道称 "Pope Leo XIV to launch his first encylical..."`
   - ✅ 正确：直接陈述事实，不带"据 X 报道称"，媒体名只放文末括号里
   - ✅ 正确：`Meta 在裁员前已将 7000 名员工重新分配到 AI 相关岗位。(CNBC、The New York Times、Business Insider)`

2. **新闻标题原文**：媒体的英文新闻标题禁止照搬，必须翻译
3. **媒体报道描述**：媒体对事件的叙述句必须翻译，不能保留英文原文
4. **公司公告原文**：公司公告的英文原文必须翻译

### 唯一保留英文原文的情况：人物原话

**只有这一种情况**：素材中某位**具体人物**（CEO/创始人/官员/分析师等）有**直接说的话**，并且原文用了引号包裹，才用「中文翻译。原文：'English Quote'」格式。

✅ 正确示例 1（人物引语）：
- 英文素材："NVIDIA CEO Jensen Huang said 'AI is the new industrial revolution.'"
- 输出：英伟达（NVIDIA）CEO 黄仁勋（Jensen Huang）表示："AI 是新的工业革命。原文：'AI is the new industrial revolution.'"

✅ 正确示例 2（人物引语）：
- 英文素材："Altman said 'I have no plans to take the company public.'"
- 输出：Altman 表示："我没有让公司上市的计划。原文：'I have no plans to take the company public.'"

❌ 错误示例 1（不是人物引语，是媒体标题）：
- 英文素材：TechCrunch 标题 "Elon Musk's claim that he was mistreated failed"
- 错误输出：`TechCrunch 报道称 "Elon Musk's claim that he was mistreated failed"` ← 媒体标题不该照搬
- 正确输出：加州陪审团一致裁定马斯克的诉讼失败。(TechCrunch)

❌ 错误示例 2（不是人物引语，是媒体描述）：
- 英文素材：The Information 写道 "Microsoft has earned over $30 billion from OpenAI's technology"
- 错误输出：`The Information 称 "Microsoft has earned over $30 billion from OpenAI's technology"` ← 媒体描述不该照搬
- 正确输出：微软已从 OpenAI 的技术中创造了超过 300 亿美元的收入。(The Information)

### 其他规则

5. **数字保留原值**（美元/百万/吉瓦等单位也保留）
6. **人名/产品名/机构名**首次提及时给「中文译名（English Name）」格式
7. **括号 source 字段**：仍然必须列出真实信源，多源用顿号分隔

### 自检流程

写完每条英文来源的新闻后，自检：
- 摘要里有没有出现英文句子（除了"原文：'...'"格式）？
- 如果有，看看是不是人物原话？
- 不是 → 必须翻译成中文
- 是 → 保留，并用「中文翻译。原文：'English'」格式

## 输出格式（严格 JSON）

```json
{
  "headline": "事件1; 事件2; 事件3 (3 个事件用分号空格分隔)",
  "topics": ["标签1", "标签2", "标签3", "标签4", "标签5"],
  "top_news_titles": [
    "要闻短标题 1（15-30 字）",
    "要闻短标题 2",
    "...",
    "要闻短标题 7-8"
  ],
  "headline_event": {
    "title": "今日头条标题（30 字内）",
    "summary": "200-400 字深度展开，从素材摘抄 2-3 个关键事实拼接，严守事实三铁律",
    "source": "真实信源（如 IT之家 / 澎湃 / NVIDIA Newsroom）",
    "url": "https://...",
    "pub_time": "原 pubDate 字符串"
  },
  "international": [
    {
      "title": "改写后的标题",
      "summary": "150-300 字摘要",
      "source": "真实信源",
      "url": "https://...",
      "pub_time": "原 pubDate 字符串"
    }
  ],
  "domestic": [...],
  "big_names": [...]
}
```

## 原始素材（共 {ARTICLE_COUNT} 条）

> 注：素材中带 ⚡多源命中 标记的条目说明该事件被多家媒体报道，**这是该事件重要性的信号**（重要性高、可信度高，应优先选入），但**不要把"⚡多源命中"或媒体列表写进最终摘要**。摘要直接陈述事实，媒体名只放在 source 字段（HTML 底部会显示"来源：xxx"）。

{ARTICLES_TEXT}
"""


def deepseek_organize_news(articles):
    """v12 升级版：用雷锋网风格深度编辑模式整理新闻
    
    输入：聚类合并后的文章列表（每个已附多源补充材料）
    输出：dict，含 4 个板块
    """
    # 拼接素材
    news_blocks = []
    for i, a in enumerate(articles, 1):
        multi_src = ""
        if a.get("multi_source_count", 1) > 1:
            multi_src = f"⚡多源命中：{', '.join(a.get('all_sources', [])[:5])}\n"
        news_blocks.append(
            f"[{i}] 【{a['source']}】({a.get('lang','zh')}) {a.get('pub_time','')}\n"
            f"{multi_src}"
            f"标题：{a['title']}\n"
            f"链接：{a['url']}\n"
            f"摘要：{a.get('summary','')}"
        )
    news_text = "\n\n".join(news_blocks)

    today_str = datetime.now(BJT).strftime("%Y年%m月%d日")
    prompt = DEEPSEEK_ORGANIZE_PROMPT.replace(
        "{ARTICLE_COUNT}", str(len(articles))
    ).replace(
        "{ARTICLES_TEXT}", news_text
    ).replace(
        "{TODAY}", today_str
    )

    print(f"DeepSeek 整理新闻中（输入 {len(articles)} 条事件簇）...")
    try:
        resp = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"},
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 32000,  # v12.5 提升：22000 → 32000，应对头条+要闻提示+正文扩容
                "response_format": {"type": "json_object"},
                "temperature": 0.3,   # 略带创意但仍以事实为主
            },
            timeout=240,  # v12 延长：深度生成需要更多时间
        )
        data = resp.json()
        if "choices" not in data:
            print(f"DeepSeek 错误: {data}")
            return None
        content = data["choices"][0]["message"]["content"]
        content = re.sub(r"^```json\s*|\s*```$", "", content.strip())
        result = json.loads(content)
        
        # 打印 token 使用情况
        usage = data.get("usage", {})
        prompt_tok = usage.get("prompt_tokens", 0)
        completion_tok = usage.get("completion_tokens", 0)
        print(f"  整理完成：国际 {len(result.get('international', []))} / "
              f"国内 {len(result.get('domestic', []))} / "
              f"大佬 {len(result.get('big_names', []))}")
        print(f"  Token 使用：输入 {prompt_tok} + 输出 {completion_tok} = {prompt_tok + completion_tok}")
        return result
    except Exception as e:
        print(f"DeepSeek 整理失败: {e}")
        return None


# ============================================================
# v12 新增：跨源事实交叉验证
# ============================================================
# 对 TOP 3 重要事件做多源对比，发现冲突时给 ⚠ 标记
# 仅对"多源命中"的事件验证，单源新闻没法验证
# 成本控制：每天最多 3 次，单次约 1500-2500 token
# ============================================================

CROSS_VALIDATE_PROMPT = """你是科技新闻事实核查员。下面是同一事件在多个媒体的原始报道。

任务：核查各源描述是否一致，特别注意：
- 关键数字（金额、估值、规模、百分比、时间）
- 主体（谁做了什么）
- 措辞强度（"终止"vs"重新谈判" 这类差异很重要）

只输出 JSON：
```json
{
  "is_consistent": true/false,
  "key_facts": {
    "主体": "...",
    "动作": "...",
    "金额或估值": "...如有",
    "时间": "...如有",
    "其他关键数字": "..."
  },
  "discrepancies": ["源A说X，源B说Y这种差异"],
  "potential_issues": ["如'数字偏大需进一步核对'、'措辞过强'"],
  "confidence": 0.0-1.0,
  "recommended_phrasing": "建议的中文准确表述（30-60字）"
}
```

事件素材：
{MATERIALS}
"""


def cross_validate_event(cluster, max_sources=4):
    """对一个事件簇做跨源验证"""
    if len(cluster["all"]) < 2:
        return {"status": "single_source", "skipped": True}
    
    materials = []
    for i, a in enumerate(cluster["all"][:max_sources], 1):
        materials.append(
            f"【源{i}：{a['source']}】\n"
            f"标题：{a['title']}\n"
            f"摘要：{(a.get('summary') or '')[:300]}"
        )
    
    prompt = CROSS_VALIDATE_PROMPT.replace("{MATERIALS}", "\n\n".join(materials))
    
    try:
        resp = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"},
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 800,
                "response_format": {"type": "json_object"},
                "temperature": 0.0,
            },
            timeout=60,
        )
        data = resp.json()
        if "choices" not in data:
            return {"status": "validation_error", "error": str(data)}
        
        content = data["choices"][0]["message"]["content"]
        content = re.sub(r"^```json\s*|\s*```$", "", content.strip())
        result = json.loads(content)
        
        usage = data.get("usage", {})
        print(f"    验证 token: {usage.get('total_tokens', 0)}")
        
        # 标准化返回
        is_consistent = result.get("is_consistent", True)
        issues = result.get("potential_issues", [])
        discrepancies = result.get("discrepancies", [])
        
        if not is_consistent or discrepancies or issues:
            status = "conflict"
        else:
            status = "verified"
        
        return {
            "status": status,
            "confidence": result.get("confidence", 0.7),
            "key_facts": result.get("key_facts", {}),
            "discrepancies": discrepancies,
            "potential_issues": issues,
            "recommended_phrasing": result.get("recommended_phrasing", ""),
        }
    
    except Exception as e:
        print(f"    验证失败: {e}")
        return {"status": "validation_error", "error": str(e)}


def validate_top_clusters(clusters, max_validations=3):
    """对前 N 个多源命中的事件簇做验证
    
    优先级：多源命中数高 > 一手中文源 > 其他
    """
    # 排序：先按多源命中数，再按是否含华尔街见闻/IT之家这种一手源（v13.0 调整）
    PRIORITY_SOURCES = {"华尔街见闻", "华尔街见闻快讯", "IT之家", "36氪快讯", "36kr"}
    
    def priority(c):
        score = len(c["all"])
        if any(s in PRIORITY_SOURCES for s in c["sources"]):
            score += 5
        return score
    
    sorted_clusters = sorted(
        [c for c in clusters if len(c["all"]) >= 2],  # 仅多源命中
        key=priority,
        reverse=True
    )
    
    validations = {}
    for c in sorted_clusters[:max_validations]:
        title_key = c["primary"]["title"][:40]
        print(f"  验证：{title_key}")
        result = cross_validate_event(c)
        validations[title_key] = result
        if result.get("status") == "conflict":
            print(f"    ⚠ 发现冲突: {'; '.join(result.get('potential_issues', []))[:120]}")
        elif result.get("status") == "verified":
            print(f"    ✓ 各源一致")
    
    return validations

# ============================================================
# v12 升级：HTML 渲染（保留 v11 雷锋网风格 + 验证警告徽章）
# ============================================================

def _enrich_with_validation(html_summary, validations, item_title):
    """如果该新闻有验证警告，给摘要尾部加一个 ⚠ 提示"""
    # 模糊匹配标题
    for key, v in validations.items():
        # 标题前 15 字相同就算匹配
        if v.get("status") == "conflict" and (item_title[:15] in key or key[:15] in item_title):
            issues = v.get("potential_issues", [])
            if issues:
                warning = f'<p style="font-size:12px;color:#bf8f00;background:#fff8e6;padding:6px 10px;margin:4px 0 0;border-left:3px solid #bf8f00;border-radius:0 4px 4px 0;">⚠ 多源核查提示：{"; ".join(issues[:2])[:80]}</p>'
                return html_summary + warning
    return html_summary


def render_news_item(item, now=None, validations=None):
    """渲染单条新闻为 HTML（含小标题、摘要、文末括号来源、验证徽章）"""
    now = now or datetime.now(BJT)
    title = item.get("title", "").strip()
    summary = item.get("summary", "").strip()
    source = item.get("source", "")
    is_headline = item.get("is_headline", False)
    
    # 头条样式略加强
    border_width = "5px" if is_headline else "4px"
    title_size = "18px" if is_headline else "17px"
    summary_size = "16px" if is_headline else "15px"
    
    # v12.4 改动：来源用括号附在摘要末尾，不再独立成行
    if source:
        # 摘要末尾去掉句号，加上空格 + 灰色括号来源
        summary_clean = summary.rstrip("。.").rstrip()
        summary_with_source = f'{summary_clean}。<span style="color:#9a9a9a;font-size:13px;">（{source}）</span>'
    else:
        summary_with_source = summary
    
    # 验证警告（如有）
    summary_html = f'<p style="font-size:{summary_size};color:#3e3e3e;line-height:1.85;margin:0 0 8px;text-align:justify;">{summary_with_source}</p>'
    if validations:
        summary_html = _enrich_with_validation(summary_html, validations, title)

    return f"""
<section style="margin:0 0 26px;">
<p style="font-size:{title_size};font-weight:700;color:#222;line-height:1.45;margin:0 0 10px;border-left:{border_width} solid #c0392b;padding-left:12px;">{title}</p>
{summary_html}
</section>
"""


def render_section_header(label_zh, label_en):
    return f"""
<section style="margin:36px 0 22px;text-align:center;">
<p style="display:inline-block;font-size:18px;font-weight:700;color:#222;letter-spacing:1px;margin:0;padding:0 16px;background:#fff;position:relative;">
{label_zh}
<span style="display:block;font-size:11px;color:#c0392b;letter-spacing:3px;margin-top:4px;">{label_en}</span>
</p>
<div style="border-top:2px solid #c0392b;margin-top:-32px;height:0;position:relative;z-index:-1;"></div>
</section>
"""


def render_remind_block(items, top_news_titles=None):
    """要闻提示：v12.5 优先用 DeepSeek 输出的 top_news_titles 字段
    
    top_news_titles: list[str] - DeepSeek 提供的精选短标题列表
    items: list[dict] - 完整新闻列表,作为降级使用(无 top_news_titles 时)
    """
    # v12.5 优先：DeepSeek 提供的精选要闻
    if top_news_titles and isinstance(top_news_titles, list):
        title_list = [t.strip() for t in top_news_titles if isinstance(t, str) and t.strip()][:8]
    elif items:
        # 降级：从所有新闻里取前 8 条标题
        title_list = [item.get("title", "").strip() for item in items[:8] if item.get("title")]
    else:
        return ""
    
    if not title_list:
        return ""
    
    list_html = "".join(
        f'<p style="font-size:14px;color:#3e3e3e;line-height:1.9;margin:0 0 6px;padding-left:24px;text-indent:-24px;">{i+1}. {t}</p>'
        for i, t in enumerate(title_list)
    )
    return f"""
<section style="margin:24px 0 32px;padding:18px 16px;background:#faf6ee;border-left:4px solid #c0392b;">
<p style="font-size:16px;font-weight:700;color:#c0392b;letter-spacing:2px;margin:0 0 12px;">要闻提示 · NEWS REMIND</p>
{list_html}
</section>
"""


def render_headline_event(headline_event, now=None, validations=None):
    """v12.5 新增：今日头条板块 - 1 条最重磅事件深度展开"""
    if not headline_event or not isinstance(headline_event, dict):
        return ""
    title = headline_event.get("title", "").strip()
    summary = headline_event.get("summary", "").strip()
    source = headline_event.get("source", "").strip()
    if not title or not summary:
        return ""
    
    source_html = f'<span style="display:inline-block;font-size:12px;color:#888;margin-top:8px;">来源：{source}</span>' if source else ""
    
    return f"""
<section style="margin:32px 0;padding:24px 18px;background:linear-gradient(180deg,#fff8f3 0%,#fdf2e9 100%);border:2px solid #c0392b;border-radius:8px;">
<p style="font-size:13px;font-weight:700;color:#c0392b;letter-spacing:3px;margin:0 0 14px;">🔥 今日头条 · TODAY'S HEADLINE</p>
<p style="font-size:19px;font-weight:800;color:#1a1a1a;line-height:1.45;margin:0 0 12px;">{title}</p>
<p style="font-size:15px;color:#2c2c2c;line-height:1.85;margin:0;text-align:justify;">{summary}</p>
{source_html}
</section>
"""


def build_news_html(organized, now=None, validations=None):
    """v12 升级版：把整理好的结构化数据 → 完整公众号 HTML
    
    新增：传入 validations 字典后，对应新闻会附带"多源核查提示"徽章
    v12.5：新增 today's headline 板块 + DeepSeek 提供的精选要闻
    """
    now = now or datetime.now(BJT)
    headline = organized.get("headline", "今日科技要闻")

    intl = organized.get("international", [])
    dom = organized.get("domestic", [])
    big = organized.get("big_names", [])
    
    # v12.5 新增字段
    headline_event = organized.get("headline_event")
    top_news_titles = organized.get("top_news_titles")

    weekday_cn = WEEKDAY_CN[now.weekday()]
    date_str = now.strftime("%Y年%m月%d日") + f" · {weekday_cn}"

    parts = [
        f'<p style="font-size:21px;font-weight:800;color:#1a1a1a;line-height:1.4;margin:0 0 6px;">{headline}</p>',
        f'<p style="font-size:13px;color:#9a9a9a;margin:0 0 4px;letter-spacing:1px;">{date_str}</p>',
    ]

    # v12.5 板块顺序：要闻提示 → 今日头条 → 国际/国内/大佬
    all_items = intl + dom + big
    parts.append(render_remind_block(all_items, top_news_titles=top_news_titles))
    
    # v12.5 新增：今日头条板块
    if headline_event:
        parts.append(render_headline_event(headline_event, now, validations))

    if intl:
        parts.append(render_section_header("国际要闻", "BREAKING NEWS"))
        for item in intl:
            parts.append(render_news_item(item, now, validations))

    if dom:
        parts.append(render_section_header("国内动态", "DOMESTIC NEWS"))
        for item in dom:
            parts.append(render_news_item(item, now, validations))

    if big:
        parts.append(render_section_header("大佬观点", "BIG NAMES"))
        for item in big:
            parts.append(render_news_item(item, now, validations))

    return "\n".join(parts)


def extract_titles_from_organized(organized):
    """从整理后的数据提取主副标题（用于豆包封面图 prompt）"""
    headline = organized.get("headline", "今日科技圈")
    for sep in ["，", "：", " - ", "——"]:
        if sep in headline:
            parts = headline.split(sep, 1)
            return parts[0].strip(), parts[1].strip()
    if len(headline) > 12:
        mid = len(headline) // 2
        return headline[:mid], headline[mid:]
    return headline, "过去24小时科技要闻"


# ============================================================
# v11 原有：豆包 Seedream 4.5 主题图（保留不动）
# ============================================================
CINEMATIC_BASE = (
    "【风格】真实摄影作品，类似国际通讯社（路透/彭博）发布的新闻配图，"
    "或科技纪录片定格画面（如 Apple TV+ 纪录片、National Geographic 科技专题），"
    "DSLR 单反拍摄质感，35mm 胶片颗粒感，专业级商业摄影。"
    "【色调】偏写实自然光，主色为深蓝/灰黑/不锈钢冷色调，"
    "局部琥珀色/暖橙色灯光（屏幕反光、机房 LED、信号灯）作为锚点。"
    "【景深】光圈 f/2.8 大景深，前景主体锐利对焦，中景元素清晰，远景柔和虚化（bokeh）。"
    "【主体】真实物理存在的场景：服务器机架、芯片晶圆、办公楼夜景、数据中心走廊、"
    "实验室仪器、新闻发布会现场、CEO 财报演讲台、股票交易屏幕等具体可触的实体。"
    "【打光】环境光+反射光，体积光线穿透，类似电影摄影师 Roger Deakins 的处理手法，"
    "强调材质质感（金属反光、玻璃透光、电路细节）。"
    "【画幅】2.35:1 超宽幅电影构图（横版宽屏 1920×817），"
    "主体居中或遵循三分构图，左右留延伸空间（远处建筑/城市天际线/横向延展的光线）。"
    "【画质】8K 超高清，专业摄影后期调色。"
)

NEGATIVE_STYLE = (
    "❌ 严格禁止：卡通风格、Q版、矢量插画（vector illustration）、扁平设计（flat design）、"
    "可爱、幼稚、糖果色（粉色/紫色/亮蓝糖果调）、3D 渲染玩偶感、Pixar 风格、"
    "图标式构图（小图标拼贴）、信息图表（infographic）、2D 数字插画、"
    "多个小机器人、聊天气泡、emoji、漫画、简笔画、PPT 配图风、"
    "网页设计师作品集风格、Behance/Dribbble 风格、"
    "画面中出现任何文字/字母/中文/英文/数字/logo/品牌标识/UI 界面元素、"
    "夸张比例、超现实变形、艺术抽象画。"
    "❌ 禁止生成：动画化的小人、卡通设备图标、彩色块拼贴、装饰性插图。"
)


def generate_image_prompt(news_digest_text):
    if not news_digest_text or not isinstance(news_digest_text, str):
        print("  图片 prompt 生成跳过：输入为空")
        return None

    meta_prompt = f"""你是一位**新闻摄影记者+商业摄影总监**。下面是今天的科技新闻简报。

请从简报里**提取 1-2 个最有标志性的真实物理场景**，然后写一条中文 prompt，用于生成今日文章的**真实感摄影封面**（不是插画，是摄影作品）。

## 核心原则：**真实感优先，禁止幻想**

我们要的是**新闻摄影作品**或**纪录片定格画面**——读者第一眼应该觉得"这是真实拍摄的"，而不是"这是 AI 画的插图"。

## 元素提取规则

1. **必须选真实存在的物理场景或物件**，例如：
   - **基础设施**：服务器机架（深夜机房、蓝绿色 LED 指示灯）、数据中心走廊、半导体晶圆、芯片封装、数据中心冷却管
   - **产品本体**：真实的 iPhone/Mac/Vision Pro 实物、汽车智驾屏幕、机器人手臂、AR 眼镜
   - **场景**：财报电话会议室、CEO 演讲台、华尔街交易屏幕、纳斯达克大屏、纽交所开盘钟、办公楼夜景、实验室场景
   - **细节**：芯片晶圆细节、电路板特写、GPU 散热风扇、键盘敲击瞬间、屏幕蓝光打在脸上
2. **不要选抽象元素**：不要"数据流""算力""神经网络"这类无法拍摄的概念
3. **不要选符号化元素**：不要 Logo 拼贴、不要"握手=合作"这种象征动作（除非真的是真实新闻发布会握手照）
4. **数量 1-2 个**：宁少勿多。一个有冲击力的真实场景胜过三个杂乱元素

## 场景选择示范

✅ **优秀示范**（真实可拍摄的场景）：
- 简报：苹果财报超预期 → "纽约时代广场夜景，远处摩天楼上苹果logo灯箱亮起，前景出租车流灯光拉成光轨"
- 简报：Anthropic 估值 9000 亿 → "加州沙漠中的数据中心航拍图，整齐排列的服务器机楼在黄昏中闪着蓝光"
- 简报：DeepSeek V4 发布 → "深圳南山区某科技公司办公区夜景，玻璃幕墙后面亮着工程师工位的屏幕蓝光，长焦压缩感"
- 简报：英伟达投资 → "GPU 芯片裸晶特写镜头，金色焊点和绿色基板细节，工业摄影"

❌ **错误示范**（卡通/插画风）：
- "彩色的小机器人围着一个发光的大脑跳舞"（这是儿童绘本风）
- "蓝色背景上漂浮着齿轮、芯片图标和数据线"（这是 PPT 配图风）
- "卡通笔记本电脑上面飘着代码符号和 AI 字样"（这是矢量插画风）

## Prompt 写作规则

1. **开头明确说"摄影作品"或"新闻图片"**：例如 "新闻摄影作品：在..." 或 "纪录片镜头：..."
2. **必须包含摄影专业词汇**：机位、焦距（24mm 广角/85mm 长焦/35mm 标准）、光圈（f/2.8/f/1.4）、快门、构图（三分构图、中心构图、引导线）
3. **强调材质细节**：金属磨砂、玻璃反光、电路板纹理、皮革纹路、屏幕像素感
4. **强调光影**：自然光/环境光/反射光/穿透光（绝不是平均亮度照明）
5. 全程中文（除科技公司英文名 Apple/Google/OpenAI/Anthropic/NVIDIA 等）
6. 不要有任何文字/字母在画面里
7. **控制在 120-180 字**
8. ⚠️ **2.35:1 超宽幅横版**（电影宽银幕）：主体居中，左右两侧描述远景延伸（远处建筑、城市灯火、横向延展的光线、长廊深处）

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
                "temperature": 0.8,
            },
            timeout=60,
        )
        data = resp.json()
        if "choices" not in data:
            print(f"  图片 prompt 生成失败: {data}")
            return None
        core_prompt = data["choices"][0]["message"]["content"].strip()
        core_prompt = re.sub(r'^["""\'`]|["""\'`]$', '', core_prompt)
        core_prompt = re.sub(r'```.*?```', '', core_prompt, flags=re.DOTALL).strip()
        print(f"  核心 prompt: {core_prompt[:120]}...")

        full_prompt = f"{core_prompt}。{CINEMATIC_BASE}。{NEGATIVE_STYLE}"
        return full_prompt
    except Exception as e:
        print(f"  图片 prompt 生成异常: {e}")
        return None


def generate_cover_with_doubao_image(prompt_text, output_path="cover.png"):
    if not prompt_text:
        print("  豆包跳过：prompt 为空")
        return None
    
    # 豆包 Seedream 4.5 要求图片至少 3,686,400 像素（约 3.5MP）
    # v12.4 修正：1920x817 仅 1.57MP 不够，改为 3000x1277（3.83MP，符合公众号 2.35:1）
    size_candidates = [
        ("3000x1277", "2.35:1 超宽幅 / 3.83MP"),  # 公众号封面/朋友圈分享卡片标准比例
        ("16:9", "16:9 比例（豆包枚举值）"),       # 兜底1：豆包枚举的 16:9
        ("2K", "2K 默认正方 / 4MP"),              # 兜底2：豆包默认 2K 一定能成
    ]
    
    for size_value, size_desc in size_candidates:
        try:
            print(f"  请求豆包 Seedream 4.5（size={size_value} / {size_desc}）...")
            resp = requests.post(
                "https://ark.cn-beijing.volces.com/api/v3/images/generations",
                headers={
                    "Authorization": f"Bearer {DOUBAO_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "doubao-seedream-4-5-251128",
                    "prompt": prompt_text,
                    "size": size_value,
                    "response_format": "url",
                    "watermark": False,
                },
                timeout=120,
            )
            
            # 详细日志：HTTP 状态码
            print(f"  豆包 HTTP 状态: {resp.status_code}")
            
            # 解析 JSON
            try:
                data = resp.json()
            except Exception as je:
                print(f"  豆包返回非JSON: {je}, 原文前200字: {resp.text[:200]}")
                continue  # 尝试下一个 size
            
            # 检查返回结构
            if "data" not in data or not data["data"]:
                error_info = data.get("error", {})
                error_msg = error_info.get("message", "未知错误")
                error_code = error_info.get("code", "")
                print(f"  豆包返回异常: code={error_code}, msg={error_msg}")
                print(f"  完整返回: {data}")
                # 如果是 size 不支持，继续尝试下一个；其他错误直接退出
                if "size" in str(error_msg).lower() or "invalid" in str(error_msg).lower() or "unsupported" in str(error_msg).lower():
                    print(f"  推测是 size 参数问题，尝试下一个尺寸...")
                    continue
                else:
                    print(f"  非 size 问题，停止重试")
                    return None
            
            image_url = data["data"][0].get("url")
            if not image_url:
                print(f"  豆包返回缺 url 字段")
                continue
            
            print(f"  豆包返回 url: {image_url[:80]}...")
            img_resp = requests.get(image_url, timeout=60)
            if img_resp.status_code != 200:
                print(f"  下载图片失败: HTTP {img_resp.status_code}")
                continue
            
            with open(output_path, "wb") as f:
                f.write(img_resp.content)
            print(f"  ✓ 主题插图已保存: {output_path} ({len(img_resp.content) // 1024} KB) size={size_value}")
            return output_path
            
        except Exception as e:
            print(f"  豆包异常（size={size_value}）: {type(e).__name__}: {e}")
            continue  # 尝试下一个 size
    
    print(f"  ✗ 豆包所有 size 候选全部失败，将走 HTML 兜底")
    return None


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

# ============================================================
# v12 主流程
# ============================================================

if __name__ == "__main__":
    now_bjt = datetime.now(BJT)
    today = now_bjt.strftime("%Y年%m月%d日")
    title = f"硅谷过去24小时发生了什么？| {today}"

    start_time, end_time = get_time_range()
    print(f"时间窗口: {start_time.strftime('%Y-%m-%d %H:%M')} ~ {end_time.strftime('%Y-%m-%d %H:%M')} BJT")

    print("\n=== 0/9 读取历史 ===")
    recent_quotes = read_recent_quotes()
    recent_titles = read_recent_titles()  # v12.5 新增：读取最近 7 天报道过的标题

    print("\n=== 1/9 抓取新闻（4 国外 + 3 国内 RSS + 4 NewsNow + 3 AI 公司官方）===")
    print("【英文源】")
    google_articles = fetch_google_news()
    newsapi_articles = fetch_newsapi()
    hn_articles = fetch_hackernews()
    tc_articles = fetch_techcrunch_rss()
    
    print("【AI 公司官方源(v13.0 Day 2 新增)】")
    openai_articles = fetch_openai_blog()
    deepmind_articles = fetch_deepmind_blog()
    anthropic_articles = fetch_anthropic_news()
    
    print("【国内 RSS 源】")
    ithome_articles = fetch_ithome()
    jqzx_articles = fetch_jiqizhixin()
    kr36_articles = fetch_36kr()
    
    print("【NewsNow 中文一手快讯】")
    newsnow_articles = fetch_all_newsnow()

    all_articles = (
        google_articles + newsapi_articles + hn_articles + tc_articles
        + openai_articles + deepmind_articles + anthropic_articles  # v13.0 Day 2 新增
        + ithome_articles + jqzx_articles + kr36_articles
        + newsnow_articles
    )
    print(f"\n  合计原始素材：{len(all_articles)} 条")

    print("\n=== 2/9 时间过滤（24小时硬约束，不足放宽到36h）===")
    all_articles = filter_by_time(all_articles, hours=24, fallback_hours=36, min_count=8)
    
    # v12.5 新增：历史标题查重 - 防止过期热点新闻（如 NewsNow 热门榜常驻条目）反复出现
    print("  历史标题查重...")
    all_articles = filter_by_recent_titles(all_articles, recent_titles)
    print(f"  最终素材池：{len(all_articles)} 条")

    if not all_articles:
        send_pushplus(title, "<p>过去24小时暂无重要科技动态。</p>")
        print("无新闻，已发送空报")
    else:
        print("\n=== 3/9 三元组聚类去重（多源命中合并）===")
        clusters = cluster_articles(all_articles, time_window_hours=24)
        multi_source_count = sum(1 for c in clusters if len(c["all"]) > 1)
        print(f"  {len(all_articles)} 条 → {len(clusters)} 个事件簇（其中 {multi_source_count} 个多源命中）")
        
        # 给 DeepSeek 用合并后的事件簇
        merged_articles = merge_clusters_to_articles(clusters)
        
        # v12.5 新增：历史标题查重，过滤掉最近 7 天报道过的事件
        print("\n=== 3.5/9 历史标题查重（防过期热点污染）===")
        history_titles = read_last_titles(days=7)
        merged_articles, removed_dup, _ = filter_articles_against_history(merged_articles, history_titles)
        print(f"  查重后剩余 {len(merged_articles)} 条事件簇")
        
        print("\n=== 4/9 跨源事实验证（仅 TOP 3 多源命中事件）===")
        validations = validate_top_clusters(clusters, max_validations=3)
        print(f"  完成 {len(validations)} 个事件验证")

        print("\n=== 5/9 DeepSeek 整理（雷锋网风格深度编辑）===")
        organized = deepseek_organize_news(merged_articles)

        if organized:
            print("\n=== 6/9 模板拼接 HTML（含验证警告）===")
            now_for_render = datetime.now(BJT)
            final = build_news_html(organized, now_for_render, validations)
            topics = organized.get("topics", [])
        else:
            final = "<p>AI 整理失败。</p>"
            organized = {"headline": "今日科技要闻", "topics": []}
            topics = []

        # 生成主题封面图
        print("\n=== 7/9 生成主题封面图（豆包 Seedream 4.5）===")
        
        # v13.0-day1.1 封面图开关：DISABLE_COVER_IMAGE=1 → 整段跳过
        if DISABLE_COVER_IMAGE:
            print("  ⏭ DISABLE_COVER_IMAGE 已开启，跳过封面图生成")
            cover_url = None
            cover_path = None
        else:
            main_title, sub_title = extract_titles_from_organized(organized)
            if not topics:
                topics = ["AI动态", "芯片算力", "国内创投", "海外巨头", "新品发布"]
            print(f"  主标题: {main_title} / {sub_title}")
            print(f"  话题标签: {topics}")

            cover_url = None
            cover_path = None

            if organized:
                digest_for_image = json.dumps(organized, ensure_ascii=False)[:2000]
                print("  步骤 7.1: 生成图片 prompt...")
                image_prompt = generate_image_prompt(digest_for_image)
                if image_prompt:
                    print("  步骤 7.2: 豆包 Seedream 4.5 生图...")
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

        # 日历卡（保留品牌资产）
        print("\n=== 8/9 生成日历卡片 ===")
        quote_text = ""
        quote_author = ""
        DEFAULT_QUOTES = [
            ("预测未来的最好方式，就是去创造它。", "艾伦·凯（计算机科学家）"),
            ("我们构建的系统，最终会暴露出构建者的优先级。", "布莱恩·克里斯蒂安（作家）"),
            ("技术是一种权力，而权力需要制衡。", "蒂姆·伯纳斯-李（万维网发明者）"),
            ("简单是终极的复杂。", "达·芬奇"),
            ("好的设计，是把复杂的事变简单。", "乔布斯"),
            ("我们高估了短期的变化，低估了长期的革命。", "罗伊·阿玛拉"),
            ("代码不会说谎，注释才会。", "罗伯特·C·马丁"),
            ("做正确的事，再把事做正确。", "彼得·德鲁克"),
            ("创新区分领导者和追随者。", "史蒂夫·乔布斯"),
            ("如果你不能简单地解释它，说明你还没有真正理解它。", "爱因斯坦"),
        ]
        random.seed(datetime.now(BJT).strftime("%Y%m%d"))
        for q_text, q_author in random.sample(DEFAULT_QUOTES, len(DEFAULT_QUOTES)):
            if q_text not in (recent_quotes or []):
                quote_text, quote_author = q_text, q_author
                break
        if not quote_text:
            quote_text, quote_author = DEFAULT_QUOTES[0]

        calendar = generate_calendar_card(quote_text, quote_author)
        final = final + calendar + DISCLAIMER

        print("\n=== 9/9 推送微信 ===")
        send_pushplus(title, final)

        if quote_text:
            save_recent_quote(quote_text, quote_author)
        
        # v12.5 新增：保存今日报道过的标题到历史，供后续查重
        if organized:
            today_titles = []
            # v12.5：今日头条
            he = organized.get("headline_event")
            if isinstance(he, dict):
                t = he.get("title", "").strip()
                if t:
                    today_titles.append(t)
            # 国际/国内/大佬
            for section in ("international", "domestic", "big_names"):
                for item in organized.get(section, []) or []:
                    t = item.get("title", "").strip()
                    if t:
                        today_titles.append(t)
            if today_titles:
                save_today_titles(today_titles)

    print("\n全部完成！")
