import google.genai as genai
import os
from dotenv import load_dotenv

# 1. 환경 변수 로드 (.env에 저장된 API 키를 가져옵니다)
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("❌ 에러: .env 파일에서 GOOGLE_API_KEY를 찾을 수 없습니다.")
else:
    # 2. 클라이언트 객체 초기화
    client = genai.Client(api_key=api_key)

    print("🔍 [2026-04-26] 사용 가능한 모델 리스트를 조회합니다...\n")

    # 3. 모델 목록 조회 및 출력 로직 수정
    try:
        # Paginator 객체를 리스트로 변환하여 순회
        model_list = list(client.models.list())

        found_any = False
        for m in model_list:
            # 4. 'supported_generation_methods' 속성 제거 및 안전한 출력 구조 적용
            # 최신 버전에서는 모델의 이름(name)과 설명(description)을 중심으로 출력합니다.
            print(f"✅ 모델명: {m.name}")

            # 설명이 없는 경우를 대비한 안전한 출력
            description = getattr(m, 'description', '설명 없음')
            print(f"   ㄴ 설명: {description}")
            print("-" * 50)
            found_any = True

        if not found_any:
            print("⚠️ 현재 API 키로 조회할 수 있는 모델이 없습니다.")

    except Exception as e:
        print(f"❌ API 호출 중 오류 발생: {e}")