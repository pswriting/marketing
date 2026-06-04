# -*- coding: utf-8 -*-
"""
MarketKit — 전자책 판매를 위한 콘텐츠 마케팅 통합 프로그램
CashMaker 브랜드 / Writey 자매 제품

탭 구성:
  1. 키워드 도우미   : 주제 → 파생 키워드 30개 + 검색의도 분류
  2. 블로그 생성기   : 자청 후킹 + 논문급 근거 구조 (2026 네이버 알고리즘 대응)
  3. SNS 변환기      : 블로그 글 → 스레드 / 인스타 카드뉴스 / X
  4. 후킹 자산       : 도입부 → 광고카피 / 이메일 제목 / 쇼츠 대본

기술: Streamlit + Claude API (Sonnet 4.5) / 클립보드 복사 방식
"""
import os
import logging

os.environ['PYTHONIOENCODING'] = 'utf-8'
logging.getLogger('anthropic').setLevel(logging.ERROR)
logging.getLogger('httpx').setLevel(logging.ERROR)

import streamlit as st
import json
import html

# Claude API
try:
    import anthropic
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False

# ==========================================
# 설정
# ==========================================
CORRECT_PASSWORD = "cashmaker2024"   # ← 비밀번호 변경 시 여기만 수정
CLAUDE_MODEL = "claude-sonnet-4-5"   # 품질 보장용 고정 모델

st.set_page_config(page_title="MarketKit", layout="wide", page_icon="📣")

# ==========================================
# STYLE — CashMaker 다크 + 골드 (Writey 자매 톤, 액센트는 청록으로 차별화)
# ==========================================
st.markdown("""
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

:root {
    --gold: #C9A24B;
    --gold-light: #E0C074;
    --teal: #4BB7A8;          /* MarketKit 고유 액센트 */
    --dark: #0B0B0D;
    --charcoal: #141416;
    --card: rgba(255,255,255,0.03);
    --card2: rgba(255,255,255,0.06);
    --text: #F5F3EF;
    --text2: #8A8780;
    --line: rgba(201,162,75,0.18);
}

* { font-family: 'Pretendard', -apple-system, sans-serif !important; }

.stApp {
    background:
        radial-gradient(ellipse at 20% 0%, rgba(75,183,168,0.05) 0%, transparent 55%),
        radial-gradient(ellipse at 80% 100%, rgba(201,162,75,0.04) 0%, transparent 55%),
        linear-gradient(180deg, #0B0B0D 0%, #08080A 50%, #0B0B0D 100%) !important;
    background-attachment: fixed;
}
.main .block-container { max-width: 1100px; padding: 2.5rem 2rem; }
.stDeployButton, footer, #MainMenu { display: none !important; }
header[data-testid="stHeader"] { background: transparent !important; }

h1, h2, h3 { color: var(--text) !important; letter-spacing: 0.3px; }
h1 { font-size: 32px !important; font-weight: 800 !important; }
h2 { font-size: 24px !important; font-weight: 700 !important; }
h3 { font-size: 19px !important; color: var(--gold) !important; font-weight: 600 !important; }
p, span, label, div, li { color: var(--text); font-size: 16px; line-height: 1.7; }

/* 버튼 — 골드 그라데이션 */
.stButton > button {
    background: linear-gradient(135deg, #E0C074 0%, #C9A24B 100%) !important;
    color: #0B0B0D !important;
    -webkit-text-fill-color: #0B0B0D !important;
    border: none !important;
    border-radius: 12px;
    font-weight: 700;
    font-size: 15px !important;
    padding: 14px 32px;
    transition: all 0.3s ease;
    box-shadow: 0 6px 20px rgba(201,162,75,0.22);
}
.stButton > button * { color: #0B0B0D !important; -webkit-text-fill-color: #0B0B0D !important; }
.stButton > button:hover {
    box-shadow: 0 10px 32px rgba(201,162,75,0.4);
    transform: translateY(-2px);
}

/* 입력 필드 */
.stTextInput input, .stTextArea textarea {
    background: #ffffff !important;
    border: 0.5px solid var(--line) !important;
    border-radius: 10px !important;
    color: #000 !important;
    -webkit-text-fill-color: #000 !important;
    padding: 16px !important;
    font-size: 16px !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: var(--teal) !important;
    box-shadow: 0 0 0 2px rgba(75,183,168,0.2) !important;
}

/* 탭 */
.stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid var(--line); }
.stTabs [data-baseweb="tab"] {
    background: transparent;
    color: var(--text2) !important;
    border-radius: 10px 10px 0 0;
    padding: 12px 20px;
    font-weight: 600;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, rgba(75,183,168,0.18), rgba(201,162,75,0.10)) !important;
    color: var(--gold) !important;
    border-bottom: 2px solid var(--teal);
}

/* 결과 카드 */
.result-box {
    background: var(--card) !important;
    border: 0.5px solid var(--line);
    border-left: 3px solid var(--teal);
    border-radius: 12px;
    padding: 24px 28px;
    margin: 16px 0;
}
.hero {
    text-align: center;
    padding: 10px 0 30px;
}
.hero .badge {
    display: inline-block;
    color: var(--teal);
    border: 1px solid var(--teal);
    border-radius: 20px;
    padding: 5px 16px;
    font-size: 12px;
    letter-spacing: 2px;
    margin-bottom: 14px;
}
.kw-chip {
    display: inline-block;
    background: var(--card2);
    border: 0.5px solid var(--line);
    border-radius: 8px;
    padding: 6px 14px;
    margin: 4px;
    font-size: 14px;
}
.footer {
    text-align: center; padding: 30px 20px; margin-top: 50px;
    border-top: 1px solid var(--line); color: #fff; font-size: 14px; letter-spacing: 2px;
}
</style>
""", unsafe_allow_html=True)


# ==========================================
# Claude API 호출
# ==========================================
def ask_ai(prompt, temperature=0.8, max_tokens=4000):
    """Claude API 호출. 실패 시 None 반환."""
    api_key = st.session_state.get('api_key', '')
    if not api_key:
        st.error("API 키를 먼저 입력해주세요 (사이드바).")
        return None
    if not CLAUDE_AVAILABLE:
        st.error("anthropic 패키지가 설치되지 않았습니다. pip install anthropic")
        return None
    try:
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text.strip()
    except Exception as e:
        st.error(f"생성 중 오류가 발생했습니다: {str(e)[:120]}")
        return None


def parse_json(text):
    """AI 응답에서 JSON 안전 추출."""
    if not text:
        return None
    try:
        cleaned = text.replace('```json', '').replace('```', '').strip()
        start = cleaned.find('{')
        start_arr = cleaned.find('[')
        if start_arr != -1 and (start == -1 or start_arr < start):
            start = start_arr
            end = cleaned.rfind(']') + 1
        else:
            end = cleaned.rfind('}') + 1
        if start != -1 and end > start:
            return json.loads(cleaned[start:end])
    except Exception:
        pass
    return None


def copy_block(text, key):
    """클립보드 복사용 텍스트 영역 + 안내."""
    st.text_area("결과 (전체 선택 후 복사)", value=text, height=400, key=key)
    st.caption("위 내용을 전체 선택(Ctrl+A) → 복사(Ctrl+C)해서 네이버 스마트에디터에 붙여넣으세요.")


# ==========================================
# 인증 / 사이드바
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
        api_key = st.text_input(
            "Claude API 키", type="password",
            value=st.session_state.get('api_key', ''), key="api_input",
            help="sk-ant-... 형식. 한 번 입력하면 이 세션 동안 유지됩니다."
        )
        if api_key:
            st.session_state['api_key'] = api_key

        st.markdown("---")
        st.markdown("##### 📣 MarketKit")
        st.caption("전자책 하나로 전 채널 마케팅 콘텐츠를 뽑아내는 통합기")
        return True


# ==========================================
# 프롬프트 — 공통 스타일 가이드
# ==========================================
# 자청 톤 + 2026 네이버 알고리즘(C-Rank 전문성 / D.I.A+ 완결성) + 논문급 근거
STYLE_CORE = """
[글의 정체성 — 이 둘을 동시에 만족시켜라]
1) 후킹: 첫 3줄 안에 독자가 "이거 내 얘기인데"라고 멈추게 만든다. 통념을 뒤집고, 독자의 현재 행동을 정확히 짚는다.
2) 신뢰: 주장마다 근거(데이터·원리·출처 맥락·단계)를 붙여 "이 사람은 진짜 아는 사람"이라는 인상을 준다. 논문 수준의 논리 구조를 갖되, 문장은 중학생도 읽을 만큼 쉽게 쓴다.

[2026 네이버 알고리즘 대응 — 반드시 반영]
- C-Rank(전문성): 한 주제를 깊게 파고들어 전문성 신호를 준다. 구체적 수치, 단계, 비교, 근거를 넣는다.
- D.I.A+(검색의도 충족): 독자가 이 글을 읽고 "더 검색할 필요가 없다"고 느끼게 완결성 있게 쓴다. 검색의도를 글 안에서 끝까지 해소한다.
- 진정성: AI가 뽑아낸 광고글 티가 나면 저품질로 분류된다. 실제 경험·구체적 장면·솔직한 한계를 섞어 사람이 쓴 글처럼 만든다.
- 키워드 남용 금지: 같은 키워드를 억지로 반복하지 않는다. 자연스러운 문맥 안에서 핵심어가 녹아들게 한다.

[어법]
- 한국어 원어민이 한 번에 이해되는 자연스러운 문장만 쓴다. 어색하면 자극을 줄여서라도 자연스럽게.
- 추상 명사에 물리 동사 금지("복리가 굴러간다" X). 비유 오용 금지.
- AI 클리셰 금지: "~의 모든 것", "결정적", "게임체인저", "~하는 방법" 같은 교과서·광고 상투어.
"""


# ==========================================
# 탭 1 — 키워드 도우미
# ==========================================
def tab_keywords():
    st.markdown("### 🔍 키워드 도우미")
    st.caption("전자책 주제를 넣으면 파생 블로그 키워드 30개를 검색의도별로 분류해줍니다.")

    topic = st.text_input(
        "전자책 주제 / 핵심 키워드",
        placeholder="예: AI로 전자책 만들어 크몽에서 파는 법",
        key="kw_topic"
    )

    if st.button("키워드 30개 뽑기", key="kw_btn", use_container_width=True):
        if not topic.strip():
            st.warning("주제를 입력해주세요.")
        else:
            with st.spinner("검색 키워드 분석 중..."):
                prompt = f"""너는 네이버 블로그 SEO 전문가다. 아래 주제로 블로그를 운영하는 사람이
노릴 만한 검색 키워드 30개를 뽑고, 검색의도별로 분류해라.

[주제]: {topic}

[분류 기준 — 검색의도]
- 정보형: 방법·이유·개념을 알고 싶은 키워드 (구매 전 단계)
- 비교형: A vs B, 추천, 후기 등 선택을 고민하는 키워드 (구매 직전)
- 구매형: 가격·신청·시작 등 행동 직전 키워드 (전환 단계)

[규칙]
- 실제 사람이 네이버에 칠 법한 자연스러운 검색어로. (억지 조합 금지)
- 경쟁이 덜하면서 전자책 판매로 이어질 '롱테일' 키워드를 우선한다.
- 각 키워드에 한 줄 메모(왜 이 키워드가 전자책 판매에 좋은지)를 붙인다.

JSON만 출력:
{{
  "정보형": [{{"keyword": "...", "memo": "..."}}, ...],
  "비교형": [{{"keyword": "...", "memo": "..."}}, ...],
  "구매형": [{{"keyword": "...", "memo": "..."}}, ...]
}}"""
                result = ask_ai(prompt, temperature=0.6, max_tokens=3000)
                data = parse_json(result)
                if data:
                    st.session_state['kw_result'] = data
                    st.session_state['kw_topic_saved'] = topic
                else:
                    st.error("키워드 생성에 실패했습니다. 다시 시도해주세요.")

    # 결과 표시
    if st.session_state.get('kw_result'):
        data = st.session_state['kw_result']
        labels = {"정보형": "📘 정보형 (구매 전)", "비교형": "⚖️ 비교형 (구매 직전)", "구매형": "🛒 구매형 (전환)"}
        for cat in ["정보형", "비교형", "구매형"]:
            items = data.get(cat, [])
            if not items:
                continue
            st.markdown(f"#### {labels.get(cat, cat)}")
            for it in items:
                kw = it.get('keyword', '')
                memo = it.get('memo', '')
                st.markdown(
                    f'<div class="result-box" style="padding:14px 20px;margin:8px 0;">'
                    f'<b style="color:var(--teal);">{html.escape(kw)}</b><br>'
                    f'<span style="color:var(--text2);font-size:14px;">{html.escape(memo)}</span></div>',
                    unsafe_allow_html=True
                )
        st.info("💡 마음에 드는 키워드를 '블로그 생성기' 탭의 주제 칸에 넣어 글을 만들어보세요.")


# ==========================================
# 탭 2 — 블로그 생성기 (메인)
# ==========================================
def tab_blog():
    st.markdown("### ✍️ 블로그 글 생성기")
    st.caption("자청 후킹 + 논문급 근거 구조. 2026 네이버 알고리즘(C-Rank·D.I.A+)에 맞춰 작성됩니다.")

    col1, col2 = st.columns([1, 1])
    with col1:
        topic = st.text_input(
            "글 주제 / 타겟 키워드",
            value=st.session_state.get('kw_topic_saved', ''),
            placeholder="예: 직장인이 퇴근 후 전자책으로 부수입 만드는 법",
            key="blog_topic"
        )
    with col2:
        length = st.selectbox(
            "글 길이",
            ["표준 (1500자 내외)", "롱폼 (2500자 내외)", "숏폼 (800자 내외)"],
            key="blog_length"
        )

    reader = st.text_input(
        "타겟 독자 (구체적일수록 좋아요)",
        placeholder="예: 월급 280만원 7년차 직장인, 부업은 하고 싶은데 뭘 팔지 모르는 사람",
        key="blog_reader"
    )

    ref_url = st.text_area(
        "(선택) 벤치마킹할 인기 블로그 글 — 본문을 붙여넣으면 구조·톤을 분석해 반영합니다",
        placeholder="상위노출된 인기 글의 본문을 여기에 붙여넣으세요. (없으면 비워두세요)",
        height=100,
        key="blog_ref"
    )

    cta = st.text_input(
        "(선택) 글 끝에 넣을 전환 문구 / 전자책 소개",
        placeholder="예: 이 과정을 처음부터 끝까지 담은 전자책을 준비했습니다.",
        key="blog_cta"
    )

    if st.button("블로그 글 생성", key="blog_btn", use_container_width=True):
        if not topic.strip():
            st.warning("주제를 입력해주세요.")
        else:
            with st.spinner("글 작성 중... (논문급 근거 구조라 30초~1분 걸릴 수 있어요)"):
                length_map = {
                    "표준 (1500자 내외)": "1500자 내외",
                    "롱폼 (2500자 내외)": "2500자 내외",
                    "숏폼 (800자 내외)": "800자 내외",
                }
                length_str = length_map.get(length, "1500자 내외")
                reader_block = f"\n[타겟 독자]\n{reader}\n" if reader.strip() else ""
                ref_block = (
                    f"\n[벤치마킹 글 — 이 글의 구조·톤·문단 호흡을 분석해 반영하라. 단 내용은 베끼지 말 것]\n{ref_url}\n"
                    if ref_url.strip() else ""
                )
                cta_block = f"\n[글 끝 전환 문구]\n{cta}\n" if cta.strip() else ""

                prompt = f"""너는 네이버 블로그에서 전자책을 파는 콘텐츠 마케터다.
아래 주제로 블로그 글 한 편을 완성해라.

[주제]: {topic}
[목표 길이]: {length_str}
{reader_block}{ref_block}{cta_block}
{STYLE_CORE}

[글 구조 — 이 순서로]
1. 후킹 도입 (3~4줄): 독자의 현재 상황·고민을 정확히 짚어 "내 얘기다" 싶게. 통념을 한 번 뒤집어라.
2. 문제 정의: 왜 대부분이 여기서 실패하는지, 근거와 함께.
3. 본론 (핵심): 해결의 큰 줄기를 단계·근거·구체적 수치와 함께. 소제목으로 나눠 가독성을 높여라.
4. 실전 디테일: 바로 적용할 수 있는 구체적 행동 1~2개. (단, 전자책에서 다룰 핵심 디테일은 살짝 남겨둬라)
5. 마무리 + 전환: 핵심을 정리하고, 전환 문구가 있으면 자연스럽게 연결.

[형식]
- 소제목은 ■ 또는 숫자로 구분해 스캔이 쉽게.
- 한 문단은 2~4줄. 모바일에서 읽기 쉽게 짧게 끊어라.
- 과장·낚시 금지. 진짜 도움이 되는 정보로 신뢰를 쌓아라.
- 글 맨 위에 추천 제목 3개를 먼저 제안하라. (검색 키워드가 앞쪽에 들어간 제목)

[출력]
추천 제목 3개 → 본문 순서로. 다른 설명·주석 없이 글만 출력."""
                result = ask_ai(prompt, temperature=0.85, max_tokens=4000)
                if result:
                    st.session_state['blog_result'] = result

    if st.session_state.get('blog_result'):
        st.markdown("---")
        st.markdown("#### 📝 완성된 글")
        copy_block(st.session_state['blog_result'], key="blog_output")
        st.info("💡 이 글을 'SNS 변환기' 탭으로 가져가면 스레드·인스타·X용으로 쪼갤 수 있어요.")


# ==========================================
# 탭 3 — SNS 변환기
# ==========================================
def tab_sns():
    st.markdown("### 📱 SNS 변환기")
    st.caption("블로그 글을 스레드·인스타 카드뉴스·X(트위터)용으로 분해합니다.")

    source = st.text_area(
        "원본 글 (블로그 생성기 결과를 붙여넣거나, 직접 입력)",
        value=st.session_state.get('blog_result', ''),
        height=180,
        key="sns_source"
    )

    channels = st.multiselect(
        "변환할 채널",
        ["스레드(Threads)", "인스타 카드뉴스", "X(트위터)"],
        default=["스레드(Threads)", "인스타 카드뉴스"],
        key="sns_channels"
    )

    if st.button("SNS용으로 변환", key="sns_btn", use_container_width=True):
        if not source.strip():
            st.warning("원본 글을 입력해주세요.")
        elif not channels:
            st.warning("변환할 채널을 하나 이상 선택해주세요.")
        else:
            ch_specs = {
                "스레드(Threads)": "스레드: 첫 줄이 후킹. 짧은 문장 5~8개로 끊어서. 1개 글당 500자 이내. 마지막에 자연스러운 행동 유도.",
                "인스타 카드뉴스": "인스타 카드뉴스: 표지 1장(강한 후킹 한 문장) + 내용 카드 5~7장. 각 카드는 한 줄 제목 + 2~3줄 설명. 마지막 카드는 전환 유도.",
                "X(트위터)": "X 스레드: 첫 트윗이 후킹(280자 이내). 이어지는 트윗 4~6개로 핵심 전개. 각 트윗 280자 이내. 번호 매기기(1/n).",
            }
            selected_specs = "\n".join(f"- {ch_specs[c]}" for c in channels)
            with st.spinner("채널별로 변환 중..."):
                prompt = f"""너는 SNS 콘텐츠 전문가다. 아래 원본 글의 핵심 메시지를 유지하면서
선택된 채널 각각의 특성에 맞게 변환해라.

[원본 글]
{source}

[변환할 채널과 규칙]
{selected_specs}

[공통 규칙]
- 채널마다 톤을 다르게. 같은 내용을 그대로 복붙하지 마라.
- 첫 문장은 무조건 후킹. 스크롤을 멈추게 만들어라.
- 과장·낚시 금지. 읽고 나면 도움이 됐다고 느끼게.
- 해시태그는 채널당 3~5개, 실제로 검색될 법한 것만.

[출력 형식]
선택된 각 채널을 ===== 채널명 ===== 으로 구분해서 차례로 출력.
다른 설명 없이 변환 결과만."""
                result = ask_ai(prompt, temperature=0.85, max_tokens=4000)
                if result:
                    st.session_state['sns_result'] = result

    if st.session_state.get('sns_result'):
        st.markdown("---")
        st.markdown("#### 📤 변환 결과")
        copy_block(st.session_state['sns_result'], key="sns_output")


# ==========================================
# 탭 4 — 후킹 자산 생성기
# ==========================================
def tab_assets():
    st.markdown("### 🎯 후킹 자산 생성기")
    st.caption("글 도입부나 핵심 메시지를 → 광고 카피·이메일 제목·유튜브 쇼츠 대본으로.")

    source = st.text_area(
        "소재 (블로그 도입부, 핵심 메시지, 또는 전자책 주제)",
        value=st.session_state.get('blog_result', '')[:500] if st.session_state.get('blog_result') else '',
        height=150,
        key="asset_source"
    )

    asset_types = st.multiselect(
        "만들 자산",
        ["광고 카피 (메타/인스타)", "이메일 제목", "유튜브 쇼츠 대본(60초)"],
        default=["광고 카피 (메타/인스타)", "이메일 제목"],
        key="asset_types"
    )

    if st.button("후킹 자산 생성", key="asset_btn", use_container_width=True):
        if not source.strip():
            st.warning("소재를 입력해주세요.")
        elif not asset_types:
            st.warning("만들 자산을 하나 이상 선택해주세요.")
        else:
            specs = {
                "광고 카피 (메타/인스타)": "광고 카피: 스크롤을 멈추는 첫 줄 + 본문 2~3줄 + CTA. 5세트 제안. 각각 다른 각도(공포/호기심/이득/사회증명/통념박살).",
                "이메일 제목": "이메일 제목: 열어보고 싶게 만드는 제목 10개. 길이 다양하게. 각 제목 옆에 어떤 심리를 노렸는지 한 단어 메모.",
                "유튜브 쇼츠 대본(60초)": "쇼츠 대본: 첫 3초 후킹 + 본론 40초 + 마지막 행동유도. 말로 읽는 대본체. 화면 자막 표시도 [자막] 으로 함께.",
            }
            selected = "\n".join(f"- {specs[a]}" for a in asset_types)
            with st.spinner("후킹 자산 만드는 중..."):
                prompt = f"""너는 전자책을 파는 퍼포먼스 마케터이자 카피라이터다.
아래 소재로 선택된 마케팅 자산을 만들어라.

[소재]
{source}

[만들 자산과 규칙]
{selected}

[공통 규칙]
- 첫 한 줄이 전부다. 스크롤·시선을 멈추게.
- 과장·허위 금지. 그러나 심심하지 않게. 자청식으로 통념을 뒤집거나 독자를 정확히 저격.
- 한국어 어법이 자연스러워야 한다. 어색하면 자극을 줄여서라도 자연스럽게.

[출력 형식]
선택된 각 자산을 ===== 자산명 ===== 으로 구분해 차례로 출력. 설명 없이 결과만."""
                result = ask_ai(prompt, temperature=0.9, max_tokens=4000)
                if result:
                    st.session_state['asset_result'] = result

    if st.session_state.get('asset_result'):
        st.markdown("---")
        st.markdown("#### 🎁 생성된 자산")
        copy_block(st.session_state['asset_result'], key="asset_output")


# ==========================================
# MAIN
# ==========================================
def main():
    # 헤더
    st.markdown("""
    <div class="hero">
        <span class="badge">CASHMAKER · 마케팅 통합기</span>
        <h1>📣 MarketKit</h1>
        <p style="color:var(--text2);">전자책 하나로 블로그·SNS·광고 콘텐츠를 한 번에</p>
    </div>
    """, unsafe_allow_html=True)

    authed = render_sidebar()
    if not authed:
        st.info("👈 사이드바에서 비밀번호를 입력해 시작하세요.")
        st.markdown("""
        <div class="result-box">
        <h3>MarketKit으로 할 수 있는 것</h3>
        <p>① <b>키워드 도우미</b> — 주제 하나로 검색 키워드 30개를 의도별로 분류<br>
        ② <b>블로그 생성기</b> — 자청 후킹 + 논문급 근거로 2026 네이버 알고리즘 대응 글<br>
        ③ <b>SNS 변환기</b> — 블로그 글을 스레드·인스타·X로 분해<br>
        ④ <b>후킹 자산</b> — 광고 카피·이메일 제목·쇼츠 대본까지</p>
        </div>
        """, unsafe_allow_html=True)
        return

    if not st.session_state.get('api_key'):
        st.warning("👈 사이드바에 Claude API 키를 입력하면 모든 기능이 켜집니다.")

    # 탭
    t1, t2, t3, t4 = st.tabs(["🔍 키워드 도우미", "✍️ 블로그 생성기", "📱 SNS 변환기", "🎯 후킹 자산"])
    with t1:
        tab_keywords()
    with t2:
        tab_blog()
    with t3:
        tab_sns()
    with t4:
        tab_assets()

    st.markdown("""
    <div class="footer">
        <span style="color:#C9A24B;">CASHMAKER</span> · MarketKit | 제작: <span style="color:#fff;">남현우</span>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
