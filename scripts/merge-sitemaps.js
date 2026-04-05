import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const distDir = path.join(__dirname, '../dist');

// sitemap-index.xml を読み込む
const indexPath = path.join(distDir, 'sitemap-index.xml');
const indexContent = fs.readFileSync(indexPath, 'utf-8');

// すべてのサイトマップファイルを取得
const files = fs.readdirSync(distDir);
const sitemapFiles = files
  .filter(f => f.match(/^sitemap-\d+\.xml$/))
  .sort((a, b) => {
    const numA = parseInt(a.match(/\d+/)[0]);
    const numB = parseInt(b.match(/\d+/)[0]);
    return numA - numB;
  });

// すべてのサイトマップを統合
let allUrls = [];

sitemapFiles.forEach(file => {
  const filePath = path.join(distDir, file);
  const content = fs.readFileSync(filePath, 'utf-8');

  // <url>...</url> タグを抽出
  const urlMatches = content.match(/<url>[\s\S]*?<\/url>/g) || [];
  allUrls = allUrls.concat(urlMatches);
});

// 単一の sitemap.xml を生成
const sitemapContent = `<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1" xmlns:video="http://www.google.com/schemas/sitemap-video/1.1">${allUrls.join('')}</urlset>`;

fs.writeFileSync(path.join(distDir, 'sitemap.xml'), sitemapContent);

console.log(`✓ Generated sitemap.xml with ${allUrls.length} URLs`);
