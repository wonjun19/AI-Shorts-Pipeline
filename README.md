# AI 쇼츠 자동화 파이프라인 명세서

## 사용법

```bash
# 1. 게시글 수집
python main.py --step crawl

# 2. 필터링 및 랭킹
python main.py --step rank

# 3. Claude 각색 (대본 + 장면 목록 생성)
python main.py --step script
```

여기서 멈추고 `output/pipeline_state.json`의 `scenes[].image_prompt`를 Ideogram에 복붙해서 이미지 생성.
다운받은 이미지를 아래 경로에 저장:

```
output/
└── {post_id}/
    └── images/
        ├── scene_1.png   ← scenes[0]에 대응
        ├── scene_2.png   ← scenes[1]에 대응
        └── scene_3.png   ← scenes[2]에 대응
```

> 파일명은 반드시 `scene_1.png`부터 순서대로, 번호는 1-based.

```bash
# 4. TTS 음성 생성
python main.py --step tts

# 5. 영상 합성
python main.py --step video
# → output/{post_id}/final.mp4 생성
```

**중간 재실행**: 특정 단계만 다시 돌려도 됨. (예: 이미지 교체 후 `--step video`만 재실행)

**상태 파일 저장 위치**:
- `crawl` / `rank` 단계: `output/temp/pipeline_state.json` (post_id 미확정)
- `script` 이후: `output/{post_id}/pipeline_state.json` (post_id 확정 시점부터)
- post_id 확정 시 temp 파일은 자동 삭제됨

---

## 프로젝트 개요

에펨코리아 연애 게시판에서 인기 썰을 수집하고, Claude API로 각색한 뒤, Microsoft Edge TTS + FFmpeg으로 영상을 자동 생성하는 파이프라인.

**목표**: 하루 1개 쇼츠 영상 반자동 생성 (크롤링~영상 생성 자동, 업로드는 수동)

---

## 기술 스택

| 역할 | 도구 |
|---|---|
| 언어 | Python 3.11+ |
| 크롤링 | Playwright + playwright-stealth |
| AI 각색 | Anthropic Claude API (claude-sonnet-4-5) |
| TTS | edge-tts (Microsoft Edge TTS, API 키 불필요) |
| 영상 합성 | FFmpeg (moviepy 래퍼) |
| 환경변수 | python-dotenv |
| 스케줄러 | (추후) APScheduler |

---

## 폴더 구조

```
AI-Shorts-Pipeline/
├── .env                    # API 키 (gitignore)
├── .env.example            # 키 양식 예시
├── requirements.txt
├── main.py                 # 전체 파이프라인 실행 진입점
├── config.py               # 설정값 상수 모음
│
├── crawler/
│   ├── __init__.py
│   └── fmkorea.py          # 에펨코리아 크롤러
│
├── filter/
│   ├── __init__.py
│   ├── ranker.py           # 조회수/댓글수 필터링 및 랭킹
│   └── test_ranker.py      # ranker 테스트
│
├── script/
│   ├── __init__.py
│   ├── rewriter.py         # Claude API 각색
│   └── test_rewriter.py    # rewriter 테스트
│
├── tts/
│   ├── __init__.py
│   ├── edge_tts.py         # Microsoft Edge TTS (edge-tts)
│   └── test_edge_tts.py    # edge_tts 테스트
│
├── video/
│   ├── __init__.py
│   ├── composer.py         # 영상 합성 (FFmpeg)
│   ├── test_composer.py    # composer 테스트
│   └── assets/
│       └── fonts/          # 자막용 폰트 파일 (NanumGothicBold 등, 별도 설치 필요)
│
└── output/                 # 최종 생성 영상 저장 (gitignore)
    └── .gitkeep
```

---

## 환경변수 (.env)

```env
# Anthropic
ANTHROPIC_API_KEY=your_key_here

# 파이프라인 설정
MAX_POSTS=10              # 크롤링할 게시글 수
MIN_VIEWS=5000            # 최소 조회수 필터
MIN_COMMENTS=20           # 최소 댓글수 필터
OUTPUT_DIR=./output
```

---

## API 키 발급 방법

### 1. Anthropic Claude API
1. https://console.anthropic.com 접속
2. 회원가입 후 로그인
3. API Keys 메뉴 → Create Key
4. 발급된 키를 `.env`의 `ANTHROPIC_API_KEY`에 입력

### 2. TTS
edge-tts는 API 키 불필요. `pip install edge-tts`만으로 사용 가능.
- 기본 화자: `ko-KR-SunHiNeural` (여성)
- 남성 화자: `ko-KR-InJoonNeural`
- `config.py`의 `TTS_VOICE`에서 변경 가능

---

## 모듈별 상세 명세

### 1. crawler/fmkorea.py

**역할**: 에펨코리아 연애 게시판 게시글 수집

**목표 URL**: `https://www.fmkorea.com/index.php?mid=love`

**수집 데이터**:
```python
{
    "title": str,        # 게시글 제목
    "content": str,      # 본문 텍스트 (이미지 제외)
    "views": int,        # 조회수
    "comments": int,     # 댓글수
    "url": str,          # 원본 URL
    "post_id": str       # 게시글 고유 ID
}
```

**구현 요구사항**:
- Playwright 헤드리스 모드로 실행
- playwright-stealth 적용 (봇 감지 우회)
- 목록 페이지에서 게시글 링크 추출
- 각 게시글 진입 후 본문/조회수/댓글수 파싱
- 예외처리: 타임아웃, 파싱 실패 시 해당 글 스킵

**반환값**: `List[Dict]`

---

### 2. filter/ranker.py

**역할**: 수집된 게시글 중 영상화 적합 글 선별

**필터링 기준**:
- 조회수 `MIN_VIEWS` 이상
- 댓글수 `MIN_COMMENTS` 이상
- 본문 글자수 200자 이상 (너무 짧은 글 제외)
- 본문 글자수 2000자 이하 (60초 쇼츠 기준 초과 방지)

**랭킹 로직**:
```
score = (views * 0.6) + (comments * 100 * 0.4)
```
댓글수에 100 가중치를 곱해 조회수와 스케일 맞춤

**반환값**: score 기준 내림차순 정렬된 `List[Dict]`, 상위 3개만 반환

---

### 3. script/rewriter.py

**역할**: 원본 썰을 쇼츠용 대본으로 각색

**Claude API 설정**:
- 모델: `claude-sonnet-4-5`
- max_tokens: 1000
- temperature: 0.8

**시스템 프롬프트**:
```
당신은 유튜브 쇼츠용 연애 썰 작가입니다.
원본 게시글을 쇼츠에 최적화된 대본으로 각색하세요.

규칙:
1. 총 길이: 400~600자 (60초 기준)
2. 첫 문장은 반드시 강한 후킹으로 시작 (예: "이게 말이 됩니까?", "실화입니다")
3. 구어체, 반말 사용 (예: ~했어, ~더라고, ~잖아)
4. 원본 사실관계는 유지하되 극적으로 재구성
5. 마지막 문장은 여운/공감 유도로 마무리
6. 등장인물은 익명 처리 (A, B 또는 남자친구, 여자친구 등)
7. 특정 커뮤니티, 사이트 언급 금지
```

**유저 프롬프트**:
```
다음 게시글을 쇼츠 대본으로 각색해줘:

제목: {title}
내용: {content}
```

**반환값**:
```python
{
    "original": Dict,    # 원본 게시글 데이터
    "script": str,       # 각색된 대본 전문
    "scenes": [          # 장면 목록
        {
            "image_prompt": str,  # Ideogram 이미지 생성용 영문 프롬프트
            "start_line": str,    # 이 장면의 시작 대사
            "end_line": str       # 이 장면의 끝 대사
        },
        ...
    ]
}
```

---

### 4. [수동] 이미지 생성 (Ideogram)

**역할**: 각 장면의 배경 이미지를 수동으로 생성 및 선택

**흐름**:
1. `rewriter.py` 출력의 `scenes[].image_prompt`를 Ideogram에 입력
2. 생성된 이미지 중 적합한 것을 선택
3. 파일명 규칙에 맞게 저장:

```
output/{post_id}/images/scene_1.png
output/{post_id}/images/scene_2.png
...
```

**주의**: `scene_N.png`의 번호는 `scenes` 배열 인덱스(1-based)와 일치해야 함

---

### 5. tts/edge_tts.py

**역할**: 대본 텍스트를 음성 파일로 변환

**라이브러리**: edge-tts (Microsoft Edge TTS, API 키 불필요)

**파라미터** (`config.py`):
```python
TTS_VOICE  = "ko-KR-SunHiNeural"  # 여성. 남성: ko-KR-InJoonNeural
TTS_RATE   = "+10%"                # 속도 (쇼츠 특성상 약간 빠르게)
TTS_VOLUME = "+0%"
TTS_PITCH  = "+0Hz"
```

**구현 요구사항**:
- edge-tts가 긴 텍스트를 내부적으로 처리 (별도 청크 분할 불필요)
- 출력 파일: `output/{post_id}/voice.mp3`
- `voice` 파라미터로 화자 런타임 변경 가능

**반환값**: `str` (음성 파일 경로)

---

### 6. video/composer.py

**역할**: TTS 음성 + 자막을 합쳐 최종 쇼츠 영상 생성

**영상 스펙**:
```
해상도: 1080 x 1920 (세로형 9:16)
배경: 단색 (#1a1a2e, 다크 네이비)
프레임레이트: 30fps
포맷: mp4 (H.264)
```

**자막 스펙**:
```
폰트: NanumGothicBold (./assets/fonts/)
크기: 52px
색상: 흰색 (#FFFFFF)
위치: 중앙 하단 (y = 영상 높이의 75%)
줄당 최대 글자수: 18자 (자동 줄바꿈)
배경: 반투명 검정 박스 (가독성)
자막 싱크: 음성 구간에 맞춰 문장 단위로 표시
```

**구현 흐름**:
1. TTS 음성 파일 로드 → 전체 길이 파악
2. 대본을 문장 단위로 분할
3. 글자수 비례로 각 문장의 시작/끝 타임코드 계산
4. `scenes[].start_line` / `end_line` 매칭 → 장면별 이미지 전환 타임코드 확정
5. FFmpeg으로 장면 이미지 + 음성 + 자막 합성
6. 출력: `output/{post_id}/final.mp4`

**FFmpeg 커맨드 구조**:
```bash
ffmpeg -f lavfi -i color=c=#1a1a2e:size=1080x1920:rate=30 \
       -i voice.mp3 \
       -vf "drawtext=..." \
       -shortest -c:v libx264 -c:a aac \
       output/final.mp4
```

**반환값**: `str` (최종 영상 파일 경로)

---

### 7. main.py

**역할**: 단계별 파이프라인 실행 진입점

**`--step` 은 필수 인수.** 인수 없이 실행하면 오류 출력 후 종료.

**실행 순서**:
```bash
python main.py --step crawl    # 게시글 수집
python main.py --step rank     # 필터링 및 랭킹
python main.py --step script   # Claude 각색 → pipeline_state.json 저장
# [수동] Ideogram에서 이미지 생성 → output/{post_id}/images/scene_N.png 저장
python main.py --step tts      # TTS 음성 생성
python main.py --step video    # FFmpeg 영상 합성
```

**로깅**:
- 각 단계 시작/완료 시 타임스탬프와 함께 stdout 출력
- 에러 발생 시 해당 단계 스킵 + 에러 로그 출력 후 계속 진행

---

## 구현 순서 (B 플랜)

크롤러보다 핵심 파이프라인 먼저 검증하는 순서로 진행.

```
1단계: 프로젝트 초기 세팅
   - 폴더 구조 생성
   - requirements.txt 작성
   - .env.example 작성
   - config.py 작성

2단계: script/rewriter.py
   - Claude API 연동
   - 프롬프트 테스트 (하드코딩된 샘플 썰로 먼저 테스트)

3단계: tts/edge_tts.py
   - Edge TTS 연동
   - 샘플 텍스트로 음성 생성 테스트

4단계: video/composer.py
   - FFmpeg 설치 확인
   - 샘플 음성으로 영상 합성 테스트
   - 자막 싱크 검증

5단계: filter/ranker.py
   - 랭킹 로직 구현 및 단위 테스트

6단계: crawler/fmkorea.py
   - Playwright 크롤러 구현
   - Cloudflare 우회 검증

7단계: main.py
   - 전체 파이프라인 연결
   - end-to-end 테스트
```

---

## requirements.txt

```
anthropic
edge-tts
playwright
playwright-stealth
python-dotenv
moviepy
requests
```

설치 후 추가 실행:
```bash
playwright install chromium
```

---

## 주의사항

- `.env` 파일은 절대 깃에 커밋하지 말 것 (`.gitignore`에 포함)
- 에펨코리아 크롤링 시 요청 간격 최소 2~3초 유지 (서버 부하 방지)
- Edge TTS는 Microsoft의 무료 서비스이므로 별도 API 키 불필요
- 타인 게시글 원문을 그대로 사용하지 말고 반드시 각색 후 사용