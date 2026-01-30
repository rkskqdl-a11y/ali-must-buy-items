import os
import time
import random
import hmac
import hashlib
import requests
import json
from datetime import datetime

# 1. 환경 변수 및 설정
ALI_APP_KEY = os.environ.get("ALI_APP_KEY", "").strip()
ALI_SECRET = os.environ.get("ALI_SECRET", "").strip()
ALI_TRACKING_ID = os.environ.get("ALI_TRACKING_ID", "").strip()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
SITE_URL = "https://rkskqdl-a11y.github.io/ali-must-buy-items"

ID_LOG_FILE = "posted_ids.txt"

def load_posted_ids():
    if os.path.exists(ID_LOG_FILE):
        with open(ID_LOG_FILE, "r") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_posted_id(p_id):
    with open(ID_LOG_FILE, "a") as f:
        f.write(f"{p_id}\n")

def get_ali_products():
    """랜덤 카테고리에서 상품을 수집합니다."""
    cat_ids = ["3", "1501", "34", "66", "7", "44", "502", "1503", "1511", "18", "509", "26", "15", "2", "1524"]
    cat_id = random.choice(cat_ids)
    url = "https://api-sg.aliexpress.com/sync"
    params = {
        "app_key": ALI_APP_KEY, "timestamp": str(int(time.time() * 1000)), "sign_method": "sha256",
        "method": "aliexpress.affiliate.product.query", "category_ids": cat_id, 
        "page_size": "50", "target_currency": "USD", "target_language": "EN", "tracking_id": ALI_TRACKING_ID
    }
    params["sort"] = random.choice(["VOLUME_DESC", "SALE_PRICE_ASC", "SALE_PRICE_DESC"])
    sorted_params = sorted(params.items())
    base_string = "".join([f"{k}{v}" for k, v in sorted_params])
    sign = hmac.new(ALI_SECRET.encode('utf-8'), base_string.encode('utf-8'), hashlib.sha256).hexdigest().upper()
    params["sign"] = sign
    try:
        response = requests.post(url, data=params, timeout=20)
        return response.json().get("aliexpress_affiliate_product_query_response", {}).get("resp_result", {}).get("result", {}).get("products", {}).get("product", [])
    except: return []

def generate_blog_content(product):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    prompt = f"Write a professional 5-sentence review for: {product.get('product_title')}. Use Markdown."
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=40)
        res_json = response.json()
        if "candidates" in res_json:
            return res_json["candidates"][0]["content"]["parts"][0]["text"]
    except: pass
    return None

def update_seo_files():
    """모든 SEO 파일과 메인 index.md를 강제 갱신합니다."""
    print("🛠️ Starting SEO & Index update...")
    posts = sorted([f for f in os.listdir("_posts") if f.endswith(".md")], reverse=True)
    now_dt = datetime.now()
    now_str = now_dt.strftime("%Y-%m-%d")
    now_full = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    
    # 1. Sitemap.xml 생성 (XML 규격 준수)
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n'
    sitemap += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sitemap += f'  <url><loc>{SITE_URL}/</loc><lastmod>{now_str}</lastmod><priority>1.0</priority></url>\n'
    for p in posts:
        parts = p.replace(".md", "").split("-")
        if len(parts) >= 4:
            year, month, day = parts[0], parts[1], parts[2]
            title_id = "-".join(parts[3:])
            loc_url = f"{SITE_URL}/{year}/{month}/{day}/{title_id}.html"
            sitemap += f'  <url><loc>{loc_url}</loc><lastmod>{now_str}</lastmod></url>\n'
    sitemap += '</urlset>'
    with open("sitemap.xml", "w", encoding="utf-8") as f: f.write(sitemap.strip())

    # 2. robots.txt 생성
    robots = f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml"
    with open("robots.txt", "w", encoding="utf-8") as f: f.write(robots.strip())

    # 3. index.md 강제 업데이트 (타임스탬프 삽입)
    # 메인 페이지 목록이 꼬이지 않도록 Liquid 태그를 유지하며 날짜만 갱신합니다.
    index_content = f"""---
layout: default
title: Home
last_updated: "{now_full}"
---

# AliExpress Daily Must-Buy Items
*Last Updated: {now_full} (KST)*

<ul>
  {{% for post in site.posts %}}
    <li>
      <a href="{{{{ post.url | relative_url }}}}">{{{{ post.date | date: "%Y-%m-%d" }}}} - {{{{ post.title }}}}</a>
    </li>
  {{% endfor %}}
</ul>
"""
    with open("index.md", "w", encoding="utf-8") as f: f.write(index_content.strip())
    print(f"   ✅ SEO files and index.md updated at {now_full}")

def main():
    os.makedirs("_posts", exist_ok=True)
    today_str = datetime.now().strftime("%Y-%m-%d")
    posted_ids = load_posted_ids()
    success_count = 0
    max_posts = 10 
    disclosure = "> **Affiliate Disclosure:** As an AliExpress Associate, I earn from qualifying purchases.\n\n"

    print(f"🚀 Mission Start: {max_posts} Posts for {today_str}")

    while success_count < max_posts:
        products = get_ali_products()
        if not products: 
            time.sleep(10)
            continue
            
        for p in products:
            if success_count >= max_posts: break
            p_id = str(p.get('product_id'))
            if p_id in posted_ids: continue
            
            img_url = p.get('product_main_image_url', '').strip()
            if img_url.startswith('//'): img_url = 'https:' + img_url
            img_url = img_url.split('?')[0]

            content = generate_blog_content(p)
            if not content:
                content = (
                    "\n\n### Product Specifications\n\n"
                    "| Attribute | Detail |\n"
                    "| :--- | :--- |\n"
                    f"| **Item** | {p.get('product_title')} |\n"
                    f"| **Price** | ${p.get('target_sale_price')} |\n"
                    "| **Status** | Highly Recommended |\n\n"
                )

            file_path = f"_posts/{today_str}-{p_id}.md"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"---\nlayout: post\ntitle: \"{p['product_title']}\"\ndate: {today_str}\n---\n\n"
                        f"{disclosure}"
                        f"<img src=\"{img_url}\" alt=\"{p['product_title']}\" referrerpolicy=\"no-referrer\" style=\"width:100%; max-width:600px; display:block; margin:20px 0;\">\n\n"
                        f"{content}\n\n"
                        f"### [🛒 Shop Now on AliExpress]({p.get('promotion_link')})")
            
            save_posted_id(p_id)
            posted_ids.add(p_id)
            success_count += 1
            print(f"   ✅ SUCCESS ({success_count}/{max_posts}): {p_id}")
            time.sleep(6)

    update_seo_files()
    print(f"🏁 Mission Completed!")

if __name__ == "__main__":
    main()
