import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta, timezone
import urllib.parse
import urllib3
import streamlit as st
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
KST = timezone(timedelta(hours=9))


@st.cache_data(ttl=600)
def fetch_monster_announcements():
    all_bids = []

    # 📅 크롤링은 하나씩 읽어야 해서 속도가 느려. 일단 안전하게 최근 7일치만!
    end_date = datetime.now(KST).strftime('%Y/%m/%d')
    start_date = (datetime.now(KST) - timedelta(days=7)).strftime('%Y/%m/%d')

    # 🚩 나라장터 앞문(메인 홈페이지) 검색 주소
    base_url = "https://www.g2b.go.kr:8101/ep/tbid/tbidList.do"

    # 블로그에서 쓴 파라미터 그대로 적용 (공사 검색)
    params = {
        "taskClCds": "3",  # 3 = 공사
        "bidNm": "",  # 전체 공사
        "searchDtType": "1",
        "fromBidDt": start_date,
        "toBidDt": end_date,
        "fromOpenBidDt": "",
        "toOpenBidDt": "",
        "radOrgan": "1",
        "instNm": "",
        "area": "",
        "regYn": "Y",
        "bidSearchType": "1",
        "searchType": "1"
    }

    encoded_params = urllib.parse.urlencode(params, encoding='euc-kr')
    url = f"{base_url}?{encoded_params}"

    try:
        # 나라장터 메인 홈페이지에 접속!
        response = requests.get(url, verify=False, timeout=30)
        soup = BeautifulSoup(response.content, 'html.parser')

        # 테이블에서 데이터 뽑아내기
        rows = soup.select('table.table_list tr')[1:]  # 첫 번째 행(헤더) 제외

        for row in rows:
            cols = row.select('td')
            if len(cols) >= 5:
                # K-건설맵 UI에 맞게 이름 맞추기
                공고번호 = cols[1].text.strip()
                공고명 = cols[2].text.strip()
                수요기관 = cols[3].text.strip()
                마감일시 = cols[4].text.strip()

                # 링크 주소 만들기
                상세링크 = f"https://www.g2b.go.kr:8081/ep/invitation/publish/bidInfoDtl.do?bidno={공고번호[:11]}&bidseq={공고번호[12:]}"

                all_bids.append({
                    'bidNtceNo': 공고번호,
                    'bidNtceNm': 공고명,
                    'ntceInsttNm': 수요기관,
                    'bidNtceDt': 마감일시,
                    'bdgtAmt': "0",  # 리스트 화면엔 예산이 없어서 0으로 처리 (크롤링 한계)
                    'bidNtceDtlUrl': 상세링크
                })

    except Exception as e:
        st.session_state['debug_text'] = f"크롤링 에러 발생: {str(e)}"
        pass

    return pd.DataFrame(all_bids)