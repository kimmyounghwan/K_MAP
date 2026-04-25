import streamlit as st
import pandas as pd
import requests
import pyrebase
import urllib3
import urllib.parse
from datetime import datetime, timedelta, timezone
import time
import re
import os

# ==========================================
# 1. 보안 및 페이지 설정
# ==========================================
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="K-건설맵 Master", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
        <meta name="naver-site-verification" content="bfb3f10bce2983b4dd5974ba39d05e3ce5225e73" />
        <meta name="description" content="K-건설맵: 전국 건설 공사 입찰 및 실시간 1순위 개찰 결과를 즉시 확인하세요.">
    </head>
    <style>
        /* 모바일 화면 흔들림 및 줌 방지 */
        html, body { overflow-x: hidden; overscroll-behavior-x: none; touch-action: pan-y; }

        .stApp[data-teststate="running"] .stAppViewBlockContainer { filter: none !important; opacity: 1 !important; }
        [data-testid="stStatusWidget"] { visibility: hidden !important; display: none !important; }
        .stApp { transition: none !important; }
        .main-title { background-color: #1e3a8a; color: white; border-radius: 10px; font-weight: 900; font-size: 28px; text-align: center; padding: 20px; margin-bottom: 25px; }
        .stat-card { background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; text-align: center; margin-bottom: 10px; }
        .stat-label { font-size: 13px; color: #64748b; font-weight: 600; margin-bottom: 4px; }
        .stat-val { font-size: 17px; font-weight: 800; color: #1e3a8a; }
        .calc-badge { font-size: 10px; color: #ea580c; font-weight: 700; margin-top: 3px; }
        .guide-box { background-color: #eff6ff; border-left: 4px solid #3b82f6; padding: 12px; border-radius: 5px; margin-bottom: 15px; font-size: 14px; color: #1e3a8a; }
    </style>
""", unsafe_allow_html=True)

KST = timezone(timedelta(hours=9))

# ==========================================
# 2. 파이어베이스 & G드라이브 보물창고 셋팅
# ==========================================
firebaseConfig = {
    "apiKey": "AIzaSyB5uvAzUIbEDTTbxwflTQk3wdzOufc4SE0",
    "authDomain": "k-conmap.firebaseapp.com",
    "databaseURL": "https://k-conmap-default-rtdb.firebaseio.com",
    "projectId": "k-conmap",
    "storageBucket": "k-conmap.firebasestorage.app",
    "messagingSenderId": "230642116525",
    "appId": "1:230642116525:web:f6f3765cf9a7273ba92324"
}
G2B_API_KEY = "13610863df3680cc4e7c70a64d752b37485535929bfa514f4ad4d71ea56e4ccb"
SAFE_API_KEY = urllib.parse.unquote(G2B_API_KEY)


@st.cache_resource
def init_firebase():
    firebase = pyrebase.initialize_app(firebaseConfig)
    return firebase.auth(), firebase.database()


auth, db = init_firebase()

for k, v in [('logged_in', False), ('user_name', ""), ('user_license', ""), ('user_phone', ""), ('localId', ""),
             ('idToken', "")]:
    if k not in st.session_state: st.session_state[k] = v

# [핵심] 노트북 G드라이브 마스터 데이터 로드 (분석용)
MASTER_DATA_PATH = r"G:\내 드라이브\K-건설맵_데이터\bid_data_3years.csv"


@st.cache_data(show_spinner=False)
def load_master_data():
    try:
        if os.path.exists(MASTER_DATA_PATH):
            return pd.read_csv(MASTER_DATA_PATH, encoding='utf-8-sig')
        return None
    except Exception as e:
        return None


big_data = load_master_data()


# ==========================================
# 3. 방문 누적 카운팅 로직
# ==========================================
def update_stats():
    if 'visited' not in st.session_state:
        try:
            curr = db.child("stats").child("total_visits").get().val()
            if curr is None: curr = 1828
            db.child("stats").update({"total_visits": curr + 1})
            st.session_state['visited'] = True
        except:
            pass


def get_stats():
    try:
        t_v = db.child("stats").child("total_visits").get().val() or 1828
        u_v = db.child("users").get().val()
        return t_v, len(u_v) if u_v else 0
    except:
        return 1828, 0


# ==========================================
# 4. 유틸리티 함수
# ==========================================
REGION_LIST = ["전국(전체)", "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남",
               "제주"]
ALL_LICENSES = ["[종합] 건축공사업", "[종합] 토목공사업", "[종합] 토목건축공사업", "[종합] 조경공사업", "[전문] 지반조성·포장공사업", "[전문] 실내건축공사업",
                "[전문] 철근·콘크리트공사업", "[기타] 전기공사업", "[기타] 정보통신공사업", "[기타] 소방시설공사업"]
BASE = 'http://apis.data.go.kr/1230000'


def filter_by_region(df, sel):
    if sel == "전국(전체)": return df
    rk = {"서울": ["서울"], "부산": ["부산"], "대구": ["대구"], "인천": ["인천"], "광주": ["광주"], "대전": ["대전"], "울산": ["울산"],
          "세종": ["세종"], "경기": ["경기", "경기도"], "강원": ["강원", "강원도"], "충북": ["충북", "충청북도"], "충남": ["충남", "충청남도"],
          "전북": ["전북", "전라북도"], "전남": ["전남", "전라남도"], "경북": ["경북", "경상북도"], "경남": ["경남", "경상남도"], "제주": ["제주"]}
    pat = '|'.join(rk.get(sel, [sel]))
    return df[df['발주기관'].str.contains(pat, na=False) | df['공고명'].str.contains(pat, na=False)]


def raw_to_int(raw) -> int:
    if raw is None: return 0
    r = str(raw).strip().replace(',', '').replace('원', '').replace('%', '')
    try:
        return int(float(r))
    except:
        return 0


def fmt_amt(v: int) -> str:
    return f"{v:,}원" if v > 0 else ''


def get_match_keywords(lic):
    k = []
    if "토목" in lic: k.extend(["토목", "도로", "포장", "하천", "교량", "정비", "관로", "상수도", "하수도"])
    if "건축" in lic: k.extend(["건축", "신축", "증축", "보수", "인테리어", "방수", "도장"])
    if "조경" in lic: k.extend(["조경", "식재", "공원", "수목"])
    if "전기" in lic: k.extend(["전기", "배전", "가로등", "CCTV"])
    if "통신" in lic: k.extend(["통신", "네트워크", "방송"])
    if "소방" in lic: k.extend(["소방", "화재", "스프링클러"])
    if "철근" in lic or "콘크리트" in lic: k.extend(["철콘", "구조물", "옹벽", "배수", "기초"])
    return list(set(k))


# ==========================================
# 5. 데이터 팝업창 (조달청 삭제 -> 100% 역산 & 팩트 분석 탑재)
# ==========================================
@st.dialog("📋 K-건설맵 정밀 리포트", width="large")
def show_analysis_dialog(row, det, mode="1st"):
    if mode == "1st":
        st.markdown(f"### {row['공고명']}")
        m1, m2, m3, m4 = st.columns(4)

        def _card(col, icon, label, val, key, val_color="#1e3a8a"):
            badge = {'CALC': '🧮 역산추정'}.get(det['sources'].get(key, ''), '')
            col.markdown(
                f'<div class="stat-card"><div class="stat-label">{icon} {label}</div><div class="stat-val" style="color:{val_color};">{val if val else "-"}</div><div class="calc-badge">{badge}</div></div>',
                unsafe_allow_html=True)

        _card(m1, "💰", "기초금액(추정)", det['bss_amt'], 'bss')
        _card(m2, "📐", "추정가격(추정)", det['est_price'], 'est')
        _card(m3, "🎯", "예정가격", det['pre_amt'], 'pre')
        _card(m4, "🏆", "낙찰금액", det['suc_amt'], 'suc', "#dc2626")

        st.caption("* 🧮 표시는 조달청 데이터가 아닌 1순위 투찰금액과 투찰률을 바탕으로 역산한 '나노 AI 추정치'입니다. (예정가격 = 투찰금액 ÷ 투찰률)")

        if det['corps']:
            st.write("**[개찰 결과 성적표]**")
            st.dataframe(pd.DataFrame(det['corps']), use_container_width=True, hide_index=True)

        if 'big_data' in globals() and big_data is not None and not big_data.empty:
            st.markdown("---")
            st.markdown(f"#### 📊 [팩트 통계] 3년 누적 데이터 분석 리포트")

            col_ana1, col_ana2 = st.columns(2)

            with col_ana1:
                st.markdown(f"**🏢 '{row['1순위업체']}' 낙찰 이력**")
                corp_data = big_data[big_data['1순위업체'] == row['1순위업체']]
                if not corp_data.empty:
                    st.write(f"- **최근 3년 누적 1순위:** `{len(corp_data)}회`")
                    # 사정률이 있으면 사정률, 없으면 투찰률로 분석
                    rate_col = '사정률' if '사정률' in corp_data.columns else '투찰률'
                    if rate_col in corp_data.columns:
                        rates = corp_data[rate_col].value_counts()
                        if not rates.empty:
                            st.write(f"- **최다 낙찰 {rate_col}:** `{rates.index[0]}` (총 {rates.iloc[0]}회 낙찰)")
                else:
                    st.write("- 검색된 과거 1순위 이력 없음")

            with col_ana2:
                st.markdown(f"**🏛️ '{row['발주기관']}' 발주 통계**")
                inst_data = big_data[big_data['발주기관'] == row['발주기관']]
                if not inst_data.empty:
                    st.write(f"- **최근 3년 누적 공고수:** `{len(inst_data)}건`")
                    rate_col = '사정률' if '사정률' in inst_data.columns else '투찰률'
                    if rate_col in inst_data.columns:
                        i_rates = inst_data[rate_col].value_counts()
                        if not i_rates.empty:
                            st.write(f"- **가장 많이 1순위가 나온 {rate_col}:** `{i_rates.index[0]}` (총 {i_rates.iloc[0]}회 발생)")
                else:
                    st.write("- 검색된 과거 발주 이력 없음")

        st.markdown("---")
        sc1, sc2 = st.columns(2)
        with sc1:
            st.markdown("💡 **나라장터 정책상 번호 복사가 필요합니다.**")
            st.code(row['공고번호'], language=None)
        with sc2:
            st.write("")
            st.link_button("🚀 나라장터 홈페이지", "https://www.g2b.go.kr/index.jsp", use_container_width=True)
            st.link_button("🏢 업체 네이버 검색", f"https://search.naver.com/search.naver?query={row['1순위업체']} 건설",
                           use_container_width=True)

    elif mode == "live":
        # 실시간 공고 팝업: 오직 팩트 데이터(업체 TOP 5, 사정률 TOP 5)만 남김
        st.markdown(f"### 🎯 실시간 공고 발주처 팩트 분석")
        st.write(f"**공고명:** {row['공고명']}")

        if 'big_data' in globals() and big_data is not None and not big_data.empty:
            st.markdown("---")
            st.markdown(f"#### 📊 [입찰 준비] '{row['발주기관']}' 최근 3년 낙찰 팩트 리포트")

            inst_data = big_data[big_data['발주기관'] == row['발주기관']]
            if not inst_data.empty:
                st.write(f"최근 3년간 **{row['발주기관']}**에서 발주한 총 **{len(inst_data)}건**의 1순위 데이터를 분석한 팩트 결과입니다.")

                col_f1, col_f2 = st.columns(2)

                # 1. 팩트: 최다 낙찰 업체 TOP 5
                with col_f1:
                    st.markdown("**🏆 최다 낙찰 업체 TOP 5**")
                    if '1순위업체' in inst_data.columns:
                        top_corps = inst_data['1순위업체'].value_counts().head(5)
                        for i, (corp, count) in enumerate(top_corps.items()):
                            st.info(f"**{i + 1}위:** {corp} (`{count}회`)")

                # 2. 팩트: 최다 발생 사정률(투찰률) TOP 5
                with col_f2:
                    st.markdown("**🎯 최다 발생 사정률(투찰률) TOP 5**")
                    rate_col = '사정률' if '사정률' in inst_data.columns else '투찰률'
                    if rate_col in inst_data.columns:
                        valid_rates = inst_data[inst_data[rate_col].astype(str).str.contains(r'\d', na=False)]
                        top_rates = valid_rates[rate_col].value_counts().head(5)
                        for i, (rate, count) in enumerate(top_rates.items()):
                            st.success(f"**{i + 1}위:** {rate} (`{count}회`)")

                st.caption("* 위 통계는 3년 치 팩트 데이터입니다. 사정률 데이터가 없을 경우 투찰률 기준으로 표시됩니다. 입찰 전략 수립 시 참고하세요.")
            else:
                st.info(f"'{row['발주기관']}'의 최근 3년 개찰 이력 데이터가 없습니다. (신규 발주처이거나 이력이 부족합니다.)")

    elif mode == "job":
        st.markdown(f"### 🤝 구인/구직 상세내용")
        st.write(f"**제목:** {row['title']} | **지역:** {row['region']}")
        st.write(f"**작성자:** {row['author']} | **연락처:** {row['phone']}")
        st.markdown("---")
        st.write(row['content'])


# ==========================================
# 6. 데이터 수집 엔진 (조달청 API 제거 -> 100% 파이어베이스)
# ==========================================
@st.cache_data(ttl=60, show_spinner=False)
def get_hybrid_1st_bids():
    db_data = db.child("archive_1st").order_by_key().limit_to_last(4000).get().val() or {}
    db_items = list(db_data.values()) if isinstance(db_data, dict) else []

    df = pd.DataFrame(db_items)
    if not df.empty:
        df = df.drop_duplicates(subset=['공고번호']).copy()
        df['dt'] = pd.to_datetime(df['날짜'], errors='coerce')
        df = df.sort_values(by='dt', ascending=False)
        df['날짜'] = df['dt'].dt.strftime('%m-%d %H:%M')
    return df


@st.cache_data(ttl=180, show_spinner=False)
def get_hybrid_live_bids():
    db_data = db.child("archive_live").order_by_key().limit_to_last(4000).get().val() or {}
    db_items = list(db_data.values()) if isinstance(db_data, dict) else []

    df = pd.DataFrame(db_items)
    if not df.empty:
        df = df.drop_duplicates(subset=['공고번호']).copy()
        df['dt'] = pd.to_datetime(df['공고일자'], errors='coerce')
        df = df.sort_values(by='dt', ascending=False)
        df['공고일자'] = df['dt'].dt.strftime('%m-%d %H:%M')
    return df


def fetch_detail(row):
    # 명환이의 수학 공식: 투찰금액 / 투찰률 = 예정가격. 조달청 API 일절 안 씀!
    res = {'bss_amt': '', 'est_price': '', 'pre_amt': '', 'sources': {}}

    suc_v = raw_to_int(row.get('투찰금액', ''))
    rate_s = str(row.get('투찰률', '')).replace('%', '').strip()
    rate_v = float(rate_s) if rate_s and rate_s != '-' else 0

    if suc_v > 0 and rate_v > 0:
        pre_calc = int(round(suc_v / (rate_v / 100.0)))
        res['pre_amt'] = fmt_amt(pre_calc)
        res['sources']['pre'] = 'CALC'

        res['bss_amt'] = fmt_amt(pre_calc)
        res['sources']['bss'] = 'CALC'

        res['est_price'] = fmt_amt(int(round(pre_calc / 1.1)))
        res['sources']['est'] = 'CALC'

    res['suc_amt'] = row.get('투찰금액', '-')
    corps = []
    corp_raw = row.get('전체업체', '')
    if corp_raw:
        for idx, c in enumerate(str(corp_raw).split('|')[:10]):
            p = c.split('^')
            if len(p) >= 5: corps.append(
                {'순위': f"{idx + 1}위", '업체명': p[0].strip(), '투찰금액': f"{int(float(p[3])):,}원", '투찰률': f"{p[4].strip()}%"})
    res['corps'] = corps
    return res


# ==========================================
# 7. UI 대시보드
# ==========================================
update_stats()
t_visit, u_total = get_stats()

st.markdown('<div class="main-title">🏛️ K-건설맵 Master</div>', unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
with c1: st.markdown(
    f'<div class="stat-card"><div class="stat-label">📅 오늘 날짜</div><div class="stat-val">{datetime.now(KST).strftime("%Y-%m-%d")}</div></div>',
    unsafe_allow_html=True)
with c2: st.markdown(
    f'<div class="stat-card"><div class="stat-label">📈 누적 방문</div><div class="stat-val">{t_visit:,}명</div></div>',
    unsafe_allow_html=True)
with c3: st.markdown(
    f'<div class="stat-card"><div class="stat-label">👥 전체 회원수</div><div class="stat-val">{u_total:,}명</div></div>',
    unsafe_allow_html=True)
with c4: st.markdown(
    f'<div class="stat-card"><div class="stat-label">🔔 가동 상태</div><div class="stat-val" style="color:green;">정상 가동 중</div></div>',
    unsafe_allow_html=True)

with st.sidebar:
    st.write(f"### 👷 {'👋 ' + st.session_state['user_name'] + ' 소장님' if st.session_state['logged_in'] else 'K-건설맵 메뉴'}")

    menu = st.radio("업무 선택",
                    ["🏆 1순위 현황판", "📊 실시간 공고 (홈)", "🤝 K-구인구직", "📁 K-건설 자료실", "💬 K건설챗", "📲 앱처럼 설치하기", "👤 내 정보/로그인"])
    st.write("---")

    if st.session_state['logged_in'] and st.button("🚪 로그아웃"):
        st.session_state.clear()
        st.rerun()

# ==========================================
# 8. 메뉴 라우팅
# ==========================================
ROWS_PER_PAGE = 20

if menu == "🏆 1순위 현황판":
    st.markdown("#### 🏆 실시간 1순위 현황판")

    st.markdown("""
        <div class="guide-box">
            💡 <b>터치 한 번으로 정밀 분석!</b><br>
            아래 리스트 맨 왼쪽의 <b>[체크박스(ㅁ)]</b>를 터치해 보세요. 역산된 상세 리포트가 즉시 열립니다.
        </div>
    """, unsafe_allow_html=True)

    df_w = get_hybrid_1st_bids()
    if not df_w.empty:
        col_f1, col_f2 = st.columns([1, 2])
        with col_f1:
            sel_reg = st.selectbox("🌍 지역 필터링", REGION_LIST, key="reg1")
        with col_f2:
            search_co = st.text_input("🏢 업체명 검색", placeholder="낙찰 업체명을 입력하세요", key="search_main")

        df_f = filter_by_region(df_w, sel_reg)
        if search_co: df_f = df_f[df_f['1순위업체'].str.contains(search_co, na=False)]

        num_pages = max(1, (len(df_f) // ROWS_PER_PAGE) + (1 if len(df_f) % ROWS_PER_PAGE > 0 else 0))
        if "p1" not in st.session_state: st.session_state["p1"] = 1

        start_idx = (st.session_state["p1"] - 1) * ROWS_PER_PAGE
        df_page = df_f.iloc[start_idx: start_idx + ROWS_PER_PAGE]
        event = st.dataframe(df_page[['1순위업체', '날짜', '공고명', '발주기관', '투찰금액', '투찰률']], use_container_width=True,
                             hide_index=True, height=700, selection_mode="single-row", on_select="rerun")

        st.write("")
        c_p1, c_p2, c_p3 = st.columns([3, 4, 3])
        with c_p2:
            st.selectbox(f"📄 페이지 이동 (총 {num_pages}쪽)", range(1, num_pages + 1), key="p1")

        if len(event.selection.rows) > 0:
            selected_row = df_page.iloc[event.selection.rows[0]]
            det = fetch_detail(selected_row)
            show_analysis_dialog(selected_row, det, mode="1st")

elif menu == "📊 실시간 공고 (홈)":
    st.markdown("#### 📊 실시간 입찰 공고")

    st.markdown("""
        <div class="guide-box">
            💡 <b>입찰 팩트 리포트 확인!</b><br>
            아래 리스트 맨 왼쪽의 <b>[체크박스(ㅁ)]</b>를 터치해 보세요. 해당 발주기관의 과거 3년 낙찰 팩트가 열립니다.
        </div>
    """, unsafe_allow_html=True)

    df_live = get_hybrid_live_bids()
    if not df_live.empty:
        df_f = filter_by_region(df_live, st.selectbox("🌍 지역 필터링", REGION_LIST, key="reg2"))
        col_cfg = {"상세보기": st.column_config.LinkColumn("상세보기", display_text="공고보기"),
                   "예산금액": st.column_config.NumberColumn("예산(원)", format="%,d")}

        if st.session_state['logged_in']:
            t1, t2 = st.tabs(["🌐 전체 공고", "✨ 내 면허 맞춤매칭"])
            with t1:
                n_all = max(1, (len(df_f) // ROWS_PER_PAGE) + 1)
                if "p_all" not in st.session_state: st.session_state["p_all"] = 1
                df_p_all = df_f.iloc[
                    (st.session_state["p_all"] - 1) * ROWS_PER_PAGE: st.session_state["p_all"] * ROWS_PER_PAGE]
                event = st.dataframe(df_p_all[['공고번호', '공고일자', '공고명', '발주기관', '예산금액', '상세보기']],
                                     use_container_width=True, hide_index=True, height=700, column_config=col_cfg,
                                     selection_mode="single-row", on_select="rerun", key="live_all")
                c1, c2, c3 = st.columns([3, 4, 3])
                with c2: st.selectbox(f"📄 페이지 이동 (총 {n_all}쪽)", range(1, n_all + 1), key="p_all")
            with t2:
                kw = get_match_keywords(st.session_state.get('user_license', ''))
                m_full = df_f[df_f['공고명'].str.contains('|'.join(kw), na=False)] if kw else df_f
                n_m = max(1, (len(m_full) // ROWS_PER_PAGE) + 1)
                if "p_m" not in st.session_state: st.session_state["p_m"] = 1
                df_p_m = m_full.iloc[
                    (st.session_state["p_m"] - 1) * ROWS_PER_PAGE: st.session_state["p_m"] * ROWS_PER_PAGE]
                event_m = st.dataframe(df_p_m[['공고번호', '공고일자', '공고명', '발주기관', '예산금액', '상세보기']],
                                       use_container_width=True, hide_index=True, height=700, column_config=col_cfg,
                                       selection_mode="single-row", on_select="rerun", key="live_match")
                c1, c2, c3 = st.columns([3, 4, 3])
                with c2:
                    st.selectbox(f"📄 페이지 이동 (총 {n_m}쪽)", range(1, n_m + 1), key="p_m")
                if len(event_m.selection.rows) > 0: event, df_p_all = event_m, df_p_m
        else:
            n_g = max(1, (len(df_f) // ROWS_PER_PAGE) + 1)
            if "p_g" not in st.session_state: st.session_state["p_g"] = 1
            df_p_g = df_f.iloc[(st.session_state["p_g"] - 1) * ROWS_PER_PAGE: st.session_state["p_g"] * ROWS_PER_PAGE]
            event = st.dataframe(df_p_g[['공고번호', '공고일자', '공고명', '발주기관', '예산금액', '상세보기']], use_container_width=True,
                                 hide_index=True, height=700, column_config=col_cfg, selection_mode="single-row",
                                 on_select="rerun")
            c1, c2, c3 = st.columns([3, 4, 3])
            with c2:
                st.selectbox(f"📄 페이지 이동 (총 {n_g}쪽)", range(1, n_g + 1), key="p_g")
            df_p_all = df_p_g

        if len(event.selection.rows) > 0:
            show_analysis_dialog(df_p_all.iloc[event.selection.rows[0]], None, mode="live")

elif menu == "🤝 K-구인구직":
    st.markdown("#### 🤝 건설현장 구인구직")
    if st.session_state['logged_in']:
        with st.expander("📝 새 구인/구직 등록하기"):
            c1, c2 = st.columns(2)
            cat = c1.selectbox("분류", ["👷 사람 구합니다", "🚜 일자리 찾습니다"])
            reg = c2.selectbox("지역", REGION_LIST)
            jt = st.text_input("직종 (예: 철근공, 포크레인)")
            ph = st.text_input("연락처", value=st.session_state.get('user_phone', ''))
            ttl = st.text_input("제목")
            con = st.text_area("상세내용")
            if st.button("등록하기"):
                db.child("jobs").push(
                    {"category": cat, "region": reg, "job_type": jt, "phone": ph, "title": ttl, "content": con,
                     "author": st.session_state['user_name'], "time": datetime.now(KST).strftime("%m-%d %H:%M")})
                st.toast("등록 완료!")
                time.sleep(1)
                st.rerun()
    jobs_data = db.child("jobs").get().val()
    if jobs_data:
        df_j = pd.DataFrame(list(jobs_data.values())).iloc[::-1]
        t1, t2 = st.tabs(["👷 사람 구함", "🚜 일자리 찾음"])
        with t1:
            h = df_j[df_j['category'] == "👷 사람 구합니다"]
            ev_h = st.dataframe(h[['time', 'region', 'job_type', 'title', 'author']], use_container_width=True,
                                hide_index=True, selection_mode="single-row", on_select="rerun", key="h_job")
            if len(ev_h.selection.rows) > 0: show_analysis_dialog(h.iloc[ev_h.selection.rows[0]], None, mode="job")
        with t2:
            s = df_j[df_j['category'] == "🚜 일자리 찾습니다"]
            ev_s = st.dataframe(s[['time', 'region', 'job_type', 'title', 'author']], use_container_width=True,
                                hide_index=True, selection_mode="single-row", on_select="rerun", key="s_job")
            if len(ev_s.selection.rows) > 0: show_analysis_dialog(s.iloc[ev_s.selection.rows[0]], None, mode="job")

elif menu == "📲 앱처럼 설치하기":
    st.markdown("### 📲 스마트폰 바탕화면에 앱으로 추가하기")
    col1, col2 = st.columns(2)
    with col1:
        st.info("🍎 **아이폰 (Safari)**\n\n1. 하단 **[공유 버튼(□↑)]** 클릭\n2. **[홈 화면에 추가]** 클릭\n3. **[추가]** 클릭")
    with col2:
        st.success("🤖 **안드로이드 (Chrome)**\n\n1. 상단 **[점 3개(⋮)]** 클릭\n2. **[홈 화면에 추가]** 또는 **[앱 설치]** 클릭\n3. **[추가]** 클릭")

elif menu == "👤 내 정보/로그인":
    st.subheader("👤 회원 정보 관리")
    if not st.session_state['logged_in']:
        t1, t2 = st.tabs(["🔑 로그인", "📝 회원가입"])
        with t1:
            le = st.text_input("이메일")
            lp = st.text_input("비밀번호", type="password")
            if st.button("로그인"):
                try:
                    user = auth.sign_in_with_email_and_password(le.strip().lower(), lp)
                    info = db.child("users").child(user['localId']).get().val() or {}
                    st.session_state.update({'logged_in': True, 'user_name': info.get('name', '소장님'),
                                             'user_license': info.get('license', ''),
                                             'user_phone': info.get('phone', ''), 'localId': user['localId'],
                                             'idToken': user['idToken']})
                    st.rerun()
                except:
                    pass
        with t2:
            re = st.text_input("이메일 가입")
            rp = st.text_input("비번 (6자 이상)", type="password")
            rn = st.text_input("성함")
            rl = st.multiselect("보유 면허 (매칭용)", ALL_LICENSES)
            if st.button("가입하기"):
                try:
                    u = auth.create_user_with_email_and_password(re.strip().lower(), rp)
                    db.child("users").child(u['localId']).set({"name": rn, "license": ", ".join(rl), "email": re})
                    st.success("🎉 가입 성공!")
                except:
                    st.error("가입 실패!")
    else:
        st.write(f"### {st.session_state['user_name']} 소장님 반갑습니다!")
        if st.button("🚪 로그아웃"):
            st.session_state.clear()
            st.rerun()

elif menu == "📁 K-건설 자료실":
    st.subheader("📁 K-건설 자료실")
    if st.session_state['logged_in']:
        with st.expander("✏️ 새 자료 등록"):
            t, c = st.text_input("제목"), st.text_area("내용")
            if st.button("등록") and t and c:
                db.child("posts").push({"author": st.session_state['user_name'], "title": t, "content": c,
                                        "time": datetime.now(KST).strftime("%Y-%m-%d %H:%M")})
                st.rerun()
    posts = db.child("posts").get().val()
    if posts:
        for k, v in reversed(list(posts.items())):
            with st.expander(f"📢 {v['title']} (작성자: {v['author']})"): st.write(v['content'])

elif menu == "💬 K건설챗":
    st.subheader("💬 실시간 현장 소통")
    if st.session_state['logged_in']:
        chat_box = st.container(height=400)
        chats_data = db.child("k_chat").get().val()
        if chats_data:
            for v in list(chats_data.values())[-20:]: chat_box.write(f"**{v['author']}**: {v['message']}")
        if msg := st.chat_input("메시지 입력"):
            db.child("k_chat").push(
                {"author": st.session_state['user_name'], "message": msg, "time": datetime.now(KST).strftime("%H:%M")})
            st.rerun()
    else:
        st.info("로그인 후 이용 가능합니다.")