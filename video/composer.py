import os
import re
import subprocess

import config


# ── 내부 헬퍼 ──────────────────────────────────────────────────────────────

def _get_audio_duration(audio_path: str) -> float:
    """ffprobe로 음성 파일 길이(초) 반환."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def _split_sentences(text: str) -> list:
    """대본을 문장 단위로 분할 (. ! ? ~ 기준)."""
    parts = re.split(r'(?<=[.!?~])\s*', text.strip())
    return [p.strip() for p in parts if p.strip()]


def _calculate_timings(sentences: list, total_duration: float) -> list:
    """각 문장의 (시작초, 끝초, 텍스트) 타이밍 계산 — 글자수 비례."""
    total_chars = sum(len(s) for s in sentences)
    if total_chars == 0:
        return []
    timings, current = [], 0.0
    for s in sentences:
        dur = (len(s) / total_chars) * total_duration
        timings.append((current, current + dur, s))
        current += dur
    return timings


def _wrap_ass(text: str, max_chars: int = config.SUBTITLE_MAX_CHARS_PER_LINE) -> str:
    """ASS 자막용 줄바꿈 (\\N 태그). 최대 글자수 기준으로 분할."""
    lines = []
    while len(text) > max_chars:
        lines.append(text[:max_chars])
        text = text[max_chars:]
    if text:
        lines.append(text)
    return r"\N".join(lines)   # ASS 개행 태그


def _sec_to_ass(t: float) -> str:
    """초 → ASS 타임스탬프 형식 (H:MM:SS.xx)."""
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _write_ass(timings: list, out_dir: str) -> str:
    """ASS 자막 파일을 생성하고 경로를 반환.

    drawtext 필터 대신 ASS 파일을 사용하면:
    - Windows 드라이브 경로('C:/')의 콜론 이스케이프 문제 없음 (폰트 이름 사용)
    - enable='between(t,...)' 콤마가 filter chain 구분자로 오파싱되는 문제 없음
    """
    ass_path = os.path.join(out_dir, "subtitles.ass")

    # 자막 세로 위치: SUBTITLE_Y_RATIO(0.75) 지점 → 아래 마진 = HEIGHT * (1 - 0.75)
    margin_v = int(config.VIDEO_HEIGHT * (1.0 - config.SUBTITLE_Y_RATIO))

    # ASS 색상 포맷: &HAABBGGRR  (A=0x00 완전불투명, 0xFF 완전투명)
    # BackColour &H80000000 → 알파 0x80(128) = 50% 반투명 검정 배경
    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {config.VIDEO_WIDTH}\n"
        f"PlayResY: {config.VIDEO_HEIGHT}\n"
        "WrapStyle: 0\n"
        "\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        # BorderStyle=3: 글자 뒤에 불투명(반투명) 박스 배경 표시
        f"Style: Default,Malgun Gothic,{config.SUBTITLE_FONT_SIZE},"
        f"&H00FFFFFF,&H000000FF,&H00000000,&H80000000,"
        f"-1,0,0,0,100,100,0,0,3,0,0,"
        f"2,30,30,{margin_v},1\n"  # Alignment=2 (하단 중앙)
        "\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )

    events = []
    for start, end, text in timings:
        wrapped = _wrap_ass(text)
        events.append(
            f"Dialogue: 0,{_sec_to_ass(start)},{_sec_to_ass(end)},"
            f"Default,,0,0,0,,{wrapped}"
        )

    with open(ass_path, "w", encoding="utf-8-sig") as f:
        f.write(header + "\n".join(events) + "\n")

    return ass_path


# ── 공개 API ───────────────────────────────────────────────────────────────

def compose(script: str, audio_path: str, post_id: str) -> str:
    """TTS 음성 + 자막을 합쳐 최종 쇼츠 영상 생성.

    Args:
        script:     각색된 대본 텍스트
        audio_path: TTS 음성 파일 경로 (voice.mp3)
        post_id:    게시글 ID (출력 경로 구성용)

    Returns:
        str: 최종 영상 파일 경로 (output/{post_id}/final.mp4)
    """
    out_dir = os.path.join(config.OUTPUT_DIR, post_id)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "final.mp4")

    # 1. 음성 길이 파악
    total_duration = _get_audio_duration(audio_path)
    print(f"[video] 음성 길이: {total_duration:.2f}초")

    # 2. 문장 분할 → 타이밍 계산
    sentences = _split_sentences(script)
    timings = _calculate_timings(sentences, total_duration)
    print(f"[video] 자막 문장 수: {len(sentences)}")

    # 3. ASS 자막 파일 생성
    ass_path = _write_ass(timings, out_dir)
    # FFmpeg에 상대경로로 전달 (Windows 드라이브 콜론 이스케이프 불필요)
    ass_rel = os.path.relpath(ass_path).replace("\\", "/")
    print(f"[video] ASS 자막: {ass_rel}")

    # 4. FFmpeg 실행
    # -vf "ass=..." 으로 자막 번인 (burn-in)
    bg_input = (
        f"color=c={config.VIDEO_BG_COLOR}"
        f":size={config.VIDEO_WIDTH}x{config.VIDEO_HEIGHT}"
        f":rate={config.VIDEO_FPS}"
    )
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", bg_input,
        "-i", audio_path,
        "-vf", f"ass={ass_rel}",
        "-shortest",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-pix_fmt", "yuv420p",
        out_path,
    ]

    print("[video] FFmpeg 실행 중...")
    subprocess.run(cmd, check=True)
    print(f"[video] 저장 완료: {out_path}")
    return out_path
