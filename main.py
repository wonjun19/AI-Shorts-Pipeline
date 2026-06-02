"""
main.py — AI 쇼츠 파이프라인 진입점

--step 은 필수 인수입니다. 단계 순서:

    python main.py --step crawl    # 게시글 수집
    python main.py --step rank     # 필터링 및 랭킹
    python main.py --step script   # Claude 각색 → script.json 생성
    [수동] Ideogram에서 이미지 생성 → output/{post_id}/images/scene_N.png 저장
    python main.py --step tts      # TTS 음성 생성
    python main.py --step video    # FFmpeg 영상 합성

단계 간 중간 결과 저장 위치:
  - crawl/rank: output/temp/pipeline_state.json (post_id 미확정)
  - rank 완료 이후: output/{post_id}/pipeline_state.json 으로 이동 (포인터 없음)
"""

import argparse
import glob
import json
import os
import sys
import traceback
from datetime import datetime

import config
from crawler.fmkorea import crawl as _crawl
from filter.ranker import rank as _rank, mark_as_used
from script.rewriter import rewrite as _rewrite
from tts.edge_tts import synthesize as _synthesize
from video.composer import compose as _compose

# ── 상태 파일 경로 ─────────────────────────────────────────────────────────

_TEMP_STATE_PATH = os.path.join(config.OUTPUT_DIR, "temp", "pipeline_state.json")


def _get_post_id(state: dict) -> str | None:
    """state에서 post_id 추출. 아직 확정 안 됐으면 None."""
    if rewritten := state.get("rewritten"):
        return rewritten["original"]["post_id"]
    if ranked := state.get("ranked"):
        return ranked[0]["post_id"]
    return None


def _post_state_path(post_id: str) -> str:
    return os.path.join(config.OUTPUT_DIR, post_id, "pipeline_state.json")


# ── 로깅 유틸 ──────────────────────────────────────────────────────────────

def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(step: str, msg: str) -> None:
    print(f"[{_ts()}] [{step}] {msg}", flush=True)


# ── 상태 저장/로드 ─────────────────────────────────────────────────────────

def _save_state(state: dict) -> None:
    post_id = _get_post_id(state)
    if post_id:
        dest = _post_state_path(post_id)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        # temp 파일이 아직 남아있으면 제거 (이미 post_id 폴더로 이동 완료)
        if os.path.exists(_TEMP_STATE_PATH):
            os.remove(_TEMP_STATE_PATH)
    else:
        os.makedirs(os.path.dirname(_TEMP_STATE_PATH), exist_ok=True)
        with open(_TEMP_STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)


def _load_state(post_id: str | None = None) -> dict:
    # --post-id 명시: glob 없이 직접 로드
    if post_id:
        path = _post_state_path(post_id)
        if not os.path.exists(path):
            log("main", f"오류 - {path} 를 찾을 수 없습니다.")
            sys.exit(1)
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    # post_id 미확정: temp 파일
    if os.path.exists(_TEMP_STATE_PATH):
        with open(_TEMP_STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    # fallback: glob (소재 하나만 있을 때만 안전 — 여러 개면 --post-id 사용 권장)
    matches = glob.glob(os.path.join(config.OUTPUT_DIR, "*", "pipeline_state.json"))
    if len(matches) == 1:
        with open(matches[0], "r", encoding="utf-8") as f:
            return json.load(f)
    if len(matches) > 1:
        log("main", "오류 - 여러 소재의 state 파일이 존재합니다. --post-id 를 명시하세요.")
        sys.exit(1)
    return {}


# ── 각 단계 구현 ────────────────────────────────────────────────────────────

def step_crawl(state: dict) -> dict:
    """게시글 수집."""
    log("crawl", "시작")
    posts = _crawl()
    log("crawl", f"완료 - {len(posts)}개 수집")
    state["posts"] = posts
    _save_state(state)
    return state


def step_rank(state: dict) -> dict:
    """필터링 및 랭킹 (상위 3개 선별)."""
    posts = state.get("posts")
    if not posts:
        log("rank", "오류 - 크롤링 결과(posts)가 없습니다. crawl 단계를 먼저 실행하세요.")
        sys.exit(1)

    log("rank", "시작")
    ranked = _rank(posts)
    if not ranked:
        log("rank", "완료 - 조건을 만족하는 게시글이 없습니다.")
    else:
        log("rank", f"완료 - 상위 {len(ranked)}개 선별 (1위 score={ranked[0]['score']:.0f})")
    state["ranked"] = ranked
    _save_state(state)
    return state


def step_script(state: dict) -> dict:
    """상위 1개 게시글을 Claude API로 각색."""
    ranked = state.get("ranked")
    if not ranked:
        log("script", "오류 - 랭킹 결과(ranked)가 없습니다. rank 단계를 먼저 실행하세요.")
        sys.exit(1)

    top = ranked[0]
    log("script", f"시작 - '{top['title'][:30]}...' (post_id={top['post_id']})")
    result = _rewrite(top)
    script_len = len(result["script"])
    retry_msg = " (재시도 있었음)" if result.get("retried") else ""
    log("script", f"완료 - {script_len}자 대본 생성{retry_msg}")
    state["rewritten"] = result
    _save_state(state)
    return state


def step_tts(state: dict) -> dict:
    """각색된 대본을 TTS로 음성 변환."""
    rewritten = state.get("rewritten")
    if not rewritten:
        log("tts", "오류 - 각색 결과(rewritten)가 없습니다. script 단계를 먼저 실행하세요.")
        sys.exit(1)

    post_id = rewritten["original"]["post_id"]
    script = rewritten["script"]
    log("tts", f"시작 - {len(script)}자 / post_id={post_id}")
    audio_path = _synthesize(script, post_id)
    log("tts", f"완료 - {audio_path}")
    state["audio_path"] = audio_path
    _save_state(state)
    return state


def step_video(state: dict) -> dict:
    """TTS 음성 + 자막으로 최종 영상 합성."""
    rewritten = state.get("rewritten")
    audio_path = state.get("audio_path")
    if not rewritten or not audio_path:
        log("video", "오류 - 대본(rewritten) 또는 음성(audio_path)이 없습니다. script/tts 단계를 먼저 실행하세요.")
        sys.exit(1)

    post_id = rewritten["original"]["post_id"]
    script = rewritten["script"]
    log("video", f"시작 - post_id={post_id}")
    video_path = _compose(script, audio_path, post_id)
    mark_as_used(post_id)
    log("video", f"완료 - {video_path}")
    state["video_path"] = video_path
    _save_state(state)
    return state


# ── 단계 레지스트리 ────────────────────────────────────────────────────────

_STEPS: dict = {
    "crawl":  step_crawl,
    "rank":   step_rank,
    "script": step_script,
    "tts":    step_tts,
    "video":  step_video,
}

_STEP_ORDER = list(_STEPS.keys())


def run_step(step_name: str, post_id: str | None = None) -> None:
    """특정 단계만 실행. 이전 상태는 pipeline_state.json 에서 로드."""
    log("main", f"=== 단일 단계 실행: {step_name} ===")
    state = _load_state(post_id)
    try:
        state = _STEPS[step_name](state)
        log("main", f"=== {step_name} 완료 ===")
    except SystemExit:
        raise
    except Exception:
        log("main", f"=== {step_name} 실패 ===")
        traceback.print_exc()
        sys.exit(1)


# ── 진입점 ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="AI 쇼츠 자동화 파이프라인",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="단계 목록: " + ", ".join(_STEP_ORDER),
    )
    parser.add_argument(
        "--step",
        choices=_STEP_ORDER,
        metavar="STEP",
        required=True,
        help=f"실행할 단계 ({', '.join(_STEP_ORDER)})",
    )
    parser.add_argument(
        "--post-id",
        metavar="POST_ID",
        default=None,
        help="로드할 state의 post_id. 소재가 여러 개 쌓인 경우 명시 필요.",
    )
    args = parser.parse_args()
    run_step(args.step, args.post_id)
