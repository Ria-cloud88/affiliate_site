"""
トレンドキーワード自動発掘スクリプト（ジャンル動的拡張版）
使い方:
  python scripts/discover_keywords.py              # すべてのジャンルから発掘 + 新ジャンル検出
  python scripts/discover_keywords.py --category plants --limit 10
  python scripts/discover_keywords.py --update     # keywords_pool.json を更新
"""

import json
import os
import subprocess
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Set
from collections import defaultdict

try:
    from pytrends.request import TrendReq
except ImportError:
    print("ERROR: pytrends is not installed. Install with: pip install pytrends")
    sys.exit(1)

try:
    import anthropic
except ImportError:
    print("ERROR: anthropic is not installed. Install with: pip install anthropic")
    sys.exit(1)

import random
import urllib.request
import urllib.error
from urllib.parse import quote

# ===== 設定 =====

# 既存ジャンル（初期値）
INITIAL_CATEGORIES = {
    'plants': ['植物', '観葉植物', '花', 'サボテン', '育て方'],
    'pets': ['ペット', '犬', '猫', 'メダカ', '金魚', 'ハムスター'],
    'mindset': ['心理', '睡眠', '集中', '習慣', 'ストレス', 'モチベーション'],
    'automation': ['Python', '自動化', 'Excel', 'API', 'プログラミング'],
    'monetize': ['副業', 'ブログ', 'YouTube', 'アフィリエイト', 'SEO']
}

KEYWORDS_POOL_PATH = Path("scripts/keywords_pool.json")


def load_categories_from_pool() -> Dict[str, List[str]]:
    """
    keywords_pool.json からカテゴリを読み込み（動的ジャンル対応）
    """
    if not KEYWORDS_POOL_PATH.exists():
        return INITIAL_CATEGORIES.copy()

    try:
        pool = json.loads(KEYWORDS_POOL_PATH.read_text(encoding='utf-8'))

        categories = {}
        for category, items in pool.items():
            if isinstance(items, list) and len(items) > 0:
                # 各カテゴリの最初のキーワードから推測（簡易版）
                keywords = [item.get('keyword', '') for item in items[:5]]
                categories[category] = keywords
            else:
                categories[category] = INITIAL_CATEGORIES.get(category, [])

        return categories if categories else INITIAL_CATEGORIES.copy()

    except Exception as e:
        print(f"WARNING: カテゴリ読み込み失敗: {e}")
        return INITIAL_CATEGORIES.copy()


def categorize_keyword(keyword: str, categories: Dict[str, List[str]]) -> str:
    """キーワードを既存カテゴリに分類"""
    for category, keywords in categories.items():
        if any(kw in keyword for kw in keywords):
            return category
    return 'unknown'


def get_google_trends_rising(base_keywords: List[str] = None) -> List[Tuple[str, float]]:
    """
    Google Trends から上昇中のトレンドキーワードを取得
    上昇率でソート（降順）
    """

    if base_keywords is None:
        base_keywords = ['観葉植物', 'ペット', 'Python', '副業', 'AI', '心理学']

    pytrends = TrendReq(hl='ja-JP', tz=540, timeout=20, retries=3)

    rising_keywords = []

    print("Google Trends からキーワード抽出中...")

    for base_kw in base_keywords:
        try:
            # 関連キーワード（rising）を取得
            print(f"  {base_kw} の関連キーワード取得...")

            pytrends.build_payload([base_kw], timeframe='now 1-m', geo='JP')
            related_data = pytrends.related_queries()

            if related_data and base_kw in related_data:
                rising_queries = related_data[base_kw].get('rising', [])

                for item in rising_queries[:15]:  # 上位15件
                    keyword = item.get('query', '')
                    value = item.get('value', 0)

                    if keyword and value > 0:
                        rising_keywords.append((keyword, value))

            # APIレート制限対策
            time.sleep(random.uniform(2, 5))

        except Exception as e:
            print(f"    WARNING: {base_kw} 処理失敗 - {type(e).__name__}")

    # スコアでソート（降順）
    rising_keywords.sort(key=lambda x: x[1], reverse=True)

    # 重複削除
    seen = set()
    unique = []
    for kw, score in rising_keywords:
        if kw not in seen:
            seen.add(kw)
            unique.append((kw, score))

    return unique[:50]  # 上位50件


def get_google_suggestions(base_keyword: str) -> List[str]:
    """
    Google からサジェストキーワードを取得
    """
    suggestions = []

    try:
        url = f"https://suggestions.google.com/complete/search?client=firefox&q={quote(base_keyword + ' ')}&hl=ja"

        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )

        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read().decode('utf-8')

            match = re.search(r'\[\s*"[^"]*",\s*\[(.*?)\]', data)
            if match:
                suggestions_str = match.group(1)
                suggestions = re.findall(r'"([^"]+)"', suggestions_str)

    except Exception as e:
        print(f"  サジェスト取得失敗: {type(e).__name__}")

    return suggestions[:15]


def detect_new_genres(all_keywords: List[str]) -> Dict[str, Dict]:
    """
    Claude API でキーワードから新しいジャンル候補を検出
    スコア>80なら自動追加
    """

    if not all_keywords:
        return {}

    # API キー確認
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY が設定されていません")
        return {}

    client = anthropic.Anthropic(api_key=api_key)

    # Claude API でジャンル検出
    keyword_list = "\n".join(all_keywords[:30])  # 最初の30個

    prompt = f"""以下のトレンドキーワード一覧から、新しい「有望なジャンル」を検出してください。

【キーワード一覧】
{keyword_list}

以下の JSON フォーマットで返してください。新しい（まだ記事化されていない）ジャンルのみ抽出してください：

{{
  "new_genres": [
    {{
      "genre_id": "snake_case_genre_name",
      "genre_name": "日本語ジャンル名",
      "description": "このジャンルについての簡潔な説明",
      "keywords": ["キーワード1", "キーワード2", "キーワード3"],
      "priority_score": 85,
      "reason": "なぜこのジャンルが有望か"
    }}
  ]
}}

条件:
- priority_score は 0-100 で評価（80以上 = 自動追加候補）
- keywords は 3-5 個の代表的なキーワード
- 既存ジャンル（plants, pets, mindset, automation, monetize）との重複は避ける
- 日本市場で成長性があるジャンルを優先
"""

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = message.content[0].text

        # JSON 抽出
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            result = json.loads(json_match.group(0))
            return result.get('new_genres', [])

    except Exception as e:
        print(f"Claude API エラー: {type(e).__name__}: {e}")

    return []


def score_keywords(candidates: List[Dict], categories: Dict[str, List[str]]) -> List[Dict]:
    """複合指標でキーワードをスコアリング（0-100）"""

    for c in candidates:
        score = 0

        # Google Trends スコア（重視度50%）
        if 'trends_value' in c and c['trends_value'] > 0:
            trend_score = min(50, (c['trends_value'] / 100) * 50)
            score += trend_score

        # ソースボーナス（30%）
        if c['source'] == 'google_trends':
            score += 30
        elif c['source'] == 'google_suggest':
            score += 20

        # 既出チェック（重複だとマイナス）
        if is_duplicate_in_pool(c['keyword']):
            score = max(0, score - 30)
        if is_duplicate_in_git(c['keyword']):
            score = max(0, score - 20)

        c['score'] = min(100, score)

    return candidates


def is_duplicate_in_pool(keyword: str) -> bool:
    """キーワードプール内で既出かチェック"""

    if not KEYWORDS_POOL_PATH.exists():
        return False

    try:
        pool = json.loads(KEYWORDS_POOL_PATH.read_text(encoding='utf-8'))

        for category in pool.values():
            if isinstance(category, list):
                for item in category:
                    if item.get('keyword') == keyword:
                        return True
    except Exception:
        pass

    return False


def is_duplicate_in_git(keyword: str) -> bool:
    """Git履歴から同じキーワードの既出をチェック"""

    try:
        result = subprocess.run(
            ['git', 'log', '--all', '--oneline', '--grep=' + keyword],
            capture_output=True,
            text=True,
            cwd='.',
            timeout=10
        )
        return len(result.stdout.strip()) > 0
    except Exception:
        return False


def discover_keywords(category: str = None, limit: int = 20) -> Tuple[List[Dict], List[Dict]]:
    """
    複合情報源からキーワードを発掘
    戻り値: (キーワード, 新ジャンル候補)
    """

    # 動的にカテゴリを読み込み
    categories = load_categories_from_pool()

    candidates = []

    # 1. Google Trends から上昇キーワードを取得
    base_keywords = list(set([kw for keywords in categories.values() for kw in keywords]))
    trends = get_google_trends_rising(base_keywords)

    print(f"\n取得: Google Trends から {len(trends)} 件")

    all_keywords = []  # 新ジャンル検出用

    for kw, value in trends:
        cat = categorize_keyword(kw, categories)

        if category and cat != category:
            continue

        candidates.append({
            'keyword': kw,
            'category': cat,
            'source': 'google_trends',
            'trends_value': value,
            'score': 0,
            'discovered_at': datetime.now().isoformat()
        })

        all_keywords.append(kw)

    # 2. Google サジェストから追加キーワード取得
    print("\nGoogle サジェストからキーワード抽出中...")

    for base_kw in list(categories.values())[0][:3]:  # 最初のカテゴリから3個のベースキーワード
        suggestions = get_google_suggestions(base_kw)

        for sug in suggestions:
            cat = categorize_keyword(sug, categories)

            if category and cat != category:
                continue

            # 既にある場合はスキップ
            if any(c['keyword'] == sug for c in candidates):
                continue

            candidates.append({
                'keyword': sug,
                'category': cat,
                'source': 'google_suggest',
                'score': 0,
                'discovered_at': datetime.now().isoformat()
            })

            all_keywords.append(sug)

        time.sleep(random.uniform(1, 3))

    print(f"合計: {len(candidates)} 件の候補\n")

    # スコアリング
    scored = score_keywords(candidates, categories)

    # スコアでソート
    scored.sort(key=lambda x: x['score'], reverse=True)

    # 重複排除（プール内 + Git履歴）
    filtered = []
    for item in scored:
        if len(filtered) >= limit:
            break

        if not is_duplicate_in_pool(item['keyword']) and not is_duplicate_in_git(item['keyword']):
            filtered.append(item)

    print(f"発掘完了: {len(filtered)} 件のユニークキーワード")

    # ===== 新ジャンル検出 =====
    print("\n新ジャンル候補を検出中...")

    new_genres = detect_new_genres(all_keywords)

    if new_genres:
        print(f"検出された新ジャンル: {len(new_genres)} 件")
        for genre in new_genres:
            print(f"  - [{genre.get('priority_score', 0)}点] {genre.get('genre_name')}")

    return filtered, new_genres


def load_keywords_pool() -> Dict:
    """既存のキーワードプールを読み込み"""

    if KEYWORDS_POOL_PATH.exists():
        try:
            return json.loads(KEYWORDS_POOL_PATH.read_text(encoding='utf-8'))
        except Exception as e:
            print(f"WARNING: keywords_pool.json 読み込み失敗: {e}")

    # 初期値（既存ジャンルのみ）
    pool = {}
    for category in INITIAL_CATEGORIES.keys():
        pool[category] = []

    return pool


def save_keywords_pool(pool: Dict) -> None:
    """キーワードプールを保存"""

    # 各カテゴリをスコアでソート
    for category in pool:
        if isinstance(pool[category], list):
            pool[category].sort(key=lambda x: x.get('score', 0), reverse=True)

    KEYWORDS_POOL_PATH.write_text(
        json.dumps(pool, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )

    print(f"保存: {KEYWORDS_POOL_PATH}")


def update_keywords_pool(new_keywords: List[Dict], new_genres: List[Dict]) -> None:
    """キーワードプールを更新（新ジャンルを自動追加）"""

    pool = load_keywords_pool()

    # 1. 既存カテゴリにキーワード追加
    for kw_item in new_keywords:
        category = kw_item.get('category', 'unknown')

        if category not in pool:
            pool[category] = []

        # 既存チェック
        if not any(item['keyword'] == kw_item['keyword'] for item in pool[category]):
            kw_item['status'] = 'pending'
            pool[category].append(kw_item)

    # 2. 新ジャンルを自動追加（スコア>80）
    for genre in new_genres:
        score = genre.get('priority_score', 0)

        if score > 80:  # A）完全自動：スコア>80なら自動追加
            genre_id = genre.get('genre_id', '')
            genre_name = genre.get('genre_name', '')

            if genre_id and genre_id not in pool:
                print(f"\n✓ 新ジャンル自動追加: [{score}点] {genre_name} ({genre_id})")

                # 新ジャンルのキーワードを追加
                pool[genre_id] = []

                for kw in genre.get('keywords', []):
                    pool[genre_id].append({
                        'keyword': kw,
                        'category': genre_id,
                        'source': 'new_genre_auto_discover',
                        'score': score - 5,  # ジャンルスコアを基準に少し下げる
                        'discovered_at': datetime.now().isoformat(),
                        'status': 'pending',
                        'genre_name': genre_name,
                        'reason': genre.get('reason', '')
                    })

    save_keywords_pool(pool)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="トレンドキーワード自動発掘（ジャンル拡張版）")
    parser.add_argument('--category', type=str, help="特定カテゴリのみ発掘")
    parser.add_argument('--limit', type=int, default=20, help="発掘数の上限")
    parser.add_argument('--update', action='store_true', help="keywords_pool.json を更新")

    args = parser.parse_args()

    print("=" * 70)
    print("トレンドキーワード自動発掘スクリプト（ジャンル動的拡張版）")
    print("=" * 70)

    # キーワード発掘
    keywords, new_genres = discover_keywords(category=args.category, limit=args.limit)

    if not keywords and not new_genres:
        print("\nキーワードが見つかりませんでした。")
        return

    # キーワード表示
    if keywords:
        print("\n発掘されたキーワード:")
        print("-" * 70)
        for i, kw in enumerate(keywords, 1):
            print(f"{i}. [{kw['category']}] {kw['keyword']} (スコア: {kw['score']:.1f})")

    # 新ジャンル表示
    if new_genres:
        print("\n検出された新ジャンル候補:")
        print("-" * 70)
        for genre in new_genres:
            score = genre.get('priority_score', 0)
            status = "✓ 自動追加対象" if score > 80 else "◯ 候補"
            print(f"{status} [{score}点] {genre.get('genre_name')}")
            print(f"  キーワード: {', '.join(genre.get('keywords', []))}")
            print(f"  理由: {genre.get('reason')}")
            print()

    # プール更新オプション
    if args.update:
        update_keywords_pool(keywords, new_genres)
        print("\nkeywords_pool.json を更新しました。")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
