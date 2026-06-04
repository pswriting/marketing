# -*- coding: utf-8 -*-
"""
MarketKit v3 — 전자책 → 전 채널 마케팅 통합기
CashMaker 브랜드 / Writey 자매 제품

v3 변경점
  · 안정성: API 키 형식 검증 + 지수 백오프 재시도 + 오류 유형별 친절한 메시지
  · 품질  : 프롬프트 정교화, 카드뉴스 이미지 '병렬' 생성(빠르고 일관성↑), 전체 ZIP 저장
  · UI    : 과감한 미니멀 — 군더더기 제거, 한 화면 한 동작
  · 디자인: 다크 + 골드 전문가급 디자인 시스템

이미지: Google Gemini Nano Banana Pro (gemini-3-pro-image-preview)
텍스트: Claude Sonnet 4.5
"""
import os
import time
import logging
import json
import html
import io
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed

os.environ['PYTHONIOENCODING'] = 'utf-8'
logging.getLogger('anthropic').setLevel(logging.ERROR)
logging.getLogger('httpx').setLevel(logging.ERROR)

import streamlit as st

try:
    import anthropic
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False

try:
    from google import genai as google_genai
    from google.genai import types as genai_types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

try:
    from pypdf import PdfReader
    PDF_AVAILABLE = True
except ImportError:
    try:
        from PyPDF2 import PdfReader
        PDF_AVAILABLE = True
    except ImportError:
        PDF_AVAILABLE = False

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

# ==========================================
# 설정
# ==========================================
CORRECT_PASSWORD = "cashmaker2024"
CLAUDE_MODEL = "claude-sonnet-4-5"
IMAGE_MODEL = "gemini-3-pro-image-preview"   # Nano Banana Pro
MAX_RETRIES = 3
IMG_WORKERS = 4   # 카드뉴스 병렬 생성 워커 수

st.set_page_config(page_title="MarketKit", layout="wide", page_icon="📣")

# ==========================================
# STYLE — 다크 + 골드 전문가급 디자인 시스템
# ==========================================
st.markdown("""
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
:root {
    --gold:#C9A24B; --gold-light:#E6CC84; --teal:#4BB7A8; --teal-deep:#2E8276;
    --bg:#0A0A0C; --bg2:#0E0E11;
    --card:rgba(255,255,255,.025); --card2:rgba(255,255,255,.05);
    --text:#F6F4F0; --text2:#8B8884; --text3:#5E5C58;
    --line:rgba(201,162,75,.16); --line2:rgba(255,255,255,.06);
    --radius:14px;
}
* { font-family:'Pretendard',-apple-system,BlinkMacSystemFont,sans-serif !important; }
html, body { -webkit-font-smoothing:antialiased; }
.stApp {
    background:
        radial-gradient(900px 500px at 12% -5%, rgba(75,183,168,.05) 0%, transparent 55%),
        radial-gradient(900px 600px at 92% 105%, rgba(201,162,75,.045) 0%, transparent 55%),
        linear-gradient(180deg,#0A0A0C 0%,#08080A 50%,#0A0A0C 100%) !important;
    background-attachment:fixed;
}
.main .block-container { max-width:920px; padding:2rem 2rem 4rem; }
.stDeployButton, footer, #MainMenu { display:none !important; }
header[data-testid="stHeader"] { background:transparent !important; }

/* 타이포 스케일 */
h1,h2,h3,h4 { color:var(--text) !important; letter-spacing:-.2px; }
h1 { font-size:30px !important; font-weight:800 !important; }
h2 { font-size:21px !important; font-weight:700 !important; }
h3 { font-size:15px !important; color:var(--text2) !important; font-weight:600 !important;
     text-transform:uppercase; letter-spacing:1.5px !important; margin-top:.5rem !important; }
h4 { font-size:16px !important; font-weight:700 !important; }
p,span,label,div,li { color:var(--text); font-size:15.5px; line-height:1.7; }
.stCaption, [data-testid="stCaptionContainer"] { color:var(--text2) !important; }
hr { border-color:var(--line2) !important; margin:1.6rem 0 !important; }

/* 버튼 — primary는 골드, 보조는 외곽선 */
.stButton > button {
    background:linear-gradient(135deg,var(--gold-light),var(--gold)) !important;
    color:#0A0A0C !important; -webkit-text-fill-color:#0A0A0C !important;
    border:none !important; border-radius:12px; font-weight:700; font-size:15px !important;
    padding:12px 26px; transition:transform .18s ease, box-shadow .18s ease;
    box-shadow:0 4px 16px rgba(201,162,75,.18);
}
.stButton > button * { color:#0A0A0C !important; -webkit-text-fill-color:#0A0A0C !important; }
.stButton > button:hover { box-shadow:0 8px 26px rgba(201,162,75,.34); transform:translateY(-1px); }
.stButton > button:active { transform:translateY(0); }
.stDownloadButton > button {
    background:transparent !important; color:var(--gold) !important; -webkit-text-fill-color:var(--gold) !important;
    border:1px solid var(--line) !important; border-radius:11px; font-weight:600; box-shadow:none !important;
}
.stDownloadButton > button:hover { border-color:var(--gold) !important; background:rgba(201,162,75,.06) !important; }

/* 입력 — 흰 배경 + 검은 글씨 */
.stTextInput input, .stTextArea textarea {
    background:#fff !important; border:1px solid var(--line) !important; border-radius:11px !important;
    color:#111 !important; -webkit-text-fill-color:#111 !important; padding:14px !important; font-size:15.5px !important;
}
.stTextInput input::placeholder, .stTextArea textarea::placeholder {
    color:#9a9a9a !important; -webkit-text-fill-color:#9a9a9a !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color:var(--teal) !important; box-shadow:0 0 0 3px rgba(75,183,168,.16) !important;
}
.stSelectbox div[data-baseweb="select"] > div, .stMultiSelect div[data-baseweb="select"] > div {
    background:#fff !important; border:1px solid var(--line) !important; border-radius:11px !important;
}
.stSelectbox div[data-baseweb="select"] span, .stSelectbox div[data-baseweb="select"] div {
    color:#111 !important; -webkit-text-fill-color:#111 !important;
}
div[data-baseweb="popover"] li, ul[role="listbox"] li {
    color:#111 !important; -webkit-text-fill-color:#111 !important; background:#fff !important;
}
.stMultiSelect span[data-baseweb="tag"] { background:var(--gold) !important; }
.stMultiSelect span[data-baseweb="tag"] span { color:#0A0A0C !important; -webkit-text-fill-color:#0A0A0C !important; }
.stMultiSelect div[data-baseweb="select"] input { color:#111 !important; -webkit-text-fill-color:#111 !important; }
.stSlider [data-baseweb="slider"] div[role="slider"] { background:var(--gold) !important; }

/* 탭 — 미니멀 */
.stTabs [data-baseweb="tab-list"] { gap:2px; border-bottom:1px solid var(--line2); flex-wrap:wrap; }
.stTabs [data-baseweb="tab"] {
    background:transparent; color:var(--text2) !important; border-radius:10px 10px 0 0;
    padding:10px 16px; font-weight:600; font-size:14.5px;
}
.stTabs [aria-selected="true"] {
    color:var(--gold) !important; border-bottom:2px solid var(--gold);
}

/* 카드/박스 */
.result-box { background:var(--card) !important; border:1px solid var(--line2); border-left:2px solid var(--teal);
    border-radius:var(--radius); padding:20px 24px; margin:14px 0; }
.hero { padding:10px 0 22px; }
.hero .badge { display:inline-block; color:var(--teal); border:1px solid rgba(75,183,168,.4);
    border-radius:20px; padding:4px 14px; font-size:11px; letter-spacing:2.5px; margin-bottom:14px; }
.ctx-pill { display:inline-block; background:var(--card2); border:1px solid var(--line);
    border-radius:20px; padding:5px 14px; font-size:12.5px; color:var(--teal); margin-bottom:6px; }
.step-tag { display:inline-block; color:var(--gold); font-size:12px; font-weight:700;
    letter-spacing:2px; margin-bottom:2px; }
.footer { text-align:center; padding:26px 20px; margin-top:48px; border-top:1px solid var(--line2);
    color:var(--text2); font-size:13px; letter-spacing:1.5px; }

/* 로그인 */
.login-wrap { max-width:400px; margin:9vh auto 0; text-align:center; }
.login-card { background:var(--card2); border:1px solid var(--line); border-radius:20px;
    padding:46px 38px; box-shadow:0 24px 70px rgba(0,0,0,.5); }
.login-card h1 { font-size:28px !important; margin-bottom:6px; }
.login-card .sub { color:var(--text2); font-size:14.5px; margin-bottom:26px; }

/* 알림 톤 다운 */
.stAlert { border-radius:12px !important; }
[data-testid="stProgress"] > div > div { background:linear-gradient(90deg,var(--teal),var(--gold)) !important; }
</style>
""", unsafe_allow_html=True)


# ==========================================
# 안정성 레이어 — 키 검증 / 재시도 / 오류처리
# ==========================================
def validate_claude_key(key):
    if not key:
        return False, "Claude API 키를 입력해주세요."
    if not key.startswith("sk-ant-"):
        return False, "Claude 키 형식이 올바르지 않아요. (sk-ant- 로 시작해야 해요)"
    return True, ""


def validate_gemini_key(key):
    if not key:
        return False, "Google API 키를 입력해주세요."
    if not key.startswith("AIza"):
        return False, "Google 키 형식이 올바르지 않아요. (AIza 로 시작해야 해요)"
    return True, ""


def _friendly_error(e):
    """예외를 사용자가 알아볼 수 있는 메시지로."""
    s = str(e).lower()
    if "401" in s or "authentication" in s or "invalid x-api-key" in s or "api key" in s:
        return "API 키가 거부됐어요. 키가 정확한지, 결제가 활성화돼 있는지 확인해주세요."
    if "429" in s or "rate" in s or "overloaded" in s:
        return "요청이 몰려 잠시 거절됐어요. 30초쯤 뒤에 다시 시도해주세요."
    if "529" in s:
        return "서버가 잠시 과부하 상태예요. 잠시 후 다시 시도해주세요."
    if "timeout" in s or "timed out" in s:
        return "응답이 지연됐어요. 네트워크를 확인하고 다시 시도해주세요."
    if "connection" in s or "network" in s:
        return "네트워크 연결을 확인해주세요."
    return f"오류: {str(e)[:140]}"


def _should_retry(e):
    s = str(e).lower()
    return any(k in s for k in ["429", "529", "overloaded", "timeout", "timed out", "connection", "rate"])


def ask_ai(prompt, temperature=0.8, max_tokens=4000):
    """Claude 호출. 일시적 오류는 지수 백오프로 재시도."""
    api_key = st.session_state.get('api_key', '')
    ok, msg = validate_claude_key(api_key)
    if not ok:
        st.error(msg)
        return None
    if not CLAUDE_AVAILABLE:
        st.error("anthropic 패키지가 없습니다. requirements.txt를 확인해주세요.")
        return None

    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            client = anthropic.Anthropic(api_key=api_key)
            resp = client.messages.create(
                model=CLAUDE_MODEL, max_tokens=max_tokens, temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.content[0].text.strip()
        except Exception as e:
            last_err = e
            if _should_retry(e) and attempt < MAX_RETRIES - 1:
                time.sleep(1.5 * (2 ** attempt))
                continue
            break
    st.error(f"생성 실패 — {_friendly_error(last_err)}")
    return None


def _gen_image_core(gkey, prompt, aspect_ratio, image_size):
    """순수 이미지 생성(세션 미접근, 스레드 안전). (bytes, None) 또는 (None, err)."""
    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            client = google_genai.Client(api_key=gkey)
            try:
                cfg = genai_types.GenerateContentConfig(
                    response_modalities=["Image"],
                    image_config=genai_types.ImageConfig(
                        aspect_ratio=aspect_ratio, image_size=image_size),
                )
                resp = client.models.generate_content(model=IMAGE_MODEL, contents=prompt, config=cfg)
            except Exception:
                # 구형 SDK 폴백 (image_config 미지원)
                resp = client.models.generate_content(model=IMAGE_MODEL, contents=prompt)
            for part in resp.candidates[0].content.parts:
                if getattr(part, 'inline_data', None) and part.inline_data.data:
                    return part.inline_data.data, None
            return None, "이미지가 반환되지 않았어요. 프롬프트를 바꿔 다시 시도해주세요."
        except Exception as e:
            last_err = e
            if _should_retry(e) and attempt < MAX_RETRIES - 1:
                time.sleep(1.5 * (2 ** attempt))
                continue
            break
    return None, _friendly_error(last_err)


def generate_image(prompt, aspect_ratio="1:1", image_size="2K"):
    """메인 스레드용 래퍼 — 세션에서 키를 읽어 검증 후 생성."""
    gkey = st.session_state.get('gemini_key', '')
    ok, msg = validate_gemini_key(gkey)
    if not ok:
        return None, msg
    if not GENAI_AVAILABLE:
        return None, "google-genai 패키지가 없습니다. requirements.txt를 확인해주세요."
    return _gen_image_core(gkey, prompt, aspect_ratio, image_size)


# ==========================================
# 유틸
# ==========================================
def parse_json(text):
    if not text:
        return None
    try:
        c = text.replace('```json', '').replace('```', '').strip()
        s, sa = c.find('{'), c.find('[')
        if sa != -1 and (s == -1 or sa < s):
            s, e = sa, c.rfind(']') + 1
        else:
            e = c.rfind('}') + 1
        if s != -1 and e > s:
            return json.loads(c[s:e])
    except Exception:
        pass
    return None


def extract_ebook_text(uploaded_file):
    name = uploaded_file.name.lower()
    try:
        if name.endswith('.pdf'):
            if not PDF_AVAILABLE:
                return None, "PDF 처리 패키지(pypdf)가 없습니다."
            reader = PdfReader(io.BytesIO(uploaded_file.read()))
            return "\n".join((p.extract_text() or "") for p in reader.pages).strip(), None
        elif name.endswith('.docx'):
            if not DOCX_AVAILABLE:
                return None, "DOCX 처리 패키지(python-docx)가 없습니다."
            doc = Document(io.BytesIO(uploaded_file.read()))
            return "\n".join(p.text for p in doc.paragraphs).strip(), None
        elif name.endswith('.txt') or name.endswith('.md'):
            return uploaded_file.read().decode('utf-8', errors='ignore').strip(), None
        return None, "지원 형식: PDF, DOCX, TXT, MD"
    except Exception as e:
        return None, f"파일 읽기 오류: {str(e)[:100]}"


def copy_block(text, key, height=380):
    st.text_area("결과", value=text, height=height, key=key, label_visibility="collapsed")
    st.caption("Ctrl+A → Ctrl+C 로 복사해서 사용하세요.")


def zip_images(pairs, prefix="card"):
    """[(title, bytes)] → zip bytes"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, (_, data) in enumerate(pairs, 1):
            zf.writestr(f"{prefix}_{i}.png", data)
    return buf.getvalue()


def ctx_summary():
    return st.session_state.get('ebook_analysis', {})


def _ctx_block():
    a = ctx_summary()
    if not a:
        return ""
    return f"""
[분석된 전자책 — 이 책 판매를 돕는 콘텐츠를 만들어라]
제목: {a.get('title','')}
핵심 메시지: {a.get('core_message','')}
타겟 독자: {a.get('target','')}
차별점: {a.get('unique_value','')}
핵심 주제: {', '.join(a.get('key_topics', []))}
독자의 고통: {', '.join(a.get('pain_points', []))}
"""


def section(step, title):
    """미니멀 섹션 헤더."""
    st.markdown(f'<div class="step-tag">{step}</div>', unsafe_allow_html=True)
    st.markdown(f"#### {title}")


# ==========================================
# 몰입형 글쓰기 가이드
# ==========================================
STYLE_CORE = """
[★ 절대 원칙 — 설명문이 아니라 '몰입형 글'을 써라]
지금까지 가장 큰 실패는 '정보를 나열하는 설명문'이었다. 독자는 정보를 원하지 않는다. '내 얘기'에 빨려들기를 원한다.
아래를 지키지 않으면 글은 죽는다.

1. 첫 문장은 장면이거나 단언이다. 절대 '~에 대해 알아보겠습니다' 류로 시작하지 마라.
   ✗ "오늘은 직장인 부업에 대해 알아보겠습니다"
   ✓ "퇴근하고 책상에 앉으면, 이미 밤 10시다. 그리고 또 아무것도 못 했다."
   ✓ "부업으로 돈 못 버는 사람은 게을러서가 아니다. 정반대다."

2. '너 지금 이러고 있지?' — 독자의 현재 행동·생각을 정확히 묘사해 들키게 하라. 2~3문장마다 독자가 뜨끔하게.

3. 통념을 부순다. "다들 A라고 하죠? 틀렸습니다. 진짜는 B입니다." 이 리듬을 반복하라.

4. 짧게 끊어라. 한 문장이 길면 자른다. 한 문단은 1~3줄. 가끔 한 줄짜리 문단으로 쳐라. (강조)

5. 구어체 단언. "~합니다"체 위주에 가끔 반말 단언("이게 핵심이다.")을 섞어 리듬을 만든다.

6. 근거는 장면·숫자·경험으로. 추상적 설명 대신 "내가 7년차에 280만원 받을 때" 같은 구체적 장면.

7. 문단마다 다음을 안 읽으면 못 배기게 끝낸다. "그런데 여기서 모두가 실수한다." 같은 갈고리.

[2026 네이버 알고리즘 — 위 몰입감을 해치지 않는 선에서]
- 전문성(C-Rank): 구체적 수치·단계·근거. 단, 논문체로 쓰지 말고 위 몰입형 톤 안에 녹여라.
- 완결성(D.I.A+): 검색의도를 글 안에서 끝까지 해소. 읽고 나면 더 검색할 필요 없게.
- 진정성: AI 광고글 티 금지. 실제 경험·솔직한 한계·구체적 장면.

[어법]
- 한국어 원어민이 한 번에 이해되는 문장만. AI 클리셰 금지("~의 모든 것","결정적","게임체인저").
- 추상 명사에 물리 동사 금지. 억지 비유 금지.
"""


# ==========================================
# 로그인
# ==========================================
def render_login():
    st.markdown('<div class="login-wrap">', unsafe_allow_html=True)
    st.markdown("""
    <div class="login-card">
        <div style="color:#4BB7A8;font-size:12px;letter-spacing:3px;margin-bottom:10px;">CASHMAKER</div>
        <h1>📣 MarketKit</h1>
        <p class="sub">전자책 하나로 블로그·SNS·크몽까지 한 번에</p>
    </div>
    """, unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        pw = st.text_input("비밀번호", type="password", key="pw_input",
                           placeholder="비밀번호 입력", label_visibility="collapsed")
        if st.button("입장하기", key="login_btn", use_container_width=True):
            if pw == CORRECT_PASSWORD:
                st.session_state['authenticated'] = True
                st.rerun()
            else:
                st.error("비밀번호가 올바르지 않습니다.")
    st.markdown('</div>', unsafe_allow_html=True)


# ==========================================
# 사이드바
# ==========================================
def render_sidebar():
    with st.sidebar:
        st.markdown("### API")

        st.markdown('<div style="font-size:13px;color:#C9A24B;margin-bottom:4px;">Claude 키 · 글 생성</div>', unsafe_allow_html=True)
        api_key = st.text_input("Claude API 키", type="password", label_visibility="collapsed",
                                value=st.session_state.get('api_key', ''), key="api_input",
                                placeholder="sk-ant-...")
        if api_key:
            st.session_state['api_key'] = api_key
            ok, msg = validate_claude_key(api_key)
            if ok:
                st.markdown('<div style="font-size:12px;color:#4BB7A8;margin-bottom:12px;">✓ 형식 확인됨</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div style="font-size:12px;color:#E0894B;margin-bottom:12px;">{html.escape(msg)}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="font-size:12px;color:#888;margin-bottom:12px;">console.anthropic.com 에서 발급</div>', unsafe_allow_html=True)

        st.markdown('<div style="font-size:13px;color:#C9A24B;margin-bottom:4px;">Google 키 · 이미지 (선택)</div>', unsafe_allow_html=True)
        gkey = st.text_input("Google API 키", type="password", label_visibility="collapsed",
                             value=st.session_state.get('gemini_key', ''), key="gkey_input",
                             placeholder="AIza...")
        if gkey:
            st.session_state['gemini_key'] = gkey
            ok, msg = validate_gemini_key(gkey)
            if ok:
                st.markdown('<div style="font-size:12px;color:#4BB7A8;margin-bottom:8px;">✓ 형식 확인됨</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div style="font-size:12px;color:#E0894B;margin-bottom:8px;">{html.escape(msg)}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="font-size:12px;color:#888;margin-bottom:8px;">aistudio.google.com · 카드뉴스/상세페이지용</div>', unsafe_allow_html=True)

        st.markdown("---")
        a = ctx_summary()
        if a:
            st.markdown('<div style="font-size:13px;color:#8B8884;margin-bottom:4px;">분석된 전자책</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="color:#4BB7A8;font-size:14px;margin-bottom:10px;">{html.escape(a.get("title",""))}</div>', unsafe_allow_html=True)
            if st.button("전자책 비우기", key="clear_ebook", use_container_width=True):
                for k in ['ebook_analysis', 'ebook_text', 'blog_topics', 'blog_result',
                          'sns_result', 'kmong_result', 'detail_text', 'detail_img', 'card_imgs']:
                    st.session_state.pop(k, None)
                st.rerun()
        else:
            st.markdown('<div style="font-size:13px;color:#8B8884;">① 탭에서 전자책을 올려주세요.</div>', unsafe_allow_html=True)


# ==========================================
# 탭 0 — 전자책 분석
# ==========================================
def tab_ebook():
    section("STEP 01", "전자책 분석")
    st.caption("파일을 올리면 내용을 분석해, 이후 모든 콘텐츠가 이 책에 맞춰 생성됩니다.")

    up = st.file_uploader("PDF / DOCX / TXT / MD", type=['pdf', 'docx', 'txt', 'md'], key="ebook_up")
    if up is not None and st.button("이 전자책 분석하기", key="ebook_btn", use_container_width=True):
        with st.spinner("내용 추출 중..."):
            text, err = extract_ebook_text(up)
        if err:
            st.error(err)
        elif not text or len(text) < 50:
            st.warning("텍스트를 충분히 추출하지 못했어요. (스캔 PDF는 인식이 안 될 수 있어요)")
        else:
            st.session_state['ebook_text'] = text[:20000]
            with st.spinner("Claude가 전자책을 분석하는 중..."):
                prompt = f"""아래는 전자책 본문이다. 이 책을 마케팅하기 위해 핵심을 분석해라.
[전자책 본문 (일부)]
{text[:15000]}

JSON만 출력:
{{
  "title":"이 책의 핵심을 담은 제목(추정)",
  "target":"이 책이 가장 도움 될 독자 한 문장",
  "core_message":"핵심 메시지 한 문장",
  "key_topics":["핵심 주제 5개"],
  "pain_points":["타겟 독자가 지금 겪는 고통 3개"],
  "unique_value":"이 책만의 차별점 한 문장"
}}"""
                data = parse_json(ask_ai(prompt, 0.5, 2000))
                if data:
                    st.session_state['ebook_analysis'] = data
                    st.success("분석 완료! 이제 다른 탭에서 이 책에 맞춘 콘텐츠를 만들 수 있어요.")
                else:
                    st.error("분석에 실패했어요. 다시 시도해주세요.")

    a = ctx_summary()
    if a:
        st.markdown("---")
        st.markdown(f"#### 📖 {html.escape(a.get('title',''))}")
        st.markdown(f"""<div class="result-box">
        <p><b style="color:var(--teal);">핵심 메시지</b><br>{html.escape(a.get('core_message',''))}</p>
        <p><b style="color:var(--teal);">타겟 독자</b><br>{html.escape(a.get('target',''))}</p>
        <p><b style="color:var(--teal);">차별점</b><br>{html.escape(a.get('unique_value',''))}</p></div>""",
                    unsafe_allow_html=True)
        cols = st.columns(2)
        with cols[0]:
            st.markdown("**핵심 주제**")
            for t in a.get('key_topics', []):
                st.markdown(f"- {html.escape(t)}")
        with cols[1]:
            st.markdown("**독자의 고통**")
            for p in a.get('pain_points', []):
                st.markdown(f"- {html.escape(p)}")


# ==========================================
# 탭 1 — 블로그
# ==========================================
def tab_blog():
    section("STEP 02", "블로그")
    a = ctx_summary()
    if a:
        st.markdown(f'<span class="ctx-pill">📚 {html.escape(a.get("title",""))} 기반</span>', unsafe_allow_html=True)
    else:
        st.caption("전자책을 먼저 분석하면 책에 맞춘 주제가 추천돼요. (없어도 직접 입력 가능)")

    if st.button("블로그 주제 10개 추천받기", key="topic_btn", use_container_width=True):
        with st.spinner("판매로 이어질 주제 뽑는 중..."):
            prompt = f"""너는 네이버 블로그로 전자책을 파는 콘텐츠 전략가다.
{_ctx_block()}
이 전자책 판매로 이어질 블로그 글 주제 10개를 추천해라.
- 검색량 있으면서 경쟁 덜한 롱테일. 그대로 제목으로 써도 될 만큼 구체적이고 후킹 있게.
- 정보형(구매 전)~구매형(전환)이 골고루.
JSON만 출력:
{{"topics":[{{"title":"주제(제목형)","intent":"정보형/비교형/구매형","why":"판매에 좋은 이유 한 줄"}}]}}"""
            data = parse_json(ask_ai(prompt, 0.8, 2500))
            if data and data.get('topics'):
                st.session_state['blog_topics'] = data['topics']
            else:
                st.error("주제 추천에 실패했어요. 다시 시도해주세요.")

    topics = st.session_state.get('blog_topics', [])
    if topics:
        st.caption("주제를 클릭하면 아래 본문 칸에 자동 입력돼요.")
        for i, t in enumerate(topics):
            label = f"[{t.get('intent','')}] {t.get('title','')}"
            if st.button(label, key=f"pick_topic_{i}", use_container_width=True):
                st.session_state['blog_topic'] = t.get('title', '')
                st.rerun()
            st.markdown(f'<div style="font-size:13px;color:#8B8884;margin:-6px 0 10px 4px;">└ {html.escape(t.get("why",""))}</div>', unsafe_allow_html=True)

    st.markdown("---")
    topic = st.text_input("글 주제", key="blog_topic", placeholder="위에서 클릭하거나 직접 입력")
    length = st.selectbox("글 길이", ["표준 (1500자)", "롱폼 (2500자)", "숏폼 (800자)"], key="blog_len")

    if st.button("블로그 본문 생성", key="blog_btn", use_container_width=True):
        if not topic.strip():
            st.warning("주제를 입력하거나 위에서 클릭해주세요.")
        else:
            lmap = {"표준 (1500자)": "1500자 내외", "롱폼 (2500자)": "2500자 내외", "숏폼 (800자)": "800자 내외"}
            with st.spinner("몰입형 글 작성 중... (30초~1분)"):
                prompt = f"""너는 독자가 스크롤을 멈추고 끝까지 빨려드는 글을 쓰는 블로그 작가다.
[주제]: {topic}
[목표 길이]: {lmap[length]}
{_ctx_block()}
{STYLE_CORE}
[구조 — 단 설명문처럼 쓰지 말고 위 몰입형 원칙으로]
1. 후킹 도입: 장면 또는 단언으로 시작. 독자가 "내 얘기다" 하게.
2. 통념 부수기: "다들 A라죠? 틀렸다." 리듬으로 독자의 착각을 깬다.
3. 진짜 이유: 근거를 장면·숫자·경험으로. 추상 설명 금지.
4. 그래서 어떻게: 바로 적용할 한두 가지. 단 핵심 디테일은 전자책으로 남긴다.
5. 마무리+전환: 여운 있게 정리하고 전자책으로 자연스럽게.
[형식] 맨 위 추천 제목 3개(키워드 앞쪽). 한 문단 1~3줄, 가끔 한 줄 문단. 제목 3개 → 본문 순. 설명 없이 글만."""
                result = ask_ai(prompt, 0.9, 4000)
                if result:
                    st.session_state['blog_result'] = result

    if st.session_state.get('blog_result'):
        st.markdown("---")
        st.markdown("#### 📝 완성된 글")
        copy_block(st.session_state['blog_result'], key="blog_out")
        st.download_button("글 파일로 저장 (.txt)", data=st.session_state['blog_result'].encode('utf-8'),
                           file_name="blog.txt", mime="text/plain", use_container_width=True, key="blog_dl")
        st.info("'SNS 변환' 탭에서 이 글이 자동 반영돼요.")


# ==========================================
# 탭 2 — SNS 변환
# ==========================================
def tab_sns():
    section("STEP 03", "SNS 변환")
    blog = st.session_state.get('blog_result', '')
    if blog:
        st.markdown('<span class="ctx-pill">✅ 블로그 글 자동 반영됨</span>', unsafe_allow_html=True)
    else:
        st.caption("블로그 글을 먼저 만들면 자동 반영돼요. (전자책 분석만으로도 변환 가능)")

    st.markdown("**글 콘텐츠**")
    text_channels = st.multiselect("SNS 채널",
                                   ["스레드(Threads)", "X(트위터)", "유튜브 쇼츠 대본"],
                                   default=["스레드(Threads)"], key="sns_text_ch", label_visibility="collapsed")
    if st.button("글 콘텐츠 변환", key="sns_text_btn", use_container_width=True):
        base = blog if blog else _ctx_block()
        if not base.strip():
            st.warning("블로그 글을 먼저 만들거나 전자책을 분석해주세요.")
        elif not text_channels:
            st.warning("채널을 선택해주세요.")
        else:
            specs = {
                "스레드(Threads)": "스레드: 첫 줄 후킹, 짧은 문장 5~8개, 500자 이내, 끝에 자연스러운 행동 유도.",
                "X(트위터)": "X 스레드: 첫 트윗 후킹(280자), 이어 4~6개(각 280자), 1/n 번호.",
                "유튜브 쇼츠 대본": "쇼츠 대본: 첫 3초 후킹+본론 40초+행동유도, 말로 읽는 대본체, [자막] 표시 포함.",
            }
            sel = "\n".join(f"- {specs[c]}" for c in text_channels)
            with st.spinner("채널별 변환 중..."):
                prompt = f"""너는 SNS 콘텐츠 전문가다. 아래 글의 핵심을 살려 채널별로 변환해라.
[원본]
{base}
[채널 규칙]
{sel}
[공통] 채널마다 톤 다르게(복붙 금지), 첫 문장 무조건 후킹, 과장·낚시 금지, 해시태그 채널당 3~5개.
각 채널을 ===== 채널명 ===== 으로 구분. 설명 없이 결과만."""
                r = ask_ai(prompt, 0.85, 4000)
                if r:
                    st.session_state['sns_result'] = r
    if st.session_state.get('sns_result'):
        copy_block(st.session_state['sns_result'], key="sns_out")

    st.markdown("---")
    st.markdown("**인스타 카드뉴스**")
    st.caption("실제 인기 카드뉴스 템플릿(고정 여백·페이지 번호·핸들)으로 병렬 생성합니다. (Google API 키 필요)")

    card_style = st.selectbox(
        "디자인 스타일",
        ["모던 그리드 (화이트+형광 포인트, 정보형 인기템)",
         "다크 모노 (블랙+옐로우, 동기부여 강렬)",
         "감성 사진 오버레이 (무드 사진+흰 텍스트)",
         "파스텔 소프트 (크림+세리프, 독서·감성)",
         "트렌디 그라데이션 (보라·핑크, MZ)"],
        key="card_style"
    )
    c_a, c_b = st.columns(2)
    with c_a:
        n_cards = st.slider("카드 장수", 3, 8, 5, key="card_n")
    with c_b:
        brand_handle = st.text_input("브랜드 핸들 (하단 표시)", value="@cashmaker", key="card_handle")

    if st.button("카드뉴스 이미지 생성", key="card_btn", use_container_width=True):
        base = blog if blog else _ctx_block()
        ok_key, key_msg = validate_gemini_key(st.session_state.get('gemini_key', ''))
        if not base.strip():
            st.warning("블로그 글을 먼저 만들거나 전자책을 분석해주세요.")
        elif not ok_key:
            st.warning(key_msg + " (카드뉴스는 Google 키가 필요해요)")
        else:
            with st.spinner("카드 문구 구성 중..."):
                txt_prompt = f"""아래 글로 인스타 카드뉴스 {n_cards}장의 문구를 만들어라.
[원본]
{base}
규칙:
- 1번 카드=표지(스크롤 멈추는 강한 후킹 한 줄 + 한 줄 보조).
- 중간 카드=핵심 포인트 한 개씩(짧고 센 제목 + 1~2줄 설명).
- 마지막 카드=행동 유도(저장/팔로우/링크 클릭 유도).
- 문구는 짧게. 카드에 글자가 많으면 디자인이 깨진다.
JSON만: {{"cards":[{{"no":1,"title":"큰 글자 문구(10자 내외)","sub":"보조 문구(20자 내외, 없으면 빈칸)"}}]}}"""
                cards = parse_json(ask_ai(txt_prompt, 0.8, 2000))
            if not cards or not cards.get('cards'):
                st.error("카드 문구 생성에 실패했어요.")
            else:
                # 실제 인기 한국 카드뉴스의 디자인 디렉션 (스타일별 아트디렉터 노트)
                style_system = {
                    "모던 그리드 (화이트+형광 포인트, 정보형 인기템)":
                        "Art direction: clean pure-white (#FFFFFF) or off-white (#FAFAF7) background. "
                        "Extra-bold geometric sans-serif Korean type that looks like Gmarket Sans / Pretendard Black. "
                        "Near-black (#111) headline, with ONE single neon-lime or electric-blue highlight on the most important word "
                        "(like a marker swipe or solid color box behind 2~3 characters). Thin 1px divider lines, lots of whitespace, "
                        "left-aligned editorial grid layout. The trustworthy, information-card aesthetic of top Korean fintech/newsletter Instagram accounts (토스·뉴닉 느낌). Flat, no gradients, no glow.",
                    "다크 모노 (블랙+옐로우, 동기부여 강렬)":
                        "Art direction: solid near-black (#0E0E10) background. Huge bold condensed Korean sans-serif headline in pure white, "
                        "with ONE accent color (electric yellow #FFE03A or mint #36E0C0) used sparingly on a keyword or a small underline bar. "
                        "High contrast, punchy, masculine, motivational self-development account aesthetic. Centered or bottom-left text block. "
                        "Flat solid color, no gradients, no glow, no busy texture.",
                    "감성 사진 오버레이 (무드 사진+흰 텍스트)":
                        "Art direction: a moody, atmospheric lifestyle photograph as the full-bleed background (soft desk, window light, coffee, books, blurred bokeh), "
                        "covered with a dark gradient overlay (darker at the bottom) for text legibility. Clean bold white Korean sans-serif headline placed in the lower third. "
                        "Calm, emotional, premium blog/vlog Instagram aesthetic. The photo is real and tasteful, the typography is minimal and elegant.",
                    "파스텔 소프트 (크림+세리프, 독서·감성)":
                        "Art direction: warm cream / soft beige (#F3ECE0) background. Elegant Korean serif (명조) headline mixed with a light sans-serif subtext. "
                        "Muted earthy accent (terracotta or sage). Generous margins, gentle minimal layout, a small thin line or tiny dot ornament. "
                        "Warm, cozy, sophisticated reading/self-care Instagram aesthetic. No gradients, soft and quiet.",
                    "트렌디 그라데이션 (보라·핑크, MZ)":
                        "Art direction: smooth modern gradient (violet → pink → coral) background, bold rounded Korean sans-serif type in white with crisp edges, "
                        "one simple geometric shape accent. Trendy Gen-Z Korean creator aesthetic, clean and not cluttered. Subtle, tasteful — not over-saturated.",
                }[card_style]

                card_list = cards['cards']
                total = len(card_list)
                gkey = st.session_state.get('gemini_key', '')

                # 모든 카드 공통 템플릿 — 시리즈 일관성의 핵심
                handle = (brand_handle or "@cashmaker").strip()
                template_spec = (
                    f"FIXED TEMPLATE applied identically to every card in the series (this guarantees a consistent, professional carousel): "
                    f"(a) keep the SAME background treatment, the SAME font family, the SAME color palette, and the SAME margins on all cards. "
                    f"(b) a generous safe margin of about 10% on all four sides — text and key elements NEVER touch the edges. "
                    f"(c) a small page indicator in a consistent top-right or bottom-right corner showing '{{n}}/{total}'. "
                    f"(d) the brand handle '{handle}' as small, quiet text in the SAME bottom corner on every card. "
                    f"(e) ONE single idea per card, very short text, huge readable headline — never crowd the card with text."
                )

                def build_prompt(idx, card):
                    title = card.get('title', '')
                    sub = card.get('sub', '')
                    page = template_spec.replace("{n}", str(idx + 1))
                    if idx == 0:
                        role = ("This is the COVER (title) card: the biggest, boldest headline of the whole series, the strongest scroll-stopping hook. "
                                "Add a subtle swipe cue in a corner (a small right-arrow '→' or '밀어서 보기') inviting the user to swipe.")
                    elif idx == total - 1:
                        role = ("This is the CLOSING card: include a clear call-to-action element — a rounded button or pill shape with short Korean text like "
                                "'저장하기' or '프로필 링크 확인', and prompt to save/follow.")
                    else:
                        role = "This is a CONTENT card: one single key point, clear typographic hierarchy (one huge headline + one short supporting line)."
                    return (
                        f"Design a single 1:1 square Instagram carousel card that looks like a REAL high-performing Korean Instagram card-news made by a professional graphic designer in Figma. "
                        f"This is card {idx+1} of {total} in one cohesive series. {role} "
                        f"{style_system} {page} "
                        f"Render the Korean text 100% accurately, perfectly spelled and crisp, with strong hierarchy. "
                        f"Headline (대제목, keep it short): \"{title}\". "
                        + (f"Supporting line (보조, one short line): \"{sub}\". " if sub else "")
                        + "Flat, clean, intentional vector-style graphic design with precise alignment to an invisible grid. "
                        "It must look designed and editorial, NOT like a generic AI image. "
                        "No photo unless the style explicitly calls for one, no glossy 3D, no random glow, no watermark, no logo, no fake/gibberish text, no English filler text."
                    )

                # 병렬 생성 — 순서 보존
                results = [None] * total
                prog = st.progress(0.0, text="카드 디자인 생성 중...")
                done = 0
                with ThreadPoolExecutor(max_workers=IMG_WORKERS) as ex:
                    futs = {
                        ex.submit(_gen_image_core, gkey, build_prompt(i, c), "1:1", "2K"): i
                        for i, c in enumerate(card_list)
                    }
                    for fut in as_completed(futs):
                        i = futs[fut]
                        try:
                            data, err = fut.result()
                        except Exception as e:
                            data, err = None, _friendly_error(e)
                        if data:
                            results[i] = (card_list[i].get('title', ''), data)
                        done += 1
                        prog.progress(done / total, text=f"카드 생성 중... {done}/{total}")
                prog.empty()

                imgs = [r for r in results if r]
                st.session_state['card_imgs'] = imgs
                if imgs:
                    st.success(f"카드 {len(imgs)}장 생성 완료!" + (f" ({total - len(imgs)}장 실패)" if len(imgs) < total else ""))
                else:
                    st.error("이미지 생성에 실패했어요. 잠시 후 다시 시도해주세요.")

    if st.session_state.get('card_imgs'):
        imgs = st.session_state['card_imgs']
        st.download_button("전체 카드 ZIP 저장", data=zip_images(imgs),
                           file_name="cardnews.zip", mime="application/zip",
                           use_container_width=True, key="card_zip_dl")
        cols = st.columns(2)
        for i, (title, data) in enumerate(imgs):
            with cols[i % 2]:
                st.image(data, caption=f"카드 {i+1}: {title[:20]}", use_container_width=True)
                st.download_button(f"카드 {i+1} 저장", data=data, file_name=f"card_{i+1}.png",
                                   mime="image/png", key=f"card_dl_{i}", use_container_width=True)


# ==========================================
# 탭 3 — 크몽 등록 자료
# ==========================================
def tab_kmong():
    section("STEP 04", "크몽 등록 자료")
    a = ctx_summary()
    if a:
        st.markdown(f'<span class="ctx-pill">📚 {html.escape(a.get("title",""))} 기반</span>', unsafe_allow_html=True)
    st.caption("크몽 서비스 등록에 필요한 제목·소개·가격을 한 번에 만듭니다.")

    product_kind = st.text_input("판매 상품 종류",
                                 value="전자책" if a else "전자책 + AI 자동작성 프로그램", key="km_kind")

    if st.button("크몽 등록 자료 생성", key="km_btn", use_container_width=True):
        with st.spinner("크몽 등록 자료 만드는 중..."):
            prompt = f"""너는 크몽 상위 0.1% 디지털상품 셀러이자 카피라이터다.
크몽 서비스 등록에 필요한 자료를 만들어라.
{_ctx_block()}
[판매 상품]: {product_kind}
{STYLE_CORE}

[만들 것]
1. 서비스 제목 7개 — ★크몽 제목은 25자 내외(공백 포함)다. 반드시 25자 안에서 자극적이고 클릭을 부르게. 각 제목 끝에 (글자수) 표기.
2. 한 줄 소개 3개 — 클릭을 부르는.
3. 가격 추천 — 이 상품에 적정한 가격을 네가 직접 추천해라. 베이직/스탠다드/프리미엄 3단 구성으로 각 가격과 포함 내용, 추천 근거까지.

각 항목을 ===== 제목(25자 내외) ===== / ===== 한 줄 소개 ===== / ===== 가격 추천 ===== 으로 구분. 설명 없이 결과만."""
            r = ask_ai(prompt, 0.8, 4000)
            if r:
                st.session_state['kmong_result'] = r

    if st.session_state.get('kmong_result'):
        st.markdown("---")
        copy_block(st.session_state['kmong_result'], key="km_out", height=440)
        st.download_button("자료 저장 (.txt)", data=st.session_state['kmong_result'].encode('utf-8'),
                           file_name="kmong.txt", mime="text/plain", use_container_width=True, key="km_dl")
        st.info("상세페이지는 '⑤ 상세페이지' 탭에서 전자책 기반으로 자동 생성돼요.")


# ==========================================
# 탭 4 — 상세페이지
# ==========================================
def tab_detail():
    section("STEP 05", "크몽 상세페이지")
    a = ctx_summary()
    if not a:
        st.warning("먼저 ① 탭에서 전자책을 분석해주세요. 상세페이지는 전자책 내용을 토대로 생성돼요.")
        return
    st.markdown(f'<span class="ctx-pill">📚 {html.escape(a.get("title",""))} 기반 · 자동 생성</span>', unsafe_allow_html=True)
    st.caption("상단 디자인 이미지 + 9페이지 분량의 설득형 상품 설명을 자동으로 만듭니다.")

    col1, col2 = st.columns(2)
    with col1:
        gen_text = st.button("① 상품 설명 글 (9페이지)", key="detail_text_btn", use_container_width=True)
    with col2:
        gen_img = st.button("② 상단 디자인 이미지", key="detail_img_btn", use_container_width=True)

    if gen_text:
        with st.spinner("설득형 상품 설명 작성 중... 9페이지 분량이라 1~2분 걸려요"):
            prompt = f"""너는 크몽 상세페이지로 전자책을 파는 최고의 세일즈 카피라이터다.
아래 전자책을 토대로 '상품 설명 글'을 9페이지 분량(약 8000~9000자)으로 길고 설득력 있게 써라. (디자인 말고 순수 텍스트)
{_ctx_block()}
{STYLE_CORE}
[상세페이지 9개 섹션 — 각 섹션을 충분히 길고 깊게. 섹션마다 ■ 소제목으로 구분]
1. 후킹 (1페이지): 타겟 독자의 현재 고통을 정면으로. "이러고 있지 않나요?" 장면을 생생하게.
2. 깊은 공감 (1페이지): 그 고통이 어떤 일상인지 구체적 장면으로. 독자가 "내 얘기다" 하게.
3. 통념 부수기 (1페이지): 왜 지금까지 안 됐는지. 그건 당신 탓이 아니라고. 흔한 방법들이 왜 틀렸는지.
4. 해답 제시 (1페이지): 그래서 이 전자책이 답인 이유. 무엇이 어떻게 다른지 구체적으로.
5. 내용 미리보기 (1페이지): 이 책에 무엇이 담겼는지. 목차/핵심 포인트를 매력적으로 소개.
6. 구체적 혜택·결과 (1페이지): 이 책을 읽으면 무엇이 달라지는지 장면과 숫자로.
7. 대상 독자 (1페이지): 누구에게 꼭 필요한가 / 누구에겐 필요 없는가. 체크리스트 형태로.
8. 신뢰·후기 톤 (1페이지): 구매 후 변화, 적용 사례 느낌, 자주 묻는 질문(Q&A) 몇 개.
9. 마지막 클로징 (1페이지): 지금 결제해야 하는 이유. 강한 행동 유도로 마무리.

[중요] 분량을 충분히 채워라. 각 섹션이 너무 짧으면 안 된다. 전체 8000자 이상.
설명 없이 상품 설명 글만 출력. 소제목(■)으로 9개 섹션을 명확히 구분하되 딱딱하지 않게."""
            r = ask_ai(prompt, 0.85, 8000)
            if r:
                st.session_state['detail_text'] = r

    if gen_img:
        ok_key, key_msg = validate_gemini_key(st.session_state.get('gemini_key', ''))
        if not ok_key:
            st.warning(key_msg + " (이미지는 Google 키가 필요해요)")
        else:
            with st.spinner("상단 디자인 이미지 생성 중... (2K 고화질)"):
                title = a.get('title', '전자책')
                msg = a.get('core_message', '')
                img_prompt = (
                    "Create a premium hero banner for a Korean digital product detail page (크몽 상세페이지 상단 배너), "
                    "designed by a top commercial designer. Landscape 16:9. "
                    "Deep navy-to-black background with elegant gold (#C9A24B) accents, refined light rays or subtle geometric texture, "
                    "luxury self-development brand aesthetic, the polish of a Wadiz crowdfunding main banner. "
                    "Render Korean text PERFECTLY and legibly with strong typographic hierarchy. "
                    f"Large main headline: \"{title}\". Supporting subheadline: \"{msg}\". "
                    "Generous margins, balanced cinematic composition, high contrast, trustworthy and high-end. "
                    "Typography and shape driven graphic design, NOT a photo. No watermark, no logo, no random gibberish text."
                )
                data, err = generate_image(img_prompt, aspect_ratio="16:9", image_size="2K")
                if data:
                    st.session_state['detail_img'] = data
                elif err:
                    st.error(err)

    if st.session_state.get('detail_img'):
        st.markdown("---")
        st.markdown("#### 🖼️ 상단 디자인 이미지")
        st.image(st.session_state['detail_img'], use_container_width=True)
        st.download_button("이미지 저장", data=st.session_state['detail_img'],
                           file_name="detail_head.png", mime="image/png",
                           use_container_width=True, key="detail_img_dl")

    if st.session_state.get('detail_text'):
        st.markdown("---")
        st.markdown("#### 📝 상품 설명 글 (9페이지 분량)")
        copy_block(st.session_state['detail_text'], key="detail_text_out", height=460)
        st.download_button("설명 글 저장 (.txt)", data=st.session_state['detail_text'].encode('utf-8'),
                           file_name="detail.txt", mime="text/plain", use_container_width=True, key="detail_text_dl")


# ==========================================
# MAIN
# ==========================================
def main():
    if not st.session_state.get('authenticated'):
        render_login()
        return

    st.markdown("""
    <div class="hero">
        <span class="badge">CASHMAKER · 마케팅 통합기</span>
        <h1>📣 MarketKit</h1>
        <p style="color:var(--text2);">전자책 하나로 블로그·SNS·크몽 상세페이지까지 한 번에</p>
    </div>
    """, unsafe_allow_html=True)

    render_sidebar()
    if not validate_claude_key(st.session_state.get('api_key', ''))[0]:
        st.warning("👈 사이드바에 Claude API 키를 입력하면 모든 기능이 켜집니다.")

    t0, t1, t2, t3, t4 = st.tabs([
        "① 전자책", "② 블로그", "③ SNS", "④ 크몽", "⑤ 상세페이지"
    ])
    with t0:
        tab_ebook()
    with t1:
        tab_blog()
    with t2:
        tab_sns()
    with t3:
        tab_kmong()
    with t4:
        tab_detail()

    st.markdown("""
    <div class="footer">
        <span style="color:#C9A24B;">CASHMAKER</span> · MarketKit · 제작 남현우
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
