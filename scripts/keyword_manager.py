"""
キーワード管理モジュール

keyword1,keyword2,keyword3.txt から CSV形式のキーワードを読み込み、
使用済み/未使用の管理を行う。
"""

from pathlib import Path
import random


KEYWORD_FILE = Path("keyword1,keyword2,keyword3.txt")
USED_MARKER = "[USED] "  # 使用済みマーカー（cp932互換）


def load_keywords_from_csv():
    """
    CSV形式のキーワードファイルを読み込む

    Returns:
        {
            'used': [("メインKW", "関連KW1", "関連KW2"), ...],
            'unused': [("メインKW", "関連KW1", "関連KW2"), ...]
        }
    """
    if not KEYWORD_FILE.exists():
        return {'used': [], 'unused': []}

    try:
        lines = KEYWORD_FILE.read_text(encoding='utf-8').strip().split('\n')
        used = []
        unused = []

        for line in lines:
            if not line.strip():
                continue

            # ヘッダー行をスキップ
            if line.startswith('keyword'):
                continue

            # 使用済みマーカーをチェック（複数のマーカー形式に対応）
            if line.startswith(USED_MARKER) or line.startswith('✓ '):
                # マーカーを除去してキーワードを抽出
                if line.startswith(USED_MARKER):
                    clean_line = line[len(USED_MARKER):].strip()
                else:  # ✓ マーカー
                    clean_line = line[2:].strip()
                parts = [p.strip() for p in clean_line.split(',')]
                if len(parts) >= 1:
                    used.append(tuple(parts))
            else:
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 1:
                    unused.append(tuple(parts))

        return {'used': used, 'unused': unused}

    except Exception as e:
        print(f"[ERROR] Failed to read keyword file: {e}")
        return {'used': [], 'unused': []}


def select_unused_keyword():
    """
    未使用のキーワードをランダムに選択

    Returns:
        (メインキーワード, [関連キーワード1, 関連キーワード2, ...]) or None
    """
    data = load_keywords_from_csv()
    unused = data['unused']

    if not unused:
        print("[WARNING] No unused keywords available")
        return None

    # ランダムに未使用キーワードを選択
    selected = random.choice(unused)

    # メインキーワード = 最初の要素
    main_kw = selected[0]
    # 関連キーワード = 残りの要素
    related_kws = list(selected[1:]) if len(selected) > 1 else [main_kw]

    return main_kw, related_kws


def mark_keyword_as_used(main_kw: str):
    """
    キーワードを使用済みにマークして ファイルを更新

    Args:
        main_kw: メインキーワード
    """
    if not KEYWORD_FILE.exists():
        return

    try:
        data = load_keywords_from_csv()
        used = data['used']
        unused = data['unused']

        # 該当するキーワードを探す
        matched = None
        for i, kw_tuple in enumerate(unused):
            if kw_tuple[0] == main_kw:
                matched = kw_tuple
                unused.pop(i)
                used.append(matched)
                break

        if not matched:
            # すでに使用済みの可能性
            print(f"  [INFO] '{main_kw}' is already used or not found")
            return

        # ファイルを更新
        _save_keywords_to_csv(used, unused)
        print(f"  [OK] Keyword recorded: {main_kw}")

    except Exception as e:
        print(f"[ERROR] Failed to update keyword: {e}")


def _save_keywords_to_csv(used, unused):
    """
    キーワードをCSVファイルに保存

    Args:
        used: 使用済みキーワードのリスト
        unused: 未使用キーワードのリスト
    """
    lines = []

    # ヘッダーを追加
    lines.append("keyword1,keyword2,keyword3")

    # 未使用キーワードを追加
    for kw_tuple in unused:
        line = ','.join(str(k) for k in kw_tuple)
        lines.append(line)

    # 使用済みキーワードを追加（マーカー付き）
    for kw_tuple in used:
        line = ','.join(str(k) for k in kw_tuple)
        lines.append(f"{USED_MARKER}{line}")

    # ファイルに書き込み
    content = '\n'.join(lines)
    KEYWORD_FILE.write_text(content, encoding='utf-8')


def print_keyword_stats():
    """キーワード統計を表示"""
    data = load_keywords_from_csv()
    used_count = len(data['used'])
    unused_count = len(data['unused'])
    total = used_count + unused_count

    print("\n[Keyword Statistics]:")
    print(f"  Total: {total}")
    print(f"  Used: {used_count} ({used_count*100//total if total else 0}%)")
    print(f"  Unused: {unused_count} ({unused_count*100//total if total else 0}%)")


def reset_all_keywords():
    """
    すべてのキーワードを未使用状態にリセット
    """
    if not KEYWORD_FILE.exists():
        return

    try:
        data = load_keywords_from_csv()
        all_keywords = data['used'] + data['unused']

        # すべてを未使用として保存
        _save_keywords_to_csv([], all_keywords)
        print("[OK] All keywords have been reset")

    except Exception as e:
        print(f"[ERROR] Failed to reset keywords: {e}")
