import os
import time
import random
import hmac
import hashlib
import requests
import json
from datetime import datetime

# 1. 환경 변수 설정 (GitHub Secrets 기반)
ALI_APP_KEY = os.environ.get("ALI_APP_KEY", "").strip()
ALI_SECRET = os.environ.get("ALI_SECRET", "").strip()
ALI_TRACKING_ID = os.environ.get("ALI_TRACKING_ID", "").strip()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

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
        # ✅ 제품 리스트 경로 수정
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
        # ✅ Gemini JSON 응답 경로 수정
        if "candidates" in res_json:
            return res_json["candidates"][0]["content"]["parts"][0]["text"]
        if "quota" in str(res_json).lower() or "429" in str(res_json):
            print("   ⏳ API Quota full. Resting 70s...")
            time.sleep(70)
    except: pass
    return None

def main():
    os.makedirs("_posts", exist_ok=True)
    today_str = datetime.now().strftime("%Y-%m-%d")
    posted_ids = load_posted_ids()
    success_count = 0
    max_posts = 40 
    
    # ✅ 영문 고지 문구
    disclosure = "> **Affiliate Disclosure:** As an AliExpress Associate, I earn from qualifying purchases. This post contains affiliate links.\n\n"

    print(f"🚀 Mission: {max_posts} Posts Start")

    while success_count < max_posts:
        products = get_ali_products()
        if not products: 
            print("⚠️ No products found, retrying...")
            time.sleep(10)
            continue
            
        for p in products:
            if success_count >= max_posts: break
            p_id = str(p.get('product_id'))
            if p_id in posted_ids: continue
            
            # ✅ 이미지 URL 문자열 처리 수정
            img_url = p.get('product_main_image_url', '').strip()
            if img_url.startswith('//'): img_url = 'https:' + img_url
            img_url = img_url.split('?')[0] # [0] 인덱스 추가

            content = generate_blog_content(p)
            
            # ✅ 본문 표 형식(Box) 보장
            if not content:
                content = (
                    f"### Product Specifications\n\n"
                    f"| Attribute | Detail |\n"
                    f"| :--- | :--- |\n"
                    f"| **Item** | {p.get('product_title')} |\n"
                    f"| **Price** | ${p.get('target_sale_price')} |\n"
                    f"| **Status** | Highly Recommended |\n"
                )

            file_path = f"_posts/{today_str}-{p_id}.md"
            with open(file_path, "w", encoding="utf-8") as f:
                # ✅ 제목은 깔끔하게 텍스트로
                f.write(f"---\nlayout: post\ntitle: \"{p['product_title']}\"\ndate: {today_str}\n---\n\n"
                        f"{disclosure}"
                        f"<img src=\"{img_url}\" alt=\"{p['product_title']}\" referrerpolicy=\"no-referrer\" style=\"width:100%; max-width:600px; display:block; margin:20px 0;\">\n\n"
                        f"{content}\n\n"
                        f"### [🛒 Shop Now on AliExpress]({p.get('promotion_link')})") # ✅ 링크 형식 수정
            
            save_posted_id(p_id)
            posted_ids.add(p_id)
            success_count += 1
            print(f"   ✅ SUCCESS ({success_count}/{max_posts}): {p_id}")
            time.sleep(6)

    print(f"🏁 Mission Completed!")

if __name__ == "__main__":
    main()
