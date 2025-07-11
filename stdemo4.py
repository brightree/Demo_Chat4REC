# 반영 사항
    # 2-3번 정보 취합

import streamlit as st
from dotenv import load_dotenv
import os
import json
from datetime import datetime
from typing import TypedDict
import uuid
import openai
from langgraph.graph import StateGraph
from supabase import create_client

# 🎯 초기 설정
load_dotenv()
api_key = os.getenv("MY_API_KEY")
if not api_key:
    st.error("❗OpenAI API 키가 설정되지 않았습니다.")
    st.stop()
client = openai.OpenAI(api_key=api_key)

# 🔗 Supabase 연결
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 🧱 상태 초기화
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = f"conv_{uuid.uuid4().hex[:8]}"
if "turn_index" not in st.session_state:
    st.session_state.turn_index = 0

# 📚 강의 데이터 로드
@st.cache_data
def load_course_data():
    try:
        with open("sales_learning_dummy_data.json", "r", encoding="utf-8") as f:
            return json.load(f)["courses"]
    except Exception as e:
        st.error(f"❗강의 데이터를 불러오지 못했습니다: {e}")
        return []
course_data = load_course_data()

# 🧠 LangGraph 구조
class GraphState(TypedDict):
    user_query: str
    final_response: str

def recommend_courses(state: GraphState) -> GraphState:
    # 💬 이전 대화 포함
    full_history = ""
    for turn in st.session_state.chat_history:
        full_history += f"사용자: {turn['user']}\n"
        full_history += f"챗봇: {turn['bot']}\n"
    full_history += f"사용자: {state['user_query']}\n"

    prompt = f"""

[역할]
삼성전자 영업사원이 제품 설명, 고객 상담, 세일즈 전략 등 업무에서 겪는 고민을 기반으로, 가장 적합한 강의를 추천하는 챗봇입니다.

전문성과 친절함을 갖춘 어투로, 사용자의 고민에 맞는 강의를 추천해 주세요.
응답은 핵심적이고 간결하게, 바쁜 영업사원의 시간을 고려해 응답해 주세요.

[행동 지침]
1. 사용자가 강의를 요청하더라도, 최소 2~3회의 자연스러운 대화를 통해 정보를 수집해 주세요.
2. 정보를 수집할 때는 질문을 한 번에 하나씩만 던지고, 사용자가 부담 없이 답할 수 있도록 해 주세요.  
   - 질문은 이전 사용자의 답변을 기반으로 자연스럽게 이어가주세요.
3. 사용자가 “지금 바로 추천해줘”라고 명확히 요청하는 경우에는 예외적으로 즉시 추천을 진행해 주세요.
4. 사용자의 답변을 통해 충분한 정보가 모였다고 판단되면,
   - 지금까지의 답변 내용을 간단히 요약  
   - 그에 따라 강의 3~5개를 추천
   - 강의는 추천 강도가 높은 순서대로 나열

[추천 방식]
- 강의는 삼성전자 영업사원의 실무 및 매출 개선에 실질적으로 도움이 되는 주제를 중심으로 추천해 주세요.
- 사용자의 고민, 목표, 선호하는 강의 스타일에 따라 [강의 목록]에서 적합한 강의를 선별해서 추천해 주세요.
- 추천 시 고려할 수 있는 요소는 예를 들어 다음과 같습니다,
  - 집중력이 낮다는 사용자는 짧고 핵심적인 강의가 적합할 수 있습니다.
  - 고객 응대가 어렵다는 사용자는 상황별 응대법이나 고객 심리 이해 관련 강의가 유용할 수 있습니다,
  - 제품 설명이 어려운 경우는 제품 구조, 기술 이해, 설명 커뮤니케이션 관련 강의가 도움될 수 있습니다.

[출력 형식 지침]  
  - 강의 제목:
  - 추천 이유:
  - 링크: https://www.ubion.co.kr/ubion/

[질문 설계 참고]
- 아래는 질문 작성 시 참고용 예시이며, 그대로 출력하지 말고 상황에 맞게 응용해 주세요.
  - 강의를 듣는 목적은 무엇인가요? (예: 실적 향상, 고객 이해, 제품 지식 등)
  - 고객 응대 중 어떤 유형의 고객이 가장 응대하기 어려우셨나요? (특정 성별, 연령, 고객 특성)
  - 선호하는 강의 스타일은 어떤 유형인가요? (예: 짧고 핵심적인 강의, 사례 중심 강의 등)

[대화 기록]
{full_history}

이 대화 내용을 바탕으로 추가 질문이 필요하면 자연스럽게 이어가고, 정보가 충분하다고 판단되면 강의를 추천해 주세요.


[강의 목록]
{json.dumps(course_data, ensure_ascii=False, indent=2)}
"""
    try:
        res = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {"role": "system", "content": "삼성전자 세일즈 강의 추천 전문가"},
                {"role": "user", "content": prompt}
            ]
        )
        response_text = res.choices[0].message.content.strip()
    except Exception as e:
        response_text = f"❗추천 생성 중 오류 발생: {e}"

    return {**state, "final_response": response_text}

builder = StateGraph(GraphState)
builder.add_node("recommend_courses", recommend_courses)
builder.set_entry_point("recommend_courses")
graph = builder.compile()

# 💾 Supabase 저장 함수
def save_chat_to_db(user_input, llm_response):
    supabase.table("chat_history").insert({
        "user_id": "guest_user",
        "conversation_id": st.session_state.conversation_id,
        "turn_index": st.session_state.turn_index,
        "timestamp": datetime.utcnow().isoformat(),
        "user_input": user_input,
        "llm_response": llm_response
    }).execute()
    st.session_state.turn_index += 1

# 🎨 페이지 UI
st.set_page_config(
    page_title="삼성 세일즈 챗봇",
    page_icon="💼",
    layout="centered",
    initial_sidebar_state="collapsed"
)

samsung_blue = "#1428A0"
st.markdown(f"""
    <div style="text-align:center; margin-bottom:20px;">
        <img src="https://upload.wikimedia.org/wikipedia/commons/2/24/Samsung_Logo.svg" width="180" />
        <h2 style="color:{samsung_blue};">삼성전자 세일즈 강의 추천 챗봇</h2>
        <p style="font-size:15px;">제품 정보 부족, 소심한 성격, 커뮤니케이션 고민 등 무엇이든 입력해보세요.</p>
    </div>
""", unsafe_allow_html=True)

# 💬 이전 대화 렌더링
for turn in st.session_state.chat_history:
    # 사용자 메시지 (오른쪽 정렬)
    st.markdown(f"""
    <div style="text-align:right; margin: 8px 0;">
        <div style="display:inline-block; background-color:#DCF8C6; color:#000; padding:10px 14px; border-radius:18px; max-width:70%; font-size:15px;">
            {turn['user']}
        </div> 🦁
    </div>
    """, unsafe_allow_html=True)

    # 챗봇 메시지 (왼쪽 정렬 + 삼성 로고)
    st.markdown(f"""
    <div style="text-align:left; margin: 8px 0;">
        <img src="https://upload.wikimedia.org/wikipedia/commons/2/24/Samsung_Logo.svg" width="32" height="32" style="vertical-align:middle; margin-right:8px;" />
        <div style="display:inline-block; background-color:#F1F0F0; color:#000; padding:10px 14px; border-radius:18px; max-width:75%; font-size:15px;">
            <pre style="white-space:pre-wrap; margin:0;">{turn['bot']}</pre>
        </div>
    </div>
    """, unsafe_allow_html=True)

# 📝 입력창 (하단 고정)
user_input = st.chat_input("세일즈 고민을 입력해 주세요")
if user_input:
    # 오른쪽 말풍선 출력
    st.markdown(f"""
    <div style="text-align:right; margin: 8px 0;">
        <div style="display:inline-block; background-color:#DCF8C6; color:#000; padding:10px 14px; border-radius:18px; max-width:70%; font-size:15px;">
            {user_input}
        </div> 🦁
    </div>
    """, unsafe_allow_html=True)

    # LangGraph 호출
    result = graph.invoke({"user_query": user_input})
    response_text = result["final_response"]

    # 왼쪽 말풍선 출력
    st.markdown(f"""
    <div style="text-align:left; margin: 8px 0; position: relative;">
        <div style="display:inline-block; background-color:#F1F0F0; color:#000; padding:14px 14px 10px 14px; border-radius:18px; max-width:75%; font-size:15px; position:relative;">
            <img src="https://upload.wikimedia.org/wikipedia/commons/2/24/Samsung_Logo.svg"
                width="40" height="14"
                style="position: absolute; top: 10px; left: 10px;" />
            <div style="padding-top: 24px;">
                <pre style="white-space:pre-wrap; margin:0;">{response_text}</pre>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.session_state.chat_history.append({"user": user_input, "bot": response_text})
    save_chat_to_db(user_input, response_text)