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
# 💎 사이트 주소 끝에 '/'가 없는지 확인하세요.
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
    """다양한 카테고리와 정렬 방식을 랜덤하게 선택하여 상품을 수집합니다."""
    cat_ids = ["3", "1501", "34", "66", "7", "44", "502", "1503", "1511", "18", "509", "200000343", "200000345", "200000532", "26", "15", "2", "1524", "21", "13"]
    cat_id = random.choice(cat_ids)
    
    url = "https://api-sg.aliexpress.com/sync"
    params = {
        "app_key": ALI_APP_KEY,
        "timestamp": str(int(time.time() * 1000)),
        "sign_method": "sha256",
        "method": "aliexpress.affiliate.product.query",
        "category_ids": cat_id,
        "page_size": "50",
        "target_currency": "USD",
        "target_language": "EN",
        "tracking_id": ALI_TRACKING_ID
    }
    sort_options = ["VOLUME_DESC", "SALE_PRICE_ASC", "SALE_PRICE_DESC", "LAST_VOLUME_ASC"]
    params["sort"] = random.choice(sort_options)

    # 💎 서명 생성 (AliExpress API 필수 규격)
    sorted_params = sorted(params.items())
    base_string = "".join([f"{k}{v}" for k, v in sorted_params])
    sign = hmac.new(ALI_SECRET.encode('utf-8'), base_string.encode('utf-8'), hashlib.sha256).hexdigest().upper()
    params["sign"] = sign
    
    try:
        response = requests.post(url, data=params, timeout=20)
        # 💎 안전한 JSON 파싱
        res_json = response.json()
        return res_json.get("aliexpress_affiliate_product_query_response", {}).get("resp_result", {}).get("result", {}).get("products", {}).get("product", [])
    except Exception as e:
        print(f"❌ Ali API Error: {e}")
        return []

def generate_blog_content(product):
    """💎 1,000자 이상의 장문 리뷰를 작성하도록 프롬프트를 대폭 강화했습니다."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    title = product.get('product_title')
    price = product.get('target_sale_price')
    
    # 🤖 AI를 압박하는 구체적인 장문 지시서
    prompt = f"""
    Write a detailed professional product review column for: "{title}". 
    The product price is ${price}.
    
    [Requirements]
    1. Language: English
    2. Length: Minimum 1,000 characters.
    3. Style: Expert tech/lifestyle blogger.
    4. Structure: Use the following H3 sections:
       - ### 🔍 Professional Overview & Design
       - ### 🚀 Performance & Real-world Testing
       - ### 💡 Why We Recommend This Item
       - ### 💰 Value Analysis & Final Verdict
    5. Formatting: Use Markdown (bold, bullet points) for readability.
    6. Content: Do NOT mention "discount rate" or "sale". Focus on quality and value.
    """
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": [{"category": c, "threshold": "BLOCK_NONE"} for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
    }
    
    try:
        response = requests.post(url, json=payload, timeout=45)
        res_json = response.json()
        
        # 💎 안전한 AI 응답 추출 (리스트 인덱스 [0] 필수)
        if "candidates" in res_json and len(res_json["candidates"]) > 0:
            candidate = res_json["candidates"][0]
            if "content" in candidate:
                return candidate["content"]["parts"][0]["text"].strip()
        
        if "429" in str(res_json):
            print("⏳ Quota limit reached. Resting...")
            time.sleep(70)
    except Exception as e:
        print(f"❌ Gemini Error: {e}")
    return None

def update_seo_files():
    """💎 사이트맵의 첫 줄 공백 문제를 원천 차단했습니다."""
    posts = sorted([f for f in os.listdir("_posts") if f.endswith(".md")], reverse=True)
    now = datetime.now().strftime("%Y-%m-%d")
    
    # 💎 중요: 문자열 시작 시 공백이나 줄바꿈이 절대 없어야 합니다.
    sitemap_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    sitemap_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sitemap_content += f'  <url><loc>{SITE_URL}/</loc><lastmod>{now}</lastmod><priority>1.0</priority></url>\n'
    
    for p in posts:
        # 파일명 형식: 2026-01-29-12345.md -> URL 형식: /2026/01/29/12345.html
        name_parts = p.replace(".md", "").split("-")
        if len(name_parts) >= 4:
            year, month, day = name_parts[0], name_parts[1], name_parts[2]
            title_id = "-".join(name_parts[3:])
            loc_url = f"{SITE_URL}/{year}/{month}/{day}/{title_id}.html"
            sitemap_content += f'  <url><loc>{loc_url}</loc><lastmod>{now}</lastmod></url>\n'
    
    sitemap_content += '</urlset>'
    
    # 💎 파일 쓰기 (strip()으로 혹시 모를 앞뒤 공백 제거)
    with open("sitemap.xml", "w", encoding="utf-8") as f:
        f.write(sitemap_content.strip())
        
    with open("robots.txt", "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml")

def main():
    os.makedirs("_posts", exist_ok=True)
    today_str = datetime.now().strftime("%Y-%m-%d")
    posted_ids = load_posted_ids()
    success_count = 0
    max_posts = 10 
    disclosure = "> **Affiliate Disclosure:** As an AliExpress Associate, I earn from qualifying purchases.\n\n"

    print(f"🚀 Mission Start: Generating {max_posts} Posts for {today_str}")

    while success_count < max_posts:
        products = get_ali_products()
        if not products: 
            print("⚠️ No products found. Retrying in 10s...")
            time.sleep(10)
            continue
            
        for p in products:
            if success_count >= max_posts: break
            p_id = str(p.get('product_id'))
            if p_id in posted_ids: continue
            
            img_url = p.get('product_main_image_url', '').strip()
            if img_url.startswith('//'): img_url = 'https:' + img_url
            img_url = img_url.split('?')[0] # 💎 깨끗한 이미지 주소 추출

            print(f"📝 Analyzing: {p_id}...")
            content = generate_blog_content(p)
            
            # AI 생성 실패 시 기본 테이블로 대체
            if not content:
                content = (
                    "### Product Technical Specs\n\n"
                    "| Attribute | Description |\n"
                    "| :--- | :--- |\n"
                    f"| **Product** | {p.get('product_title')} |\n"
                    f"| **Price** | ${p.get('target_sale_price')} |\n"
                    "| **Evaluation** | Expert Choice |\n"
                )

            # Jekyll 포스트 생성
            file_path = f"_posts/{today_str}-{p_id}.md"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"---\nlayout: post\ntitle: \"{p['product_title']}\"\ndate: {today_str}\n---\n\n"
                        f"{disclosure}"
                        f"<img src=\"{img_url}\" alt=\"{p['product_title']}\" referrerpolicy=\"no-referrer\" style=\"width:100%; max-width:600px; display:block; margin:20px 0;\">\n\n"
                        f"{content}\n\n"
                        f"### [🛒 View Details on AliExpress]({p.get('promotion_link')})")
            
            save_posted_id(p_id)
            posted_ids.add(p_id)
            success_count += 1
            print(f"   ✅ COMPLETED ({success_count}/{max_posts}): {p_id}")
            time.sleep(8) # RPM 제한을 고려한 안정적인 대기 시간

    update_seo_files()
    print(f"🏁 Mission Completed & SEO Files Synchronized!")

if __name__ == "__main__":
    main()
