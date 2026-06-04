# -*- coding: utf-8 -*-
"""
MarketKit v2 — 전자책 → 전 채널 마케팅 통합기
CashMaker 브랜드 / Writey 자매 제품

흐름:
  0. 전자책 업로드 → 내용 자동 분석
  1. 블로그 주제 추천(클릭 시 본문 칸 자동입력) → 본문 생성 (몰입형)
  2. SNS 변환 (블로그 결과 자동 반영, 카드뉴스는 이미지로 생성)
  3. 크몽 서비스 등록 자료 (제목 25자·가격 추천 포함)
  4. 상세페이지 = 디자인된 이미지 + 설득형 상품설명 2000자 (전자책 기반 자동)

이미지: Google Gemini Nano Banana Pro (gemini-3-pro-image-preview)
텍스트: Claude Sonnet 4.5
"""
import os
import logging
import json
import html
import io
import base64

os.environ['PYTHONIOENCODING'] = 'utf-8'
logging.getLogger('anthropic').setLevel(logging.ERROR)
logging.getLogger('httpx').setLevel(logging.ERROR)

import streamlit as st

try:
    import anthropic
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False

# Gemini 이미지 생성 (새 SDK)
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

st.set_page_config(page_title="MarketKit", layout="wide", page_icon="📣")

# ==========================================
# STYLE
# ==========================================
st.markdown("""
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
:root {
    --gold:#C9A24B; --gold-light:#E0C074; --teal:#4BB7A8; --dark:#0B0B0D;
    --card:rgba(255,255,255,0.03); --card2:rgba(255,255,255,0.06);
    --text:#F5F3EF; --text2:#908D86; --line:rgba(201,162,75,0.18);
}
* { font-family:'Pretendard',-apple-system,sans-serif !important; }
.stApp {
    background:
        radial-gradient(ellipse at 18% 0%, rgba(75,183,168,0.06) 0%, transparent 52%),
        radial-gradient(ellipse at 82% 100%, rgba(201,162,75,0.05) 0%, transparent 52%),
        linear-gradient(180deg,#0B0B0D 0%,#08080A 50%,#0B0B0D 100%) !important;
    background-attachment:fixed;
}
.main .block-container { max-width:1080px; padding:2.5rem 2rem; }
.stDeployButton, footer, #MainMenu { display:none !important; }
header[data-testid="stHeader"] { background:transparent !important; }

h1,h2,h3 { color:var(--text) !important; letter-spacing:.3px; }
h1 { font-size:32px !important; font-weight:800 !important; }
h2 { font-size:23px !important; font-weight:700 !important; }
h3 { font-size:18px !important; color:var(--gold) !important; font-weight:600 !important; }
p,span,label,div,li { color:var(--text); font-size:16px; line-height:1.7; }

.stButton > button {
    background:linear-gradient(135deg,#E0C074,#C9A24B) !important;
    color:#0B0B0D !important; -webkit-text-fill-color:#0B0B0D !important;
    border:none !important; border-radius:12px; font-weight:700; font-size:15px !important;
    padding:13px 30px; transition:all .3s ease; box-shadow:0 6px 20px rgba(201,162,75,.22);
}
.stButton > button * { color:#0B0B0D !important; -webkit-text-fill-color:#0B0B0D !important; }
.stButton > button:hover { box-shadow:0 10px 32px rgba(201,162,75,.4); transform:translateY(-2px); }

/* 입력 필드 — 흰 배경 + 검은 글씨 + 검은 placeholder/도움말 */
.stTextInput input, .stTextArea textarea {
    background:#fff !important; border:.5px solid var(--line) !important; border-radius:10px !important;
    color:#111 !important; -webkit-text-fill-color:#111 !important; padding:15px !important; font-size:16px !important;
}
.stTextInput input::placeholder, .stTextArea textarea::placeholder {
    color:#888 !important; -webkit-text-fill-color:#888 !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color:var(--teal) !important; box-shadow:0 0 0 2px rgba(75,183,168,.2) !important;
}

/* 셀렉트박스 — 흰 배경 + 검은 글씨 */
.stSelectbox div[data-baseweb="select"] > div {
    background:#fff !important; border:.5px solid var(--line) !important; border-radius:10px !important;
}
.stSelectbox div[data-baseweb="select"] span,
.stSelectbox div[data-baseweb="select"] div {
    color:#111 !important; -webkit-text-fill-color:#111 !important;
}
/* 드롭다운 펼침 목록 */
div[data-baseweb="popover"] li, ul[role="listbox"] li {
    color:#111 !important; -webkit-text-fill-color:#111 !important; background:#fff !important;
}
/* 멀티셀렉트 선택 태그 — 골드 배경 + 검은 글씨 */
.stMultiSelect div[data-baseweb="select"] > div {
    background:#fff !important; border:.5px solid var(--line) !important; border-radius:10px !important;
}
.stMultiSelect span[data-baseweb="tag"] {
    background:#C9A24B !important;
}
.stMultiSelect span[data-baseweb="tag"] span {
    color:#0B0B0D !important; -webkit-text-fill-color:#0B0B0D !important;
}
.stMultiSelect div[data-baseweb="select"] input { color:#111 !important; -webkit-text-fill-color:#111 !important; }

.stTabs [data-baseweb="tab-list"] { gap:4px; border-bottom:1px solid var(--line); flex-wrap:wrap; }
.stTabs [data-baseweb="tab"] { background:transparent; color:var(--text2) !important; border-radius:10px 10px 0 0; padding:11px 18px; font-weight:600; }
.stTabs [aria-selected="true"] {
    background:linear-gradient(135deg,rgba(75,183,168,.18),rgba(201,162,75,.10)) !important;
    color:var(--gold) !important; border-bottom:2px solid var(--teal);
}

.result-box { background:var(--card) !important; border:.5px solid var(--line); border-left:3px solid var(--teal); border-radius:12px; padding:22px 26px; margin:16px 0; }
.hero { text-align:center; padding:6px 0 26px; }
.hero .badge { display:inline-block; color:var(--teal); border:1px solid var(--teal); border-radius:20px; padding:5px 16px; font-size:12px; letter-spacing:2px; margin-bottom:12px; }
.ctx-pill { display:inline-block; background:var(--card2); border:.5px solid var(--line); border-radius:20px; padding:6px 16px; font-size:13px; color:var(--teal); margin-bottom:8px; }
.footer { text-align:center; padding:30px 20px; margin-top:50px; border-top:1px solid var(--line); color:#fff; font-size:14px; letter-spacing:2px; }

/* 전체화면 로그인 */
.login-wrap { max-width:420px; margin:8vh auto 0; text-align:center; }
.login-card {
    background:var(--card2); border:.5px solid var(--line); border-radius:20px;
    padding:48px 40px; box-shadow:0 20px 60px rgba(0,0,0,.4);
}
.login-card h1 { font-size:30px !important; margin-bottom:6px; }
.login-card .sub { color:var(--text2); font-size:15px; margin-bottom:28px; }
</style>
""", unsafe_allow_html=True)


# ==========================================
# Claude / Gemini 호출 + 유틸
# ==========================================
def ask_ai(prompt, temperature=0.8, max_tokens=4000):
    api_key = st.session_state.get('api_key', '')
    if not api_key:
        st.error("사이드바에 Claude API 키를 먼저 입력해주세요.")
        return None
    if not CLAUDE_AVAILABLE:
        st.error("anthropic 패키지가 없습니다. requirements.txt 확인 필요.")
        return None
    try:
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=CLAUDE_MODEL, max_tokens=max_tokens, temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text.strip()
    except Exception as e:
        st.error(f"생성 오류: {str(e)[:140]}")
        return None


def generate_image(prompt, aspect_ratio="1:1", image_size="2K"):
    """Gemini Nano Banana Pro로 이미지 생성. 화면비·해상도 지정.
    성공 시 (PNG bytes, None), 실패 시 (None, 에러)."""
    gkey = st.session_state.get('gemini_key', '')
    if not gkey:
        return None, "이미지 생성에는 Google(Gemini) API 키가 필요해요. 사이드바에 입력해주세요."
    if not GENAI_AVAILABLE:
        return None, "google-genai 패키지가 없습니다. requirements.txt 확인 필요."
    try:
        client = google_genai.Client(api_key=gkey)
        cfg = genai_types.GenerateContentConfig(
            response_modalities=["Image"],
            image_config=genai_types.ImageConfig(
                aspect_ratio=aspect_ratio,
                image_size=image_size,
            ),
        )
        resp = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=prompt,
            config=cfg,
        )
        for part in resp.candidates[0].content.parts:
            if getattr(part, 'inline_data', None) and part.inline_data.data:
                return part.inline_data.data, None
        return None, "이미지가 반환되지 않았어요. 프롬프트를 바꿔 다시 시도해주세요."
    except Exception as e:
        # image_config 미지원 SDK 대비 폴백
        try:
            client = google_genai.Client(api_key=gkey)
            resp = client.models.generate_content(model=IMAGE_MODEL, contents=prompt)
            for part in resp.candidates[0].content.parts:
                if getattr(part, 'inline_data', None) and part.inline_data.data:
                    return part.inline_data.data, None
        except Exception as e2:
            return None, f"이미지 생성 오류: {str(e2)[:140]}"
        return None, f"이미지 생성 오류: {str(e)[:140]}"


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
    st.text_area("결과 (전체 선택 후 복사)", value=text, height=height, key=key)
    st.caption("Ctrl+A → Ctrl+C 로 복사해서 사용하세요.")


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


# ==========================================
# 몰입형 글쓰기 가이드 (강화)
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
# 전체화면 로그인 (피드백 3)
# ==========================================
def render_login():
    st.markdown('<div class="login-wrap">', unsafe_allow_html=True)
    st.markdown("""
    <div class="login-card">
        <div style="color:#4BB7A8;font-size:13px;letter-spacing:3px;margin-bottom:10px;">CASHMAKER</div>
        <h1>📣 MarketKit</h1>
        <p class="sub">전자책 하나로 블로그·SNS·크몽까지 한 번에</p>
    </div>
    """, unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        pw = st.text_input("비밀번호를 입력하세요", type="password", key="pw_input",
                           placeholder="비밀번호 입력")
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
        st.markdown("### 🔑 API 설정")

        # 도움말을 본문 캡션(검은 배경에 흰 글씨가 기본이라 여기선 마크다운으로) 대신
        # 흰 입력칸 + 별도 설명 박스로. label은 사이드바라 흰색이지만 입력값은 검정.
        st.markdown('<div style="font-size:13px;color:#C9A24B;margin-bottom:4px;">Claude API 키 (글 생성용)</div>', unsafe_allow_html=True)
        api_key = st.text_input("Claude API 키", type="password", label_visibility="collapsed",
                                value=st.session_state.get('api_key', ''), key="api_input",
                                placeholder="sk-ant-...")
        if api_key:
            st.session_state['api_key'] = api_key
        st.markdown('<div style="font-size:12px;color:#888;margin-bottom:14px;">console.anthropic.com 에서 발급 (sk-ant- 로 시작)</div>', unsafe_allow_html=True)

        st.markdown('<div style="font-size:13px;color:#C9A24B;margin-bottom:4px;">Google API 키 (이미지 생성용·선택)</div>', unsafe_allow_html=True)
        gkey = st.text_input("Google API 키", type="password", label_visibility="collapsed",
                             value=st.session_state.get('gemini_key', ''), key="gkey_input",
                             placeholder="AIza...")
        if gkey:
            st.session_state['gemini_key'] = gkey
        st.markdown('<div style="font-size:12px;color:#888;margin-bottom:8px;">aistudio.google.com 에서 발급. 카드뉴스·상세페이지 이미지 생성에 사용</div>', unsafe_allow_html=True)

        st.markdown("---")
        a = ctx_summary()
        if a:
            st.markdown("##### 📚 분석된 전자책")
            st.markdown(f'<div style="color:#4BB7A8;font-size:14px;">{html.escape(a.get("title",""))}</div>', unsafe_allow_html=True)
            if st.button("전자책 비우기", key="clear_ebook", use_container_width=True):
                for k in ['ebook_analysis', 'ebook_text', 'blog_topics', 'blog_result',
                          'sns_result', 'kmong_result', 'detail_text', 'detail_images']:
                    st.session_state.pop(k, None)
                st.rerun()
        else:
            st.markdown('<div style="font-size:13px;color:#908D86;">아직 분석된 전자책이 없어요.<br>① 탭에서 업로드하세요.</div>', unsafe_allow_html=True)


# ==========================================
# 탭 0 — 전자책 분석
# ==========================================
def tab_ebook():
    st.markdown("### 📚 전자책 분석")
    st.caption("전자책 파일을 올리면 내용을 분석해, 이후 모든 콘텐츠가 이 책에 맞춰 생성됩니다.")

    up = st.file_uploader("전자책 파일 (PDF / DOCX / TXT / MD)", type=['pdf', 'docx', 'txt', 'md'], key="ebook_up")
    if up is not None and st.button("이 전자책 분석하기", key="ebook_btn", use_container_width=True):
        with st.spinner("파일에서 내용 추출 중..."):
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
                    st.success("✅ 분석 완료! 이제 다른 탭에서 이 책에 맞춘 콘텐츠를 만들 수 있어요.")
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
# 탭 1 — 블로그 (주제 클릭→본문칸 자동입력)
# ==========================================
def tab_blog():
    st.markdown("### ✍️ 블로그 (주제 추천 → 본문)")
    a = ctx_summary()
    if a:
        st.markdown(f'<span class="ctx-pill">📚 {html.escape(a.get("title",""))} 기반</span>', unsafe_allow_html=True)
    else:
        st.caption("전자책을 먼저 분석하면 책에 맞춘 주제가 추천돼요. (없어도 직접 입력 가능)")

    st.markdown("#### 1단계 · 블로그 주제 추천")
    if st.button("이 전자책으로 블로그 주제 10개 추천받기", key="topic_btn", use_container_width=True):
        with st.spinner("검색에 걸리면서 전자책 판매로 이어질 주제 뽑는 중..."):
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

    # 추천 주제 — 각 주제를 버튼으로. 클릭하면 본문 주제칸에 자동 입력 (피드백 1)
    topics = st.session_state.get('blog_topics', [])
    if topics:
        st.caption("👇 주제를 클릭하면 아래 본문 생성 칸에 자동으로 입력돼요.")
        for i, t in enumerate(topics):
            label = f"[{t.get('intent','')}] {t.get('title','')}"
            if st.button(label, key=f"pick_topic_{i}", use_container_width=True):
                # 위젯 key 자체를 세팅해야 text_input에 즉시 반영된다
                st.session_state['blog_topic'] = t.get('title', '')
                st.rerun()
            st.markdown(f'<div style="font-size:13px;color:#908D86;margin:-6px 0 10px 4px;">└ {html.escape(t.get("why",""))}</div>', unsafe_allow_html=True)

    st.markdown("#### 2단계 · 본문 생성")
    # value를 주지 않고 key만 사용 — 버튼이 session_state['blog_topic']를 채우면 그대로 표시됨
    topic = st.text_input("글 주제 (위에서 클릭하면 자동 입력 / 직접 입력도 가능)", key="blog_topic")
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
        st.info("💡 'SNS 변환' 탭으로 가면 이 글이 자동으로 반영돼요. (다시 입력 안 해도 됨)")


# ==========================================
# 탭 2 — SNS 변환 (블로그 자동 반영 + 카드뉴스 이미지)
# ==========================================
def tab_sns():
    st.markdown("### 📱 SNS 변환")
    blog = st.session_state.get('blog_result', '')
    if blog:
        st.markdown('<span class="ctx-pill">✅ 블로그 글이 자동 반영됨</span>', unsafe_allow_html=True)
        st.caption("방금 만든 블로그 글을 기반으로 변환합니다. (원본 재입력 불필요)")
    else:
        st.caption("블로그 탭에서 글을 먼저 만들면 자동 반영돼요. (또는 전자책 분석만으로도 변환 가능)")

    # 글 기반 채널
    st.markdown("#### 글 콘텐츠")
    text_channels = st.multiselect("SNS 채널 선택",
                                   ["스레드(Threads)", "X(트위터)", "유튜브 쇼츠 대본"],
                                   default=["스레드(Threads)"], key="sns_text_ch")
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

    # 인스타 카드뉴스 (이미지)
    st.markdown("---")
    st.markdown("#### 인스타 카드뉴스 (이미지로 생성)")
    st.caption("실제 인기 카드뉴스 수준의 고품질 디자인으로 생성합니다. (Google API 키 필요)")

    card_style = st.selectbox(
        "디자인 스타일",
        ["트렌디 그라데이션 (보라·핑크, MZ 감성)",
         "프리미엄 다크 (네이비·골드, 고급)",
         "클린 미니멀 (화이트·블랙, 매거진)",
         "비비드 팝 (선명한 단색, 강한 대비)"],
        key="card_style"
    )
    n_cards = st.slider("카드 장수", 3, 8, 5, key="card_n")

    if st.button("카드뉴스 이미지 생성", key="card_btn", use_container_width=True):
        base = blog if blog else _ctx_block()
        if not base.strip():
            st.warning("블로그 글을 먼저 만들거나 전자책을 분석해주세요.")
        elif not st.session_state.get('gemini_key'):
            st.warning("카드뉴스 이미지 생성에는 사이드바의 Google API 키가 필요해요.")
        else:
            # 1) 카드별 문구를 Claude로 구성
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
                # 2) 스타일별 통일 디자인 시스템 (시리즈 일관성)
                style_system = {
                    "트렌디 그라데이션 (보라·핑크, MZ 감성)":
                        "Design system: vibrant purple-to-pink-to-coral gradient background, "
                        "modern geometric shapes and soft glow accents, bold rounded sans-serif Korean typography, "
                        "trendy Gen-Z social media aesthetic like top Korean Instagram creators, white text with subtle shadow.",
                    "프리미엄 다크 (네이비·골드, 고급)":
                        "Design system: deep navy to near-black background, elegant gold (#C9A24B) accent lines and frames, "
                        "premium serif+sans Korean typography, luxury self-development brand aesthetic, generous negative space, refined and trustworthy.",
                    "클린 미니멀 (화이트·블랙, 매거진)":
                        "Design system: clean off-white background, strong black Korean typography, single accent color, "
                        "editorial magazine layout, lots of whitespace, minimal geometric divider lines, sophisticated and calm.",
                    "비비드 팝 (선명한 단색, 강한 대비)":
                        "Design system: one bold vivid solid color background per card from a cohesive palette, "
                        "huge high-contrast Korean typography, playful bold shapes, punchy energetic social media style, eye-catching.",
                }[card_style]

                st.session_state['card_imgs'] = []
                prog = st.progress(0)
                total = len(cards['cards'])
                for idx, card in enumerate(cards['cards']):
                    title = card.get('title', '')
                    sub = card.get('sub', '')
                    is_cover = (idx == 0)
                    role = ("COVER card — make it the most eye-catching, largest headline, strongest hook"
                            if is_cover else
                            ("CLOSING card — include a clear call-to-action button or label" if idx == total - 1
                             else "CONTENT card — one key point, clear hierarchy"))
                    img_prompt = (
                        f"Create a professional Instagram carousel card, 1:1 square, designed by a top social media designer. "
                        f"This is card {idx+1} of {total} in a cohesive series — keep the SAME visual style across the series. "
                        f"{style_system} "
                        f"This is the {role}. "
                        f"Render Korean text PERFECTLY and legibly, with strong typographic hierarchy (big headline, smaller subtext). "
                        f"Headline (대제목): \"{title}\". "
                        + (f"Sub text (보조): \"{sub}\". " if sub else "")
                        + "Balanced composition, professional grid alignment, generous margins so text never touches edges. "
                        "High visual polish, looks like a real viral Korean Instagram card-news. No watermark, no logo, no extra gibberish text. "
                        "Typography-driven graphic design, NOT a photo."
                    )
                    data, err = generate_image(img_prompt, aspect_ratio="1:1", image_size="2K")
                    if data:
                        st.session_state['card_imgs'].append((title, data))
                    prog.progress((idx + 1) / total)
                prog.empty()
                if st.session_state['card_imgs']:
                    st.success(f"✅ 카드 {len(st.session_state['card_imgs'])}장 생성 완료!")
                else:
                    st.error("이미지 생성에 실패했어요. (오류 메시지가 위에 떴다면 그 내용을 확인해주세요)")

    # 생성된 카드 표시
    if st.session_state.get('card_imgs'):
        cols = st.columns(2)
        for i, (title, data) in enumerate(st.session_state['card_imgs']):
            with cols[i % 2]:
                st.image(data, caption=f"카드 {i+1}: {title[:20]}", use_container_width=True)
                st.download_button(f"카드 {i+1} 저장", data=data, file_name=f"card_{i+1}.png",
                                   mime="image/png", key=f"card_dl_{i}", use_container_width=True)


# ==========================================
# 탭 3 — 크몽 서비스 등록 자료 (피드백 8·9·10)
# ==========================================
def tab_kmong():
    st.markdown("### 🛒 크몽 서비스 등록에 필요한 자료 생성")
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
        st.info("💡 상세페이지(디자인 이미지 + 설명 글)는 '⑤ 상세페이지' 탭에서 전자책 기반으로 자동 생성돼요.")


# ==========================================
# 탭 4 — 상세페이지 (디자인 이미지 + 설득형 2000자, 전자책 자동) 피드백 11
# ==========================================
def tab_detail():
    st.markdown("### 🎨 크몽 상세페이지")
    a = ctx_summary()
    if a:
        st.markdown(f'<span class="ctx-pill">📚 {html.escape(a.get("title",""))} 기반 · 자동 생성</span>', unsafe_allow_html=True)
        st.caption("전자책 내용을 토대로, 상단 디자인 이미지 + 9페이지 분량의 설득형 상품 설명을 자동으로 만듭니다.")
    else:
        st.warning("먼저 ① 탭에서 전자책을 분석해주세요. 상세페이지는 전자책 내용을 토대로 생성돼요.")
        return

    col1, col2 = st.columns(2)
    with col1:
        gen_text = st.button("① 상품 설명 글 생성 (9페이지 분량)", key="detail_text_btn", use_container_width=True)
    with col2:
        gen_img = st.button("② 상단 디자인 이미지 생성", key="detail_img_btn", use_container_width=True)

    # ① 설득형 상품 설명 — 9페이지(약 9000자) 분량
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

    # ② 상단 디자인 이미지 — 16:9, 2K, 디자인 디렉팅 강화
    if gen_img:
        if not st.session_state.get('gemini_key'):
            st.warning("이미지 생성에는 사이드바의 Google API 키가 필요해요.")
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

    # 결과 표시
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
        st.caption("위 이미지를 상단에 넣고, 이 글을 본문으로 붙이면 크몽 상세페이지가 완성돼요.")


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
    if not st.session_state.get('api_key'):
        st.warning("👈 사이드바에 Claude API 키를 입력하면 모든 기능이 켜집니다.")

    t0, t1, t2, t3, t4 = st.tabs([
        "① 전자책 분석", "② 블로그", "③ SNS 변환", "④ 크몽 등록자료", "⑤ 상세페이지"
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
        <span style="color:#C9A24B;">CASHMAKER</span> · MarketKit | 제작: <span style="color:#fff;">남현우</span>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
