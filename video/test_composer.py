"""
4단계 테스트: video/composer.py
- 기존 TTS 음성(output/sample/voice.mp3)이 없으면 edge-tts로 먼저 생성
- 생성된 음성으로 영상 합성 검증
"""

import os
import sys

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from video.composer import compose


SAMPLE_POST_ID = "sample"
SAMPLE_SCRIPT = (
    "이게 말이 됩니까? 남자친구가 3년 동안 매달 용돈을 받아갔어. "
    "처음엔 잠깐 어렵다길래 도와줬는데, 어느 순간 당연한 게 되더라고. "
    "결국 내가 먼저 헤어지자고 했지. 근데 헤어지고 나서 더 잘 살더라. "
    "지금 생각하면 그때 바로 끊었어야 했는데, 왜 그렇게 오래 참았는지 모르겠어."
)


def ensure_voice(post_id: str, script: str) -> str:
    """voice.mp3 없으면 TTS로 생성 후 경로 반환."""
    import config
    voice_path = os.path.join(config.OUTPUT_DIR, post_id, "voice.mp3")
    if os.path.isfile(voice_path):
        print(f"[test] 기존 음성 파일 사용: {voice_path}")
        return voice_path

    print("[test] voice.mp3 없음 → edge-tts로 생성 중...")
    from tts.edge_tts import synthesize
    return synthesize(script, post_id)


def test_compose():
    audio_path = ensure_voice(SAMPLE_POST_ID, SAMPLE_SCRIPT)

    print("\n[test] 영상 합성 시작")
    output = compose(
        script=SAMPLE_SCRIPT,
        audio_path=audio_path,
        post_id=SAMPLE_POST_ID,
    )

    assert os.path.isfile(output), f"출력 파일 없음: {output}"
    size_mb = os.path.getsize(output) / 1_000_000
    print(f"\n[test] 완료: {output} ({size_mb:.2f} MB)")
    print("[test] PASS")


if __name__ == "__main__":
    test_compose()
