# 1. 초경량 파이썬 3.12 슬림 이미지 사용
FROM python:3.12-slim

# 2. 파이썬 버퍼링 해제 (로그가 실시간으로 보이게 설정)
ENV PYTHONUNBUFFERED=1

# 3. 작업 디렉토리 설정
WORKDIR /app

# 4. 필수 시스템 패키지 설치 (시간대 설정을 위한 tzdata 포함)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata && \
    ln -fs /usr/share/zoneinfo/Asia/Seoul /etc/localtime && \
    rm -rf /var/lib/apt/lists/*

# 5. 라이브러리 목록 복사 및 설치 (캐싱 최적화를 위해 소스보다 먼저 수행)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. 전체 소스 코드 및 설정 파일 복사
COPY . .

# 7. 실행 명령 (지휘자 엔진 가동)
CMD ["python", "main_report.py"]