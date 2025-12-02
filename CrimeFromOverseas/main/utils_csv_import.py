import pandas as pd
from django.conf import settings
from .models import TravelStat

def clean_number(x):
    """문자열 숫자 처리 ('1,234' → 1234), 결측치는 0."""
    if pd.isna(x):
        return 0
    if isinstance(x, str):
        x = x.replace(",", "").strip()
        if x == "" or x == "-":
            return 0
    try:
        return int(float(x))
    except:
        return 0


def load_csv(path, region_name):
    """CSV 파일을 로드하고 통일된 스키마로 전처리."""
    df = pd.read_csv(path)

    # 컬럼명 표준화
    df.columns = [c.strip().lower() for c in df.columns]

    # 필수 컬럼 체크
    required = ["year", "month"]
    if not all(col in df.columns for col in required):
        raise ValueError(f"{path} 파일에 year, month 컬럼이 없습니다.")

    # country 이름 있는 컬럼 찾기
    country_cols = [c for c in df.columns if c not in ["year", "month"]]

    rows = []

    for country in country_cols:
        sub = df[["year", "month", country]].copy()
        sub["country"] = country
        sub["departures"] = sub[country].apply(clean_number)
        sub["region"] = region_name
        sub["ed_cd"] = "D"  # 항상 출국자 수
        sub = sub[["year", "month", "country", "region", "ed_cd", "departures"]]
        rows.append(sub)

    df_final = pd.concat(rows, ignore_index=True)

    # 결측치 처리
    df_final.fillna(0, inplace=True)

    # 국가명 소문자 통일
    df_final["country"] = df_final["country"].str.strip().str.lower()

    # 중복 제거
    df_final.drop_duplicates(subset=["year", "month", "country", "region"], inplace=True)

    return df_final


def save_to_db(df):
    """전처리된 DF를 TravelStat DB에 저장."""
    count = 0
    for _, row in df.iterrows():
        TravelStat.objects.update_or_create(
            year=int(row["year"]),
            month=int(row["month"]),
            country=row["country"],
            region=row["region"],
            ed_cd=row["ed_cd"],
            defaults={"departures": int(row["departures"])}
        )
        count += 1
    return count


def import_all_regions():
    """ENV에 등록된 모든 CSV 파일을 자동으로 불러와 DB에 저장."""
    files = {
        "asia": settings.ASIA_CSV,
        "europe": settings.EUROPE_CSV,
        "africa": settings.AFRICA_CSV,
        "america": settings.AMERICA_CSV,
        "oceania": settings.OCEANIA_CSV,
    }

    total_saved = 0

    for region, path in files.items():
        if path is None:
            continue
        print(f"=== {region.upper()} CSV IMPORT START ===")
        df = load_csv(path, region)
        saved = save_to_db(df)
        total_saved += saved
        print(f"{region} 저장 완료: {saved} rows")

    print(f"\n총 저장된 데이터: {total_saved} rows")
    return total_saved
