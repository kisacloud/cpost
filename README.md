# 🐦 CPOST (Customizable Periodic Observation & Strategy Tracker)

> **"맥북의 온실을 벗어나, 야생의 마이크로 서버에서도 24시간 멈추지 않는 지능형 리서처"**

CPOST는 **Google Gemini AI**와 **Tavily Search API**를 결합하여 특정 도메인의 뉴스를 수집하고, AI가 스스로 분석 가치를 판단하여 심층 리포트를 발행하는 자동화 엔진입니다. 특히 **1GB RAM**이라는 척박한 클라우드 환경에서도 시스템 중단 없이 구동되도록 설계된 최적화 패키지입니다.

---

## 🌟 핵심 기능 (Key Features)

1. **지능형 다단계 분석 (Two-Pass Analysis)**
   - **1단계 (Screening):** 설정된 키워드로 광범위한 뉴스를 수집하고 핵심을 요약합니다.
   - **2단계 (Deep-Dive):** 1차 요약본을 보고 AI가 "오늘 가장 중요한 뉴스"를 직접 선정, 해당 주제만 타겟팅하여 심층 재조사 및 전략적 시사점을 수립합니다.
2. **자율적 의사결정 (Graceful Refusal)**
   - 수집된 정보의 가치가 낮거나 단순 반복 뉴스일 경우, AI가 스스로 판단하여 분석 시퀀스를 건너뜁니다. 이를 통해 불필요한 API 비용 발생과 Hallucination(환각)을 원천 차단합니다.
3. **마이크로 서버 최적화 (Micro-server Ready)**
   - Docker 메모리 하드 리밋(512MB) 설정을 통해 1GB RAM 서버에서도 전체 시스템의 안정성을 보장합니다.
4. **요일별 섹터 라우팅 (Sector Routing)**
   - 월요일(TECH), 화요일(POLICY) 등 요일마다 서로 다른 산업 분야를 추적하도록 유연한 스케줄링이 가능합니다.
5. **데이터 영속성 보장 (Volume Mounting)**
   - Docker 컨테이너가 교체되거나 서버가 불시에 재부팅되어도, 과거 리포트(JSON/MD)와 실행 로그는 호스트 서버 폴더에 영구 보존됩니다.

---

## 🛠️ 기술 스택 및 환경 (Tech Stack)

- **Language:** Python 3.12.x (Slim-buster 환경 권장)
- **AI Model:** Google Gemini (Stable: gemini-2.0-flash / gemini-1.5-flash 지원)
- **Search Engine:** Tavily AI (Advanced Search Depth 모드 활용)
- **Infra:** Docker & Docker Compose
- **Notification:** Slack Webhook & Python Slack SDK

---

## 📂 프로젝트 구조 (Project Structure)

```text
cpost/
├── core/                # [수정 금지] 시스템의 뇌와 근육
│   ├── analyst.py       # AI 모델 핸들링 및 다단계 프롬프트 실행
│   ├── collector.py     # Tavily 검색 엔진 연동 및 데이터 수집
│   └── reporter.py      # 리포트 파일 생성 및 슬랙 전송 관리
├── config/              # [설정] 시스템의 환경 및 규칙
│   └── config.py        # API 키 로드, 경로 설정, 섹터 스케줄링 정의
├── prompts/             # [중요] AI의 페르소나 및 가이드라인
│   └── base_prompt.py   # AI의 분석 로직과 출력 형식을 결정하는 프롬프트
├── data/                # [Volume] 생성된 리포트(.json, .md) 저장소
├── logs/                # [Volume] 시스템 실행 로그 아카이브
├── main_report.py       # 지휘자 (스케줄러 가동 및 전체 프로세스 오케스트레이션)
├── Dockerfile           # 파이썬 3.12 기반 경량화 이미지 설계도
├── docker-compose.yml   # 컨테이너 배치, 자동 재시작 및 자원 제한 설정
├── build_and_run.sh     # 원클릭 배포/빌드 자동화 스크립트
└── requirements.txt     # 필수 라이브러리 (schedule, slack-sdk, dotenv 등)
```

---

## 🎨 커스터마이징 가이드 (Customization)

### 1. 분석 스케줄 및 키워드 (`config/config.py`)
`SCHEDULE_ROUTING`에서 요일별 섹터 명칭을 변경하고, `SECTOR_CONFIG`에서 각 섹터가 검색할 구체적인 키워드를 수정하세요.

### 2. AI 분석 관점 및 보고서 양식 (`prompts/base_prompt.py`)
`DAILY_PROMPT` 섹션의 지시문을 수정하여 AI가 전문적인 어조를 쓸지, 요약 위주로 할지, 아니면 실질적인 투자 제안을 할지 결정할 수 있습니다.

---

## 📦 설치 및 배포 (Installation)

### 1. 환경 변수 설정
프로젝트 루트에 `.env` 파일을 생성하고 아래 형식을 채웁니다.
```env
GOOGLE_API_KEY=your_key
TAVILY_API_KEY=your_key
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
SLACK_SIGNING_SECRET=...
```

### 2. 배포 및 업데이트 실행
코드나 프롬프트를 수정한 후에는 반드시 아래 스크립트를 실행하여 이미지를 새로 빌드해야 합니다.
```bash
# 실행 권한 부여 (최초 1회)
chmod +x build_and_run.sh

# 빌드 및 배포 실행
./build_and_run.sh
```

---

## ⚠️ 문제 해결 (Troubleshooting)

- **수정 사항이 반영되지 않음:** Docker는 빌드 시점의 코드를 이미지화하여 들고 있습니다. 소스 수정 후에는 반드시 `./build_and_run.sh`를 실행하여 컨테이너를 갱신하십시오.
- **이미지 빌드 중 서버 멈춤:** 1GB RAM 서버의 경우 빌드 과정에서 메모리가 일시적으로 부족할 수 있습니다. 리눅스 Swap 메모리를 2GB 이상 확보하는 것을 강력히 권장합니다.
- **리포트 시간 불일치:** `Dockerfile` 내부의 `TZ=Asia/Seoul` 설정이 올바른지 확인하십시오.

---

## 🔍 실시간 모니터링
컨테이너 내부에서 AI가 현재 어떤 작업을 수행 중인지 확인하려면:
```bash
docker logs -f cpost_active
```