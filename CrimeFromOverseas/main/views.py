from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings 
from .utils_csv_import import load_all_departure_data
from .models import TravelStat
from django.db.models import Count

def test_departure_csv(request):
    df, year_totals, crime_totals, total_all_years = load_all_departure_data()


    return JsonResponse({
        "rows": len(df),
        "columns": list(df.columns),
        "sample": df.head(20).to_dict(orient="records")
    }, safe=False)


from .api_client import (
    sync_cyber_scam,
    sync_voice_phishing,
    sync_travel_stats_from_csv,
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
    })

from .utils_csv_import import load_all_departure_data, save_to_db

def sync_travel_view(request):
    df, year_totals, crime_totals, total_all_years = load_all_departure_data()
    saved = save_to_db(df)

    return JsonResponse({
        "status": "ok",
        "saved_rows": saved,
        "total_rows": len(df),
        "year_totals": year_totals.to_dict(),          # 연도별 출국자 합계
        "crime_totals": crime_totals.to_dict(),        # 범죄국 연도별 합계
        "total_all_years": int(total_all_years),       # 전체 합계
    })


# 사이버사기 API 동기화
def sync_cyber_view(request):
    sync_cyber_scam()
    return JsonResponse({"status": "cyber_scam_sync_ok"})


# 보이스피싱 API 동기화
def sync_voice_view(request):
    sync_voice_phishing()
    return JsonResponse({"status": "voice_phishing_sync_ok"})

# 사이버사기 원본 데이터 테스트 조회
def test_cyber(request):
    data = fetch_cyber_scam()
    return JsonResponse(data, safe=False)


def travel_debug_view(request):
    stats_limit = 100

    total = TravelStat.objects.count()

    if total == 0:
        return render(request, "main/travel_debug.html", {
            "total_count": 0,
            "regions": [],
            "stats": [],
            "stats_limit": stats_limit,
            "empty": True,
        })

    stats = (
        TravelStat.objects
        .order_by("-year", "-month", "region", "country")[:stats_limit]
    )

    regions = (
        TravelStat.objects
        .values("region")
        .annotate(count=Count("id"))
        .order_by("region")
    )

    context = {
        "total_count": TravelStat.objects.count(),
        "regions": regions,
        "stats": stats,
        "stats_limit": stats_limit,
    }
    return render(request, "main/travel_debug.html", context)
