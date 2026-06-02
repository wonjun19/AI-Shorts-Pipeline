"""
tts/edge_tts.py 단독 테스트
샘플 대본으로 음성 파일 생성 검증
"""
import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tts.edge_tts import synthesize

SAMPLE_SCRIPT = (
    "이게 말이 됩니까? 남자친구 폰 갤러리에서 숨김 폴더를 발견했어. "
    "비번 물어보니까 처음엔 모른다고 발뺌하더니, 내 표정 보고는 결국 열어주더라고. "
    "근데 거기에 뭐가 있었냐면, 전 여자친구 사진이 200장 넘게 저장돼 있는 거야. "
    "더 충격적인 건 사진 날짜였어. 전 여자친구랑 2년 전에 헤어졌다면서? "
    "근데 사진 메타데이터 보니까 우리 사귀고 난 다음에도 계속 SNS에서 긁어와서 저장한 흔적이 있더라고. "
    "남자친구는 그냥 추억이래. 볼 생각 없었대. "
    "근데 추억이면 왜 숨김 폴더에 넣어? 왜 우리 사귀면서도 계속 저장해? "
    "지금 일주일째 연락 안 하고 있는데, 이거 헤어져야 하는 거 맞지? "
    "여러분이라면 어떻게 하시겠어요?"
)

SAMPLE_POST_ID = "test_001"


def main():
    print(f"대본 길이: {len(SAMPLE_SCRIPT)}자\n")

    # 기본 화자 (여성)
    path = synthesize(SAMPLE_SCRIPT, SAMPLE_POST_ID)
    size_kb = os.path.getsize(path) / 1024
    print(f"파일 크기: {size_kb:.1f} KB")

    # 남성 화자 테스트
    print("\n남성 화자(ko-KR-InJoonNeural)로도 테스트...")
    path_male = synthesize(SAMPLE_SCRIPT, SAMPLE_POST_ID + "_male", voice="ko-KR-InJoonNeural")
    size_kb_male = os.path.getsize(path_male) / 1024
    print(f"파일 크기: {size_kb_male:.1f} KB")


if __name__ == "__main__":
    main()
