import json
import logging
from datetime import datetime, timedelta
from tavily import TavilyClient
from config.config import Config

logger = logging.getLogger(__name__)

class DataCollector:
    """
    Tavily API 수집 및 원천 데이터 저장 전담 클래스 (블로그 제외 & 날짜 필터링 강화)
    """
    def __init__(self):
        self.tavily = TavilyClient(api_key=Config.TAVILY_API_KEY)
        # 제외할 도메인 리스트 (블로그 등 노이즈 제거)
        self.blacklist = ["tistory.com", "blog.naver.com", "velog.io", "brunch.co.kr"]
        self.exclude_str = " ".join([f"-site:{site}" for site in self.blacklist])
        logger.info("📡 DataCollector 초기화 완료 (블로그 필터링 활성화)")

    def _get_dynamic_query(self, query):
        """
        오늘 날짜와 Config의 LOOKBACK을 기준으로 쿼리를 정제함
        예: 'AI 트렌드' -> 'AI 트렌드 -site:tistory.com ... after:2026-04-24'
        """
        # Config에서 LOOKBACK 기간(일수) 가져오기
        lookback_days = Config.REPORTS.get("DAILY", {}).get("LOOKBACK", 7)

        # 기준 날짜 계산 (오늘 - LOOKBACK 일수)
        start_date = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')

        # 필터와 날짜 연산자 결합
        return f"{query} {self.exclude_str} after:{start_date}"

    def _save_raw_search_data(self, query, results, suffix="raw"):
        """수집된 원천 데이터를 JSON으로 기록"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = Config.RAW_DATA_DIR / f"tavily_{timestamp}_{suffix}.json"

        log_data = {
            "query": query,
            "timestamp": timestamp,
            "type": suffix,
            "results": results
        }

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, ensure_ascii=False, indent=4)
            logger.info(f"💾 원천 데이터({suffix}) 기록 완료: {file_path.name}")
        except Exception as e:
            logger.error(f"❌ 원천 데이터 기록 실패: {e}")

    def get_latest_news_context(self, queries):
        """1차 광범위 뉴스 수집 (Broad Scan) - 날짜 제한 및 블로그 필터 적용"""
        all_news_items = []
        all_raw_results = []

        # Config에서 검색용 days 파라미터 가져오기 (LOOKBACK과 연동)
        search_days = Config.REPORTS.get("DAILY", {}).get("LOOKBACK", 3)

        for query in queries:
            try:
                # 쿼리에 날짜와 사이트 필터 자동 적용
                refined_query = self._get_dynamic_query(query)
                logger.info(f"🔍 Tavily 검색 가동 (필터적용): {refined_query}")

                search_result = self.tavily.search(
                    query=refined_query,
                    search_depth=Config.TAVILY["SEARCH_DEPTH"],
                    max_results=Config.TAVILY["MAX_RESULTS"]
                    # days=search_days  <-- 중복 명령 오류 방지를 위해 삭제함 (after 연산자가 대신 역할 수행)
                )

                results = search_result.get('results', [])
                all_raw_results.extend(results)
                for res in results:
                    item = f"제목: {res['title']}\n내용: {res['content']}\n출처: {res['url']}\n"
                    all_news_items.append(item)
            except Exception as e:
                logger.error(f"❌ 검색 실패: {e}")

        self._save_raw_search_data("Broad_Scan", all_raw_results, suffix="basic")
        return "\n\n".join(all_news_items)

    def get_deep_dive_context(self, keyword):
        """2차 심층 검색 (Deep-Dive) - 필터 적용"""
        refined_keyword = self._get_dynamic_query(keyword)
        logger.info(f"🌊 Tavily 심층(Deep-Dive) 검색 가동: {refined_keyword}")

        try:
            # 심층 검색은 advanced 모드로 고정, 날짜는 동일하게 제한
            search_days = Config.REPORTS.get("DAILY", {}).get("LOOKBACK", 3)
            search_result = self.tavily.search(
                query=refined_keyword,
                search_depth="advanced",
                max_results=5
                # days=search_days <-- 중복 명령 오류 방지를 위해 삭제함
            )

            results = search_result.get('results', [])
            self._save_raw_search_data(keyword, results, suffix="deep")

            items = [f"제목: {res['title']}\n내용: {res['content']}\n출처: {res['url']}\n" for res in results]
            return "\n\n".join(items)
        except Exception as e:
            logger.error(f"❌ 심층 검색 실패: {e}")
            return "심층 데이터 수집 실패"