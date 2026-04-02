"""
アフィリエイト記事自動生成スクリプト
使い方: python scripts/generate_article.py
"""

import anthropic
import random
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

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

SYSTEM_PROMPT = """あなたはSEOとアフィリエイト収益最大化に特化した記事生成AIです。

# ■記事要件
・日本語で出力
・3000〜5000文字
・初心者にも理解できる内容
・具体例・手順を必ず含める
・オリジナル性を意識（コピペ感禁止）

# ■構成テンプレート（必須）
1. タイトル（クリック率を意識）
2. 導入（読者の悩みを明確化）
3. 結論（最初に答えを提示）
4. 本文（見出し構造で詳しく解説）
5. メリット・デメリット
6. 比較（可能な場合は必ず入れる）
7. おすすめの人
8. まとめ
9. CTA（行動喚起）

# ■SEOルール
・h2 / h3 見出しを適切に使用
・キーワードを自然に含める
・検索意図に完全一致する内容にする

# ■収益化ルール
・記事内で自然にサービス・ツールを紹介する
・無料体験・無料プランを積極的に訴求
・「今すぐ試す理由」を明確にする
・最後に必ず行動喚起を入れる

# ■出力形式
・Markdown形式（frontmatterなし、本文のみ）
・最初の行は # タイトル から始める

# ■禁止事項
・内容が薄い記事
・抽象的で中身のない説明
・同じ内容の繰り返し
・AI特有の不自然な文章"""


def select_keyword():
    """ジャンルとキーワードをランダム選択"""
    genre = random.choice(list(KEYWORD_POOLS.keys()))
    keyword_data = random.choice(KEYWORD_POOLS[genre])
    main_kw, related_kws = keyword_data
    return genre, main_kw, related_kws


def generate_article(main_kw: str, related_kws: list, genre: str) -> str:
    """Claude APIで記事生成"""
    client = anthropic.Anthropic()

    prompt = f"""以下のキーワードで高品質なアフィリエイトブログ記事を生成してください。

ジャンル: {genre}
メインキーワード: {main_kw}
関連キーワード: {', '.join(related_kws)}

記事の冒頭は # タイトル から始めてください。"""

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}],
        system=SYSTEM_PROMPT,
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


def generate_hero_image(title: str, genre: str, slug: str) -> str | None:
    """AI画像生成（Pollinations優先 → loremflickrフォールバック）"""
    import urllib.parse as up
    seed = abs(hash(slug)) % 9999
    prompt = f"blog thumbnail, {genre}, {title[:60]}, professional, 16:9"

    sources = [
        f"https://image.pollinations.ai/prompt/{up.quote(prompt)}?width=800&height=400&nologo=true&seed={seed}",
        f"https://loremflickr.com/800/400/{up.quote(genre)},technology?lock={seed}",
    ]

    img_dir = Path("public/images/blog")
    img_dir.mkdir(parents=True, exist_ok=True)
    img_path = img_dir / f"{slug}.jpg"

    for url in sources:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                img_path.write_bytes(resp.read())
            source = "Pollinations" if "pollinations" in url else "loremflickr"
            print(f"画像生成完了 ({source}): {img_path}")
            return f"/affiliate_site/images/blog/{slug}.jpg"
        except Exception as e:
            print(f"画像生成失敗 ({url.split('/')[2]}): {e}")

    return None


def save_article(content: str, genre: str, main_kw: str) -> Path:
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

    frontmatter = f"""---
title: '{title.replace("'", "''")}'
description: '{description.replace("'", "''")}'
pubDate: '{today}'
genre: '{genre}'{hero_line}
---

"""

    # h1タイトルを除去した本文
    article_body = body_without_title

    full_content = frontmatter + article_body

    output_path = Path("src/content/blog") / f"{slug}.md"
    output_path.write_text(full_content, encoding="utf-8")

    return output_path


def main():
    print("記事生成を開始します...")

    genre, main_kw, related_kws = select_keyword()
    print(f"ジャンル: {genre}")
    print(f"メインKW: {main_kw}")
    print(f"関連KW: {', '.join(related_kws)}")
    print("Claude APIで記事生成中...")

    content = generate_article(main_kw, related_kws, genre)
    output_path = save_article(content, genre, main_kw)

    print(f"完了: {output_path}")
    print(f"文字数: {len(content)}文字")


if __name__ == "__main__":
    main()
