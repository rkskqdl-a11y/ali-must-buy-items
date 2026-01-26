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
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    prompt = f"Write a detailed review for: {product.get('product_title')}. Price is ${product.get('target_sale_price')}. Use Markdown."
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=40)
        res_json = response.json()
        if "candidates" in res_json:
            return res_json["candidates"][0]["content"]["parts"][0]["text"]
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
    
    # ✅ 대가성 문구 설정 (포스팅 최상단에 노출)
    disclosure_text = "> **고지사항:** 이 포스팅은 알리익스프레스 어필리에이트 활동의 일환으로, 구매 시 이에 따른 일정액의 수수료를 제공받을 수 있습니다."

    print(f"🚀 Mission: 40 Posts (Image & Disclosure Fix)")

    while success_count < 40:
        products = get_ali_products()
        if not products: continue
            
        for p in products:
            if success_count >= 40: break
            p_id = str(p.get('product_id'))
            if p_id in current_session_ids: continue
            
            # 🖼️ 이미지 URL 2중 보안 교정
            img_url = p.get('product_main_image_url', '').strip()
            if img_url.startswith('//'):
                img_url = 'https:' + img_url
            elif not img_url.startswith('http'):
                img_url = 'https://' + img_url
            
            # 주소에 포함된 불필요한 쿼리 파라미터 제거 (이미지 로딩 최적화)
            img_url = img_url.split('?')[0] if '?' in img_url else img_url

            content = generate_blog_content(p)
            
            # AI 실패 시 대체 텍스트
            if not content:
                content = f"Check out this amazing {p.get('product_title')} available now on AliExpress!"
            
            file_path = f("_posts/{today_str}-{p_id}.md")
            with open(file_path, "w", encoding="utf-8") as f:
                # 📝 대가성 문구를 제목 바로 아래(Front Matter 직후)에 배치
                f.write(f"---\nlayout: post\ntitle: \"{p['product_title']}\"\ndate: {today_str}\n---\n\n"
                        f"{disclosure_text}\n\n" # 대가성 문구 삽입
                        f"![Product Image]({img_url})\n\n" # 이미지 삽입
                        f"{content}\n\n"
                        f"### [🛒 Buy on AliExpress]({p.get('promotion_link')})")
            
            current_session_ids.add(p_id)
            success_count += 1
            print(f"   ✅ SUCCESS ({success_count}/40): {p_id}")
            time.sleep(5)

    print(f"🏁 Mission Completed: 40 posts.")

if __name__ == "__main__":
    main()
