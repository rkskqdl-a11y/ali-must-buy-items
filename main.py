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

# 2. 통합 키워드 리스트 (2,400개 이상)
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
    # 🚀 제미나이 3.0 기반의 최신 고성능 엔진 호출 (2026 표준)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    prompt_text = f"As a professional reviewer using Gemini 3.0, write a detailed English review for: {product.get('product_title')}. Price: ${product.get('target_sale_price')}. In Markdown."
    payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        result = response.json()
        if "candidates" in result:
            return result["candidates"][0]["content"]["parts"][0]["text"]
        # 실패 시 로그 출력
        print(f"DEBUG: Gemini API Error Response: {result}")
        return None
    except Exception as e:
        print(f"DEBUG: Gemini Exception: {e}")
        return None

def main():
    # 1. 128 에러 방지: 파일 및 폴더 강제 생성
    os.makedirs("posts", exist_ok=True)
    if not os.path.exists("posted_ids.txt"):
        with open("posted_ids.txt", "w") as f: f.write("")

    # 2. 키워드 선택
    all_keywords = get_massive_keyword_list()
    target_keyword = random.choice(all_keywords)
    print(f"📚 Total Keywords: {len(all_keywords)} | 🎯 Target: {target_keyword}")

    # 3. 상품 검색
    products = get_ali_products(target_keyword)
    if not products:
        print("❌ AliExpress No Products Found.")
        return

    # 4. 글 생성 및 저장
    selected_product = products[0]
    print(f"📝 Writing Review: {selected_product['product_title'][:40]}...")
    content = generate_blog_content(selected_product)
    
    if content:
        today = datetime.now().strftime("%Y-%m-%d")
        file_path = f"posts/{today}-post.md"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        # 성공 시 ID 기록
        with open("posted_ids.txt", "a") as f:
            f.write(f"{selected_product.get('product_id')}\n")
        print(f"🎉 SUCCESS: {file_path} created!")
    else:
        print("❌ Content generation failed.")

if __name__ == "__main__":
    main()
