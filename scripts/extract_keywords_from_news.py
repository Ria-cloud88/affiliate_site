"""
ニュース RSS フィードから自動的にトレンドキーワードを抽出
完全自動化版（Python のみ）

使い方:
  python scripts/extract_keywords_from_news.py
  python scripts/extract_keywords_from_news.py --update  # JSON に追加
"""

import feedparser
import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from collections import Counter

import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

# ニュース RSS フィード（複数ジャンル対応）
NEWS_FEEDS = [
    # === AI・テック系（確実なフィード） ===
    ("Gigazine", "https://gigazine.net/news/rss_2.0/"),
    ("ITmedia AI+", "https://rss.itmedia.co.jp/rss/2.0/aiplus.xml"),
    ("ITmedia NEWS", "https://rss.itmedia.co.jp/rss/2.0/news.xml"),

    # === ビジネス・スタートアップ ===
    ("TechCrunch Japan", "https://jp.techcrunch.com/feed/"),
    ("Startup Times", "https://startupipt.com/feed/"),

    # === ガジェット・家電 ===
    ("Engadget Japanese", "https://japanese.engadget.com/rss.xml"),
    ("CNET Japan", "https://japan.cnet.com/xml/rss.xml"),

    # === プログラミング・開発 ===
    ("Zenn トレンド", "https://zenn.dev/feed.atom"),
    ("GitHub Trending", "https://github.com/trending.atom"),

    # === 副業・キャリア ===
    ("Wantedly News", "https://news.wantedly.com/feed"),

    # === IT・テック総合 ===
    ("マイナビニュース", "https://news.mynavi.jp/rss/index.xml"),
    ("アスキー", "https://ascii.jp/feed.xml"),

    # === Google News（集約） ===
    ("Google News AI", "https://news.google.com/rss/search?q=AI&hl=ja&gl=JP&ceid=JP:ja"),
    ("Google News 副業", "https://news.google.com/rss/search?q=副業&hl=ja&gl=JP&ceid=JP:ja"),
    ("Google News スタートアップ", "https://news.google.com/rss/search?q=スタートアップ&hl=ja&gl=JP&ceid=JP:ja"),
]

# トレンド判定用：ニュースに頻出するキーワード = トレンド
KEYWORD_PATTERNS = {
    'AIツール': [
        'AI', 'Claude', 'ChatGPT', 'Gemini', 'GPT', 'LLM', '言語モデル',
        'Copilot', 'Perplexity', '生成AI', 'Anthropic', 'OpenAI'
    ],
    '副業': [
        '副業', 'フリーランス', 'YouTube', 'ブログ', 'アフィリエイト',
        'クラウドワークス', 'ランサーズ', 'せどり', 'ショート動画'
    ],
    '自動化ツール': [
        'Zapier', 'Make', 'n8n', 'Automator', 'GAS', 'Python',
        '自動化', 'ワークフロー', 'API'
    ],
    'ガジェット': [
        'iPhone', 'iPad', 'MacBook', 'AirPods', 'Apple', 'Google',
        'Samsung', 'イヤホン', 'キーボード', 'バッテリー', 'ディスプレイ'
    ],
    '生活改善': [
        '睡眠', '瞑想', '運動', '健康', '栄養', 'フィットネス',
        '心理学', 'メンタル', 'ストレス', '集中力'
    ]
}


def fetch_news_headlines() -> List[str]:
    """
    複数の RSS フィードからニュースを取得

    Returns:
        ニュースタイトルのリスト
    """

    headlines = []

    print("ニュースフィードから記事を取得中...\n")

    for feed_name, feed_url in NEWS_FEEDS:
        try:
            print("  {}: 取得中...".format(feed_name), end=" ")

            feed = feedparser.parse(feed_url)

            if feed.bozo:
                print("WARN: パース警告")
                continue

            # 最新 10 件の記事
            for entry in feed.entries[:10]:
                title = entry.get('title', '')
                if title:
                    headlines.append(title)

            print("OK ({} 件)".format(len(feed.entries[:10])))

        except Exception as e:
            print("NG ({})".format(type(e).__name__))

    print("\n合計: {} 件の記事取得".format(len(headlines)))
    return headlines


def extract_keywords_from_text(text: str) -> List[str]:
    """
    テキストからキーワード候補を抽出（単語単位）

    Args:
        text: テキスト

    Returns:
        キーワード一覧
    """

    # 日本語・英数字の単語を抽出
    words = re.findall(r'\b[ぁ-んァ-ヴー一-龠a-zA-Z0-9]+\b', text)

    # 3文字以上のみ
    return [w for w in words if len(w) >= 3]


def detect_trending_keywords(headlines: List[str]) -> List[Dict]:
    """
    ニュースの記事タイトルから トレンドキーワードを検出

    Args:
        headlines: ニュースタイトル一覧

    Returns:
        トレンドキーワード（頻出度でソート）
    """

    print("\nキーワード抽出中...\n")

    # 全記事からキーワードを抽出
    all_keywords = []

    for headline in headlines:
        keywords = extract_keywords_from_text(headline)
        all_keywords.extend(keywords)

    # 出現回数をカウント
    keyword_counts = Counter(all_keywords)

    print("  抽出キーワード: {}個".format(len(keyword_counts)))

    # 出現回数が多い順でソート
    trending_keywords = []

    for keyword, count in keyword_counts.most_common(50):
        # 既知のキーワードパターンにマッチするか確認
        category = None
        for cat, patterns in KEYWORD_PATTERNS.items():
            if any(pattern.lower() in keyword.lower() for pattern in patterns):
                category = cat
                break

        if category:  # カテゴリマッチしたもののみ追加
            trending_keywords.append({
                'keyword': keyword,
                'category': category,
                'frequency': count,
                'score': count * 10,  # スコア化
                'reason': 'ニュースフィードで{}回出現'.format(count)
            })

    # スコアでソート
    trending_keywords.sort(key=lambda x: x['score'], reverse=True)

    print("  トレンドキーワード: {}個".format(len(trending_keywords)))

    return trending_keywords


def save_to_json(keywords: List[Dict], update_existing: bool = False) -> None:
    """
    キーワードを JSON ファイルに保存

    Args:
        keywords: キーワード一覧
        update_existing: 既存ファイルにマージするか
    """

    json_file = Path("scripts/trending_keywords.json")

    if update_existing and json_file.exists():
        data = json.loads(json_file.read_text(encoding='utf-8'))

        # 既存キーワードと新しいキーワードをマージ
        existing_keywords = [kw['keyword'] for kw in data.get('keywords', [])]

        for kw in keywords:
            if kw['keyword'] not in existing_keywords:
                data['keywords'].append(kw)

        # スコアでソート
        data['keywords'].sort(key=lambda x: x.get('score', 0), reverse=True)
    else:
        data = {
            'description': 'ニュースフィードから自動抽出したトレンドキーワード',
            'last_updated': datetime.now().isoformat(),
            'update_method': 'auto_news_extraction',
            'keywords': keywords
        }

    json_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    print("\nOK: ファイルに保存 {}".format(json_file))


def main():
    import argparse

    parser = argparse.ArgumentParser(description="ニュースフィードからトレンドキーワード抽出")
    parser.add_argument('--update', action='store_true', help='既存ファイルにマージ')

    args = parser.parse_args()

    print("=" * 70)
    print("自動トレンドキーワード抽出（Python RSS フィード版）")
    print("=" * 70 + "\n")

    # ステップ1: ニュース取得
    headlines = fetch_news_headlines()

    if not headlines:
        print("\nERROR: ニュース取得失敗")
        return

    # ステップ2: キーワード抽出
    keywords = detect_trending_keywords(headlines)

    if not keywords:
        print("\nERROR: キーワード抽出失敗")
        return

    # ステップ3: 結果表示
    print("\n" + "=" * 70)
    print("検出されたトレンドキーワード（TOP 10）")
    print("=" * 70)

    for i, kw in enumerate(keywords[:10], 1):
        print("{}: {} [{}] (スコア: {})".format(
            i,
            kw['keyword'],
            kw['category'],
            kw['score']
        ))

    # ステップ4: ファイル保存
    print()
    save_to_json(keywords[:30], update_existing=args.update)  # トップ 30 個を保存

    print("=" * 70)


if __name__ == "__main__":
    main()
