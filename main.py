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

def get_massive_keyword_list():
    modifiers = ["Best Budget", "Top Rated", "High Quality", "Portable", "Wireless", "Gaming", "RGB", "Mechanical", "Waterproof", "Smart", "Minimalist", "Professional", "Gift for Him", "Gift for Her", "Trending", "Xiaomi", "Anker Style", "Must Have"]
    products = ["Mechanical Keyboard", "Gaming Mouse", "Power Bank", "USB Hub", "GaN Charger", "Monitor Light Bar", "Tablet Stand", "Laptop Stand", "Bluetooth Speaker", "TWS Earbuds", "Smart Watch", "NVMe SSD Enclosure", "Mini PC", "Portable Projector", "Robot Vacuum", "Electric Toothbrush", "Smart Scale", "Portable Monitor", "Action Camera", "Dash Cam", "Car Vacuum", "Camping Lantern", "Survival Kit", "Multitool", "Pocket Knife"]
    return [f"{m} {p}" for m in modifiers for p in products]

def get_ali_products(keyword):
    url = "https://api-sg.aliexpress.com/sync"
    params = {
        "app_key": ALI_APP_KEY, "timestamp": str(int(time.time() * 1000)), "sign_method": "sha256",
        "method": "aliexpress.affiliate.product.query", "partner_id": "apidoc", "keywords": keyword,
        "target_currency": "USD", "target_language": "EN", "tracking_id": ALI_TRACKING_ID, "page_size": "5"
    }
    sorted_params = sorted(params.items())
    base_string = "".join([f"{k}{v}" for k, v in sorted_params])
    sign = hmac.new(ALI_SECRET.encode('utf-8'), base_string.encode('utf-8'), hashlib.sha256).hexdigest().upper()
    params["sign"] = sign
    try:
        response = requests.post(url, data=params)
        return response.json().get("aliexpress_affiliate_product_query_response", {}).get("resp_result", {}).get("result", {}).get("products", {}).get("product", [])
    except: return []

def generate_blog_content(product):
    # 🚀 429 에러 해결을 위해 가장 안정적인 'gemini-1.5-flash' 모델로 변경
    # 이 모델은 무료 티어에서도 분당 15회 요청을 안정적으로 제공합니다.
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    prompt_text = f"Review this product in professional English: {product.get('product_title')}. Price: ${product.get('target_sale_price')}. In Markdown."
    payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        result = response.json()
        
        if "candidates" in result:
            return result["candidates"][0]["content"]["parts"][0]["text"]
        
        # 할당량 초과(429) 에러 처리
        if result.get("error", {}).get("code") == 429:
            print("⚠️ API 할당량 초과: 무료 티어 제한에 걸렸습니다. 잠시 후 다시 시도하거나 모델 설정을 확인하세요.")
        else:
            print(f"DEBUG: Gemini API Error: {result.get('error', {}).get('message')}")
        return None
    except Exception as e:
        print(f"DEBUG: Gemini Exception: {e}")
        return None

def main():
    os.makedirs("posts", exist_ok=True)
    if not os.path.exists("posted_ids.txt"):
        with open("posted_ids.txt", "w") as f: f.write("")

    all_keywords = get_massive_keyword_list()
    target_keyword = random.choice(all_keywords)
    print(f"📚 Total Keywords: {len(all_keywords)} | 🎯 Target: {target_keyword}")

    products = get_ali_products(target_keyword)
    if not products:
        print("❌ AliExpress No Products Found.")
        return

    selected_product = products[0]
    print(f"📝 Writing Review: {selected_product['product_title'][:40]}...")
    content = generate_blog_content(selected_product)
    
    if content:
        today = datetime.now().strftime("%Y-%m-%d")
        # 파일명에 날짜와 상품 ID를 조합해 중복 방지
        file_path = f"posts/{today}-{selected_product.get('product_id')}.md"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        with open("posted_ids.txt", "a") as f:
            f.write(f"{selected_product.get('product_id')}\n")
        print(f"🎉 SUCCESS: {file_path} created!")
    else:
        print("❌ Content generation failed. Skip saving file.")

if __name__ == "__main__":
    main()
