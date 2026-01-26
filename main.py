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

# 2. 핵폭탄급 키워드 생성기 (조합수 수천 개 이상)
def get_explosive_keyword_bank():
    # 형용사/수식어
    modifiers = [
        "Best", "Top Rated", "Smart", "Portable", "Wireless", "Mini", "Professional", "Luxury", "Budget", 
        "2026 New", "Trending", "Must-have", "Minimalist", "High-tech", "Ergonomic", "Xiaomi Style", 
        "Eco-friendly", "Outdoor", "Home", "Office", "Gaming", "Travel", "Essential", "Unique"
    ]
    # 메인 카테고리
    categories = [
        "Electronics", "Gadgets", "Home Improvement", "Kitchen Tools", "Car Accessories", "Pet Supplies", 
        "Beauty & Care", "Sports Gear", "Security Systems", "Office Supplies", "Outdoor Tools", "Audio", 
        "Lighting", "Mobile Access", "Computer Parts", "Health Tech", "DIY Projects", "Photography", 
        "Garden Tools", "Smart Wearables", "Cleaning Tools", "Camping Gear", "Survival Kits"
    ]
    # 세부 아이템
    items = [
        "Keyboard", "Mouse", "Power Bank", "Charger", "Adapter", "Sensor", "Camera", "Projector", "Fan", 
        "Vacuum", "Scale", "Speaker", "Earbuds", "Hub", "Monitor", "Light", "Clock", "Massager", 
        "Drone", "Gimbal", "Microphone", "Router", "Display", "Controller", "Tracker", "Lamp"
    ]
    
    # 💥 무작위 조합 생성
    keyword_list = []
    for m in modifiers:
        for c in categories:
            for i in items:
                keyword_list.append(f"{m} {c} {i}")
    return keyword_list

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
    # 🎯 AI가 거절하지 않도록 프롬프트 최적화
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    prompt = f"Write a catchy 5-sentence review for: {product.get('product_title')}. Price: ${product.get('target_sale_price')}. Use Markdown."
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=40)
        res_json = response.json()
        
        if "candidates" in res_json:
            return res_json["candidates"][0]["content"]["parts"][0]["text"]
        
        # 🚨 할당량 초과 시 60초 휴식 모드
        if "quota" in str(res_json).lower() or "429" in str(res_json):
            print("   🚨 Rate Limit Hit! Sleeping for 60 seconds...")
            time.sleep(60)
            
    except Exception as e:
        print(f"   ⚠️ AI Error: {e}")
    return None

def main():
    os.makedirs("_posts", exist_ok=True)
    today_str = datetime.now().strftime("%Y-%m-%d")
    current_session_ids = set()
    success_count = 0
    
    # 💥 폭탄급 키워드 로드 및 섞기
    keywords = get_explosive_keyword_bank()
    random.shuffle(keywords)

    print(f"🚀 Mission: 무조건 40개 발행 (키워드 {len(keywords)}개 대기 중)")

    while success_count < 40:
        for kw in keywords:
            if success_count >= 40: break
            
            print(f"🔍 Searching: {kw} (Progress: {success_count}/40)")
            products = get_ali_products(kw)
            if not products: continue
            
            for p in products:
                if success_count >= 40: break
                p_id = str(p.get('product_id'))
                
                # 중복 방지는 오늘 세션 내에서만 최소화
                if p_id in current_session_ids: continue
                
                content = generate_blog_content(p)
                if content:
                    # 🖼️ 이미지 URL 자동 교정
                    img_url = p.get('product_main_image_url', '')
                    if img_url.startswith('//'): img_url = 'https:' + img_url
                    
                    file_path = f"_posts/{today_str}-{p_id}.md"
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(f"---\nlayout: post\ntitle: \"{p['product_title']}\"\ndate: {today_str}\n---\n\n![Image]({img_url})\n\n{content}\n\n[🛒 AliExpress Link]({p.get('promotion_link')})")
                    
                    current_session_ids.add(p_id)
                    success_count += 1
                    print(f"   ✅ SUCCESS ({success_count}/40): {p_id}")
                    # 안정적인 호출을 위해 5초 대기
                    time.sleep(5) 
                else:
                    time.sleep(2)

    print(f"🏁 Mission Completed: 40 posts created!")

if __name__ == "__main__":
    main()
