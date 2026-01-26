import os
import time
import random
import hmac
import hashlib
import requests
import json
from datetime import datetime

# [환경 변수 설정 - 사용자 정보 기반]
ALI_APP_KEY = os.environ.get("ALI_APP_KEY", "").strip()
ALI_SECRET = os.environ.get("ALI_SECRET", "").strip()
ALI_TRACKING_ID = os.environ.get("ALI_TRACKING_ID", "").strip()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

def get_ali_products():
    # 🎯 상품을 확실히 가져오기 위해 카테고리 범위를 넓혔습니다.
    cat_id = random.choice(["502", "44", "7", "509", "1501", "1503", "18"])
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
    # 🎯 속도와 안정성이 검증된 1.5 Flash 모델 사용
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    prompt = f"Write a detailed, high-quality review for: {product.get('product_title')}. Highlight 3 pros. Price is ${product.get('target_sale_price')}. Use Markdown."
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=40)
        res_json = response.json()
        if "candidates" in res_json:
            return res_json["candidates"][0]["content"]["parts"][0]["text"]
        # 🚨 할당량 초과 시 1분 대기 (어제 약속드린 설정)
        if "quota" in str(res_json).lower() or "429" in str(res_json):
            print("   ⏳ API Quota full. Waiting 60s...")
            time.sleep(60)
    except: pass
    return None

def main():
    os.makedirs("_posts", exist_ok=True)
    today_str = datetime.now().strftime("%Y-%m-%d")
    current_session_ids = set()
    success_count = 0
    
    print(f"🚀 Mission: 40 Posts (Image & Content Fix Mode)")

    while success_count < 40:
        products = get_ali_products()
        if not products: continue
            
        for p in products:
            if success_count >= 40: break
            p_id = str(p.get('product_id'))
            if p_id in current_session_ids: continue
            
            # 🖼️ 이미지 URL 완벽 교정
            img_url = p.get('product_main_image_url', '')
            if img_url.startswith('//'):
                img_url = 'https:' + img_url
            elif not img_url.startswith('http'):
                img_url = 'https://' + img_url

            content = generate_blog_content(p)
            
            # ✅ AI 실패 시에도 상품 정보를 최대한 활용하여 글을 채웁니다.
            if not content:
                print(f"   ⚠️ AI generation failed for {p_id}. Using Rich Fallback.")
                content = (f"### Product Details\n- **Item**: {p.get('product_title')}\n"
                           f"- **Price**: ${p.get('target_sale_price')}\n"
                           f"- **Status**: Highly Recommended\n\n"
                           f"Don't miss this amazing deal on AliExpress! Professional grade quality at an affordable price.")
            
            file_path = f"_posts/{today_str}-{p_id}.md"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"---\nlayout: post\ntitle: \"{p['product_title']}\"\ndate: {today_str}\n---\n\n"
                        f"![Product Image]({img_url})\n\n" # 이미지 삽입
                        f"{content}\n\n"
                        f"### [🛒 Buy on AliExpress]({p.get('promotion_link')})") # 구매 버튼
            
            current_session_ids.add(p_id)
            success_count += 1
            print(f"   ✅ SUCCESS ({success_count}/40): {p_id}")
            time.sleep(5) # ⚡ API 보호를 위한 여유 시간

    print(f"🏁 Mission Completed: 40 posts.")

if __name__ == "__main__":
    main()
