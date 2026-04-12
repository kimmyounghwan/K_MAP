import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
import urllib3
import streamlit as st

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
# 🔑 사장님의 무적 API 키
API_KEY = "13610863df3680cc4e7c70a64d752b37485535929bfa514f4ad4d71ea56e4ccb"
KST = timezone(timedelta(hours=9))


def fetch_blog_logic():
    # 🚩 사장님이 찾아준 블로그의 그 '무적 주소' (공사 입찰공고 검색 전용)
    url = 'http://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoCnstwkPPSSrch'

    # 1. 날짜 범위 설정 (오늘부터 30일 전까지로 넓게 잡아서 데이터가 나오게 함)
    end_dt = datetime.now(KST).strftime('%Y%m%d2359')
    start_dt = (datetime.now(KST) - timedelta(days=30)).strftime('%Y%m%d0000')

    # 2. 파라미터 (블로그 로직 그대로, 검색어는 가장 흔한 '공사'로 고정해서 뚫어보기)
    params = {
        'inqryDiv': '1',
        'inqryBgnDt': start_dt,
        'inqryEndDt': end_dt,
        'pageNo': '1',
        'numOfRows': '500',
        'bidNtceNm': '공사',  # 일단 뭐라도 가져오기 위해 '공사'로 고정
        'type': 'json',
        'serviceKey': API_KEY
    }

    try:
        res = requests.get(url, params=params, verify=False, timeout=15)
        # 🚨 조달청이 보낸 답변 원문을 사장님이 직접 볼 수 있게 저장
        st.session_state['debug_text'] = res.text

        if res.status_code == 200:
            data = res.json()
            items = data.get('response', {}).get('body', {}).get('items', [])
            return items if items else []
    except Exception as e:
        st.session_state['debug_text'] = f"통신 에러: {str(e)}"
    return []

