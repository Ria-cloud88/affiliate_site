"""
既存記事から重複を検出するスクリプト（詳細版）
generate_article.py の check_duplicate_article() ロジックを使用
"""

import re
from pathlib import Path
from collections import defaultdict


def extract_title(content: str) -> str:
    """frontmatterからタイトルを抽出"""
    match = re.search(r"^title:\s*['\"](.+?)['\"]", content, re.MULTILINE)
    return match.group(1).strip() if match else ""


def extract_main_words(text: str) -> list[str]:
    """テキストから主要な単語を抽出（3文字以上）"""
    # 日本語と英数字を抽出
    words = re.findall(r'[\u4e00-\u9fff]{3,}|[a-zA-Z]{3,}', text.lower())
    return list(dict.fromkeys(words))  # 重複排除（順序保持）


def check_duplicates_in_articles() -> list[dict]:
    """既存記事から重複を検出"""
    blog_dir = Path("src/content/blog")
    article_files = sorted(list(blog_dir.glob("*.md")))

    print(f"[分析中] {len(article_files)}件の記事をスキャン...")

    # 記事データを収集
    articles = {}
    for article_file in article_files:
        try:
            content = article_file.read_text(encoding='utf-8')
            title = extract_title(content)
            if title:
                articles[article_file.name] = {
                    'title': title,
                    'main_words': extract_main_words(title),
                    'title_lower': title.lower()
                }
        except Exception as e:
            print(f"[警告] {article_file.name}: {e}")

    print(f"[完了] タイトル抽出: {len(articles)}件\n")

    # 重複検出
    duplicates = []
    checked_pairs = set()

    article_list = list(articles.keys())
    for i, file1 in enumerate(article_list):
        for file2 in article_list[i+1:]:
            pair_key = tuple(sorted([file1, file2]))
            if pair_key in checked_pairs:
                continue
            checked_pairs.add(pair_key)

            title1 = articles[file1]['title']
            title1_lower = articles[file1]['title_lower']
            words1 = articles[file1]['main_words']

            title2 = articles[file2]['title']
            title2_lower = articles[file2]['title_lower']
            words2 = articles[file2]['main_words']

            # 1. 完全一致チェック
            if title1_lower == title2_lower:
                duplicates.append({
                    'type': '完全一致',
                    'file1': file1,
                    'title1': title1,
                    'file2': file2,
                    'title2': title2,
                    'reason': 'タイトルが完全に同じ'
                })
                continue

            # 2. 一方が他方に含まれるチェック
            if title1_lower in title2_lower or title2_lower in title1_lower:
                duplicates.append({
                    'type': '部分一致',
                    'file1': file1,
                    'title1': title1,
                    'file2': file2,
                    'title2': title2,
                    'reason': 'タイトルが部分的に重複'
                })
                continue

            # 3. メイン単語の厳密な類似度チェック（真の重複のみ）
            if len(words1) >= 3 and len(words2) >= 3:
                common_words = set(words1) & set(words2)
                match_rate = len(common_words) / max(len(words1), len(words2))

                # 3語以上マッチするか、マッチ率80%以上のみが真の重複
                if len(common_words) >= 3 and match_rate >= 0.8:
                    duplicates.append({
                        'type': '真の重複',
                        'file1': file1,
                        'title1': title1,
                        'file2': file2,
                        'title2': title2,
                        'common_words': list(common_words),
                        'match_rate': round(match_rate, 2),
                        'reason': f'{len(common_words)}単語が共通（一致率{match_rate*100:.0f}%）'
                    })

    return duplicates


def print_duplicates(duplicates: list[dict]):
    """重複結果を表示"""
    if not duplicates:
        print("[OK] 重複検出なし\n")
        return

    # タイプ別に分類
    by_type = defaultdict(list)
    for dup in duplicates:
        by_type[dup['type']].append(dup)

    print(f"[警告] 重複検出: {len(duplicates)}ペア\n")
    print("=" * 100)

    for dup_type in ['完全一致', '部分一致', '高類似度']:
        if dup_type not in by_type:
            continue

        items = by_type[dup_type]
        print(f"\n[{dup_type}] {len(items)}ペア")
        print("-" * 100)

        for i, dup in enumerate(items, 1):
            print(f"\n  {i}. {dup['reason']}")
            print(f"     ファイル1: {dup['file1']}")
            print(f"       タイトル: {dup['title1']}")
            print(f"\n     ファイル2: {dup['file2']}")
            print(f"       タイトル: {dup['title2']}")

            if 'common_words' in dup:
                print(f"\n     共通単語: {', '.join(dup['common_words'])}")
                print(f"     一致率: {dup['match_rate']*100:.0f}%")

    print("\n" + "=" * 100)


def export_duplicates_json(duplicates: list[dict]):
    """重複結果をJSONで保存"""
    import json

    output_path = Path("scripts/duplicate_articles_detailed.json")

    export_data = {
        'total_duplicates': len(duplicates),
        'duplicates': []
    }

    for dup in duplicates:
        export_data['duplicates'].append({
            'type': dup['type'],
            'file1': dup['file1'],
            'title1': dup['title1'],
            'file2': dup['file2'],
            'title2': dup['title2'],
            'reason': dup['reason'],
            'common_words': dup.get('common_words', []),
            'match_rate': dup.get('match_rate', 0)
        })

    output_path.write_text(
        json.dumps(export_data, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )

    print(f"[保存] {output_path}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="既存記事から重複を検出（詳細版）")
    parser.add_argument("--export", action="store_true", help="結果をJSONで保存")
    args = parser.parse_args()

    print("\n" + "=" * 100)
    print("既存記事の重複検出（詳細版）")
    print("=" * 100 + "\n")

    duplicates = check_duplicates_in_articles()
    print_duplicates(duplicates)

    if args.export:
        export_duplicates_json(duplicates)

    print(f"\n[完了] スキャン終了")


if __name__ == "__main__":
    main()
