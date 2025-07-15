# 변경 사항
    # 프롬프트 템플릿 사용

# ==========================
# 기본 라이브러리
# ==========================
import os
import json
import uuid
from datetime import datetime, timezone
from typing import Literal, TypedDict

# ==========================
# 외부 라이브러리
# ==========================
from dotenv import load_dotenv
import openai
from supabase import create_client

# ==========================
# LangChain 관련
# ==========================
import streamlit as st
from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from langchain.chains import RetrievalQA
# LangChain Community 모듈
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyMuPDFLoader
# LangChain OpenAI 관련
from langchain_openai import OpenAIEmbeddings, OpenAI
# LangGraph
from langgraph.graph import StateGraph

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

rag_retriever = load_or_create_rag_retriever("RAG/Rag_Galaxy25_Ultra.pdf")
rag_chain = RetrievalQA.from_chain_type(llm=OpenAI(temperature=0), retriever=rag_retriever)

# ===========================
# 📚 강의 데이터 전처리 (Agent2)
# ===========================

# 강의 데이터 읽기
@st.cache_data
def load_course_data():
    try:
        with open("RAG/sales_learning_dummy_data.json", "r", encoding="utf-8") as f:
            return json.load(f)["courses"]
    except Exception as e:
        st.error(f"❗강의 데이터를 불러오지 못했습니다: {e}")
        return []

course_data = load_course_data()

# 강의 데이터 랭체인 문서로 변환
def course_data_to_documents(course_data: list) -> list[Document]:
    docs = []
    for course in course_data:
        text = "\n".join([f"{key}: {value}" for key, value in course.items()])
        docs.append(Document(page_content=text, metadata={"title": course.get("title", "")}))
    return docs

# 임베딩 및 청킹
@st.cache_resource
def create_course_rag_retriever(course_data: list, index_dir: str = "course_faiss_index") -> FAISS:
    from langchain.text_splitter import RecursiveCharacterTextSplitter

    if os.path.exists(index_dir):
        return FAISS.load_local(
            index_dir,
            OpenAIEmbeddings(api_key=api_key),
            allow_dangerous_deserialization=True
        ).as_retriever()

    docs = course_data_to_documents(course_data)
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    split_docs = splitter.split_documents(docs)

    embeddings = OpenAIEmbeddings(api_key=api_key)
    db = FAISS.from_documents(split_docs, embeddings)
    db.save_local(index_dir)
    return db.as_retriever()


# ==============================
# 🧠 LangGraph 상태 정의
# ==============================
class GraphState(TypedDict):
    user_query: str
    final_response: str
    route: Literal["agent1", "agent2"]

# ==============================
# 프롬프트 로딩
# ==============================
def load_prompt(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

# ==============================
# 🔍 의도 분류 엔진 노드
# ==============================
routing_prompt_template = PromptTemplate(
    input_variables=["user_query"],
    template=load_prompt("prompts/routing_prompt.txt")
)

def route_intent(state: GraphState) -> GraphState:
    user_query = state["user_query"]

    formatted_prompt = routing_prompt_template.format(user_query=user_query)

    response = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=[
            {"role": "system", "content": "당신은 사용자 질문을 분류하는 시스템입니다."},
            {"role": "user", "content": formatted_prompt}
        ]
    )

    raw = response.choices[0].message.content.strip().lower()

    # 안정적 처리
    if "agent1" in raw:
        route = "agent1"
    elif "agent2" in raw:
        route = "agent2"
    else:
        route = "agent2"  # fallback
    return {**state, "route": route}

# ==============================
# 🤖 Agent1 (RAG 기반 제품 답변)
# ==============================
agent1_prompt_template = PromptTemplate(
    input_variables=["user_query"],
    template=load_prompt("prompts/agent1_prompt.txt")
)

def agent1_product_info(state: GraphState) -> GraphState:
    try:
        formatted_query = agent1_prompt_template.format(
            user_query=state["user_query"]
        )
        answer = rag_chain.invoke(formatted_query)
    except Exception as e:
        answer = f"❗제품 정보 조회 중 오류 발생: {e}"
    return {**state, "final_response": answer}

# ==============================
# 🎓 Agent2 (강의 추천 챗봇)
# ==============================
course_prompt_template = PromptTemplate(
    input_variables=["full_history", "course_data"],
    template=load_prompt("prompts/agent2_prompt.txt")
)
course_retriever = create_course_rag_retriever(course_data)
def agent2_recommend_courses(state: GraphState) -> GraphState:
    full_history = ""
    for turn in st.session_state.chat_history:
        full_history += f"사용자: {turn['user']}\n"
        full_history += f"챗봇: {turn['bot']}\n"
    full_history += f"사용자: {state['user_query']}\n"

    try:
        # 유사 강의 Top N 추출
        relevant_docs = course_retriever.invoke(state["user_query"])
        top_courses_text = "\n\n".join(doc.page_content for doc in relevant_docs[:5])

        formatted_prompt = course_prompt_template.format(
            full_history=full_history,
            course_data=top_courses_text
        )

        res = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {"role": "system", "content": "삼성전자 세일즈 강의 추천 전문가"},
                {"role": "user", "content": formatted_prompt}
            ]
        )
        response_text = res.choices[0].message.content.strip()
    except Exception as e:
        response_text = f"❗추천 생성 중 오류 발생: {e}"

    return {**state, "final_response": response_text}


# ==============================
# 🔁 LangGraph 구축
# ==============================
AGENTS = {
    "agent1": agent1_product_info,
    "agent2": agent2_recommend_courses
}
builder = StateGraph(GraphState)
builder.add_node("route_intent", route_intent)

# 에이전트 등록 반복문
for name, func in AGENTS.items():
    builder.add_node(name, func)
builder.set_entry_point("route_intent")

# 조건부 라우팅도 AGENTS 기반으로 구성
builder.add_conditional_edges("route_intent", lambda x: x["route"], {
    k: k for k in AGENTS
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
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_input": user_input,
        "llm_response": llm_response
    }).execute()
    st.session_state.turn_index += 1

from ui3 import render_app_ui
if __name__ == "__main__":
    render_app_ui(graph, save_chat_to_db)