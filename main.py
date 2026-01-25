import os
import time
import random
import hmac
import hashlib
import requests
import json
from datetime import datetime

# 1. 환경 변수 로드
ALI_APP_KEY = os.environ.get("ALI_APP_KEY", "").strip()
ALI_SECRET = os.environ.get("ALI_SECRET", "").strip()
ALI_TRACKING_ID = os.environ.get("ALI_TRACKING_ID", "").strip()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

print(f"DEBUG: ALI_APP_KEY exists: {bool(ALI_APP_KEY)}")
print(f"DEBUG: ALI_SECRET length: {len(ALI_SECRET)}")

def get_ali_products(keyword):
    url = "https://api-sg.aliexpress.com/sync"
    params = {
        "app_key": ALI_APP_KEY,
        "timestamp": str(int(time.time() * 1000)),
        "sign_method": "sha256",
        "method": "aliexpress.affiliate.product.query",
        "partner_id": "apidoc",
        "keywords": keyword,
        "target_currency": "USD",
        "target_language": "EN",
        "sort": "LAST_VOLUME_DESC",
        "tracking_id": ALI_TRACKING_ID,
        "page_size": "5"
    }
    
    sorted_params = sorted(params.items())
    base_string = "".join([f"{k}{v}" for k, v in sorted_params])
    sign = hmac.new(ALI_SECRET.encode('utf-8'), base_string.encode('utf-8'), hashlib.sha256).hexdigest().upper()
    params["sign"] = sign
    
    try:
        response = requests.post(url, data=params)
        data = response.json()
        if "aliexpress_affiliate_product_query_response" in data:
            return data["aliexpress_affiliate_product_query_response"]["resp_result"]["result"]["products"]["product"]
        print(f"DEBUG: Ali API Response: {data}")
        return []
    except Exception as e:
        print(f"DEBUG: Ali API Exception: {e}")
        return []

def generate_blog_content(product):
    # 가장 범용적인 v1beta 모델 주소 사용
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    headers = {'Content-Type': 'application/json'}
    prompt_text = f"Write a professional product review for: {product.get('product_title')}. Price: ${product.get('target_sale_price')}. In English, Markdown format."
    
    payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        result = response.json()
        if "candidates" in result:
            return result["candidates"][0]["content"]["parts"][0]["text"]
        print(f"DEBUG: Gemini API Error: {result}")
        return None
    except Exception as e:
        print(f"DEBUG: Gemini Exception: {e}")
        return None

def main():
    # 1. 키워드 로드
    if not os.path.exists("keywords.txt"):
        print("DEBUG: keywords.txt not found. Creating a default one.")
        with open("keywords.txt", "w") as f: f.write("Smart Watch\nWireless Earbuds")
    
    with open("keywords.txt", "r", encoding="utf-8") as f:
        keywords = [line.strip() for line in f if line.strip()]
    
    target_keyword = random.choice(keywords)
    print(f"🎯 Target: {target_keyword}")

    # 2. 상품 검색
    products = get_ali_products(target_keyword)
    if not products:
        print("❌ No products found from AliExpress.")
        return

    selected_product = products[0]
    print(f"📝 Writing review for: {selected_product['product_title'][:30]}...")

    # 3. 글 생성
    content = generate_blog_content(selected_product)
    if not content:
        print("❌ Failed to generate content from Gemini.")
        return

    # 4. 파일 저장
    os.makedirs("posts", exist_ok=True)
    today_str = datetime.now().strftime("%Y-%m-%d")
    file_path = f"posts/{today_str}-post.md"
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"---\ntitle: {selected_product['product_title']}\n---\n\n{content}")
    
    print(f"🎉 SUCCESS: {file_path} created!")

if __name__ == "__main__":
    main()
