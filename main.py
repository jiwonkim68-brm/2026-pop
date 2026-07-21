import re
import requests
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="전국 고령화 단계구분도", layout="wide")
st.title("전국 고령화 단계구분도 (2026년, 시군구별 65세 이상 비율)")

POP_URL = "https://raw.githubusercontent.com/greatsong/modudata/main/data/population_yearly.csv.gz"
GEO_URL = "https://raw.githubusercontent.com/greatsong/modudata/main/data/boundaries/sigungu_kr.geojson"

@st.cache_data
def load_population():
    # '코드' 열은 앞자리 0이 사라지지 않게 문자열로 읽어요
    return pd.read_csv(POP_URL, dtype={"코드": str})

@st.cache_data
def load_geojson():
    return requests.get(GEO_URL).json()

df = load_population()
geojson = load_geojson()

# 1. 2026년 데이터만 사용
df = df[df["연도"] == 2026].copy()

# 2. '계_'로 시작하는 나이 열만 (남_·여_ 열은 제외)
total_cols = [c for c in df.columns if c.startswith("계_")]

# 3. 그중 65세 이상 열만 골라내기 ('계_65세' ~ '계_100세 이상')
def age_of(col):
    m = re.match(r"계_(\d+)세", col)
    return int(m.group(1)) if m else None

elderly_cols = [c for c in total_cols if age_of(c) is not None and age_of(c) >= 65]

# 4. 동 단위 전체 인구·고령 인구 계산
df["전체인구"] = df[total_cols].sum(axis=1)
df["고령인구"] = df[elderly_cols].sum(axis=1)

# 5. '코드' 앞 5자리 = 시군구 코드 → 시군구별로 묶어 비율 계산
df["시군구코드"] = df["코드"].str[:5]
grouped = df.groupby("시군구코드")[["전체인구", "고령인구"]].sum().reset_index()
grouped["고령화율"] = (grouped["고령인구"] / grouped["전체인구"] * 100).round(2)

# 경계 파일에서 코드 → 시군구 이름 짝 만들기 (마우스 올렸을 때 표시용)
names = pd.DataFrame([
    {"시군구코드": str(f["properties"]["코드"]), "시군구": f["properties"]["시군구"]}
    for f in geojson["features"]
])
merged = grouped.merge(names, on="시군구코드", how="left")

# 6. 단계구분도 그리기 (배경 타일 없이 경계만)
fig = px.choropleth(
    merged,
    geojson=geojson,
    locations="시군구코드",
    featureidkey="properties.코드",
    color="고령화율",
    color_continuous_scale="Reds",
    hover_name="시군구",
    labels={"고령화율": "65세 이상 비율(%)"},
)
fig.update_geos(fitbounds="locations", visible=False)
fig.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=700)

st.plotly_chart(fig, use_container_width=True)
