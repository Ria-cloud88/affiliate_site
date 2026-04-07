"""
キーワードからタイトル生成テスト
20個のサンプルキーワードで記事タイトルを生成
"""

import anthropic
import os
import sys

# APIキーの確認
api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    print("ERROR: ANTHROPIC_API_KEY が設定されていません")
    sys.exit(1)

# サンプルキーワード（自動発掘想定）
SAMPLE_KEYWORDS = [
    # plants
    ("観葉植物 冬 育て方 コツ", "plants"),
    ("パキラ 枯れる 原因と対策", "plants"),
    ("モンステラ 黄色くなる 理由", "plants"),
    ("ポトス 根腐れ 対策 予防", "plants"),
    ("アイビー 伸びすぎ カット 増やし方", "plants"),

    # pets
    ("メダカ 夏 死ぬ 高温対策", "pets"),
    ("金魚 水が濁る 原因 対策", "pets"),
    ("ハムスター ケージ 臭い 対策", "pets"),
    ("熱帯魚 初心者 飼いやすい 種類", "pets"),
    ("ビオトープ 作り方 初心者 メンテナンス", "pets"),

    # mindset
    ("朝起きれない 理由 科学的対策", "mindset"),
    ("睡眠の質 上げる 方法 実践", "mindset"),
    ("集中力 続かない 脳科学 対策", "mindset"),
    ("やる気 出ない スランプ 回復", "mindset"),
    ("習慣化できない 理由 心理学", "mindset"),

    # automation
    ("Python 自動化 初心者 何から始める", "automation"),
    ("Excel VBA 自動化 実例", "automation"),
    ("Selenium 使い方 Webスクレイピング", "automation"),
    ("API 連携 自動化 ツール作成", "automation"),
    ("Windows 定時実行 タスク自動化", "automation"),
]

TITLE_PROMPT = """以下のキーワードから、クリック率が高いブログ記事のタイトルを生成してください。

キーワード: {keyword}
ジャンル: {category}

要件:
- 35文字以内
- キーワードを自然に含める
- 読者の悩みを解決する内容を示す
- SEO対策されている

タイトルのみを返してください。"""

client = anthropic.Anthropic(api_key=api_key)

print("=" * 70)
print("キーワード → タイトル生成テスト")
print("=" * 70)
print()

titles = []

for i, (keyword, category) in enumerate(SAMPLE_KEYWORDS, 1):
    prompt = TITLE_PROMPT.format(keyword=keyword, category=category)

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}],
        )

        title = message.content[0].text.strip()
        titles.append({
            "num": i,
            "keyword": keyword,
            "category": category,
            "title": title
        })

        print(f"{i:2d}. [{category:11s}] {title}")
        print(f"     キーワード: {keyword}")
        print()

    except Exception as e:
        print(f"{i:2d}. ERROR: {e}")
        print()

print("=" * 70)
print(f"生成完了: {len(titles)}/20 個のタイトル")
print("=" * 70)

# 結果をファイルに保存
import json
from pathlib import Path

output_file = Path("scripts/titles_test_result.json")
output_file.write_text(
    json.dumps(titles, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print(f"\n結果を保存しました: {output_file}")
