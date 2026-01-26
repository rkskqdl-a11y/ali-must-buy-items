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

def get_huge_categories():
    # 상품이 마를 날이 없도록 가장 큰 카테고리들만 모았습니다.
    return [
        "Electronics", "Home Improvement", "Computer & Office", "Home Appliances", 
        "Automobiles", "Security & Protection", "Tools", "Consumer Electronics",
        "Phones & Accessories", "Office & School Supplies", "Lights & Lighting"
    ]

def get_ali_products(category):
    url = "https://api-sg.aliexpress.com/sync"
    params = {
        "app_key": ALI_APP_KEY, "timestamp": str(int(time.time() * 1000)), "sign_method": "sha256",
        "method": "aliexpress.affiliate.product.query", "partner_id": "apidoc", 
        "keywords": category, "page_size": "50", # 🎯 한 번에 50개씩 대량으로 가져옴
        "sort": "SALE_PRICE_ASC", # 가격순 정렬로 다양한 상품 노출
        "target_currency": "USD", "target_language": "EN", "tracking_id": ALI_TRACKING_ID
    }
    sorted_params = sorted(params.items())
    base_string = "".join([f"{k}{v}" for k, v in sorted_params])
    sign = hmac.new(ALI_SECRET.encode('utf-8'), base_string.encode('utf-8'), hashlib.sha256).hexdigest().upper()
    params["sign"] = sign
    try:
        response = requests.post(url, data=params, timeout=30)
        return response.json().get("aliexpress_affiliate_product_query_response", {}).get("resp_result", {}).get("result", {}).get("products", {}).get("product", [])
    except: return []

def generate_blog_content(product):
    # 제미나이 3.0의 지능을 사용하여 빠르게 리뷰 생성
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    # ✍️ SEO를 고려하되, 생성을 빠르게 하기 위해 프롬프트를 간소화했습니다.
    prompt = f"Create a viral marketing review for: {product.get('product_title')}. Price: ${product.get('target_sale_price')}. Use Markdown."
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except: return None

def main():
    os.makedirs("_posts", exist_ok=True)
    # 🎯 SEO를 위해 '오늘 이미 올린 것'만 중복 검사하도록 완화
    posted_ids = set()
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    success_count = 0
    categories = get_huge_categories()
    random.shuffle(categories)
    
    for cat in categories:
        if success_count >= 40: break
        print(f"🚀 Category: {cat} (Goal: 40, Current: {success_count})")
        
        products = get_ali_products(cat)
        if not products: continue
        
        for p in products:
            if success_count >= 40: break
            
            p_id = str(p.get('product_id'))
            # 🛑 같은 날 중복 발행만 막습니다.
            if p_id in posted_ids: continue
            
            content = generate_blog_content(p)
            if content:
                # 🖼️ 이미지 주소 자동 교정
                img_url = p.get('product_main_image_url', '')
                if img_url.startswith('//'): img_url = 'https:' + img_url
                
                # 📝 파일 생성
                file_path = f"_posts/{today_str}-{p_id}.md"
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(f"---\nlayout: post\ntitle: \"{p['product_title']}\"\ndate: {today_str}\n---\n\n![Image]({img_url})\n\n{content}\n\n[🛒 Buy on AliExpress]({p.get('promotion_link')})")
                
                posted_ids.add(p_id)
                success_count += 1
                print(f"✅ Success {success_count}/40: {p_id}")
                time.sleep(1) # ⚡ 제미나이 프로의 속도를 믿고 대기시간 최소화
                
    print(f"🏁 Mission Completed: {success_count} posts created today!")

if __name__ == "__main__":
    main()
