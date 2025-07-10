import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta

# 설정
np.random.seed(42)

# 가능한 값들
titles = ["갤럭시 S24 제품 기본 지식", "스마트폰 고객 응대 기초 매너", "프리미엄 TV (OLED/QLED) 판매 전략",
          "삼성 가전제품(냉장고/세탁기) 기술 이해", "효과적인 세일즈 커뮤니케이션(스토리텔링)",
          "삼성 스마트홈(IoT) 판매 기술 이해", "고객 유형별 응대 전략", "구매 심리학과 세일즈 적용 방법",
          "효율적인 판매 관리 및 목표  po"
          "설정", "세일즈 데이터 분석 기초", "웨어러블 디바이스 판매 노하우",
          "홈엔터테인먼트 시스템 판매 전략", "모바일 악세사리 판매 방법", "세일즈 클로징 기법",
          "매장 내 효과적 고객 동선 설계"]

categories = ["제품지식", "세일즈 매너", "세일즈 전략", "고객응대"]
difficulties = ["입문", "초급", "중급", "고급", "전문가"]

# 데이터 생성
data = []
for i in range(300):
    duration = np.random.randint(5, 31)  # 강의 길이 (5~30분)
    completion_rate = np.random.uniform(0, 100)  # 완료율
    review_rate = np.random.uniform(0, 50)  # 복습율
    average_quiz_score = np.random.uniform(0, 100)  # 평균 퀴즈 점수
    user_rating = np.random.uniform(0.1, 5.0)  # 사용자 평점
    num_of_learners = np.random.randint(0, 3000)  # 총 수강자 수
    recent_popularity = np.random.uniform(0, 50)  # 최근 인기 증가율
    completion_time_ratio = np.random.uniform(50, 300)  # 강좌 완료 시간 비율
    update_date = datetime.now() - timedelta(days=np.random.randint(1, 365))  # 업데이트 날짜

    entry = {
        "id": i + 1,
        "title": np.random.choice(titles),
        "category": np.random.choice(categories),
        "duration_min": duration,
        "difficulty": np.random.choice(difficulties),
        "completion_rate": round(completion_rate, 1),
        "review_rate": round(review_rate, 1),
        "average_quiz_score": round(average_quiz_score, 1),
        "user_rating": round(user_rating, 2),
        "num_of_learners": num_of_learners,
        "recent_popularity": round(recent_popularity, 1),
        "update_date": update_date.strftime("%Y-%m-%d"),
        "completion_time_ratio": round(completion_time_ratio, 1)
    }

    data.append(entry)

# JSON 생성
data_with_comments = {
    "_comments": {
        "id": "강좌 고유 번호",
        "title": "강좌명",
        "category": "강좌 주제 및 영역 (제품지식, 세일즈 매너, 세일즈 전략, 고객응대)",
        "duration_min": "강좌 콘텐츠의 길이 (분)",
        "difficulty": "강좌 난이도 (입문, 초급, 중급, 고급, 전문가)",
        "completion_rate": "강좌 완료율(%)",
        "review_rate": "복습율 (%): 강좌를 완료한 뒤 다시 복습한 사용자의 비율",
        "average_quiz_score": "평균 퀴즈 점수 (%)",
        "user_rating": "사용자 평가 별점 (1~5점)",
        "num_of_learners": "총 수강자 수",
        "recent_popularity": "최근 30일간 수강자 증가율(%)",
        "update_date": "최종 업데이트 날짜",
        "completion_time_ratio": "강좌 길이 대비 평균 완료 소요시간 비율(%)"
    },
    "courses": data
}

# 파일로 저장
file_path = './sales_learning_dummy_data.json'
with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(data_with_comments, f, ensure_ascii=False, indent=4)

file_path