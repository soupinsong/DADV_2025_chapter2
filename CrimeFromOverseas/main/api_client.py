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
# 3. 출입국 관광 통계 (국민 해외관광객 위주)
# =========================
import xmltodict  # 맨 위 import에 추가 필요

def fetch_travel_stats(year_month, nat_cd, ed_cd="D"):
    """
    관광 출입국 통계 (EdrcntTourismStatsService)

    YM     : '201201' 형태의 문자열 (YYYYMM)
    NAT_CD : 국가 코드 (예: '112')
    ED_CD  : 'D' = 국민 해외관광객(출국), 'E' = 방한외래관광객(입국)

    이 함수는 XML 응답을 dict 형태로 파싱해서 반환한다.
    """

    # settings.py 에서 이렇게 읽고 있다고 가정:
    # TRAVEL_BASE_URL=https://openapi.tour.go.kr/openapi/service
    # TRAVEL_SERVICE=EdrcntTourismStatsService
    # TRAVEL_ENDPOINT=getEdrcntTourismStatsList
    url = f"{settings.TRAVEL_BASE_URL}/{settings.TRAVEL_SERVICE}/{settings.TRAVEL_ENDPOINT}"

    params = {
        "serviceKey": settings.API_KEY,
        "YM": year_month,
        "NAT_CD": nat_cd,
        "ED_CD": ed_cd,
    }

    res = requests.get(url, params=params)
    res.raise_for_status()

    # 출입국 통계는 공식적으로 XML만 제공 → xmltodict로 파싱
    data = xmltodict.parse(res.text)
    return data


def sync_travel_stats(year, month, nat_cd="112", ed_cd="D"):
    """
    출국자(국민 해외관광객) 통계를 DB에 저장

    year  : 2020
    month : 1 ~ 12
    nat_cd: 국가 코드 (112 등)
    ed_cd : 기본 'D' (국민 해외관광객)
    """

    ym = f"{year}{month:02d}"
    data = fetch_travel_stats(ym, nat_cd, ed_cd)

    # XML → dict 구조 예시:
    # data["response"]["body"]["items"]["item"]
    try:
        item = (
            data
            .get("response", {})
            .get("body", {})
            .get("items", {})
            .get("item")
        )
    except AttributeError:
        # 구조가 이상하면 그냥 종료
        return

    if item is None:
        # 조회 결과가 없으면 종료
        return

    # item 이 리스트일 수도, dict일 수도 있어서 방어
    if isinstance(item, list):
        # NAT_CD 한 개만 조회했는데 리스트면, 우선 첫 번째만 사용
        item = item[0]

    # 필드 이름은 실제 응답 확인해서 한 번 맞춰봐야 함
    # 보통 num / natCd / ym / edCd 이런 식으로 옴
    departures_raw = item.get("num") or item.get("NUM")  # 혹시 대소문자 다를 경우 대비

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
