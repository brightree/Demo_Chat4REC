# 반영 사항
    # 멀티턴

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
너는 삼성전자의 영업사원을 위한 강의 추천 챗봇이야.
전문성 있는 어투를 유지하되, 친절하고 예의 바른 응답을 제공해줘.

아래는 지금까지의 대화야. 사용자의 요구 사항(고민)과 이전 대화 맥락을 고려해 적절한 강의를 3개~5개 추천해줘.
예를 들어, 사용자가 학습 집중력이 낮은 게 고민이라면 평점이 좋고 짧은 강의를 추천할 수 있을 거야.

대화 내용:
{full_history}

형식:
1. 강의 제목: ... (줄바꿈) 추천 이유: ...
2. 강의 제목: ... (줄바꿈) 추천 이유: ...

추천하는 강도가 높은 순부터 낮은 순으로 추천 강의를 나열해줘.

강의 목록:
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