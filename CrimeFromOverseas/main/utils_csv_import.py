import pandas as pd
from django.conf import settings
from .models import TravelStat

# -----------------------------
# ✔ 숫자 변환 함수
# -----------------------------
def clean_num(x):
    if pd.isna(x):
        return 0
    x = str(x).replace(",", "").replace("-", "0").strip()
    try:
        return int(float(x))
    except:
        return 0


# -----------------------------
# ✔ CSV 월별 파싱 → 연도/국가별 집계
# -----------------------------
def load_and_aggregate_csv(path, region_name):

    df = pd.read_csv(path, header=None, encoding="utf-8-sig")

    # 1행: 국가명, 2행: 명수/전년대비
    header_country = df.iloc[1]
    header_type = df.iloc[2]
    n_cols = df.shape[1]

    # (col_index, country_name)
    country_cols = []
    for col in range(3, n_cols):
        if str(header_type[col]).strip() != "명수":
            continue
        country_name = str(header_country[col]).strip()
        if country_name.lower() == "nan" or country_name == "":
            continue
        country_cols.append((col, country_name))

    print(f"[{region_name}] 감지된 국가 수:", len(country_cols))

    output_rows = []
    current_year = None

    # -----------------------------
    # ✔ 월별 데이터 파싱
    # -----------------------------
    for idx, row in df.iloc[3:].iterrows():

        year_cell = str(row.iloc[0]).strip()
        month_cell = str(row.iloc[1]).strip()

        # 연도 감지
        if year_cell.endswith("년"):
            digits = "".join([c for c in year_cell if c.isdigit()])
            if digits:
                current_year = int(digits)
            continue

        if current_year is None:
            continue

        # 월 감지
        if not month_cell.endswith("월"):
            continue

        # 국가별 숫자 저장
        for col, country_name in country_cols:
            departures = clean_num(row.iloc[col])
            output_rows.append({
                "year": current_year,
                "country": country_name,
                "region": region_name,
                "departures": departures,
            })

    monthly_df = pd.DataFrame(output_rows)

    # -----------------------------
    # ✔ 월별 → 연도별 합계 변환
    # -----------------------------
    yearly_df = (
        monthly_df.groupby(["year", "country"])
        .sum()
        .reset_index()
    )

    return yearly_df


# -----------------------------
# ✔ 주요 범죄국 리스트
# -----------------------------
CRIME_COUNTRIES = [
    "중국", "미국", "영국", "인도", "독일",
    "캄보디아", "이스라엘", "몰디브", "미얀마", "필리핀"
]


# -----------------------------
# ✔ CSV 전체 로드 & 연도별/범죄국 집계
# -----------------------------
def load_all_departure_data():

    files = {
        "asia": settings.ASIA_CSV,
        "europe": settings.EUROPE_CSV,
        "africa": settings.AFRICA_CSV,
        "america": settings.AMERICA_CSV,
        "oceania": settings.OCEANIA_CSV,
    }

    dfs = []

    for region, path in files.items():
        print(f"\n=== {region.upper()} CSV 로드 시작 ===")
        df_yearly = load_and_aggregate_csv(path, region)
        dfs.append(df_yearly)

    final_df = pd.concat(dfs, ignore_index=True)

    # -----------------------------
    # ✔ 연도별 총합 계산
    # -----------------------------
    total_by_year = (
        final_df.groupby("year")["departures"]
        .sum()
        .reset_index()
        .rename(columns={"departures": "year_total"})
    )

    # -----------------------------
    # ✔ 주요 범죄국 연도별 합계
    # -----------------------------
    crime_df = (
        final_df[final_df["country"].isin(CRIME_COUNTRIES)]
        .groupby("year")["departures"]
        .sum()
        .reset_index()
        .rename(columns={"departures": "crime_country_total"})
    )

    print("\n📌 주요 범죄국 연도별 출국자 합계")
    print(crime_df)

    print("\n📌 전체 국가 연도별 출국자 합계")
    print(total_by_year)

    # === 전체 연도(2018~2024) 출국자 총합 ===
    total_all_years = total_by_year["year_total"].sum()

    print("\n📌 2018~2024 전체 출국자 총합 (누적)")
    print(f"{total_all_years:,}")

    return final_df, total_by_year, crime_df, total_all_years


# -----------------------------
# ✔ DB 저장 (연도별 데이터만 저장)
# -----------------------------
def save_yearly_to_db(df):
    count = 0
    for _, row in df.iterrows():
        TravelStat.objects.update_or_create(
            year=row["year"],
            month=0,
            country=row["country"],
            ed_cd="D",
            defaults={"country_name": row["country"], "departures": row["departures"]}
        )
        count += 1

    print(f"\n✔ 연도별 데이터 {count}건 저장 완료!")
    return count
