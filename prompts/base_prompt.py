"""
CPOST 프롬프트 자산 관리 파일 (V2.8 - Recency-Aware Trend Report)
- 하드코딩 배제: {today_date} 기반 시의성 판단
- 한영 병기 검색어 유지: Tavily API 기반 국내외 기사 동시 탐색
- 최신성 등급화: Fresh / Recent / Context / Background 구분
- 동향 리포트 중심: 실행 과제·대응 지침·액션 안내 제거
- Block Kit 최적화: 섹션 구분자 '---' 강제 적용 및 인용구(>) 제거
"""

# =========================================================
# [SECTION 1] 검색 쿼리 및 섹터 설정
# - 검색어는 특정 기술에 과도하게 고정하지 않고,
#   넓은 키워드 조합으로 Tavily가 후보군을 확장하도록 설계
# - 모든 쿼리는 한글 + 영문을 함께 포함
# =========================================================

SECTOR_CONFIG = {
    "TECH": {
        "queries": [
            (
                "클라우드 AI 서비스, AI 에이전트, RAG, MCP, 모델 서빙, AI 게이트웨이, "
                "cloud AI service, AI agent, RAG, MCP, model serving, AI gateway"
            ),
            (
                "AI 인프라, GPU 클라우드, 데이터센터, 쿠버네티스, MLOps, LLMOps, "
                "AI infrastructure, GPU cloud, data center, Kubernetes, MLOps, LLMOps"
            ),
            (
                "생성형 AI 플랫폼, 멀티모달 AI, 엔터프라이즈 AI, AI 애플리케이션 아키텍처, "
                "generative AI platform, multimodal AI, enterprise AI, AI application architecture"
            )
        ],
        "label": "클라우드·AI 기술 동향"
    },

    "POLICY": {
        "queries": [
            (
                "AI GRC, AI 거버넌스, 규제자동화, 컴플라이언스 자동화, 전자증적, "
                "AI GRC, AI governance, regulatory automation, compliance automation, digital evidence"
            ),
            (
                "AICM, AI Controls Matrix, AI-CAIQ, CSA STAR for AI, AI 통제체계, 공동책임모델, "
                "AICM, AI Controls Matrix, AI-CAIQ, CSA STAR for AI, AI control framework, shared responsibility model"
            ),
            (
                "기계판독형 컴플라이언스, 통제 매핑, 상시 모니터링, 감사 자동화, 증적 자동화, "
                "machine-readable compliance, control mapping, continuous control monitoring, audit automation, evidence automation"
            )
        ],
        "label": "AI GRC·규제자동화 동향"
    },

    "INDUSTRY": {
        "queries": [
            (
                "클라우드 AI 시장, AI 서비스 도입, 엔터프라이즈 AI, AI 생산성, AI 투자, "
                "cloud AI market, AI service adoption, enterprise AI, AI productivity, AI investment"
            ),
            (
                "AI 보안 시장, 클라우드 보안 시장, CNAPP, CSPM, DSPM, AI-SPM, "
                "AI security market, cloud security market, CNAPP, CSPM, DSPM, AI-SPM"
            ),
            (
                "빅테크 AI 클라우드, 소버린 AI, AI 파트너십, AI 생태계, "
                "big tech AI cloud, sovereign AI, AI partnership, AI ecosystem"
            )
        ],
        "label": "클라우드·AI 산업 동향"
    }
}


# =========================================================
# [SECTION 2] 다단계 분석 로직
# Pass 1: 심층 재검색 미션 수립
# =========================================================

KEYWORD_EXTRACTION_PROMPT = """
당신은 기술·정책·산업을 함께 보는 시니어 전략 분석가입니다.
현재 기준일은 **{today_date}**입니다.

아래 1차 뉴스 요약을 검토하여, 후속 심층 검색에 사용할
넓은 범위의 한영 혼합 검색어와 분석 방향을 도출하십시오.

[최신성 판단 기준]
- A/Fresh: 최근 0~48시간 내 발행 또는 발표
- B/Recent: 최근 3~7일 내 발행 또는 발표
- C/Context: 최근 8~45일 내 기준자료·분석자료
- D/Background: 46일 이상 경과한 배경자료

[작성 지침]
1. A/Fresh 자료가 있으면 해당 이슈를 중심으로 심층 분석 방향을 설정하십시오.
2. A/Fresh 자료가 없으면 B/Recent 또는 C/Context 자료를 기반으로
   "최근 흐름 재평가" 방향을 설정하십시오.
3. D/Background 자료는 주요 사건이 아니라 맥락 보강용으로만 사용하십시오.
4. 검색어는 특정 제품·취약점·기업명에 과도하게 고정하지 말고,
   넓은 키워드 묶음 형태의 한글·영문 병기 검색어로 작성하십시오.
5. JSON 형식으로만 답변하십시오.

[JSON 형식]
{{
    "decision": "PROCEED" | "SKIP",
    "report_mode": "DAILY_TRIGGER" | "RECENT_SIGNAL" | "CONTEXT_BRIEF",
    "query": "한글 키워드, English keywords, 관련 넓은 검색어 조합",
    "direction": "분석의 핵심 관찰 방향",
    "recency_reason": "최신성 판단 근거",
    "reason": "SKIP 시 사유"
}}

[데이터]
{news_summary}
"""


PERIODIC_QUERY_EXTRACTION_PROMPT = """
당신은 거시 전략 분석가입니다.
현재 기준일은 **{today_date}**입니다.

오늘의 뉴스와 지난 누적 리포트를 함께 검토하여,
주간 또는 월간 단위에서 반복적으로 나타나는 구조적 변화를 포착하십시오.

[최신성 판단 기준]
- A/Fresh: 최근 0~48시간 내 발행 또는 발표
- B/Recent: 최근 3~7일 내 발행 또는 발표
- C/Context: 최근 8~45일 내 기준자료·분석자료
- D/Background: 46일 이상 경과한 배경자료

[작성 지침]
1. 단일 사건보다 반복되는 흐름, 정책 변화, 산업 구조 변화를 우선하십시오.
2. 특정 기술명에 과도하게 집중하지 말고, 넓은 키워드 묶음으로 검색어를 작성하십시오.
3. 국내외 기사 탐색을 위해 한글·영문 검색어를 모두 포함하십시오.
4. 최신 자료가 부족하면 "신규 사건"이 아니라 "기존 흐름의 재평가"로 분류하십시오.
5. JSON 형식으로만 답변하십시오.

[JSON 형식]
{{
    "decision": "PROCEED",
    "report_mode": "WEEKLY_SIGNAL" | "MONTHLY_TREND" | "CONTEXT_BRIEF",
    "query": "한글 키워드, English keywords, 관련 넓은 검색어 조합",
    "direction": "이번 기간 분석의 핵심 관찰 방향",
    "macro_theme": "추출된 거시 트렌드 명칭",
    "recency_reason": "최신성 판단 근거"
}}

[데이터 A: 실시간 뉴스]
{today_news}

[데이터 B: 지난 누적 리포트]
{combined_data}
"""


# =========================================================
# [SECTION 3] 리포트 생성 공통 가이드라인
# =========================================================

REPORT_COMMON_GUIDE = """
[공통 작성 원칙]

- **동향 리포트 성격:** 본 리포트는 기술·정책·산업 동향 분석용임. 실행 과제, 대응 지침, 조치 권고를 작성하지 말 것.
- **동적 시의성:** {today_date} 기준으로 최근 자료 여부를 판단하고, 최신 자료가 없으면 없다고 명시할 것.
- **최신성 등급:** 모든 주요 출처는 A/Fresh, B/Recent, C/Context, D/Background 중 하나로 분류할 것.
- **신규 사건 제한:** "오늘의 신규 트리거"에는 A/Fresh 자료만 포함할 것.
- **오래된 자료 오용 금지:** C/D 자료를 "오늘 발표", "최근 24~48시간" 또는 "오늘의 사건"으로 표현하지 말 것.
- **자료 용도 표시:** 각 출처는 Trigger, Signal, Context, Background 중 하나의 용도를 표시할 것.
- **섹션 구분:** 각 주요 섹션 사이에는 반드시 '---' 단독 줄을 삽입할 것. Block Kit 변환용임.
- **슬랙 가독성:** 인용구 기호(>) 사용 금지. 불릿은 '• **[헤드라인]**' 형식으로 작성할 것.
- **분량 제한:** 전체 리포트는 현재 데일리 리포트 수준을 넘지 않도록 압축할 것.
- **불릿 제한:** 각 섹션별 불릿은 최대 3개만 작성할 것.
- **문체:** 격식 있는 명사형 종결 문체(-함, -임, -필요가 아니라 -로 해석됨 등)를 사용할 것.
- **하위 목록 금지:** 불릿 내부에 숫자 목록이나 추가 하위 목록을 만들지 말 것.
- **출처 형식:** [타이틀], [발행처], [YYYY-MM-DD], [등급/용도] 형식을 사용할 것.
- **발행일 불명확:** 발행일이 확인되지 않는 자료는 주요 사건에 포함하지 말고 보조 맥락으로만 사용할 것.
- **과장 금지:** 단일 기사나 벤더 주장만으로 시장 전체 전환, 표준 확정, 규제 확정처럼 단정하지 말 것.
"""


# =========================================================
# [SECTION 4] 최종 리포트 템플릿
# Pass 2: Daily / Weekly / Monthly
# =========================================================

# 1. 데일리 동향 리포트
DAILY_PROMPT = """
# ROLE: Senior Strategy Analyst
# REPORT: Daily Trend Insight
# DATE: {today_date}

{common_guide}

📢 **[News Status]**
{today_date} 기준, 오늘자 신규 트리거 존재 여부와 분석 성격을 명확히 기술

---
🚀 **[CPOST] 오늘의 전략적 함의**
{today_date} 기준, 기술·정책·산업 흐름을 관통하는 핵심 해석 한 문장

---
💡 **오늘의 신규 트리거 / 주요 흐름**
• **[신규성 판단]** : A/Fresh 자료 존재 여부와 리포트 모드 설명
• **[주요 흐름]** : 최근 자료에서 반복 확인된 핵심 변화 요약
• **[맥락 자료]** : 배경자료가 오늘 분석에서 갖는 제한적 의미 설명

---
🕵️‍♂️ **심층 분석: {direction}**
• **[현황]** : {query} 관련 글로벌·국내 동향의 핵심 사실 요약
• **[연결]** : 기술·정책·산업 흐름 간 상호 영향 관계 분석
• **[전망]** : 단기적으로 주목할 변화 방향과 불확실성 설명

---
⚖️ **비판적 시각: 과잉 해석 방지**
• **[한계]** : 오늘 자료만으로 단정하기 어려운 부분 명시
• **[편향]** : 특정 기업·벤더·매체 관점에 치우칠 가능성 점검
• **[공백]** : 추가 확인이 필요한 데이터·공식 근거·시장 반응 제시

---
📚 **주요 참고 문헌 (Sources)**
• [기사/보고서 타이틀], [발행처], [YYYY-MM-DD], [A/B/C/D, 용도]
• [기사/보고서 타이틀], [발행처], [YYYY-MM-DD], [A/B/C/D, 용도]
• [기사/보고서 타이틀], [발행처], [YYYY-MM-DD], [A/B/C/D, 용도]

[데이터]
실시간: {basic_news}

심층: {deep_news}
"""


# 2. 주간 동향 브리핑
WEEKLY_PROMPT_TEMPLATE = """
# ROLE: Strategic Trend Analyst
# REPORT: Weekly Macro Trend Briefing ({report_range})

{common_guide}

📅 **[CPOST] 주간 거시 동향 브리핑**
금주 자료를 관통하는 기술·정책·산업 변화의 핵심 흐름 한 문장

---
📊 **주간 핵심 변화 (The Shift)**
• **[반복 신호]** : 한 주 동안 반복 관측된 주요 흐름 요약
• **[변곡점]** : 기존 흐름과 달라진 정책·시장·기술 신호 분석
• **[불확실성]** : 아직 근거가 부족하거나 해석이 엇갈리는 영역 설명

---
🕵️‍♂️ **글로벌 딥다이브: {macro_theme}**
• **[진단]** : {query} 기반 글로벌 흐름의 구조적 변화 요약
• **[국내 연결]** : 국내 산업·정책·보안 환경과의 접점 분석
• **[지속성]** : 일시적 이슈인지 지속 추세인지 판단 근거 제시

---
⚖️ **비판적 시각: 관성의 위험**
• **[과열]** : 시장·정책 담론에서 과도하게 부풀려진 부분 점검
• **[공백]** : 실제 도입·운영·검증에서 확인되지 않은 영역 제시
• **[차이]** : 해외 동향과 국내 적용 환경의 현실적 차이 설명

---
📚 **주요 참고 문헌 (Sources)**
• [핵심 기사/보고서 타이틀], [발행처], [YYYY-MM-DD], [A/B/C/D, 용도]
• [핵심 기사/보고서 타이틀], [발행처], [YYYY-MM-DD], [A/B/C/D, 용도]
• [핵심 기사/보고서 타이틀], [발행처], [YYYY-MM-DD], [A/B/C/D, 용도]

[데이터]
오늘: {basic_news}

누적: {combined_data}

심층: {deep_news}
"""


# 3. 월간 동향 보고서
MONTHLY_PROMPT_TEMPLATE = """
# ROLE: Chief Strategy Analyst
# REPORT: Monthly Executive Trend Report ({report_range})

{common_guide}

🌐 **[CPOST] 월간 산업 생태계 동향 리포트**
한 달간의 데이터가 보여주는 기술·정책·산업 구조 변화 총평

---
🏛️ **월간 생태계 구조 변화 (Structural Change)**
• **[산업 재편]** : 주요 플레이어·투자·서비스 방향의 변화 요약
• **[거버넌스]** : 정책·규제·표준 논의가 시장에 미친 영향 분석
• **[시장 신호]** : 수익모델·도입률·고객 수요 변화의 관찰 결과

---
🕵️‍♂️ **글로벌 심층 진단: {macro_theme}**
• **[진단]** : {query} 관련 글로벌 선도 흐름과 성숙도 분석
• **[격차]** : 국내외 기술·정책·시장 환경의 차이 설명
• **[지속성]** : 해당 흐름이 일시적 유행인지 구조 변화인지 판단

---
⚖️ **비판적 시각: 생태계의 그림자**
• **[과잉투자]** : 기술 기대와 실제 수익성 간 괴리 점검
• **[도입한계]** : 보안·규제·운영성숙도 측면의 현실적 제약 분석
• **[자료한계]** : 공개자료 기반 분석의 편향과 확인 필요사항 제시

---
📚 **주요 참고 문헌 (Sources)**
• [핵심 기사/보고서 타이틀], [발행처], [YYYY-MM-DD], [A/B/C/D, 용도]
• [핵심 기사/보고서 타이틀], [발행처], [YYYY-MM-DD], [A/B/C/D, 용도]
• [핵심 기사/보고서 타이틀], [발행처], [YYYY-MM-DD], [A/B/C/D, 용도]

[데이터]
오늘: {basic_news}

누적: {combined_data}

심층: {deep_news}
"""