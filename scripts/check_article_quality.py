"""
記事品質検査スクリプト
AIっぽさ、冗長性、キーワード含有などを自動チェック
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# AIっぽい表現（避けるべき）
AI_LIKE_PHRASES = [
    "いかがでしたか",
    "ぜひご覧ください",
    "ぜひご参照ください",
    "いかがでしょうか",
    "いえるでしょう",
    "といえます",
    "といった",
    "こちら",
    "ご紹介します",
    "お伝えします",
    "さらに詳しく",
    "注目されています",
    "人気があります",
    "話題になっています",
    "重要です",
    "大切です",
    "わかります",
    "できます",
    "思います",
    "考えられます",
]

# 冗長な表現
REDUNDANT_PHRASES = [
    r"また、",  # 文頭の「また」
    r"しかし、",  # 文頭の「しかし」
    r"そして、",  # 文頭の「そして」
    r"([。！？])\1{2,}",  # 句点の多重
    r"です。です。",  # 同じ文末の繰り返し
]

# 禁止ワード
FORBIDDEN_WORDS = [
    "AI特有",
    "〜という",
    "〜と言える",
    "〜と言えるでしょう",
]


def check_ai_likeness(text: str) -> Dict:
    """AIっぽさをスコア化（0-100、低いほどOK）"""
    found_phrases = []

    for phrase in AI_LIKE_PHRASES:
        count = text.lower().count(phrase)
        if count > 0:
            found_phrases.append((phrase, count))

    # スコア計算：表現の数 × 重み
    score = min(100, sum(count * 5 for _, count in found_phrases))

    return {
        "score": score,
        "status": "OK" if score < 20 else "WARNING" if score < 50 else "NG",
        "found_phrases": found_phrases,
        "total_issues": sum(count for _, count in found_phrases),
    }


def check_redundancy(text: str) -> Dict:
    """冗長性をチェック（同じ文や表現の繰り返し）"""
    lines = text.split("\n")
    issues = []

    # 短い文が連続していないか
    short_lines = [l for l in lines if len(l) < 30 and l.strip()]
    if len(short_lines) > len(lines) * 0.3:
        issues.append(("短い文が多い（読みにくい可能性）", len(short_lines)))

    # 句点の多重をチェック
    for phrase, count in [(p, len(re.findall(p, text))) for p in REDUNDANT_PHRASES]:
        if count > 0:
            issues.append((f"冗長表現: {phrase}", count))

    # スコア計算
    score = min(100, len(issues) * 15)

    return {
        "score": score,
        "status": "OK" if score < 20 else "WARNING" if score < 50 else "NG",
        "issues": issues,
        "total_issues": len(issues),
    }


def check_keyword_inclusion(text: str, keyword: str) -> Dict:
    """キーワード含有チェック"""
    # タイトルを除外
    body = text.split("\n", 2)[-1] if "\n" in text else text

    keyword_lower = keyword.lower()
    count = body.lower().count(keyword_lower)

    return {
        "keyword": keyword,
        "count": count,
        "status": "OK" if count >= 1 else "NG",
        "requirement": "1回以上含まれるべき",
    }


def check_word_count(text: str) -> Dict:
    """文字数チェック"""
    # タイトル行を除外
    body = text.split("\n", 2)[-1] if "\n" in text else text
    body = re.sub(r"```[\s\S]*?```", "", body)  # コードブロック除外
    char_count = len(re.sub(r"\s", "", body))

    status = (
        "OK"
        if 2000 <= char_count <= 3500
        else "WARNING" if 1800 <= char_count <= 3700 else "NG"
    )

    return {
        "char_count": char_count,
        "status": status,
        "requirement": "2000～3500文字（推奨）",
    }


def check_structure(text: str) -> Dict:
    """見出し構成チェック"""
    h2_count = len(re.findall(r"^##\s", text, re.MULTILINE))
    h3_count = len(re.findall(r"^###\s", text, re.MULTILINE))

    issues = []
    if h2_count > 5:
        issues.append(f"h2見出しが多い（{h2_count}個） → 3～4個に絞ってください")
    if h2_count == 0:
        issues.append("h2見出しがない")
    if h3_count > h2_count * 2:
        issues.append(f"h3が多い（h2:{h2_count}, h3:{h3_count}）")

    return {
        "h2_count": h2_count,
        "h3_count": h3_count,
        "status": "OK" if not issues else "WARNING",
        "issues": issues,
    }


def generate_quality_report(
    text: str, keyword: str = None
) -> Dict:
    """品質レポート生成"""
    ai_likeness = check_ai_likeness(text)
    redundancy = check_redundancy(text)
    word_count = check_word_count(text)
    structure = check_structure(text)
    keyword_check = check_keyword_inclusion(text, keyword) if keyword else None

    # 総合スコア（0-100、低いほどOK）
    scores = [ai_likeness["score"], redundancy["score"], word_count["score"]]
    overall_score = sum(scores) // len(scores)

    return {
        "overall_score": overall_score,
        "overall_status": (
            "PASS"
            if overall_score < 30
            else "CAUTION" if overall_score < 60 else "REWRITE_NEEDED"
        ),
        "ai_likeness": ai_likeness,
        "redundancy": redundancy,
        "word_count": word_count,
        "structure": structure,
        "keyword_check": keyword_check,
    }


def print_report(report: Dict):
    """レポートを見やすく表示"""
    print("\n" + "=" * 70)
    print("📊 記事品質検査レポート")
    print("=" * 70)

    # 総合スコア
    overall = report["overall_status"]
    score = report["overall_score"]
    emoji = "✅" if overall == "PASS" else "⚠️" if overall == "CAUTION" else "❌"
    print(f"\n{emoji} 総合判定: {overall} (スコア: {score}/100)")

    # AIっぽさ
    print("\n【AIっぽさチェック】")
    ai = report["ai_likeness"]
    print(f"  スコア: {ai['score']}/100 ({ai['status']})")
    if ai["found_phrases"]:
        print("  避けるべき表現:")
        for phrase, count in ai["found_phrases"]:
            print(f"    - '{phrase}' ({count}回)")

    # 冗長性
    print("\n【冗長性チェック】")
    red = report["redundancy"]
    print(f"  スコア: {red['score']}/100 ({red['status']})")
    if red["issues"]:
        print("  問題:")
        for issue, count in red["issues"]:
            print(f"    - {issue} ({count}件)")

    # 文字数
    print("\n【文字数チェック】")
    wc = report["word_count"]
    print(f"  {wc['char_count']} 文字 ({wc['status']})")
    print(f"  要件: {wc['requirement']}")

    # 構成
    print("\n【見出し構成チェック】")
    st = report["structure"]
    print(f"  h2: {st['h2_count']}個, h3: {st['h3_count']}個 ({st['status']})")
    if st["issues"]:
        print("  改善提案:")
        for issue in st["issues"]:
            print(f"    - {issue}")

    # キーワード
    if report["keyword_check"]:
        print("\n【キーワード含有チェック】")
        kw = report["keyword_check"]
        print(f"  キーワード: '{kw['keyword']}'")
        print(f"  含有数: {kw['count']}回 ({kw['status']})")

    print("\n" + "=" * 70)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="記事品質検査")
    parser.add_argument("file", type=str, help="チェック対象ファイル")
    parser.add_argument("--keyword", type=str, help="キーワード（オプション）")

    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"ERROR: ファイルが見つかりません: {file_path}")
        sys.exit(1)

    text = file_path.read_text(encoding="utf-8")

    report = generate_quality_report(text, args.keyword)
    print_report(report)

    # 終了コード（PASS=0, CAUTION=1, REWRITE=2）
    exit_codes = {"PASS": 0, "CAUTION": 1, "REWRITE_NEEDED": 2}
    sys.exit(exit_codes.get(report["overall_status"], 2))


if __name__ == "__main__":
    main()
