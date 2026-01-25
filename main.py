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
    modifiers = ["Best Budget", "Top Rated", "High Quality", "Portable", "Wireless", "Gaming", "Waterproof", "Smart", "Gift for Him", "Trending", "Must Have"]
    products = ["Mechanical Keyboard", "Gaming Mouse", "Power Bank", "USB Hub", "GaN Charger", "Smart Watch", "Mini PC", "Portable Projector", "Robot Vacuum", "Camping Lantern", "Pocket Knife"]
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

def list_available_models():
    """사용 가능한 모델 목록을 출력하여 이름표 에러를 해결합니다."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
    try:
        response = requests.get(url)
        models = response.json().get('models', [])
        print("🔍 Available Models for your API Key:")
        for m in models:
            print(f" - {m['name']}")
        return [m['name'] for m in models]
    except:
        return []

def generate_blog_content(product, available_model_names):
    # 제미나이 3.0 및 최신 엔진을 위한 후보군
    candidates = [
        "models/gemini-2.0-flash",
        "models/gemini-1.5-flash",
        "models/gemini-pro"
    ]
    
    # 실제 사용 가능한 모델이 있다면 후보군 맨 앞에 추가
    if available_model_names:
        # gemini-3 계열이 있다면 최우선 순위
        g3_models = [m for m in available_model_names if 'gemini-3' in m.lower()]
        candidates = g3_models + candidates

    headers = {'Content-Type': 'application/json'}
    prompt_text = (f"Review this product using your advanced reasoning: {product.get('product_title')}. "
                   f"Price: ${product.get('target_sale_price')}. Write a professional review in Markdown.")
    payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
    
    for model_name in candidates:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={GEMINI_API_KEY}"
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            result = response.json()
            
            if "candidates" in result:
                print(f"✅ Success using model: {model_name}")
                return result["candidates"][0]["content"]["parts"][0]["text"]
            
            print(f"ℹ️ Model {model_name} failed: {result.get('error', {}).get('message', 'Unknown error')}")
        except:
            continue
            
    return None

def main():
    os.makedirs("_posts", exist_ok=True)
    
    # 1. 사용 가능한 모델 이름들 먼저 확인 (로그에 출력됨)
    available_models = list_available_models()

    # 2. 키워드 선택
    all_keywords = get_massive_keyword_list()
    target_keyword = random.choice(all_keywords)
    print(f"📚 Total Keywords: {len(all_keywords)} | 🎯 Target: {target_keyword}")

    # 3. 상품 검색
    products = get_ali_products(target_keyword)
    if not products:
        print("❌ AliExpress No Products Found.")
        return

    selected_product = products[0]
    print(f"📝 Writing Review: {selected_product['product_title'][:40]}...")
    
    # 4. 글 생성 (모델 리스트 전달)
    content = generate_blog_content(selected_product, available_models)
    
    if content:
        today = datetime.now().strftime("%Y-%m-%d")
        file_path = f"_posts/{today}-{selected_product.get('product_id')}.md"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"🎉 SUCCESS: {file_path} created!")
    else:
        print("❌ Content generation failed across all models.")

if __name__ == "__main__":
    main()
