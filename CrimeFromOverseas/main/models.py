from django.db import models


class TravelStat(models.Model):
    """
    월별 해외 출국자 수 (국가별)
    - year, month : 기준 연월
    - country     : 국가 코드(NAT_CD, 예: '112')
    - country_name: 국가명(한국어, 예: '일본') - 선택
    - ed_cd       : 출입국 구분 ('D' = 국민 해외관광객, 'E' = 방한외래관광객)
    - departures  : 출국자 수 (num)
    - ratio       : 전년 동월 대비 증감률(%) (옵션)
    """

    year = models.IntegerField()
    month = models.IntegerField()

    # 기존 country 필드를 그대로 쓰되, 의미를 명확히: 국가 코드(NAT_CD)
    country = models.CharField(max_length=10)  # '112', '100' 등 국가 코드

    country_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="국가명 (예: 일본, 미국 등)"
    )

    ed_cd = models.CharField(
        max_length=1,
        default="D",  # 기본: 국민 해외관광객(출국)
        help_text="D=국민 해외관광객(출국), E=방한 외래관광객(입국)"
    )

    departures = models.IntegerField(help_text="출국자 수 (num 필드)")

    ratio = models.FloatField(
        blank=True,
        null=True,
        help_text="전년 동월 대비 증감률(%) (없으면 NULL)"
    )

    class Meta:
        unique_together = ("year", "month", "country", "ed_cd")

    def __str__(self):
        name = self.country_name or self.country
        return f"{self.year}-{self.month:02d} [{self.ed_cd}] {name}: {self.departures}명"


class VoicePhishingStat(models.Model):
    """월별 보이스피싱 발생 건수"""
    year = models.IntegerField()
    month = models.IntegerField()
    cases = models.IntegerField()  # 발생 건수

    class Meta:
        unique_together = ("year", "month")

    def __str__(self):
        return f"{self.year}-{self.month:02d}: {self.cases}건"


class CyberScamStat(models.Model):
    """
    연도별 사이버 사기 범죄 (유형별 분리 저장)
    API 필드 구성:
      - 연도
      - 구분 (발생건수 / 검거건수)
      - 직거래
      - 쇼핑몰
      - 게임
      - 이메일 무역
      - 연예빙자
      - 사이버투자
      - 사이버사기_기타
    """
    year = models.IntegerField()
    category = models.CharField(max_length=50)  # 발생건수 / 검거건수 등

    direct_trade = models.IntegerField()        # 직거래
    shopping_mall = models.IntegerField()       # 쇼핑몰
    game = models.IntegerField()                # 게임
    email_trade = models.IntegerField()         # 이메일 무역
    romance = models.IntegerField()             # 연예빙자
    investment = models.IntegerField()          # 사이버투자
    etc = models.IntegerField()                 # 사이버사기_기타

    class Meta:
        unique_together = ("year", "category")

    @property
    def total_cases(self):
        return (
            self.direct_trade +
            self.shopping_mall +
            self.game +
            self.email_trade +
            self.romance +
            self.investment +
            self.etc
        )

    def __str__(self):
        return f"{self.year} {self.category}: 총 {self.total_cases}건"
