from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings

from .api_client import (
    sync_cyber_scam,
    sync_voice_phishing,
    sync_travel_stats,
    fetch_cyber_scam,
)


def test_voice(request):
    from .api_client import fetch_voice_phishing
    return JsonResponse(fetch_voice_phishing(), safe=False)


# 메인 페이지
def index(request):
    return render(request, 'main/index.html')


# API Key 테스트 (현재 구조에 맞춤)
def test_keys(request):
    return JsonResponse({
        "API_KEY": settings.API_KEY is not None,
        "SCAM_BASE_URL": settings.SCAM_BASE_URL,
        "VOICE_BASE_URL": settings.VOICE_BASE_URL,
        "TRAVEL_BASE_URL": settings.TRAVEL_BASE_URL,
    })


# 사이버사기 API 동기화
def sync_cyber_view(request):
    sync_cyber_scam()
    return JsonResponse({"status": "cyber_scam_sync_ok"})


# 보이스피싱 API 동기화
def sync_voice_view(request):
    sync_voice_phishing()
    return JsonResponse({"status": "voice_phishing_sync_ok"})


# 출입국 통계 API 동기화 (특정 연/월)
def sync_travel_view(request):
    year = int(request.GET.get("year", 2024))
    month = int(request.GET.get("month", 1))
    sync_travel_stats(year, month)
    return JsonResponse({"status": f"travel_stats_sync_ok for {year}-{month}"})


# 사이버사기 원본 데이터 테스트 조회
def test_cyber(request):
    data = fetch_cyber_scam()
    return JsonResponse(data, safe=False)
