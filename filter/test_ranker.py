"""
5단계 단위 테스트: filter/ranker.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from filter.ranker import rank

# ── 더미 데이터 ────────────────────────────────────────────────────────────

LONG_CONTENT   = "가" * 500   # 500자 (기준 충족)
SHORT_CONTENT  = "가" * 100   # 100자 (MIN_CONTENT_LENGTH 미달)
TOO_LONG       = "가" * 2100  # 2100자 (MAX_CONTENT_LENGTH 초과)

DUMMY_POSTS = [
    # 통과 예상 (score 높은 순)
    {
        "post_id": "A",
        "title": "1등 예상 게시글",
        "content": LONG_CONTENT,
        "views": 20000,
        "comments": 150,
        "url": "https://example.com/A",
    },
    {
        "post_id": "B",
        "title": "2등 예상 게시글",
        "content": LONG_CONTENT,
        "views": 10000,
        "comments": 80,
        "url": "https://example.com/B",
    },
    {
        "post_id": "C",
        "title": "3등 예상 게시글",
        "content": LONG_CONTENT,
        "views": 8000,
        "comments": 50,
        "url": "https://example.com/C",
    },
    {
        "post_id": "D",
        "title": "4등 (상위 3개에서 밀림)",
        "content": LONG_CONTENT,
        "views": 6000,
        "comments": 25,
        "url": "https://example.com/D",
    },
    # 필터 탈락 케이스
    {
        "post_id": "FAIL_VIEWS",
        "title": "조회수 미달",
        "content": LONG_CONTENT,
        "views": config.MIN_VIEWS - 1,
        "comments": 100,
        "url": "https://example.com/FAIL_VIEWS",
    },
    {
        "post_id": "FAIL_COMMENTS",
        "title": "댓글수 미달",
        "content": LONG_CONTENT,
        "views": config.MIN_VIEWS + 1000,
        "comments": config.MIN_COMMENTS - 1,
        "url": "https://example.com/FAIL_COMMENTS",
    },
    {
        "post_id": "FAIL_SHORT",
        "title": "본문 너무 짧음",
        "content": SHORT_CONTENT,
        "views": 10000,
        "comments": 50,
        "url": "https://example.com/FAIL_SHORT",
    },
    {
        "post_id": "FAIL_LONG",
        "title": "본문 너무 길음",
        "content": TOO_LONG,
        "views": 10000,
        "comments": 50,
        "url": "https://example.com/FAIL_LONG",
    },
]


# ── 헬퍼 ───────────────────────────────────────────────────────────────────

def _expected_score(views: int, comments: int) -> float:
    return (views * 0.6) + (comments * 100 * 0.4)


# ── 테스트 함수 ─────────────────────────────────────────────────────────────

def test_filter_and_top3():
    """통과/탈락 필터링 + 상위 3개 반환 검증."""
    result = rank(DUMMY_POSTS)

    assert len(result) == 3, f"상위 3개여야 하는데 {len(result)}개 반환"

    # 반환 순서: score 내림차순
    scores = [p["score"] for p in result]
    assert scores == sorted(scores, reverse=True), "score 내림차순 정렬 위반"

    # 1등 검증
    assert result[0]["post_id"] == "A", f"1등이 A여야 하는데: {result[0]['post_id']}"

    # 필터 탈락 post_id가 결과에 없어야 함
    fail_ids = {"FAIL_VIEWS", "FAIL_COMMENTS", "FAIL_SHORT", "FAIL_LONG"}
    for p in result:
        assert p["post_id"] not in fail_ids, f"탈락해야 할 게시글이 포함됨: {p['post_id']}"

    print("[test] test_filter_and_top3 PASS")


def test_score_formula():
    """score 공식 정확도 검증."""
    result = rank(DUMMY_POSTS)
    for p in result:
        expected = _expected_score(p["views"], p["comments"])
        assert abs(p["score"] - expected) < 1e-9, (
            f"post_id={p['post_id']} score 불일치: {p['score']} != {expected}"
        )
    print("[test] test_score_formula PASS")


def test_empty_input():
    """빈 입력 → 빈 리스트 반환."""
    result = rank([])
    assert result == [], f"빈 리스트여야 하는데: {result}"
    print("[test] test_empty_input PASS")


def test_all_filtered_out():
    """모든 게시글이 필터 탈락 → 빈 리스트."""
    bad_posts = [
        {
            "post_id": f"bad_{i}",
            "title": "탈락",
            "content": SHORT_CONTENT,   # 100자 → 탈락
            "views": 1,
            "comments": 1,
            "url": "https://example.com",
        }
        for i in range(5)
    ]
    result = rank(bad_posts)
    assert result == [], f"빈 리스트여야 하는데: {result}"
    print("[test] test_all_filtered_out PASS")


def test_fewer_than_3():
    """통과 게시글이 3개 미만이면 있는 만큼만 반환."""
    two_posts = [
        {
            "post_id": "X",
            "title": "첫 번째",
            "content": LONG_CONTENT,
            "views": 10000,
            "comments": 50,
            "url": "https://example.com/X",
        },
        {
            "post_id": "Y",
            "title": "두 번째",
            "content": LONG_CONTENT,
            "views": 8000,
            "comments": 30,
            "url": "https://example.com/Y",
        },
    ]
    result = rank(two_posts)
    assert len(result) == 2, f"2개여야 하는데 {len(result)}개 반환"
    print("[test] test_fewer_than_3 PASS")


# ── 실행 ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_filter_and_top3()
    test_score_formula()
    test_empty_input()
    test_all_filtered_out()
    test_fewer_than_3()
    print("\n모든 테스트 통과")
