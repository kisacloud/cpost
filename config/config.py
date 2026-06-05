import os
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# [보안 가이드] .env 파일 로드
load_dotenv()

# 프로젝트 루트 경로 설정
BASE_DIR = Path(__file__).parent.parent

class Config:
    """
    지능형 비서 CPOST의 통합 설정 클래스
    (가용 자원 50% 투자 최적화 버전)
    """
    # --- 🔑 API 환경 변수 로드 ---
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
    SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
    SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

    # --- 🔍 검색 엔진 설정 (자원 50% 집중 투자) ---
    TAVILY = {
        "SEARCH_DEPTH": "advanced", # 심층 크롤링 모드 (기본 basic)
        "MAX_RESULTS": 10,          # 수집량 대폭 확장 (기본 3)
        "DAYS": 3,                  # 최신성 범위 확보
    }

    # --- 🧠 AI 모델 설정 ---
    # 2026년 기준 가장 안정적인 스테이블 모델 사용
    MODEL_NAME = "gemini-flash-latest"
    # MODEL_NAME = "gemini-pro-latest"
    MAX_OUTPUT_TOKENS = 8192       # 리포트 길이 및 추론량 확보
    TEMPERATURE = 0.7              # 분석의 창의성과 논리성 균형

    # --- 📂 시스템 경로 설정 ---
    DATA_DIR = BASE_DIR / "data"
    LOG_DIR = BASE_DIR / "logs"
    RAW_DATA_DIR = DATA_DIR / "raw_data"

    # 폴더 자동 생성
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # --- 📅 리포트 주기 및 데이터 보관 정책 ---
    REPORTS = {
        "DAILY": {
            "DIR": DATA_DIR / "daily",
            "RETENTION": 30,          # 30일간 보관
            "LOOKBACK": 3,            # 분석 시 참조할 과거 데이터 개수
            "CHANNEL": "#dev-test"    # 슬랙 채널명
        },
        "WEEKLY": {
            "DIR": DATA_DIR / "weekly",
            "RETENTION": 90,          # 90일간 보관
            "LOOKBACK": 7,            # 7일치 데이터 통합
            "CHANNEL": "#dev-test"
        },
        "MONTHLY": {
            "DIR": DATA_DIR / "monthly",
            "RETENTION": 730,         # 2년간 보관
            "LOOKBACK": 8,            # 8주치 데이터 통합
            "CHANNEL": "#dev-test"
        }
    }

    # [요일별 섹터 라우팅]
    SCHEDULE_ROUTING = {
        0: "TECH",      # 월
        1: "POLICY",    # 화
        2: "INDUSTRY",  # 수
        3: "TECH",      # 목
        4: "POLICY",    # 금
        5: "INDUSTRY",  # 토
        6: "TECH"       # 일
    }

    @classmethod
    def validate(cls):
        """필수 API 키 검사"""
        required = ["GOOGLE_API_KEY", "SLACK_BOT_TOKEN", "TAVILY_API_KEY"]
        missing = [k for k in required if not getattr(cls, k)]
        if missing:
            raise EnvironmentError(f"🚨 필수 설정 누락: {', '.join(missing)}")

    @staticmethod
    def get_today_str_korean():
        return datetime.now().strftime("%Y년 %m월 %d일")

    @staticmethod
    def get_today_str():
        return datetime.now().strftime("%Y-%m-%d")

# 설정 검증 실행
Config.validate()