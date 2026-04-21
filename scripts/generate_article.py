"""
アフィリエイト記事自動生成スクリプト
使い方:
  python scripts/generate_article.py              # ランダム記事
  python scripts/generate_article.py --topic "Claude Codeソースコード流出"
  python scripts/generate_article.py --news       # RSSから最新ニュース取得して生成
  python scripts/generate_article.py --csv --csv-count 3  # CSVキーワードから3記事生成
  python scripts/generate_article.py --keyword-stats      # キーワード統計表示
  python scripts/generate_article.py --reset-keywords     # キーワードをリセット
"""

import anthropic
import argparse
import json
import os
import random
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from keyword_manager import (
    select_unused_keyword,
    mark_keyword_as_used,
    print_keyword_stats,
    reset_all_keywords,
)

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# APIキーの改行文字を除去（GitHub Secrets貼り付け時の混入対策）
if "ANTHROPIC_API_KEY" in os.environ:
    os.environ["ANTHROPIC_API_KEY"] = os.environ["ANTHROPIC_API_KEY"].strip()

# ジャンル別キーワードプール（現在は未使用 - CSVキーワード優先）
"""
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
    "ペット": [
        ("犬 飼い方 初心者 完全ガイド", ["犬", "ペット", "初心者", "飼育"]),
        ("猫 飼い方 初心者 準備 必要なもの", ["猫", "ペット", "初心者", "飼育"]),
        ("ハムスター 飼い方 初心者 ケージ選び", ["ハムスター", "ペット", "小動物", "飼育"]),
        ("うさぎ 飼い方 初心者 食べ物 注意点", ["うさぎ", "ペット", "小動物", "飼育"]),
        ("インコ 飼い方 初心者 しつけ 方法", ["インコ", "ペット", "鳥類", "飼育"]),
        ("ペット 初心者 おすすめ 費用 選び方", ["ペット", "初心者", "飼育", "選択"]),
    ],
}
"""

# ニュース取得先RSSフィード（日本語テック系）
NEWS_FEEDS = [
    ("Gigazine", "https://gigazine.net/news/rss_2.0/"),
    ("ITmedia AI+", "https://rss.itmedia.co.jp/rss/2.0/aiplus.xml"),
    ("Google News AI", "https://news.google.com/rss/search?q=AI%20%E4%BA%BA%E5%B7%A5%E7%9F%A5%E8%83%BD&hl=ja&gl=JP&ceid=JP:ja"),
    ("Google News 副業", "https://news.google.com/rss/search?q=%E5%89%AF%E6%A5%AD%20%E3%83%95%E3%83%AA%E3%83%BC%E3%83%A9%E3%83%B3%E3%82%B9&hl=ja&gl=JP&ceid=JP:ja"),
]

SYSTEM_PROMPT = """あなたはSEO最適化された、詳細で実用的なブログ記事を書く編集者です。人間らしい自然な日本語で、専門家による解説のような文体を目指します。

# ■超重要：文字数指定（絶対厳守）【必ず3000字以上・句点120個以上】
【最小文字数】 絶対に3000文字以上。2500字では失敗。足りなければセクション追加
【推奨範囲】 3500～5000文字（4000字超が基準）
【句点の数】 【絶対に100個以上必須】120個が目安。毎段落で確実に句点を入れる
【計算方法】 各文末に「。」をつける。短い文を複数つなげない。1文＝1句点
【チェック】 各見出し下に10～15文を書く。短い段落は避ける。段落は3～5文で構成

# ■キーワード埋め込み（必須）
【キーワード】 記事タイトルに含まれるメインキーワードを本文に「最低8回」含める
【関連KW】 類似キーワード・言い換え表現も10回以上含める
【計算】 すべてのキーワード出現を数えてから出力

# ■記事構成（プロフェッショナル版・必須）
1. # タイトル
2. 導入段落（読者の悩みを1～2文で。50～100字。具体的な問題提起）
3. ## 見出し1（基本知識。600～700字。背景と重要性を説明）
4. ## 見出し2（重要なポイント・メリット。700～900字。表を含む）【表必須】
5. ## 見出し3（比較・選び方。700～900字。複数の表推奨）
6. ## 見出し4（詳細な使い方・実践例。600～800字。具体的なステップ）
7. ## 見出し5（さらに詳しい情報。400～500字。応用例や追加知識）
8. ## 見出し6（よくある質問・FAQ。300～400字。Q&A形式）
9. ## 見出し7（実行ステップ・次のアクション。300～400字）
10. ## まとめ
   その後、見出しなしで250～350字の本文テキスト。主要ポイント復習と実行への促し。
   【重要】本文は通常の段落テキスト。別の ## 見出しを作らない。

【まとめセクションの出力形式（絶対厳守）】
[ERROR] 間違い：
## まとめ

## 初心者向けの～～は...

✅ 正しい：
## まとめ

初心者向けの～～は...

合計：3000字以上（4000字超が目安）

【絶対厳守】## まとめ の後は何も生成しない
・まとめの本文テキストは通常の段落テキスト（# や ## の見出しではなく、通常の文章）
・見出しなしのテキストのみ。改行後に ## が出現することは絶対に禁止
・絶対に ## を使って本文を囲まない
・「## サイト内の人気記事」などの追加見出しを作らない
・まとめの次は即座に記事を終了する
・出力の最後の見出しは必ず「## まとめ」で終わる。その後は本文テキストのみ
・「## 補足」「## 追加情報」「## 関連リンク」など、いかなる見出しも禁止

# ■見出しの生成ルール（重要）
【見出しの長さ】
・見出しテキストは最大15字程度。長い説明は本文に。
・見出しに説明口調・長文は禁止。簡潔に。
・見出しが長くなったら、分割するか短縮する。

【記事終了ルール】※CRITICAL※
・「## まとめ」の後に、追加の見出しは絶対に一切生成しない
・まとめの後は本文テキストのみ。その後は即座に記事を終了
・「## 関連記事」「## 補足」「## 追加情報」「## さらに詳しく」などの余分な見出しを作らない
・出力の最終行はまとめセクションの本文で終わる。## で始まる行は出力しない
・** データの自動追加（関連記事など）は別途スクリプトで処理される。生成時に追加しない

# ■表の生成（複数表必須・自然に配置）
・記事に「Markdown 表」を最低2～3個含める
・比較表（機能・料金・特徴の比較）
・一覧表（メリット・デメリット・ポイント）
・手順表（ステップバイステップ・説明）
・表の説明文を必ず入れる（表の直前か直後）

# ■AIっぽさを完全に排除（最重要）
【絶対に使わない表現】
・「いかがでしたか」「ぜひご覧ください」
・「～と思います」「～といえます」「～わかります」
・「重要です」「大切です」「便利です」（一般的な感想）
・「このように」「その結果」「このため」（つなぎ表現が多い）
・「注目されています」「話題になっています」「人気があります」
・「こちら」（カジュアル）
・「ご紹介します」「参考にしてください」
・「できます」「できるようになります」「実現できます」
・「考えられます」「言えるでしょう」（曖昧）
・「もう一度」「さらに詳しく」「念のため」
・「～のです」（説明的すぎる）
・「～より」（比較時は「～の方が」を使う）

【改善例1】
[ERROR] AIっぽい：「このツールは非常に便利であり、多くの人に活用されています。できるだけ早く始めることをお勧めします」
✅ 人間らしい：「このツールは45分の作業を15分に短縮できます。月額300円で利用できます」

【改善例2】
[ERROR] AIっぽい：「この方法により、以下のようなメリットが得られます」
✅ 人間らしい：「この方法で得られること：」

【改善例3】
[ERROR] AIっぽい：「～と考えられます」「～であると言えます」
✅ 人間らしい：「～です」「～の理由は～」

【改善例4 - まとめセクション】
[ERROR] 絶対に禁止：## まとめ の直後に別の ## 見出しを作る
## まとめ
## 初心者向けの効果的な英語勉強方法は...（この## は禁止）

✅ 正しい形式：## まとめ の直後は通常のテキスト（見出しなし）
## まとめ
初心者向けの効果的な英語勉強方法は...(通常の段落テキスト)

【文体ルール】
・1文は15～25字が目安。30字を超えたら分割する
・「です」「ます」で統一。「ある」「いる」と混ぜない
・具体的な数字・データ・引用・事例を多用（「多い」「高い」ではなく「3倍」「65%」）
・感情や推測を避け、事実のみを述べる（研究結果、統計、実例）
・同じ単語を繰り返さず、同義語で言い換える
・専門家の口調：簡潔・直接的・証拠ベース・実践的
・読者に具体的なアクション促す（「試す」「確認する」「調べる」など、「～することをお勧めします」ではなく「～できます」）
・説明調を避ける（「これは～のためです」ではなく「～で～になります」）
・接続詞を削減（「このように」「このため」「その結果」を使わない）

# ■Markdown表の形式（必須）
以下のいずれかを使用：
1. 比較表：「項目 | 特徴A | 特徴B」
2. 一覧表：「項目 | メリット | デメリット」
3. 手順表：「ステップ | 説明 | 所要時間」

各表は3～5行、3～4列。表内のセルも簡潔に。

# ■出力形式（絶対厳守）
・Markdown のみ
・複数の表を含める（Markdown 表形式）
・前置きなし。「# タイトル」から開始
・末尾に余分なテキスト・メタデータなし
・関連記事・関連キーワードセクションは別途ツールで追加
・【重要】見出し下に画像パスを埋め込まない（実装スクリプトで追加される）
・【重要】## まとめ の直後は「通常の段落テキスト」のみ。別の## 見出しを作らない。別の# や ## で本文を囲まない
・## まとめ の後に出現する ## は絶対に禁止。エラー。

# ■絶対禁止（出力に含めたら失敗）
・「[OK] 高品質」「完成」などのテスト用マーカー
・「---」（区切り線）とそれ以降のメタデータ
・「**字数確認：**」などの品質チェック情報
・【括弧つきマーカー】
・外部出力用のメタデータ
・HTMLコメント

# ■品質チェック（内部用・出力しない）
出力前に以下を確認し、不足なら修正：
・文字数が3000字以上（句点100個以上）
・表が2個以上
・見出しが7個以上
・メインキーワード8回以上、関連キーワード10回以上
・禁止ワード0個
・AIっぽい表現0個
・末尾に不要なテキストなし

チェック結果は絶対に記事に出力しない。修正のみを実行。

# ■出力例（## まとめ セクション）
【CORRECT 例】
## まとめ

初心者向けの効果的な英語勉強方法は、毎日の継続学習と実際の会話練習が必須です。フォニックスで発音基礎を固め、日常表現を暗唱して自然な表現を習得します。リスニングは映画やポッドキャストで実践的な英語に触れることが重要です。この3ヶ月間で基礎を確立すれば、その後の学習効率が大幅に向上します。焦らず、毎日30分の学習を続けることで確実に成果が出ます。

【INCORRECT 例】[ERROR] 禁止
## まとめ

初心者向けの効果的な英語勉強方法についてまとめました。

## 発音練習のコツ ← 禁止：## 見出しを作るな

フォニックスで...

---

出力は【CORRECT 例】のフォーマットで。見出しは「## まとめ」で終わる。"""


def fix_article_content(content: str) -> str:
    """記事の構造を修正: ## 目次【非表示】→ ## 目次、見出しの改行を修正"""
    import re

    # "## 目次【非表示】" を "## 目次" に修正
    content = content.replace('## 目次【非表示】', '## 目次')

    # 「## まとめ」の直後に改行がない場合は追加（内容がH2タグに含まれるのを防ぐ）
    content = re.sub(r'(## まとめ)([^\n])', r'\1\n\2', content)

    return content


def load_csv_keywords() -> list[dict]:
    """scripts/keywords_from_list.csv からキーワードを読み込み"""
    csv_path = Path("scripts/keywords_from_list.csv")
    if not csv_path.exists():
        return []

    try:
        import csv
        keywords = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['status'] == 'unused':
                    # keyword の形式: """キーワード1,キーワード2,キーワード3"""
                    # ダブルクォートを削除してキーワードリストに変換
                    keyword_str = row['keyword'].strip()
                    # 先頭と末尾のダブルクォート（""" または "）を削除
                    if keyword_str.startswith('"""') and keyword_str.endswith('"""'):
                        keyword_str = keyword_str[3:-3]
                    elif keyword_str.startswith('"') and keyword_str.endswith('"'):
                        keyword_str = keyword_str[1:-1]

                    # カンマで分割してキーワード配列に変換
                    parts = [kw.strip() for kw in keyword_str.split(',')]

                    keywords.append({
                        'keyword': keyword_str,  # 元の形式
                        'parts': parts,          # 分割後のリスト
                        'status': row['status']
                    })
        return keywords
    except Exception as e:
        print(f"CSVキーワード読み込み失敗: {e}")
        return []


def mark_csv_keyword_as_used(keyword: str):
    """CSVでキーワードをusedに更新"""
    csv_path = Path("scripts/keywords_from_list.csv")
    if not csv_path.exists():
        return

    try:
        import csv
        rows = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['keyword'] == keyword:
                    row['status'] = 'used'
                rows.append(row)

        # 更新内容を書き込み
        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['keyword', 'status'])
            writer.writeheader()
            writer.writerows(rows)
        print(f"✅ キーワードをusedに更新: {keyword}")
    except Exception as e:
        print(f"CSVキーワード更新失敗: {e}")


def infer_genre_from_keyword(keyword_first_word: str) -> str:
    """キーワードの最初の単語からジャンルを推測"""
    # ジャンル判定マッピング（新ジャンル対応版）
    genre_keywords = {
        "動物": ["犬", "猫", "ハムスター", "うさぎ", "インコ", "熱帯魚", "爬虫類", "メダカ", "金魚"],
        "植物": ["観葉植物", "多肉植物", "ガーデニング", "花", "エアプランツ", "アイビー", "モンステラ",
                "パキラ", "ユーカリ", "ポトス"],
        "食べ物": ["料理", "レシピ", "食材", "デザート", "お菓子", "パン", "麺"],
        "副業": ["副業", "フリーランス", "転職", "起業", "プログラミング", "Python", "JavaScript",
                "クラウドソーシング", "ブログ", "アフィリエイト", "動画編集"],
        "生活改善": ["ダイエット", "ヨガ", "プロテイン", "サプリメント", "睡眠", "免疫力",
                    "コレステロール", "頭痛", "めまい", "スキンケア", "クレンジング", "洗顔",
                    "化粧水", "美容液", "乳液", "日焼け止め", "ファンデーション", "アイシャドウ",
                    "リップ", "チーク", "マスカラ", "アイライナー", "シャンプー", "コンディショナー",
                    "ソファ", "ベッド", "英語学習", "時間管理", "集中力"],
        "ガジェット": ["照明", "スマートフォン", "iPhone", "ノートパソコン", "ヘッドフォン",
                      "スピーカー", "Tシャツ", "パーカー", "スニーカー", "靴", "バッグ",
                      "モニター", "キーボード", "マウス"],
    }

    for genre, keywords in genre_keywords.items():
        if keyword_first_word in keywords:
            return genre

    return "副業"  # デフォルト


def select_keyword():
    """キーワード選択（CSVを優先、なければKEYWORD_POOLSから選択）"""
    # CSVから未使用キーワードを取得
    csv_keywords = load_csv_keywords()
    if csv_keywords:
        selected = random.choice(csv_keywords)
        keyword = selected['keyword']
        # キーワードを分割（例："ダイエット,食事制限,やり方" → "ダイエット 食事制限 やり方"）
        parts = keyword.split(',')
        main_kw = ' '.join(parts)  # 複合キーワード
        related_kws = parts

        # ジャンルを推測（最初の単語から）
        genre = infer_genre_from_keyword(parts[0])

        # 使用済みに更新
        mark_csv_keyword_as_used(keyword)
        return genre, main_kw, related_kws

    # CSVにない場合は従来の方法
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

    article_content = message.content[0].text

    # 記事構造の修正
    article_content = fix_article_content(article_content)

    # AIっぽい表現をチェック
    _, ai_issues = check_and_remove_ai_expressions(article_content)
    if ai_issues:
        print("[WARNING] AIっぽい表現が検出されました:")
        for issue in ai_issues:
            print(f"  {issue}")

    return article_content


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

    article_content = message.content[0].text
    # 記事構造の修正
    article_content = fix_article_content(article_content)
    return article_content


def check_and_remove_ai_expressions(content: str) -> tuple[str, list[str]]:
    """
    AIっぽい表現を検出して報告し、簡単な修正案を提示
    戻り値: (修正内容, [問題リスト])
    """
    ai_patterns = [
        (r'いかがでしたか', 'いかがでしたか'),
        (r'ぜひご覧ください', 'ぜひご覧ください'),
        (r'と思います', 'と思います'),
        (r'といえます', 'といえます'),
        (r'重要です', '重要です'),
        (r'大切です', '大切です'),
        (r'このように', 'このように'),
        (r'その結果', 'その結果'),
        (r'注目されています', '注目されています'),
        (r'話題になっています', '話題になっています'),
        (r'できるようになります', 'できるようになります'),
        (r'考えられます', '考えられます'),
        (r'言えるでしょう', '言えるでしょう'),
        (r'わかります', 'わかります'),
        (r'もう一度', 'もう一度'),
        (r'さらに詳しく', 'さらに詳しく'),
        (r'のです', 'のです'),
    ]

    issues = []
    for pattern, phrase in ai_patterns:
        if re.search(pattern, content):
            issues.append(f"[WARNING] 禁止フレーズ: '{phrase}' が見つかりました")

    return content, issues


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
    "動物": "animal,pet,cute,dog,cat",
    "植物": "plant,garden,green,nature,leaf",
    "食べ物": "food,cooking,recipe,delicious,kitchen",
    "ニュース": "technology,news,digital",
}


def init_gemini_api():
    """Gemini APIを初期化"""
    if not GEMINI_AVAILABLE:
        print("[WARNING] google-generativeai がインストールされていません")
        print("  インストール: pip install google-generativeai")
        return False

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("[WARNING] GOOGLE_API_KEY が設定されていません")
        print("  .env.local に GOOGLE_API_KEY=... を追加してください")
        return False

    try:
        genai.configure(api_key=api_key)
        return True
    except Exception as e:
        print(f"[ERROR] Gemini API初期化失敗: {e}")
        return False


def generate_image_with_gemini(prompt: str, width: int = 800, height: int = 400) -> bytes | None:
    """Gemini APIで画像を生成"""
    if not GEMINI_AVAILABLE:
        return None

    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        image_prompt = f"{prompt} (aspect ratio 16:9, professional quality, clean background)"

        response = model.generate_images(
            prompt=image_prompt,
            number_of_images=1,
            safety_settings=[
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_ONLY_HIGH",
                },
            ]
        )

        if response.images:
            return response.images[0]._image_bytes
        return None
    except Exception as e:
        print(f"[WARNING] Gemini画像生成失敗: {e}")
        return None


def generate_hero_image(title: str, genre: str, slug: str) -> str | None:
    """ヒーロー画像取得（Gemini → Pollinations → loremflickr → picsum.photos）"""
    import urllib.parse as up
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
            if len(data) < 1000:
                return False
            img_path.write_bytes(data)
            return True
        except Exception:
            return False

    # 1. Gemini API（高品質AI生成）
    if GEMINI_AVAILABLE:
        try:
            img_data = generate_image_with_gemini(prompt, 800, 400)
            if img_data:
                img_path.write_bytes(img_data)
                print(f"[OK] Hero image created (Gemini): {img_path}")
                return f"/images/blog/{slug}.jpg"
        except Exception as e:
            print(f"  Gemini generation failed: {type(e).__name__}")

    # 2. Pollinations.ai（フォールバック）
    pollinations_url = f"https://image.pollinations.ai/prompt/{up.quote(prompt)}?width=800&height=400&nologo=true&seed={seed}"
    try:
        req = urllib.request.Request(pollinations_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = resp.read()
        if len(data) >= 1000:
            img_path.write_bytes(data)
            print(f"[OK] Hero image created (Pollinations): {img_path}")
            return f"/images/blog/{slug}.jpg"
    except urllib.error.HTTPError as e:
        print(f"  Pollinations {e.code}: fallback to next service")
    except Exception as e:
        print(f"  Pollinations failed: {type(e).__name__}")

    # 3. loremflickr（キーワード検索）
    for kw_try in [kw, kw.split(",")[0]]:
        url = f"https://loremflickr.com/800/400/{kw_try}?lock={seed}"
        if fetch(url):
            print(f"[OK] Hero image created (loremflickr/{kw_try}): {img_path}")
            return f"/images/blog/{slug}.jpg"

    # 4. picsum.photos（確実な取得）
    url = f"https://picsum.photos/seed/{seed}/800/400"
    if fetch(url):
        print(f"[OK] Hero image created (picsum): {img_path}")
        return f"/images/blog/{slug}.jpg"
    print(f"[WARNING] Hero image generation failed: {slug}")
    return None


def embed_images_in_article(content: str, genre: str, slug: str) -> str:
    """記事の各H2見出しの後に画像を埋め込む（Gemini → Pollinations.ai）"""
    import urllib.parse as up

    # ## で始まる見出しを抽出（最大2～3個）
    headings = re.findall(r'^## (.+)$', content, re.MULTILINE)[1:4]  # 最初のH2は除外（タイトル直後）

    if not headings:
        return content

    img_dir = Path("public/images/blog")
    img_dir.mkdir(parents=True, exist_ok=True)

    images_to_embed = {}

    for i, heading in enumerate(headings):
        img_num = i + 1
        img_filename = f"{slug}-section{img_num}.jpg"
        img_path = img_dir / img_filename

        seed = abs(hash(f"{slug}-{heading}")) % 9999
        prompt = f"article illustration, {genre}, {heading[:50]}, 16:9, professional"
        kw = GENRE_KEYWORDS.get(genre, "technology,business")

        success = False

        # 1. Gemini APIで生成
        if GEMINI_AVAILABLE:
            try:
                img_data = generate_image_with_gemini(prompt, 800, 400)
                if img_data:
                    img_path.write_bytes(img_data)
                    images_to_embed[heading] = f"/images/blog/{img_filename}"
                    print(f"  [OK] Section image({i+1}) (Gemini): {img_filename}")
                    success = True
            except Exception as e:
                pass  # Fallback へ

        # 2. Gemini失敗時は Pollinations.ai で取得
        if not success:
            try:
                pollinations_url = f"https://image.pollinations.ai/prompt/{up.quote(prompt)}?width=800&height=400&nologo=true&seed={seed}"
                req = urllib.request.Request(pollinations_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=90) as resp:
                    data = resp.read()
                if len(data) >= 1000:
                    img_path.write_bytes(data)
                    images_to_embed[heading] = f"/images/blog/{img_filename}"
                    print(f"  [OK] Section image({i+1}) (Pollinations): {img_filename}")
                    success = True
            except Exception as e:
                print(f"  [FAIL] Section image({heading}): {type(e).__name__}")

    # H2見出し直後に画像を埋め込む
    if images_to_embed:
        for heading, img_url in images_to_embed.items():
            pattern = f"(^## {re.escape(heading)}$)"
            replacement = f"\\1\n\n![{heading}]({img_url})"
            content = re.sub(pattern, replacement, content, count=1, flags=re.MULTILINE)

    return content


def generate_table_of_contents(content: str) -> str:
    """
    # タイトル と ## 見出し から目次を生成
    3500字相当（句点120個以上）の記事のみ目次を挿入
    見出しにアンカーIDを付与
    """
    # 見出しを抽出
    h2_pattern = r'^## (.+?)$'
    headings_matches = list(re.finditer(h2_pattern, content, re.MULTILINE))

    # 文字数をカウント（句点の数）
    period_count = content.count('。')

    # 句点120個以上の場合のみ目次を生成
    if period_count < 120 or len(headings_matches) < 7:
        return content

    # 見出しにアンカーIDを付与
    modified_content = content
    offset = 0
    for i, match in enumerate(headings_matches, 1):
        heading_text = match.group(1).strip()
        # HTMLアンカータグを見出しの後に挿入
        anchor_html = f'\n<span id="heading-{i}"></span>'
        insert_pos = match.end() + offset
        modified_content = modified_content[:insert_pos] + anchor_html + modified_content[insert_pos:]
        offset += len(anchor_html)

    # 目次を生成
    toc_lines = ["## 目次【非表示】"]
    toc_lines.append("")
    for i, match in enumerate(headings_matches, 1):
        heading_text = match.group(1).strip()
        toc_lines.append(f"{i}. [{heading_text}](#heading-{i})")

    # 本文の最初の導入段落の後に目次を挿入
    # H1タイトルの直後、最初の見出しの前に挿入
    insert_position = modified_content.find('\n## ')
    if insert_position > 0:
        toc_text = '\n\n' + '\n'.join(toc_lines) + '\n\n'
        modified_content = modified_content[:insert_position] + toc_text + modified_content[insert_position:]

    return modified_content


def generate_related_articles(genre: str, main_kw: str) -> str:
    """関連記事セクションを生成"""
    # 同じジャンルの記事を探す
    blog_path = Path("src/content/blog")
    try:
        article_files = sorted(list(blog_path.glob("*.md")), reverse=True)[:20]  # 最新20件

        # ジャンル一致記事を抽出
        related = []
        for article_file in article_files:
            content = article_file.read_text(encoding='utf-8')
            if f"genre: '{genre}'" in content or f'genre: "{genre}"' in content:
                # タイトルを抽出
                title_match = re.search(r"title: ['\"](.+?)['\"]", content)
                if title_match and title_match.group(1) != main_kw:
                    slug = article_file.stem
                    related.append((title_match.group(1), slug))

        related = related[:3]  # 最大3件
    except:
        related = []

    if not related:
        return ""

    lines = ["\n---\n", "## 関連記事\n"]
    for title, slug in related:
        lines.append(f"- [{title}](/blog/{slug}/)")

    return '\n'.join(lines)


def generate_popular_articles() -> str:
    """人気記事セクションを生成"""
    blog_path = Path("src/content/blog")
    try:
        # すべての記事を取得（最新順）
        all_articles = sorted(list(blog_path.glob("*.md")), reverse=True)[:10]

        # 最新記事のうちランダムに3つを選択
        import random
        selected = random.sample(all_articles, min(3, len(all_articles)))

        popular = []
        for article_file in selected:
            content = article_file.read_text(encoding='utf-8')
            title_match = re.search(r"title: ['\"](.+?)['\"]", content)
            if title_match:
                slug = article_file.stem
                popular.append((title_match.group(1), slug))
    except:
        popular = []

    if not popular:
        return ""

    lines = ["\n---\n", "## サイト内の人気記事\n"]
    for title, slug in popular:
        lines.append(f"- [{title}](/blog/{slug}/)")

    return '\n'.join(lines)


def generate_related_keywords(main_kw: str, related_kws: list = None) -> str:
    """関連キーワードセクションを生成"""
    if not related_kws:
        return ""

    # メインキーワードと関連キーワードを組み合わせ
    all_keywords = [main_kw] + (related_kws[:8] if related_kws else [])

    # 重複削除
    all_keywords = list(dict.fromkeys(all_keywords))[:10]

    lines = ["\n---\n", "## 関連キーワード\n"]
    for kw in all_keywords:
        lines.append(f"- {kw}")

    return '\n'.join(lines)


def save_article(content: str, genre: str, main_kw: str, category: str = None, source: str = None, related_kws: list = None) -> Path:
    """記事をMarkdownファイルとして保存"""
    title = extract_title(content)
    today = datetime.now().strftime("%Y-%m-%d")
    slug = f"{today}-{slugify(main_kw)}"

    # スラッグ重複チェック：同じスラッグが既に存在する場合、ユニークIDを追加
    blog_dir = Path("src/content/blog")
    if (blog_dir / f"{slug}.md").exists():
        import string
        unique_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        slug = f"{today}-{slugify(main_kw)}-{unique_id}"
        print(f"  ℹ️ スラッグ重複回避: {unique_id} を追加")

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

    # 不要な末尾テキストを削除（複数パターン）
    # まとめセクション内のテキストは保持し、その後の --- 以降のみ削除
    # 「## まとめ」セクションのテキストがない場合（空行のみ）でも、段落を生成する前提で処理
    # まとめセクションが存在する場合、その内容を保持してから ---以降を削除
    article_body = re.sub(r'(## まとめ\n(?:.*?\n)*?)\n*---[\s\S]*$', r'\1', article_body, flags=re.MULTILINE)
    # またはシンプルに：最後の --- 区切り線 以降をすべて削除（品質チェック情報用）
    if '\n---\n' in article_body:
        parts = article_body.rsplit('\n---\n', 1)
        article_body = parts[0]
    # 完成マーカー
    article_body = re.sub(r'\n+完成\s*$', '', article_body)
    # [OK]高品質マーカー（すべてのバリエーション）
    article_body = re.sub(r'\n+\*?\*?[OK]\*?\*?\s*高品質\*?\*?\s*$', '', article_body)
    article_body = re.sub(r'\n+[OK].*?高品質.*?$', '', article_body, flags=re.MULTILINE)
    # その他のチェックマーク
    article_body = re.sub(r'\n+\*?\*?[[OK]✔]\*?\*?.*?$', '', article_body, flags=re.MULTILINE)
    # 括弧で囲まれたマーカー
    article_body = re.sub(r'\n+【.*?】\s*$', '', article_body, flags=re.MULTILINE)
    # **字数確認：など品質チェック行
    article_body = re.sub(r'\n+\*\*[字数キーワード表見出高].*?\*\*.*?$', '', article_body, flags=re.MULTILINE)
    # 末尾の余分な改行
    article_body = re.sub(r'\n\n+$', '\n', article_body)

    # 本文にセクション画像を埋め込む（Gemini API対応）
    try:
        print("  セクション画像を生成中...")
        article_body = embed_images_in_article(article_body, genre, slug)
    except Exception as e:
        print(f"  [WARNING] セクション画像埋め込み失敗: {e}")

    # 目次を生成（3500字以上の記事のみ）
    article_body = generate_table_of_contents(article_body)

    # 記事構造の最終修正（目次の【非表示】テキストを削除）
    article_body = fix_article_content(article_body)

    # 記事本文のみを保存（関連記事・人気記事はレイアウト側で追加）
    # keywords_section は削除（ユーザー要望）

    # フルコンテンツを組み立て（記事本文のみ）
    full_content = frontmatter + article_body

    output_path = Path("src/content/blog") / f"{slug}.md"
    output_path.write_text(full_content, encoding="utf-8")

    return output_path


def load_evergreen_keywords(count: int = 1) -> list[tuple[str, str, list[str]]]:
    """
    evergreen_keywords.json から優先度付きでキーワードを取得
    戻り値: [(keyword, category, related_kws), ...]
    """
    evergreen_path = Path("scripts/evergreen_keywords.json")

    if not evergreen_path.exists():
        return []

    try:
        data = json.loads(evergreen_path.read_text(encoding='utf-8'))

        candidates = []

        # すべてのカテゴリからキーワードを収集
        for category, items in data.items():
            if not isinstance(items, list):
                continue

            for item in items:
                if item.get('keyword'):
                    candidates.append({
                        'keyword': item.get('keyword'),
                        'category': category,
                        'related_kws': item.get('related_kws', []) if isinstance(item.get('related_kws'), list) else [],
                        'priority': item.get('priority', 50)
                    })

        # 優先度でソート（降順）
        candidates.sort(key=lambda x: x['priority'], reverse=True)

        # 上位 count 個を返す
        result = []
        for i, c in enumerate(candidates[:count]):
            result.append((c['keyword'], c['category'], c['related_kws']))

        return result

    except Exception as e:
        print(f"WARNING: evergreen_keywords.json 読み込み失敗: {e}")
        return []


def load_keywords_from_pool(count: int = 1, blend_evergreen: bool = True) -> list[tuple[str, str, list[str]]]:
    """
    keywords_pool.json と evergreen_keywords.json をブレンドしてキーワードを取得
    优先顺：新ジャンル > 高スコアキーワード
    blend_evergreen=True の場合、約50%をトレンディング、50%をエバーグリーンから取得
    戻り値: [(keyword, category, related_kws), ...]
    """
    keywords_pool_path = Path("scripts/keywords_pool.json")

    # トレンディングキーワードを取得
    trending_keywords = []
    if keywords_pool_path.exists():
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

            # 取得する数：count の 50% + 10% 余裕
            trending_count = max(int(count * 0.55), 1)
            for i, c in enumerate(candidates[:trending_count]):
                trending_keywords.append((c['keyword'], c['category'], c['related_kws']))

        except Exception as e:
            print(f"WARNING: keywords_pool.json 読み込み失敗: {e}")

    # エバーグリーンキーワードを取得
    evergreen_keywords = []
    if blend_evergreen:
        evergreen_count = max(count - len(trending_keywords), 1)
        evergreen_keywords = load_evergreen_keywords(count=evergreen_count + 5)  # 余裕を持たせ取得

    # 合算してランダムに返す
    all_keywords = trending_keywords + evergreen_keywords
    if not all_keywords:
        # フォールバック：既存の KEYWORD_POOLS から選択
        print("WARNING: キーワードプールが見つかりません。既存キーワードプールから選択します")
        result = []
        for i in range(count):
            genre, main_kw, related_kws = select_keyword()
            result.append((main_kw, genre, related_kws))
        return result

    # ランダムに順序を混ぜて返す（トレンディングとエバーグリーンを混在させる）
    random.shuffle(all_keywords)
    return all_keywords[:count]


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


def check_duplicate_article(keyword: str) -> bool:
    """既存記事との重複をチェック（スラッグ重複・キーワード完全一致のみ）"""
    blog_dir = Path("src/content/blog")

    # 1. スラッグの完全一致チェック（最も厳密）
    slug = f"*-{slugify(keyword)}.md"
    existing_slug_files = list(blog_dir.glob(slug))
    if existing_slug_files:
        print(f"  [WARNING] 重複検出（スラッグ一致）: {', '.join(f.name for f in existing_slug_files)}")
        return True

    # キーワードから主要な単語を抽出（3文字以上）
    main_words = [w for w in keyword.split() if len(w) >= 3]
    if not main_words:
        return False

    for article_file in blog_dir.glob("*.md"):
        try:
            content = article_file.read_text(encoding="utf-8")
            # frontmatter からタイトルを抽出
            title_match = re.search(r"^title:\s*['\"](.+?)['\"]", content, re.MULTILINE)
            if title_match:
                title = title_match.group(1).lower()

                # 2. 完全一致チェック（同一タイトル）
                if keyword.lower() == title:
                    print(f"  [WARNING] 重複検出（完全一致）: {article_file.name}")
                    return True

                # 3. 部分一致チェック（一方が他方を完全に含む）
                if keyword.lower() in title or title in keyword.lower():
                    print(f"  [WARNING] 重複検出（部分一致）: {article_file.name}")
                    return True

                # 注: 高類似度の記事は「関連記事」として別扱い（重複ではない）
        except Exception:
            pass

    return False


def check_article_quality(file_path: Path, keyword: str) -> bool:
    """記事品質をチェック（簡易版）"""
    try:
        from check_article_quality import generate_quality_report

        text = file_path.read_text(encoding="utf-8")
        report = generate_quality_report(text, keyword)

        status = report["overall_status"]
        score = report["overall_score"]

        print(f"\n[Quality Check] {status} (Score: {score}/100)")

        # 警告表示
        if report["ai_likeness"]["found_phrases"]:
            print(f"  [WARNING] AIっぽい表現: {report['ai_likeness']['total_issues']}個")

        if report["word_count"]["status"] != "OK":
            print(f"  [WARNING] 文字数: {report['word_count']['char_count']} 字 (推奨: 2000-3500)")

        return status == "PASS"

    except ImportError:
        print("[WARNING] 品質検査スクリプトが見つかりません")
        return True  # エラーでも続行


def main():
    parser = argparse.ArgumentParser(description="アフィリエイト記事自動生成（ハイブリッドモード）")
    parser.add_argument("--count", type=int, default=2, metavar="N", help="生成する記事数（デフォルト: 2）")
    parser.add_argument("--csv", action="store_true", help="CSVキーワードから生成のみ")
    parser.add_argument("--csv-count", type=int, metavar="N", help="CSV記事生成数")
    parser.add_argument("--topic", type=str, help="記事にするトピック（例: 'Claude Codeソースコード流出'）")
    parser.add_argument("--news", action="store_true", help="RSSから最新ニュースを取得して記事生成")
    parser.add_argument("--auto", action="store_true", help="対話なしで自動実行（--newsと組み合わせてランダム選択）")
    parser.add_argument("--auto-discover", type=int, metavar="N", help="トレンドキーワード発掘 + 記事生成（N記事）")
    parser.add_argument("--hybrid", action="store_true", help="ハイブリッドモード：1記事RSSフィード + 1記事CSV（デフォルト）")
    parser.add_argument("--keyword-stats", action="store_true", help="キーワード統計を表示")
    parser.add_argument("--reset-keywords", action="store_true", help="CSVキーワードをリセット（未使用状態に戻す）")
    args = parser.parse_args()

    print("記事生成を開始します...")

    # Gemini API初期化
    if not init_gemini_api():
        print("[INFO] Gemini API is not available. Using Pollinations.ai for image generation.\n")

    # キーワード統計表示
    if args.keyword_stats:
        print_keyword_stats()
        return

    # キーワードリセット
    if args.reset_keywords:
        if input("本当にCSVキーワードをリセットしますか？ (yes/no): ").lower() == "yes":
            reset_all_keywords()
        return

    # CSV キーワードファイルから記事生成
    if args.csv:
        csv_count = args.csv_count or 1
        print(f"\n[CSV MODE] {csv_count} articles will be generated")
        print_keyword_stats()

        generated_count = 0
        excluded_keywords = set()  # 除外キーワード
        target_count = csv_count

        # 生成成功件数が目標に達するまでループ
        while generated_count < target_count:
            # 未使用キーワードを選択
            result = select_unused_keyword()
            if result is None:
                print("[ERROR] No available keywords")
                break

            main_kw, related_kws = result
            genre = "ブログ"  # CSVファイルのキーワードはジャンル指定なし

            print(f"\n[{generated_count+1}/{target_count}] メインキーワード: {main_kw}")
            print(f"  関連キーワード: {', '.join(related_kws)}")

            # 重複チェック
            if check_duplicate_article(main_kw):
                print(f"  [WARNING] スキップ: 既存記事と重複 → 除外リストに追加して次へ")
                mark_keyword_as_used(main_kw)  # 重複した場合も使用済みにマーク
                excluded_keywords.add(main_kw)
                continue

            print("Claude APIで記事生成中...")

            try:
                content = generate_article(main_kw, related_kws, genre)
                output_path = save_article(content, genre, main_kw, related_kws=related_kws)
                print(f"[OK] 完了: {output_path}")

                # キーワードを使用済みにマーク
                mark_keyword_as_used(main_kw)

                # 品質チェック
                check_article_quality(output_path, main_kw)

                generated_count += 1

                # レート制限対策
                time.sleep(3)

            except Exception as e:
                print(f"[FAIL] エラー: {e}")
                # エラー時は次のキーワードへ
                mark_keyword_as_used(main_kw)
                excluded_keywords.add(main_kw)

        print(f"\n生成完了: {generated_count}/{target_count}記事")
        if excluded_keywords:
            print(f"除外キーワード: {', '.join(excluded_keywords)}")
        print_keyword_stats()
        return

    # トレンドキーワード自動発掘モード
    if args.auto_discover:
        print(f"\n[AUTO-DISCOVER MODE] トレンドキーワード発掘 + {args.auto_discover}記事生成")

        # discover_keywords.py を実行してキーワード発掘
        try:
            result = subprocess.run(
                ["python", "scripts/discover_keywords.py"],
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode != 0:
                print(f"[WARN] キーワード発掘: スキップ（discover_keywords.py エラー）")
                print(f"  {result.stderr[:200]}")
            else:
                print("[OK] キーワード発掘: 完了")
        except Exception as e:
            print(f"[WARNING] キーワード発掘: スキップ（{type(e).__name__}）")

        # 発掘されたキーワード（trending_keywords.json）から記事生成
        try:
            trending_path = Path("scripts/trending_keywords.json")
            if not trending_path.exists():
                print("[ERROR] trending_keywords.json が見つかりません")
                return

            trending_data = json.loads(trending_path.read_text(encoding='utf-8'))
            trending_keywords = trending_data.get('keywords', [])

            if not trending_keywords:
                print("[ERROR] トレンドキーワードが見つかりません")
                return

            # スコアが高い順にソート
            trending_keywords.sort(key=lambda x: x.get('score', 0), reverse=True)

            generated_count = 0
            excluded_keywords = set()  # 除外キーワード
            kw_index = 0  # キーワードリストのインデックス
            target_count = args.auto_discover

            # 生成成功件数が目標に達するまで、またはキーワード尽きるまでループ
            while generated_count < target_count and kw_index < len(trending_keywords):
                kw_item = trending_keywords[kw_index]
                main_kw = kw_item['keyword']
                genre = kw_item.get('category', 'トレンド')
                related_kws = [main_kw]  # 関連キーワードはキーワード本体のみ

                print(f"\n[{generated_count+1}/{target_count}] キーワード: {main_kw}")
                print(f"  ジャンル: {genre}")
                print(f"  スコア: {kw_item.get('score', 0)}")

                # 重複チェック
                if check_duplicate_article(main_kw):
                    print(f"  [SKIP] 既存記事と重複 → 除外リストに追加して次へ")
                    excluded_keywords.add(main_kw)
                    # 除外キーワードをプールから「excluded」ステータスで更新
                    update_keyword_status_in_pool(main_kw, 'excluded')
                    kw_index += 1
                    continue

                print("Claude APIで記事生成中...")

                try:
                    content = generate_article(main_kw, related_kws, genre)
                    output_path = save_article(content, genre, main_kw, related_kws=related_kws)
                    print(f"[OK] 完了: {output_path}")

                    # キーワードを「completed」にマーク
                    update_keyword_status_in_pool(main_kw, 'completed')

                    # 品質チェック
                    check_article_quality(output_path, main_kw)

                    generated_count += 1

                    # レート制限対策
                    time.sleep(3)

                except Exception as e:
                    print(f"[ERROR] {e}")
                    # エラー時も除外して次へ進む
                    excluded_keywords.add(main_kw)
                    update_keyword_status_in_pool(main_kw, 'excluded')

                kw_index += 1

            print(f"\n生成完了: {generated_count}/{target_count}記事")
            if excluded_keywords:
                print(f"除外キーワード: {', '.join(excluded_keywords)}")

        except Exception as e:
            print(f"[ERROR] 自動発掘モード実行失敗: {e}")

        return

    if args.topic:
        # トピック直接指定モード
        print(f"トピック: {args.topic}")
        print("Claude APIで記事生成中...")
        content = generate_news_article(args.topic)
        output_path = save_article(content, "ニュース", args.topic)
        print(f"[OK] 完了: {output_path}")
        check_article_quality(output_path, args.topic)

    elif args.news:
        # RSSニュース取得モード
        print("RSSフィードからニュースを取得中...")
        news_items = fetch_news()
        if not news_items:
            print("ニュース取得失敗。通常モードで実行します。")
            genre, main_kw, related_kws = select_keyword()
            content = generate_article(main_kw, related_kws, genre)
            output_path = save_article(content, genre, main_kw, related_kws=related_kws)
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
            print(f"[OK] 完了: {output_path}")
            check_article_quality(output_path, selected['title'])

    else:
        # デフォルト：ハイブリッドモード（1記事RSSフィード + 1記事CSV）
        if not args.csv and not args.auto_discover and not args.topic and not args.news:
            # --hybrid フラグがなくても、他のオプションがなければハイブリッドモード
            args.hybrid = True

        if args.hybrid:
            print("\n[HYBRID MODE] RSSフィード(1記事) + CSV(1記事)を生成します")

            # ステップ1：RSSフィード発掘 + 1記事生成
            print("\n【ステップ1】RSSフィードからトレンドキーワード発掘...")
            try:
                result = subprocess.run(
                    ["python", "scripts/discover_keywords.py"],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                if result.returncode == 0:
                    print("[OK] キーワード発掘: 完了")
                else:
                    print(f"[WARN] キーワード発掘: スキップ")
            except Exception as e:
                print(f"[WARN] キーワード発掘: スキップ（{type(e).__name__}）")

            # 発掘されたキーワードから1記事生成
            try:
                trending_path = Path("scripts/trending_keywords.json")
                if trending_path.exists():
                    trending_data = json.loads(trending_path.read_text(encoding='utf-8'))
                    trending_keywords = trending_data.get('keywords', [])

                    if trending_keywords:
                        trending_keywords.sort(key=lambda x: x.get('score', 0), reverse=True)

                        # スコアが高いキーワードから重複なしで1記事生成
                        kw_index = 0
                        while kw_index < len(trending_keywords):
                            kw_item = trending_keywords[kw_index]
                            main_kw = kw_item['keyword']
                            genre = kw_item.get('category', 'トレンド')
                            related_kws = [main_kw]

                            print(f"\n[1/2] RSSキーワード: {main_kw}")
                            print(f"  ジャンル: {genre}")

                            if not check_duplicate_article(main_kw):
                                print("Claude APIで記事生成中...")
                                try:
                                    content = generate_article(main_kw, related_kws, genre)
                                    output_path = save_article(content, genre, main_kw, related_kws=related_kws)
                                    print(f"[OK] 完了: {output_path}")
                                    check_article_quality(output_path, main_kw)
                                    time.sleep(3)
                                    break
                                except Exception as e:
                                    print(f"[ERROR] {e}")
                            else:
                                print("  [SKIP] 重複検出")

                            kw_index += 1
            except Exception as e:
                print(f"[ERROR] RSS記事生成失敗: {e}")

            # ステップ2：CSVキーワードから1記事生成
            print("\n【ステップ2】CSVキーワードから1記事生成...")
            csv_count = 1
            generated_count = 0
            excluded_keywords = set()
            target_count = csv_count

            while generated_count < target_count:
                # 未使用キーワードを選択
                result = select_unused_keyword()
                if result is None:
                    print("[ERROR] CSVキーワードが見つかりません")
                    break

                main_kw, related_kws = result
                genre = "ブログ"

                print(f"\n[2/2] CSVキーワード: {main_kw}")
                print(f"  関連キーワード: {', '.join(related_kws)}")

                # 重複チェック
                if check_duplicate_article(main_kw):
                    print(f"  [SKIP] 重複検出 → 次へ")
                    mark_keyword_as_used(main_kw)
                    excluded_keywords.add(main_kw)
                    continue

                print("Claude APIで記事生成中...")

                try:
                    content = generate_article(main_kw, related_kws, genre)
                    output_path = save_article(content, genre, main_kw, related_kws=related_kws)
                    print(f"[OK] 完了: {output_path}")

                    # キーワードを使用済みにマーク
                    mark_keyword_as_used(main_kw)

                    # 品質チェック
                    check_article_quality(output_path, main_kw)

                    generated_count += 1

                    time.sleep(3)

                except Exception as e:
                    print(f"[ERROR] {e}")
                    mark_keyword_as_used(main_kw)
                    excluded_keywords.add(main_kw)

            print(f"\n生成完了: ハイブリッドモード（RSS + CSV）")
            if excluded_keywords:
                print(f"除外キーワード: {', '.join(excluded_keywords)}")
            return

        # CSVキーワード単独モード（--csv オプション指定時）
        csv_count = args.count
        print(f"\n[CSV MODE] {csv_count} 記事を生成します")

        generated_count = 0
        excluded_keywords = set()  # 除外キーワード
        target_count = csv_count

        # 生成成功件数が目標に達するまでループ
        while generated_count < target_count:
            # 未使用キーワードを選択
            result = select_unused_keyword()
            if result is None:
                print("[ERROR] CSVキーワードが見つかりません")
                break

            main_kw, related_kws = result
            keyword = selected['keyword']
            parts = keyword.split(',')
            main_kw = ' '.join(parts)
            related_kws = parts
            genre = infer_genre_from_keyword(parts[0])

            print(f"\n[{generated_count+1}/{target_count}] キーワード: {main_kw}")
            print(f"  ジャンル: {genre}")

            # 重複チェック
            if check_duplicate_article(main_kw):
                print(f"  [WARNING] スキップ: 既存記事と重複 → 除外リストに追加して次へ")
                mark_csv_keyword_as_used(keyword)
                excluded_keywords.add(main_kw)
                continue

            print("Claude APIで記事生成中...")

            try:
                content = generate_article(main_kw, related_kws, genre)
                output_path = save_article(content, genre, main_kw, related_kws=related_kws)
                print(f"[OK] 完了: {output_path}")

                # キーワードを使用済みにマーク
                mark_csv_keyword_as_used(keyword)

                # 品質チェック
                check_article_quality(output_path, main_kw)

                generated_count += 1

                # レート制限対策
                time.sleep(3)

            except Exception as e:
                print(f"[FAIL] エラー: {e}")
                # エラー時も除外して次のキーワードへ
                mark_csv_keyword_as_used(keyword)
                excluded_keywords.add(main_kw)

        print(f"\n生成完了: {generated_count}/{target_count}記事")
        if excluded_keywords:
            print(f"除外キーワード: {', '.join(excluded_keywords)}")


if __name__ == "__main__":
    main()
