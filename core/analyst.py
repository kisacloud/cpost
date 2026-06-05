import logging
import json
import time
import re
from config.config import Config
import prompts.base_prompt as prompts
from google import genai  # 새로운 Google Gen AI SDK 임포트

# 시스템 로그 설정: 분석 과정의 주요 단계를 추적합니다.
logger = logging.getLogger(__name__)

class ReportAnalyst:
    """
    CPOST 2.0 통합 전략 분석 엔진 (google-genai SDK 표준 적용)
    - 모든 리포트 주기를 단일 파이프라인(run_analysis_flow)으로 통합 처리.
    - Pass 1 (미션 수립): 기초 데이터를 분석하여 심층 재검색을 위한 쿼리와 가설 도출.
    - Pass 2 (최종 합성): 수집된 모든 데이터를 조립하여 전략 리포트 생성.
    - 안정성 정책: 데이터 세척(Cleaning) 및 입력 길이 제한(Truncation)을 통한 런타임 에러 방지.
    """

    def __init__(self, client, model_id):
        """
        초기화: 새로운 SDK의 Client 객체와 모델 ID를 주입받습니다.
        """
        self.client = client
        self.model_id = model_id

        # 새로운 SDK의 GenerateConfig 구조에 맞춘 설정 (dict 형태 지원)
        self.gen_config = {
            "max_output_tokens": Config.MAX_OUTPUT_TOKENS,
            "temperature": Config.TEMPERATURE,
            "top_p": 0.95,
            "top_k": 40,
        }

    def _extract_json_safely(self, text):
        """
        AI의 응답 텍스트에서 JSON 블록만 안전하게 추출합니다.
        - 마크다운 코드 블록(```json) 제거 및 정규표현식 매칭 수행.
        """
        try:
            # 코드 블록 기호 제거
            clean_text = re.sub(r'```json\s*|```\s*', '', text).strip()
            # 중괄호로 둘러싸인 부분 검색
            match = re.search(r'\{.*\}', clean_text, re.DOTALL)
            if match:
                return json.loads(match.group())
            return json.loads(clean_text)
        except Exception as e:
            logger.error(f"❌ JSON 파싱 실패: {e}")
            return None

    def run_analysis_flow(self, period_type, collector, sector_info, past_data=None):
        """
        [핵심 메서드] 통합 분석 파이프라인을 실행합니다.

        Args:
            period_type: 분석 주기 ('DAILY', 'WEEKLY', 'MONTHLY')
            collector: 데이터 수집 객체 (Tavily 검색용)
            sector_info: 현재 분석 타겟 섹션 정보
            past_data: 주간/월간 분석을 위한 과거 리포트 누적 데이터 (Optional)
        """
        logger.info(f"🚀 [{period_type}] 분석 파이프라인 가동 시작")

        # --- [Step 1] 기초 데이터 확보 (실시간 뉴스 검색) ---
        basic_news = collector.get_latest_news_context(sector_info["queries"])
        if not basic_news or len(basic_news.strip()) < 300:
            logger.warning("⚠️ 기초 데이터 부족으로 분석을 중단함")
            return None, "기초 데이터 수집 부족"

        # 🚨 [방어 운전] 구글 서버의 과부하를 막기 위해 2초간 대기
        time.sleep(2)

        # --- [Step 2] 심층 미션 수립 (Pass 1) ---
        # 🚨 [수정] 이제 프롬프트에 {today_date}가 포함되었으므로, format 시 함께 넘겨줘야 합니다.
        today_str = Config.get_today_str_korean()

        if period_type == "DAILY":
            # 🚨 데일리에도 과거 데이터를 주입하도록 변수 추가!
            mission_prompt = prompts.KEYWORD_EXTRACTION_PROMPT.format(
                today_date=today_str,
                news_summary=basic_news[:4000],
                combined_data=(past_data or "과거 데이터 없음")[:4000]
            )
        else:
            # 주간/월간은 오늘 뉴스, 과거 맥락, 그리고 오늘 날짜를 주입
            mission_prompt = prompts.PERIODIC_QUERY_EXTRACTION_PROMPT.format(
                today_date=today_str,
                today_news=basic_news[:3000],
                combined_data=(past_data or "누적 데이터 없음")[:4000]
            )

        logger.info("🧠 분석 미션 및 심층 쿼리 도출 중...")

        # [변경점] 새로운 SDK 호출 방식: client.models.generate_content
        mission_res = self.client.models.generate_content(
            model=self.model_id,
            contents=mission_prompt,
            config=self.gen_config
        )
        mission = self._extract_json_safely(mission_res.text)

        if not mission or mission.get("decision") == "SKIP":
            return None, mission.get("reason", "분석 가치 미달로 판단됨")

        # --- [Step 3] 글로벌 심층 재검색 (Deep-Dive) ---
        query = mission.get("query", "")
        direction = mission.get("direction", mission.get("macro_theme", ""))

        logger.info(f"🎯 심층 검색 쿼리 실행: {query}")
        deep_news = collector.get_deep_dive_context(str(query)[:300])

        # --- [Step 4] 데이터 안전 세척 및 템플릿 조립 ---
        # 🚨 [안전장치] 뉴스 데이터 내 중괄호가 .format() 에러를 일으키지 않도록 치환합니다.
        safe_basic = basic_news[:3000].replace("{", "[").replace("}", "]")
        safe_deep = deep_news[:4000].replace("{", "[").replace("}", "]")
        safe_past = (past_data or "과거 데이터 없음")[:4000].replace("{", "[").replace("}", "]")

        template_map = {
            "DAILY": prompts.DAILY_PROMPT,
            "WEEKLY": prompts.WEEKLY_PROMPT_TEMPLATE,
            "MONTHLY": prompts.MONTHLY_PROMPT_TEMPLATE
        }

        # 🚨 [버그 픽스] COMMON_GUIDE 내부에 있는 {today_date} 변수를 먼저 치환합니다.
        today_str = Config.get_today_str_korean()
        formatted_common_guide = prompts.REPORT_COMMON_GUIDE.format(today_date=today_str)

        # [Step 5] 단일 포맷팅 (Single-Pass Formatting)
        try:
            # 프롬프트 파일에 미리 조립하지 않고, 여기서 모든 변수를 한 번에 주입합니다. (Single-Pass)
            final_prompt = template_map[period_type].format(
                common_guide=formatted_common_guide,
                today_date=today_str,
                basic_news=safe_basic,
                deep_news=safe_deep,
                combined_data=safe_past,
                direction=direction,
                macro_theme=direction,
                query=query,
                report_range=f"최근 {Config.REPORTS[period_type].get('LOOKBACK', 1)}일"
            )
        except Exception as e:
            logger.error(f"❌ 리포트 템플릿 조립 중 오류 발생: {e}")
            return None, "Template Assembly Error"

        # --- [Step 6] 최종 전략 리포트 합성 (Pass 2) ---
        logger.info(f"✍️ {period_type} 최종 전략 보고서 합성 중...")

        # [변경점] 새로운 SDK 호출 방식 적용
        final_res = self.client.models.generate_content(
            model=self.model_id,
            contents=final_prompt,
            config=self.gen_config
        )

        # 가비지 컬렉션 유도 (메모리 관리)
        del safe_basic, safe_deep, safe_past, final_prompt

        return final_res.text, {"query": query, "theme": direction}