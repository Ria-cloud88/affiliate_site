"""
既存記事に画像を追加するスクリプト
Pollinations.ai（無料・APIキー不要）で生成
使い方: python scripts/add_images.py
"""

import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ARTICLES = [
    ("2026-04-02-chatgpt-guide",         "artificial-intelligence,chatbot"),
    ("2026-04-02-claude-vs-chatgpt",     "artificial-intelligence,technology"),
    ("2026-04-02-ai-fukugyou",           "laptop,money,freelance"),
    ("2026-04-02-zapier-guide",          "automation,technology,workflow"),
    ("2026-04-02-affiliate-blog",        "blog,laptop,writing"),
    ("2026-04-02-ai-tools-comparison",   "technology,computer,software"),
    ("2026-04-02-wireless-earphone",     "earphones,headphones,music"),
    ("2026-04-02-crowdworks-vs-lancers", "freelance,remote,work"),
    ("2026-04-02-notion-ai",             "productivity,app,notebook"),
    ("2026-04-02-perplexity-guide",      "search,internet,technology"),
    ("2026-04-02-fukugyou-beginner",     "startup,money,success"),
    ("2026-04-02-setsuyaku-app",         "savings,money,finance"),
]

IMG_DIR = Path("public/images/blog")
BLOG_DIR = Path("src/content/blog")


def download_image(slug: str, prompt: str) -> bool:
    img_path = IMG_DIR / f"{slug}.jpg"
    if img_path.exists():
        print(f"  スキップ（既存）: {img_path.name}")
        return True

    seed = abs(hash(slug)) % 9999
    url = f"https://loremflickr.com/800/400/{prompt}?lock={seed}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=40) as resp:
            data = resp.read()
        img_path.write_bytes(data)
        print(f"  生成完了: {img_path.name} ({len(data)//1024}KB)")
        return True
    except Exception as e:
        print(f"  失敗: {e}")
        return False


def update_frontmatter(slug: str) -> bool:
    md_path = BLOG_DIR / f"{slug}.md"
    if not md_path.exists():
        return False

    content = md_path.read_text(encoding="utf-8")
    if "heroImage:" in content:
        return False  # 既にあるのでスキップ

    hero_line = f"heroImage: '/affiliate_site/images/blog/{slug}.jpg'"
    # pubDate行の後に挿入
    content = re.sub(
        r"(pubDate: '[^']+'\n)",
        r"\1" + hero_line + "\n",
        content
    )
    md_path.write_text(content, encoding="utf-8")
    return True


def main():
    IMG_DIR.mkdir(parents=True, exist_ok=True)

    for i, (slug, prompt) in enumerate(ARTICLES):
        print(f"[{i+1}/{len(ARTICLES)}] {slug}")
        success = download_image(slug, prompt)
        if success:
            updated = update_frontmatter(slug)
            if updated:
                print(f"  frontmatter更新済み")
        time.sleep(1)  # API負荷軽減

    print("\n完了！次のコマンドでデプロイしてください:")
    print('git add -A && git commit -m "add AI generated hero images" && git push')


if __name__ == "__main__":
    main()
