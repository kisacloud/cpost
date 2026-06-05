from google import genai
import os
from dotenv import load_dotenv

# 1. 환경 변수 로드 (.env에 저장된 API 키를 가져옵니다)
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("❌ 에러: .env 파일에서 GOOGLE_API_KEY를 찾을 수 없습니다.")
else:
    client = genai.Client(api_key=api_key)

    print(f"🔍 [2026-04-26] 사용 가능한 모델 리스트를 조회합니다...\n")

    # 2. 서버에서 지원하는 모델 목록 가져오기
    try:
        model_list = client.models.list()

        found_any = False
        for m in model_list:
            # 리포트 생성에 필요한 'generateContent' 기능을 지원하는 모델만 필터링
            if m.supported_actions and 'generateContent' in m.supported_actions:
                print(f"✅ 모델명: {m.name}")
                print(f"   ㄴ 설명: {m.description}")
                print(f"   ㄴ 지원 기능: {m.supported_actions}")
                print("-" * 50)
                found_any = True

        if not found_any:
            print("⚠️ 현재 API 키로 사용할 수 있는 모델이 없습니다.")

    except Exception as e:
        print(f"❌ API 호출 중 오류 발생: {e}")