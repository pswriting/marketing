# -*- coding: utf-8 -*-
"""
MarketKit — 전자책 → 전 채널 마케팅 통합기 (통합 버전)
CashMaker 브랜드 / Writey 자매 제품

흐름:
  0. 전자책 업로드(PDF/DOCX/TXT) → 내용 자동 분석
  1. 블로그 주제 추천 → 선택 → 본문 생성
  2. SNS 플랫폼별 콘텐츠 변환 (복사 방식)
  3. 크몽 입점 세트: 제목·설명·상세페이지·가격 추천
  4. 상세페이지 디자인을 HTML/이미지로 생성 (코드로 그리는 카드형, 다운로드)

기술: Streamlit + Claude API (Sonnet 4.5)
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

# Claude API
try:
    import anthropic
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False

# 파일 읽기용
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

st.set_page_config(page_title="MarketKit", layout="wide", page_icon="📣")

# ==========================================
# STYLE — 디자이너 톤 (다크 + 골드 + 청록 액센트)
# ==========================================
st.markdown("""
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

:root {
    --gold: #C9A24B;
    --gold-light: #E0C074;
    --teal: #4BB7A8;
    --dark: #0B0B0D;
    --card: rgba(255,255,255,0.03);
    --card2: rgba(255,255,255,0.06);
    --text: #F5F3EF;
    --text2: #908D86;
    --line: rgba(201,162,75,0.18);
}
* { font-family: 'Pretendard', -apple-system, sans-serif !important; }

.stApp {
    background:
        radial-gradient(ellipse at 18% 0%, rgba(75,183,168,0.06) 0%, transparent 52%),
        radial-gradient(ellipse at 82% 100%, rgba(201,162,75,0.05) 0%, transparent 52%),
        linear-gradient(180deg, #0B0B0D 0%, #08080A 50%, #0B0B0D 100%) !important;
    background-attachment: fixed;
}
.main .block-container { max-width: 1080px; padding: 2.5rem 2rem; }
.stDeployButton, footer, #MainMenu { display: none !important; }
header[data-testid="stHeader"] { background: transparent !important; }

h1,h2,h3 { color: var(--text) !important; letter-spacing:.3px; }
h1 { font-size: 32px !important; font-weight: 800 !important; }
h2 { font-size: 23px !important; font-weight: 700 !important; }
h3 { font-size: 18px !important; color: var(--gold) !important; font-weight: 600 !important; }
p,span,label,div,li { color: var(--text); font-size: 16px; line-height: 1.7; }

.stButton > button {
    background: linear-gradient(135deg,#E0C074,#C9A24B) !important;
    color:#0B0B0D !important; -webkit-text-fill-color:#0B0B0D !important;
    border:none !important; border-radius:12px; font-weight:700; font-size:15px !important;
    padding:13px 30px; transition:all .3s ease; box-shadow:0 6px 20px rgba(201,162,75,.22);
}
.stButton > button * { color:#0B0B0D !important; -webkit-text-fill-color:#0B0B0D !important; }
.stButton > button:hover { box-shadow:0 10px 32px rgba(201,162,75,.4); transform:translateY(-2px); }

.stTextInput input, .stTextArea textarea {
    background:#fff !important; border:.5px solid var(--line) !important; border-radius:10px !important;
    color:#000 !important; -webkit-text-fill-color:#000 !important; padding:15px !important; font-size:16px !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color:var(--teal) !important; box-shadow:0 0 0 2px rgba(75,183,168,.2) !important;
}

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
</style>
""", unsafe_allow_html=True)


# ==========================================
# Claude API + 유틸
# ==========================================
def ask_ai(prompt, temperature=0.8, max_tokens=4000):
    api_key = st.session_state.get('api_key', '')
    if not api_key:
        st.error("사이드바에 API 키를 먼저 입력해주세요.")
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
    """업로드된 전자책에서 텍스트 추출. (PDF/DOCX/TXT)"""
    name = uploaded_file.name.lower()
    try:
        if name.endswith('.pdf'):
            if not PDF_AVAILABLE:
                return None, "PDF 처리 패키지(pypdf)가 없습니다."
            reader = PdfReader(io.BytesIO(uploaded_file.read()))
            text = "\n".join((p.extract_text() or "") for p in reader.pages)
            return text.strip(), None
        elif name.endswith('.docx'):
            if not DOCX_AVAILABLE:
                return None, "DOCX 처리 패키지(python-docx)가 없습니다."
            doc = Document(io.BytesIO(uploaded_file.read()))
            text = "\n".join(p.text for p in doc.paragraphs)
            return text.strip(), None
        elif name.endswith('.txt') or name.endswith('.md'):
            return uploaded_file.read().decode('utf-8', errors='ignore').strip(), None
        else:
            return None, "지원 형식: PDF, DOCX, TXT, MD"
    except Exception as e:
        return None, f"파일 읽기 오류: {str(e)[:100]}"


def copy_block(text, key, height=380):
    st.text_area("결과 (전체 선택 후 복사)", value=text, height=height, key=key)
    st.caption("Ctrl+A → Ctrl+C 로 복사해서 사용하세요.")


def ctx_summary():
    """업로드된 전자책 컨텍스트가 있으면 핵심 요약을 반환."""
    return st.session_state.get('ebook_analysis', {})


# 공통 스타일 가이드 (자청 톤 + 2026 네이버 알고리즘)
STYLE_CORE = """
[글의 정체성]
1) 후킹: 첫 3줄 안에 독자가 "이거 내 얘기인데"라고 멈추게. 통념을 뒤집고 독자의 현재 행동을 정확히 짚어라.
2) 신뢰: 주장마다 근거(데이터·원리·단계). 논문 수준 논리, 중학생도 읽을 쉬운 문장.

[2026 네이버 알고리즘 대응]
- C-Rank(전문성): 한 주제를 깊게. 구체적 수치·단계·비교·근거.
- D.I.A+(검색의도 충족): 읽고 나면 "더 검색할 필요 없다"고 느끼게 완결성 있게.
- 진정성: AI 광고글 티 나면 저품질. 실제 경험·구체적 장면·솔직한 한계를 섞어라.
- 키워드 남용 금지: 자연스러운 문맥에 핵심어가 녹게.

[어법]
- 한국어 원어민이 한 번에 이해되는 자연스러운 문장만. 어색하면 자극을 줄여서라도 자연스럽게.
- 추상 명사에 물리 동사 금지. 비유 오용 금지. AI 클리셰("~의 모든 것","결정적","게임체인저","~하는 방법") 금지.
"""


# ==========================================
# 사이드바 / 인증
# ==========================================
def render_sidebar():
    with st.sidebar:
        st.markdown("### 🔑 설정")
        if not st.session_state.get('authenticated'):
            pw = st.text_input("비밀번호", type="password", key="pw_input")
            if st.button("입장", key="login_btn", use_container_width=True):
                if pw == CORRECT_PASSWORD:
                    st.session_state['authenticated'] = True
                    st.rerun()
                else:
                    st.error("비밀번호가 올바르지 않습니다.")
            return False
        st.success("✓ 인증됨")
        api_key = st.text_input("Claude API 키", type="password",
                                value=st.session_state.get('api_key', ''), key="api_input",
                                help="sk-ant-... 형식")
        if api_key:
            st.session_state['api_key'] = api_key

        st.markdown("---")
        # 업로드된 전자책 상태
        a = ctx_summary()
        if a:
            st.markdown("##### 📚 분석된 전자책")
            st.caption(f"**{a.get('title','(제목 미상)')}**")
            st.caption(f"타겟: {a.get('target','-')[:40]}")
            if st.button("전자책 비우기", key="clear_ebook", use_container_width=True):
                for k in ['ebook_analysis', 'ebook_text']:
                    st.session_state.pop(k, None)
                st.rerun()
        else:
            st.caption("아직 분석된 전자책이 없어요. '① 전자책 분석' 탭에서 업로드하세요.")
        return True


# ==========================================
# 탭 0 — 전자책 분석
# ==========================================
def tab_ebook():
    st.markdown("### 📚 전자책 분석")
    st.caption("전자책 파일을 올리면 내용을 분석해서, 이후 모든 콘텐츠가 이 책에 맞춰 생성됩니다.")

    up = st.file_uploader("전자책 파일 (PDF / DOCX / TXT / MD)", type=['pdf', 'docx', 'txt', 'md'], key="ebook_up")

    if up is not None and st.button("이 전자책 분석하기", key="ebook_btn", use_container_width=True):
        with st.spinner("파일에서 내용 추출 중..."):
            text, err = extract_ebook_text(up)
        if err:
            st.error(err)
        elif not text or len(text) < 50:
            st.warning("텍스트를 충분히 추출하지 못했어요. (스캔 PDF는 인식이 안 될 수 있어요)")
        else:
            st.session_state['ebook_text'] = text[:20000]  # 너무 길면 앞부분
            with st.spinner("Claude가 전자책을 분석하는 중..."):
                prompt = f"""아래는 전자책의 본문이다. 이 책을 마케팅하기 위해 핵심을 분석해라.

[전자책 본문 (일부)]
{text[:15000]}

JSON만 출력:
{{
  "title": "이 책의 핵심을 담은 제목 (추정)",
  "target": "이 책이 가장 도움 될 독자 한 문장",
  "core_message": "이 책이 전하는 핵심 메시지 한 문장",
  "key_topics": ["책에서 다루는 핵심 주제 5개"],
  "pain_points": ["타겟 독자가 지금 겪는 고통 3개"],
  "unique_value": "이 책만의 차별점 한 문장"
}}"""
                result = ask_ai(prompt, temperature=0.5, max_tokens=2000)
                data = parse_json(result)
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
        <p><b style="color:var(--teal);">차별점</b><br>{html.escape(a.get('unique_value',''))}</p>
        </div>""", unsafe_allow_html=True)
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
# 탭 1 — 블로그 (주제 추천 → 본문 생성)
# ==========================================
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


def tab_blog():
    st.markdown("### ✍️ 블로그 (주제 추천 → 본문)")
    a = ctx_summary()
    if a:
        st.markdown(f'<span class="ctx-pill">📚 {html.escape(a.get("title",""))} 기반</span>', unsafe_allow_html=True)
    else:
        st.caption("전자책을 먼저 분석하면 책에 맞춘 주제가 추천돼요. (없어도 직접 주제 입력 가능)")

    # 1) 주제 추천
    st.markdown("#### 1단계 · 블로그 주제 추천")
    if st.button("이 전자책으로 블로그 주제 10개 추천받기", key="topic_btn", use_container_width=True):
        with st.spinner("검색에 걸리면서 전자책 판매로 이어질 주제 뽑는 중..."):
            prompt = f"""너는 네이버 블로그로 전자책을 파는 콘텐츠 전략가다.
{_ctx_block()}
이 전자책의 판매로 이어질 블로그 글 주제 10개를 추천해라.
- 검색량이 있으면서 경쟁이 덜한 롱테일 주제 위주.
- 각 주제는 그대로 블로그 제목으로 써도 될 만큼 구체적이고 후킹 있게.
- 정보형(구매 전)~구매형(전환)까지 단계가 골고루 섞이게.

JSON만 출력:
{{"topics": [{{"title": "주제(제목형)", "intent": "정보형/비교형/구매형", "why": "이게 왜 판매에 좋은지 한 줄"}}]}}"""
            result = ask_ai(prompt, temperature=0.8, max_tokens=2500)
            data = parse_json(result)
            if data and data.get('topics'):
                st.session_state['blog_topics'] = data['topics']
            else:
                st.error("주제 추천에 실패했어요. 다시 시도해주세요.")

    topics = st.session_state.get('blog_topics', [])
    if topics:
        labels = [f"[{t.get('intent','')}] {t.get('title','')}" for t in topics]
        idx = st.radio("마음에 드는 주제를 고르세요", range(len(labels)),
                       format_func=lambda i: labels[i], key="topic_pick")
        st.caption(f"💡 {topics[idx].get('why','')}")
        chosen = topics[idx].get('title', '')
    else:
        chosen = ""

    # 2) 본문 생성
    st.markdown("#### 2단계 · 본문 생성")
    topic = st.text_input("글 주제 (위에서 고르거나 직접 입력)", value=chosen, key="blog_topic")
    length = st.selectbox("글 길이", ["표준 (1500자)", "롱폼 (2500자)", "숏폼 (800자)"], key="blog_len")

    if st.button("블로그 본문 생성", key="blog_btn", use_container_width=True):
        if not topic.strip():
            st.warning("주제를 입력하거나 골라주세요.")
        else:
            lmap = {"표준 (1500자)": "1500자 내외", "롱폼 (2500자)": "2500자 내외", "숏폼 (800자)": "800자 내외"}
            with st.spinner("글 작성 중... (30초~1분)"):
                prompt = f"""너는 네이버 블로그에서 전자책을 파는 콘텐츠 마케터다. 블로그 글 한 편을 완성해라.
[주제]: {topic}
[목표 길이]: {lmap[length]}
{_ctx_block()}
{STYLE_CORE}
[구조] 1.후킹 도입(3~4줄,통념 뒤집기) 2.문제 정의(근거와 함께) 3.본론(단계·근거·수치,소제목 ■로) 4.실전 디테일(바로 적용할 행동 1~2개,핵심은 살짝 남겨) 5.마무리+전환(전자책 자연스럽게 연결)
[형식] 맨 위 추천 제목 3개(키워드 앞쪽) 먼저. 한 문단 2~4줄.
제목 3개 → 본문 순. 설명 없이 글만."""
                result = ask_ai(prompt, temperature=0.85, max_tokens=4000)
                if result:
                    st.session_state['blog_result'] = result

    if st.session_state.get('blog_result'):
        st.markdown("---")
        st.markdown("#### 📝 완성된 글")
        copy_block(st.session_state['blog_result'], key="blog_out")
        st.info("💡 'SNS 변환' 탭으로 가면 이 글이 자동으로 넘어가 채널별로 쪼갤 수 있어요.")


# ==========================================
# 탭 2 — SNS 변환
# ==========================================
def tab_sns():
    st.markdown("### 📱 SNS 변환")
    st.caption("블로그 글을 채널별 콘텐츠로 변환합니다. (만든 뒤 복사해서 직접 발행)")

    source = st.text_area("원본 글 (블로그 결과가 자동으로 들어와요)",
                          value=st.session_state.get('blog_result', ''), height=160, key="sns_src")
    channels = st.multiselect("변환할 채널",
                              ["스레드(Threads)", "인스타 카드뉴스", "X(트위터)", "유튜브 쇼츠 대본"],
                              default=["스레드(Threads)", "인스타 카드뉴스"], key="sns_ch")

    if st.button("SNS용으로 변환", key="sns_btn", use_container_width=True):
        if not source.strip():
            st.warning("원본 글을 입력하거나 블로그 탭에서 먼저 생성해주세요.")
        elif not channels:
            st.warning("채널을 하나 이상 선택해주세요.")
        else:
            specs = {
                "스레드(Threads)": "스레드: 첫 줄 후킹, 짧은 문장 5~8개, 500자 이내, 끝에 자연스러운 행동 유도.",
                "인스타 카드뉴스": "인스타 카드뉴스: 표지 1장(강한 후킹) + 내용 카드 5~7장(한 줄 제목+2~3줄), 마지막 카드 전환 유도. [카드 N] 으로 구분.",
                "X(트위터)": "X 스레드: 첫 트윗 후킹(280자), 이어 4~6개(각 280자), 1/n 번호.",
                "유튜브 쇼츠 대본": "쇼츠 대본: 첫 3초 후킹+본론 40초+행동유도, 말로 읽는 대본체, [자막] 표시 포함.",
            }
            sel = "\n".join(f"- {specs[c]}" for c in channels)
            with st.spinner("채널별 변환 중..."):
                prompt = f"""너는 SNS 콘텐츠 전문가다. 원본 글의 핵심을 유지하며 채널별로 변환해라.
[원본 글]
{source}
{_ctx_block()}
[채널 규칙]
{sel}
[공통] 채널마다 톤 다르게(복붙 금지), 첫 문장 무조건 후킹, 과장·낚시 금지, 해시태그 채널당 3~5개.
각 채널을 ===== 채널명 ===== 으로 구분해 출력. 설명 없이 결과만."""
                result = ask_ai(prompt, temperature=0.85, max_tokens=4000)
                if result:
                    st.session_state['sns_result'] = result

    if st.session_state.get('sns_result'):
        st.markdown("---")
        st.markdown("#### 📤 변환 결과")
        copy_block(st.session_state['sns_result'], key="sns_out")


# ==========================================
# 탭 3 — 크몽 입점 세트
# ==========================================
def tab_kmong():
    st.markdown("### 🛒 크몽 입점 세트")
    st.caption("제목·설명·상세페이지·가격을 한 번에. (전자책 분석 결과를 기반으로)")

    a = ctx_summary()
    if a:
        st.markdown(f'<span class="ctx-pill">📚 {html.escape(a.get("title",""))} 기반</span>', unsafe_allow_html=True)

    product_kind = st.text_input("판매 상품 종류",
                                 value="전자책 + AI 자동작성 프로그램" if not a else "전자책",
                                 key="km_kind")
    price_hint = st.text_input("(선택) 희망 가격대 / 참고", placeholder="예: 3~5만원대 / 경쟁사는 보통 2만원", key="km_price")

    if st.button("크몽 입점 세트 생성", key="km_btn", use_container_width=True):
        with st.spinner("크몽 판매 페이지 세트 만드는 중..."):
            prompt = f"""너는 크몽 상위 0.1% 전자책·디지털상품 셀러이자 카피라이터다.
아래 정보로 크몽 입점에 필요한 판매 자료 세트를 만들어라.
{_ctx_block()}
[판매 상품]: {product_kind}
{f'[가격 참고]: {price_hint}' if price_hint.strip() else ''}
{STYLE_CORE}

[만들 것]
1. 상품 제목 5개 — 크몽 검색에 걸리는 키워드 + 후킹. 각 50자 이내.
2. 한 줄 소개 (서브 제목) 3개 — 클릭을 부르는.
3. 상세페이지 본문 — 아래 흐름으로 자청/와디즈 스타일(짧고 센 카피, 소제목, 구체 수치):
   ① 후킹(이 고민 있죠?) ② 문제 공감 ③ 이 상품이 답인 이유 ④ 구체적 결과/혜택 ⑤ 누구에게 필요한가 ⑥ 구매 후 변화 ⑦ 마지막 한 방(지금 사야 하는 이유)
4. 가격 전략 — 추천 가격 + 근거 + 가능하면 3단 구성(베이직/스탠다드/프리미엄) 제안.

각 항목을 ===== 제목 ===== / ===== 한 줄 소개 ===== / ===== 상세페이지 ===== / ===== 가격 전략 ===== 으로 구분해 출력. 설명 없이 결과만."""
            result = ask_ai(prompt, temperature=0.8, max_tokens=4000)
            if result:
                st.session_state['kmong_result'] = result

    if st.session_state.get('kmong_result'):
        st.markdown("---")
        st.markdown("#### 🛍️ 크몽 입점 세트")
        copy_block(st.session_state['kmong_result'], key="km_out", height=460)
        st.info("💡 상세페이지 텍스트가 마음에 들면 '상세페이지 디자인' 탭에서 카드형 이미지로 뽑을 수 있어요.")


# ==========================================
# 탭 4 — 상세페이지 디자인 생성 (HTML/이미지)
# ==========================================
def tab_design():
    st.markdown("### 🎨 상세페이지 디자인 생성")
    st.caption("크몽 상세페이지를 '디자이너가 만든 듯한' 카드형 디자인으로 생성합니다. HTML로 받아 브라우저에서 이미지로 캡처/저장하세요.")

    a = ctx_summary()
    default_copy = ""
    if st.session_state.get('kmong_result'):
        default_copy = st.session_state['kmong_result']

    copy_text = st.text_area(
        "상세페이지에 담을 내용 (크몽 탭 결과를 붙여넣거나 직접 작성)",
        value=default_copy, height=180, key="design_src"
    )

    style = st.selectbox("디자인 스타일",
                         ["자청/와디즈 (볼드·고대비·카피 중심)", "미니멀 럭셔리 (골드·여백)", "선명한 정보형 (도표·아이콘)"],
                         key="design_style")

    if st.button("상세페이지 디자인 생성", key="design_btn", use_container_width=True):
        if not copy_text.strip():
            st.warning("상세페이지에 담을 내용을 입력해주세요.")
        else:
            with st.spinner("디자인 코드 생성 중... (40초~1분)"):
                style_guide = {
                    "자청/와디즈 (볼드·고대비·카피 중심)":
                        "검정 배경에 강한 노랑/흰색 텍스트, 큰 헤드라인, 짧고 센 카피, 섹션마다 한 줄 후킹. 와디즈 펀딩 페이지 느낌.",
                    "미니멀 럭셔리 (골드·여백)":
                        "어두운 배경에 골드 포인트, 넉넉한 여백, 세리프 헤드라인, 절제된 고급스러움.",
                    "선명한 정보형 (도표·아이콘)":
                        "밝은 배경에 또렷한 대비, 숫자·단계·체크리스트를 카드로, 아이콘 활용, 신뢰감 있는 정보 정리.",
                }[style]
                prompt = f"""너는 전환율 높은 상세페이지를 만드는 웹 디자이너다.
아래 내용으로 크몽 상세페이지를 '완성된 단일 HTML 파일'로 만들어라.

[담을 내용]
{copy_text[:6000]}

[디자인 스타일]
{style_guide}

[기술 요구사항]
- 하나의 완결된 HTML (인라인 CSS). 외부 의존성 없이 그대로 브라우저에서 열려야 한다.
- 세로로 긴 상세페이지 형태. 폭 800px 중앙 정렬, 모바일에서도 읽히게.
- 섹션을 카드/블록으로 나눠 시각적 리듬을 준다. 큰 헤드라인 + 서브카피 + 본문.
- 한글 폰트는 시스템 기본 + Pretendard CDN(@import) 사용.
- 색·여백·타이포로 '디자이너가 만든 느낌'을 낸다. 밋밋한 기본 HTML 금지.
- 숫자·핵심 혜택은 시각적으로 강조(큰 숫자, 색 포인트, 박스).
- 이미지 태그(<img>)는 쓰지 마라(외부 이미지 없음). 도형·색·타이포·아이콘(유니코드/이모지)으로만 디자인.

HTML 코드만 출력. 설명·주석·코드펜스(```) 없이 <!DOCTYPE html>부터 시작."""
                result = ask_ai(prompt, temperature=0.7, max_tokens=8000)
                if result:
                    # 코드펜스 제거
                    result = result.replace('```html', '').replace('```', '').strip()
                    st.session_state['design_html'] = result

    if st.session_state.get('design_html'):
        st.markdown("---")
        st.markdown("#### 🖼️ 디자인 미리보기")
        html_code = st.session_state['design_html']
        st.components.v1.html(html_code, height=900, scrolling=True)

        st.download_button(
            "📥 HTML 파일 다운로드",
            data=html_code.encode('utf-8'),
            file_name="kmong_detail_page.html",
            mime="text/html",
            use_container_width=True,
            key="design_dl"
        )
        st.caption("내려받은 HTML을 브라우저로 열어 → 전체 화면 캡처하거나, "
                   "Canva·미리캔버스에 옮겨 이미지(PNG/JPG)로 내보내면 크몽 상세페이지로 바로 쓸 수 있어요.")


# ==========================================
# MAIN
# ==========================================
def main():
    st.markdown("""
    <div class="hero">
        <span class="badge">CASHMAKER · 마케팅 통합기</span>
        <h1>📣 MarketKit</h1>
        <p style="color:var(--text2);">전자책 하나로 블로그·SNS·크몽 상세페이지까지 한 번에</p>
    </div>
    """, unsafe_allow_html=True)

    if not render_sidebar():
        st.info("👈 사이드바에서 비밀번호를 입력해 시작하세요.")
        return
    if not st.session_state.get('api_key'):
        st.warning("👈 사이드바에 Claude API 키를 입력하면 모든 기능이 켜집니다.")

    t0, t1, t2, t3, t4 = st.tabs([
        "① 전자책 분석", "② 블로그", "③ SNS 변환", "④ 크몽 입점", "⑤ 상세페이지 디자인"
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
        tab_design()

    st.markdown("""
    <div class="footer">
        <span style="color:#C9A24B;">CASHMAKER</span> · MarketKit | 제작: <span style="color:#fff;">남현우</span>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
