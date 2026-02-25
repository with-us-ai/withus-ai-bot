import google.generativeai as genai

# 대표님의 API 키
API_KEY = "AIzaSyA9m5N1VI5aBSjgah36fFRbxe2y2CXqiBY"
genai.configure(api_key=API_KEY)

print("🔍 현재 API 키로 사용 가능한 텍스트 생성 모델 목록을 불러옵니다...\n")

try:
    for m in genai.list_models():
        # 텍스트 생성이 가능한 모델만 필터링해서 출력
        if 'generateContent' in m.supported_generation_methods:
            print(f"✅ 사용 가능 모델명: {m.name}")
except Exception as e:
    print(f"오류 발생: {e}")
    
print("\n출력된 모델명 중 'flash'가 들어간 가장 최신 버전을 메인 코드에 적용하시면 됩니다!")