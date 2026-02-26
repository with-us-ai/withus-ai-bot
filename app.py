import streamlit as st
import streamlit.components.v1 as components
import google.generativeai as genai
from google.oauth2 import service_account
from googleapiclient.discovery import build
import json, datetime, requests, uuid, os, urllib.parse, base64, re, html, threading

# [UI 설정] 반드시 맨 윗줄 고정
st.set_page_config(page_title="다낭 위드어스 AI 컨시어지", page_icon="🌴", layout="wide")

# ==========================================
# 🚨 [설정] 대표님의 고유 정보
# ==========================================
TELEGRAM_BOT_TOKEN = st.secrets["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = st.secrets["TELEGRAM_CHAT_ID"]
API_KEY = st.secrets["API_KEY"]
SHEET_ID = st.secrets["SHEET_ID"]
creds_dict = json.loads(st.secrets["GCP_SERVICE_ACCOUNT_JSON"])
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

genai.configure(api_key=API_KEY)

# ==========================================
# 🚀 [최적화 1] 정규식 패턴 미리 로드
# ==========================================
RE_PHOTO = re.compile(r'(?:사진\s*보기|사진\s*확인|사진확인|사진링크).*?((?:http|https)://[^\s\]]+)')
RE_VIDEO = re.compile(r'(?:영상\s*보기|영상\s*확인|영상확인|영상링크).*?((?:http|https)://[^\s\]]+)')
RE_MAP = re.compile(r'(?:위치\s*보기|구글\s*맵|지도\s*보기|위치\s*확인).*?((?:http|https)://[^\s\]]+)')
RE_KAKAO = re.compile(r'(https://open\.kakao\.com/[^\s\]]+)')
RE_CLEAN = re.compile(r'(?:사진|영상|위치|지도|링크|오픈채팅|확인).*?((?:http|https)://\S+)')

# ==========================================
# 🚀 [최적화 2] 구글 시트 인증 (금고 데이터 사용)
# ==========================================
@st.cache_resource
def get_sheets_service():
    try:
        creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        return build('sheets', 'v4', credentials=creds)
    except Exception as e:
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

# 텔레그램 발송
def send_tele(u_id, u_m, a_m):
    safe_um = html.escape(u_m)
    safe_am = html.escape(a_m)
    text = f"🔔 [위블리 웹 상담]\n👤 고객({u_id[-4:]}): {safe_um}\n🤖 위블리:\n{safe_am}"
    try: requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"})
    except: pass

# 구글 시트 저장
def append_to_sheet(u_id, u_t, a_t):
    service = get_sheets_service()
    if not service: return
    try:
        now = (datetime.datetime.utcnow() + datetime.timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S')
        service.spreadsheets().values().append(spreadsheetId=SHEET_ID, range='로그!A:D', valueInputOption='USER_ENTERED', body={'values': [[now, u_id, u_t, a_t]]}).execute()
    except: pass

# 백그라운드 작업 처리
def run_background_tasks(u_id, u_m, a_m):
    threading.Thread(target=append_to_sheet, args=(u_id, u_m, a_m)).start()
    threading.Thread(target=send_tele, args=(u_id, u_m, a_m)).start()

# 🚀 [오토 스크롤 엔진]
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
        setTimeout(scrollToBottom, 500);
    </script>
    """
    components.html(js_code, height=0)

# ==========================================
# 🎨 UI 디자인
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
        height: 100vh !important;
    }}
    """

css_style += """
    .main .block-container {
        background-color: transparent !important;
        max-width: 1000px; margin: auto;
        padding-bottom: 150px !important;
    }
    [data-testid="stSidebar"], [data-testid="stSidebar"] > div {
        background-color: rgba(255, 255, 255, 0.15) !important;
        backdrop-filter: blur(2px) !important;
        -webkit-backdrop-filter: blur(2px) !important;
    }
    [data-testid="stChatMessage"] {
        background-color: rgba(0, 0, 0, 0.5) !important;
        border-radius: 15px !important; margin-bottom: 15px !important;
        padding: 20px !important;
    }
    .stChatMessage .stMarkdown * {
        color: #ffffff !important; opacity: 1 !important;
        font-size: 1.1rem !important; font-weight: 400 !important;
        line-height: 1.8 !important; text-align: left !important;
        word-break: keep-all !important;
        text-shadow: 1px 1px 4px rgba(0,0,0,0.8), 2px 2px 8px rgba(0,0,0,0.6) !important;
    }
    .stChatMessage .stMarkdown strong { font-weight: 800 !important; color: #FFD700 !important; opacity: 1 !important; }
    .stChatMessage blockquote {
        border-left: 5px solid #87CEEB !important; background-color: rgba(0,0,0,0.3) !important;
        padding: 15px !important; margin: 10px 0 !important; opacity: 1 !important;
    }
    .stChatMessage blockquote * { color: #ffffff !important; opacity: 1 !important; }
    [data-testid="stBottom"], [data-testid="stBottom"] > div { background-color: transparent !important; background: transparent !important; }
    [data-testid="stBottom"]::before, [data-testid="stBottom"] > div::before { display: none !important; background: transparent !important; }
    </style>
"""
st.markdown(css_style, unsafe_allow_html=True)

if os.path.exists(LOGO_WATERMARK_FILE):
    logo_bin = get_base64_of_bin_file(LOGO_WATERMARK_FILE)
    st.markdown(f"""<div style="position: fixed; bottom: 150px; right: 30px; width: 150px; z-index: 9999; pointer-events: none; opacity: 0.85; transform: rotate(10deg); filter: drop-shadow(2px 4px 3px rgba(0,0,0,0.5));"><img src="data:image/png;base64,{logo_bin}" style="width: 100%;"></div>""", unsafe_allow_html=True)

if "messages" not in st.session_state: st.session_state.messages = []
if "user_id" not in st.session_state: st.session_state.user_id = str(uuid.uuid4())

# ==========================================
# 🛠️ 렌더링 엔진 (버튼 생성기)
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
                st.markdown('\n'.join(text_buffer).strip(), unsafe_allow_html=True)
                text_buffer = []

            buttons = []
            if photo_match: buttons.append(("📸 사진 보기", photo_match.group(1)))
            if video_match: buttons.append(("🎥 영상 보기", video_match.group(1)))
            if map_match: buttons.append(("🗺️ 위치 보기", map_match.group(1)))

            while i + 1 < len(lines):
                next_line = lines[i+1]
                n_photo = RE_PHOTO.search(next_line)
                n_video = RE_VIDEO.search(next_line)
                n_map = RE_MAP.search(next_line)
                if n_photo or n_video or n_map:
                    if n_photo: buttons.append(("📸 사진 보기", n_photo.group(1)))
                    if n_video: buttons.append(("🎥 영상 보기", n_video.group(1)))
                    if n_map: buttons.append(("🗺️ 위치 보기", n_map.group(1)))
                    i += 1
                else: break

            if buttons:
                cols = st.columns(len(buttons))
                for idx, (lbl, url) in enumerate(buttons):
                    with cols[idx]: st.link_button(lbl, url, use_container_width=True)

            if kakao_match:
                st.markdown("<br>", unsafe_allow_html=True)
                st.link_button("💖 실시간 예약 상담하기 💖", kakao_match.group(1), use_container_width=True)
        else:
            clean_line = RE_CLEAN.sub('', line).strip()
            text_buffer.append(clean_line)
        i += 1

    if text_buffer:
        st.markdown('\n'.join(text_buffer).strip(), unsafe_allow_html=True)

# 메인 화면
col = st.columns([1, 10, 1])[1]
with col:
    if os.path.exists(LOGO_WATERMARK_FILE):
        title_logo_bin = get_base64_of_bin_file(LOGO_WATERMARK_FILE)
        st.markdown(f"""
        <div style="display: flex; align-items: center; justify-content: center; gap: 20px; margin-bottom: 30px; flex-wrap: wrap;">
            <h1 style="margin: 0; color: #87CEEB; font-size: 3rem; font-weight: 900;
                       text-shadow: -1.5px -1.5px 0 #000, 1.5px -1.5px 0 #000, -1.5px 1.5px 0 #000, 1.5px 1.5px 0 #000,
                                    -3px -3px 0 #000, 3px -3px 0 #000, -3px 3px 0 #000, 3px 3px 0 #000,
                                    5px 5px 8px rgba(0,0,0,0.8);">🌴 언제나 놀라운 만족감! With Us!</h1>
            <img src="data:image/png;base64,{title_logo_bin}" style="height: 120px; filter: drop-shadow(2px 4px 3px rgba(0,0,0,0.6));">
        </div>
        """, unsafe_allow_html=True)
    else:
        st.title("🌴 언제나 놀라운 만족감! With Us!")

    db = get_withus_db()
    if db is None: st.stop()

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar=USER_AVATAR if msg["role"]=="user" else WIBLY_AVATAR):
            if msg["role"] == "assistant": render_assistant_content(msg["content"])
            else: st.markdown(msg["content"])

# 🚀 메시지 출력 후 스크롤 내리기
auto_scroll_to_bottom()

if prompt := st.chat_input("인원과 날짜를 말씀해 주세요!"):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(prompt)
        
    # 입력과 동시에 다시 한번 스크롤 내리기
    auto_scroll_to_bottom()

    with st.chat_message("assistant", avatar=WIBLY_AVATAR):
        placeholder = st.empty()
        placeholder.markdown("✨ **위블리가 실시간 DB를 확인하여 맞춤 견적을 작성 중입니다...** ⏳")

        # 🚨 민감 키워드 검사
        vip_keywords = ["가라오케", "에코걸", "에코", "떡마사지", "VIP마사지", "불건전", "가라", "떡마사", "VIP마사","불건마", "불건마사", "불건마사지"]
        
        prompt_no_space = prompt.replace(" ", "")
        has_vip = any(keyword in prompt_no_space for keyword in vip_keywords)

        safe_prompt = prompt
        if has_vip:
            for kw in vip_keywords:
                safe_prompt = safe_prompt.replace(kw, "").strip()

        # 🚨 귀여운 VIP 철벽 템플릿
        vip_template = """\n\n━━━━━━━━━━━━━━
🔥 **다낭 위드어스 스페셜 문의**
━━━━━━━━━━━━━━

고객님~~🥰 문의하신 특별한(?) 내용은 위블리가 대답할 수 없는 정보에용 ㅠㅡㅠ
아래 **실시간 상담 링크 버튼**을 눌러서! 상담해주시면!
저희 다낭 위드어스의 꼼꼼하신 대표님이 더 정확하고 자세한 안내 해드릴꺼에용~ 💕

> 👇 **아래 [실시간 예약 상담하기] 버튼을 꾹! 눌러주세요!** 👇

오픈채팅: https://open.kakao.com/o/sxJ8neWg"""

        # 고객이 오직 유흥 키워드만 입력했을 경우 (가로채기)
        if has_vip and len(safe_prompt) <= 2:
            full_res = vip_template.strip()
            placeholder.empty()
            with placeholder.container():
                render_assistant_content(full_res)
        
        # 정상적인 질문이 포함되어 있는 경우 (AI 처리 + 맨 밑에 철벽 멘트 추가)
        else:
            # 🚨 1. 히스토리에서 민감 키워드 싹 지우기 (AI가 훔쳐보지 못하게 원천 차단!)
            clean_history = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-10:]])
            for kw in vip_keywords:
                clean_history = clean_history.replace(kw, "")

            master_instruction = f"""당신은 다낭 위드어스 매니저 '위블리'입니다.
아래 [🚨 상황별 답변 지침]을 우선적으로 파악하여 똑똑하게 대답하세요.

[🚨 상황별 답변 지침 (고객의 질문 의도를 파악하세요!)]

👉 **상황 A: 고객이 처음 '인원/날짜'를 말하거나, '숙소(풀빌라) 및 차량' 견적을 문의할 때**
1. 맞춤형 인사
2. 풀빌라/차량 추천 (설명 바로 밑줄에 반드시 "사진 보기: [URL]", "영상 보기: [URL]" 작성)
3. 아래 [가견적 템플릿]을 사용하여 깔끔한 견적서 제공
4. 맺음말 및 오픈채팅 링크 (오픈채팅: https://open.kakao.com/o/sxJ8neWg)

👉 **상황 B: 숙소 문의 없이 특정 서비스만 단독으로 물어볼 때**
1. 맞춤형 인사
2. [실시간 DB]를 꼼꼼히 확인하여, 고객이 묻는 업체의 상세 코스 설명, 정확한 가격, 장점을 상세히 설명하세요.
3. 🚨 풀빌라 가견적서를 절대 다시 출력하지 마세요!
4. 맺음말 및 오픈채팅 링크

[🚨 가독성 및 형식 절대 지침]
- 텍스트가 뭉쳐보이지 않도록 문장 1~2개마다 반드시 엔터(줄바꿈)를 두 번 쳐서 문단을 나누세요.
- 중요한 키워드나 숙소명/업체명은 반드시 **굵게(볼드체)** 처리하여 눈에 띄게 만드세요.

[🚨 절대 준수 지침]
1. 달러 기호($) 절대 금지! 한글로 '달러' 표기. (베트남 동은 '동'으로 표기)
2. 기억력: 위 대화 히스토리에서 고객이 말한 사항을 절대 다시 묻지 마세요.
3. ★우선 추천 풀빌라: 인원수(=룸 개수)에 따라 무조건 1순위로 추천하세요! (2룸:미니더블, 3룸:블랙미러, 4룸:블루에덴1/버블캐슬5, 5룸:피크닉, 6룸:피크닉2, 8룸:네온드림)
4. ★차량(솔라티) 견적 룰: 기본 단가는 무조건 '80달러'로 계산하세요.
5. 🚫 ★초강력 민감 정보 차단★: 고객의 질문에 유흥, 에코걸, 가라오케 등 민감한 키워드가 포함되어 있더라도, 견적서의 '추가 서비스 견적'이나 본문 그 어디에도 절대 1글자도 언급하지 마세요! "특수 서비스"라는 말도 절대 쓰지 마세요. 오직 풀빌라와 차량, 일반 마사지 견적만 작성해야 합니다.

[가견적 템플릿 (상황 A에서만 사용!)]
━━━━━━━━━━━━━━
🧾 **다낭 위드어스 가견적서**
━━━━━━━━━━━━━━
**🗓️ 일정:** [일정]
**👥 인원:** [인원수]명

> **🏡 숙소 견적**
> - 내용: [숙소명] ([박수]박)
> - 금액: [달러단가]달러 x [박수]박 (약 [원화금액]원)
>
> **🚐 차량 견적**
> - 내용: 14인승 솔라티 ([일수]일)
> - 금액: 기본 80달러 x [일수]일 (약 [원화금액]원)
>
> **💆‍♂️ 추가 서비스 견적**
> - 내용: [업체명 및 코스명] ([인원수]명)
> - 금액: [단가] x [인원수]명 (약 [원화금액]원)
>
> - 💡 *안내: 차량 요금은 동선/이용 시간에 따라 80~120달러로 유동 적용됩니다.*

━━━━━━━━━━━━━━
💰 **예상 총합: 약 [총합원화]원**
━━━━━━━━━━━━━━
*(💸 환율 1달러=1,500원 기준)*

[실시간 DB]
{db}
[대화 히스토리]
{clean_history}"""

            try:
                # 🚀 확고한 지시대로 gemini-3-flash-preview 고정
                model = genai.GenerativeModel('gemini-3-flash-preview')
                response = model.generate_content(f"{master_instruction}\n고객님: {safe_prompt}", stream=True)

                full_res = ""
                is_first_chunk = True

                for chunk in response:
                    if chunk.text:
                        if is_first_chunk:
                            placeholder.empty()
                            is_first_chunk = False
                        full_res += chunk.text
                        placeholder.markdown(full_res + "▌")
                        # 글자가 출력될 때마다 스크롤을 끝까지 내리도록 지시
                        auto_scroll_to_bottom()

                # 🚨 정상 질문 + 유흥 질문이 섞여 있을 때 맨 마지막에 멘트 추가
                if has_vip:
                    full_res += vip_template

                placeholder.empty()
                with placeholder.container():
                    render_assistant_content(full_res)
                    auto_scroll_to_bottom()

            except Exception as e:
                full_res = f"앗! 일시적인 통신 오류가 발생했어요. (에러 원인: {e})"
                placeholder.markdown(full_res)

        run_background_tasks(st.session_state.user_id, prompt, full_res)

    st.session_state.messages.append({"role": "assistant", "content": full_res})
    st.rerun()

# ==========================================
# 🌟 사이드바 (간소화 완료)
# ==========================================
with st.sidebar:
    t_style = "color: #ffffff; font-weight: 900; text-align: center; text-shadow: -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000, -2px -2px 0 #000, 2px -2px 0 #000, -2px 2px 0 #000, 2px 2px 0 #000, 3px 3px 5px rgba(0,0,0,0.8);"

    st.markdown(f"""<h3 style="{t_style}">👇 담당자 호출 버튼 👇</h3>""", unsafe_allow_html=True)
    st.link_button("💖 담당자 호출 버튼 💖", "https://open.kakao.com/o/sxJ8neWg", use_container_width=True)
    st.divider()

    st.markdown(f"""<h3 style="{t_style}">🚀 위블리 빠른 추천 🚀</h3>""", unsafe_allow_html=True)

    # 🚨 [수정됨] 버튼 이름 간소화 완료
    if st.button('" 맛집 " 추천', use_container_width=True):
        prompt = "다낭 맛집 추천해 줘"
        st.session_state.messages.append({"role": "user", "content": prompt})

        food_res = """고객님, 다낭에 오셨으면 맛집 투어는 필수죠! 🤤
위드어스가 자신 있게 추천하는 찐 맛집 리스트입니다.

━━━━━━━━━━━━━━
🍲 **다낭 위드어스 찐 맛집 리스트**
━━━━━━━━━━━━━━
> **1. Long Beach Seafood (해산물)**
> - 특징: 주문과 동시에 요리 시작! 신선한 재료, 맛, 합리적 가격까지 만족!
> 위치 보기: https://maps.app.goo.gl/gdAXR1YPhq4a2nmk7

> **2. 4U Seafood (해산물)**
> - 특징: 미케비치 바로 앞 오션뷰! 직원이 친절하고 깔끔.
> 위치 보기: https://maps.app.goo.gl/nnEVzeRm8FKxdHaV9

> **3. FOR YOU Steak House (스테이크)**
> - 특징: 고기 신선도 최고! 오션뷰 프리미엄 맛집.
> 위치 보기: https://maps.app.goo.gl/8xfefEGvk1rSNWz36

> **4. 템하이산 (현지/해산물)**
> - 특징: 가족 단위 한국 손님 픽 1위!
> 위치 보기: https://maps.app.goo.gl/vAfGNWuVCGVgRmEu9?g\_st=ipc

> **5. Van may 식당 (로컬)**
> - 특징: 안트엉 지역 찐 로컬 식당.
> 위치 보기: https://maps.app.goo.gl/GpGDfq8U4vhwoXdg7?g\_st=ipc

> **6. 다빈 식당 (중식)**
> - 특징: 한국보다 더 맛있는 중국집! 간짜장/탕수육 강추.
> 위치 보기: https://maps.app.goo.gl/CbegPCx3irjzXFsE6?g\_st=ipc

> **7. Mad Platter (양식/씨푸드)**
> - 특징: 끝내주는 오션뷰와 훌륭한 맛!
> 위치 보기: https://maps.app.goo.gl/m3zEaZeAjeTSbSVQ9?g\_st=ipc

> **8. GU EM BBQ RESTAURANT (고기집)**
> - 특징: 팜반동 한인타운 신상 고기집!
> 위치 보기: https://maps.app.goo.gl/Yrumio8dmkSrjxJy9?g\_st=ipc

> **9. 무쇠고기살롱 (고기집)**
> - 특징: 무쇠판에 직접 구워주는 팜반동 맛집.
> 위치 보기: https://maps.app.goo.gl/r7JZpB3aUoNCx8h67

> **10. 논라 (베트남 가정식)**
> - 특징: 깔끔하고 맛있는 가성비 로컬 식당!
> 위치 보기: https://maps.app.goo.gl/n2xL214kv66R3Cvs5

> **11. 쭈꾸뽕 (한식)**
> - 특징: 다낭에서 맛보는 매콤한 쭈꾸미!
> 위치 보기: https://maps.app.goo.gl/kXLGHHA7YgwDRTDz7

> **12. Gordon's New York Pizza Cityside (피자)**
> - 특징: 한강 뷰를 보며 즐기는 피자 찐 맛집!
> 위치 보기: https://maps.app.goo.gl/sjQ8Ligwj95khgzs5"""

        st.session_state.messages.append({"role": "assistant", "content": food_res})
        run_background_tasks(st.session_state.user_id, prompt, food_res)
        st.rerun()

    if st.button('" 관광지 " 추천', use_container_width=True):
        prompt = "다낭 관광지 추천해 줘"
        st.session_state.messages.append({"role": "user", "content": prompt})

        tour_res = """고객님, 다낭의 핵심 관광지들을 안내해 드립니다! 📸

━━━━━━━━━━━━━━
🏞️ **다낭 위드어스 추천 관광지**
━━━━━━━━━━━━━━
> **1. 바나힐 (Ba Na Hills)**
> - 특징: 세계에서 가장 긴 케이블카와 골든브릿지가 있는 다낭 랜드마크!
> 위치 보기: https://maps.app.goo.gl/9cyKvXuwaqXWQP9V8
>
> **2. 호이안 올드타운 (Hoi An)**
> - 특징: 다낭에서 차로 40분. 로맨틱한 야경 맛집!
> 위치 보기: https://maps.app.goo.gl/ysgHAp7ZtnrgKvo79
>
> **3. 오행산 (Marble Mountains)**
> - 특징: 5개의 대리석 산으로 이루어진 명소!
> 위치 보기: https://maps.app.goo.gl/9FArYjJ8ANYbNvZLA
>
> **4. 누이탄타이 핫스프링 파크 (온천/워터파크)**
> - 특징: 다낭에서 즐기는 이색 온천 여행!
> 위치 보기: https://maps.app.goo.gl/TRFgxPQQSXf7ekNh9"""

        st.session_state.messages.append({"role": "assistant", "content": tour_res})
        run_background_tasks(st.session_state.user_id, prompt, tour_res)
        st.rerun()

    if st.button('" 카페 " 추천', use_container_width=True):
        prompt = "다낭 분위기 좋은 카페 추천해 줘"
        st.session_state.messages.append({"role": "user", "content": prompt})

        cafe_res = """고객님, 여행 중 달콤한 휴식을 위한 다낭 예쁜 카페를 소개합니다! ☕

━━━━━━━━━━━━━━
☕ **다낭 위드어스 찐 로컬 카페 리스트**
━━━━━━━━━━━━━━
> **1. 콩카페 다낭 (Cong Caphe)**
> - 특징: 다낭 로컬 카페의 스타벅스!
> 위치 보기: https://maps.app.goo.gl/w4u7PWDRSqWHJBvr6

> **2. Cửa Ngõ Café – Cửa Hàng Số 2**
> - 특징: 잉어 먹이 주기 체험 가능, 아이들과 가기 좋아요.
> 위치 보기: https://maps.app.goo.gl/tLGUw7gacy1cRiVM7

> **3. Gé Cafe**
> - 특징: 이색적인 인테리어, 한시장 근처 쉼터.
> 위치 보기: https://maps.app.goo.gl/4HPkAM257qRzWSd3A

> **4. Tou Zone food & Drink Đà Nẵng**
> - 특징: 한강 뷰를 따라 걷다 나오는 찐 로컬 감성.
> 위치 보기: https://maps.app.goo.gl/8ztEfa1sw4PxS1tw9

> **5. Wind Garden Coffee**
> - 특징: 팜반동 한인타운 근처, 분위기 깡패 카페!
> 위치 보기: https://maps.app.goo.gl/6NB3SzjvsuBj7y1c8"""

        st.session_state.messages.append({"role": "assistant", "content": cafe_res})
        run_background_tasks(st.session_state.user_id, prompt, cafe_res)
        st.rerun()

    st.markdown("""
    <div style="background-color: rgba(0,0,0,0.5); padding: 15px; border-radius: 10px; color: white; margin-top: 15px;">
        <p style="font-weight: bold; margin-bottom: 8px; color: #87CEEB;">💡 위블리 사용 설명서</p>
        <p style="font-size: 0.9em; margin-bottom: 10px; line-height: 1.4;">추가로 궁금하신 사항은 하단 채팅창에 자유롭게 입력해 주세요!</p>
        <p style="font-size: 0.85em; color: #FFD700; margin-bottom: 3px;">예시) 다낭 이발소 추천해줘</p>
        <p style="font-size: 0.85em; color: #FFD700; margin-bottom: 0;">예시) 다낭 마사지 추천해줘</p>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    st.markdown(f"""<h3 style="{t_style}">🌤️ 다낭 날씨</h3>""", unsafe_allow_html=True)
    weather_html = """<a class="weatherwidget-io" href="https://forecast7.com/en/16d05108d20/da-nang/" data-label_1="다낭 실시간 날씨" data-label_2="Da Nang" data-theme="dark" data-basecolor="rgba(0,0,0,0)" data-textcolor="#ffffff" >다낭 실시간 날씨</a><script>!function(d,s,id){var js,fjs=d.getElementsByTagName(s)[0];if(!d.getElementById(id)){js=d.createElement(s);js.id=id;js.src='https://weatherwidget.io/js/widget.min.js';fjs.parentNode.insertBefore(js,fjs);}}(document,'script','weatherwidget-io-js');</script>"""
    components.html(weather_html, height=120)
    st.divider()
    st.markdown(f"""<h3 style="{t_style}">⏰ 다낭 시간</h3>""", unsafe_allow_html=True)
    time_html = """<div style="display: flex; justify-content: center; align-items: center; height: 100%;"><div id="clock" style="color: #ffffff; font-size: 32px; font-weight: 900; font-family: sans-serif; text-shadow: -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000, 3px 3px 5px rgba(0,0,0,0.8);"></div></div><script>function updateTime() {let options = { timeZone: 'Asia/Ho_Chi_Minh', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false };let timeString = new Date().toLocaleTimeString('ko-KR', options);document.getElementById('clock').innerText = timeString;}setInterval(updateTime, 1000);updateTime();</script>"""
    components.html(time_html, height=60)
