import json
import logging
from datetime import datetime, timedelta
from urllib.parse import urlsplit, urlunsplit
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
        쿼리에 제외할 사이트 문자열을 추가합니다.
        """
        return f"{query} {self.exclude_str}"

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

    def _normalize_url(self, url):
        """중복 제거를 위해 URL의 querystring과 fragment를 제거합니다."""
        if not url:
            return ""
        parts = urlsplit(url)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))

    def _truncate(self, text, limit=800):
        """프롬프트 과대 입력을 방지하기 위해 본문 길이를 제한합니다."""
        if not text:
            return ""
        return text[:limit] + ("..." if len(text) > limit else "")

    def _search_with_fallback(self, query, search_depth, max_results):
        """
        Tavily 검색을 start_date 파라미터로 시도하고, 실패 시 after: 문자열로 1회 fallback합니다.
        """
        search_days = Config.TAVILY.get("DAYS", 3)
        start_date = (datetime.now() - timedelta(days=search_days)).strftime("%Y-%m-%d")

        try:
            logger.info(f"🔍 Tavily 검색 (start_date={start_date}): {query}")
            return self.tavily.search(
                query=query,
                search_depth=search_depth,
                max_results=max_results,
                start_date=start_date
            )
        except Exception as e:
            logger.warning(f"⚠️ start_date 검색 실패, after 방식으로 1회 재시도: {e}")
            try:
                fallback_query = f"{query} after:{start_date}"
                return self.tavily.search(
                    query=fallback_query,
                    search_depth=search_depth,
                    max_results=max_results
                )
            except Exception as fallback_error:
                logger.error(f"❌ fallback 검색도 실패: {fallback_error}")
                return {"results": []}

    def _normalize_result(self, res, query):
        """Tavily 검색 결과를 표준화된 dict 형식으로 변환합니다."""
        # Tavily는 'publishedDate', 'publish_date', 'date' 등 다양한 키를 사용하므로 순차적으로 확인
        published_date = res.get("publishedDate") or res.get("publish_date") or res.get("date")
        return {
            "title": res.get("title", ""),
            "url": res.get("url", ""),
            "content": res.get("content", ""),
            "published_date": published_date,
            "score": res.get("score"),
            "query": query,
            "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    def _dedupe_items(self, items):
        """URL을 기준으로 중복된 항목을 제거합니다."""
        seen_urls = set()
        deduped = []
        for item in items:
            url = item.get("url")
            key = self._normalize_url(url)
            if not key or key in seen_urls:
                continue
            seen_urls.add(key)
            deduped.append(item)
        return deduped

    def _simple_recency_label(self, published_date_str):
        """발행일에 따라 간단한 최신성 라벨을 부여합니다."""
        if not published_date_str:
            return "날짜 미확인"
        try:
            # 날짜 형식(YYYY-MM-DD)만 사용하도록 파싱
            dt = datetime.fromisoformat(published_date_str.split("T")[0])
            age_days = (datetime.now() - dt).days

            if age_days < 0:
                return "날짜 확인 필요"
            if age_days <= 2:
                return "최근 48시간"
            if age_days <= 7:
                return "최근 7일"
            return "배경자료"
        except (ValueError, TypeError):
            return "날짜 형식 미확인"

    def _format_items_for_prompt(self, items):
        """분석 모델에 전달할 프롬프트용 문자열을 생성합니다."""
        if not items:
            return "검색 결과 없음. 오늘자 신규 자료 또는 관련 최신 자료가 확인되지 않음."

        lines = []
        for item in items:
            lines.append(
                f"제목: {item.get('title')}\n"
                f"발행일: {item.get('published_date') or '미확인'}\n"
                f"최신성: {item.get('recency_label')}\n"
                f"내용: {self._truncate(item.get('content'), 800)}\n"
                f"출처: {item.get('url')}"
            )
        return "\n\n".join(lines)

    # core/collector.py 내부의 해당 메서드만 교체합니다.
    def _search_with_fallback(self, query, search_depth, max_results, topic="general"):
        """
        Tavily 검색을 수행합니다. 1차 broad scan 시에는 topic="news"를 사용하여
        과거 백서가 아닌 실시간 뉴스를 강제 크롤링합니다.
        """
        search_days = Config.TAVILY.get("DAYS", 3)
        start_date = (datetime.now() - timedelta(days=search_days)).strftime("%Y-%m-%d")

        try:
            logger.info(f"🔍 Tavily 검색 시행 (topic={topic}, start_date={start_date}): {query}")
            # topic="news"일 때 start_date 파라미터가 정확히 매칭됩니다.
            return self.tavily.search(
                query=query,
                search_depth=search_depth,
                max_results=max_results,
                topic=topic,
                start_date=start_date
            )
        except Exception as e:
            logger.warning(f"⚠️ Tavily 표준 검색 실패, 일반 Fallback 모드로 전환: {e}")
            try:
                # 실패 시 일반 검색 전 전환하되, 쿼리 내부에 날짜 제약을 강제 주입
                fallback_query = f"{query} after:{start_date}"
                return self.tavily.search(
                    query=fallback_query,
                    search_depth=search_depth,
                    max_results=max_results,
                    topic="general"
                )
            except Exception as fallback_error:
                logger.error(f"❌ Fallback 검색마저 최종 실패: {fallback_error}")
                return {"results": []}

    def get_latest_news_context(self, queries):
        """1차 광범위 뉴스 수집 (Broad Scan) - topic='news' 스펙을 적용하여 최신성 확보"""
        all_normalized_items = []
        all_raw_results = []

        for query in queries:
            try:
                refined_query = self._get_dynamic_query(query)
                # [교정] 1차 스캔은 무조건 최신 뉴스 탭을 뒤지도록 topic="news" 지정
                search_result = self._search_with_fallback(
                    query=refined_query,
                    search_depth=Config.TAVILY.get("SEARCH_DEPTH", "advanced"),
                    max_results=Config.TAVILY.get("MAX_RESULTS", 10),
                    topic="news"
                )

                results = search_result.get('results', [])
                all_raw_results.extend(results)
                for res in results:
                    all_normalized_items.append(self._normalize_result(res, query))
            except Exception as e:
                logger.error(f"❌ 1차 검색 중 오류 발생: {query} - {e}")

        deduped_items = self._dedupe_items(all_normalized_items)
        for item in deduped_items:
            item['recency_label'] = self._simple_recency_label(item.get('published_date'))

        self._save_raw_search_data("Broad_Scan", all_raw_results, suffix="basic")
        return self._format_items_for_prompt(deduped_items)

    def get_deep_dive_context(self, keyword):
        """2차 심층 검색 (Deep-Dive) - 필터 적용"""
        all_normalized_items = []
        all_raw_results = []

        try:
            refined_keyword = self._get_dynamic_query(keyword)
            search_result = self._search_with_fallback(
                query=refined_keyword,
                search_depth="advanced",
                max_results=Config.TAVILY.get("DEEP_MAX_RESULTS", 5)
            )

            results = search_result.get('results', [])
            all_raw_results.extend(results)
            for res in results:
                all_normalized_items.append(self._normalize_result(res, keyword))
        except Exception as e:
            logger.error(f"❌ 2차 심층 검색 중 오류 발생: {keyword} - {e}")
            return "심층 데이터 수집 실패"

        deduped_items = self._dedupe_items(all_normalized_items)
        for item in deduped_items:
            item['recency_label'] = self._simple_recency_label(item.get('published_date'))

        self._save_raw_search_data(keyword, all_raw_results, suffix="deep")
        return self._format_items_for_prompt(deduped_items)