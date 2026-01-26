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

def get_ali_products(keyword):
    url = "https://api-sg.aliexpress.com/sync"
    params = {
        "app_key": ALI_APP_KEY, "timestamp": str(int(time.time() * 1000)), "sign_method": "sha256",
        "method": "aliexpress.affiliate.product.query", "keywords": keyword, "page_size": "50",
        "target_currency": "USD", "target_language": "EN", "tracking_id": ALI_TRACKING_ID
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
    # ✅ 가장 성공률이 높았던 3.0 Flash 모델을 고정 사용합니다.
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    prompt = f"Review this item professionally: {product.get('product_title')}. Price: ${product.get('target_sale_price')}. Use Markdown."
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=40)
        res_json = response.json()
        
        if "candidates" in res_json:
            return res_json["candidates"][0]["content"]["parts"][0]["text"]
        
        # 🔍 실패 원인을 구체적으로 출력하여 대응합니다.
        error_msg = res_json.get("error", {}).get("message", "Unknown Error")
        print(f"   ⚠️ AI Issue: {error_msg}")
        
        # 할당량 초과(Quota) 시 10초 대기
        if "quota" in error_msg.lower() or "429" in str(res_json):
            print("   ⏳ Rate limit hit. Cooling down for 10 seconds...")
            time.sleep(10)
            
    except Exception as e:
        print(f"   ⚠️ Connection Error: {e}")
    return None

def main():
    os.makedirs("_posts", exist_ok=True)
    today_str = datetime.now().strftime("%Y-%m-%d")
    current_session_ids = set()
    success_count = 0
    
    # 🎯 무조건 40개를 채우기 위한 키워드 뱅크
    keywords = ["Smart Gadget", "Tech Essentials", "Home Electronics", "New Trend", "Best Seller"]
    random.shuffle(keywords)

    print(f"🚀 Mission: Create 40 Posts (Super Stable Mode)")

    while success_count < 40:
        for kw in keywords:
            if success_count >= 40: break
            
            print(f"🔍 Searching: {kw} (Progress: {success_count}/40)")
            products = get_ali_products(kw)
            if not products: continue
            
            for p in products:
                if success_count >= 40: break
                
                p_id = str(p.get('product_id'))
                if p_id in current_session_ids: continue
                
                content = generate_blog_content(p)
                if content:
                    # 🖼️ 이미지 엑박(Broken) 완벽 해결 로직
                    img_url = p.get('product_main_image_url', '')
                    if img_url.startswith('//'): img_url = 'https:' + img_url
                    
                    file_path = f"_posts/{today_str}-{p_id}.md"
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(f"---\nlayout: post\ntitle: \"{p['product_title']}\"\ndate: {today_str}\n---\n\n![Image]({img_url})\n\n{content}\n\n[🛒 Buy Link]({p.get('promotion_link')})")
                    
                    current_session_ids.add(p_id)
                    success_count += 1
                    print(f"   ✅ SUCCESS ({success_count}/40): {p_id}")
                    time.sleep(3) # ⚡ 안정적인 생성을 위해 3초 대기
                else:
                    # AI 생성 실패 시 5초 쉬고 다음 상품 시도
                    time.sleep(5)

    print(f"🏁 Mission Completed: 40 posts created!")

if __name__ == "__main__":
    main()
