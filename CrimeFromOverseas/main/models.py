from django.db import models

class TravelStat(models.Model):
    """월별 해외 출국자 수 (국가별 or 전체)"""
    year = models.IntegerField()
    month = models.IntegerField()
    country = models.CharField(max_length=255, default="TOTAL")  # 국가 코드 또는 전체

    departures = models.IntegerField()  # 출국자 수

    class Meta:
        unique_together = ("year", "month", "country")

    def __str__(self):
        return f"{self.year}-{self.month:02d} {self.country}: {self.departures}명"

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
