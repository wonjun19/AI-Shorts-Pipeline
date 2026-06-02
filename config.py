import os
from dotenv import load_dotenv

load_dotenv()

# API 키
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

# 파이프라인 설정
MAX_POSTS = int(os.getenv("MAX_POSTS", 10))
MIN_VIEWS = int(os.getenv("MIN_VIEWS", 5000))
MIN_COMMENTS = int(os.getenv("MIN_COMMENTS", 20))
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./output")

# 필터 설정
MIN_CONTENT_LENGTH = 200
MAX_CONTENT_LENGTH = 2000

# Claude API 설정
CLAUDE_MODEL = "claude-sonnet-4-5"
CLAUDE_MAX_TOKENS = 1000
CLAUDE_TEMPERATURE = 0.8

# Edge TTS 설정 (Microsoft Edge TTS, API 키 불필요)
TTS_VOICE = "ko-KR-SunHiNeural"   # 여성. 남성: ko-KR-InJoonNeural
TTS_RATE = "+10%"                  # 속도 (쇼츠 특성상 약간 빠르게)
TTS_VOLUME = "+0%"
TTS_PITCH = "+0Hz"

# 영상 스펙
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS = 30
VIDEO_BG_COLOR = "#1a1a2e"

# 자막 스펙
SUBTITLE_FONT = "./video/assets/fonts/NanumGothicBold.ttf"
SUBTITLE_FONT_SIZE = 52
SUBTITLE_COLOR = "white"
SUBTITLE_Y_RATIO = 0.75
SUBTITLE_MAX_CHARS_PER_LINE = 18

# 크롤링 설정
FMKOREA_URL = "https://www.fmkorea.com/index.php?mid=love"
CRAWL_DELAY_MIN = 2
CRAWL_DELAY_MAX = 3
