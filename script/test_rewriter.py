"""
script/rewriter.py 단독 테스트
하드코딩된 샘플 썰로 Claude API 연동 검증
"""
import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from script.rewriter import rewrite

SAMPLE_POST = {
    "post_id": "test_001",
    "title": "남자친구가 전 여자친구 사진을 몰래 보관하고 있었음",
    "content": (
        "사귄 지 8개월 된 남자친구 폰을 잠깐 빌렸는데 갤러리 정리하다가 "
        "숨김 폴더를 발견했어. 비번 물어봤더니 처음엔 모른다고 하다가 "
        "내가 표정이 굳으니까 결국 열어줬거든. "
        "근데 거기에 전 여자친구 사진이 200장 넘게 있는 거야. "
        "그것도 최근까지 계속 저장해온 흔적이 있고. "
        "전 여자친구랑은 2년 전에 헤어졌다고 했는데, "
        "사진 날짜 보니까 우리 사귀고 나서도 SNS에서 긁어온 게 있더라. "
        "남자친구는 그냥 추억이라고, 볼 생각은 없었다고 하는데 "
        "나는 배신감이 너무 심하게 들어서 일주일째 연락을 안 하고 있어. "
        "이게 헤어져야 할 이유가 되는 건지 아니면 내가 너무 예민한 건지 모르겠어."
    ),
    "views": 82000,
    "comments": 347,
    "url": "https://example.com/test_001",
}


def main():
    print("=" * 50)
    print("[원본]")
    print(f"제목: {SAMPLE_POST['title']}")
    print(f"내용: {SAMPLE_POST['content']}")
    print(f"조회수: {SAMPLE_POST['views']:,} / 댓글: {SAMPLE_POST['comments']}")
    print("=" * 50)
    print("\nClaude API 호출 중...\n")

    result = rewrite(SAMPLE_POST)

    print("[각색된 쇼츠 대본]")
    print("-" * 50)
    print(result["script"])
    print("-" * 50)
    print(f"\n글자수: {len(result['script'])}자  |  재시도: {'O' if result['retried'] else 'X'}")


if __name__ == "__main__":
    main()
