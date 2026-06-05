import logging
from datetime import datetime
from google import genai  # [UPDATE] 단종된 google-generativeai 대신 최신 google-genai 사용

# 프로젝트 내부 설정 및 전담 모듈 임포트
from config.config import Config
import prompts.base_prompt as prompts
from core.collector import DataCollector
from core.reporter import ReportDispatcher
from core.analyst import ReportAnalyst
import time
import schedule

# =========================================================
# [영역 1] 시스템 로깅 및 실행 환경 설정
# =========================================================

# 로그 저장 디렉토리 자동 생성 (데이터 누적을 위한 필수 절차)
Config.LOG_DIR.mkdir(exist_ok=True)

# 실행 로그 설정: 콘솔 출력과 파일 기록을 동시에 수행하며 UTF-8 인코딩을 보장합니다.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Config.LOG_DIR / "main_report.log", encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# =========================================================
# [영역 2] InsightEngine 클래스 (지휘자)
# =========================================================
class InsightEngine:
    """
    CPOST 프로젝트의 통합 지휘자(Orchestrator) 엔진입니다.
    - google-genai SDK를 통해 최신 Gemini 모델과의 통신을 관리합니다.
    - 리포트 주기(Daily/Weekly/Monthly)에 따른 파이프라인 제어를 전담합니다.
    - 데이터 수집기, 리포트 전송기, 분석 전문가 객체를 조립하여 구동합니다.
    """

    def __init__(self):
        """
        시스템 초기화: 새로운 SDK 클라이언트를 생성하고 분석에 필요한 컴포넌트를 조립합니다.
        """
        # 1. 새로운 Google Gen AI 클라이언트 인스턴스 생성
        # api_key를 통해 인증하며, 향후 Vertex AI 등으로 확장 시 설정 변경이 용이합니다.
        self.client = genai.Client(api_key=Config.GOOGLE_API_KEY)
        self.model_id = Config.MODEL_NAME  # 예: "gemini-2.5-flash"

        # 2. 분석 기준 시간 설정
        self.today = datetime.now()

        # 3. 전담 컴포넌트 인스턴스화 (의존성 주입)
        self.collector = DataCollector()          # Tavily 기반 데이터 수집 전담
        self.reporter = ReportDispatcher()        # 슬랙 전송 및 파일 저장 전담

        # [중요] 분석기(Analyst)에 생성된 클라이언트와 모델 ID를 전달하여 지능을 부여합니다.
        self.analyst = ReportAnalyst(self.client, self.model_id)

        logger.info("🚀 CPOST 2.0 지휘자 엔진 조립 완료 (최신 SDK 표준 적용)")

    def process(self, report_type):
        """
        리포트 생성 파이프라인을 실행합니다. (DAILY, WEEKLY, MONTHLY)
        모든 주기는 '실시간 검색'을 앵커(Anchor)로 삼아 최신성을 유지합니다.
        """
        # 저장 경로 확보
        Config.REPORTS[report_type]["DIR"].mkdir(parents=True, exist_ok=True)
        today_str = self.today.strftime("%Y-%m-%d")

        # 🚨 [테스트용] API 할당량 소진 방지를 위해 실제 로직은 건너뛰고 로그만 출력합니다.
        # logger.info(f"🧪 [TEST] {report_type} 분석 시퀀스 가동 준비 완료")
        # return

        logger.info(f"📝 {report_type} 분석 시퀀스 가동")

        try:
            # [Step 1] 상황 인지 및 맥락 준비
            # 오늘 요일에 따른 타겟 섹터를 결정합니다.
            weekday = self.today.weekday()
            sector = Config.SCHEDULE_ROUTING.get(weekday, "TECH")
            sector_info = prompts.SECTOR_CONFIG.get(sector)

            # 일간/주간/월간의 경우 누적된 과거 리포트 데이터(config에 설정된 기간)를 로드하여 '흐름'을 파악하게 합니다.
            past_data = self.reporter.get_accumulated_text(report_type)

            # [Step 2] 분석 전문가에게 통찰 도출 위임 (The Unified Flow)
            # 실시간 데이터와 누적 데이터를 융합하여 전략적 리포트를 생성합니다.
            report_text, meta = self.analyst.run_analysis_flow(
                period_type=report_type,
                collector=self.collector,
                sector_info=sector_info,
                past_data=past_data
            )

            # [Step 3] 예외 처리: 분석 가치가 없거나 데이터가 부족할 경우
            if not report_text:
                logger.info(f"⏭️ 분석 건너뜀 알림 발송: {meta}")
                self.reporter.slack.chat_postMessage(
                    channel=Config.REPORTS[report_type]["CHANNEL"],
                    text=f"☕ *[{sector_info['label']}] {report_type} 분석 휴재*: {meta}"
                )
                return

            # [Step 4] 중간 분석 브리핑 (슬랙 실시간 알림)
            # AI가 어떤 가설(미션)을 가지고 심층 분석을 수행했는지 사용자에게 알립니다.
            # progress_msg = (
            #     f"🎯 *[{report_type}] 심층 주제 선정:* *'{meta['query']}'*\n"
            #     f"🧠 *분석 테마:* {meta['theme']}"
            # )
            # self.reporter.slack.chat_postMessage(
            #     channel=Config.REPORTS[report_type]["CHANNEL"],
            #     text=progress_msg
            # )

            # [Step 5] 최종 결과물 저장 및 슬랙 전송
            # 생성된 전략 리포트를 파일로 보관하고 슬랙 채널에 게시합니다.
            self.reporter.save_and_send(report_type, today_str, report_text)

            # 자원 최적화: 대용량 텍스트 데이터의 명시적 메모리 해제
            if past_data: del past_data
            logger.info(f"✅ {report_type} 리포트 발행 성공")

        except Exception as e:
            logger.error(f"🚨 {report_type} 실행 오류 발생: {e}", exc_info=True)

    def run_scheduler(self):
        """
        스케줄러: 현재 날짜/시간에 따라 적절한 리포트 프로세스를 호출합니다.
        """

        # 1. 데일리 분석 수행
        self.process("DAILY")

        # 2. 주간 분석 (월요일)
        if self.today.weekday() == 0:
            logger.info("⏳ 주간 분석 전 API 할당량 확보를 위해 60초간 대기합니다...")
            time.sleep(60)
            self.process("WEEKLY")

        # 3. 월간 분석 (매월 1일)
        if self.today.day == 1:
            logger.info("⏳ 월간 분석 전 API 할당량 확보를 위해 60초간 대기합니다...")
            time.sleep(60)
            self.process("MONTHLY")

def job():
    """스케줄러에 의해 실행될 단일 작업 단위"""
    logger.info("🔄 예약된 리포트 분석 파이프라인 가동을 시작합니다.")
    # 매번 새로운 엔진 객체를 생성하여 datetime.now()가 호출 시점의 올바른 시간을 갖도록 함
    engine = InsightEngine()
    engine.run_scheduler()

if __name__ == "__main__":
    try:
        logger.info("🚀 CPOST 리포트 생성을 시작합니다.")

        # =========================================================
        # [운영 모드 1: Batch / Cron 모드] - ✨ 현재 활성화 ✨
        # - GCP e2-micro (1G RAM) 서버의 자원(메모리) 최적화를 위한 1회성 실행 모드입니다.
        # - 리눅스의 crontab이 매일 아침 정해진 시간에 이 스크립트를 1번만 실행하고 종료합니다.
        # - 대기 시간 동안 파이썬이 메모리를 전혀 차지하지 않아 극한의 효율을 자랑합니다.
        # =========================================================
        job()
        logger.info("✅ CPOST 리포트 생성 및 전송 완료. 메모리 반환을 위해 프로세스를 종료합니다.")

        # =========================================================
        # [운영 모드 2: Daemon / Schedule 모드] - 🔒 현재 비활성화 (주석 처리)
        # - 도커(Docker)를 24시간 띄워두거나, 넉넉한 스펙의 서버에서 사용할 때의 세팅입니다.
        # - while True 무한 루프가 메모리를 지속적으로 점유하므로, 현재의 1G RAM 환경에서는
        #   OS(OOM Killer)에 의해 프로세스가 강제 종료될 위험이 있어 잠시 꺼두었습니다.
        # - 훗날 서버 스펙을 업그레이드하거나 도커 환경으로 복귀할 때 아래 주석을 해제하세요.
        # =========================================================
        # logger.info("⏰ CPOST 스케줄러 데몬을 시작합니다.")
        # schedule.every().day.at("08:00").do(job)
        #
        # # 무한 루프를 돌며 스케줄 대기
        # while True:
        #     schedule.run_pending()
        #     time.sleep(60)
        # =========================================================

        # =========================================================
        # 🧪 [테스트 및 수동 실행 모드]
        # - 특정 주기 리포트를 강제로 생성하고 싶을 때 아래 주석을 해제하세요.
        # - 실행 후에는 다시 주석 처리해야 다음 날 중복 발행을 방지할 수 있습니다.
        # =========================================================
        # engine = ReportDispatcher() # 객체 초기화가 필요하다면 활성화
        # engine.process("WEEKLY")    # 주간 리포트 강제 생성 테스트
        # engine.process("MONTHLY")   # 월간 리포트 강제 생성 테스트
    except Exception as e:
        # 복구 불가능한 시스템 레벨 오류 로깅
        logger.critical(f"💀 시스템 구동 불가 (Critical Error): {e}")