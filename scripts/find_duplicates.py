"""
既存記事から重複を検出するスクリプト
同じテーマ・キーワードを持つ記事ペアを特定
"""

import re
from pathlib import Path
from collections import defaultdict


def extract_metadata(content: str) -> dict:
    """記事のメタデータを抽出"""
    metadata = {}

    # タイトル抽出
    title_match = re.search(r"^title:\s*['\"](.+?)['\"]", content, re.MULTILINE)
    metadata['title'] = title_match.group(1) if title_match else ""

    # ジャンル抽出
    genre_match = re.search(r"^genre:\s*['\"](.+?)['\"]", content, re.MULTILINE)
    metadata['genre'] = genre_match.group(1) if genre_match else ""

    # 本文抽出（frontmatter除外）
    body_match = re.search(r'^---\n(.*?)\n---\n\n(.+)$', content, re.MULTILINE | re.DOTALL)
    if body_match:
        metadata['body'] = body_match.group(2)
    else:
        metadata['body'] = content

    # 見出しを抽出（メインキーワード候補）
    headings = re.findall(r'^## (.+)$', metadata['body'], re.MULTILINE)
    metadata['headings'] = headings

    return metadata


def extract_keywords(title: str, body: str) -> set:
    """タイトル・本文から重要な単語を抽出（3文字以上）"""
    all_text = f"{title} {body}".lower()

    # 日本語をそのままキーワード化
    # 単語分割（スペース区切り）
    words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]{3,}', all_text)

    # 重複排除
    return set(words)


def calculate_similarity(keywords1: set, keywords2: set) -> float:
    """2つのキーワードセットの類似度を計算（Jaccard係数）"""
    if not keywords1 or not keywords2:
        return 0.0

    intersection = len(keywords1 & keywords2)
    union = len(keywords1 | keywords2)

    return intersection / union if union > 0 else 0.0


def find_duplicates(similarity_threshold: float = 0.5) -> list[dict]:
    """既存記事から重複ペアを検出"""
    blog_dir = Path("src/content/blog")
    articles = list(blog_dir.glob("*.md"))

    print(f"[分析中] {len(articles)}件の記事")
    print()

    # 記事データを読み込み
    article_data = {}
    for article_file in articles:
        try:
            content = article_file.read_text(encoding='utf-8')
            metadata = extract_metadata(content)

            article_data[article_file.name] = {
                'title': metadata['title'],
                'genre': metadata['genre'],
                'keywords': extract_keywords(metadata['title'], metadata['body']),
                'body_length': len(metadata['body']),
                'file': article_file.name
            }
        except Exception as e:
            print(f"[警告] 読み込み失敗: {article_file.name} - {e}")

    # 重複検出
    duplicates = []
    checked_pairs = set()

    article_files = list(article_data.keys())
    for i, file1 in enumerate(article_files):
        for file2 in article_files[i+1:]:
            pair_key = tuple(sorted([file1, file2]))
            if pair_key in checked_pairs:
                continue
            checked_pairs.add(pair_key)

            data1 = article_data[file1]
            data2 = article_data[file2]

            # 同じジャンルかつキーワード類似度が高い場合
            if data1['genre'] == data2['genre']:
                similarity = calculate_similarity(data1['keywords'], data2['keywords'])

                if similarity >= similarity_threshold:
                    duplicates.append({
                        'file1': file1,
                        'title1': data1['title'],
                        'file2': file2,
                        'title2': data2['title'],
                        'genre': data1['genre'],
                        'similarity': similarity,
                        'body_length1': data1['body_length'],
                        'body_length2': data2['body_length']
                    })

    # 類似度でソート（降順）
    duplicates.sort(key=lambda x: x['similarity'], reverse=True)

    return duplicates


def print_duplicates(duplicates: list[dict]):
    """重複を見やすく出力"""
    if not duplicates:
        print("[OK] 重複なし")
        return

    print(f"[警告] 重複検出: {len(duplicates)}ペア\n")
    print("=" * 100)

    for i, dup in enumerate(duplicates, 1):
        similarity_pct = dup['similarity'] * 100

        print(f"\n[{i}] 類似度: {similarity_pct:.1f}% | ジャンル: {dup['genre']}")
        print(f"  記事1: {dup['file1']}")
        print(f"    タイトル: {dup['title1']}")
        print(f"    本文長: {dup['body_length1']}字")
        print(f"\n  記事2: {dup['file2']}")
        print(f"    タイトル: {dup['title2']}")
        print(f"    本文長: {dup['body_length2']}字")

        # 削除候補を提案（古い方 = スラッグ番号が小さい方）
        file1_num = int(dup['file1'].split('-')[2].split('.')[0] or '0')
        file2_num = int(dup['file2'].split('-')[2].split('.')[0] or '0')

        if file1_num < file2_num:
            old_file = dup['file1']
            new_file = dup['file2']
        else:
            old_file = dup['file2']
            new_file = dup['file1']

        print(f"\n  [提案] {old_file} を削除（古い方）")
        print(f"     理由: 新しい記事 {new_file} で統合済み")
        print("-" * 100)


def export_duplicates_json(duplicates: list[dict]):
    """重複結果をJSONで保存"""
    import json

    output_path = Path("scripts/duplicate_articles.json")

    export_data = {
        'total_duplicates': len(duplicates),
        'duplicates': [
            {
                'file1': d['file1'],
                'title1': d['title1'],
                'file2': d['file2'],
                'title2': d['title2'],
                'genre': d['genre'],
                'similarity': round(d['similarity'], 3),
                'body_length1': d['body_length1'],
                'body_length2': d['body_length2']
            }
            for d in duplicates
        ]
    }

    output_path.write_text(
        json.dumps(export_data, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )

    print(f"\n[保存] {output_path}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="既存記事から重複を検出")
    parser.add_argument("--threshold", type=float, default=0.5,
                        help="類似度の閾値 (0.0-1.0, デフォルト: 0.5)")
    parser.add_argument("--export", action="store_true",
                        help="結果をJSONで保存")
    args = parser.parse_args()

    print("\n" + "=" * 100)
    print("既存記事の重複検出")
    print("=" * 100 + "\n")

    duplicates = find_duplicates(similarity_threshold=args.threshold)
    print_duplicates(duplicates)

    if args.export:
        export_duplicates_json(duplicates)

    print(f"\n[完了] スキャン完了")


if __name__ == "__main__":
    main()
