"""
crawler/fmkorea.py
에펨코리아 연애 게시판 크롤러 (Playwright + playwright-stealth)
"""

import random
import re
import time
from typing import Optional

from playwright.sync_api import (
    Page,
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
)
from playwright_stealth import Stealth

import config

_BOARD_URL = config.FMKOREA_URL   # https://www.fmkorea.com/index.php?mid=love
_BASE_URL  = "https://www.fmkorea.com"

_STEALTH = Stealth(
    navigator_languages_override=("ko-KR", "ko"),
    navigator_platform_override="Win32",
)

# ── 유틸 ───────────────────────────────────────────────────────────────────

def _extract_post_id(url: str) -> Optional[str]:
    """URL에서 document_srl(게시글 ID) 추출."""
    m = re.search(r"fmkorea\.com/(\d{6,})", url)
    if m:
        return m.group(1)
    m = re.search(r"document_srl=(\d+)", url)
    if m:
        return m.group(1)
    return None


def _to_int(text: str) -> int:
    """'1,234' 형태 숫자 문자열 → int. 실패 시 0."""
    digits = re.sub(r"[^\d]", "", text.strip())
    return int(digits) if digits else 0


def _sleep():
    """요청 간격 2~3초 랜덤 대기 (서버 부하 방지)."""
    time.sleep(random.uniform(config.CRAWL_DELAY_MIN, config.CRAWL_DELAY_MAX))


# ── 목록 페이지 파싱 ────────────────────────────────────────────────────────

def _get_post_links(page: Page) -> list:
    """목록 페이지에서 게시글 URL 추출 (공지 제외)."""
    hrefs = []

    # FMKorea XE 게시판: td.title 안의 첫 번째 <a> 가 본문 링크
    candidates = [
        "table.bd_lst td.title a:not([class])",   # class 없는 본문 링크
        "table.bd_lst td.title a",
        ".bd_lst td.title a",
        "td.title > a:first-child",
    ]

    for sel in candidates:
        for el in page.query_selector_all(sel):
            href = el.get_attribute("href") or ""
            if not href:
                continue
            if href.startswith("/"):
                href = _BASE_URL + href
            if _extract_post_id(href):
                hrefs.append(href)
        if hrefs:
            break

    # 폴백: 전체 <a> 에서 numeric ID 패턴
    if not hrefs:
        for el in page.query_selector_all("a[href]"):
            href = el.get_attribute("href") or ""
            if re.search(r"fmkorea\.com/\d{6,}", href) or re.match(r"/\d{6,}$", href):
                if href.startswith("/"):
                    href = _BASE_URL + href
                hrefs.append(href)

    # 중복 제거 (순서 유지)
    seen, unique = set(), []
    for href in hrefs:
        pid = _extract_post_id(href)
        if pid and pid not in seen:
            seen.add(pid)
            unique.append(href)

    return unique


# ── 개별 게시글 파싱 ────────────────────────────────────────────────────────

def _parse_post(page: Page, url: str) -> Optional[dict]:
    """
    게시글 페이지 파싱.

    실제 FMKorea HTML 구조 (확인된 셀렉터):
      - 제목     : h1.np_18px  (span 안에 텍스트)
      - 본문     : .xe_content  (img/video/iframe 제거 후 텍스트)
      - 조회수   : .rd_hd .btm_area .side.fr 안의 첫 번째 <b>
      - 댓글수   : .rd_hd .btm_area .side.fr 안의 두 번째 <b>

    필수 필드(title·content) 누락 시 None 반환.
    """
    post_id = _extract_post_id(url)
    if not post_id:
        return None

    # ── 제목 ──
    title = ""
    for sel in ["h1.np_18px", "h1.np_18", ".rd_hd h1", "h1"]:
        el = page.query_selector(sel)
        if el:
            t = el.inner_text().strip()
            if t:
                title = t
                break

    # ── 본문 (이미지·미디어·첨부파일 제거) ──
    content = ""
    for sel in [".xe_content", ".rd_body .xe_content", ".article .xe_content"]:
        el = page.query_selector(sel)
        if el:
            page.evaluate(
                """el => el.querySelectorAll(
                    'img, video, iframe, .fileAttach, figure, .file_attach'
                ).forEach(e => e.remove())""",
                el,
            )
            c = el.inner_text().strip()
            if c:
                content = c
                break

    if not title or not content:
        return None

    # ── 조회수 / 댓글수 (.rd_hd .btm_area .side.fr b[0], b[1]) ──
    views, comments = 0, 0
    stat_els = page.query_selector_all(".rd_hd .btm_area .side.fr b")
    if len(stat_els) >= 1:
        views = _to_int(stat_els[0].inner_text())
    if len(stat_els) >= 2:
        comments = _to_int(stat_els[1].inner_text())

    # 폴백: 본문 텍스트 패턴 검색
    if views == 0 and comments == 0:
        body_text = page.inner_text("body")
        m = re.search(r"조회\s*[:\s수]?\s*([\d,]+)", body_text)
        if m:
            views = _to_int(m.group(1))
        m = re.search(r"댓글\s*[:\s]?\s*([\d,]+)", body_text)
        if m:
            comments = _to_int(m.group(1))

    return {
        "title": title,
        "content": content,
        "views": views,
        "comments": comments,
        "url": url,
        "post_id": post_id,
    }


# ── 메인 크롤러 ─────────────────────────────────────────────────────────────

def crawl(max_posts: int = None) -> list:
    """
    에펨코리아 연애 게시판 게시글 수집.

    Args:
        max_posts: 크롤링할 최대 게시글 수 (기본값: config.MAX_POSTS)

    Returns:
        List[Dict] — title, content, views, comments, url, post_id
    """
    if max_posts is None:
        max_posts = config.MAX_POSTS

    results = []

    with _STEALTH.use_sync(sync_playwright()) as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="ko-KR",
            timezone_id="Asia/Seoul",
        )
        page = context.new_page()

        # ── 목록 페이지 로드 ──
        print(f"[crawler] 목록 로드: {_BOARD_URL}")
        try:
            page.goto(_BOARD_URL, timeout=30_000, wait_until="domcontentloaded")
            page.wait_for_timeout(2_000)
        except PlaywrightTimeoutError:
            print("[crawler] 목록 페이지 타임아웃 — 중단")
            browser.close()
            return results

        links = _get_post_links(page)
        print(f"[crawler] 수집된 링크 수: {len(links)}")

        if not links:
            print("[crawler] 링크를 찾지 못했습니다. 셀렉터를 확인하세요.")
            browser.close()
            return results

        # ── 개별 게시글 순회 ──
        target = links[:max_posts]
        for i, url in enumerate(target, start=1):
            _sleep()
            print(f"[crawler] ({i}/{len(target)}) {url}")

            try:
                page.goto(url, timeout=30_000, wait_until="domcontentloaded")
                page.wait_for_timeout(1_000)
            except PlaywrightTimeoutError:
                print(f"[crawler] 타임아웃 스킵: {url}")
                continue

            try:
                post = _parse_post(page, url)
            except Exception as e:
                print(f"[crawler] 파싱 오류 스킵: {url} — {e}")
                continue

            if post is None:
                print(f"[crawler] 필수 필드 누락 스킵: {url}")
                continue

            results.append(post)
            print(
                f"[crawler] 수집: 조회 {post['views']:,} / 댓글 {post['comments']} "
                f"/ 본문 {len(post['content'])}자"
            )

        browser.close()

    print(f"[crawler] 완료 - 총 {len(results)}개 수집")
    return results
