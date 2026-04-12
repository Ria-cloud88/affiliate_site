"""
トレンドキーワード自動発掘スクリプト（改善版）
Google Trends は Google がブロック中のため、Google Suggestions + フォールバック方式に変更

使い方:
  python scripts/discover_keywords.py              # キーワード発掘 + プール更新
  python scripts/discover_keywords.py --limit 10   # 10個のキーワード発掘
  python scripts/discover_keywords.py --update     # keywords_pool.json を更新
"""

import json
import os
import subprocess
import re
import sys
import time
import random
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

try:
    import anthropic
except ImportError:
    print("ERROR: anthropic is not installed. Install with: pip install anthropic")
    sys.exit(1)

from urllib.parse import quote

# ===== 設定 =====

KEYWORDS_POOL_PATH = Path("scripts/keywords_pool.json")
FALLBACK_KEYWORDS_PATH = Path("scripts/trending_keywords.json")

INITIAL_CATEGORIES = {
    'AIツール': ['ChatGPT', 'Claude', 'Gemini', 'Perplexity', 'AI'],
    'ペット': ['ペット', '犬', '猫', 'メダカ', '金魚', 'ハムスター'],
    '生活改善': ['心理', '睡眠', '集中', '習慣', 'ストレス'],
    '自動化': ['Python', '自動化', 'Excel', 'GAS', 'Zapier', 'Make'],
    '副業': ['副業', 'ブログ', 'YouTube', 'アフィリエイト', 'フリーランス']
}


# ===== Google Suggestions API =====

def get_google_suggestions(base_keyword: str) -> List[Dict]:
    """
    Google Suggestions からキーワードを取得

    Args:
        base_keyword: ベースキーワード（例：'ChatGPT'）

    Returns:
        キーワード辞書のリスト
    """
    suggestions = []

    print(f"  {base_keyword} のサジェスト取得中...")

    try:
        url = f"https://suggestions.google.com/complete/search?client=firefox&q={quote(base_keyword + ' ')}&hl=ja&gl=JP"

        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        )

        # リトライ3回
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=20) as resp:
                    data = resp.read().decode('utf-8')

                    # JSON パース
                    match = re.search(r'\[\s*"[^"]*",\s*\[(.*?)\]', data)
                    if match:
                        suggestions_str = match.group(1)
                        raw_suggestions = re.findall(r'"([^"]+)"', suggestions_str)

                        # キーワード辞書に変換
                        for kw in raw_suggestions[:15]:
                            if kw and len(kw) >= 3:
                                suggestions.append({
                                    'keyword': kw,
                                    'source': 'google_suggestions',
                                    'score': 50,
                                    'discovered_at': datetime.now().isoformat()
                                })

                        print("    OK: {}個のキーワード取得".format(len(suggestions)))
                        return suggestions

            except (urllib.error.HTTPError, urllib.error.URLError) as e:
                if attempt < 2:
                    print(f"    リトライ {attempt+1}/3: {type(e).__name__}")
                    time.sleep(random.uniform(3, 6))
                else:
                    print(f"    WARN: リトライ失敗 - {type(e).__name__}")

            except Exception as e:
                if attempt < 2:
                    time.sleep(random.uniform(2, 4))
                    continue
                else:
                    print(f"    WARN: {type(e).__name__}: {str(e)[:60]}")

    except Exception as e:
        print(f"    ERROR: {type(e).__name__}: {str(e)[:60]}")

    return suggestions


# ===== フォールバックキーワード =====

def load_fallback_keywords() -> List[Dict]:
    """
    フォールバック JSON からキーワードを読み込み
    Google API が失敗した時の保険
    """
    if not FALLBACK_KEYWORDS_PATH.exists():
        print("WARNING: フォールバック JSON が見つかりません")
        return []

    try:
        data = json.loads(FALLBACK_KEYWORDS_PATH.read_text(encoding='utf-8'))
        keywords = []

        for item in data.get('keywords', []):
            keywords.append({
                'keyword': item['keyword'],
                'category': item.get('category', 'その他'),
                'source': 'fallback',
                'score': item.get('score', item.get('priority', 10)),  # scoreまたはpriorityフィールドを使用
                'discovered_at': datetime.now().isoformat()
            })

        print(f"  フォールバック: {len(keywords)}個のキーワード読み込み")
        return keywords

    except Exception as e:
        print(f"  ERROR: フォールバック読み込み失敗 - {type(e).__name__}: {str(e)[:60]}")
        return []


# ===== キーワード発掘メイン =====

def discover_keywords(limit: int = 20) -> List[Dict]:
    """
    キーワード発掘（3段階フォールバック方式）

    フロー：
    1. Google Suggestions で取得を試みる
    2. 不足時はフォールバック JSON から追加
    3. 重複を削除
    """

    print("\n" + "="*70)
    print("トレンドキーワード自動発掘")
    print("="*70)

    all_keywords = []

    # ===== ステップ1：Google Suggestions =====
    print("\n[ステップ1] Google Suggestions からキーワード発掘中...")

    base_keywords = ['ChatGPT', 'Claude', 'AI', '副業', 'Python', 'ブログ']
    suggestions_count = 0

    for base_kw in base_keywords:
        try:
            suggestions = get_google_suggestions(base_kw)
            all_keywords.extend(suggestions)
            suggestions_count += len(suggestions)
            time.sleep(random.uniform(2, 4))
        except Exception as e:
            print(f"    WARN: {base_kw} スキップ - {type(e).__name__}")

    print(f"\n  取得: Google Suggestions から {suggestions_count} 件")

    # ===== ステップ2：フォールバック =====
    if len(all_keywords) < limit * 0.5:
        print("\n[ステップ2] キーワード不足 → フォールバック JSON から追加")

        fallback = load_fallback_keywords()

        # 既取得の Google Suggestions と重複しないもののみ追加
        existing_kws = set(kw['keyword'] for kw in all_keywords)
        fallback_additions = [kw for kw in fallback if kw['keyword'] not in existing_kws]

        all_keywords.extend(fallback_additions)
        print(f"  追加: {len(fallback_additions)}個")

    # ===== ステップ3：スコアリング & ソート =====
    print("\n[ステップ3] キーワードをスコアリング中...")

    # スコアでソート（降順）
    all_keywords.sort(key=lambda x: x['score'], reverse=True)

    # 重複削除
    seen = set()
    unique = []
    for kw in all_keywords:
        if kw['keyword'] not in seen:
            seen.add(kw['keyword'])
            unique.append(kw)

    # limit 数に制限
    result = unique[:limit]

    print(f"  発掘完了: {len(result)}個のユニークキーワード")

    return result


# ===== キーワードプール更新 =====

def load_keywords_pool() -> Dict:
    """既存のキーワードプール読み込み"""
    if KEYWORDS_POOL_PATH.exists():
        try:
            return json.loads(KEYWORDS_POOL_PATH.read_text(encoding='utf-8'))
        except Exception as e:
            print(f"WARNING: keywords_pool.json 読み込み失敗: {e}")

    # 初期化
    pool = {}
    for category in INITIAL_CATEGORIES.keys():
        pool[category] = []

    return pool


def save_keywords_pool(pool: Dict) -> None:
    """キーワードプールを保存"""

    # カテゴリごとにスコアでソート
    for category in pool:
        if isinstance(pool[category], list):
            pool[category].sort(key=lambda x: x.get('score', 0), reverse=True)

    KEYWORDS_POOL_PATH.write_text(
        json.dumps(pool, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )

    print("OK: {}".format(KEYWORDS_POOL_PATH))


def update_keywords_pool(new_keywords: List[Dict]) -> None:
    """キーワードプールを更新"""

    pool = load_keywords_pool()

    print("\nキーワードプール更新中...")
    added_count = 0

    for kw_item in new_keywords:
        # カテゴリを判定
        keyword = kw_item['keyword']
        category = kw_item.get('category', 'その他')

        if category not in pool:
            pool[category] = []

        # 既存チェック
        if not any(item['keyword'] == keyword for item in pool[category]):
            kw_item['status'] = 'pending'
            pool[category].append(kw_item)
            added_count += 1

    save_keywords_pool(pool)
    print("OK: {}個のキーワードを追加".format(added_count))


# ===== メイン処理 =====

def main():
    import argparse

    parser = argparse.ArgumentParser(description="トレンドキーワード自動発掘")
    parser.add_argument('--limit', type=int, default=20, help="発掘キーワード数の上限")
    parser.add_argument('--update', action='store_true', help="keywords_pool.json を更新")

    args = parser.parse_args()

    # キーワード発掘
    keywords = discover_keywords(limit=args.limit)

    if not keywords:
        print("\nERROR: キーワードが見つかりませんでした")
        return

    # キーワード表示
    print("\n発掘されたキーワード:")
    print("-"*70)
    for i, kw in enumerate(keywords, 1):
        print(f"{i}. [{kw.get('category', '未分類')}] {kw['keyword']} (スコア: {kw['score']})")

    # プール更新
    if args.update:
        print()
        update_keywords_pool(keywords)

    print("\n" + "="*70)


if __name__ == "__main__":
    main()
