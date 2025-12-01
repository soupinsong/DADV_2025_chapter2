import requests
import json
from django.conf import settings

from .models import (
    CyberScamStat,
    VoicePhishingStat,
    TravelStat,
)


# =========================
# 1. 사이버 사기 (JSON 깨끗함)
# =========================
def fetch_cyber_scam(page=1, per_page=100):
    """경찰청 사이버사기 범죄 API에서 원본 JSON 가져오기"""

    url = f"{settings.SCAM_BASE_URL}{settings.SCAM_ENDPOINT}"

    params = {
        "page": page,
        "perPage": per_page,
        "serviceKey": settings.API_KEY,  # 공통 키
        "returnType": "JSON",
    }

    res = requests.get(url, params=params)
    res.raise_for_status()

    data = res.json()
    return data.get("data", [])


def sync_cyber_scam():
    """사이버 사기 데이터를 DB에 저장"""
    rows = fetch_cyber_scam(page=1, per_page=100)

    for row in rows:
        try:
            year = int(row.get("연도"))
            category = row.get("구분", "")
        except (TypeError, ValueError):
            # 연도 이상하면 스킵
            continue

        CyberScamStat.objects.update_or_create(
            year=year,
            category=category,
            defaults={
                "direct_trade": int(row.get("직거래") or 0),
                "shopping_mall": int(row.get("쇼핑몰") or 0),
                "game": int(row.get("게임") or 0),
                "email_trade": int(row.get("이메일 무역") or 0),
                "romance": int(row.get("연예빙자") or 0),
                "investment": int(row.get("사이버투자") or 0),
                "etc": int(row.get("사이버사기_기타") or 0),
            },
        )


# =========================
# 2. 보이스피싱 월별 (문자열 JSON 방어 포함)
# =========================
def fetch_voice_phishing(page=1, per_page=200):
    """보이스피싱 월별 현황 API에서 데이터 가져오기"""

    url = f"{settings.VOICE_BASE_URL}{settings.VOICE_ENDPOINT}"

    params = {
        "page": page,
        "perPage": per_page,
        "serviceKey": settings.API_KEY,
        "returnType": "JSON",
    }

    res = requests.get(url, params=params)
    res.raise_for_status()

    # 1차 파싱: 최상위 JSON
    try:
        raw = res.json()
    except ValueError:
        raw = json.loads(res.text)

    # 경우에 따라 {"data": [...]} 이거나 그냥 [...] 일 수 있음
    rows = raw.get("data", raw)

    clean_rows = []

    for r in rows:
        obj = None

        # 문자열로 한 번 더 감싸져 있는 경우
        if isinstance(r, str):
            try:
                obj = json.loads(r)
            except ValueError:
                continue
        elif isinstance(r, dict):
            obj = r
        else:
            # dict도 문자열도 아니면 버림
            continue

        clean_rows.append(obj)

    return clean_rows


def sync_voice_phishing():
    """보이스피싱 월별 데이터를 DB에 저장"""

    rows = fetch_voice_phishing(page=1, per_page=500)

    for row in rows:
        # 안전하게 get + 검증
        year_raw = row.get("년")
        month_raw = row.get("월")
        cases_raw = row.get("전화금융사기 발생건수")

        # 하나라도 None / 빈 문자열이면 스킵
        if not year_raw or not month_raw or cases_raw is None or cases_raw == "":
            continue

        try:
            year = int(year_raw)
            month = int(month_raw)
            cases = int(cases_raw)
        except (TypeError, ValueError):
            # 숫자로 안 바뀌면 그냥 버리기
            continue

        VoicePhishingStat.objects.update_or_create(
            year=year,
            month=month,
            defaults={"cases": cases},
        )


# =========================
# 3. 출입국 관광 통계
# =========================
def fetch_travel_stats(year_month, nat_cd, ed_cd="E"):
    """
    관광 출입국 통계 기능(1번 API)
    YM: 201201 형태
    NAT_CD: 112 (국가코드)
    ED_CD: E(출국), D(입국)
    """

    url = f"{settings.TRAVEL_BASE_URL}{settings.TRAVEL_ENDPOINT}"

    params = {
        "serviceKey": settings.API_KEY,
        "YM": year_month,
        "NAT_CD": nat_cd,
        "ED_CD": ed_cd,
    }

    res = requests.get(url, params=params)
    res.raise_for_status()

    # 이 API는 XML 기반인데, 포털 세팅에 따라 JSON이 올 수도 있음.
    # 우선 json() 시도, 안 되면 text 그대로 반환해서 나중에 따로 처리해도 됨.
    try:
        return res.json()
    except ValueError:
        # XML 그대로 돌려주기 (지금은 안 쓰면 됨)
        return {"raw_xml": res.text}


def sync_travel_stats(year, month, nat_cd="112", ed_cd="E"):
    """출국자 통계를 DB에 저장"""

    ym = f"{year}{month:02d}"
    data = fetch_travel_stats(ym, nat_cd, ed_cd)

    # JSON인 경우만 처리 (XML이면 나중에 xmltodict 같은 걸로 파싱)
    try:
        item = data["response"]["body"]["items"]["item"]
    except (KeyError, TypeError):
        return  # 데이터 없음 or 아직 XML 처리 안 함

    departures_raw = item.get("num")

    try:
        departures = int(departures_raw)
    except (TypeError, ValueError):
        departures = 0

    TravelStat.objects.update_or_create(
        year=year,
        month=month,
        country=nat_cd,
        defaults={"departures": departures},
    )
