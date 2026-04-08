#!/usr/bin/env python3
"""
既存のKEYWORD_POOLSからkeywords_pool.jsonを初期化するスクリプト
"""

import json
from pathlib import Path
from datetime import datetime

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

def init_pool():
    """キーワードプールを初期化"""
    pool = {}

    for genre, keywords in KEYWORD_POOLS.items():
        pool[genre] = []
        for main_kw, related_kws in keywords:
            pool[genre].append({
                "keyword": main_kw,
                "category": genre,
                "source": "builtin",
                "score": 75.0,
                "discovered_at": datetime.now().isoformat(),
                "status": "pending",
                "keywords": related_kws
            })

    # JSON保存
    output_path = Path("scripts/keywords_pool.json")
    output_path.write_text(json.dumps(pool, ensure_ascii=False, indent=2), encoding='utf-8')

    # 統計表示
    total = sum(len(items) for items in pool.values())
    try:
        print(f"[OK] キーワードプール初期化完了: {total}個のキーワード")
        for genre, items in pool.items():
            print(f"  {genre}: {len(items)}個")
    except Exception:
        # GitHub Actions など Unicode 対応環境でのエラー回避
        print(f"[OK] Initialized {total} keywords")

if __name__ == "__main__":
    import sys
    if "--force" in sys.argv or not Path("scripts/keywords_pool.json").exists():
        init_pool()
    else:
        # Check if pool is mostly empty or corrupted
        try:
            pool = json.loads(Path("scripts/keywords_pool.json").read_text(encoding='utf-8'))
            total_keywords = sum(len(items) if isinstance(items, list) else 0 for items in pool.values())
            if total_keywords < 5:  # Less than 5 keywords: reinitialize
                print("Pool is too small, reinitializing...")
                init_pool()
            else:
                print(f"Pool exists with {total_keywords} keywords, skipping reinitialization")
        except Exception as e:
            print(f"Pool corrupted or unreadable, reinitializing...")
            init_pool()
