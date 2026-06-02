import anthropic
import config

SYSTEM_PROMPT = """당신은 유튜브 쇼츠용 연애 썰 작가입니다.
원본 게시글을 쇼츠에 최적화된 대본으로 각색하세요.

규칙:
1. 총 길이: 400~600자 (60초 기준), 반드시 450자 이상 출력할 것
2. 첫 문장은 반드시 강한 후킹으로 시작 (예: "이게 말이 됩니까?", "실화입니다")
3. 구어체, 반말 사용 (예: ~했어, ~더라고, ~잖아)
4. 원본 사실관계는 유지하되 극적으로 재구성
5. 마지막 문장은 여운/공감 유도로 마무리
6. 등장인물은 익명 처리 (A, B 또는 남자친구, 여자친구 등)
7. 특정 커뮤니티, 사이트 언급 금지"""

MIN_SCRIPT_LENGTH = 400


def _call_api(client: anthropic.Anthropic, user_prompt: str) -> str:
    message = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=config.CLAUDE_MAX_TOKENS,
        temperature=config.CLAUDE_TEMPERATURE,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return message.content[0].text.strip()


def rewrite(post: dict) -> dict:
    """
    원본 게시글을 쇼츠 대본으로 각색.
    글자수 400자 미만이면 1회 재시도.

    Args:
        post: {"title": str, "content": str, "views": int, "comments": int, "url": str, "post_id": str}

    Returns:
        {"original": dict, "script": str, "retried": bool}
    """
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    user_prompt = f"다음 게시글을 쇼츠 대본으로 각색해줘:\n\n제목: {post['title']}\n내용: {post['content']}"

    script = _call_api(client, user_prompt)
    retried = False

    if len(script) < MIN_SCRIPT_LENGTH:
        print(f"[rewriter] 글자수 부족 ({len(script)}자) → 재시도")
        retry_prompt = (
            f"{user_prompt}\n\n"
            f"(이전 결과가 {len(script)}자로 너무 짧았습니다. 반드시 450자 이상으로 작성하세요.)"
        )
        script = _call_api(client, retry_prompt)
        retried = True

    return {"original": post, "script": script, "retried": retried}
