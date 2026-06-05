import logging
import json
import sys
from pathlib import Path

# 파일 직접 실행 시 루트 디렉토리의 모듈(config 등)을 찾을 수 있도록 sys.path에 추가합니다.
sys.path.append(str(Path(__file__).resolve().parent.parent))

from slack_sdk import WebClient
from config.config import Config

logger = logging.getLogger(__name__)

class ReportDispatcher:
    """
    CPOST 리포트 배달부:
    1. 분석 결과를 파일로 저장 (.txt)
    2. 과거 리포트를 읽어와서 맥락 제공 (Accumulation)
    3. AI 텍스트를 슬랙 Block Kit 구조로 변환하여 전송
    """
    def __init__(self):
        self.slack = WebClient(token=Config.SLACK_BOT_TOKEN)
        logger.info("📤 ReportDispatcher 초기화 완료 (Block Kit 모드)")

    def get_accumulated_text(self, report_type):
        """과거 리포트 데이터를 로드하여 분석 맥락을 제공합니다."""
        if report_type == "DAILY":
            source_dir = Config.REPORTS["DAILY"]["DIR"]
        else:
            # 주간은 데일리 데이터를, 월간은 주간 데이터를 참조 (설정에 따름)
            source_key = "DAILY" if report_type == "WEEKLY" else "WEEKLY"
            source_dir = Config.REPORTS[source_key]["DIR"]

        lookback_count = Config.REPORTS[report_type]["LOOKBACK"]
        # 최신 파일 순으로 정렬하여 지정된 개수만큼 로드
        files = sorted(source_dir.glob("*.txt"), reverse=True)[:lookback_count]

        if not files:
            return "참조 가능한 과거 리포트가 없습니다."

        combined = [f"### [참조] {f.stem} ###\n{f.read_text(encoding='utf-8')}" for f in files]
        return "\n\n".join(combined)

    def _convert_to_blocks(self, title, text):
        """
        AI가 생성한 텍스트에서 '---'를 찾아 슬랙 블록 구조로 변환합니다.
        """
        # 🚨 개선 1: AI의 마크다운(**)을 슬랙 마크다운(*)으로 일괄 변환
        text = text.replace("**", "*")

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"🧠 {title}", "emoji": True}
            },
            {"type": "divider"}
        ]

        # '---'를 기준으로 섹션을 나눕니다.
        sections = [s.strip() for s in text.split("---") if s.strip()]

        for i, content in enumerate(sections):
            # 🚨 개선 2: 슬랙 API 에러 방지를 위한 3,000자 제한 방어 로직 (여유 있게 2900자로 컷)
            if len(content) > 2900:
                logger.warning(f"⚠️ 섹션 길이가 너무 깁니다. 슬랙 정책에 의해 잘라냅니다. (현재 길이: {len(content)})")
                content = content[:2900] + "\n\n*[...길이 초과로 내용이 생략되었습니다...]*"

            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": content}
            })

            # 섹션 사이에만 구분선 삽입
            if i < len(sections) - 1:
                blocks.append({"type": "divider"})

        # 하단 정보 추가
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": "📍 _CPOST Intelligence Framework v2.6_"}]
        })

        return blocks

    def save_and_send(self, report_type, today_str, text_content):
        """리포트를 저장하고 슬랙으로 구조화된 메시지를 보냅니다."""
        conf = Config.REPORTS[report_type]

        # 1. 파일 저장 (UTF-8 인코딩 보장)
        file_path = conf["DIR"] / f"{today_str}.txt"
        try:
            file_path.write_text(text_content, encoding='utf-8')
            logger.info(f"💾 리포트 파일 저장 완료: {file_path}")
        except Exception as e:
            logger.error(f"❌ 파일 저장 실패: {e}")

        # 2. 슬랙 전송 (Block Kit 구조화)
        try:
            title = f"[{report_type} INSIGHT] ({today_str})"
            rich_blocks = self._convert_to_blocks(title, text_content)

            self.slack.chat_postMessage(
                channel=conf["CHANNEL"],
                blocks=rich_blocks,
                text=title  # 푸시 알림용 텍스트
            )
            logger.info(f"✅ {report_type} 슬랙 전송 성공 (Block Kit 적용)")
        except Exception as e:
            logger.error(f"❌ 슬랙 전송 실패: {e}")

if __name__ == "__main__":
    # 단독 실행 시 테스트용 코드
    reporter = ReportDispatcher()
    print("✅ ReportDispatcher 초기화 성공")