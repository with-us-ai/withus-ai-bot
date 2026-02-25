import streamlit as st

# [UI 설정] 반드시 맨 윗줄에 딱 한 번만 있어야 합니다!
st.set_page_config(page_title="다낭 위드어스 AI 컨시어지", page_icon="🌴", layout="wide")

import streamlit.components.v1 as components
import google.generativeai as genai
from google.oauth2 import service_account
from googleapiclient.discovery import build
import json
import datetime, requests, uuid, os, urllib.parse, base64, re, html, threading

# ==========================================
# 🚨 정규식(Regex) 정의 (이 부분이 빠져서 에러가 났었습니다)
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

# 구글 서비스 계정 연결 (JSON 형식을 바로 읽어옵니다)
creds_dict = json.loads(st.secrets["GCP_SERVICE_ACCOUNT_JSON"])
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

@st.cache_resource
def get_sheets_service():
    try:
        # 파일 대신 금고 데이터를 사용하여 보안과 성능을 모두 잡았습니다.
        creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        return build('sheets', 'v4', credentials=creds)
    except Exception:
        return None

# ==========================================
# 🎨 이미지 변환 및 경로 설정
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
LOGO_WATERMARK_FILE = "logo_white.png"

# ==========================================
# 📊 데이터 로드 및 통신 함수
# ==========================================
@st.cache_data(ttl=600)
def get_withus_db():
    service = get_sheets_service()
    if not service: return None
    try:
        ranges = ['DB!A2:J50', '골프!A2:F30', '스파!A2:H30', '차량!A2:J30', '이발소!A2:F30']
        result = service.spreadsheets().values().batchGet(spreadsheetId=SHEET_ID, ranges=ranges).execute()
        v = result.get('valueRanges', [])
        def fd(d): return "\n".join([" | ".join(map(str, r)) for r in d]) if d else "데이터 없음"
        return {"villa": fd(v[0].get('values', [])), "golf": fd(v[1].get('values', [])), "spa": fd(v[2].get('values', [])), "car": fd(v[3].get('values', [])), "barber": fd(v[4].get('values', []))}
    except: return None

def send_tele(u_id, u_m, a_m):
    safe_um = html.escape(u_m)
    safe_am = html.escape(a_m)
    text = f"🔔 <b>[위블리 웹 상담]</b>\n👤 고객({u_id[-4:]}): {safe_um}\n🤖 위블리:\n{safe_am}"
    try: requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"})
    except: pass

def append_to_sheet(u_id, u_t, a_t):
    service = get_sheets_service()
    if not service: return
    try:
        now = (datetime.datetime.utcnow() + datetime.timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S')
        service.spreadsheets().values().append(spreadsheetId=SHEET_ID, range='로그!A:D', valueInputOption='USER_ENTERED', body={'values': [[now, u_id, u_t, a_t]]}).execute()
    except: pass

def run_background_tasks(u_id, u_m, a_m):
    threading.Thread(target=append_to_sheet, args=(u_id, u_m, a_m)).start()
    threading.Thread(target=send_tele, args=(u_id, u_m, a_m)).start()

def auto_scroll_to_bottom():
    js_code = """
    <script>
        function scrollToBottom() {
            try {
                var doc = window.parent.document;
                var chatBoxes = doc.querySelectorAll('[data-testid="stChatMessage"]');
                if (chatBoxes && chatBoxes.length > 0) {
                    chatBoxes[chatBoxes.length - 1].scrollIntoView({ behavior: 'smooth', block: 'end' });
                }
            } catch (e) {}
        }
        setTimeout(scrollToBottom, 100);
        setTimeout(scrollToBottom, 400);
    </script>
    """
    components.html(js_code, height=0)

# ==========================================
# 🎨 UI 디자인 (CSS 적용)
# ==========================================
css_style = """
    <style>
    #MainMenu, header, footer {visibility: hidden;}
"""

if os.path.exists(BACKGROUND_IMAGE_FILE):
    bg_bin = get_base64_of_bin_file(BACKGROUND_IMAGE_FILE)
    css_style += f"""
    .stApp {{
        background-image: url("data:image/png;base64,{bg_bin}") !important;
        background-size: cover !important;
        background-position: center !important;
        background-repeat: no-repeat !important;
        background-attachment: fixed !important;
    }}
    """

css_style += """
    .main .block-container { max-width: 1000px; margin: auto; padding-bottom: 150px !important; }
    [data-testid="stSidebar"] { background-color: rgba(255, 255, 255, 0.15) !important; backdrop-filter: blur(2px); }
    [data-testid="stChatMessage"] { background-color: rgba(0, 0, 0, 0.5) !important; border-radius: 15px; margin-bottom: 15px; }
    .stChatMessage .stMarkdown * { color: #ffffff !important; text-shadow: 1px 1px 4px rgba(0,0,0,0.8); }
    </style>
"""
st.markdown(css_style, unsafe_allow_html=True)

if "messages" not in st.session_state: st.session_state.messages = []
if "user_id" not in st.session_state: st.session_state.user_id = str(uuid.uuid4())

# ==========================================
# 🛠️ 렌더링 엔진 (함수 정의)
# ==========================================
def render_assistant_content(content):
    lines = content.split('\n')
    text_buffer = []
    i = 0
    while i < len(lines):
        line = lines[i]
        photo_match = RE_PHOTO.search(line)
        video_match = RE_VIDEO.search(line)
        map_match = RE_MAP.search(line) 
        kakao_match = RE_KAKAO.search(line)
        
        if photo_match or video_match or map_match or kakao_match:
            if text_buffer:
                st.markdown('\n'.join(text_buffer), unsafe_allow_html=True)
                text_buffer = [] 
            if photo_match: st.link_button("📸 사진 보기", photo_match.group(1), use_container_width=True)
            if video_match: st.link_button("🎥 영상 보기", video_match.group(1), use_container_width=True)
            if map_match: st.link_button("🗺️ 위치 보기", map_match.group(1), use_container_width=True)
            if kakao_match: st.link_button("💖 실시간 상담하기 💖", kakao_match.group(1), use_container_width=True)
        else:
            text_buffer.append(RE_CLEAN.sub('', line))
        i += 1
    if text_buffer: st.markdown('\n'.join(text_buffer), unsafe_allow_html=True)

# 메인 화면 제목
st.markdown("""<h1 style="text-align: center; color: #87CEEB; text-shadow: 2px 2px 4px #000;">🌴 언제나 놀라운 만족감! With Us!</h1>""", unsafe_allow_html=True)

# 데이터 로드 확인
db = get_withus_db()
if db is None: st.stop()

# 대화 내역 렌더링
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar=USER_AVATAR if msg["role"]=="user" else WIBLY_AVATAR):
        if msg["role"] == "assistant": render_assistant_content(msg["content"])
        else: st.markdown(msg["content"])

auto_scroll_to_bottom()

# 채팅 입력창
if prompt := st.chat_input("인원과 날짜를 말씀해 주세요!"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar=USER_AVATAR): st.markdown(prompt)
    
    with st.chat_message("assistant", avatar=WIBLY_AVATAR):
        placeholder = st.empty()
        placeholder.markdown("🌀 위블리가 고객님을 위해 열심히 뛰고 있습니당!! 🏃‍♀️💨")
        
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        response = model.generate_content(f"당신은 다낭 위드어스 매니저 위블리입니다. 다음 정보를 참고해 답변하세요: {db}\n질문: {prompt}")
        full_res = response.text
        
        placeholder.empty()
        render_assistant_content(full_res)
        run_background_tasks(st.session_state.user_id, prompt, full_res)
    
    st.session_state.messages.append({"role": "assistant", "content": full_res})
    st.rerun()

# 사이드바
with st.sidebar:
    st.markdown("### 👇 담당자 호출 버튼 👇")
    st.link_button("💖 실시간 예약 상담하기 💖", "https://open.kakao.com/o/sxJ8neWg", use_container_width=True)
    st.divider()
    st.markdown("⏰ 다낭 시간")
    components.html("""<div id="clock" style="color:white; font-size:24px; text-align:center;"></div><script>setInterval(()=>{let t=new Date().toLocaleTimeString('ko-KR',{timeZone:'Asia/Ho_Chi_Minh',hour12:false});document.getElementById('clock').innerText=t;},1000);</script>""", height=50)
