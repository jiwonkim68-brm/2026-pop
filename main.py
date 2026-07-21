import pandas as pd
import plotly.express as px
import streamlit as st

# =========================================================
# 화면 기본 설정
# =========================================================
# page_title : 브라우저 탭에 뜨는 제목
# page_icon  : 브라우저 탭 아이콘(이모지도 가능해요)
# layout     : "wide"로 하면 화면을 꽉 채워서 넓게 보여줘요
st.set_page_config(
    page_title="우리나라 인구, 얼마나 퍼져있을까?",
    page_icon="🌱",
    layout="wide",
)

# 데이터가 있는 주소예요. 확장자가 .gz(압축파일)여도
# pandas가 알아서 압축을 풀어서 읽어줘요. 우리가 따로 할 일은 없어요!
DATA_URL = "https://raw.githubusercontent.com/greatsong/modudata/main/data/population_yearly.csv.gz"


# =========================================================
# 데이터 불러오기
# =========================================================
# @st.cache_data 를 붙여두면, 한 번 불러온 데이터는 저장해뒀다가
# 재사용해요. 그래서 앱이 새로고침될 때마다 매번 인터넷에서
# 다시 받아오지 않아도 되어서 훨씬 빨라져요.
@st.cache_data
def load_data():
    # 주소 끝이 .gz라서 pandas가 압축 파일인 걸 자동으로 알아채고
    # 알아서 압축을 풀면서 읽어줘요. 우리는 그냥 평범한 CSV처럼
    # read_csv 한 줄만 쓰면 됩니다.
    df = pd.read_csv(DATA_URL, compression="gzip")
    return df


# 화면에 "불러오는 중이에요" 같은 안내를 보여주면서 데이터를 불러와요.
with st.spinner("인구 데이터를 불러오고 있어요... 잠시만 기다려주세요 🙂"):
    df = load_data()

st.title("🌱 우리 동네 인구, 얼마나 퍼져있을까?")
st.write(
    "전국 읍·면·동 단위로, 동네마다 사람이 얼마나 살고 있는지를 모아서 "
    "'퍼짐(분포)'을 살펴보는 아주 간단한 앱이에요."
)

# =========================================================
# 1단계. 가장 최신 연도만 남기기
# =========================================================
# '연도' 열에서 가장 큰 값(=가장 최근 연도)만 골라내요.
latest_year = df["연도"].max()
df_latest = df[df["연도"] == latest_year].copy()

st.info(f"📅 가장 최신 연도인 **{latest_year}년** 데이터만 사용할게요. "
        f"(전체 {len(df_latest):,}개 동네)")

# =========================================================
# 2단계. '총인구' 열 새로 만들기
# =========================================================
# 이 데이터는 '남_0세', '여_0세', '남_1세', '여_1세' ... 처럼
# 나이 하나마다 남자/여자 인구가 각각 열로 나뉘어 있어요.
# 그래서 이름이 '남_'이나 '여_'로 시작하는 열을 전부 찾아서
# 한 동네(한 행)마다 옆으로 다 더하면, 그 동네의 총인구가 나와요.
gender_age_cols = [
    col for col in df_latest.columns
    if col.startswith("남_") or col.startswith("여_")
]

# 혹시 숫자가 아닌 값(빈 칸 등)이 섞여 있을 수도 있으니,
# 안전하게 숫자로 한 번 변환해줘요. 변환이 안 되는 값은 0으로 처리해요.
df_latest[gender_age_cols] = df_latest[gender_age_cols].apply(
    pd.to_numeric, errors="coerce"
).fillna(0)

# axis=1은 "옆으로(가로로) 더하기"라는 뜻이에요.
# (axis=0은 위아래로 더하기)
df_latest["총인구"] = df_latest[gender_age_cols].sum(axis=1)

st.divider()

# =========================================================
# 화면에 보여줄 1) describe() 결과 표
# =========================================================
st.header("1️⃣ 총인구, 숫자로 요약해서 보기")
st.write(
    "describe()는 데이터를 한눈에 요약해주는 함수예요. "
    "평균이 얼마인지, 가장 작은 동네와 가장 큰 동네는 인구가 몇 명인지, "
    "전체적으로 어떻게 퍼져있는지를 숫자로 보여줘요."
)

# describe()의 결과(Series)를 보기 좋은 표 형태로 바꿔줘요.
describe_table = df_latest["총인구"].describe().to_frame(name="총인구")
# 한국어로 이름을 바꿔서 더 이해하기 쉽게 만들어요.
describe_table.index = [
    "동네 개수 (count)",
    "평균 (mean)",
    "표준편차 (std)",
    "최솟값 (min)",
    "25% 지점",
    "50% 지점 (중앙값)",
    "75% 지점",
    "최댓값 (max)",
]
# 소수점은 보기 편하게 반올림해요.
st.dataframe(
    describe_table.style.format("{:,.1f}"),
    use_container_width=True,
)

st.divider()

# =========================================================
# 화면에 보여줄 2) 총인구 히스토그램
# =========================================================
st.header("2️⃣ 히스토그램으로 퍼짐 살펴보기")
st.write(
    "히스토그램은 인구수를 여러 구간으로 나눈 뒤, "
    "각 구간에 동네가 몇 개나 있는지 막대로 세어서 보여줘요. "
    "막대가 왼쪽(적은 인구)에 몰려있다면, 대부분 작은 동네가 많다는 뜻이에요. "
    "마우스로 드래그하면 확대할 수 있고, 더블클릭하면 원래대로 돌아와요."
)

fig_hist = px.histogram(
    df_latest,
    x="총인구",
    nbins=60,  # 막대(구간)를 몇 개로 나눌지 정해요. 숫자를 바꿔보며 실험해도 좋아요.
    labels={"총인구": "동네별 총인구 (명)"},
    title=f"{latest_year}년 읍·면·동 총인구 히스토그램",
)
fig_hist.update_layout(
    yaxis_title="동네 개수",
    bargap=0.05,  # 막대 사이 살짝 간격을 줘서 더 보기 편하게 해요.
)
# use_container_width=True로 하면 화면 너비에 맞춰 그래프가 늘어나요.
st.plotly_chart(fig_hist, use_container_width=True)

st.divider()

# =========================================================
# 화면에 보여줄 3) 총인구 상자그림(박스플롯)
# =========================================================
st.header("3️⃣ 상자그림(박스플롯)으로 퍼짐 살펴보기")
st.write(
    "상자그림은 데이터를 작은 값부터 큰 값까지 줄 세운 뒤, "
    "가운데 절반이 모여있는 구간을 상자로, 유난히 튀는 값(이상치)을 "
    "점으로 따로 보여줘요. 상자가 좁을수록 동네들의 인구가 서로 "
    "비슷하다는 뜻이고, 점이 많을수록 유난히 인구가 많거나 적은 "
    "동네가 많다는 뜻이에요."
)

fig_box = px.box(
    df_latest,
    y="총인구",
    points="outliers",  # 이상치(튀는 값)만 점으로 표시해요.
    labels={"총인구": "동네별 총인구 (명)"},
    title=f"{latest_year}년 읍·면·동 총인구 상자그림",
)
st.plotly_chart(fig_box, use_container_width=True)

st.divider()
st.caption(
    "💡 데이터 출처: greatsong/modudata (population_yearly.csv.gz) · "
    "이 앱은 학습·연습 목적으로 만들어졌어요."
)
