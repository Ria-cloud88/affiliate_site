"""
Ollama版アフィリエイト記事自動生成スクリプト
Claude APIの代わりにローカルOllamaを使用（完全無料）

使用方法:
  # まずOllamaをインストール & 起動:
  ollama pull mistral
  ollama serve

  # 別のターミナルで実行:
  python scripts/generate_article_ollama.py --count 2
"""

import argparse
import json
import os
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path

# Ollama API用
import requests

# 既存モジュール
sys.path.insert(0, str(Path(__file__).parent))
from keyword_manager import mark_keyword_as_used
from check_article_quality import check_article_quality

# ========================================
# Ollama API設定
# ========================================
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "mistral"  # または "neural-chat", "orca-mini", etc
OLLAMA_TIMEOUT = 300  # 5分

def call_ollama(prompt: str, system_prompt: str = "") -> str:
    """Ollamaを呼び出して記事生成（API料金なし）"""
    try:
        # フルプロンプトを構築
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": full_prompt,
                "stream": False,
                "temperature": 0.7,
                "top_p": 0.9,
            },
            timeout=OLLAMA_TIMEOUT,
        )

        if response.status_code != 200:
            raise Exception(f"Ollama API Error: {response.status_code}")

        result = response.json()
        return result.get("response", "")

    except requests.exceptions.ConnectionError:
        print("❌ エラー: Ollamaに接続できません")
        print("   以下のコマンドでOllamaを起動してください:")
        print("   $ ollama pull mistral")
        print("   $ ollama serve")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Ollama呼び出しエラー: {e}")
        raise


# ========================================
# システムプロンプト（Claude版を簡略化）
# ========================================
SYSTEM_PROMPT = """あなたはSEO最適化された実用的なブログ記事を書くエディターです。

# 記事生成ルール
【文字数】3000字以上、推奨4000字
【句点】120個以上（1文＝1句点）
【構成】導入 → 目次 → 複数セクション → 表 → Q&A → まとめ
【キーワード】メインKW最低8回、関連KW10回以上
【品質】実用的で、読者が「何をすべきか」わかる内容

禁止表現：「重要です」「大切です」「のです」「ぜひ」
"""


def load_csv_keywords() -> list[dict]:
    """CSVからキーワード読み込み"""
    csv_path = Path("scripts/keywords_from_list.csv")
    if not csv_path.exists():
        print(f"❌ {csv_path} が見つかりません")
        return []

    try:
        import csv
        keywords = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['status'] == 'unused':
                    keywords.append({
                        'keyword': row['keyword'],
                        'status': row['status']
                    })
        return keywords
    except Exception as e:
        print(f"❌ CSV読み込みエラー: {e}")
        return []


def mark_csv_keyword_as_used(keyword: str):
    """CSVキーワードをusedに更新"""
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

        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['keyword', 'genre', 'status'])
            writer.writeheader()
            writer.writerows(rows)
        print(f"✅ キーワードをusedに更新: {keyword}")
    except Exception as e:
        print(f"❌ CSV更新エラー: {e}")


def infer_genre_from_keyword(keyword_first_word: str) -> str:
    """キーワードからジャンルを推測"""
    genre_keywords = {
        "ペット": ["犬", "猫", "ハムスター", "うさぎ", "インコ", "熱帯魚", "爬虫類"],
        "副業": ["副業", "フリーランス", "転職", "起業", "プログラミング", "Python"],
        "生活改善": ["ダイエット", "ヨガ", "プロテイン", "サプリメント", "睡眠", "スキンケア"],
        "ガジェット": ["照明", "スマートフォン", "iPhone", "ノートパソコン", "ヘッドフォン"],
    }

    for genre, keywords in genre_keywords.items():
        if keyword_first_word in keywords:
            return genre
    return "副業"


def generate_article(keyword: str, genre: str) -> str:
    """Ollamaで記事を生成（完全無料）"""
    parts = keyword.split(',')
    main_kw = ' '.join(parts)

    prompt = f"""以下のキーワードについて、SEO最適化されたブログ記事を書いてください。

キーワード: {main_kw}
ジャンル: {genre}

【必須条件】
- 3000字以上4000字程度
- タイトルは「# タイトル」形式
- 見出しは「## 見出し」形式
- 最後に「## まとめ」セクションを追加
- 記事の最後に「<span id="heading-XX"></span>」を各見出しの下に追加
- 表・図表を最低1個含める
- 実用的で、読者が「何をすべきか」わかる内容
- 禁止: 「重要です」「大切です」「のです」

記事を書いてください:"""

    print("🔄 Ollama で記事生成中...")
    print(f"   (ローカルで実行中のため API料金¥0)")

    try:
        content = call_ollama(prompt, SYSTEM_PROMPT)
        return content
    except Exception as e:
        print(f"❌ 記事生成エラー: {e}")
        raise


def save_article(content: str, genre: str, keyword: str) -> Path:
    """記事をマークダウンで保存"""
    parts = keyword.split(',')
    main_kw = ' '.join(parts)

    # タイトル抽出
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    title = title_match.group(1) if title_match else main_kw

    # 説明文抽出
    description = re.sub(r'[#*`]', '', content.split('\n\n')[1] if '\n\n' in content else '')[:120]

    # Frontmatter
    today = datetime.now().strftime('%Y-%m-%d')
    slug = f"{today}-{random.randint(10000, 99999):05x}"

    frontmatter = f"""---
title: '{title.replace("'", "''")}'
description: '{description.replace("'", "''")}'
pubDate: '{today}'
genre: '{genre}'
category: '{genre}'
source: 'ollama-local'
---

"""

    full_content = frontmatter + content

    output_path = Path("src/content/blog") / f"{slug}.md"
    output_path.write_text(full_content, encoding="utf-8")

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Ollama版 アフィリエイト記事自動生成（API料金ゼロ）"
    )
    parser.add_argument("--count", type=int, default=2, help="生成する記事数（デフォルト: 2）")
    parser.add_argument("--model", type=str, default="mistral", help="使用するOllamaモデル")
    args = parser.parse_args()

    global OLLAMA_MODEL
    OLLAMA_MODEL = args.model

    print("=" * 70)
    print("🎯 Ollama版 アフィリエイト記事自動生成")
    print("=" * 70)
    print(f"モデル: {OLLAMA_MODEL}")
    print(f"生成記事数: {args.count}")
    print(f"API料金: ¥0（ローカル実行）")
    print("=" * 70)
    print()

    generated_count = 0
    for i in range(args.count):
        # キーワード選択
        csv_keywords = load_csv_keywords()
        if not csv_keywords:
            print("❌ CSVキーワードが見つかりません")
            break

        selected = random.choice(csv_keywords)
        keyword = selected['keyword']
        parts = keyword.split(',')
        genre = infer_genre_from_keyword(parts[0])

        print(f"\n[{i+1}/{args.count}] キーワード: {keyword}")
        print(f"  ジャンル: {genre}")

        try:
            # 記事生成
            content = generate_article(keyword, genre)

            # 保存
            output_path = save_article(content, genre, keyword)
            print(f"✅ 完了: {output_path}")

            # キーワード更新
            mark_csv_keyword_as_used(keyword)

            generated_count += 1

            # 制限対策
            time.sleep(2)

        except Exception as e:
            print(f"❌ エラー: {e}")
            continue

    print()
    print("=" * 70)
    print(f"✅ 生成完了: {generated_count}/{args.count}記事")
    print(f"💰 API料金: ¥0")
    print("=" * 70)


if __name__ == "__main__":
    main()
