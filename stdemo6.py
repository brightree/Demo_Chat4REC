# 변경 사항
    # multi_agent_chatbot

import streamlit as st
from dotenv import load_dotenv
import os
import json
import uuid
from datetime import datetime
from typing import Literal, TypedDict
import openai
from langgraph.graph import StateGraph
from supabase import create_client
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings, OpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyMuPDFLoader
from langchain.chains import RetrievalQA
#from langchain_community.llms import OpenAI
#from langchain_community.embeddings import OpenAIEmbeddings

# ==========================
# 🔧 환경 설정 및 초기화
# ==========================
load_dotenv()
api_key = os.getenv("MY_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not api_key:
    st.error("❗OpenAI API 키가 설정되지 않았습니다.")
    st.stop()

client = openai.OpenAI(api_key=api_key)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ===============================
# 🧱 세션 상태 초기화
# ===============================
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = f"conv_{uuid.uuid4().hex[:8]}"
if "turn_index" not in st.session_state:
    st.session_state.turn_index = 0

# ===========================
# 📚 강의 데이터 로딩 (Agent2)
# ===========================
@st.cache_data
def load_course_data():
    try:
        with open("sales_learning_dummy_data.json", "r", encoding="utf-8") as f:
            return json.load(f)["courses"]
    except Exception as e:
        st.error(f"❗강의 데이터를 불러오지 못했습니다: {e}")
        return []

course_data = load_course_data()

# ===========================
# 📁 PDF 문서 임베딩 (Agent1)
# ===========================
@st.cache_resource
def load_or_create_rag_retriever(
    file_path: str,
    index_dir: str = "faiss_index",
    chunk_size: int = 700,
    chunk_overlap: int = 150,
) -> FAISS:
    if os.path.exists(index_dir):
        return FAISS.load_local(
            index_dir,
            OpenAIEmbeddings(api_key=api_key),
            allow_dangerous_deserialization=True  # ✅ 여기가 핵심입니다
        ).as_retriever()


    # 1. PDF 읽기 및 청킹
    loader = PyMuPDFLoader(file_path)
    documents = loader.load()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    chunks = splitter.split_documents(documents)

    # 2. 임베딩 및 FAISS 저장
    embeddings = OpenAIEmbeddings(api_key=api_key)
    db = FAISS.from_documents(chunks, embeddings)
    db.save_local(index_dir)
    return db.as_retriever()

rag_retriever = load_or_create_rag_retriever("Rag_Galaxy25_Ultra.pdf")
rag_chain = RetrievalQA.from_chain_type(llm=OpenAI(temperature=0), retriever=rag_retriever)

# ==============================
# 🧠 LangGraph 상태 정의
# ==============================
class GraphState(TypedDict):
    user_query: str
    final_response: str
    route: Literal["agent1", "agent2"]

# ==============================
# 🔍 의도 분류 엔진 노드
# ==============================
def route_intent(state: GraphState) -> GraphState:
    user_query = state["user_query"]

    routing_prompt = f"""
다음 사용자 질문이 어떤 유형인지 분류해 주세요.
각 유형 별로 다른 LLM Agent를 사용하므로, 합리적 분류가 중요합니다.

- 제품 스펙, 기능, 배터리, 카메라 등 '제품 정보'에 대한 질문이면: agent1
- 영업 고민, 강의 추천, 학습에 대한 질문이면: agent2

❗️반드시 아래 중 하나만 출력하세요 (따옴표 없이 단독으로 한 줄):
agent1
agent2

[사용자 질문]
{user_query}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=[
            {"role": "system", "content": "당신은 사용자 질문을 분류하는 시스템입니다."},
            {"role": "user", "content": routing_prompt}
        ]
    )

    raw = response.choices[0].message.content.strip().lower()

    # 안정적 처리
    if "agent1" in raw:
        route = "agent1"
    elif "agent2" in raw:
        route = "agent2"
    else:
        # fallback: 학습 관련으로 처리
        route = "agent2"

    return {**state, "route": route}

# ==============================
# 🤖 Agent1 (RAG 기반 제품 답변)
# ==============================
def agent1_product_info(state: GraphState) -> GraphState:
    user_query = state["user_query"]
    try:
        answer = rag_chain.run(user_query)
    except Exception as e:
        answer = f"❗제품 정보 조회 중 오류 발생: {e}"
    return {**state, "final_response": answer}

# ==============================
# 🎓 Agent2 (강의 추천 챗봇)
# ==============================
def agent2_recommend_courses(state: GraphState) -> GraphState:
    full_history = ""
    for turn in st.session_state.chat_history:
        full_history += f"사용자: {turn['user']}\n"
        full_history += f"챗봇: {turn['bot']}\n"
    full_history += f"사용자: {state['user_query']}\n"

    prompt = f"""
당신은 삼성전자 영업사원을 위한 "전문 강의 추천 챗봇"입니다.

## 역할
- 삼성전자 영업사원이 제품 설명, 고객 상담, 세일즈 전략 등 업무에서 겪는 고민을 기반으로, 가장 적합한 강의를 추천하는 챗봇입니다.
- 사용자는 바쁜 업무 중 질문하므로, 응답은 항상 **핵심적이고 간결하게**, **친근하면서도 전문적인 어투**로 전달해야 합니다.

## 목표
- 사용자의 고민/상황/선호 스타일을 파악하여 맞춤 강의 3~5개를 추천합니다.
- 단, 사용자가 "지금 바로 추천해줘"라고 말하지 않는 이상, 2회 내외의 상호대화를 통해 정보를 수집합니다.
    - 예를 들어, 단순한 인삿말만 주고 받았다면 원하는 강의나 학습 고민을 유도 질문하여 정보를 수집합니다.

## 대화 흐름 지침 (Flow Logic)
1. **정보 수집**
   - 사용자의 응답에 따라 자연스럽게 질문을 이어가며, 한 번에 하나의 질문만 던집니다.
   - 질문은 짧고 명확하되, 적절한 강의를 추천할 수 있도록 질문합니다.

2. **즉시 추천 예외**
   - 사용자가 “지금 바로 추천해줘”라고 말하면, 질문 생략 후 바로 추천을 진행합니다.

3. **추천 응답 형식**
   - 강의는 다음 정보를 담되, 자연스럽고 간결한 문장으로 구성합니다:
     - 강의 제목
     - 추천 이유 (사용자 고민과 연결)
     - 링크: https://www.ubion.co.kr/ubion/
   - 추천 강의는 **중요도 순서로 3~5개**, 항목별로 구분해 제시합니다.

4. **예외 응대**
   - 사용자가 농담, 과격한 표현, 욕설 등을 입력하더라도 감정적 대응 없이 원래 주제로 자연스럽게 유도합니다.

## 응답 스타일 (Tone & Format)
- 말투: 전문성 있고 친절한 말투
- 문장: 짧고 핵심적으로, 정보 밀도 높게
- 불필요한 서두/결론/과잉 설명 배제
- 사용자의 표현을 요약하며 다음 질문 또는 추천으로 자연스럽게 연결

## 응답 예시 (참고용 프라이밍)
사용자: 고객 응대가 힘들어요  
→ 챗봇: 고객 대응이 어려우시군요. 혹시 어떤 유형의 고객이 특히 어려우셨나요? 예를 들면 불만 고객, 설명을 못 알아듣는 고객 등요.  

사용자: 집중이 잘 안돼요.
→ 챗봇: 짧고 핵심적인 강의를 추천해 드릴게요.
→ [강의 추천 시작]


[대화 기록]
{full_history}

이 대화 내용을 바탕으로 추가 질문이 필요하면 자연스럽게 이어가고,  
정보가 충분하다고 판단되면 강의를 추천해 주세요.


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

# ==============================
# 🔁 LangGraph 구축
# ==============================
builder = StateGraph(GraphState)
builder.add_node("route_intent", route_intent)
builder.add_node("agent1", agent1_product_info)
builder.add_node("agent2", agent2_recommend_courses)

builder.set_entry_point("route_intent")
builder.add_conditional_edges("route_intent", lambda x: x["route"], {
    "agent1": "agent1",
    "agent2": "agent2"
})

graph = builder.compile()

# ==============================
# 💾 Supabase 저장 함수
# ==============================
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

# ==============================
# 🎨 Streamlit UI
# ==============================
st.set_page_config(
    page_title="삼성 세일즈 Agentic 챗봇",
    page_icon="💼",
    layout="centered",
    initial_sidebar_state="collapsed"
)

for turn in st.session_state.chat_history:
    st.chat_message("user").write(turn["user"])
    st.chat_message("assistant").write(turn["bot"])

samsung_blue = "#1428A0"
st.markdown(f"""
    <div style="text-align:center; margin-bottom:20px;">
        <img src="https://upload.wikimedia.org/wikipedia/commons/2/24/Samsung_Logo.svg" width="180" />
        <h2 style="color:{samsung_blue};">삼성전자 Sales Agentic Assitant</h2>
        <p style="font-size:15px;">제품 스펙 정보부터 고객 커뮤니케이션 고민까지, 무엇이든 물어보세요!</p>
    </div>
""", unsafe_allow_html=True)

user_input = st.chat_input("세일즈 관련 궁금점을 말씀해 주세요.")
if user_input:
    st.chat_message("user").write(user_input)
    result = graph.invoke({"user_query": user_input})
    response_text = result["final_response"]
    
    # ✅ 현재 응답한 agent 알려주기
    route_used = result.get("route", "")
    if route_used == "agent1":
        response_header = "📱 [제품 정보 Agent]"
    elif route_used == "agent2":
        response_header = "🎓 [학습 추천 Agent]"
    else:
        response_header = "🤖 [Agent 응답]"

    st.chat_message("assistant").write(f"{response_header}\n\n{response_text}")
    
    st.session_state.chat_history.append({"user": user_input, "bot": f"{response_header}\n\n{response_text}"})
    save_chat_to_db(user_input, response_text)
