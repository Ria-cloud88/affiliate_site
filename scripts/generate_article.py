"""
アフィリエイト記事自動生成スクリプト
使い方:
  python scripts/generate_article.py              # ランダム記事
  python scripts/generate_article.py --topic "Claude Codeソースコード流出"
  python scripts/generate_article.py --news       # RSSから最新ニュース取得して生成
"""

import anthropic
import argparse
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

# APIキーの改行文字を除去（GitHub Secrets貼り付け時の混入対策）
if "ANTHROPIC_API_KEY" in os.environ:
    os.environ["ANTHROPIC_API_KEY"] = os.environ["ANTHROPIC_API_KEY"].strip()

# ジャンル別キーワードプール
KEYWORD_POOLS = {
    "AIツール": [
        ("ChatGPT 使い方 初心者 完全ガイド", ["ChatGPT", "AI", "無料", "活用法"]),
        ("Claude AI 使い方 ChatGPTとの違い 比較", ["Claude", "Anthropic", "AI比較", "無料"]),
        ("Perplexity AI 使い方 検索 おすすめ", ["Perplexity", "AI検索", "無料", "使い方"]),
        ("Gemini 使い方 Google AI 初心者", ["Gemini", "Google", "無料", "AI"]),
        ("AI画像生成 おすすめツール 比較 2024", ["Midjourney", "Stable Diffusion", "DALL-E", "無料"]),
        ("NotionAI 使い方 効率化 メモ", ["Notion", "AI", "メモ", "生産性"]),
        ("Copilot 使い方 プログラミング 効率化", ["GitHub Copilot", "AI", "コーディング", "無料"]),
    ],
    "自動化ツール": [
        ("Zapier 使い方 自動化 初心者 おすすめ", ["Zapier", "自動化", "無料", "連携"]),
        ("Make (Integromat) 使い方 Zapierとの違い", ["Make", "Zapier", "自動化", "比較"]),
        ("n8n 使い方 無料 自動化 ツール", ["n8n", "無料", "自動化", "オープンソース"]),
        ("Google Apps Script 使い方 入門", ["GAS", "Google", "自動化", "無料"]),
        ("Python 自動化 初心者 おすすめ 使い方", ["Python", "自動化", "プログラミング", "無料"]),
    ],
    "副業": [
        ("AI副業 おすすめ 初心者 稼ぎ方 2024", ["AI", "副業", "在宅", "稼ぐ"]),
        ("ブログ アフィリエイト 始め方 初心者 収益化", ["ブログ", "アフィリエイト", "副業", "収益"]),
        ("クラウドソーシング おすすめ 比較 副業", ["クラウドワークス", "ランサーズ", "副業", "在宅"]),
        ("動画編集 副業 始め方 ソフト おすすめ", ["動画編集", "副業", "YouTube", "稼ぐ"]),
        ("プログラミング 副業 初心者 おすすめ言語", ["プログラミング", "副業", "フリーランス", "稼ぐ"]),
        ("せどり 副業 始め方 初心者 稼ぎ方", ["せどり", "副業", "Amazon", "転売"]),
    ],
    "ガジェット": [
        ("ワイヤレスイヤホン おすすめ 比較 2024", ["イヤホン", "AirPods", "コスパ", "ノイキャン"]),
        ("メカニカルキーボード おすすめ 比較 初心者", ["キーボード", "メカニカル", "テレワーク", "コスパ"]),
        ("モバイルバッテリー おすすめ 大容量 比較", ["モバイルバッテリー", "充電", "コスパ", "軽量"]),
        ("Webカメラ おすすめ テレワーク 比較", ["Webカメラ", "テレワーク", "リモート", "HD"]),
        ("スマートスピーカー おすすめ 比較 Echo Alexa", ["Echo", "Alexa", "スマートホーム", "音声"]),
    ],
    "生活改善": [
        ("節約 アプリ おすすめ 家計管理 比較", ["節約", "家計", "アプリ", "無料"]),
        ("タスク管理 アプリ おすすめ 比較 2024", ["Todoist", "Notion", "タスク", "生産性"]),
        ("睡眠 改善 アプリ おすすめ 効果", ["睡眠", "アプリ", "健康", "改善"]),
        ("読書 習慣 アプリ Kindle おすすめ", ["Kindle", "読書", "習慣", "電子書籍"]),
        ("時間管理 テクニック 生産性 向上 方法", ["時間管理", "ポモドーロ", "生産性", "効率化"]),
    ],
}

# ニュース取得先RSSフィード（日本語テック系）
NEWS_FEEDS = [
    ("Gigazine", "https://gigazine.net/news/rss_2.0/"),
    ("ITmedia AI+", "https://rss.itmedia.co.jp/rss/2.0/aiplus.xml"),
    ("Google News AI", "https://news.google.com/rss/search?q=AI%20%E4%BA%BA%E5%B7%A5%E7%9F%A5%E8%83%BD&hl=ja&gl=JP&ceid=JP:ja"),
    ("Google News 副業", "https://news.google.com/rss/search?q=%E5%89%AF%E6%A5%AD%20%E3%83%95%E3%83%AA%E3%83%BC%E3%83%A9%E3%83%B3%E3%82%B9&hl=ja&gl=JP&ceid=JP:ja"),
]

SYSTEM_PROMPT = """あなたはSEO最適化された、詳細で実用的なブログ記事を書く編集者です。AIっぽさのない、人間らしい自然な日本語を使います。

# ■超重要：文字数指定（厳守）【絶対に3000字以上】
【最小文字数】 絶対に3000文字以上。2500字では失敗
【推奨範囲】 3500～4500文字（プロレベルは4000字超が基準）
【計算方法】 句点「。」の数を数える。最低100～130個の句点が必要
【チェック】 毎段落は3～5文を目安に。短い段落はNG

# ■キーワード埋め込み（必須）
【キーワード】 記事タイトルに含まれるメインキーワードを本文に「最低8回」含める
【関連KW】 類似キーワード・言い換え表現も10回以上含める
【計算】 すべてのキーワード出現を数えてから出力

# ■記事構成（プロフェッショナル版）
1. # タイトル
2. 導入（読者の悩みを1～2文で。50～100字）
3. ## 見出し1（基本知識。600～700字）
4. ## 見出し2（重要なポイント・メリット。表を含む。700～900字）【表必須】
5. ## 見出し3（比較・選び方。複数の表。700～900字）【複数表推奨】
6. ## 見出し4（詳細な使い方・実践例。600～800字）
7. ## 見出し5（さらに詳しい情報。400～500字）
8. ## 見出し6（よくある質問・FAQ。300～400字）
9. ## 見出し7（まとめ・CTA。300～400字）

合計：3000字以上（4000字超が目安）

# ■表の生成（複数表必須）
・記事に「Markdown 表」を最低2～3個含める（複数は必須）
・比較表（機能・料金・特徴の比較）
・一覧表（ポイント・メリット・デメリット）
・手順表（ステップ・説明）
・詳細な表を自然に配置

# ■文体（プロレベル）
・1文は15～25字が最適。短すぎず長すぎず
・「です」「ます」で統一。絶対に「ある」「いる」と混ぜない
・各見出し下に最低10～15文を書く（充実した内容、段落分ける）
・段落は3～5文で構成。長すぎる段落は避ける
・同じ単語の繰り返しは避ける。同義語で言い換える
・リストアップ（箇条書き）や数字を多用して可視化
・「〜です」「〜ます」で句点「。」をカウント（最低100個必須）

# ■完全禁止（これらのフレーズが1個でもあれば失敗）
禁止ワード一覧：
「いかがでしたか」「ぜひご覧ください」「〜と思います」「〜といえます」
「重要です」「大切です」「このように」「その結果」「注目されています」
「話題になっています」「こちら」「ご紹介します」「できます」「できるようになります」
「考えられます」「言えるでしょう」「わかります」「もう一度」「さらに詳しく」
「完成」「---」（末尾のマーカー）

もしこれらが1個でも含まれたら、記事を書き直す。

# ■出力形式
・Markdown のみ
・複数の表を含める（Markdown 表形式）
・3000～4500文字が目安（3000字は絶対最小）
・前置きなし。「# タイトル」から開始
・各見出し下に画像埋め込みは ![] で自動生成予定

# ■品質チェック（自動判定）
・文字数が3000字以上か確認
・表が2個以上含まれているか確認
・見出しが7個以上あるか確認
・メインキーワードが8回以上含まれるか確認
・句点「。」が100個以上あるか確認
すべてOKなら「✓ 高品質」、1個でも不足なら修正する"""


def select_keyword():
    """ジャンルとキーワードをランダム選択"""
    genre = random.choice(list(KEYWORD_POOLS.keys()))
    keyword_data = random.choice(KEYWORD_POOLS[genre])
    main_kw, related_kws = keyword_data
    return genre, main_kw, related_kws


def fetch_news(max_items: int = 10) -> list[dict]:
    """RSSフィードから最新ニュースを取得"""
    import ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    items = []
    for source_name, feed_url in NEWS_FEEDS:
        try:
            req = urllib.request.Request(feed_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                xml_data = resp.read()
            root = ET.fromstring(xml_data)
            # RSS 2.0形式
            for item in root.findall(".//item")[:3]:
                title = item.findtext("title", "").strip()
                desc = item.findtext("description", "").strip()
                link = item.findtext("link", "").strip()
                pub_date = item.findtext("pubDate", "").strip()
                if title:
                    items.append({
                        "source": source_name,
                        "title": title,
                        "description": re.sub(r'<[^>]+>', '', desc)[:200],
                        "link": link,
                        "pubDate": pub_date,
                    })
            print(f"  {source_name}: {len(items)}件取得")
        except Exception as e:
            print(f"  {source_name} 取得失敗: {e}")

    return items[:max_items]


def select_news_topic(news_items: list[dict]) -> dict:
    """ニュース一覧から記事にするトピックを選択（インタラクティブ）"""
    print("\n--- 取得したニュース ---")
    for i, item in enumerate(news_items):
        print(f"[{i+1}] [{item['source']}] {item['title']}")
    print(f"[0] ランダム選択")
    print()

    while True:
        try:
            choice = input(f"記事にするニュースを選択 (0-{len(news_items)}): ").strip()
            n = int(choice)
            if n == 0:
                return random.choice(news_items)
            elif 1 <= n <= len(news_items):
                return news_items[n - 1]
        except (ValueError, KeyboardInterrupt):
            pass


def generate_article(main_kw: str, related_kws: list, genre: str) -> str:
    """Claude APIで通常記事生成"""
    client = anthropic.Anthropic()

    prompt = f"""以下のキーワードで高品質なアフィリエイトブログ記事を生成してください。

ジャンル: {genre}
メインキーワード: {main_kw}
関連キーワード: {', '.join(related_kws)}

記事の冒頭は # タイトル から始めてください。"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}],
        system=SYSTEM_PROMPT,
    )

    return message.content[0].text


def generate_news_article(topic: str, source_info: str = "") -> str:
    """Claude APIでニュース系記事生成"""
    client = anthropic.Anthropic()

    news_system_prompt = SYSTEM_PROMPT + """

# ■ニュース記事追加ルール（重要）
・「最新情報」「速報」「〜が話題」などの時事性を明確に出す
・ニュースの背景・影響・読者への具体的な意味を必ず詳しく解説
・事実ベースで書き、憶測は「〜とみられる」「〜と考えられます」と明示
・複数の視点や専門家の見解を含める
・関連するサービス・ツール・解決策を自然に挿入
・公開日が重要なので「2026年最新」「〜速報」などを含める
・読者が「自分はこのニュースに対して何をすべきか」が分かる実用的な内容"""

    prompt = f"""以下のトピックについて、最新ニュースを元にした解説記事を生成してください。

トピック: {topic}
{f'参考情報: {source_info}' if source_info else ''}

読者が「このニュースで自分はどう動くべきか」がわかる実用的な内容にしてください。
記事の冒頭は # タイトル から始めてください。"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}],
        system=news_system_prompt,
    )

    return message.content[0].text


def extract_title(content: str) -> str:
    """記事本文からタイトルを抽出"""
    match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return "無題の記事"


def slugify(text: str) -> str:
    """スラッグ生成（英数字・ハイフンのみ）"""
    # 日本語はローマ字変換せず、日付+ランダム番号で代替
    import hashlib
    h = hashlib.md5(text.encode()).hexdigest()[:6]
    return h


GENRE_KEYWORDS = {
    "AIツール": "technology,computer,artificial-intelligence",
    "自動化ツール": "automation,computer,productivity",
    "副業": "business,work,laptop",
    "ガジェット": "gadget,technology,electronics",
    "生活改善": "lifestyle,wellness,health",
    "ニュース": "technology,news,digital",
}


def generate_hero_image(title: str, genre: str, slug: str) -> str | None:
    """画像取得（Pollinations優先 → loremflickr → picsum.photos）"""
    import urllib.parse as up
    import time
    seed = abs(hash(slug)) % 9999
    prompt = f"blog thumbnail, {genre}, {title[:60]}, professional, 16:9"
    kw = GENRE_KEYWORDS.get(genre, "technology,business")

    img_dir = Path("public/images/blog")
    img_dir.mkdir(parents=True, exist_ok=True)
    img_path = img_dir / f"{slug}.jpg"

    def fetch(url: str) -> bool:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
            if len(data) < 1000:  # 壊れたレスポンス除外
                return False
            img_path.write_bytes(data)
            return True
        except Exception:
            return False

    # 1. Pollinations.ai（AI生成・記事に最も即した画像）
    pollinations_url = f"https://image.pollinations.ai/prompt/{up.quote(prompt)}?width=800&height=400&nologo=true&seed={seed}"
    try:
        req = urllib.request.Request(pollinations_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = resp.read()
        if len(data) >= 1000:
            img_path.write_bytes(data)
            print(f"画像取得完了 (Pollinations): {img_path}")
            return f"/images/blog/{slug}.jpg"
    except urllib.error.HTTPError as e:
        print(f"Pollinations {e.code}: フォールバックへ")
    except Exception as e:
        print(f"Pollinations 失敗: {type(e).__name__}")

    # 2. loremflickr（キーワード検索・ジャンルに即した写真）
    for kw_try in [kw, kw.split(",")[0]]:
        url = f"https://loremflickr.com/800/400/{kw_try}?lock={seed}"
        if fetch(url):
            print(f"画像取得完了 (loremflickr/{kw_try}): {img_path}")
            return f"/images/blog/{slug}.jpg"

    # 3. picsum.photos（完全ランダム・確実に取得できる）
    url = f"https://picsum.photos/seed/{seed}/800/400"
    if fetch(url):
        print(f"画像取得完了 (picsum): {img_path}")
        return f"/images/blog/{slug}.jpg"
    print(f"画像取得失敗: {slug}")
    return None


def embed_images_in_article(content: str, genre: str, slug: str) -> str:
    """記事の各見出しに画像を埋め込む"""
    import urllib.parse as up

    # ## で始まる見出しを抽出（最大3個）
    headings = re.findall(r'^## (.+)$', content, re.MULTILINE)[:3]

    img_dir = Path("public/images/blog")
    img_dir.mkdir(parents=True, exist_ok=True)

    images_to_embed = {}

    for i, heading in enumerate(headings):
        img_num = i + 1
        img_filename = f"{slug}-{img_num}.jpg"
        img_path = img_dir / img_filename

        # 画像キーワード生成（見出しから）
        seed = abs(hash(f"{slug}-{heading}")) % 9999
        prompt = f"article section image, {genre}, {heading[:60]}, professional, 16:9"
        kw = GENRE_KEYWORDS.get(genre, "technology,business")

        # 画像取得を試みる
        try:
            pollinations_url = f"https://image.pollinations.ai/prompt/{up.quote(prompt)}?width=800&height=400&nologo=true&seed={seed}"
            req = urllib.request.Request(pollinations_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = resp.read()
            if len(data) >= 1000:
                img_path.write_bytes(data)
                images_to_embed[heading] = f"/images/blog/{img_filename}"
                print(f"  見出し画像取得完了 ({i+1}/{len(headings)}): {img_filename}")
        except Exception as e:
            print(f"  見出し画像失敗 ({heading}): {type(e).__name__}")

    # 見出し後に画像を埋め込む
    if images_to_embed:
        for heading, img_url in images_to_embed.items():
            # ## <見出し> を見つけて、その直後に画像を挿入
            pattern = f"(^## {re.escape(heading)}$)"
            replacement = f"\\1\n\n![{heading}]({img_url})"
            content = re.sub(pattern, replacement, content, count=1, flags=re.MULTILINE)

    return content


def save_article(content: str, genre: str, main_kw: str, category: str = None, source: str = None) -> Path:
    """記事をMarkdownファイルとして保存"""
    title = extract_title(content)
    today = datetime.now().strftime("%Y-%m-%d")
    slug = f"{today}-{slugify(main_kw)}"

    # frontmatter生成
    # 本文からh1タイトルを除去してdescriptionを抽出
    body_without_title = re.sub(r'^#\s+.+\n', '', content, count=1).strip()
    # 最初の段落をdescriptionに
    first_para = re.split(r'\n\n', body_without_title)[0]
    description = re.sub(r'[#*`]', '', first_para)[:120].replace('\n', ' ').strip()

    hero_image = generate_hero_image(title, genre, slug)
    hero_line = f"\nheroImage: '{hero_image}'" if hero_image else ""

    # category と source フィールドを追加
    category_line = f"\ncategory: '{category}'" if category else ""
    source_line = f"\nsource: '{source}'" if source else ""

    frontmatter = f"""---
title: '{title.replace("'", "''")}'
description: '{description.replace("'", "''")}'
pubDate: '{today}'
genre: '{genre}'{hero_line}{category_line}{source_line}
---

"""

    # h1タイトルを除去した本文
    article_body = body_without_title

    # 「完成」マーカーなどの不要な末尾テキストを削除
    article_body = re.sub(r'\n+完成\s*$', '', article_body)
    article_body = re.sub(r'\n+---\s*$', '', article_body)

    # 本文に見出し画像を埋め込む
    try:
        print("見出し画像を生成中...")
        article_body = embed_images_in_article(article_body, genre, slug)
    except Exception as e:
        print(f"見出し画像埋め込み失敗: {e}")

    full_content = frontmatter + article_body

    output_path = Path("src/content/blog") / f"{slug}.md"
    output_path.write_text(full_content, encoding="utf-8")

    return output_path


def load_keywords_from_pool(count: int = 1) -> list[tuple[str, str, list[str]]]:
    """
    keywords_pool.json から優先度付きでキーワードを取得
    優先順：新ジャンル > 高スコアキーワード > 既存KEYWORD_POOLS（フォールバック）
    戻り値: [(keyword, category, related_kws), ...]
    """
    keywords_pool_path = Path("scripts/keywords_pool.json")

    if not keywords_pool_path.exists():
        print("WARNING: keywords_pool.json が見つかりません。既存キーワードプールから選択します")
        # フォールバック：既存の KEYWORD_POOLS から選択
        result = []
        for i in range(count):
            genre, main_kw, related_kws = select_keyword()
            result.append((main_kw, genre, related_kws))
        return result

    try:
        pool = json.loads(keywords_pool_path.read_text(encoding='utf-8'))

        candidates = []

        # すべてのカテゴリから pending キーワードを収集
        for category, items in pool.items():
            if not isinstance(items, list):
                continue

            for item in items:
                if item.get('status') == 'pending' and item.get('keyword'):
                    # 優先度スコア計算
                    priority = item.get('score', 0)

                    # 新ジャンル（genre_name を持つ）なら優先度UP
                    if item.get('genre_name'):
                        priority += 50

                    candidates.append({
                        'keyword': item.get('keyword'),
                        'category': category,
                        'related_kws': item.get('keywords', []) if isinstance(item.get('keywords'), list) else [],
                        'priority': priority,
                        'item': item  # 元のアイテムを保持
                    })

        # 優先度でソート（降順）
        candidates.sort(key=lambda x: x['priority'], reverse=True)

        # 上位 count 個を返す
        result = []
        for i, c in enumerate(candidates[:count]):
            result.append((c['keyword'], c['category'], c['related_kws']))

        return result

    except Exception as e:
        print(f"ERROR: keywords_pool.json 読み込み失敗: {e}")
        return []


def update_keyword_status_in_pool(keyword: str, new_status: str = 'completed') -> None:
    """keywords_pool.json のキーワードの status を更新"""
    keywords_pool_path = Path("scripts/keywords_pool.json")

    if not keywords_pool_path.exists():
        return

    try:
        pool = json.loads(keywords_pool_path.read_text(encoding='utf-8'))

        for category, items in pool.items():
            if not isinstance(items, list):
                continue

            for item in items:
                if item.get('keyword') == keyword:
                    item['status'] = new_status
                    break

        keywords_pool_path.write_text(
            json.dumps(pool, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )

    except Exception as e:
        print(f"WARNING: status 更新失敗: {e}")


def check_article_quality(file_path: Path, keyword: str) -> bool:
    """記事品質をチェック（簡易版）"""
    try:
        from check_article_quality import generate_quality_report

        text = file_path.read_text(encoding="utf-8")
        report = generate_quality_report(text, keyword)

        status = report["overall_status"]
        score = report["overall_score"]

        print(f"\n📊 品質チェック: {status} (スコア: {score}/100)")

        # 警告表示
        if report["ai_likeness"]["found_phrases"]:
            print(f"  ⚠️ AIっぽい表現: {report['ai_likeness']['total_issues']}個")

        if report["word_count"]["status"] != "OK":
            print(f"  ⚠️ 文字数: {report['word_count']['char_count']} 字 (推奨: 2000-3500)")

        return status == "PASS"

    except ImportError:
        print("⚠️ 品質検査スクリプトが見つかりません")
        return True  # エラーでも続行


def main():
    parser = argparse.ArgumentParser(description="アフィリエイト記事自動生成")
    parser.add_argument("--topic", type=str, help="記事にするトピック（例: 'Claude Codeソースコード流出'）")
    parser.add_argument("--news", action="store_true", help="RSSから最新ニュースを取得して記事生成")
    parser.add_argument("--auto", action="store_true", help="対話なしで自動実行（--newsと組み合わせてランダム選択）")
    parser.add_argument("--auto-discover", type=int, metavar="N", help="キーワード自動発掘で N 個の記事を生成（優先度付け）")
    args = parser.parse_args()

    print("記事生成を開始します...")

    if args.auto_discover:
        # 自動発掘モード：N 個の記事を生成
        print(f"\n自動発掘モード: {args.auto_discover} 記事を生成します")

        # 事前に必要な数のキーワードを全部ロード
        keywords = load_keywords_from_pool(count=args.auto_discover)

        if not keywords:
            print("ERROR: keywords_pool.json にキーワードがありません")
            print("先に: python scripts/discover_keywords.py --update を実行してください")
            sys.exit(1)

        # ロードしたキーワード数を記録（途中で更新されないように）
        available_count = len(keywords)
        print(f"利用可能なキーワード: {available_count}個")

        generated_count = 0
        for i, (keyword, category, related_kws) in enumerate(keywords, 1):
            print(f"\n[{i}/{args.auto_discover}] キーワード: {keyword}")
            print("Claude APIで記事生成中...")

            try:
                content = generate_article(keyword, related_kws if related_kws else [keyword], category)
                output_path = save_article(content, category, keyword, category=category, source='auto-discover')
                print(f"✓ 完了: {output_path}")

                # 品質チェック
                check_article_quality(output_path, keyword)

                # status を completed に更新
                update_keyword_status_in_pool(keyword, 'completed')
                generated_count += 1

                # レート制限対策
                if i < len(keywords):
                    time.sleep(3)

            except Exception as e:
                print(f"✗ エラー: {e}")

        print(f"\n生成完了: {generated_count}/{args.auto_discover}記事")

    elif args.topic:
        # トピック直接指定モード
        print(f"トピック: {args.topic}")
        print("Claude APIで記事生成中...")
        content = generate_news_article(args.topic)
        output_path = save_article(content, "ニュース", args.topic)
        print(f"✓ 完了: {output_path}")
        check_article_quality(output_path, args.topic)

    elif args.news:
        # RSSニュース取得モード
        print("RSSフィードからニュースを取得中...")
        news_items = fetch_news()
        if not news_items:
            print("ニュース取得失敗。通常モードで実行します。")
            genre, main_kw, related_kws = select_keyword()
            content = generate_article(main_kw, related_kws, genre)
            output_path = save_article(content, genre, main_kw)
        else:
            if args.auto:
                selected = random.choice(news_items)
                print(f"自動選択: {selected['title']}")
            else:
                selected = select_news_topic(news_items)
            print(f"\n選択: {selected['title']}")
            print("Claude APIで記事生成中...")
            source_info = f"{selected['description']} (出典: {selected['source']})"
            content = generate_news_article(selected['title'], source_info)
            output_path = save_article(content, "ニュース", selected['title'])
            print(f"✓ 完了: {output_path}")
            check_article_quality(output_path, selected['title'])

    else:
        # 通常ランダムモード
        genre, main_kw, related_kws = select_keyword()
        print(f"ジャンル: {genre}")
        print(f"メインKW: {main_kw}")
        print(f"関連KW: {', '.join(related_kws)}")
        print("Claude APIで記事生成中...")
        content = generate_article(main_kw, related_kws, genre)
        output_path = save_article(content, genre, main_kw)
        print(f"✓ 完了: {output_path}")
        check_article_quality(output_path, main_kw)

    print(f"\n文字数: {len(content)}文字")


if __name__ == "__main__":
    main()
