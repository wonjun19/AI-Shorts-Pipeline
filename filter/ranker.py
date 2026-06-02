import json
import os
import config

USED_POSTS_PATH = os.path.join(config.OUTPUT_DIR, "used_posts.json")


def _load_used_ids() -> set:
    if not os.path.exists(USED_POSTS_PATH):
        return set()
    with open(USED_POSTS_PATH, "r", encoding="utf-8") as f:
        return set(json.load(f))


def mark_as_used(post_id: str) -> None:
    """
    영상 합성 완료 후 post_id를 used_posts.json에 기록.
    video/composer.py 끝에서 호출.
    """
    used = _load_used_ids()
    if post_id in used:
        return
    used.add(post_id)
    os.makedirs(os.path.dirname(USED_POSTS_PATH), exist_ok=True)
    with open(USED_POSTS_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted(used), f, ensure_ascii=False, indent=2)
    print(f"[ranker] used_posts 등록: {post_id} (누적 {len(used)}개)")


def rank(posts: list[dict]) -> list[dict]:
    """
    게시글 필터링 → 중복 제외 → 랭킹 → 상위 3개 반환.

    필터 조건:
        - 조회수 >= MIN_VIEWS
        - 댓글수 >= MIN_COMMENTS
        - 본문 200자 이상 2000자 이하
        - used_posts.json에 없는 post_id

    랭킹 점수:
        score = (views * 0.6) + (comments * 100 * 0.4)

    Returns:
        score 내림차순 상위 3개 List[Dict] (score 필드 포함)
    """
    used_ids = _load_used_ids()

    filtered = []
    skip_counts = {"views": 0, "comments": 0, "length": 0, "duplicate": 0}

    for post in posts:
        content_len = len(post.get("content", ""))

        if post.get("views", 0) < config.MIN_VIEWS:
            skip_counts["views"] += 1
            continue
        if post.get("comments", 0) < config.MIN_COMMENTS:
            skip_counts["comments"] += 1
            continue
        if not (config.MIN_CONTENT_LENGTH <= content_len <= config.MAX_CONTENT_LENGTH):
            skip_counts["length"] += 1
            continue
        if post.get("post_id") in used_ids:
            skip_counts["duplicate"] += 1
            continue

        score = (post["views"] * 0.6) + (post["comments"] * 100 * 0.4)
        filtered.append({**post, "score": score})

    print(
        f"[ranker] 전체 {len(posts)}개 → "
        f"조회수 미달 {skip_counts['views']} / "
        f"댓글 미달 {skip_counts['comments']} / "
        f"길이 미달 {skip_counts['length']} / "
        f"중복 {skip_counts['duplicate']} / "
        f"통과 {len(filtered)}개"
    )

    top3 = sorted(filtered, key=lambda p: p["score"], reverse=True)[:3]
    return top3
