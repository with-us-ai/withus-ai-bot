import streamlit as st

# [1. UI 설정] 프리미엄 모드
st.set_page_config(page_title="다낭 위드어스 AI 컨시어지", page_icon="🌴", layout="wide")

import streamlit.components.v1 as components
import google.generativeai as genai
from google.oauth2 import service_account
from googleapiclient.discovery import build
import json
import datetime, requests, uuid, os, urllib.parse, base64, re, html, threading

# [2. 정규식 정의] 버튼 자동 생성 엔진
RE_PHOTO = re.compile(r'(?:사진\s*보기|사진\s*확인|사진확인|사진링크).*?((?:http|https)://[^\s\]]+)')
RE_VIDEO = re.compile(r'(?:영상\s*보기|영상\s*확인|영상확인|영상링크).*?((?:http|https)://[^\s\]]+)')
RE_MAP = re.compile(r'(?:위치\s*보기|구글\s*맵|지도\s*보기|위치\s*확인).*?((?:http|https)://[^\s\]]+)')
RE_KAKAO = re.compile(r'(https://open\.kakao\.com/[^\s\]]+)')
RE_CLEAN = re.compile(r'(?:사진|영상|위치|지도|링크|오픈채팅|확인).*?((?:http|https)://\S+)')

# [3. 설정 및 금고 연결]
TELEGRAM_BOT_TOKEN = st.secrets["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = st.secrets["TELEGRAM_CHAT_ID"]
API_KEY = st.secrets["API_KEY"]
SHEET_ID = st.secrets["SHEET_ID"]
creds_dict = json.loads(st.secrets["GCP_SERVICE_ACCOUNT_JSON"])
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

@st.cache_resource
def get_sheets_service():
    try:
        creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        return build('sheets', 'v4', credentials=creds)
    except: return None

# [4. 디자인 소스]
@st.cache_data
def get_base64(file):
    if not os.path.exists(file): return ""
    with open(file, 'rb') as f: return base64.b64encode(f.read()).decode()

BACKGROUND_IMAGE = "background.png"
USER_AVATAR = "user.png" if os.path.exists("user.png") else "👤"
WIBLY_AVATAR = "wibly.png" if os.path.exists("wibly.png") else "👩‍🚀"

# [5. UI 디자인 (CSS)] - "엉망"인 부분을 깔끔하게 교정
bg_data = get_base64(BACKGROUND_IMAGE)
st.markdown(f"""
    <style>
    #MainMenu, header, footer {{visibility: hidden;}}
    .stApp {{
        background-image: url("data:image/png;base64,{bg_data}") !important;
        background-size: cover; background-attachment: fixed;
    }}
    .main .block-container {{ max-width: 900px; padding-top: 50px; padding-bottom: 100px; }}
    [data-testid="stSidebar"] {{ background-color: rgba(0, 0, 0, 0.4) !important; backdrop-filter: blur(10px); color: white; }}
    [data-testid="stChatMessage"] {{ background-color: rgba(0, 0, 0, 0.6) !important; border-radius: 20px; border: 1px solid rgba(255,255,255,0.1); margin-bottom: 10px; }}
    .stChatMessage .stMarkdown * {{ color: white !important; font-size: 1.05rem; line-height: 1.6; }}
    [data-testid="stChatInput"] {{ border-radius: 30px !important; border: 1px solid #87CEEB !important; background-color: rgba(255,255,255,0.1) !important; }}
    </style>
""", unsafe_allow_html=True)

# [6. 핵심 로직]
if "messages" not in st.session_state:
    # 🌟 첫 인사 추가 (이걸 넣어야 화면이 안 썰렁합니다!)
    st.session_state.messages = [{"role": "assistant", "content": "반가워요 대표님! 😊 다낭 위드어스의 똑똑한 비서 **위블리**입니다. 인원과 날짜를 말씀해 주시면 최고의 여행을 만들어 드릴게요!"}]
if "user_id" not in st.session_state: st.session_state.user_id = str(uuid.uuid4())

# 사이드바
with st.sidebar:
    st.markdown("## 🌴 With Us AI")
    st.link_button("💖 실시간 상담 (카톡)", "https://open.kakao.com/o/sxJ8neWg", use_container_width=True)
    st.divider()
    st.markdown("⏰ 다낭 시간")
    components.html("""<div id="c" style="color:white;font-size:28px;text-align:center;font-weight:900;"></div><script>setInterval(()=>{document.getElementById('c').innerText=new Date().toLocaleTimeString('ko-KR',{timeZone:'Asia/Ho_Chi_Minh',hour12:false});},1000);</script>""", height=60)

# 메인 타이틀
st.markdown("""<h1 style='text-align: center; color: #87CEEB; text-shadow: 2px 2px 10px #000;'>🌴 다낭 위드어스 컨시어지</h1>""", unsafe_allow_html=True)

# 데이터 로드
db = get_sheets_service()
db_data = "구글 시트 연결 전입니다." # 실제 DB 로드 로직 생략 (필요시 추가)

# 대화 렌더링
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar=USER_AVATAR if msg["role"]=="user" else WIBLY_AVATAR):
        st.markdown(msg["content"])

# 채팅 입력
if prompt := st.chat_input("위블리에게 여행 계획을 물어보세요!"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar=USER_AVATAR): st.markdown(prompt)
    
    with st.chat_message("assistant", avatar=WIBLY_AVATAR):
        placeholder = st.empty()
        placeholder.markdown("🌀 위블리가 확인하고 있어요...")
        
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel('gemini-3-flash-preview')
        response = model.generate_content(f"당신은 위블리입니다. 질문: {prompt}")
        full_res = response.text
        
        placeholder.markdown(full_res)
        st.session_state.messages.append({"role": "assistant", "content": full_res})
    st.rerun()
