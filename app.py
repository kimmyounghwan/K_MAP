import streamlit as st
import pandas as pd
import pyrebase
import urllib3
import urllib.parse
from datetime import datetime, timedelta, timezone
import time
import os
import math
import re

# ==========================================
# 1. 페이지 설정
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
        html, body { overflow-x: hidden; overscroll-behavior-x: none; touch-action: pan-y; }
        .stApp[data-teststate="running"] .stAppViewBlockContainer { filter: none !important; opacity: 1 !important; }
        [data-testid="stStatusWidget"] { visibility: hidden !important; display: none !important; }
        .stApp { transition: none !important; }

        [data-testid="stSidebar"] .stRadio > div { gap: 0px !important; }
        [data-testid="stSidebar"] .stRadio label {
            padding: 10px 10px 10px 6px !important;
            font-size: 14px !important;
            font-weight: 600 !important;
            border-radius: 8px !important;
            margin-bottom: 3px !important;
            cursor: pointer;
            transition: background 0.15s;
        }
        [data-testid="stSidebar"] .stRadio label:hover {
            background: rgba(59,130,246,0.08) !important;
        }

        [data-testid="collapsedControl"] {
            background: linear-gradient(135deg, #1e3a8a, #1d4ed8) !important;
            border-radius: 50% !important;
            width: 52px !important;
            height: 52px !important;
            border: 3px solid #fde68a !important;
            box-shadow: 0 4px 16px rgba(30,58,138,0.7) !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }
        [data-testid="collapsedControl"] svg {
            color: #fde68a !important;
            fill: #fde68a !important;
            width: 26px !important;
            height: 26px !important;
        }
        button[kind="header"] {
            display: none !important;
            visibility: hidden !important;
            opacity: 0 !important;
            pointer-events: none !important;
            width: 0 !important;
            height: 0 !important;
            overflow: hidden !important;
        }
        .sidebar-toggle-hint { display: none !important; }

        .main-title { background-color: #1e3a8a; color: white; border-radius: 10px; font-weight: 900; font-size: 26px; text-align: center; padding: 18px; margin-bottom: 22px; }
        .stat-card { background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 11px; text-align: center; margin-bottom: 10px; }
        .stat-label { font-size: 12px; color: #64748b; font-weight: 600; margin-bottom: 4px; }
        .stat-val { font-size: 16px; font-weight: 800; color: #1e3a8a; }
        .guide-box { background-color: #eff6ff; border-left: 4px solid #3b82f6; padding: 11px; border-radius: 5px; margin-bottom: 14px; font-size: 13px; color: #1e3a8a; }

        .hit-zone { background: linear-gradient(135deg, #fef3c7, #fde68a); border: 2px solid #f59e0b; border-radius: 8px; padding: 11px; margin: 8px 0; text-align: center; font-weight: 800; font-size: 14px; color: #92400e; }
        .insight-box { background: #1e3a8a; color: white; border-radius: 10px; padding: 14px; margin: 8px 0; text-align: center; }
        .insight-title { font-size: 12px; font-weight: 700; margin-bottom: 6px; color: #93c5fd; }
        .insight-val { font-size: 21px; font-weight: 900; }
        .similar-card { background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 10px; margin: 5px 0; }
        .corp-rank1 { background: linear-gradient(135deg, #fef9c3, #fde047); border: 2px solid #eab308; border-radius: 8px; padding: 10px; margin: 4px 0; font-weight: 800; font-size: 13px; }
        .corp-rank-other { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 8px; margin: 3px 0; font-size: 12px; }
        .warn-box { background: #fef2f2; border: 2px solid #ef4444; border-radius: 8px; padding: 10px; margin: 6px 0; color: #7f1d1d; font-weight: 700; }
        .ok-box { background: #f0fdf4; border: 2px solid #22c55e; border-radius: 8px; padding: 10px; margin: 6px 0; color: #14532d; font-weight: 700; }
        .diag-box { background: #1e3a8a; color: white; border-radius: 10px; padding: 15px; margin: 8px 0; text-align: center; }
        .diag-title { font-size: 12px; color: #93c5fd; font-weight: 700; margin-bottom: 4px; }
        .diag-val { font-size: 19px; font-weight: 900; }
        .calc-result { background: linear-gradient(135deg, #1e3a8a, #1e40af); color: white; border-radius: 12px; padding: 18px; margin: 10px 0; text-align: center; }
        .calc-price { font-size: 24px; font-weight: 900; color: #fde68a; }
        .calc-label { font-size: 12px; color: #93c5fd; margin-bottom: 6px; }
        .zoom-card { background: linear-gradient(135deg, #fef3c7, #fde68a); border: 2px solid #f59e0b; border-radius: 8px; padding: 10px; margin: 4px 0; text-align: center; font-weight: 800; font-size: 13px; color: #92400e; }

        /* 투찰가 계산기 히어로 배너 */
        .calc-hero {
            background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 40%, #1e40af 70%, #0f172a 100%);
            border-radius: 20px;
            padding: 36px 28px 32px 28px;
            margin-bottom: 26px;
            text-align: center;
            position: relative;
            overflow: hidden;
            box-shadow: 0 8px 40px rgba(30,58,138,0.45);
        }
        .calc-hero-badge {
            display: inline-block;
            background: rgba(253,230,138,0.18);
            border: 1px solid rgba(253,230,138,0.4);
            color: #fde68a;
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 2px;
            padding: 4px 14px;
            border-radius: 20px;
            margin-bottom: 14px;
        }
        .calc-hero-title {
            font-size: 30px;
            font-weight: 900;
            color: #ffffff;
            line-height: 1.2;
            margin-bottom: 10px;
        }
        .calc-hero-title span { color: #fde68a; }
        .calc-hero-sub {
            font-size: 14px;
            color: #93c5fd;
            margin-bottom: 20px;
            line-height: 1.7;
        }
        .calc-hero-chips {
            display: flex;
            justify-content: center;
            gap: 10px;
            flex-wrap: wrap;
            margin-bottom: 24px;
        }
        .calc-hero-chip {
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.2);
            color: white;
            font-size: 12px;
            font-weight: 700;
            padding: 5px 14px;
            border-radius: 20px;
        }
        .calc-input-section {
            background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
            border: 2px solid #38bdf8;
            border-radius: 16px;
            padding: 22px;
            margin-bottom: 20px;
        }
        .calc-input-title {
            font-size: 16px;
            font-weight: 900;
            color: #0c4a6e;
            margin-bottom: 14px;
            text-align: center;
        }

        /* =============================================
           낙찰스코어 전용 스타일
           ============================================= */
        .score-hero {
            background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 40%, #312e81 70%, #0f172a 100%);
            border-radius: 20px;
            padding: 36px 28px 32px 28px;
            margin-bottom: 26px;
            text-align: center;
            position: relative;
            overflow: hidden;
            box-shadow: 0 8px 40px rgba(49,46,129,0.55);
        }
        .score-hero-badge {
            display: inline-block;
            background: rgba(167,139,250,0.18);
            border: 1px solid rgba(167,139,250,0.4);
            color: #c4b5fd;
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 2px;
            padding: 4px 14px;
            border-radius: 20px;
            margin-bottom: 14px;
        }
        .score-hero-title {
            font-size: 30px;
            font-weight: 900;
            color: #ffffff;
            line-height: 1.2;
            margin-bottom: 10px;
        }
        .score-hero-title span { color: #a78bfa; }
        .score-hero-sub {
            font-size: 14px;
            color: #a5b4fc;
            margin-bottom: 20px;
            line-height: 1.7;
        }
        .score-chips {
            display: flex;
            justify-content: center;
            gap: 10px;
            flex-wrap: wrap;
            margin-bottom: 24px;
        }
        .score-chip {
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.2);
            color: white;
            font-size: 12px;
            font-weight: 700;
            padding: 5px 14px;
            border-radius: 20px;
        }
        /* 점수 게이지 */
        .score-gauge-wrap {
            background: linear-gradient(135deg, #1e1b4b, #312e81);
            border-radius: 16px;
            padding: 24px 20px;
            margin: 14px 0;
            text-align: center;
            box-shadow: 0 4px 20px rgba(49,46,129,0.4);
        }
        .score-gauge-label {
            font-size: 13px;
            color: #a5b4fc;
            font-weight: 700;
            margin-bottom: 8px;
            letter-spacing: 1px;
        }
        .score-gauge-num {
            font-size: 56px;
            font-weight: 900;
            line-height: 1;
            margin-bottom: 6px;
        }
        .score-gauge-grade {
            font-size: 18px;
            font-weight: 800;
            margin-bottom: 4px;
        }
        .score-gauge-desc {
            font-size: 12px;
            color: #c4b5fd;
            margin-top: 4px;
        }
        /* 점수 항목 카드 */
        .score-item-card {
            background: #f5f3ff;
            border: 1.5px solid #ddd6fe;
            border-radius: 12px;
            padding: 12px 16px;
            margin: 6px 0;
        }
        .score-item-title {
            font-size: 13px;
            font-weight: 800;
            color: #4c1d95;
            margin-bottom: 4px;
        }
        .score-item-val {
            font-size: 15px;
            font-weight: 900;
            color: #7c3aed;
        }
        .score-item-desc {
            font-size: 11px;
            color: #6b7280;
            margin-top: 2px;
        }
        /* 등급별 색상 */
        .grade-S { color: #f59e0b; }
        .grade-A { color: #10b981; }
        .grade-B { color: #3b82f6; }
        .grade-C { color: #f97316; }
        .grade-D { color: #ef4444; }
        /* 낙찰스코어 결과 배너 */
        .score-result-banner {
            border-radius: 16px;
            padding: 22px 20px;
            margin: 14px 0;
            text-align: center;
        }
        /* 낙찰스코어 조언 박스 */
        .score-advice {
            background: #faf5ff;
            border: 2px solid #a78bfa;
            border-radius: 12px;
            padding: 14px 16px;
            margin: 8px 0;
            font-size: 13px;
            color: #4c1d95;
            line-height: 1.8;
        }
        .score-advice-title {
            font-size: 14px;
            font-weight: 900;
            color: #7c3aed;
            margin-bottom: 8px;
        }

        /* =============================================
           홈 대문 전용 스타일
           ============================================= */
        .hero-banner {
            background: linear-gradient(135deg, #1e3a8a 0%, #1d4ed8 60%, #1e40af 100%);
            padding: 80px 40px 70px 40px;
            text-align: center;
            border-radius: 20px;
            margin-bottom: 40px;
            color: white;
            box-shadow: 0 20px 50px rgba(30, 58, 138, 0.25);
            width: 100%;
            box-sizing: border-box;
        }
        .hero-date-badge {
            display: inline-block;
            background: #10b981;
            color: white;
            padding: 7px 24px;
            border-radius: 50px;
            font-weight: 700;
            font-size: 14px;
            letter-spacing: 0.5px;
            margin-bottom: 28px;
        }
        .hero-live-dot {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #a7f3d0;
            margin-right: 6px;
            vertical-align: middle;
            animation: hero-blink 2s infinite;
        }
        @keyframes hero-blink { 0%,100%{opacity:1} 50%{opacity:0.3} }
        .hero-main-title {
            font-size: 3.2rem;
            font-weight: 900;
            line-height: 1.2;
            margin-bottom: 18px;
            letter-spacing: -1px;
        }
        .hero-sub-title {
            font-size: 1.15rem;
            opacity: 0.85;
            margin-bottom: 12px;
            font-weight: 400;
            line-height: 1.8;
            max-width: 640px;
            margin-left: auto;
            margin-right: auto;
        }
        .hero-desc {
            font-size: 0.95rem;
            opacity: 0.65;
            line-height: 1.9;
            max-width: 560px;
            margin: 0 auto;
        }
        .stat-card-landing {
            background: white;
            padding: 36px 16px;
            border-radius: 20px;
            text-align: center;
            border: 1px solid #e2e8f0;
            box-shadow: 0 4px 16px rgba(0,0,0,0.05);
            min-height: 160px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }
        .stat-val-landing {
            color: #10b981;
            font-size: 2.8rem;
            font-weight: 900;
            margin-bottom: 8px;
            letter-spacing: -1px;
            line-height: 1;
        }
        .stat-txt-landing {
            color: #64748b;
            font-size: 0.9rem;
            font-weight: 600;
            letter-spacing: 0.3px;
        }
        .info-card {
            background: white;
            padding: 32px 28px;
            border-radius: 20px;
            border-top: 6px solid #1e3a8a;
            box-shadow: 0 8px 24px rgba(0,0,0,0.06);
            min-height: 220px;
        }
        .info-card h3 {
            color: #1e3a8a;
            font-size: 1.05rem;
            font-weight: 800;
            margin-bottom: 12px;
            letter-spacing: -0.3px;
        }
        .info-card p {
            font-size: 0.88rem;
            color: #475569;
            line-height: 1.85;
            margin: 0;
        }
        .info-card .badge-row {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-top: 14px;
        }
        .info-badge {
            background: #eff6ff;
            color: #1e3a8a;
            font-size: 0.72rem;
            font-weight: 700;
            padding: 3px 10px;
            border-radius: 20px;
        }
        .preview-wrap {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 16px;
            padding: 18px 18px 12px;
            margin-bottom: 8px;
        }
        .preview-title {
            font-size: 13px;
            font-weight: 800;
            color: #1e3a8a;
            margin-bottom: 10px;
        }
        .preview-row {
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 8px 12px;
            margin-bottom: 5px;
            font-size: 12px;
            overflow: hidden;
        }
        .preview-row .pr-name {
            font-weight: 600;
            color: #1e293b;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 68%;
            display: inline-block;
        }
        .preview-row .pr-amt {
            color: #dc2626;
            font-weight: 700;
            float: right;
        }
        .preview-row .pr-org {
            color: #64748b;
            font-size: 11px;
            display: block;
            margin-top: 2px;
            clear: both;
        }

        /* =============================================
           로그인 전용 화면 스타일
           ============================================= */
        .login-hero {
            background: linear-gradient(135deg, #1e3a8a 0%, #1d4ed8 60%, #1e40af 100%);
            border-radius: 20px;
            padding: 60px 40px 50px 40px;
            text-align: center;
            margin-bottom: 32px;
            color: white;
            box-shadow: 0 20px 50px rgba(30, 58, 138, 0.25);
        }
        .login-hero-title {
            font-size: 2.4rem;
            font-weight: 900;
            margin-bottom: 14px;
            letter-spacing: -1px;
        }
        .login-hero-sub {
            font-size: 1rem;
            opacity: 0.85;
            line-height: 1.8;
            margin-bottom: 0;
        }
        .login-feature-card {
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        .login-feature-icon { font-size: 2rem; margin-bottom: 8px; }
        .login-feature-title { font-size: 0.95rem; font-weight: 800; color: #1e3a8a; margin-bottom: 6px; }
        .login-feature-desc { font-size: 0.8rem; color: #64748b; line-height: 1.6; }
    </style>
""", unsafe_allow_html=True)

KST = timezone(timedelta(hours=9))

# ==========================================
# 2. 파이어베이스 셋팅
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

ADMIN_EMAILS = {"admin@kconmap.com", "master@kconmap.com", "a02280118@naver.com"}


@st.cache_resource
def init_firebase():
    firebase = pyrebase.initialize_app(firebaseConfig)
    return firebase.auth(), firebase.database()


auth, db = init_firebase()

for k, v in [('logged_in', False), ('user_name', ""), ('user_license', ""),
             ('user_phone', ""), ('localId', ""), ('idToken', ""), ('user_email', ""),
             ('main_cat', "🏠 홈 대문"), ('menu_c', "📊 실시간 공고 (홈)"),
             ('menu_s', "📊 실시간 공고 (홈)"), ('menu_comm', "👤 내 정보/로그인")]:
    if k not in st.session_state:
        st.session_state[k] = v


def is_admin():
    return st.session_state.get('user_email', '').strip().lower() in ADMIN_EMAILS


# ==========================================
# 3. 마스터 데이터 로딩 (공사 + 용역)
# ==========================================
@st.cache_data(show_spinner=False)
def load_master_data():
    file_path = "bid_data_3years.zip"
    if not os.path.exists(file_path):
        st.sidebar.error("🚨 서버 오류: 공사 3년 CSV 파일을 찾을 수 없습니다!")
        return None
    try:
        return pd.read_csv(file_path, compression='zip', encoding='utf-8-sig', low_memory=False)
    except Exception as e1:
        try:
            return pd.read_csv(file_path, compression='zip', encoding='cp949', low_memory=False)
        except Exception as e2:
            st.sidebar.error(f"🚨 공사 CSV 읽기 실패!\n원인1: {e1}\n원인2: {e2}")
            return None


@st.cache_data(show_spinner=False)
def load_service_master_data():
    file_path = "service_data_3years.zip"
    if not os.path.exists(file_path):
        return None
    try:
        return pd.read_csv(file_path, compression='zip', encoding='utf-8-sig', low_memory=False)
    except Exception:
        try:
            return pd.read_csv(file_path, compression='zip', encoding='cp949', low_memory=False)
        except Exception:
            return None


big_data = load_master_data()
service_big_data = load_service_master_data()


# ==========================================
# 4. 방문 카운팅
# ==========================================
def update_stats():
    now_ts = time.time()
    last_ts = st.session_state.get('visit_last_ts', 0)
    if now_ts - last_ts >= 300:
        try:
            curr = db.child("stats").child("total_visits").get().val()
            if curr is None:
                curr = 1828
            db.child("stats").update({"total_visits": int(curr) + 1})
            st.session_state['visit_last_ts'] = now_ts
            st.session_state['visited'] = True
        except Exception:
            pass


def get_stats():
    try:
        t_v = db.child("stats").child("total_visits").get().val() or 1828
        u_v = db.child("stats").child("total_users").get().val()
        if not u_v or int(u_v) == 0:
            actual_users = db.child("users").get().val()
            u_v = len(actual_users) if actual_users else 0
            if u_v and int(u_v) > 0:
                try:
                    db.child("stats").update({"total_users": int(u_v)})
                except Exception:
                    pass
        return int(t_v), int(u_v)
    except Exception:
        return 1828, 0


def get_total_data_count():
    count = 0
    if big_data is not None and not big_data.empty:
        count += len(big_data)
    if service_big_data is not None and not service_big_data.empty:
        count += len(service_big_data)
    return count


# ==========================================
# 5. 유틸리티 함수
# ==========================================
REGION_LIST = ["전국(전체)", "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
               "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]
ALL_LICENSES = ["[종합] 건축공사업", "[종합] 토목공사업", "[종합] 토목건축공사업", "[종합] 조경공사업",
                "[전문] 지반조성·포장공사업", "[전문] 실내건축공사업", "[전문] 철근·콘크리트공사업",
                "[기타] 전기공사업", "[기타] 정보통신공사업", "[기타] 소방시설공사업"]


def filter_by_region(df, sel):
    if sel == "전국(전체)":
        return df
    rk = {
        "서울": ["서울"], "부산": ["부산"], "대구": ["대구"], "인천": ["인천"],
        "광주": ["광주"], "대전": ["대전"], "울산": ["울산"], "세종": ["세종"],
        "경기": ["경기", "경기도"], "강원": ["강원", "강원도"],
        "충북": ["충북", "충청북도"], "충남": ["충남", "충청남도"],
        "전북": ["전북", "전라북도"], "전남": ["전남", "전라남도"],
        "경북": ["경북", "경상북도"], "경남": ["경남", "경상남도"], "제주": ["제주"]
    }
    pat = '|'.join(rk.get(sel, [sel]))
    return df[df['발주기관'].str.contains(pat, na=False) | df['공고명'].str.contains(pat, na=False)]


def raw_to_int(raw) -> int:
    if raw is None:
        return 0
    r = str(raw).strip().replace(',', '').replace('원', '').replace('%', '')
    try:
        return int(float(r))
    except Exception:
        return 0


def to_float_rate(val):
    try:
        return float(str(val).replace('%', '').strip())
    except Exception:
        return None


def get_rate_col(df):
    return '사정률' if '사정률' in df.columns else '투찰률'


def get_match_keywords(lic):
    k = []
    if "토목" in lic: k.extend(["토목", "도로", "포장", "하천", "교량", "정비", "관로", "상수도", "하수도"])
    if "건축" in lic: k.extend(["건축", "신축", "증축", "보수", "인테리어", "방수", "도장"])
    if "조경" in lic: k.extend(["조경", "식재", "공원", "수목"])
    if "전기" in lic: k.extend(["전기", "배전", "가로등", "CCTV"])
    if "통신" in lic: k.extend(["통신", "네트워크", "방송"])
    if "소방" in lic: k.extend(["소방", "화재", "스프링클러"])
    if "철근" in lic or "콘크리트" in lic: k.extend(["철콘", "구조물", "옹벽", "배수", "기초"])
    if "지반" in lic or "포장" in lic: k.extend(["지반", "포장", "아스팔트", "토공"])
    if "실내건축" in lic: k.extend(["실내건축", "인테리어", "내장", "칸막이"])
    return list(set(k))


# ==========================================
# 6. 5대 팩트 분석 엔진 (master_df 동적 바인딩)
# ==========================================

def engine_heatmap(inst_name, master_df):
    if master_df is None or master_df.empty:
        return None
    df = master_df[master_df['발주기관'] == inst_name].copy()
    if df.empty:
        return None
    rate_col = get_rate_col(df)
    df['rate_f'] = df[rate_col].apply(to_float_rate)
    df = df.dropna(subset=['rate_f'])
    if df.empty:
        return None
    df['구간'] = (df['rate_f'] // 0.5 * 0.5).apply(lambda x: f"{x:.1f}~{x+0.5:.1f}%")
    zone_counts = df['구간'].value_counts().sort_values(ascending=False)
    return {
        'zone_counts': zone_counts,
        'avg': round(df['rate_f'].mean(), 2),
        'std': round(df['rate_f'].std(), 2),
        'min': round(df['rate_f'].min(), 2),
        'max': round(df['rate_f'].max(), 2),
        'top_zone': zone_counts.index[0],
        'top_count': int(zone_counts.iloc[0]),
        'total': len(df),
        'rate_col': rate_col
    }


def engine_dominant(inst_name, master_df):
    if master_df is None or master_df.empty:
        return None
    df = master_df[master_df['발주기관'] == inst_name].copy()
    if df.empty or '1순위업체' not in df.columns:
        return None
    total = len(df)
    corp_counts = df['1순위업체'].value_counts()
    top_corp = corp_counts.index[0]
    top_count = int(corp_counts.iloc[0])
    monopoly_rate = round(top_count / total * 100, 1)
    recent_top = pd.Series(dtype=int)
    if '날짜' in df.columns:
        df['dt'] = pd.to_datetime(df['날짜'], errors='coerce')
        cutoff = datetime.now() - timedelta(days=365)
        recent = df[df['dt'] >= cutoff]
        if not recent.empty:
            recent_top = recent['1순위업체'].value_counts().head(5)
    return {
        'corp_counts': corp_counts.head(7),
        'top_corp': top_corp,
        'top_count': top_count,
        'monopoly_rate': monopoly_rate,
        'total': total,
        'recent_top': recent_top
    }


def engine_pattern(inst_name, master_df):
    if master_df is None or master_df.empty:
        return None
    df = master_df[master_df['발주기관'] == inst_name].copy()
    if df.empty:
        return None
    monthly = pd.Series(dtype=int)
    yearly = pd.Series(dtype=int)
    peak_month = None
    if '날짜' in df.columns:
        df['dt'] = pd.to_datetime(df['날짜'], errors='coerce')
        df2 = df.dropna(subset=['dt'])
        if not df2.empty:
            monthly = df2['dt'].dt.month.value_counts().sort_index()
            yearly = df2['dt'].dt.year.value_counts().sort_index()
            peak_month = int(monthly.idxmax())
    avg_per_year = round(len(df) / max(len(yearly), 1), 1)
    amt_stats = {}
    for c in ['투찰금액', '예산금액']:
        if c in df.columns:
            df['amt_v'] = df[c].apply(raw_to_int)
            df_a = df[df['amt_v'] > 0]
            if not df_a.empty:
                amt_stats = {
                    'col': c,
                    'avg': int(df_a['amt_v'].mean()),
                    'min': int(df_a['amt_v'].min()),
                    'max': int(df_a['amt_v'].max()),
                    'median': int(df_a['amt_v'].median()),
                }
            break
    return {
        'total': len(df), 'monthly': monthly, 'yearly': yearly,
        'peak_month': peak_month, 'avg_per_year': avg_per_year, 'amt_stats': amt_stats
    }


def engine_similar(notice_name, inst_name, master_df, top_n=7):
    if master_df is None or master_df.empty or not notice_name:
        return None
    stopwords = {'공사', '용역', '설치', '사업', '시공', '및', '기타', '위한', '에', '의', '을', '를'}
    keywords = [w for w in re.findall(r'[가-힣]{2,}', notice_name) if w not in stopwords]
    if not keywords:
        return None
    pattern = '|'.join(keywords[:5])
    matched = master_df[master_df['공고명'].str.contains(pattern, na=False)].copy()
    if matched.empty:
        return None
    matched['same_inst'] = 0
    if '발주기관' in matched.columns and inst_name:
        matched['same_inst'] = (matched['발주기관'] == inst_name).astype(int)
    if '날짜' in matched.columns:
        matched['dt'] = pd.to_datetime(matched['날짜'], errors='coerce')
        matched = matched.sort_values(['same_inst', 'dt'], ascending=[False, False])
    result = matched.head(top_n).copy()
    rate_col = get_rate_col(result)
    result['rate_f'] = result[rate_col].apply(to_float_rate)
    valid = result.dropna(subset=['rate_f'])
    rate_dist = None
    if not valid.empty:
        valid2 = valid.copy()
        valid2['구간'] = (valid2['rate_f'] // 0.5 * 0.5).apply(lambda x: f"{x:.1f}~{x+0.5:.1f}%")
        rate_dist = valid2['구간'].value_counts()
    return {
        'cases': result, 'rate_col': rate_col,
        'keywords': keywords[:5], 'rate_dist': rate_dist, 'valid_count': len(valid)
    }


def engine_self_diagnosis(corp_name, master_df):
    if master_df is None or master_df.empty or not corp_name:
        return None
    df = master_df[master_df['1순위업체'].str.contains(corp_name, na=False)].copy()
    if df.empty:
        return None
    total_wins = len(df)
    region_wins = {}
    for reg in ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
                "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]:
        mask = df['발주기관'].str.contains(reg, na=False) | df['공고명'].str.contains(reg, na=False)
        cnt = int(mask.sum())
        if cnt > 0:
            region_wins[reg] = cnt
    region_wins = dict(sorted(region_wins.items(), key=lambda x: x[1], reverse=True))
    best_month = None
    monthly = pd.Series(dtype=int)
    yearly = pd.Series(dtype=int)
    if '날짜' in df.columns:
        df['dt'] = pd.to_datetime(df['날짜'], errors='coerce')
        df2 = df.dropna(subset=['dt'])
        if not df2.empty:
            monthly = df2['dt'].dt.month.value_counts().sort_index()
            yearly = df2['dt'].dt.year.value_counts().sort_index()
            best_month = int(monthly.idxmax())
    rate_col = get_rate_col(df)
    df['rate_f'] = df[rate_col].apply(to_float_rate)
    df_r = df.dropna(subset=['rate_f'])
    rate_dist = pd.Series(dtype=int)
    avg_rate = None
    if not df_r.empty:
        avg_rate = round(df_r['rate_f'].mean(), 2)
        df_r2 = df_r.copy()
        df_r2['구간'] = (df_r2['rate_f'] // 0.5 * 0.5).apply(lambda x: f"{x:.1f}~{x+0.5:.1f}%")
        rate_dist = df_r2['구간'].value_counts()
    top_inst = df['발주기관'].value_counts().head(5) if '발주기관' in df.columns else pd.Series()
    return {
        'corp_name': corp_name, 'total_wins': total_wins,
        'region_wins': region_wins, 'best_month': best_month,
        'monthly': monthly, 'yearly': yearly,
        'avg_rate': avg_rate, 'rate_dist': rate_dist,
        'top_inst': top_inst, 'rate_col': rate_col
    }


# ==========================================
# 투찰가 계산기 엔진 (master_df 동적 바인딩)
# ==========================================
def engine_bid_calculator(inst_name, base_price, master_df):
    if master_df is None or master_df.empty or not inst_name or not base_price:
        return None
    df = master_df[master_df['발주기관'] == inst_name].copy()
    if df.empty:
        return None
    rate_col = get_rate_col(df)
    df['rate_f'] = df[rate_col].apply(to_float_rate)
    df = df.dropna(subset=['rate_f'])
    if df.empty:
        return None
    df['구간_01'] = (df['rate_f'] // 0.1 * 0.1).round(1)
    zone_01 = df['구간_01'].value_counts().sort_values(ascending=False)
    top5 = zone_01.head(5)
    best_rate = float(top5.index[0])
    recommended = int(base_price * best_rate / 100)
    avg_rate = round(df['rate_f'].mean(), 2)
    mid_rate = round(df['rate_f'].median(), 2)
    avg_price = int(base_price * avg_rate / 100)
    mid_price = int(base_price * mid_rate / 100)
    return {
        'df': df,
        'total': len(df),
        'rate_col': rate_col,
        'zone_01': zone_01,
        'top5': top5,
        'best_rate': best_rate,
        'recommended': recommended,
        'avg_rate': avg_rate,
        'mid_rate': mid_rate,
        'avg_price': avg_price,
        'mid_price': mid_price,
    }


def engine_zoom(df, hot_rate, base_price):
    lower = round(hot_rate, 1)
    upper = round(lower + 0.1, 1)
    mask = (df['rate_f'] >= lower) & (df['rate_f'] < upper)
    sub = df[mask].copy()
    if sub.empty:
        return None
    sub['구간_001'] = (sub['rate_f'] // 0.01 * 0.01).round(2)
    zone_001 = sub['구간_001'].value_counts().sort_values(ascending=False)
    best_001 = float(zone_001.index[0])
    return {
        'zone_001': zone_001,
        'best_001': best_001,
        'best_price': int(base_price * best_001 / 100),
        'total_sub': len(sub),
        'lower': lower,
        'upper': upper,
    }


# ==========================================
# 🏆 낙찰스코어 엔진
# ==========================================
def engine_bid_score(inst_name, notice_name, my_rate, base_price, master_df):
    if master_df is None or master_df.empty:
        return None

    df_inst = master_df[master_df['발주기관'] == inst_name].copy()
    if df_inst.empty:
        return None

    rate_col = get_rate_col(df_inst)
    df_inst['rate_f'] = df_inst[rate_col].apply(to_float_rate)
    df_inst = df_inst.dropna(subset=['rate_f'])
    if df_inst.empty:
        return None

    total_data = len(df_inst)
    avg_rate = round(df_inst['rate_f'].mean(), 3)
    std_rate = round(df_inst['rate_f'].std(), 3)

    df_inst['구간_01'] = (df_inst['rate_f'] // 0.1 * 0.1).round(1)
    zone_01 = df_inst['구간_01'].value_counts().sort_values(ascending=False)
    best_rate_01 = float(zone_01.index[0]) if not zone_01.empty else avg_rate
    total_zone = zone_01.sum()

    # ─── 항목 1: 핫존 일치도 (30점) ───
    my_zone = round(my_rate // 0.1 * 0.1, 1)
    hot_zone_cnt = int(zone_01.get(my_zone, 0))
    hot_zone_pct = hot_zone_cnt / total_zone * 100 if total_zone > 0 else 0
    dist_from_best = abs(my_rate - best_rate_01)
    if dist_from_best <= 0.05:
        score_hotzone = 30
    elif dist_from_best <= 0.1:
        score_hotzone = 25
    elif dist_from_best <= 0.2:
        score_hotzone = 18
    elif dist_from_best <= 0.5:
        score_hotzone = 10
    elif dist_from_best <= 1.0:
        score_hotzone = 4
    else:
        score_hotzone = 0

    # ─── 항목 2: 경쟁 강도 (20점) ───
    monopoly_rate = 0
    top_corp = "-"
    if '1순위업체' in df_inst.columns:
        corp_counts = df_inst['1순위업체'].value_counts()
        top_corp = corp_counts.index[0]
        monopoly_rate = round(corp_counts.iloc[0] / total_data * 100, 1)
    if monopoly_rate >= 60:
        score_competition = 2
    elif monopoly_rate >= 40:
        score_competition = 7
    elif monopoly_rate >= 25:
        score_competition = 13
    elif monopoly_rate >= 15:
        score_competition = 17
    else:
        score_competition = 20

    # ─── 항목 3: 유사공고 적중 (20점) ───
    score_similar = 0
    similar_best_zone = None
    similar_count = 0
    if notice_name:
        stopwords = {'공사', '용역', '설치', '사업', '시공', '및', '기타', '위한'}
        keywords = [w for w in re.findall(r'[가-힣]{2,}', notice_name) if w not in stopwords]
        if keywords:
            pattern = '|'.join(keywords[:4])
            sim_df = master_df[master_df['공고명'].str.contains(pattern, na=False)].copy()
            sim_df['rate_f'] = sim_df[rate_col].apply(to_float_rate)
            sim_df = sim_df.dropna(subset=['rate_f'])
            similar_count = len(sim_df)
            if not sim_df.empty:
                sim_df['구간_01'] = (sim_df['rate_f'] // 0.1 * 0.1).round(1)
                sim_zone = sim_df['구간_01'].value_counts()
                similar_best_zone = float(sim_zone.index[0])
                sim_dist = abs(my_rate - similar_best_zone)
                if sim_dist <= 0.05:
                    score_similar = 20
                elif sim_dist <= 0.1:
                    score_similar = 16
                elif sim_dist <= 0.2:
                    score_similar = 10
                elif sim_dist <= 0.5:
                    score_similar = 5
                else:
                    score_similar = 0

    # ─── 항목 4: 투찰률 안정성 (15점) ───
    if std_rate <= 0.3:
        score_stability = 15
    elif std_rate <= 0.5:
        score_stability = 12
    elif std_rate <= 0.8:
        score_stability = 8
    elif std_rate <= 1.2:
        score_stability = 4
    else:
        score_stability = 1

    # ─── 항목 5: 데이터 충분성 (15점) ───
    if total_data >= 100:
        score_data = 15
    elif total_data >= 50:
        score_data = 12
    elif total_data >= 20:
        score_data = 8
    elif total_data >= 10:
        score_data = 4
    else:
        score_data = 1

    total_score = score_hotzone + score_competition + score_similar + score_stability + score_data

    if total_score >= 85:
        grade = "S"
        grade_label = "S등급 — 최상위 낙찰 확률"
        grade_color = "#f59e0b"
        bg_color = "linear-gradient(135deg, #78350f, #92400e)"
        win_prob = "75~90%"
        advice = [
            "✅ 현재 투찰률이 발주기관 핫존과 매우 정확하게 일치합니다.",
            "✅ 경쟁 구도도 열려 있어 특정 독식 업체 위협이 낮습니다.",
            "✅ 유사공고 낙찰 패턴과도 높은 일치도를 보입니다.",
            "💡 현재 투찰가를 그대로 유지하거나 ±0.03% 이내 미세조정을 고려하세요."
        ]
    elif total_score >= 70:
        grade = "A"
        grade_label = "A등급 — 높은 낙찰 가능성"
        grade_color = "#10b981"
        bg_color = "linear-gradient(135deg, #064e3b, #065f46)"
        win_prob = "55~75%"
        advice = [
            "✅ 투찰률이 핫존에 근접해 있어 경쟁력이 충분합니다.",
            "⚡ 핫존 중심까지 약간의 미세조정 여지가 있습니다.",
            f"💡 최다발생 구간({best_rate_01}%)과의 거리를 좁히면 S등급 진입 가능합니다.",
            "📊 유사공고 분석도 긍정적 신호를 보이고 있습니다."
        ]
    elif total_score >= 55:
        grade = "B"
        grade_label = "B등급 — 보통 수준"
        grade_color = "#3b82f6"
        bg_color = "linear-gradient(135deg, #1e3a8a, #1e40af)"
        win_prob = "35~55%"
        advice = [
            "⚠️ 투찰률이 핫존에서 다소 벗어나 있습니다.",
            f"💡 발주기관 최다발생 구간 {best_rate_01}% 방향으로 조정을 검토하세요.",
            "📊 경쟁업체 분포와 유사공고 패턴을 다시 확인해보세요.",
            "🔍 투찰가 계산기로 0.01% 단위 정밀 분석을 추가로 진행하세요."
        ]
    elif total_score >= 40:
        grade = "C"
        grade_label = "C등급 — 낙찰 가능성 낮음"
        grade_color = "#f97316"
        bg_color = "linear-gradient(135deg, #7c2d12, #9a3412)"
        win_prob = "15~35%"
        advice = [
            "⚠️ 현재 투찰률은 발주기관 낙찰 집중 구간과 거리가 있습니다.",
            f"❗ 핫존({best_rate_01}%)과 비교하여 투찰가 재검토가 필요합니다.",
            "🔍 독식업체 존재 여부도 추가로 확인하세요.",
            "💡 투찰가 계산기의 0.01% 돋보기 분석을 활용하세요."
        ]
    else:
        grade = "D"
        grade_label = "D등급 — 낙찰 가능성 매우 낮음"
        grade_color = "#ef4444"
        bg_color = "linear-gradient(135deg, #450a0a, #7f1d1d)"
        win_prob = "5~15%"
        advice = [
            "❌ 현재 투찰률은 발주기관 낙찰 패턴과 크게 벗어나 있습니다.",
            f"❗ 발주기관 핫존({best_rate_01}%)으로 투찰가를 전면 재검토하세요.",
            "⚠️ 독식업체가 있는 경우 전략적 판단이 필요합니다.",
            "💡 투찰가 계산기를 먼저 실행하여 추천 투찰가를 확인하세요."
        ]

    my_bid_price = int(base_price * my_rate / 100) if base_price else 0
    best_bid_price = int(base_price * best_rate_01 / 100) if base_price else 0

    return {
        'total_score': total_score,
        'grade': grade,
        'grade_label': grade_label,
        'grade_color': grade_color,
        'bg_color': bg_color,
        'win_prob': win_prob,
        'advice': advice,
        'score_hotzone': score_hotzone,
        'score_competition': score_competition,
        'score_similar': score_similar,
        'score_stability': score_stability,
        'score_data': score_data,
        'total_data': total_data,
        'avg_rate': avg_rate,
        'std_rate': std_rate,
        'best_rate_01': best_rate_01,
        'hot_zone_pct': round(hot_zone_pct, 1),
        'monopoly_rate': monopoly_rate,
        'top_corp': top_corp,
        'similar_best_zone': similar_best_zone,
        'similar_count': similar_count,
        'rate_col': rate_col,
        'my_bid_price': my_bid_price,
        'best_bid_price': best_bid_price,
        'zone_01': zone_01,
    }


# ==========================================
# 7. 분석 렌더 함수 (master_df 파라미터로 받음)
# ==========================================

def render_heatmap(inst_name, master_df):
    r = engine_heatmap(inst_name, master_df)
    if r is None:
        st.info(f"'{inst_name}'의 투찰률 데이터가 없습니다.")
        return
    st.markdown(f"**'{inst_name}' 최근 3년 {r['rate_col']} 구간 분포** (총 {r['total']}건 실제 데이터)")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("평균", f"{r['avg']}%")
    c2.metric("표준편차", f"±{r['std']}%")
    c3.metric("최솟값", f"{r['min']}%")
    c4.metric("최댓값", f"{r['max']}%")
    st.markdown("---")
    st.markdown("**📊 구간별 낙찰 집중도** (0.5% 단위, 상위 12개)")
    top12 = r['zone_counts'].head(12)
    max_cnt = int(top12.iloc[0]) if not top12.empty else 1
    for zone, cnt in top12.items():
        bar_w = int(cnt / max_cnt * 100)
        is_top = (zone == r['top_zone'])
        color = "#f59e0b" if is_top else "#3b82f6"
        star = " ⭐ 최다발생" if is_top else ""
        st.markdown(
            f"""<div style="margin:4px 0;display:flex;align-items:center;gap:8px;">
                <span style="font-size:13px;font-weight:{'900' if is_top else '500'};width:145px;flex-shrink:0;">{zone}{star}</span>
                <div style="background:{color};width:{bar_w}%;height:18px;border-radius:3px;min-width:3px;"></div>
                <span style="font-size:13px;font-weight:700;">{cnt}회 ({round(cnt/r['total']*100,1)}%)</span>
            </div>""", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown(
        f'<div class="hit-zone">📌 {r["rate_col"]} 최다 발생 구간: <b>{r["top_zone"]}</b>'
        f' — {r["top_count"]}회 / {r["total"]}건 중 {round(r["top_count"]/r["total"]*100,1)}% 집중</div>',
        unsafe_allow_html=True)
    st.caption(f"* 3년 실제 낙찰 데이터 기준 {r['rate_col']} 분포입니다. 추정 없음.")


def render_dominant(inst_name, master_df):
    r = engine_dominant(inst_name, master_df)
    if r is None:
        st.info(f"'{inst_name}'의 낙찰 데이터가 없습니다.")
        return
    st.markdown(f"**'{inst_name}' 최근 3년 낙찰 업체 분포** (총 {r['total']}건 실제 데이터)")
    monopoly = r['monopoly_rate']
    if monopoly >= 40:
        st.markdown(f'<div class="warn-box">⚠️ 독식 경보! <b>{r["top_corp"]}</b>이 전체의 <b>{monopoly}%</b> 독식 중</div>', unsafe_allow_html=True)
    elif monopoly >= 20:
        st.warning(f"🔶 `{r['top_corp']}`이 **{monopoly}%** 점유 중 — 강한 고정 경쟁자 존재")
    else:
        st.markdown(f'<div class="ok-box">✅ 특정 독식 업체 없음 — 비교적 열린 경쟁 구도 ({r["top_corp"]} {monopoly}% 점유)</div>', unsafe_allow_html=True)
    medals = ["🥇", "🥈", "🥉", "4위", "5위", "6위", "7위"]
    for i, (corp, cnt) in enumerate(r['corp_counts'].items()):
        pct = round(cnt / r['total'] * 100, 1)
        if i == 0:
            st.markdown(f'<div class="corp-rank1">{medals[i]} {corp} — {cnt}회 ({pct}%)</div>', unsafe_allow_html=True)
        else:
            m = medals[i] if i < 7 else f"{i+1}위"
            st.markdown(f'<div class="corp-rank-other">{m} {corp} — {cnt}회 ({pct}%)</div>', unsafe_allow_html=True)
    if not r['recent_top'].empty:
        st.markdown("---")
        st.markdown("**📅 최근 1년 낙찰 TOP 5**")
        for corp, cnt in r['recent_top'].items():
            st.info(f"**{corp}**: {cnt}회")


def render_pattern(inst_name, master_df):
    r = engine_pattern(inst_name, master_df)
    if r is None:
        st.info(f"'{inst_name}'의 발주 패턴 데이터가 없습니다.")
        return
    st.markdown(f"**'{inst_name}' 발주 패턴** (총 {r['total']}건 실제 데이터)")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f'<div class="insight-box"><div class="insight-title">📅 연평균 발주 건수</div><div class="insight-val">{r["avg_per_year"]}건/년</div></div>', unsafe_allow_html=True)
    with c2:
        peak = f"{r['peak_month']}월" if r['peak_month'] else "-"
        st.markdown(f'<div class="insight-box"><div class="insight-title">🔥 발주 집중 월</div><div class="insight-val">{peak}</div></div>', unsafe_allow_html=True)
    if not r['monthly'].empty:
        st.markdown("**📊 월별 발주 건수 (3년 합산)**")
        month_labels = {1: "1월", 2: "2월", 3: "3월", 4: "4월", 5: "5월", 6: "6월",
                        7: "7월", 8: "8월", 9: "9월", 10: "10월", 11: "11월", 12: "12월"}
        max_m = int(r['monthly'].max())
        for m in range(1, 13):
            cnt = int(r['monthly'].get(m, 0))
            bar_w = int(cnt / max_m * 100) if max_m > 0 else 0
            is_peak = (m == r['peak_month'])
            color = "#ef4444" if is_peak else "#6366f1"
            label = " 🔥" if is_peak else ""
            st.markdown(
                f"""<div style="margin:3px 0;display:flex;align-items:center;gap:8px;">
                    <span style="font-size:12px;width:42px;flex-shrink:0;font-weight:{'800' if is_peak else '500'}">{month_labels[m]}{label}</span>
                    <div style="background:{color};width:{bar_w}%;height:14px;border-radius:3px;min-width:2px;"></div>
                    <span style="font-size:12px;font-weight:700;">{cnt}건</span>
                </div>""", unsafe_allow_html=True)
    if not r['yearly'].empty:
        st.markdown("---")
        st.markdown("**📈 연도별 발주 건수**")
        cols = st.columns(len(r['yearly']))
        for i, (yr, cnt) in enumerate(r['yearly'].items()):
            cols[i].metric(f"{yr}년", f"{cnt}건")
    if r['amt_stats']:
        a = r['amt_stats']
        st.markdown("---")
        st.markdown(f"**💰 실제 {a['col']} 규모 분포**")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("평균", f"{a['avg']//10000:,}만원")
        col2.metric("중간값", f"{a['median']//10000:,}만원")
        col3.metric("최소", f"{a['min']//10000:,}만원")
        col4.metric("최대", f"{a['max']//10000:,}만원")
        st.caption(f"* 실제 {a['col']} 기준. 추정 없음.")


def render_similar(notice_name, inst_name, master_df):
    r = engine_similar(notice_name, inst_name, master_df)
    if r is None:
        st.info("유사한 과거 공고를 찾을 수 없습니다.")
        return
    st.markdown(f"**검색 키워드:** `{'`, `'.join(r['keywords'])}`")
    st.markdown(f"유사 과거 사례 **{len(r['cases'])}건** 검색됨")
    rate_col = r['rate_col']
    for _, row in r['cases'].iterrows():
        same_tag = " 🏛️ 동일기관" if str(row.get('발주기관', '')) == inst_name else ""
        rate_val = row.get(rate_col, '-')
        date_val = str(row.get('날짜', '-'))[:10]
        corp_val = row.get('1순위업체', '-')
        name_val = str(row.get('공고명', ''))[:50]
        amt_val = row.get('투찰금액', '')
        amt_str = f"{raw_to_int(amt_val):,}원" if amt_val and raw_to_int(amt_val) > 0 else '-'
        st.markdown(
            f'<div class="similar-card">'
            f'<div style="font-size:11px;color:#6b7280;">{date_val} | {row.get("발주기관","")}{same_tag}</div>'
            f'<div style="font-size:13px;font-weight:700;margin:3px 0;">{name_val}</div>'
            f'<span style="color:#dc2626;font-weight:800;">1순위: {corp_val}</span>'
            f' &nbsp;|&nbsp; <span style="color:#1e3a8a;font-weight:800;">{rate_col}: {rate_val}</span>'
            f' &nbsp;|&nbsp; <span style="color:#374151;">낙찰금액: {amt_str}</span>'
            f'</div>', unsafe_allow_html=True)
    if r['rate_dist'] is not None and not r['rate_dist'].empty:
        st.markdown("---")
        st.markdown(f"**📊 유사 공고 {rate_col} 분포**")
        max_cnt = int(r['rate_dist'].iloc[0])
        for zone, cnt in r['rate_dist'].items():
            bar_w = int(cnt / max_cnt * 100)
            st.markdown(
                f"""<div style="margin:3px 0;display:flex;align-items:center;gap:8px;">
                    <span style="font-size:12px;width:130px;flex-shrink:0;">{zone}</span>
                    <div style="background:#10b981;width:{bar_w}%;height:14px;border-radius:3px;min-width:2px;"></div>
                    <span style="font-size:12px;font-weight:700;">{cnt}건</span>
                </div>""", unsafe_allow_html=True)
        top_zone = r['rate_dist'].index[0]
        st.markdown(
            f'<div class="hit-zone">📌 유사 공고 {rate_col} 최다 발생 구간: <b>{top_zone}</b> ({r["valid_count"]}건 실제 데이터 기준)</div>',
            unsafe_allow_html=True)
    st.caption("* 공고명 키워드 기반 실제 낙찰 사례. 추정 없음.")


def render_self_diagnosis(corp_name, master_df):
    r = engine_self_diagnosis(corp_name, master_df)
    if r is None:
        st.warning(f"'{corp_name}' 업체의 3년 낙찰 이력이 없습니다.")
        return
    st.markdown(f"**'{r['corp_name']}' 3년 낙찰 팩트 리포트**")
    c1, c2, c3 = st.columns(3)
    best_reg = list(r['region_wins'].keys())[0] if r['region_wins'] else "-"
    best_cnt = list(r['region_wins'].values())[0] if r['region_wins'] else 0
    avg_r = f"{r['avg_rate']}%" if r['avg_rate'] else "-"
    c1.markdown(f'<div class="diag-box"><div class="diag-title">🏆 3년 총 낙찰 건수</div><div class="diag-val">{r["total_wins"]}건</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="diag-box"><div class="diag-title">📍 최강 지역</div><div class="diag-val">{best_reg} ({best_cnt}건)</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="diag-box"><div class="diag-title">🎯 평균 낙찰 {r["rate_col"]}</div><div class="diag-val">{avg_r}</div></div>', unsafe_allow_html=True)
    if r['region_wins']:
        st.markdown("---")
        st.markdown("**📍 지역별 낙찰 건수**")
        max_r = max(r['region_wins'].values())
        for reg, cnt in r['region_wins'].items():
            bar_w = int(cnt / max_r * 100)
            st.markdown(
                f"""<div style="margin:3px 0;display:flex;align-items:center;gap:8px;">
                    <span style="font-size:13px;width:40px;flex-shrink:0;font-weight:700;">{reg}</span>
                    <div style="background:#3b82f6;width:{bar_w}%;height:16px;border-radius:3px;min-width:3px;"></div>
                    <span style="font-size:13px;font-weight:700;">{cnt}건</span>
                </div>""", unsafe_allow_html=True)
    if not r['rate_dist'].empty:
        st.markdown("---")
        st.markdown(f"**🎯 낙찰 {r['rate_col']} 구간 분포**")
        max_rd = int(r['rate_dist'].iloc[0])
        for zone, cnt in r['rate_dist'].head(10).items():
            bar_w = int(cnt / max_rd * 100)
            st.markdown(
                f"""<div style="margin:3px 0;display:flex;align-items:center;gap:8px;">
                    <span style="font-size:12px;width:130px;flex-shrink:0;">{zone}</span>
                    <div style="background:#8b5cf6;width:{bar_w}%;height:14px;border-radius:3px;min-width:2px;"></div>
                    <span style="font-size:12px;font-weight:700;">{cnt}건</span>
                </div>""", unsafe_allow_html=True)
    if not r['top_inst'].empty:
        st.markdown("---")
        st.markdown("**🏛️ 주요 낙찰 발주기관 TOP 5**")
        for inst, cnt in r['top_inst'].items():
            st.info(f"**{inst}**: {cnt}건")
    if not r['yearly'].empty:
        st.markdown("---")
        st.markdown("**📈 연도별 낙찰 추이**")
        cols = st.columns(len(r['yearly']))
        for i, (yr, cnt) in enumerate(r['yearly'].items()):
            cols[i].metric(f"{yr}년", f"{cnt}건")
    if r['best_month'] and not r['monthly'].empty:
        st.markdown("---")
        st.markdown(f"**📅 월별 낙찰 건수** (집중 월: {r['best_month']}월)")
        month_labels = {1: "1월", 2: "2월", 3: "3월", 4: "4월", 5: "5월", 6: "6월",
                        7: "7월", 8: "8월", 9: "9월", 10: "10월", 11: "11월", 12: "12월"}
        max_m = int(r['monthly'].max())
        for m in range(1, 13):
            cnt = int(r['monthly'].get(m, 0))
            bar_w = int(cnt / max_m * 100) if max_m > 0 else 0
            is_best = (m == r['best_month'])
            color = "#f59e0b" if is_best else "#94a3b8"
            st.markdown(
                f"""<div style="margin:3px 0;display:flex;align-items:center;gap:8px;">
                    <span style="font-size:12px;width:40px;flex-shrink:0;font-weight:{'800' if is_best else '400'}">{month_labels[m]}</span>
                    <div style="background:{color};width:{bar_w}%;height:14px;border-radius:3px;min-width:2px;"></div>
                    <span style="font-size:12px;font-weight:700;">{cnt}건</span>
                </div>""", unsafe_allow_html=True)
    st.caption("* 3년 실제 낙찰 데이터 기준. 추정 없음.")


# ==========================================
# 투찰가 계산기 렌더
# ==========================================
def render_bid_calculator(master_df, live_df_func, tab_prefix):
    st.markdown("""
    <div class="calc-hero">
        <div class="calc-hero-badge">⭐ AI 데이터 분석 · 3년 실제 낙찰 데이터</div>
        <div class="calc-hero-title">🧮 <span>투찰가 계산기</span></div>
        <div class="calc-hero-sub">
            공고명만 입력하면<br>
            <b style="color:white;">발주기관 자동 탐지 → 핫존 분석 → 추천 투찰가</b> 즉시 산출
        </div>
        <div class="calc-hero-chips">
            <div class="calc-hero-chip">📊 0.01% 단위 정밀 분석</div>
            <div class="calc-hero-chip">🎯 핫존 자동 탐지</div>
            <div class="calc-hero-chip">💰 원단위 추천가 산출</div>
            <div class="calc-hero-chip">🏛️ 전국 발주기관 지원</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if master_df is None or master_df.empty:
        st.info("3년 마스터 데이터가 없습니다.")
        return

    st.markdown("""
    <div class="calc-input-section">
        <div class="calc-input-title">📝 공고 정보 입력</div>
    </div>
    """, unsafe_allow_html=True)

    df_live_calc = live_df_func() if live_df_func else pd.DataFrame()
    notice_input = ""

    if not df_live_calc.empty and '공고명' in df_live_calc.columns:
        live_notices = df_live_calc['공고명'].dropna().tolist()
        select_options = ["✏️ 직접 입력 (공고명 타이핑)"] + live_notices
        selected_notice = st.selectbox(
            "📋 공고 선택 또는 직접 입력",
            select_options,
            key=f"calc_notice_select_{tab_prefix}",
            help="실시간 공고 목록에서 바로 선택하거나, '직접 입력'을 선택해 공고명을 입력하세요."
        )
        if selected_notice == "✏️ 직접 입력 (공고명 타이핑)":
            notice_input = st.text_input(
                "📋 공고명 직접 입력",
                placeholder="예: 장성군관광문화재단 사무실 리모델링 건축공사",
                key=f"calc_notice_manual_{tab_prefix}"
            )
        else:
            notice_input = selected_notice
            st.markdown(
                f'<div style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;'
                f'padding:8px 14px;margin:4px 0;font-size:13px;color:#166534;">'
                f'✅ 선택된 공고: <b>{selected_notice}</b>'
                f'</div>', unsafe_allow_html=True)
    else:
        notice_input = st.text_input(
            "📋 공고명 입력",
            placeholder="예: 장성군관광문화재단 사무실 리모델링 건축공사",
            key=f"calc_notice_manual_{tab_prefix}"
        )

    base_input = st.text_input(
        "💰 기초금액 입력 (원)",
        placeholder="예: 150000000",
        key=f"calc_base_{tab_prefix}"
    )

    if not (notice_input and base_input):
        st.markdown(
            '<div class="guide-box">'
            '📌 <b>1단계</b>: 입찰할 공고명을 입력하세요 (발주기관이 자동으로 탐지됩니다)<br>'
            '📌 <b>2단계</b>: 기초금액을 입력하면 핫존 분석이 시작됩니다<br>'
            '📌 <b>3단계</b>: 핫존을 선택하면 0.01% 단위 정밀 추천 투찰가가 즉시 산출됩니다'
            '</div>', unsafe_allow_html=True)
        return

    base_clean = base_input.replace(',', '').replace('원', '').strip()
    try:
        base_price = int(float(base_clean))
    except Exception:
        st.error("기초금액을 숫자로 입력해주세요. 예: 150000000")
        return

    stopwords = {'공사', '용역', '설치', '사업', '시공', '및', '기타', '위한', '에', '의', '을', '를', '위', '에서'}
    keywords = [w for w in re.findall(r'[가-힣]{2,}', notice_input) if w not in stopwords]

    if not keywords:
        st.warning("공고명에서 검색 키워드를 추출할 수 없습니다. 더 구체적인 공고명을 입력해주세요.")
        return

    pattern = '|'.join(keywords[:5])
    matched_notices = master_df[master_df['공고명'].str.contains(pattern, na=False)]

    if matched_notices.empty:
        st.warning(f"'{notice_input}' 와 유사한 공고 데이터가 없습니다.")
        return

    inst_candidates = matched_notices['발주기관'].value_counts()
    st.success(f"🔍 공고명 키워드 `{'`, `'.join(keywords[:5])}`로 **{len(matched_notices)}건** 유사 공고 탐지 — 발주기관 **{len(inst_candidates)}곳** 확인")

    inst_select = st.selectbox(
        f"🏛️ 분석할 발주기관 선택 ({len(inst_candidates)}곳 탐지됨)",
        inst_candidates.index.tolist(),
        format_func=lambda x: f"{x} ({inst_candidates[x]}건 유사공고)",
        key=f"calc_inst_select_{tab_prefix}"
    )

    r = engine_bid_calculator(inst_select, base_price, master_df)
    if r is None:
        st.warning("해당 발주기관의 데이터가 부족합니다.")
        return

    st.markdown("---")
    st.markdown(f"**'{inst_select}' 3년 {r['total']}건 실제 데이터 분석 결과**")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f'<div class="calc-result">'
            f'<div class="calc-label">⭐ 최다발생 구간 추천가</div>'
            f'<div class="calc-price">{r["recommended"]:,}원</div>'
            f'<div style="font-size:12px;color:#93c5fd;margin-top:4px;">투찰률 {r["best_rate"]}%</div>'
            f'</div>', unsafe_allow_html=True)
    with c2:
        st.markdown(
            f'<div class="calc-result">'
            f'<div class="calc-label">📊 평균 투찰률 기준</div>'
            f'<div class="calc-price">{r["avg_price"]:,}원</div>'
            f'<div style="font-size:12px;color:#93c5fd;margin-top:4px;">투찰률 {r["avg_rate"]}%</div>'
            f'</div>', unsafe_allow_html=True)
    with c3:
        st.markdown(
            f'<div class="calc-result">'
            f'<div class="calc-label">📈 중간값 기준</div>'
            f'<div class="calc-price">{r["mid_price"]:,}원</div>'
            f'<div style="font-size:12px;color:#93c5fd;margin-top:4px;">투찰률 {r["mid_rate"]}%</div>'
            f'</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 📊 1단계 — 0.1% 단위 핫존 분석")
    max_cnt = int(r['top5'].iloc[0])
    for rate_val, cnt in r['top5'].items():
        bar_w = int(cnt / max_cnt * 100)
        is_best = (rate_val == r['best_rate'])
        color = "#f59e0b" if is_best else "#3b82f6"
        star = " ⭐ 핫존" if is_best else ""
        price = int(base_price * rate_val / 100)
        st.markdown(
            f"""<div style="margin:5px 0;display:flex;align-items:center;gap:8px;">
                <span style="font-size:13px;font-weight:{'900' if is_best else '500'};width:90px;flex-shrink:0;">{rate_val}%{star}</span>
                <div style="background:{color};width:{bar_w}%;height:18px;border-radius:3px;min-width:3px;"></div>
                <span style="font-size:12px;font-weight:700;">{cnt}회 | {price:,}원</span>
            </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🔬 2단계 — 0.01% 돋보기 모드")
    st.markdown("👇 **핫존 구간을 선택하면 추천 투찰가가 바로 나옵니다.**")

    zone_options = [f"{v}%" for v in r['zone_01'].head(10).index.tolist()]
    selected_zone = st.selectbox(
        "🎯 분석할 핫존 구간 선택 (클릭하면 추천 투찰가 즉시 확인)",
        zone_options,
        key=f"zoom_zone_{tab_prefix}"
    )

    if selected_zone:
        hot_rate = float(selected_zone.replace('%', ''))
        zr = engine_zoom(r['df'], hot_rate, base_price)
        if zr is None:
            st.info("해당 구간의 데이터가 없습니다.")
        else:
            st.markdown(
                f'<div style="background:linear-gradient(135deg,#f59e0b,#d97706);color:white;border-radius:12px;'
                f'padding:18px;margin:10px 0;text-align:center;">'
                f'<div style="font-size:13px;font-weight:700;margin-bottom:6px;">🔬 {zr["lower"]}% ~ {zr["upper"]}% 구간 돋보기 분석 ({zr["total_sub"]}건)</div>'
                f'<div style="font-size:14px;margin-bottom:4px;">최다발생 구간: <b>{zr["best_001"]}%</b></div>'
                f'<div style="font-size:28px;font-weight:900;color:#1e3a8a;">⭐ 추천 투찰가</div>'
                f'<div style="font-size:32px;font-weight:900;margin-top:4px;">{zr["best_price"]:,}원</div>'
                f'<div style="font-size:12px;margin-top:6px;opacity:0.9;">투찰률 {zr["best_001"]}% × 기초금액 {base_price:,}원</div>'
                f'</div>', unsafe_allow_html=True)

            st.markdown(f"**📊 0.01% 단위 상세 분포** (상위 10개) — 원단위 금액 표시")
            max_z = int(zr['zone_001'].iloc[0]) if not zr['zone_001'].empty else 1
            for rate_val, cnt in zr['zone_001'].head(10).items():
                bar_w = int(cnt / max_z * 100)
                is_best = (rate_val == zr['best_001'])
                color = "#f59e0b" if is_best else "#10b981"
                star = " ⭐ 추천" if is_best else ""
                price = int(base_price * rate_val / 100)
                pct_of_total = round(cnt / zr['total_sub'] * 100, 1)
                st.markdown(
                    f"""<div style="margin:5px 0;display:flex;align-items:center;gap:8px;">
                        <span style="font-size:13px;font-weight:{'900' if is_best else '500'};width:100px;flex-shrink:0;color:{'#d97706' if is_best else 'inherit'};">{rate_val}%{star}</span>
                        <div style="background:{color};width:{bar_w}%;height:18px;border-radius:3px;min-width:3px;"></div>
                        <span style="font-size:12px;font-weight:700;">{cnt}회({pct_of_total}%) | <b>{price:,}원</b></span>
                    </div>""", unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("**📋 투찰가 추천 정리**")
            tbl_data = []
            zone_001_idx = list(zr['zone_001'].head(5).index)
            for rate_val, cnt in zr['zone_001'].head(5).items():
                price = int(base_price * rate_val / 100)
                is_best = (rate_val == zr['best_001'])
                rank_str = "⭐ 1위 추천" if is_best else f"{zone_001_idx.index(rate_val)+1}위"
                tbl_data.append({
                    '순위': rank_str,
                    '투찰률': f"{rate_val}%",
                    '투찰금액 (원단위)': f"{price:,}원",
                    '낙찰 빈도': f"{cnt}회"
                })
            st.dataframe(pd.DataFrame(tbl_data), use_container_width=True, hide_index=True)

    st.caption("* 3년 실제 낙찰 데이터 기준. 투찰 결정은 본인 판단으로 하세요.")


# ==========================================
# 🏆 낙찰스코어 렌더 함수
# ==========================================
def render_bid_score(master_df, live_df_func, tab_prefix):
    st.markdown("""
    <div class="score-hero">
        <div class="score-hero-badge">🏆 낙찰 확률 점수화 · 5가지 팩트 기반</div>
        <div class="score-hero-title">🎯 <span>낙찰스코어</span></div>
        <div class="score-hero-sub">
            내가 생각한 투찰률이 실제로 1순위가 될 확률을<br>
            <b style="color:white;">5가지 항목 · 100점 만점</b>으로 즉시 채점
        </div>
        <div class="score-chips">
            <div class="score-chip">🔥 핫존 일치도 30점</div>
            <div class="score-chip">⚔️ 경쟁 강도 20점</div>
            <div class="score-chip">🔍 유사공고 적중 20점</div>
            <div class="score-chip">📐 투찰률 안정성 15점</div>
            <div class="score-chip">📦 데이터 충분성 15점</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("📖 낙찰스코어 채점 기준 보기"):
        st.markdown("""
        | 등급 | 점수 범위 | 의미 | 예상 낙찰 확률 |
        |------|-----------|------|---------------|
        | **S등급** | 85~100점 | 최상위 낙찰 가능성 | 75~90% |
        | **A등급** | 70~84점  | 높은 낙찰 가능성   | 55~75% |
        | **B등급** | 55~69점  | 보통 수준           | 35~55% |
        | **C등급** | 40~54점  | 낙찰 가능성 낮음    | 15~35% |
        | **D등급** | 0~39점   | 매우 낮음           | 5~15%  |

        **채점 항목 상세:**
        - 🔥 **핫존 일치도 (30점)**: 내 투찰률이 발주기관 최다발생 구간과 얼마나 가까운지
        - ⚔️ **경쟁 강도 (20점)**: 독식업체 점유율이 낮을수록 높은 점수
        - 🔍 **유사공고 적중 (20점)**: 유사 공고명의 낙찰 구간과 내 투찰률의 일치도
        - 📐 **투찰률 안정성 (15점)**: 해당 발주기관의 투찰률 표준편차가 좁을수록 예측 신뢰도 높음
        - 📦 **데이터 충분성 (15점)**: 분석 근거 데이터가 많을수록 신뢰도 상승

        > ⚠️ 낙찰스코어는 3년 실제 낙찰 데이터 기반의 통계적 참고 지표입니다. 최종 투찰 결정은 반드시 본인 판단으로 하세요.
        """)

    if master_df is None or master_df.empty:
        st.info("3년 마스터 데이터가 없습니다.")
        return

    st.markdown("---")

    st.markdown("""
    <div class="calc-input-section">
        <div class="calc-input-title">📝 채점할 공고 정보 입력</div>
    </div>
    """, unsafe_allow_html=True)

    df_live_score = live_df_func() if live_df_func else pd.DataFrame()
    notice_input = ""

    if not df_live_score.empty and '공고명' in df_live_score.columns:
        live_notices = df_live_score['공고명'].dropna().tolist()
        select_options = ["✏️ 직접 입력 (공고명 타이핑)"] + live_notices
        selected_notice = st.selectbox(
            "📋 공고 선택 또는 직접 입력",
            select_options,
            key=f"score_notice_select_{tab_prefix}",
        )
        if selected_notice == "✏️ 직접 입력 (공고명 타이핑)":
            notice_input = st.text_input(
                "📋 공고명 직접 입력",
                placeholder="예: 여수시 도로 포장 보수공사",
                key=f"score_notice_manual_{tab_prefix}"
            )
        else:
            notice_input = selected_notice
            st.markdown(
                f'<div style="background:#f5f3ff;border:1px solid #c4b5fd;border-radius:8px;'
                f'padding:8px 14px;margin:4px 0;font-size:13px;color:#4c1d95;">'
                f'✅ 선택된 공고: <b>{selected_notice}</b>'
                f'</div>', unsafe_allow_html=True)
    else:
        notice_input = st.text_input(
            "📋 공고명 입력",
            placeholder="예: 여수시 도로 포장 보수공사",
            key=f"score_notice_manual_{tab_prefix}"
        )

    col_rate, col_base = st.columns(2)
    with col_rate:
        my_rate_input = st.text_input(
            "🎯 내가 생각한 투찰률 입력 (%)",
            placeholder="예: 87.345",
            key=f"score_rate_{tab_prefix}",
            help="소수점 3자리까지 입력 가능합니다. 예: 87.345"
        )
    with col_base:
        base_input_score = st.text_input(
            "💰 기초금액 입력 (원, 선택)",
            placeholder="예: 150000000 (없으면 비워두세요)",
            key=f"score_base_{tab_prefix}",
            help="기초금액을 입력하면 투찰가도 함께 계산됩니다."
        )

    if not (notice_input and my_rate_input):
        st.markdown(
            '<div class="guide-box">'
            '📌 <b>1단계</b>: 입찰할 공고명을 입력하세요<br>'
            '📌 <b>2단계</b>: 내가 생각한 투찰률(%)을 입력하세요<br>'
            '📌 <b>3단계</b>: 발주기관을 선택하면 낙찰스코어가 즉시 산출됩니다<br>'
            '💡 기초금액을 함께 입력하면 투찰금액도 계산됩니다'
            '</div>', unsafe_allow_html=True)
        return

    try:
        my_rate = float(my_rate_input.replace('%', '').strip())
        if not (50 <= my_rate <= 110):
            st.error("투찰률은 50~110% 사이의 값을 입력해주세요.")
            return
    except Exception:
        st.error("투찰률을 숫자로 입력해주세요. 예: 87.345")
        return

    base_price = 0
    if base_input_score.strip():
        try:
            base_price = int(float(base_input_score.replace(',', '').replace('원', '').strip()))
        except Exception:
            st.warning("기초금액 형식이 올바르지 않아 금액 계산을 건너뜁니다.")

    stopwords = {'공사', '용역', '설치', '사업', '시공', '및', '기타', '위한', '에', '의', '을', '를', '위', '에서'}
    keywords = [w for w in re.findall(r'[가-힣]{2,}', notice_input) if w not in stopwords]

    if not keywords:
        st.warning("공고명에서 키워드를 추출할 수 없습니다. 더 구체적인 공고명을 입력해주세요.")
        return

    pattern = '|'.join(keywords[:5])
    matched_notices = master_df[master_df['공고명'].str.contains(pattern, na=False)]

    if matched_notices.empty:
        st.warning(f"'{notice_input}' 와 유사한 공고 데이터가 없습니다.")
        return

    inst_candidates = matched_notices['발주기관'].value_counts()
    st.success(f"🔍 키워드 `{'`, `'.join(keywords[:4])}`로 **{len(matched_notices)}건** 유사 공고 탐지 — 발주기관 **{len(inst_candidates)}곳** 확인")

    inst_select = st.selectbox(
        f"🏛️ 채점할 발주기관 선택 ({len(inst_candidates)}곳 탐지됨)",
        inst_candidates.index.tolist(),
        format_func=lambda x: f"{x} ({inst_candidates[x]}건 유사공고)",
        key=f"score_inst_select_{tab_prefix}"
    )

    r = engine_bid_score(inst_select, notice_input, my_rate, base_price, master_df)
    if r is None:
        st.warning("해당 발주기관의 데이터가 부족합니다.")
        return

    st.markdown("---")

    score = r['total_score']
    grade_color = r['grade_color']
    bg_color = r['bg_color']
    gauge_pct = min(score, 100)

    st.markdown(
        f'<div class="score-gauge-wrap" style="background:{bg_color};">'
        f'<div class="score-gauge-label">낙찰스코어 — {inst_select} 기준</div>'
        f'<div class="score-gauge-num" style="color:{grade_color};">{score}점</div>'
        f'<div style="background:rgba(255,255,255,0.15);border-radius:20px;height:14px;margin:8px 0;">'
        f'<div style="background:{grade_color};width:{gauge_pct}%;height:14px;border-radius:20px;'
        f'transition:width 0.5s ease;"></div></div>'
        f'<div class="score-gauge-grade" style="color:{grade_color};">{r["grade_label"]}</div>'
        f'<div class="score-gauge-desc">예상 낙찰 확률: <b style="color:{grade_color};">{r["win_prob"]}</b>'
        f' &nbsp;·&nbsp; 분석 근거: {r["total_data"]}건 실제 데이터</div>'
        f'</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 📊 내 투찰률 vs 발주기관 핫존 비교")
    cmp1, cmp2, cmp3 = st.columns(3)
    with cmp1:
        my_price_str = f"{r['my_bid_price']:,}원" if base_price else "-"
        st.markdown(
            f'<div class="score-item-card">'
            f'<div class="score-item-title">🎯 내가 입력한 투찰률</div>'
            f'<div class="score-item-val">{my_rate}%</div>'
            f'<div class="score-item-desc">{my_price_str}</div>'
            f'</div>', unsafe_allow_html=True)
    with cmp2:
        best_price_str = f"{r['best_bid_price']:,}원" if base_price else "-"
        st.markdown(
            f'<div class="score-item-card" style="background:#fef3c7;border-color:#fde68a;">'
            f'<div class="score-item-title" style="color:#92400e;">⭐ 발주기관 핫존 (최다발생)</div>'
            f'<div class="score-item-val" style="color:#d97706;">{r["best_rate_01"]}%</div>'
            f'<div class="score-item-desc">{best_price_str}</div>'
            f'</div>', unsafe_allow_html=True)
    with cmp3:
        diff = round(my_rate - r['best_rate_01'], 3)
        diff_str = f"+{diff}%" if diff > 0 else f"{diff}%"
        diff_color = "#ef4444" if abs(diff) > 0.5 else ("#f97316" if abs(diff) > 0.2 else "#10b981")
        st.markdown(
            f'<div class="score-item-card">'
            f'<div class="score-item-title">📏 핫존과의 거리</div>'
            f'<div class="score-item-val" style="color:{diff_color};">{diff_str}</div>'
            f'<div class="score-item-desc">{"⚠️ 조정 필요" if abs(diff) > 0.5 else ("💡 미세조정 권장" if abs(diff) > 0.1 else "✅ 핫존 내")}</div>'
            f'</div>', unsafe_allow_html=True)

    st.markdown("#### 📈 발주기관 투찰률 핫존 분포 (내 투찰률 위치 표시)")
    zone_01 = r['zone_01']
    my_zone_key = round(my_rate // 0.1 * 0.1, 1)
    max_zone_cnt = int(zone_01.iloc[0]) if not zone_01.empty else 1
    for rate_val, cnt in zone_01.head(12).items():
        bar_w = int(cnt / max_zone_cnt * 100)
        is_best = (rate_val == r['best_rate_01'])
        is_mine = (abs(rate_val - my_zone_key) < 0.05)
        if is_mine and is_best:
            color = "#a855f7"
            tag = " ⭐🎯 핫존+내투찰"
        elif is_best:
            color = "#f59e0b"
            tag = " ⭐ 핫존"
        elif is_mine:
            color = "#a855f7"
            tag = " 🎯 내 투찰 위치"
        else:
            color = "#6366f1"
            tag = ""
        price_disp = f" | {int(base_price * rate_val / 100):,}원" if base_price else ""
        st.markdown(
            f"""<div style="margin:4px 0;display:flex;align-items:center;gap:8px;">
                <span style="font-size:12px;font-weight:{'900' if (is_best or is_mine) else '400'};
                width:85px;flex-shrink:0;color:{'#a855f7' if is_mine else ('inherit')}">{rate_val}%{tag}</span>
                <div style="background:{color};width:{bar_w}%;height:16px;border-radius:3px;min-width:2px;"></div>
                <span style="font-size:12px;font-weight:700;">{cnt}회{price_disp}</span>
            </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 🗂️ 항목별 채점 결과")

    items = [
        ("🔥 핫존 일치도", r['score_hotzone'], 30,
         f"내 투찰률 {my_rate}% ↔ 핫존 {r['best_rate_01']}% (거리: {abs(my_rate - r['best_rate_01']):.3f}%)"),
        ("⚔️ 경쟁 강도", r['score_competition'], 20,
         f"독식업체 '{r['top_corp']}' 점유율 {r['monopoly_rate']}%"),
        ("🔍 유사공고 적중", r['score_similar'], 20,
         f"유사공고 {r['similar_count']}건 분석 · 유사공고 핫존: {r['similar_best_zone']}%" if r['similar_best_zone'] else "유사공고 데이터 없음"),
        ("📐 투찰률 안정성", r['score_stability'], 15,
         f"발주기관 표준편차 ±{r['std_rate']}% (좁을수록 예측 신뢰도 높음)"),
        ("📦 데이터 충분성", r['score_data'], 15,
         f"분석 근거 데이터 {r['total_data']}건"),
    ]

    for item_name, item_score, item_max, item_desc in items:
        pct = int(item_score / item_max * 100)
        bar_color = "#10b981" if pct >= 80 else ("#3b82f6" if pct >= 50 else ("#f97316" if pct >= 30 else "#ef4444"))
        st.markdown(
            f'<div class="score-item-card">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:5px;">'
            f'<span class="score-item-title">{item_name}</span>'
            f'<span style="font-size:16px;font-weight:900;color:{bar_color};">{item_score}/{item_max}점</span>'
            f'</div>'
            f'<div style="background:#e5e7eb;border-radius:10px;height:10px;margin-bottom:5px;">'
            f'<div style="background:{bar_color};width:{pct}%;height:10px;border-radius:10px;"></div></div>'
            f'<div class="score-item-desc">{item_desc}</div>'
            f'</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 💡 낙찰스코어 AI 조언")
    advice_html = "".join([f"<div style='margin:5px 0;'>• {a}</div>" for a in r['advice']])
    st.markdown(
        f'<div class="score-advice">'
        f'<div class="score-advice-title">🤖 {r["grade_label"]} 맞춤 전략</div>'
        f'{advice_html}'
        f'</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(
        '<div class="guide-box">'
        '💡 <b>다음 단계</b>: 투찰가 계산기 → 0.01% 단위 핫존 정밀 분석으로 최종 투찰가를 확정하세요.<br>'
        '📊 <b>참고</b>: 낙찰스코어는 통계 기반 참고 지표입니다. 최종 결정은 반드시 본인 판단으로 하세요.'
        '</div>', unsafe_allow_html=True)

    st.caption(f"* 분석 기준: {r['total_data']}건 실제 낙찰 데이터 · 추정 없음 · 3년 팩트 데이터 기반")


# ==========================================
# 8. Firebase 데이터 로딩 — 공사 / 용역 분리
# ==========================================
DISPLAY_DAYS = 15


def _parse_dt(val):
    if not val or str(val).strip() in ('', 'nan', 'None', '-'):
        return pd.NaT
    s = str(val).strip()
    s = s.replace('-', '').replace(':', '').replace(' ', '').replace('.', '')
    try:
        if len(s) >= 12:
            return pd.to_datetime(s[:12], format='%Y%m%d%H%M')
        elif len(s) == 8:
            return pd.to_datetime(s, format='%Y%m%d')
        else:
            return pd.NaT
    except Exception:
        return pd.NaT


@st.cache_data(ttl=600, show_spinner=False)
def get_hybrid_1st_bids():
    try:
        cutoff_str = (datetime.now(KST).replace(tzinfo=None) - timedelta(days=DISPLAY_DAYS)).strftime('%Y-%m-%d')
        db_data = (db.child("archive_1st").order_by_child("날짜").start_at(cutoff_str).get().val()) or {}
        db_items = list(db_data.values()) if isinstance(db_data, dict) else []
    except Exception:
        try:
            db_data = db.child("archive_1st").order_by_key().limit_to_last(500).get().val() or {}
            db_items = list(db_data.values()) if isinstance(db_data, dict) else []
        except Exception:
            db_items = []
    if not db_items:
        return pd.DataFrame()
    df = pd.DataFrame(db_items)
    if df.empty or '공고번호' not in df.columns:
        return pd.DataFrame()
    df = df.drop_duplicates(subset=['공고번호']).copy()
    df['dt'] = df['날짜'].apply(_parse_dt) if '날짜' in df.columns else pd.NaT
    df = df.sort_values(by='dt', ascending=False, na_position='last')
    df['날짜'] = df['dt'].apply(lambda x: x.strftime('%m-%d %H:%M') if pd.notna(x) else '-')
    return df.drop(columns=['dt'])


@st.cache_data(ttl=600, show_spinner=False)
def get_hybrid_live_bids():
    try:
        cutoff_str = (datetime.now(KST).replace(tzinfo=None) - timedelta(days=DISPLAY_DAYS)).strftime('%Y-%m-%d')
        db_data = (db.child("archive_live").order_by_child("공고일자").start_at(cutoff_str).get().val()) or {}
        db_items = list(db_data.values()) if isinstance(db_data, dict) else []
    except Exception:
        try:
            db_data = db.child("archive_live").order_by_key().limit_to_last(500).get().val() or {}
            db_items = list(db_data.values()) if isinstance(db_data, dict) else []
        except Exception:
            db_items = []
    if not db_items:
        return pd.DataFrame()
    df = pd.DataFrame(db_items)
    if df.empty or '공고번호' not in df.columns:
        return pd.DataFrame()
    df = df.drop_duplicates(subset=['공고번호']).copy()
    df['dt'] = df['공고일자'].apply(_parse_dt) if '공고일자' in df.columns else pd.NaT
    df = df.sort_values(by='dt', ascending=False, na_position='last')
    df['공고일자'] = df['dt'].apply(lambda x: x.strftime('%m-%d %H:%M') if pd.notna(x) else '-')
    return df.drop(columns=['dt'])


@st.cache_data(ttl=600, show_spinner=False)
def get_hybrid_1st_bids_serv():
    try:
        cutoff_str = (datetime.now(KST).replace(tzinfo=None) - timedelta(days=DISPLAY_DAYS)).strftime('%Y-%m-%d')
        db_data = (db.child("service_1st").order_by_child("날짜").start_at(cutoff_str).get().val()) or {}
        db_items = list(db_data.values()) if isinstance(db_data, dict) else []
    except Exception:
        try:
            db_data = db.child("service_1st").order_by_key().limit_to_last(500).get().val() or {}
            db_items = list(db_data.values()) if isinstance(db_data, dict) else []
        except Exception:
            db_items = []
    if not db_items:
        return pd.DataFrame()
    df = pd.DataFrame(db_items)
    if df.empty or '공고번호' not in df.columns:
        return pd.DataFrame()
    df = df.drop_duplicates(subset=['공고번호']).copy()
    df['dt'] = df['날짜'].apply(_parse_dt) if '날짜' in df.columns else pd.NaT
    df = df.sort_values(by='dt', ascending=False, na_position='last')
    df['날짜'] = df['dt'].apply(lambda x: x.strftime('%m-%d %H:%M') if pd.notna(x) else '-')
    return df.drop(columns=['dt'])


@st.cache_data(ttl=600, show_spinner=False)
def get_hybrid_live_bids_serv():
    try:
        cutoff_str = (datetime.now(KST).replace(tzinfo=None) - timedelta(days=DISPLAY_DAYS)).strftime('%Y-%m-%d')
        db_data = (db.child("service_live").order_by_child("공고일자").start_at(cutoff_str).get().val()) or {}
        db_items = list(db_data.values()) if isinstance(db_data, dict) else []
    except Exception:
        try:
            db_data = db.child("service_live").order_by_key().limit_to_last(500).get().val() or {}
            db_items = list(db_data.values()) if isinstance(db_data, dict) else []
        except Exception:
            db_items = []
    if not db_items:
        return pd.DataFrame()
    df = pd.DataFrame(db_items)
    if df.empty or '공고번호' not in df.columns:
        return pd.DataFrame()
    df = df.drop_duplicates(subset=['공고번호']).copy()
    df['dt'] = df['공고일자'].apply(_parse_dt) if '공고일자' in df.columns else pd.NaT
    df = df.sort_values(by='dt', ascending=False, na_position='last')
    df['공고일자'] = df['dt'].apply(lambda x: x.strftime('%m-%d %H:%M') if pd.notna(x) else '-')
    return df.drop(columns=['dt'])


def fetch_detail(row):
    suc_amt = row.get('투찰금액', '-')
    rate = row.get('투찰률', '-')
    corps = []
    corp_raw = row.get('전체업체', '')
    if corp_raw:
        for idx, c in enumerate(str(corp_raw).split('|')[:10]):
            p = c.split('^')
            if len(p) >= 5:
                try:
                    amt_disp = f"{int(float(p[3])):,}원"
                except Exception:
                    amt_disp = p[3]
                corps.append({'순위': f"{idx+1}위", '업체명': p[0].strip(),
                              '투찰금액': amt_disp, '투찰률': f"{p[4].strip()}%"})
    return {'suc_amt': suc_amt, 'rate': rate, 'corps': corps}


# ==========================================
# ✅ 비로그인 사용자 전용 화면 (로그인/회원가입)
# ==========================================
def render_login_page():
    """로그인하지 않은 사용자에게 보여주는 전용 화면"""
    st.markdown("""
    <div class="login-hero">
        <div style="font-size:3rem;margin-bottom:12px;">🏛️</div>
        <div class="login-hero-title">K-건설맵 Master</div>
        <div class="login-hero-sub">
            전국 건설·용역 입찰 데이터 분석 플랫폼<br>
            <b>회원 전용 서비스</b>입니다. 로그인 후 이용해 주세요.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 기능 소개 카드
    f1, f2, f3 = st.columns(3)
    with f1:
        st.markdown("""
        <div class="login-feature-card">
            <div class="login-feature-icon">📊</div>
            <div class="login-feature-title">실시간 입찰 공고</div>
            <div class="login-feature-desc">전국 건설·용역 공고를 15분마다 자동 수집하여 즉시 확인</div>
        </div>
        """, unsafe_allow_html=True)
    with f2:
        st.markdown("""
        <div class="login-feature-card">
            <div class="login-feature-icon">🧮</div>
            <div class="login-feature-title">투찰가 계산기</div>
            <div class="login-feature-desc">3년 실제 낙찰 데이터 기반 0.01% 단위 원단위 추천가 산출</div>
        </div>
        """, unsafe_allow_html=True)
    with f3:
        st.markdown("""
        <div class="login-feature-card">
            <div class="login-feature-icon">🏆</div>
            <div class="login-feature-title">낙찰스코어</div>
            <div class="login-feature-desc">내 투찰률의 1순위 가능성을 100점 만점으로 즉시 채점</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 로그인 / 회원가입 탭
    tab_login, tab_register = st.tabs(["🔑 로그인", "📝 무료 회원가입"])

    with tab_login:
        st.markdown("#### 로그인")
        le = st.text_input("이메일", key="login_email_gate")
        lp = st.text_input("비밀번호", type="password", key="login_pw_gate")
        if st.button("🔑 로그인하기", use_container_width=True, type="primary", key="login_btn_gate"):
            if not le or not lp:
                st.error("이메일과 비밀번호를 입력해주세요.")
            else:
                try:
                    user = auth.sign_in_with_email_and_password(le.strip().lower(), lp)
                    info = db.child("users").child(user['localId']).get().val() or {}
                    st.session_state.update({
                        'logged_in': True,
                        'user_name': info.get('name', '소장님'),
                        'user_license': info.get('license', ''),
                        'user_phone': info.get('phone', ''),
                        'localId': user['localId'],
                        'idToken': user['idToken'],
                        'user_email': le.strip().lower()
                    })
                    st.success(f"✅ {info.get('name', '소장님')}님, 환영합니다!")
                    time.sleep(0.8)
                    st.rerun()
                except Exception:
                    st.error("로그인 실패! 이메일 또는 비밀번호를 확인해주세요.")

    with tab_register:
        st.markdown("#### 무료 회원가입")
        re_email = st.text_input("이메일", key="reg_email_gate")
        re_pw = st.text_input("비밀번호 (6자 이상)", type="password", key="reg_pw_gate")
        re_name = st.text_input("성함", key="reg_name_gate")
        re_lic = st.multiselect("보유 면허 (맞춤 매칭용, 선택)", ALL_LICENSES, key="reg_lic_gate")
        if st.button("🎉 무료 가입하기", use_container_width=True, type="primary", key="reg_btn_gate"):
            if not re_email or not re_pw or not re_name:
                st.error("이메일, 비밀번호, 성함을 모두 입력해주세요.")
            else:
                try:
                    u = auth.create_user_with_email_and_password(re_email.strip().lower(), re_pw)
                    db.child("users").child(u['localId']).set({
                        "name": re_name, "license": ", ".join(re_lic), "email": re_email
                    })
                    try:
                        curr_u = db.child("stats").child("total_users").get().val() or 0
                        db.child("stats").update({"total_users": int(curr_u) + 1})
                    except Exception:
                        pass
                    st.success("🎉 가입 성공! 이제 로그인해주세요.")
                except Exception:
                    st.error("가입 실패! 이미 사용 중인 이메일이거나 비밀번호가 6자 미만입니다.")


# ==========================================
# 9. 팝업 다이얼로그 (master_df + tab_prefix 동적 전달)
# ==========================================
@st.dialog("📋 K-건설맵 팩트 리포트", width="large")
def show_analysis_dialog(row, det, mode="1st", master_df=None, tab_prefix="c"):
    if master_df is None:
        master_df = big_data

    if mode == "1st":
        st.markdown(f"### {row['공고명']}")
        col1, col2 = st.columns(2)
        col1.markdown(
            f'<div class="stat-card"><div class="stat-label">🏆 낙찰금액 (실제)</div>'
            f'<div class="stat-val" style="color:#dc2626;">{det["suc_amt"]}</div></div>',
            unsafe_allow_html=True)
        col2.markdown(
            f'<div class="stat-card"><div class="stat-label">📊 투찰률 (실제)</div>'
            f'<div class="stat-val">{det["rate"]}</div></div>',
            unsafe_allow_html=True)

        if det['corps']:
            st.markdown("**[개찰 결과 — 실제 데이터]**")
            st.dataframe(pd.DataFrame(det['corps']), use_container_width=True, hide_index=True)

        if master_df is not None and not master_df.empty:
            st.markdown("---")
            st.markdown("#### 📊 3년 팩트 분석")
            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "🎯 투찰률 히트맵", "🏆 독식업체", "📅 발주패턴", "🔍 유사공고", "🏢 자가진단"
            ])
            inst_name = row.get('발주기관', '')
            notice_name = row.get('공고명', '')
            with tab1: render_heatmap(inst_name, master_df)
            with tab2: render_dominant(inst_name, master_df)
            with tab3: render_pattern(inst_name, master_df)
            with tab4: render_similar(notice_name, inst_name, master_df)
            with tab5:
                corp_search = st.text_input(
                    "🔍 우리 회사명 입력", placeholder="예: 한국건설",
                    key=f"sd_{mode}_{tab_prefix}"
                )
                if corp_search:
                    render_self_diagnosis(corp_search, master_df)

        st.markdown("---")
        sc1, sc2 = st.columns(2)
        with sc1:
            st.markdown("💡 **나라장터 정책상 번호 복사가 필요합니다.**")
            st.code(row['공고번호'], language=None)
        with sc2:
            st.link_button("🚀 나라장터 홈페이지", "https://www.g2b.go.kr/index.jsp", use_container_width=True)
            corp_name_for_search = row.get('1순위업체', '')
            st.link_button("🏢 업체 네이버 검색",
                           f"https://search.naver.com/search.naver?query={corp_name_for_search} 건설",
                           use_container_width=True)

    elif mode == "live":
        inst_name = row.get('발주기관', '')
        notice_name = row.get('공고명', '')
        st.markdown("### 🎯 입찰 준비 종합 분석")
        st.markdown(f"**발주기관:** `{inst_name}`")
        st.markdown(f"**공고명:** {notice_name}")

        if master_df is not None and not master_df.empty:
            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "🎯 투찰률 히트맵", "🏆 독식업체", "📅 발주패턴", "🔍 유사공고", "🏢 자가진단"
            ])
            with tab1: render_heatmap(inst_name, master_df)
            with tab2: render_dominant(inst_name, master_df)
            with tab3: render_pattern(inst_name, master_df)
            with tab4: render_similar(notice_name, inst_name, master_df)
            with tab5:
                corp_search = st.text_input(
                    "🔍 우리 회사명 입력", placeholder="예: 한국건설",
                    key=f"sd_{mode}_{tab_prefix}"
                )
                if corp_search:
                    render_self_diagnosis(corp_search, master_df)
        else:
            st.info("3년 마스터 데이터가 없습니다.")

    elif mode == "job":
        st.markdown("### 🤝 구인/구직 상세내용")
        st.write(f"**제목:** {row['title']} | **지역:** {row['region']}")
        st.write(f"**작성자:** {row['author']} | **연락처:** {row['phone']}")
        st.markdown("---")
        st.write(row['content'])


# ==========================================
# 🔥 홈 대문 렌더링 (로그인 후만 표시)
# ==========================================
def render_landing_page(t_visit):
    today_str = datetime.now(KST).strftime("%Y년 %m월 %d일")
    total_count = get_total_data_count()
    total_data_str = f"{total_count:,}+" if total_count > 0 else "152,430+"

    df_live_con = get_hybrid_live_bids()
    df_live_srv = get_hybrid_live_bids_serv()

    st.markdown(f"""
        <div class="hero-banner">
            <div class="hero-date-badge">
                <span class="hero-live-dot"></span>{today_str}
            </div>
            <div class="hero-main-title">
                데이터가 말하는 정확한 투찰가
            </div>
            <div class="hero-sub-title">
                나라장터 전국 건설·용역 입찰 공고를 실시간으로 수집하고,<br>
                3년치 실제 낙찰 데이터로 <b>발주기관별 투찰률 히트맵</b>과<br>
                <b>0.01% 단위 원단위 추천 투찰가</b>를 즉시 산출합니다.
            </div>
            <div class="hero-desc">
                추정 없는 팩트 데이터만 사용 &nbsp;·&nbsp; 공사·용역 분야 통합 지원<br>
                15분 간격 개찰 자동 업데이트 &nbsp;·&nbsp; 발주기관·업체 심층 분석
            </div>
        </div>
    """, unsafe_allow_html=True)

    c_btn1, c_btn2, c_btn3 = st.columns(3)
    with c_btn1:
        if st.button("🏗️ 건설·공사 실시간 공고", use_container_width=True, key="qbtn_con"):
            st.session_state['main_cat'] = "🏗️ 건설·공사"
            st.session_state['menu_c'] = "📊 실시간 공고 (홈)"
            st.rerun()
    with c_btn2:
        if st.button("💼 용역·서비스 실시간 공고", use_container_width=True, key="qbtn_srv"):
            st.session_state['main_cat'] = "💼 용역·서비스"
            st.session_state['menu_s'] = "📊 실시간 공고 (홈)"
            st.rerun()
    with c_btn3:
        if st.button("🧮 투찰가 계산기 바로가기", use_container_width=True, key="qbtn_calc"):
            st.session_state['main_cat'] = "🏗️ 건설·공사"
            st.session_state['menu_c'] = "🧮 투찰가 계산기"
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    _, c_score, _ = st.columns([1, 2, 1])
    with c_score:
        if st.button("🏆 낙찰스코어 — 내 투찰률 즉시 채점하기", use_container_width=True, key="qbtn_score"):
            st.session_state['main_cat'] = "🏗️ 건설·공사"
            st.session_state['menu_c'] = "🏆 낙찰스코어"
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    live_con_count = len(df_live_con) if not df_live_con.empty else 0
    live_srv_count = len(df_live_srv) if not df_live_srv.empty else 0
    live_total = live_con_count + live_srv_count

    st.markdown(
        "<h2 style='text-align:center; color:#1e3a8a; margin-bottom:28px; "
        "font-size:1.6rem; font-weight:800; letter-spacing:-0.5px;'>"
        "📈 실시간 팩트 데이터 현황</h2>",
        unsafe_allow_html=True
    )

    s1, s2, s3, s4 = st.columns(4)
    with s1:
        st.markdown(
            f'<div class="stat-card-landing">'
            f'<div class="stat-val-landing">{total_data_str}</div>'
            f'<div class="stat-txt-landing">누적 분석 데이터<br>'
            f'<span style="font-size:0.75rem;color:#94a3b8;font-weight:400;">(공사+용역 3년치)</span></div>'
            f'</div>', unsafe_allow_html=True)
    with s2:
        st.markdown(
            f'<div class="stat-card-landing">'
            f'<div class="stat-val-landing">{live_total:,}건</div>'
            f'<div class="stat-txt-landing">오늘의 실시간 공고<br>'
            f'<span style="font-size:0.75rem;color:#94a3b8;font-weight:400;">'
            f'(공사 {live_con_count}건 + 용역 {live_srv_count}건)</span></div>'
            f'</div>', unsafe_allow_html=True)
    with s3:
        st.markdown(
            '<div class="stat-card-landing">'
            '<div class="stat-val-landing">0.01%</div>'
            '<div class="stat-txt-landing">투찰률 분석 정밀도<br>'
            '<span style="font-size:0.75rem;color:#94a3b8;font-weight:400;">(원단위 추천가 산출)</span></div>'
            '</div>', unsafe_allow_html=True)
    with s4:
        st.markdown(
            f'<div class="stat-card-landing">'
            f'<div class="stat-val-landing">{t_visit:,}명</div>'
            f'<div class="stat-txt-landing">누적 방문자<br>'
            f'<span style="font-size:0.75rem;color:#94a3b8;font-weight:400;">(Firebase 실시간 집계)</span></div>'
            f'</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(
        "<h3 style='color:#1e3a8a;font-size:1.2rem;font-weight:800;"
        "margin-bottom:14px;letter-spacing:-0.3px;'>"
        "📋 실시간 입찰 공고 미리보기</h3>",
        unsafe_allow_html=True
    )

    col_con, col_srv = st.columns(2)

    with col_con:
        st.markdown('<div class="preview-wrap">', unsafe_allow_html=True)
        st.markdown('<div class="preview-title">🏗️ 건설·공사 최신 5건</div>', unsafe_allow_html=True)
        if not df_live_con.empty:
            for _, prow in df_live_con.head(5).iterrows():
                pname = str(prow.get('공고명', ''))[:28]
                porg  = str(prow.get('발주기관', ''))[:16]
                pamt_raw = prow.get('예산금액', 0)
                pamt_str = f"{raw_to_int(pamt_raw)//10000:,}만원" if raw_to_int(pamt_raw) > 0 else '-'
                st.markdown(
                    f'<div class="preview-row">'
                    f'<span class="pr-name">{pname}</span>'
                    f'<span class="pr-amt">{pamt_str}</span>'
                    f'<span class="pr-org">{porg}</span>'
                    f'</div>', unsafe_allow_html=True)
        else:
            st.markdown('<p style="font-size:12px;color:#94a3b8;padding:8px 0;">공고 데이터 로드 중...</p>',
                        unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        if st.button("건설·공사 전체 보기 →", use_container_width=True, key="btn_con_all"):
            st.session_state['main_cat'] = "🏗️ 건설·공사"
            st.session_state['menu_c'] = "📊 실시간 공고 (홈)"
            st.rerun()

    with col_srv:
        st.markdown('<div class="preview-wrap">', unsafe_allow_html=True)
        st.markdown('<div class="preview-title">💼 용역·서비스 최신 5건</div>', unsafe_allow_html=True)
        if not df_live_srv.empty:
            for _, prow in df_live_srv.head(5).iterrows():
                pname = str(prow.get('공고명', ''))[:28]
                porg  = str(prow.get('발주기관', ''))[:16]
                pamt_raw = prow.get('예산금액', 0)
                pamt_str = f"{raw_to_int(pamt_raw)//10000:,}만원" if raw_to_int(pamt_raw) > 0 else '-'
                st.markdown(
                    f'<div class="preview-row">'
                    f'<span class="pr-name">{pname}</span>'
                    f'<span class="pr-amt">{pamt_str}</span>'
                    f'<span class="pr-org">{porg}</span>'
                    f'</div>', unsafe_allow_html=True)
        else:
            st.markdown(
                '<p style="font-size:12px;color:#94a3b8;padding:8px 0;">'
                'Firebase service_live 노드에 아직 데이터가 없습니다.</p>',
                unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        if st.button("용역·서비스 전체 보기 →", use_container_width=True, key="btn_srv_all"):
            st.session_state['main_cat'] = "💼 용역·서비스"
            st.session_state['menu_s'] = "📊 실시간 공고 (홈)"
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(
        "<h3 style='color:#1e3a8a;font-size:1.2rem;font-weight:800;"
        "margin-bottom:14px;letter-spacing:-0.3px;'>"
        "🔑 K-건설맵 핵심 기능</h3>",
        unsafe_allow_html=True
    )

    f1, f2, f3 = st.columns(3)
    with f1:
        st.markdown("""
        <div class="info-card">
            <h3>📈 투찰률 히트맵 + 투찰가 계산기</h3>
            <p>지난 3년 실제 낙찰 사정률을 0.5% 단위로 분석해 낙찰 확률이 가장 높은 <b>골든 존</b>을 찾아드립니다.
            공고명을 입력하면 발주기관을 자동 탐지하고, 0.01% 단위·원단위로 추천 투찰가를 즉시 산출합니다.</p>
            <div class="badge-row">
                <span class="info-badge">0.01% 정밀도</span>
                <span class="info-badge">원단위 산출</span>
                <span class="info-badge">발주기관 자동 탐지</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with f2:
        st.markdown("""
        <div class="info-card" style="border-top-color:#7c3aed;">
            <h3 style="color:#7c3aed;">🏆 낙찰스코어 (신규)</h3>
            <p>내가 생각한 투찰률이 실제로 1순위가 될 확률을 <b>100점 만점</b>으로 즉시 채점합니다.
            핫존 일치도·경쟁강도·유사공고 적중·안정성·데이터충분성 5개 항목을 종합 분석하여
            S·A·B·C·D 등급과 맞춤 전략을 제공합니다.</p>
            <div class="badge-row">
                <span class="info-badge" style="background:#f5f3ff;color:#7c3aed;">100점 만점</span>
                <span class="info-badge" style="background:#f5f3ff;color:#7c3aed;">S~D 등급</span>
                <span class="info-badge" style="background:#f5f3ff;color:#7c3aed;">맞춤 전략 제공</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with f3:
        st.markdown("""
        <div class="info-card">
            <h3>🎯 면허 맞춤 공고 + 업체 자가진단</h3>
            <p>보유 면허를 등록하면 수만 건의 공고 중 우리 회사에 맞는 알짜 공고를 자동 선별합니다.
            업체 자가진단으로 3년간 낙찰 이력, 강세 지역, 주요 발주처,
            평균 투찰률까지 한 번에 확인하세요.</p>
            <div class="badge-row">
                <span class="info-badge">면허 자동 매칭</span>
                <span class="info-badge">지역별 강점</span>
                <span class="info-badge">3년 이력 분석</span>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ==========================================
# 10. 공통 현황판 렌더 함수 (공사/용역 공용)
# ==========================================
ROWS_PER_PAGE = 20


def render_1st_board(df_w, master_df, tab_prefix, p_key, prev_key, search_key, reg_key):
    st.markdown('<div class="guide-box">💡 <b>터치 한 번으로 팩트 분석!</b> 맨 왼쪽 <b>[체크박스(ㅁ)]</b>를 터치하면 3년 팩트 리포트가 즉시 열립니다.</div>', unsafe_allow_html=True)

    if df_w.empty:
        st.info("데이터를 불러오는 중입니다. 잠시 후 다시 시도해주세요.")
        return

    col_f1, col_f2 = st.columns([1, 2])
    with col_f1:
        sel_reg = st.selectbox("🌍 지역 필터링", REGION_LIST, key=reg_key)
    with col_f2:
        search_co = st.text_input("🏢 업체명 검색", placeholder="낙찰 업체명 입력", key=search_key)

    filter_key = f"{sel_reg}_{search_co}"
    if st.session_state.get(prev_key) != filter_key:
        st.session_state[p_key] = 1
        st.session_state[prev_key] = filter_key

    df_f = filter_by_region(df_w, sel_reg)
    if search_co and '1순위업체' in df_f.columns:
        df_f = df_f[df_f['1순위업체'].str.contains(search_co, na=False)]

    num_pages = max(1, math.ceil(len(df_f) / ROWS_PER_PAGE))
    if p_key not in st.session_state:
        st.session_state[p_key] = 1

    start_idx = (st.session_state[p_key] - 1) * ROWS_PER_PAGE
    df_page = df_f.iloc[start_idx: start_idx + ROWS_PER_PAGE]

    show_cols = [c for c in ['1순위업체', '날짜', '공고명', '발주기관', '투찰금액', '투찰률'] if c in df_page.columns]
    event = st.dataframe(
        df_page[show_cols],
        use_container_width=True, hide_index=True, height=700,
        selection_mode="single-row", on_select="rerun",
        key=f"grid_1st_{tab_prefix}"
    )

    c_p1, c_p2, c_p3 = st.columns([3, 4, 3])
    with c_p2:
        st.selectbox(f"📄 페이지 이동 (총 {num_pages}쪽)", range(1, num_pages + 1), key=p_key)

    if len(event.selection.rows) > 0:
        selected_row = df_page.iloc[event.selection.rows[0]]
        st.info(f"✅ 선택: **{str(selected_row.get('공고명',''))[:40]}**")
        if st.button("📋 팩트 리포트 보기", key=f"btn_1st_{tab_prefix}", use_container_width=True, type="primary"):
            det = fetch_detail(selected_row)
            show_analysis_dialog(selected_row, det, mode="1st", master_df=master_df, tab_prefix=tab_prefix)


def render_live_board(df_live, master_df, tab_prefix, prev_key, reg_key,
                      p_all_key, p_m_key, p_g_key):
    st.markdown('<div class="guide-box">💡 <b>입찰 팩트 리포트!</b> 맨 왼쪽 <b>[체크박스(ㅁ)]</b>를 터치하면 해당 발주기관의 3년 팩트 분석이 열립니다.</div>', unsafe_allow_html=True)

    if df_live.empty:
        st.info("데이터를 불러오는 중입니다. 잠시 후 다시 시도해주세요.")
        return

    sel_reg = st.selectbox("🌍 지역 필터링", REGION_LIST, key=reg_key)
    if st.session_state.get(prev_key) != sel_reg:
        st.session_state[p_all_key] = 1
        st.session_state[p_m_key] = 1
        st.session_state[p_g_key] = 1
        st.session_state[prev_key] = sel_reg

    df_f = filter_by_region(df_live, sel_reg)
    col_cfg = {
        "상세보기": st.column_config.LinkColumn("상세보기", display_text="공고보기"),
        "예산금액": st.column_config.NumberColumn("예산(원)", format="%,d")
    }
    show_cols = [c for c in ['공고번호', '공고일자', '공고명', '발주기관', '예산금액', '상세보기'] if c in df_f.columns]

    t1, t2 = st.tabs(["🌐 전체 공고", "✨ 내 면허 맞춤매칭"])

    with t1:
        n_all = max(1, math.ceil(len(df_f) / ROWS_PER_PAGE))
        if p_all_key not in st.session_state:
            st.session_state[p_all_key] = 1
        df_p_all = df_f.iloc[(st.session_state[p_all_key]-1)*ROWS_PER_PAGE: st.session_state[p_all_key]*ROWS_PER_PAGE]
        event_all = st.dataframe(
            df_p_all[show_cols], use_container_width=True, hide_index=True, height=700,
            column_config=col_cfg, selection_mode="single-row", on_select="rerun",
            key=f"live_all_{tab_prefix}"
        )
        c1, c2, c3 = st.columns([3, 4, 3])
        with c2:
            st.selectbox(f"📄 페이지 이동 (총 {n_all}쪽)", range(1, n_all+1), key=p_all_key)
        if len(event_all.selection.rows) > 0:
            selected_row_live = df_p_all.iloc[event_all.selection.rows[0]]
            st.info(f"✅ 선택: **{str(selected_row_live.get('공고명',''))[:40]}**")
            if st.button("📋 입찰 팩트 분석 보기", key=f"btn_live_all_{tab_prefix}", use_container_width=True, type="primary"):
                show_analysis_dialog(selected_row_live, None, mode="live", master_df=master_df, tab_prefix=tab_prefix)

    with t2:
        kw = get_match_keywords(st.session_state.get('user_license', ''))
        m_full = df_f[df_f['공고명'].str.contains('|'.join(kw), na=False)] if kw else df_f
        n_m = max(1, math.ceil(len(m_full) / ROWS_PER_PAGE))
        if p_m_key not in st.session_state:
            st.session_state[p_m_key] = 1
        df_p_m = m_full.iloc[(st.session_state[p_m_key]-1)*ROWS_PER_PAGE: st.session_state[p_m_key]*ROWS_PER_PAGE]
        m_show_cols = [c for c in show_cols if c in df_p_m.columns]
        event_m = st.dataframe(
            df_p_m[m_show_cols], use_container_width=True, hide_index=True, height=700,
            column_config=col_cfg, selection_mode="single-row", on_select="rerun",
            key=f"live_match_{tab_prefix}"
        )
        c1, c2, c3 = st.columns([3, 4, 3])
        with c2:
            st.selectbox(f"📄 페이지 이동 (총 {n_m}쪽)", range(1, n_m+1), key=p_m_key)
        if len(event_m.selection.rows) > 0:
            selected_row_live = df_p_m.iloc[event_m.selection.rows[0]]
            st.info(f"✅ 선택: **{str(selected_row_live.get('공고명',''))[:40]}**")
            if st.button("📋 입찰 팩트 분석 보기", key=f"btn_live_match_{tab_prefix}", use_container_width=True, type="primary"):
                show_analysis_dialog(selected_row_live, None, mode="live", master_df=master_df, tab_prefix=tab_prefix)


# ==========================================
# 11. UI 메인 — 비로그인 시 게이트 화면만 표시
# ==========================================
update_stats()
t_visit, u_total = get_stats()

# ──────────────────────────────────────────
# 🔒 비로그인 사용자 → 로그인 화면만 표시
# ──────────────────────────────────────────
if not st.session_state['logged_in']:
    # 사이드바 최소화 (브랜드명만 표시)
    with st.sidebar:
        st.markdown("""
            <div style="text-align:center; padding:15px 0; margin-bottom:16px;
                        background:linear-gradient(135deg,#1e3a8a,#1e40af);
                        border-radius:12px; box-shadow:0 4px 6px rgba(0,0,0,0.15);">
                <div style="color:#fde68a; font-weight:900; font-size:22px; letter-spacing:-0.5px;">🏛️ K-건설맵</div>
                <div style="color:rgba(255,255,255,0.7); font-size:11px; margin-top:4px;">Data Bidding Master</div>
            </div>
        """, unsafe_allow_html=True)
        st.info("🔒 로그인 후 모든 기능을 이용하실 수 있습니다.")

    # 메인 영역: 로그인/회원가입 전용 화면
    render_login_page()
    st.stop()  # 이후 코드(메뉴 라우팅) 실행 차단


# ──────────────────────────────────────────
# ✅ 로그인 후 사이드바 + 메뉴 라우팅
# ──────────────────────────────────────────
with st.sidebar:
    st.markdown("""
        <div style="text-align:center; padding:15px 0; margin-bottom:16px;
                    background:linear-gradient(135deg,#1e3a8a,#1e40af);
                    border-radius:12px; box-shadow:0 4px 6px rgba(0,0,0,0.15);">
            <div style="color:#fde68a; font-weight:900; font-size:22px; letter-spacing:-0.5px;">🏛️ K-건설맵</div>
            <div style="color:rgba(255,255,255,0.7); font-size:11px; margin-top:4px;">Data Bidding Master</div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown(f"**👋 {st.session_state['user_name']} 소장님, 안녕하세요!**")

    if is_admin():
        st.markdown(f"""
            <div style="background:#fef3c7; border:1px solid #f59e0b;
                        padding:10px; border-radius:8px; margin-bottom:12px; text-align:center;">
                <div style="font-size:11px; color:#92400e; font-weight:800;">👑 관리자 대시보드</div>
                <div style="font-size:15px; color:#b45309; font-weight:900; margin-top:3px;">가입자: {u_total}명</div>
            </div>
        """, unsafe_allow_html=True)

    cat_list = ["🏠 홈 대문", "🏗️ 건설·공사", "💼 용역·서비스", "🌍 커뮤니티·설정"]
    cur_idx = cat_list.index(st.session_state['main_cat']) if st.session_state['main_cat'] in cat_list else 0
    main_cat = st.selectbox("📂 조회 분야 선택", cat_list, index=cur_idx)
    st.session_state['main_cat'] = main_cat
    st.markdown("---")

    if main_cat == "🏠 홈 대문":
        menu = "홈"
    elif main_cat == "🏗️ 건설·공사":
        menu = st.radio("상세 메뉴", [
            "🏆 1순위 현황판", "📊 실시간 공고 (홈)",
            "🧮 투찰가 계산기",
            "🏆 낙찰스코어",
            "🔍 발주기관 분석", "🏢 업체 자가진단"
        ], key="menu_c")
    elif main_cat == "💼 용역·서비스":
        menu = st.radio("상세 메뉴", [
            "🏆 1순위 현황판", "📊 실시간 공고 (홈)",
            "🧮 투찰가 계산기",
            "🏆 낙찰스코어",
            "🔍 발주기관 분석", "🏢 업체 자가진단"
        ], key="menu_s")
    else:
        menu = st.radio("상세 메뉴", [
            "🤝 K-구인구직", "📁 K-건설 자료실",
            "💬 K건설챗", "📲 앱처럼 설치하기", "👤 내 정보/설정"
        ], key="menu_comm")

    st.write("---")
    if st.button("🚪 로그아웃"):
        st.session_state.clear()
        st.rerun()


# ==========================================
# 12. 메뉴 라우팅 (로그인 회원 전용)
# ==========================================

# ── 홈 대문 ──
if main_cat == "🏠 홈 대문":
    render_landing_page(t_visit)

# ──────────────────────────────────────
# [A] 건설·공사
# ──────────────────────────────────────
elif main_cat == "🏗️ 건설·공사":

    if menu == "🏆 1순위 현황판":
        st.markdown("#### 🏆 실시간 1순위 현황판 — 건설·공사")
        render_1st_board(
            df_w=get_hybrid_1st_bids(),
            master_df=big_data,
            tab_prefix="c",
            p_key="p1_c",
            prev_key="prev_filter_1st_c",
            search_key="search_main_c",
            reg_key="reg1_c"
        )

    elif menu == "📊 실시간 공고 (홈)":
        st.markdown("#### 📊 실시간 입찰 공고 — 건설·공사")
        render_live_board(
            df_live=get_hybrid_live_bids(),
            master_df=big_data,
            tab_prefix="c",
            prev_key="prev_filter_live_c",
            reg_key="reg2_c",
            p_all_key="p_all_c",
            p_m_key="p_m_c",
            p_g_key="p_g_c"
        )

    elif menu == "🧮 투찰가 계산기":
        render_bid_calculator(
            master_df=big_data,
            live_df_func=get_hybrid_live_bids,
            tab_prefix="c"
        )

    elif menu == "🏆 낙찰스코어":
        st.markdown("#### 🏆 낙찰스코어 — 건설·공사")
        render_bid_score(
            master_df=big_data,
            live_df_func=get_hybrid_live_bids,
            tab_prefix="c"
        )

    elif menu == "🔍 발주기관 분석":
        st.markdown("#### 🔍 발주기관 심층 분석 — 건설·공사")
        st.markdown('<div class="guide-box">발주기관명을 입력하면 3년 실제 데이터 기반으로 투찰률 히트맵, 독식업체, 발주패턴을 분석합니다. 추정 없음.</div>', unsafe_allow_html=True)
        if big_data is not None and not big_data.empty:
            inst_input = st.text_input("🏛️ 발주기관명 입력 (일부만 입력해도 됩니다)",
                                       placeholder="예: 여수시, 전남도청, 한국도로공사", key="inst_search_c")
            if inst_input:
                matching = big_data[big_data['발주기관'].str.contains(inst_input, na=False)]['발주기관'].value_counts()
                if matching.empty:
                    st.warning("검색된 발주기관이 없습니다.")
                else:
                    inst_select = st.selectbox(
                        f"검색 결과 {len(matching)}개 기관 — 선택하세요",
                        matching.index.tolist(),
                        format_func=lambda x: f"{x} ({matching[x]}건)",
                        key="inst_sel_c"
                    )
                    if inst_select:
                        st.markdown("---")
                        tab1, tab2, tab3 = st.tabs(["🎯 투찰률 히트맵", "🏆 독식업체 분석", "📅 발주패턴"])
                        with tab1: render_heatmap(inst_select, big_data)
                        with tab2: render_dominant(inst_select, big_data)
                        with tab3: render_pattern(inst_select, big_data)
        else:
            st.info("3년 마스터 데이터가 없습니다.")

    elif menu == "🏢 업체 자가진단":
        st.markdown("#### 🏢 업체 자가진단 리포트 — 건설·공사")
        st.markdown('<div class="guide-box">업체명을 입력하면 3년간 실제 낙찰 이력을 분석합니다. 지역별 강점, 낙찰 투찰률 분포, 주요 발주처를 확인하세요. 추정 없음.</div>', unsafe_allow_html=True)
        if big_data is not None and not big_data.empty:
            corp_input = st.text_input("🏢 업체명 입력 (일부만 입력해도 됩니다)",
                                       placeholder="예: 한국건설, 대우건설", key="corp_search_c")
            if corp_input:
                render_self_diagnosis(corp_input, big_data)
        else:
            st.info("3년 마스터 데이터가 없습니다.")

# ──────────────────────────────────────
# [B] 용역·서비스
# ──────────────────────────────────────
elif main_cat == "💼 용역·서비스":

    if service_big_data is None:
        st.warning("⚠️ 용역 3년 마스터 데이터(service_data_3years.zip)가 서버에 없습니다. 파일을 업로드해주세요.")

    if menu == "🏆 1순위 현황판":
        st.markdown("#### 🏆 실시간 1순위 현황판 — 용역·서비스")
        render_1st_board(
            df_w=get_hybrid_1st_bids_serv(),
            master_df=service_big_data,
            tab_prefix="s",
            p_key="p1_s",
            prev_key="prev_filter_1st_s",
            search_key="search_main_s",
            reg_key="reg1_s"
        )

    elif menu == "📊 실시간 공고 (홈)":
        st.markdown("#### 📊 실시간 입찰 공고 — 용역·서비스")
        render_live_board(
            df_live=get_hybrid_live_bids_serv(),
            master_df=service_big_data,
            tab_prefix="s",
            prev_key="prev_filter_live_s",
            reg_key="reg2_s",
            p_all_key="p_all_s",
            p_m_key="p_m_s",
            p_g_key="p_g_s"
        )

    elif menu == "🧮 투찰가 계산기":
        if service_big_data is not None:
            render_bid_calculator(
                master_df=service_big_data,
                live_df_func=get_hybrid_live_bids_serv,
                tab_prefix="s"
            )
        else:
            st.info("용역 마스터 데이터가 없습니다.")

    elif menu == "🏆 낙찰스코어":
        st.markdown("#### 🏆 낙찰스코어 — 용역·서비스")
        if service_big_data is not None:
            render_bid_score(
                master_df=service_big_data,
                live_df_func=get_hybrid_live_bids_serv,
                tab_prefix="s"
            )
        else:
            st.info("용역 마스터 데이터가 없습니다.")

    elif menu == "🔍 발주기관 분석":
        st.markdown("#### 🔍 발주기관 심층 분석 — 용역·서비스")
        st.markdown('<div class="guide-box">발주기관명을 입력하면 3년 실제 데이터 기반으로 투찰률 히트맵, 독식업체, 발주패턴을 분석합니다. 추정 없음.</div>', unsafe_allow_html=True)
        if service_big_data is not None and not service_big_data.empty:
            inst_input_s = st.text_input("🏛️ 발주기관명 입력 (일부만 입력해도 됩니다)",
                                         placeholder="예: 여수시, 전남도청, 한국환경공단", key="inst_search_s")
            if inst_input_s:
                matching_s = service_big_data[service_big_data['발주기관'].str.contains(inst_input_s, na=False)]['발주기관'].value_counts()
                if matching_s.empty:
                    st.warning("검색된 발주기관이 없습니다.")
                else:
                    inst_select_s = st.selectbox(
                        f"검색 결과 {len(matching_s)}개 기관 — 선택하세요",
                        matching_s.index.tolist(),
                        format_func=lambda x: f"{x} ({matching_s[x]}건)",
                        key="inst_sel_s"
                    )
                    if inst_select_s:
                        st.markdown("---")
                        tab1_s, tab2_s, tab3_s = st.tabs(["🎯 투찰률 히트맵", "🏆 독식업체 분석", "📅 발주패턴"])
                        with tab1_s: render_heatmap(inst_select_s, service_big_data)
                        with tab2_s: render_dominant(inst_select_s, service_big_data)
                        with tab3_s: render_pattern(inst_select_s, service_big_data)
        else:
            st.info("용역 3년 마스터 데이터가 없습니다.")

    elif menu == "🏢 업체 자가진단":
        st.markdown("#### 🏢 업체 자가진단 리포트 — 용역·서비스")
        st.markdown('<div class="guide-box">업체명을 입력하면 3년간 실제 낙찰 이력을 분석합니다. 지역별 강점, 낙찰 투찰률 분포, 주요 발주처를 확인하세요. 추정 없음.</div>', unsafe_allow_html=True)
        if service_big_data is not None and not service_big_data.empty:
            corp_input_s = st.text_input("🏢 업체명 입력 (일부만 입력해도 됩니다)",
                                         placeholder="예: 한국용역, 환경개발", key="corp_search_s")
            if corp_input_s:
                render_self_diagnosis(corp_input_s, service_big_data)
        else:
            st.info("용역 3년 마스터 데이터가 없습니다.")

# ──────────────────────────────────────
# [C] 커뮤니티·설정
# ──────────────────────────────────────
elif main_cat == "🌍 커뮤니티·설정":

    if menu == "🤝 K-구인구직":
        st.markdown("#### 🤝 건설현장 구인구직")
        with st.expander("📝 새 구인/구직 등록하기"):
            c1, c2 = st.columns(2)
            cat = c1.selectbox("분류", ["👷 사람 구합니다", "🚜 일자리 찾습니다"])
            reg = c2.selectbox("지역", REGION_LIST)
            jt = st.text_input("직종 (예: 철근공, 포크레인)")
            ph = st.text_input("연락처", value=st.session_state.get('user_phone', ''))
            ttl = st.text_input("제목")
            con = st.text_area("상세내용")
            if st.button("등록하기"):
                db.child("jobs").push({
                    "category": cat, "region": reg, "job_type": jt, "phone": ph,
                    "title": ttl, "content": con,
                    "author": st.session_state['user_name'],
                    "time": datetime.now(KST).strftime("%m-%d %H:%M")
                })
                st.toast("등록 완료!")
                time.sleep(1)
                st.rerun()
        jobs_data = db.child("jobs").order_by_key().limit_to_last(50).get().val()
        if jobs_data:
            df_j = pd.DataFrame(list(jobs_data.values())).iloc[::-1]
            t1, t2 = st.tabs(["👷 사람 구함", "🚜 일자리 찾음"])
            with t1:
                h = df_j[df_j['category'] == "👷 사람 구합니다"]
                ev_h = st.dataframe(h[['time', 'region', 'job_type', 'title', 'author']],
                                    use_container_width=True, hide_index=True,
                                    selection_mode="single-row", on_select="rerun", key="h_job")
                if len(ev_h.selection.rows) > 0:
                    sel_h = h.iloc[ev_h.selection.rows[0]]
                    st.info(f"✅ 선택: **{str(sel_h.get('title',''))[:40]}**")
                    if st.button("📋 상세 보기", key="btn_job_h", use_container_width=True, type="primary"):
                        show_analysis_dialog(sel_h, None, mode="job")
            with t2:
                s = df_j[df_j['category'] == "🚜 일자리 찾습니다"]
                ev_s = st.dataframe(s[['time', 'region', 'job_type', 'title', 'author']],
                                    use_container_width=True, hide_index=True,
                                    selection_mode="single-row", on_select="rerun", key="s_job")
                if len(ev_s.selection.rows) > 0:
                    sel_s = s.iloc[ev_s.selection.rows[0]]
                    st.info(f"✅ 선택: **{str(sel_s.get('title',''))[:40]}**")
                    if st.button("📋 상세 보기", key="btn_job_s", use_container_width=True, type="primary"):
                        show_analysis_dialog(sel_s, None, mode="job")

    elif menu == "📲 앱처럼 설치하기":
        st.markdown("### 📲 스마트폰 바탕화면에 앱으로 추가하기")
        col1, col2 = st.columns(2)
        with col1:
            st.info("🍎 **아이폰 (Safari)**\n\n1. 하단 **[공유 버튼(□↑)]** 클릭\n2. **[홈 화면에 추가]** 클릭\n3. **[추가]** 클릭")
        with col2:
            st.success("🤖 **안드로이드 (Chrome)**\n\n1. 상단 **[점 3개(⋮)]** 클릭\n2. **[홈 화면에 추가]** 또는 **[앱 설치]** 클릭\n3. **[추가]** 클릭")

    elif menu == "👤 내 정보/설정":
        st.subheader("👤 회원 정보 관리")
        st.write(f"### {st.session_state['user_name']} 소장님 반갑습니다!")
        my_tab1, my_tab2 = st.tabs(["✏️ 정보 수정", "🗑️ 회원 탈퇴"])

        with my_tab1:
            st.markdown("**회원 정보를 수정합니다.**")
            cur_info = db.child("users").child(st.session_state['localId']).get().val() or {}
            new_name = st.text_input("성함 수정", value=cur_info.get('name', ''))
            new_phone = st.text_input("연락처 수정", value=cur_info.get('phone', ''))
            new_lic = st.multiselect("보유 면허 수정", ALL_LICENSES,
                                     default=[l.strip() for l in cur_info.get('license', '').split(',') if l.strip() in ALL_LICENSES])
            if st.button("✅ 정보 저장"):
                try:
                    db.child("users").child(st.session_state['localId']).update({
                        "name": new_name,
                        "phone": new_phone,
                        "license": ", ".join(new_lic)
                    })
                    st.session_state['user_name'] = new_name
                    st.session_state['user_phone'] = new_phone
                    st.session_state['user_license'] = ", ".join(new_lic)
                    st.success("✅ 정보가 저장되었습니다!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"저장 실패: {e}")

        with my_tab2:
            st.warning("⚠️ 탈퇴하면 모든 정보가 삭제되며 복구할 수 없습니다.")
            confirm_pw = st.text_input("탈퇴 확인용 비밀번호 입력", type="password", key="del_pw")
            if st.button("🗑️ 회원 탈퇴 확인", type="primary"):
                if not confirm_pw:
                    st.error("비밀번호를 입력해주세요.")
                else:
                    try:
                        cur_info2 = db.child("users").child(st.session_state['localId']).get().val() or {}
                        auth.sign_in_with_email_and_password(cur_info2.get('email', ''), confirm_pw)
                        db.child("users").child(st.session_state['localId']).remove()
                        try:
                            curr_u = db.child("stats").child("total_users").get().val() or 0
                            db.child("stats").update({"total_users": max(0, int(curr_u) - 1)})
                        except Exception:
                            pass
                        st.session_state.clear()
                        st.success("탈퇴 완료. 이용해 주셔서 감사합니다.")
                        time.sleep(2)
                        st.rerun()
                    except Exception:
                        st.error("비밀번호가 틀렸거나 탈퇴에 실패했습니다.")

    elif menu == "📁 K-건설 자료실":
        st.subheader("📁 K-건설 자료실")
        with st.expander("✏️ 새 자료 등록"):
            t_title = st.text_input("제목", key="post_title")
            t_content = st.text_area("내용", key="post_content")
            if st.button("등록") and t_title and t_content:
                db.child("posts").push({
                    "author": st.session_state['user_name'],
                    "title": t_title, "content": t_content,
                    "time": datetime.now(KST).strftime("%Y-%m-%d %H:%M")
                })
                st.rerun()

        posts = db.child("posts").order_by_key().limit_to_last(30).get().val()
        if posts:
            for k, v in reversed(list(posts.items())):
                with st.expander(f"📢 {v['title']} (작성자: {v['author']})"):
                    st.write(v['content'])
                    st.caption(f"작성: {v.get('time', '')}")
                    if v['author'] == st.session_state['user_name']:
                        col_e, col_d = st.columns([1, 1])
                        with col_e:
                            if st.button("✏️ 수정", key=f"edit_{k}"):
                                st.session_state[f'editing_{k}'] = True
                        with col_d:
                            if st.button("🗑️ 삭제", key=f"del_{k}"):
                                db.child("posts").child(k).remove()
                                st.toast("삭제되었습니다.")
                                time.sleep(0.5)
                                st.rerun()
                        if st.session_state.get(f'editing_{k}'):
                            new_t = st.text_input("제목 수정", value=v['title'], key=f"et_{k}")
                            new_c = st.text_area("내용 수정", value=v['content'], key=f"ec_{k}")
                            if st.button("💾 저장", key=f"save_{k}"):
                                db.child("posts").child(k).update({"title": new_t, "content": new_c})
                                st.session_state.pop(f'editing_{k}', None)
                                st.toast("수정되었습니다.")
                                time.sleep(0.5)
                                st.rerun()

    elif menu == "💬 K건설챗":
        st.subheader("💬 실시간 현장 소통")
        chat_box = st.container(height=400)
        chats_data = db.child("k_chat").order_by_key().limit_to_last(20).get().val()
        if chats_data:
            for v in chats_data.values():
                chat_box.write(f"**{v['author']}**: {v['message']}")
        if msg := st.chat_input("메시지 입력"):
            db.child("k_chat").push({
                "author": st.session_state['user_name'],
                "message": msg,
                "time": datetime.now(KST).strftime("%H:%M")
            })
            st.rerun()



