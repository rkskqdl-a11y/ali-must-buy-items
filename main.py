import os
import time
import random
import hmac
import hashlib
import requests
import json
from datetime import datetime

# 1. 환경 변수 및 사이트 정보 설정
ALI_APP_KEY = os.environ.get("ALI_APP_KEY", "").strip()
ALI_SECRET = os.environ.get("ALI_SECRET", "").strip() # YAML에서 ALI_APP_SECRET을 매핑해줍니다.
ALI_TRACKING_ID = os.environ.get("ALI_TRACKING_ID", "").strip()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
# 실제 GitHub Pages 주소 (Jekyll 블로그 주소)
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
    """알리익스프레스 API를 통해 상품 정보를 수집합니다."""
    cat_ids = ["502", "44", "7", "509", "1501", "1503", "18", "1511"]
    cat_id = random.choice(cat_ids)
    url = "https://api-sg.aliexpress.com/sync"
    params = {
        "app_key": ALI_APP_KEY, "timestamp": str(int(time.time() * 1000)), "sign_method": "sha256",
        "method": "aliexpress.affiliate.product.query", "category_ids": cat_id, 
        "page_size": "50", "target_currency": "USD", "target_language": "EN", "tracking_id": ALI_TRACKING_ID
    }
    sorted_params = sorted(params.items())
    base_string = "".join([f"{k}{v}" for k, v in sorted_params])
    sign = hmac.new(ALI_SECRET.encode('utf-8'), base_string.encode('utf-8'), hashlib.sha256).hexdigest().upper()
    params["sign"] = sign
    try:
        response = requests.post(url, data=params, timeout=20)
        return response.json().get("aliexpress_affiliate_product_query_response", {}).get("resp_result", {}).get("result", {}).get("products", {}).get("product", [])
    except: return []

def generate_blog_content(product):
    """제미나이를 사용하여 고품질 리뷰를 생성하고 할당량을 관리합니다."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    prompt = f"Write a professional 5-sentence review for: {product.get('product_title')}. Use Markdown."
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=40)
        res_json = response.json()
        if "candidates" in res_json:
            return res_json["candidates"][0]["content"]["parts"][0]["text"]
        # API 할당량 초과 시 대기 로직
        if "quota" in str(res_json).lower() or "429" in str(res_json):
            print("   ⏳ API Quota limit. Resting 70s...")
            time.sleep(70)
    except: pass
    return None

def update_seo_files():
    """구글이 인덱스를 생성할 수 있도록 폴더 구조에 맞춘 사이트맵을 만듭니다."""
    posts = sorted([f for f in os.listdir("_posts") if f.endswith(".md")], reverse=True)
    now = datetime.now().strftime("%Y-%m-%d")
    
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sitemap += f'  <url><loc>{SITE_URL}/</loc><lastmod>{now}</lastmod><priority>1.0</priority></url>\n'
    
    for p in posts:
        # 파일명(2026-01-28-ID.md) -> Jekyll 주소(/2026/01/28/ID.html) 변환
        name_parts = p.replace(".md", "").split("-")
        if len(name_parts) >= 4:
            year, month, day = name_parts[0], name_parts[1], name_parts[2]
            title_id = "-".join(name_parts[3:])
            loc_url = f"{SITE_URL}/{year}/{month}/{day}/{title_id}.html"
            sitemap += f'  <url><loc>{loc_url}</loc><lastmod>{now}</lastmod></url>\n'
            
    sitemap += '</urlset>'
    with open("sitemap.xml", "w", encoding="utf-8") as f: f.write(sitemap)
    # robots.txt 최신화
    with open("robots.txt", "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml")

def main():
    os.makedirs("_posts", exist_ok=True)
    today_str = datetime.now().strftime("%Y-%m-%d")
    posted_ids = load_posted_ids()
    success_count = 0
    max_posts = 10 # 한 번에 발행할 수량
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
            
            # 이미지 엑박 방지 로직
            img_url = p.get('product_main_image_url', '').strip()
            if img_url.startswith('//'): img_url = 'https:' + img_url
            img_url = img_url.split('?')[0]

            content = generate_blog_content(p)
            
            # [표 깨짐 방지] 삼중 따옴표와 빈 줄 보장
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
            time.sleep(6) # RPM 관리

    update_seo_files() # 모든 글 생성 후 사이트맵 갱신
    print(f"🏁 Mission Completed & SEO Files Updated!")

if __name__ == "__main__":
    main()
