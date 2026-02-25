import streamlit as st

# [UI 설정] 반드시 코드 맨 윗줄에 딱 한 번만 있어야 합니다!
st.set_page_config(page_title="다낭 위드어스 AI 컨시어지", page_icon="🌴", layout="wide")

import streamlit.components.v1 as components
import google.generativeai as genai
from google.oauth2 import service_account
from googleapiclient.discovery import build
import json
import datetime, requests, uuid, os, urllib.parse, base64, re, html, threading

# ==========================================
# 🚨 정규식(Regex) 정의 (이미지/영상 버튼 생성용)
# ==========================================
RE_PHOTO = re.compile(r'(?:사진\s*보기|사진\s*확인|사진확인|사진링크).*?((?:http|https)://[^\s\]]+)')
RE_VIDEO = re.compile(r'(?:영상\s*보기|영상\s*확인|영상확인|영상링크).*?((?:http|https)://[^\s\]]+)')
RE_MAP = re.compile(r'(?:위치\s*보기|구글\s*맵|지도\s*보기|위치\s*확인).*?((?:http|https)://[^\s\]]+)')
RE_KAKAO = re.compile(r'(https://open\.kakao\.com/[^\s\]]+)')
RE_CLEAN = re.compile(r'(?:사진|영상|위치|지도|링크|오픈채팅|확인).*?((?:http|https)://\S+)')

# ==========================================
# 🔐 [설정] 스트림릿 금고(Secrets) 연결
# ==========================================
TELEGRAM_BOT_TOKEN = st.secrets["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = st.secrets["TELEGRAM_CHAT_ID"]
API_KEY = st.secrets["API_KEY"]
SHEET_ID = st.secrets["SHEET_ID"]

# 구글 서비스 계정 연결
creds_dict = json.loads(st.secrets["GCP_SERVICE_ACCOUNT_JSON"])
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

@st.cache_resource
def get_sheets_service():
    try:
        # Secrets 데이터를 직접 사용하여 연결 안정성을 높였습니다.
        creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        return build('sheets', 'v4', credentials=creds)
    except Exception:
        return None

# ==========================================
# 🎨 이미지 변환 및 디자인 설정
# ==========================================
@st.cache_data
def get_base64_of_bin_file(bin_file):
    if not os.path.exists(bin_file): return ""
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

USER_AVATAR = "user.png" if os.path.exists("user.png") else "👤"
WIBLY_AVATAR = "wibly.png" if os.path.exists("wibly.png") else "👩‍🚀"
BACKGROUND_IMAGE_FILE = "background.png"

@st.cache_data(ttl=600)
def get_withus_db():
    service = get_sheets_service()
    if not service: return {} # 연결 실패 시 빈 데이터 반환하여 멈춤 방지
    try:
        ranges = ['DB!A2:J50', '골프!A2:F30', '스파!A2:H30', '차량!A2:J30', '이발소!A2:F30']
        result = service.spreadsheets().values().batchGet(spreadsheetId=SHEET_ID, ranges=ranges).execute()
        v = result.get('valueRanges', [])
        def fd(d): return "\n".join([" | ".join(map(str, r)) for r in d]) if d else "데이터 없음"
        return {"villa": fd(v[0].get('values', [])), "golf": fd(v[1].get('values', [])), "spa": fd(v[2].get('values', [])), "car": fd(v[3].get('values', [])), "barber": fd(v[4].get('values', []))}
    except: return {}

def send_tele(u_id, u_m, a_m):
    try: requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": f"👤 고객({u_id[-4:]}): {u_m}\n🤖 위블리: {a_m}"})
    except: pass

def run_background_tasks(u_id, u_m, a_m):
    threading.Thread(target=send_tele, args=(u_id, u_m, a_m)).start()

def auto_scroll_to_bottom():
    js = "<script>window.parent.document.querySelectorAll('[data-testid=\"stChatMessage\"]').forEach(el => el.scrollIntoView({behavior: 'smooth', block: 'end'}));</script>"
    components.html(js, height=0)

# ==========================================
# 🎨 UI 렌더링 (CSS 적용)
# ==========================================
bg_data = get_base64_of_bin_file(BACKGROUND_IMAGE_FILE)
css_style = f"""
    <style>
    #MainMenu, header, footer {{visibility: hidden;}}
    .stApp {{
        background-image: url("data:image/png;base64,{bg_data}") !important;
        background-size: cover; background-attachment: fixed; background-position: center;
    }}
    .main .block-container {{ max-width: 1000px; margin: auto; padding-bottom: 150px !important; }}
    [data-testid="stSidebar"] {{ background-color: rgba(255, 255, 255, 0.15) !important; backdrop-filter: blur(2px); }}
    [data-testid="stChatMessage"] {{ background-color: rgba(0, 0, 0, 0.5) !important; border-radius: 15px; margin-bottom: 15px; padding: 20px; }}
    .stChatMessage .stMarkdown * {{ color: #ffffff !important; text-shadow: 1px 1px 4px rgba(0,0,0,0.8); font-size: 1.1rem; }}
    </style>
"""
st.markdown(css_style, unsafe_allow_html=True)

# 사이드바 설정
with st.sidebar:
    st.markdown("### 🌴 다낭 위드어스 AI")
    st.link_button("💖 실시간 예약 상담하기", "https://open.kakao.com/o/sxJ8neWg", use_container_width=True)
    st.divider()
    st.markdown("⏰ 다낭 현재 시간")
    components.html("""<div id="c" style="color:white;font-size:24px;text-align:center;font-weight:bold;"></div><script>setInterval(()=>{document.getElementById('c').innerText=new Date().toLocaleTimeString('ko-KR',{timeZone:'Asia/Ho_Chi_Minh',hour12:false});},1000);</script>""", height=50)

# 메인 제목
st.markdown("""<h1 style="text-align: center; color: #87CEEB; text-shadow: 2px 2px 4px #000; font-weight: 900;">🌴 언제나 놀라운 만족감! With Us!</h1>""", unsafe_allow_html=True)

if "messages" not in st.session_state: st.session_state.messages = []
if "user_id" not in st.session_state: st.session_state.user_id = str(uuid.uuid4())

# 데이터 로드
db = get_withus_db()
if not db:
    st.info("💡 현재 위블리가 정보를 불러오고 있습니다. 잠시만 기다려 주세요!")

# 기존 대화 렌더링
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar=USER_AVATAR if msg["role"]=="user" else WIBLY_AVATAR):
        st.markdown(msg["content"])

auto_scroll_to_bottom()

# 채팅 입력창 (드디어 나타납니다!)
if prompt := st.chat_input("인원과 날짜를 말씀해 주세요!"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar=USER_AVATAR): st.markdown(prompt)
    
    with st.chat_message("assistant", avatar=WIBLY_AVATAR):
        placeholder = st.empty()
        placeholder.markdown("🌀 위블리가 열심히 뛰고 있습니당!! 🏃‍♀️💨")
        
        try:
            genai.configure(api_key=API_KEY)
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(f"당신은 다낭 위드어스 매니저 위블리입니다. 다음 정보를 참고하세요: {db}\n질문: {prompt}")
            full_res = response.text
            placeholder.markdown(full_res)
            run_background_tasks(st.session_state.user_id, prompt, full_res)
        except Exception as e:
            full_res = "앗! 잠시 위블리가 숨이 찼나 봐요. 다시 한번 말씀해 주시겠어요? 😅"
            placeholder.markdown(full_res)
    
    st.session_state.messages.append({"role": "assistant", "content": full_res})
    st.rerun()
