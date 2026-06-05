# 🐦 CPOST (Customizable Periodic Observation & Strategy Tracker)

> **"맥북의 온실을 벗어나, 야생의 마이크로 서버에서도 멈추지 않는 지능형 리서처"**

CPOST는 **Google Gemini AI**와 **Tavily Search API**를 결합하여 특정 도메인의 뉴스를 수집하고, AI가 스스로 분석 가치를 판단하여 심층 리포트를 발행하는 자동화 엔진입니다.
특히 **1GB RAM**이라는 척박한 클라우드 환경(e2-micro 등)에서 메모리 누수나 OOM(Out of Memory) 강제 종료 없이 구동되도록 설계된 **초경량 최적화 패키지**입니다.

---

## 🌟 핵심 기능 (Key Features)

1. **지능형 다단계 분석 (Two-Pass Analysis)**
   - **1단계 (Screening):** 설정된 키워드로 광범위한 뉴스를 수집하고 핵심을 요약합니다.
   - **2단계 (Deep-Dive):** 1차 요약본을 보고 AI가 "오늘 가장 중요한 뉴스"를 직접 선정, 해당 주제만 타겟팅하여 심층 재조사 및 전략적 시사점을 수립합니다.
2. **자율적 의사결정 (Graceful Refusal)**
   - 수집된 정보의 가치가 낮거나 단순 반복 뉴스일 경우, AI가 스스로 판단하여 분석 시퀀스를 건너뜁니다. 이를 통해 불필요한 API 비용 발생과 환각(Hallucination)을 차단합니다.
3. **마이크로 서버 최적화 (Micro-server Ready)**
   - 무거운 도커(Docker) 데몬이나 24시간 도는 파이썬 무한 루프 스케줄러를 과감히 제거했습니다. 리눅스의 **Crontab**을 통해 필요할 때만 1회성(Batch)으로 깨어나 작업을 수행하므로, 평시 메모리 점유율 **0%**를 유지합니다.
4. **요일별 섹터 라우팅 (Sector Routing)**
   - 월요일(TECH), 화요일(POLICY) 등 요일마다 서로 다른 산업 분야를 추적하도록 유연한 스케줄링이 가능합니다.

---

## 🛠️ 기술 스택 및 환경 (Tech Stack)

- **Language:** Python 3.12.x (가상환경 `.venv` 활용)
- **AI Model:** Google Gemini (Stable: gemini-2.0-flash / gemini-1.5-flash 지원)
- **Search Engine:** Tavily AI (Advanced Search Depth 모드 활용)
- **Infra / Scheduler:** Linux OS & Crontab (Bare-metal Environment)
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
├── data/                # 생성된 리포트(.txt, .md) 영구 저장소
├── logs/                # 시스템 실행 및 크론탭 로그 아카이브
├── main_report.py       # 지휘자 (단발성 Batch 프로세스 오케스트레이션)
└── requirements.txt     # 필수 라이브러리 (slack-sdk, python-dotenv 등)
```

---

## 🎨 커스터마이징 가이드 (Customization)

### 1. 분석 스케줄 및 키워드 (`config/config.py`)
`SCHEDULE_ROUTING`에서 요일별 섹터 명칭을 변경하고, `SECTOR_CONFIG`에서 각 섹터가 검색할 구체적인 키워드를 수정하세요.

### 2. AI 분석 관점 및 보고서 양식 (`prompts/base_prompt.py`)
`DAILY_PROMPT` 섹션의 지시문을 수정하여 AI가 전문적인 어조를 쓸지, 요약 위주로 할지, 아니면 실질적인 투자 제안을 할지 결정할 수 있습니다.

---

## 📦 서버 설치 및 배포 (Installation)

### 1. 코드 다운로드 및 환경 변수 세팅
보안을 위해 `.env` 파일은 깃허브에 올라가지 않습니다. 서버에서 직접 파일을 생성해야 합니다.
```bash
git clone https://github.com/bitsonata/cpost.git
cd cpost
nano .env
```
> **`.env` 필수 항목 내용 (복사해서 붙여넣기):**
> GOOGLE_API_KEY=your_key
> TAVILY_API_KEY=your_key
> SLACK_BOT_TOKEN=xoxb-...
*(입력 후 Ctrl+O, Enter로 저장, Ctrl+X로 종료)*

### 2. 파이썬 가상환경 생성 및 패키지 설치
서버에 접속하여 프로젝트 폴더 내부에 격리된 환경을 구축합니다.
```bash
sudo apt update && sudo apt install python3-venv python3-pip -y
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Crontab 자동화 스케줄 등록
시스템이 매일 정해진 시간에 봇을 깨우도록 리눅스 스케줄러에 등록합니다.
```bash
crontab -e
```
열린 편집기 맨 아랫줄에 아래 명령어를 추가합니다. (경로는 본인 서버 환경에 맞게 수정하세요)
```bash
# 매일 오전 8시에 가상환경의 파이썬으로 리포터 실행 후 로그 기록
0 8 * * * cd /home/계정명/cpost && /home/계정명/cpost/.venv/bin/python main_report.py >> /home/계정명/cpost/logs/cron.log 2>&1
```

---

## ⚠️ 문제 해결 (Troubleshooting)

- **크론탭(Crontab)이 실행되지 않을 때:** 리눅스 환경 변수 문제일 확률이 높습니다. 크론탭 설정에 적은 `cd` 경로와 `python` 실행 파일 경로가 **절대 경로(Absolute Path)**인지 꼭 확인하세요.
- **수동 테스트를 하고 싶을 때:** 서버 터미널에서 `source .venv/bin/activate` 후 `python main_report.py`를 직접 치면 즉각 실행됩니다.

## 🔍 실시간 로그 모니터링
봇이 정해진 시간에 작동하면서 남긴 로그를 확인하려면 아래 명령어를 사용하세요.
```bash
tail -f logs/cron.log
```