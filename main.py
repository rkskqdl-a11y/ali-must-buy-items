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
    modifiers = ["Best", "Top", "Portable", "Wireless", "Gaming", "Smart", "Gift", "Trending"]
    products = ["Keyboard", "Mouse", "Power Bank", "USB Hub", "Charger", "Smart Watch", "Projector", "Vacuum", "Lantern"]
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
    # Gemini 3.0의 추론 능력을 활용할 수 있는 모델들입니다.
    candidates = ["models/gemini-3-flash-preview", "models/gemini-2.0-flash", "models/gemini-1.5-flash"]
    headers = {'Content-Type': 'application/json'}
    prompt_text = (f"Review this product with Gemini 3.0 Reasoning: {product.get('product_title')}. "
                   f"Price: ${product.get('target_sale_price')}. Write in expert English Markdown.")
    payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
    
    for model_name in candidates:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={GEMINI_API_KEY}"
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            result = response.json()
            
            if "candidates" in result:
                print(f"✅ Success using model: {model_name}")
                return result["candidates"][0]["content"]["parts"][0]["text"]
            else:
                # 🔍 에러 발생 시 로그를 상세히 찍어 원인을 파악합니다.
                print(f"⚠️ Model {model_name} failed. Message: {result.get('error', {}).get('message', 'Unknown Error')}")
                if "429" in str(result):
                    print("Waiting for 5 seconds due to rate limit...")
                    time.sleep(5)
        except Exception as e:
            print(f"ℹ️ Error with {model_name}: {e}")
            continue
    return None

def main():
    os.makedirs("_posts", exist_ok=True)
    if not os.path.exists("posted_ids.txt"):
        with open("posted_ids.txt", "w") as f: f.write("")

    all_keywords = get_massive_keyword_list()
    target = random.choice(all_keywords)
    print(f"🎯 Target: {target}")

    products = get_ali_products(target)
    if not products:
        print("❌ No products found.")
        return

    selected_product = products[0]
    print(f"📝 Writing Review: {selected_product['product_title'][:40]}...")
    
    content = generate_blog_content(selected_product)
    
    if content:
        today = datetime.now().strftime("%Y-%m-%d")
        file_path = f"_posts/{today}-{selected_product.get('product_id')}.md"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"---\nlayout: post\ntitle: \"{selected_product['product_title']}\"\ndate: {today}\n---\n\n{content}")
            
        with open("posted_ids.txt", "a") as f:
            f.write(f"{selected_product.get('product_id')}\n")
        print(f"🎉 SUCCESS: {file_path} created!")
    else:
        # 실패 시에도 로그에 기록을 남겨 추적이 가능하게 합니다.
        print("❌ Content generation failed. Please check the '⚠️ Model failed' messages above.")

if __name__ == "__main__":
    main()
