# Article Generation System - Latest Improvements

## ✅ Implementation Complete

### 1. Article Structure Improvement: Summary Section Split

**What Changed:**
- Article structure expanded from 7 sections to 8 sections
- Final "まとめ・CTA" section split into two distinct sections:
  - **Section 7:** 実行ステップ・次のアクション (250-350 chars) - Concrete first steps
  - **Section 8:** まとめと継続 (250-350 chars) - Summary & long-term goals

**Why:** Improves readability and scanning. Long articles no longer have a massive final section; instead, they have focused subsections.

**Where:** `scripts/generate_article.py` (lines 100-101 in SYSTEM_PROMPT)

---

### 2. Dynamic Color Theme System

**Color Palette by Genre:**

| Genre | Color | Hex | Use Case |
|-------|-------|-----|----------|
| **AIツール** | Blue | #0066cc | AI tools & automation |
| **自動化ツール** | Cyan-Blue | #0088dd | Automation & integration |
| **副業** | Orange | #ff9500 | Side hustles & freelancing |
| **ガジェット** | Green | #00aa44 | Hardware & devices |
| **生活改善** | Purple | #9966ff | Lifestyle & wellness |

**New Files:**
- `src/utils/colorThemes.ts` - Color configuration with utility functions
- `src/components/InteractiveTOC.astro` - Theme-aware interactive TOC

**Modified Files:**
- `src/layouts/BlogPost.astro` - Integrated theme colors throughout layout
- `src/components/TableOfContents.astro` - Added genre support for dynamic colors

**Styling Applied To:**
- Genre tag (primary color background)
- Links and breadcrumbs (theme color with dark hover)
- Hero image border (theme light color)
- Table of Contents (theme-specific styling)
- Interactive elements (theme color with transitions)

---

### 3. Interactive Table of Contents

**How It Works:**
1. New `InteractiveTOC` component runs client-side JavaScript
2. Automatically extracts h2 headings from article content
3. Generates clickable, scrollable TOC with smooth navigation
4. **Auto-hides** if article has fewer than 5 headings (keeps UI clean)
5. **Theme-aware** - colors match the article's genre

**When It Appears:**
- Automatically in all blog articles
- Displays below hero image, above article body
- Collapsible via `<details>` element for cleaner UI

---

## 🎨 Visual Changes Users Will See

### Per-Genre Color Differentiation
- **Blue links/tags** = AI tools (Claude, ChatGPT, etc.)
- **Orange links/tags** = Side hustles (副業, freelancing)
- **Green links/tags** = Gadgets (wireless earbuds, keyboards, etc.)
- **Purple links/tags** = Lifestyle improvements (sleep, productivity, etc.)
- **Cyan links/tags** = Automation (Zapier, Make, n8n, etc.)

### Improved Content Scanning
- Shorter final sections mean less wall-of-text feeling
- Interactive TOC lets readers jump to sections
- Genre-specific colors help visual categorization

---

## 📋 Technical Implementation

### File Structure
```
src/
├── utils/
│   └── colorThemes.ts          (NEW - Color config)
├── components/
│   ├── InteractiveTOC.astro    (NEW - Smart TOC)
│   └── TableOfContents.astro   (UPDATED - Theme support)
└── layouts/
    └── BlogPost.astro          (UPDATED - Theme colors + TOC)
scripts/
└── generate_article.py         (UPDATED - Section structure)
```

### Color Mapping Logic
```javascript
// In ColorThemes.ts
genreColorThemes = {
  "AIツール": { primary: "#0066cc", ... },
  "副業": { primary: "#ff9500", ... },
  // etc.
}

// Applied via CSS variables
--color-primary: {primary}
--color-background: {light variant}
--color-accent: {bright variant}
```

### Interactive TOC Logic
```javascript
// In InteractiveTOC.astro
1. Find all h2 elements in .prose
2. Filter out metadata sections (目次, 関連記事, etc.)
3. Create list items with smooth scroll-to links
4. Apply theme colors via CSS variables
5. Hide if < 5 headings found
```

---

## 🔄 How Articles Flow Through System

1. **Generation** (`generate_article.py`)
   - Selects genre + keywords
   - Generates content with 8-section structure
   - Creates markdown with proper frontmatter

2. **Rendering** (Astro)
   - `BlogPost.astro` layout receives genre from frontmatter
   - Applies theme colors via `getThemeColors(genre)`
   - Renders `InteractiveTOC` component
   - Renders article markdown in `.prose` div

3. **Client-Side** (JavaScript in `InteractiveTOC.astro`)
   - Scans h2 headings on page load
   - Builds TOC dynamically
   - Applies theme colors via CSS custom properties
   - Hides TOC if not enough headings

---

## ✨ Future Enhancement Opportunities

1. Add color customization per article via frontmatter
2. Create dark mode variants for each color theme
3. Add visual indicators for article read time (genre-colored bar)
4. Implement analytics tracking for theme-based user preferences
5. Add color preview in admin panel for article creation

---

## 🧪 Testing Recommendations

1. Generate articles in each genre category
2. Verify colors match expectations
3. Check TOC appears for long articles (120+ periods)
4. Verify TOC hides for short articles
5. Test responsive design on mobile (TOC should stack properly)
6. Verify links and hover effects use correct colors

---

**Status:** ✅ Ready for deployment  
**Last Updated:** 2026-04-09  
**Requires:** Next article generation cycle to see results
