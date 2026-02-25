import streamlit as st

# [1. UI 설정] 반드시 맨 윗줄에 위치해야 합니다.
st.set_page_config(page_title="다낭 위드어스 AI", page_icon="🌴", layout="wide")

import streamlit.components.v1 as components
import google.generativeai as genai
from google.oauth2 import service_account
from googleapiclient.discovery import build
import json, datetime, requests, uuid, os, base64, re, html, threading

# [2. 정규식 정의] 이미지/영상 버튼을 만드는 규칙입니다.
RE_PHOTO = re.compile(r'(?:사진\s*보기|사진\s*확인|사진확인|사진링크).*?((?:http|https)://[^\s\]]+)')
RE_VIDEO = re.compile(r'(?:영상\s*보기|영상\s*확인|영상확인|영상링크).*?((?:http|https)://[^\s\]]+)')
RE_MAP = re.compile(r'(?:위치\s*보기|구글\s*맵|지도\s*보기|위치\s*확인).*?((?:http|https)://[^\s\]]+)')
RE_KAKAO = re.compile(r'(https://open\.kakao\.com/[^\s\]]+)')
RE_CLEAN = re.compile(r'(?:사진|영상|위치|지도|링크|오픈채팅|확인).*?((?:http|https)://\S+)')

# [3. 설정 및 금고 연결]
try:
    API_KEY = st.secrets["API_KEY"]
    SHEET_ID = st.secrets["SHEET_ID"]
    creds_dict = json.loads(st.secrets["GCP_SERVICE_ACCOUNT_JSON"])
except Exception as e:
    st.error(f"❌ Secrets 설정 오류: {e}. 'Settings > Secrets'를 확인하세요.")
    st.stop()

SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

# [4. 구글 시트 연결 엔진] - 🚨 근본 원인을 찾아내는 진단 도구 추가
@st.cache_resource
def get_sheets_service():
    try:
        # Secrets에 적힌 정보로 인증을 시도합니다.
        creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        service = build('sheets', 'v4', credentials=creds)
        # 🔍 실제로 시트에 접속이 가능한지 '테스트'를 해봅니다.
        service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
        return service
    except Exception as e:
        # 🚨 연결에 실패하면 "왜" 실패했는지 화면에 바로 뿌립니다!
        st.error(f"❌ 구글 시트 연결 실패: {e}")
        return None

# [5. 데이터 로드 로직]
@st.cache_data(ttl=300)
def get_withus_db():
    service = get_sheets_service()
    if not service: return ""
    try:
        # 'DB' 탭의 데이터를 읽어옵니다.
        result = service.spreadsheets().values().get(spreadsheetId=SHEET_ID, range='DB!A2:J50').execute()
        rows = result.get('values', [])
        return "\n".join([" | ".join(map(str, r)) for r in rows]) if rows else "시트가 비어있습니다."
    except Exception as e:
        st.warning(f"⚠️ 'DB' 탭 데이터를 읽지 못했습니다: {e}")
        return ""

# [6. 디자인 및 배경 설정]
BACKGROUND_IMAGE = "background.png"
if os.path.exists(BACKGROUND_IMAGE):
    with open(BACKGROUND_IMAGE, "rb") as f:
        bg_data = base64.b64encode(f.read()).decode()
    st.markdown(f"""<style>.stApp {{ background-image: url("data:image/png;base64,{bg_data}"); background-size: cover; background-attachment: fixed; }}</style>""", unsafe_allow_html=True)

st.markdown("<style>[data-testid='stChatMessage'] { background-color: rgba(0,0,0,0.6) !important; color: white !important; }</style>", unsafe_allow_html=True)

# [7. 메인 화면 구성]
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "반가워요! 다낭 위드어스 비서 **위블리**입니다. 😊"}]

st.markdown("<h1 style='text-align:center; color:#87CEEB;'>🌴 다낭 위드어스 AI 컨시어지</h1>", unsafe_allow_html=True)

# 데이터 로드 시도
db_data = get_withus_db()

# 대화 내용 표시
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

# 채팅 입력
if prompt := st.chat_input("위블리에게 질문해 보세요!"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)
    
    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("🌀 위블리가 확인하고 있어요... 🏃‍♀️💨")
        
        # 🤖 AI 지침: 데이터가 없으면 '딴소리'를 못하도록 막는 최후의 보루
        master_instruction = f"""
        당신은 다낭 전문 비서 '위블리'입니다.
        반드시 아래 [데이터]에 있는 정보만 사용하여 다낭에 대해서만 답변하세요.
        데이터가 비어있거나 부족하면 한국 지명을 지어내지 말고 "대표님께 확인이 필요해요"라고 하세요.
        
        [데이터]
        {db_data if db_data else "데이터를 불러오지 못했습니다."}
        """
        
        try:
            genai.configure(api_key=API_KEY)
            # 🚨 gemini-1.5-flash 모델을 사용하여 안정성을 높였습니다.
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(f"{master_instruction}\n질문: {prompt}")
            full_res = response.text
            placeholder.markdown(full_res)
            st.session_state.messages.append({"role": "assistant", "content": full_res})
        except Exception as e:
            placeholder.error(f"죄송해요, AI 응답 중 오류가 발생했어요: {e}")
