import streamlit as st
import streamlit.components.v1 as components 
import google.generativeai as genai
from google.oauth2 import service_account
from googleapiclient.discovery import build
import datetime, requests, uuid, os, urllib.parse, base64, re, html, threading

# ==========================================
# 🚨 [설정] 대표님의 고유 정보
# ==========================================
TELEGRAM_BOT_TOKEN = "8600043269:AAEJ6WYBzxrbuM21tB4qsROy1vE0wiq_Pdc"
TELEGRAM_CHAT_ID = "6043903515"
API_KEY = "AIzaSyA9m5N1VI5aBSjgah36fFRbxe2y2CXqiBY"
SHEET_ID = "1fU954PzRt8vuwhUldNA8PP8KXgXTZJ6eOGhLuycco4I"

genai.configure(api_key=API_KEY)

# ==========================================
# 🚀 [최적화 1] 정규식 패턴 (오픈채팅 버튼화 완벽 적용)
# ==========================================
RE_PHOTO = re.compile(r'(?:사진\s*보기|사진\s*확인|사진확인|사진링크).*?((?:http|https)://[^\s\)]+)')
RE_VIDEO = re.compile(r'(?:영상\s*보기|영상\s*확인|영상확인|영상링크).*?((?:http|https)://[^\s\)]+)')
RE_MAP = re.compile(r'(?:위치\s*보기|구글\s*맵|지도\s*보기|위치\s*확인).*?((?:http|https)://[^\s\)]+)')
RE_KAKAO = re.compile(r'(https://open\.kakao\.com/[^\s\)]+)')
RE_CLEAN = re.compile(r'(?:사진|영상|위치|지도|링크|오픈채팅|확인).*?((?:http|https)://\S+)')

# ==========================================
# 🚀 [최적화 2] 구글 시트 인증 객체 캐싱
# ==========================================
@st.cache_resource
def get_sheets_service():
    try:
        creds = service_account.Credentials.from_service_account_file('credentials.json')
        return build('sheets', 'v4', credentials=creds)
    except Exception as e:
        return None

# ==========================================
# 🎨 이미지 변환 및 경로 설정
# ==========================================
@st.cache_data
def get_base64_of_bin_file(bin_file):
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

# ✨ [절대 스크롤 로직] 마지막 채팅창을 강제로 추적해서 화면을 꽂아버립니다!
def auto_scroll_to_bottom():
    js_code = """
    <script>
        function scrollToBottom() {
            try {
                var doc = window.parent.document;
                // 마지막 채팅 메시지 박스를 찾습니다.
                var chatBoxes = doc.querySelectorAll('[data-testid="stChatMessage"]');
                if (chatBoxes && chatBoxes.length > 0) {
                    // 가장 마지막 채팅창으로 부드럽게 스크롤!
                    chatBoxes[chatBoxes.length - 1].scrollIntoView({ behavior: 'smooth', block: 'end' });
                } else {
                    // 혹시 채팅박스를 못 찾으면 메인 화면을 끝까지 내립니다.
                    var mainContainer = doc.querySelector('.stMainBlockContainer') || doc.querySelector('.main');
                    if (mainContainer) mainContainer.scrollTop = mainContainer.scrollHeight;
                }
            } catch (e) {}
        }
        // 화면이 다 그려지는 타이밍에 맞춰 0.1초, 0.4초 뒤에 확실하게 당깁니다.
        setTimeout(scrollToBottom, 100);
        setTimeout(scrollToBottom, 400);
    </script>
    """
    components.html(js_code, height=0)

# ==========================================
# 🎨 UI 디자인 
# ==========================================
st.set_page_config(page_title="다낭 위드어스 AI 컨시어지", page_icon="🌴", layout="wide")

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
        color: #ffffff !important; 
        opacity: 1 !important; 
        font-size: 1.1rem !important; 
        font-weight: 400 !important; 
        line-height: 1.8 !important; 
        text-align: left !important;
        word-break: keep-all !important; 
        text-shadow: 1px 1px 4px rgba(0,0,0,0.8), 2px 2px 8px rgba(0,0,0,0.6) !important; 
    }
    
    .stChatMessage .stMarkdown strong {
        font-weight: 800 !important;
        color: #FFD700 !important; 
        opacity: 1 !important;
    }
    
    .stChatMessage blockquote {
        border-left: 5px solid #87CEEB !important; 
        background-color: rgba(0,0,0,0.3) !important;
        padding: 15px !important; margin: 10px 0 !important;
        opacity: 1 !important; 
    }

    .stChatMessage blockquote * {
        color: #ffffff !important; 
        opacity: 1 !important; 
    }

    [data-testid="stBottom"], [data-testid="stBottom"] > div {
        background-color: transparent !important;
        background: transparent !important;
    }
    [data-testid="stBottom"]::before, [data-testid="stBottom"] > div::before {
        display: none !important;
        background: transparent !important;
    }

    /* 🔄 로딩 스피너 애니메이션 */
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    .spinner {
        display: inline-block;
        animation: spin 1s linear infinite;
        margin-right: 10px;
    }
    </style>
"""
st.markdown(css_style, unsafe_allow_html=True)

if os.path.exists(LOGO_WATERMARK_FILE):
    logo_bin = get_base64_of_bin_file(LOGO_WATERMARK_FILE)
    st.markdown(f"""<div style="position: fixed; bottom: 150px; right: 30px; width: 150px; z-index: 9999; pointer-events: none; opacity: 0.85; transform: rotate(10deg); filter: drop-shadow(2px 4px 3px rgba(0,0,0,0.5));"><img src="data:image/png;base64,{logo_bin}" style="width: 100%;"></div>""", unsafe_allow_html=True)

if "messages" not in st.session_state: st.session_state.messages = []
if "user_id" not in st.session_state: st.session_state.user_id = str(uuid.uuid4())

# ==========================================
# 🛠️ 렌더링 엔진 (엔터 보존 및 무조건 버튼화)
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
            clean_line = RE_CLEAN.sub('', line)
            clean_line = re.sub(r'https://open\.kakao\.com[^\s]+', '', clean_line).rstrip()
            text_buffer.append(clean_line) 
        i += 1
        
    if text_buffer:
        st.markdown('\n'.join(text_buffer), unsafe_allow_html=True)

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

    # 💬 대화 내역 렌더링
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar=USER_AVATAR if msg["role"]=="user" else WIBLY_AVATAR):
            if msg["role"] == "assistant": render_assistant_content(msg["content"])
            else: st.markdown(msg["content"])

# 🔥 대화 내역이 화면에 다 그려진 직후 무조건 오토 스크롤을 한 번 실행합니다! (핵심 해결책)
auto_scroll_to_bottom()

if prompt := st.chat_input("인원과 날짜를 말씀해 주세요!"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user", avatar=USER_AVATAR): 
        st.markdown(prompt)
        
    with st.chat_message("assistant", avatar=WIBLY_AVATAR): 
        placeholder = st.empty() 
        
        # 🌀 회전 로딩 애니메이션
        spinner_html = """
        <div style='display: flex; align-items: center;'>
            <span class='spinner' style='font-size: 1.5rem;'>🌀</span>
            <span style='font-size: 1.1rem; font-weight: bold;'>초! 고성능! 위블리가 고객님을 위해 열심히 뛰고 있습니당!! 🏃‍♀️💨</span>
        </div>
        """
        placeholder.markdown(spinner_html, unsafe_allow_html=True)
        
        # 고객 질문과 동시에 한 번 더 스크롤 다운! (로딩 애니메이션이 보이게)
        auto_scroll_to_bottom()
        
        # 🚨 위험 키워드 및 정상 키워드 (하이브리드 분기)
        vip_keywords = ["가라오케", "에코걸", "에코", "떡마사지", "VIP마사지", "불건전", "가라", "떡마사", "VIP마사","불건마", "불건마사", "불건마사지"]
        normal_keywords = ["풀빌라", "숙소", "빌라", "차량", "렌트", "솔라티", "골프", "마사지", "스파", "이발", "맛집", "식당", "관광", "투어", "바나힐", "호이안", "카페", "견적", "예약"]
        
        prompt_no_space = prompt.replace(" ", "")
        has_vip = any(keyword in prompt_no_space for keyword in vip_keywords)
        has_normal = any(keyword in prompt_no_space for keyword in normal_keywords)
        
        safe_ai_prompt = prompt
        if has_vip:
            for kw in vip_keywords:
                safe_ai_prompt = safe_ai_prompt.replace(kw, "").strip()

        # ✨ 수정된 VIP 안내 템플릿
        vip_template = """\n\n---
🔥 **다낭 위드어스 VIP 스페셜 안내**
---

고객님~~🥰 문의하신 특별한(?) 내용은 위블리가 직접 안내해 드리기 조금 어려운 부분이에용 ㅠ_ㅠ
자세한 상담은 저희 다낭 위드어스의 꼼꼼하신 대표님과 연결 후 편하게 상담해 주세용! ✨

> 🌟 **예약을 확정하시거나 상세한 상담을 원하시면 지금 바로 아래 버튼을 통해 말씀해 주세요!**
> **대표님이 아주 빠르고 상세하게 예약 진행을 도와드릴 거예요!** ✨
>
> 👇 **아래 [실시간 예약 상담하기] 버튼을 꾹! 눌러주세요!** 👇

링크: https://open.kakao.com/o/sxJ8neWg"""

        # 🚀 [가로채기 100%] 유흥 질문만 있을 경우 AI 호출 차단
        if has_vip and not has_normal:
            full_res = vip_template.strip()
            placeholder.empty()
            with placeholder.container():
                render_assistant_content(full_res)
            
        else:
            raw_history = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-10:]])
            clean_history = raw_history
            for kw in vip_keywords:
                clean_history = clean_history.replace(kw, "")
            
            # ✨ 마스터 지침 (결제 유도 클로징 강력 강조!!!)
            master_instruction = f"""당신은 다낭 위드어스 매니저 '위블리'입니다. 
아래 [🚨 상황별 답변 지침]을 우선적으로 파악하여 똑똑하게 대답하세요.

[🚨 맺음말(클로징) 절대 규칙 - 구매 전환 유도]
설명이 모두 끝난 후, 맨 마지막에는 고객이 결제를 결심할 수 있도록 절대 대충 마무리하지 말고, **무조건 아래 문구를 돋보이는 양식(인용구, 강조, 이모지) 그대로 복사해서 출력**하세요.

> 🌟 **예약을 확정하시려면 지금 바로 아래 버튼을 통해 말씀해 주세요!**
> **위블리가 빠르게 예약 진행 도와드릴게요!** ✨
>
> 👇 **아래 [실시간 예약 상담하기] 버튼을 꾹! 눌러주세요!** 👇

링크: https://open.kakao.com/o/sxJ8neWg

[🚨 상황별 답변 지침]
👉 상황 A: 고객이 처음 '인원/날짜'를 말하거나, '숙소/차량' 견적을 문의할 때
1. 맞춤형 인사 2. 풀빌라/차량 추천 3. 가견적 템플릿 제공 4. 위 [클로징 절대 규칙] 출력

👉 상황 B: 마사지, 이발소, 골프 등 특정 서비스 단독 문의 시
해당 업체 상세 설명. 가견적서 출력 금지. 마지막에 위 [클로징 절대 규칙] 출력

[🚨 링크 버튼 생성 절대 규칙]
- 시스템이 버튼을 생성할 수 있도록 링크 앞에는 반드시 "사진 보기: ", "영상 보기: " 라는 정확한 단어만 쓰세요!

[🚨 견적서 및 추천 절대 규칙]
1. [풀빌라 강조] 추천하는 숙소명은 반드시 **[숙소명]** 처럼 별표 두 개로 감싸서 강조(노란색 표기)하세요. 
2. [골프 상세화] "골프(2회)" 처럼 뭉뚱그리지 말고 DB를 확인하여 정확한 골프장 이름과 코스 명칭을 상세히 적으세요.
3. [금지 사항] 견적서 내 '기타' 란이나 본문에 '가라오케', '에코걸', '유흥' 관련 내용은 절대 단 1글자도 적지 마세요. 

[🚨 절대 준수 지침]
1. 달러 기호($) 금지, 한글 '달러' 표기.
2. 1인 1실 원칙 우선 추천 숙소: (2룸:미니더블, 3룸:블랙미러, 4룸:블루에덴1 또는 버블캐슬5, 5룸:피크닉 또는 셀레네, 6룸:피크닉2, 8룸:네온드림)
3. 차량(솔라티) 기본 단가 80달러 계산.

[가견적 템플릿 (상황 A에서만 사용!)]
---
🧾 **다낭 위드어스 가견적서**
---

**🗓️ 일정:** [일정]
**👥 인원:** [인원수]명

> **🏡 숙소 견적**
> - 내용: **[숙소명]** ([박수]박)
> - 금액: [달러단가]달러 x [박수]박 (약 [원화금액]원)
>
> **🚐 차량 견적** (※ 고객 요청 시 제외 처리)
> - 내용: 14인승 솔라티 ([일수]일)
> - 금액: 기본 80달러 x [일수]일 (약 [원화금액]원)
> - 💡 *안내: 차량 요금은 동선 및 이용 시간에 따라 80달러 ~ 120달러 사이로 유동적으로 적용됩니다.*
> - 💖 *위블리의 안내: 완벽하고 편안한 여행을 위해 위블리가 쏙! 추가해둔 옵션이에용! 언제든 편하게 빼실 수 있으니 부담 갖지 마세용~🥰*
>
> **💆‍♂️ 추가 서비스 견적** (※ 고객이 마사지, 이발소, 골프 등을 함께 요청한 경우에만 작성)
> - 내용 1: [DB에 있는 정확한 골프장명/마사지업체명 및 코스명] ([인원수]명)
> - 금액: [단가] x [인원수]명 (약 [원화금액]원)
> (※ 골프장 견적이 포함된 경우 아래 안내문구 반드시 추가)
> - 💡 *안내: 골프 요금은 시즌 및 요일(평일/주말 등)에 따라 조금씩 변동될 수 있습니다.*

---
💰 **예상 총합: 약 [총합원화]원** (숙소+차량+추가서비스 합산)
---
*(💸 환율 1달러=1,500원 기준)*

[실시간 DB]
{db}
[대화 히스토리]
{clean_history}"""

            try:
                model = genai.GenerativeModel('gemini-3-flash-preview')
                response = model.generate_content(f"{master_instruction}\n고객님: {safe_ai_prompt}")
                
                full_res = response.text
                
                if has_vip:
                    full_res += vip_template
                    
                placeholder.empty() 
                
                with placeholder.container():
                    render_assistant_content(full_res)
                    
            except Exception as e: 
                full_res = f"앗! 시스템 연결에 오류가 발생했습니다. (에러내용: {e})"
                placeholder.markdown(full_res)
        
        run_background_tasks(st.session_state.user_id, prompt, full_res)
        
    st.session_state.messages.append({"role": "assistant", "content": full_res})
    
    # 여기서 st.rerun()이 돌면 위쪽에 배치된 auto_scroll_to_bottom()이 실행되며 화면을 완벽하게 내립니다!
    st.rerun()

# ==========================================
# 🌟 사이드바
# ==========================================
with st.sidebar:
    t_style = "color: #ffffff; font-weight: 900; text-align: center; text-shadow: -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000, -2px -2px 0 #000, 2px -2px 0 #000, -2px 2px 0 #000, 2px 2px 0 #000, 3px 3px 5px rgba(0,0,0,0.8);"
    
    st.markdown(f"""<h3 style="{t_style}">👇 담당자 호출 버튼 👇</h3>""", unsafe_allow_html=True)
    st.link_button("💖 실시간 예약 상담하기 💖", "https://open.kakao.com/o/sxJ8neWg", use_container_width=True)
    st.divider()

    st.markdown(f"""<h3 style="{t_style}">🚀 위블리 빠른 추천 🚀</h3>""", unsafe_allow_html=True)
    
    if st.button('" 맛집 " 추천', use_container_width=True):
        prompt = "다낭 맛집 추천해 줘"
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        food_res = """고객님, 다낭에 오셨으면 맛집 투어는 필수죠! 🤤 
위드어스가 자신 있게 추천하는 찐 맛집 리스트입니다.

---
🍲 **다낭 위드어스 찐 맛집 리스트**
---

> **1. Long Beach Seafood (해산물)**
> - 특징: 주문과 동시에 요리 시작! 신선한 재료, 맛, 합리적 가격까지 만족!
> 위치 보기: https://maps.app.goo.gl/gdAXR1YPhq4a2nmk7

> **2. 4U Seafood (해산물)**
> - 특징: 미케비치 바로 앞 오션뷰! 직원이 친절하고 깔끔. (오션뷰라 가격은 다소 있음)
> 위치 보기: https://maps.app.goo.gl/nnEVzeRm8FKxdHaV9

> **3. FOR YOU Steak House (스테이크)**
> - 특징: 고기 신선도 최고, 매장도 깔끔! 오션뷰 프리미엄이 있지만 맛은 보장합니다.
> 위치 보기: https://maps.app.goo.gl/8xfefEGvk1rSNWz36

> **4. 템하이산 (현지/해산물)**
> - 특징: 가족 단위 한국 손님 픽 1위! 음식 맛있고 가격도 적당. 주말 저녁은 혼잡 주의!
> 위치 보기: https://maps.app.goo.gl/vAfGNWuVCGVgRmEu9?g_st=ipc

> **5. Van may 식당 (로컬)**
> - 특징: 안트엉 지역 찐 로컬 식당. 한식 대비 절반 수준 가격에 청결함까지 완벽!
> 위치 보기: https://maps.app.goo.gl/GpGDfq8U4vhwoXdg7?g_st=ipc

> **6. 다빈 식당 (중식)**
> - 특징: 일명 한국보다 더 맛있는 중국집! 가격은 한국과 비슷, 간짜장과 탕수육 강추!
> 위치 보기: https://maps.app.goo.gl/CbegPCx3irjzXFsE6?g_st=ipc

> **7. Mad Platter (양식/씨푸드)**
> - 특징: 끝내주는 오션뷰! 음식 맛도 훌륭한 편. 가격대는 조금 높은 편입니다.
> 위치 보기: https://maps.app.goo.gl/m3zEaZeAjeTSbSVQ9?g_st=ipc

> **8. GU EM BBQ RESTAURANT (고기집)**
> - 특징: 팜반동 한인타운 신상 고기집! 대로변에 있어 찾기 편하고 맛과 가격 모두 훌륭.
> 위치 보기: https://maps.app.goo.gl/Yrumio8dmkSrjxJy9?g_st=ipc

> **9. 무쇠고기살롱 (고기집)**
> - 특징: 무쇠판에 직접 구워주는 팜반동 맛집. 위치 좋고 맛있어서 재방문율 100%!
> 위치 보기: https://maps.app.goo.gl/r7JZpB3aUoNCx8h67

> **10. 논라 (베트남 가정식)**
> - 특징: 깔끔하고 맛있는 가성비 로컬 식당! 식사 후 해변 산책하기 딱 좋은 위치.
> 위치 보기: https://maps.app.goo.gl/n2xL214kv66R3Cvs5

> **11. 쭈꾸뽕 (한식)**
> - 특징: 다낭에서 맛보는 매콤한 쭈꾸미! 다양한 한식 메뉴 구비. 단골 손님이 많은 곳!
> 위치 보기: https://maps.app.goo.gl/kXLGHHA7YgwDRTDz7

> **12. Gordon's New York Pizza Cityside (피자)**
> - 특징: 한강 뷰를 보며 즐기는 피자 찐 맛집! (스파게티보단 피자 강추) 근처 맥주 거리와 연계하기 좋습니다.
> 위치 보기: https://maps.app.goo.gl/sjQ8Ligwj95khgzs5"""
        
        st.session_state.messages.append({"role": "assistant", "content": food_res})
        run_background_tasks(st.session_state.user_id, prompt, food_res)
        st.rerun()

    if st.button('" 관광지 " 추천', use_container_width=True):
        prompt = "다낭 관광지 추천해 줘"
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        tour_res = """고객님, 다낭의 핵심 관광지들을 안내해 드립니다! 📸
인생샷 남기기 좋은 곳들로만 쏙쏙 뽑아봤어요.

---
🏞️ **다낭 위드어스 추천 관광지**
---

> **1. 바나힐 (Ba Na Hills)**
> - 특징: 세계에서 가장 긴 케이블카와 골든브릿지(거대한 손)가 있는 다낭의 랜드마크!
> 위치 보기: https://maps.app.goo.gl/9cyKvXuwaqXWQP9V8
>
> **2. 호이안 올드타운 (Hoi An)**
> - 특징: 다낭에서 차로 40분 거리. 밤이 되면 수천 개의 등불이 켜지는 로맨틱한 야경 맛집!
> 위치 보기: https://maps.app.goo.gl/ysgHAp7ZtnrgKvo79
>
> **3. 오행산 (Marble Mountains)**
> - 특징: 5개의 대리석 산으로 이루어진 다낭의 대표 명소! 동굴 탐험과 탁 트인 전망대에서 다낭 시내를 한눈에 내려다볼 수 있습니다. (엘리베이터 탑승을 강력 추천드려요!)
> 위치 보기: https://maps.app.goo.gl/9FArYjJ8ANYbNvZLA
>
> **4. 누이탄타이 핫스프링 파크 (온천/워터파크)**
> - 특징: 다낭에서 즐기는 이색 온천 여행! 워터파크와 온천을 동시에 즐길 수 있으며, 특히 피부가 뽀송뽀송해지는 **프라이빗 머드탕은 만족도 200% 강력 추천**합니다!
> 위치 보기: https://maps.app.goo.gl/TRFgxPQQSXf7ekNh9"""
        
        st.session_state.messages.append({"role": "assistant", "content": tour_res})
        run_background_tasks(st.session_state.user_id, prompt, tour_res)
        st.rerun()

    if st.button('" 카페 " 추천', use_container_width=True):
        prompt = "다낭 분위기 좋은 카페 추천해 줘"
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        cafe_res = """고객님, 여행 중 달콤한 휴식을 위한 다낭 예쁜 카페를 소개합니다! ☕

---
☕ **다낭 위드어스 찐 로컬 카페 리스트**
---

> **1. 콩카페 다낭 (Cong Caphe)**
> - 특징: 너무 유명해 설명이 필요 없는 다낭 로컬 카페의 스타벅스! 빈티지한 인테리어와 근본적으로 맛있는 커피 강추!
> 위치 보기: https://maps.app.goo.gl/w4u7PWDRSqWHJBvr6

> **2. Cửa Ngõ Café – Cửa Hàng Số 2**
> - 특징: 분위기 깡패! 테이블 앞 조그만 연못에 비단잉어들이 실시간으로 움직입니다. 잉어 먹이 주기 체험도 가능해 아이들과 가기 좋아요.
> 위치 보기: https://maps.app.goo.gl/tLGUw7gacy1cRiVM7

> **3. Gé Cafe**
> - 특징: 이색적인 인테리어의 로컬 카페! 쉼을 느끼고 싶은 분들께 추천. 한시장 근처라 쇼핑 후 북적거림을 피해 오기 딱 좋습니다.
> 위치 보기: https://maps.app.goo.gl/4HPkAM257qRzWSd3A

> **4. Tou Zone food & Drink Đà Nẵng**
> - 특징: 한강 뷰를 따라 걷다 보면 나오는 끝자락 로컬 카페! 외국인이 적어 찐 로컬 감성을 느낄 수 있고 가격도 아주 저렴합니다.
> 위치 보기: https://maps.app.goo.gl/8ztEfa1sw4PxS1tw9

> **5. Wind Garden Coffee**
> - 특징: 팜반동 한인타운에서 가까운 분위기 깡패 카페! 커피도 맛있고, 이곳 역시 잉어 먹이 주기 체험이 가능해 색다른 즐거움이 있습니다.
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