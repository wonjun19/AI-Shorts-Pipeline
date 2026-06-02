import asyncio
import os
import sys

# 파일명(edge_tts.py)이 라이브러리명과 겹쳐 자기 자신을 임포트하는 문제 방지
_this_dir = os.path.dirname(os.path.abspath(__file__))
_orig_path = sys.path[:]
sys.path = [p for p in sys.path if os.path.abspath(p) != _this_dir]
import edge_tts as _edge_tts
sys.path = _orig_path

import config


async def _synthesize_async(text: str, voice: str, out_path: str) -> None:
    communicate = _edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=config.TTS_RATE,
        volume=config.TTS_VOLUME,
        pitch=config.TTS_PITCH,
    )
    await communicate.save(out_path)


def synthesize(text: str, post_id: str, voice: str = None) -> str:
    """
    텍스트를 음성으로 변환해 파일로 저장 (edge-tts, API 키 불필요).

    Args:
        text: 대본 텍스트
        post_id: 게시글 ID (출력 경로 구성용)
        voice: 화자 (기본값: config.TTS_VOICE)

    Returns:
        str: 저장된 음성 파일 경로 (output/{post_id}/voice.mp3)
    """
    voice = voice or config.TTS_VOICE

    out_dir = os.path.join(config.OUTPUT_DIR, post_id)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "voice.mp3")

    print(f"[tts] 화자: {voice} / {len(text)}자")
    asyncio.run(_synthesize_async(text, voice, out_path))
    print(f"[tts] 저장 완료: {out_path}")
    return out_path
