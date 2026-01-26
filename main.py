import os
import time
import random
import hmac
import hashlib
import requests
import json
from datetime import datetime

# 1. 환경 변수 설정
ALI_APP_KEY = os.environ.get("ALI_APP_KEY", "").strip()
ALI_SECRET = os.environ.get("ALI_SECRET", "").strip()
ALI_TRACKING_ID = os.environ.get("ALI_TRACKING_ID", "").strip()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

def get_ali_products():
    # 🎯 검색 범위를 더 넓혀 상품 고갈을 완전히 방지합니다.
    cat_ids = ["502", "44", "7", "509", "1501", "1503", "18", "1511", "200003406"]
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
    # ⚡ 제미나이 1.5 플래시: 가장 빠르고 안정적인 모델
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    prompt = f"Write a catchy 5-sentence expert review for: {product.get('product_title')}. Price: ${product.get('target_sale_price')}. Use Markdown."
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=40)
        res_json = response.json()
        if "candidates" in res_json:
            return res_json["candidates"][0]["content"]["parts"][0]["text"]
        if "quota" in str(res_json).lower() or "429" in str(res_json):
            print("   ⏳ API Quota limit. Waiting 60s...")
            time.sleep(60)
    except: pass
    return None

def main():
    os.makedirs("_posts", exist_ok=True)
    today_str = datetime.now().strftime("%Y-%m-%d")
    current_session_ids = set()
    success_count = 0
    
    # ✅ 영문 대가성 문구 (글로벌 수익형 블로그 표준)
    # 필요시 한글 문구를 아래에 추가하셔도 됩니다.
    disclosure_text = "> **Affiliate Disclosure:** As an AliExpress Associate, I earn from qualifying purchases. This post contains affiliate links, meaning I may receive a small commission at no extra cost to you.\n\n"

    print(f"🚀 Mission: 40 Posts (Image Optimization & English Disclosure)")

    while success_count < 40:
        products = get_ali_products()
        if not products: continue
            
        for p in products:
            if success_count >= 40: break
            p_id = str(p.get('product_id'))
            if p_id in current_session_ids: continue
            
            # 🖼️ 이미지 URL 3중 보안 가공 (엑박 방지 핵심)
            img_raw = p.get('product_main_image_url', '').strip()
            if not img_raw: continue
            
            # 1. 프로토콜 보정
            if img_raw.startswith('//'): img_url = 'https:' + img_raw
            elif not img_raw.startswith('http'): img_url = 'https://' + img_raw
            else: img_url = img_raw
            
            # 2. 불필요한 쿼리 파라미터 및 리사이징 옵션 제거 (원본 화질 확보)
            img_url = img_url.split('?')[0].split('_')[0]
            if not img_url.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                img_url += ".jpg" # 확장자가 없는 경우 강제 부여

            content = generate_blog_content(p)
            if not content:
                content = f"Featured Deal: {p.get('product_title')} is now available on AliExpress for only ${p.get('target_sale_price')}!"

            file_path = f"_posts/{today_str}-{p_id}.md"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"---\nlayout: post\ntitle: \"{p['product_title']}\"\ndate: {today_str}\n---\n\n"
                        f"{disclosure_text}" # 영문 고지 문구
                        f"![{p['product_title']}]({img_url})\n\n" # 이미지 출력
                        f"{content}\n\n"
                        f"### [🛒 View Deal on AliExpress]({p.get('promotion_link')})")
            
            current_session_ids.add(p_id)
            success_count += 1
            print(f"   ✅ SUCCESS ({success_count}/40): {p_id}")
            time.sleep(5) # API 안정성을 위한 매너 대기

    print(f"🏁 Mission Completed: 40 professional posts created.")

if __name__ == "__main__":
    main()
