import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# =========================================================
# 화면 기본 설정
# =========================================================
st.set_page_config(
    page_title="동네별 인구 피라미드",
    page_icon="🔺",
    layout="wide",
)

# 데이터 주소예요. 확장자가 .gz(압축파일)여도 pandas가 알아서
# 압축을 풀어서 읽어줘요. 우리가 따로 압축을 풀 필요는 없어요!
DATA_URL = "https://raw.githubusercontent.com/greatsong/modudata/main/data/population_yearly.csv.gz"


# =========================================================
# 데이터 불러오기
# =========================================================
# @st.cache_data를 붙여두면, 한 번 불러온 데이터를 저장해뒀다가
# 재사용해요. 그래서 버튼을 눌러 화면이 다시 그려져도 매번
# 인터넷에서 다시 받아오지 않아 훨씬 빨라져요.
@st.cache_data
def load_data():
    df = pd.read_csv(DATA_URL, compression="gzip")
    return df


with st.spinner("인구 데이터를 불러오고 있어요... 잠시만 기다려주세요 🙂"):
    df = load_data()

st.title("🔺 동네별 인구 피라미드")
st.write(
    "시도 → 시군구 → 동을 차례로 골라서, 그 동네의 남녀·연령별 인구 구조를 "
    "피라미드 모양으로 살펴보는 앱이에요."
)

# =========================================================
# 1단계. 가장 최신 연도만 남기기
# =========================================================
latest_year = df["연도"].max()
df_latest = df[df["연도"] == latest_year].copy()

st.info(f"📅 가장 최신 연도인 **{latest_year}년** 데이터를 사용할게요.")

st.divider()

# =========================================================
# 2단계. 시도 → 시군구 → 동, 드롭다운 3개로 동네 고르기
# =========================================================
st.subheader("📍 우리 동네를 골라주세요")

col1, col2, col3 = st.columns(3)

# --- 시도 고르기 ---
with col1:
    sido_list = sorted(df_latest["시도"].dropna().unique())
    selected_sido = st.selectbox("시/도", sido_list)

# 선택한 시도에 맞춰서 시군구 목록을 좁혀요.
df_sido = df_latest[df_latest["시도"] == selected_sido]

# --- 시군구 고르기 ---
with col2:
    sigungu_list = sorted(df_sido["시군구"].dropna().unique())
    selected_sigungu = st.selectbox("시/군/구", sigungu_list)

# 선택한 시군구에 맞춰서 동 목록을 좁혀요.
df_sigungu = df_sido[df_sido["시군구"] == selected_sigungu]

# --- 동 고르기 ---
with col3:
    dong_list = sorted(df_sigungu["동"].dropna().unique())
    selected_dong = st.selectbox("읍/면/동", dong_list)

# 최종적으로 고른 동 하나에 해당하는 행(row)을 뽑아요.
df_dong = df_sigungu[df_sigungu["동"] == selected_dong]

if df_dong.empty:
    st.warning("해당 조건의 데이터를 찾을 수 없어요. 다른 지역을 선택해보세요.")
    st.stop()

# 혹시 같은 이름의 동이 여러 개 있을 경우를 대비해서, 첫 번째 행만 사용해요.
selected_row = df_dong.iloc[0]

st.success(f"✅ 선택한 동네: **{selected_sido} {selected_sigungu} {selected_dong}** ({latest_year}년)")

st.divider()

# =========================================================
# 3단계. 나이별 남/여 인구 뽑아오기
# =========================================================
# 나이 라벨을 0세부터 99세까지, 그리고 마지막에 '100세 이상'까지
# 순서대로 만들어요. 이 순서가 나중에 그래프의 세로축 순서를 정하는
# 아주 중요한 기준이 돼요.
age_labels = [f"{age}세" for age in range(100)] + ["100세 이상"]

# 위에서 만든 나이 라벨 앞에 '남_', '여_'를 붙여서 실제 열 이름을 만들어요.
male_cols = [f"남_{age}" for age in age_labels]
female_cols = [f"여_{age}" for age in age_labels]

# 혹시 데이터에 없는 열이 있는지 미리 확인해서, 있으면 알려줘요.
missing_cols = [c for c in male_cols + female_cols if c not in df_latest.columns]
if missing_cols:
    st.error(
        "데이터에서 다음 열을 찾을 수 없어요. 열 이름을 다시 확인해주세요:\n"
        + ", ".join(missing_cols[:10])
        + (" ..." if len(missing_cols) > 10 else "")
    )
    st.stop()

# 선택한 동네의 남자 인구, 여자 인구를 나이 순서대로 뽑아요.
# pd.to_numeric으로 혹시 모를 이상한 값을 숫자로 안전하게 바꿔줘요.
male_pop = pd.to_numeric(selected_row[male_cols], errors="coerce").fillna(0).values
female_pop = pd.to_numeric(selected_row[female_cols], errors="coerce").fillna(0).values

# 남자 + 여자를 나이별로 더해서, '나이별 전체 인구'도 만들어둬요.
# (지표 카드와 아래 한 줄 설명에서 사용할 거예요.)
total_by_age = male_pop + female_pop
total_pop = float(total_by_age.sum())

# =========================================================
# 3-1단계. 지표 카드에 쓸 값들 계산하기
# =========================================================
# --- 평균연령 계산하기 ---
# 나이 라벨이 '0세', '1세', ... 처럼 글자이기 때문에, 계산에 쓸 수 있게
# 숫자 나이 목록을 따로 만들어요. '100세 이상'은 정확한 나이를 알 수 없으니
# 105세 정도로 근사해서 계산해요(평균연령 계산에서 흔히 쓰는 방법이에요).
numeric_ages = list(range(100)) + [105]

if total_pop > 0:
    avg_age = float((total_by_age * numeric_ages).sum() / total_pop)
else:
    avg_age = 0.0

# --- 고령화율 계산하기 (65세 이상 인구 비율) ---
# age_labels는 0세부터 순서대로이므로, 인덱스 65번째부터가 '65세'예요.
# (age_labels[65] == '65세', 그 뒤로 100세 이상까지 전부 65세 이상 인구)
elderly_pop = float(total_by_age[65:].sum())
aging_rate = (elderly_pop / total_pop * 100) if total_pop > 0 else 0.0

# --- 유소년 비율도 계산해두기 (0~14세) ---
# 뒤에서 '아이가 많은 동네인지, 어르신이 많은 동네인지' 설명할 때 써요.
young_pop = float(total_by_age[0:15].sum())
young_rate = (young_pop / total_pop * 100) if total_pop > 0 else 0.0

# =========================================================
# 3-2단계. 지표 카드 3개 나란히 보여주기
# =========================================================
st.subheader("📊 한눈에 보는 동네 지표")

card1, card2, card3 = st.columns(3)

card1.metric("총인구", f"{total_pop:,.0f} 명")
card2.metric("평균연령", f"{avg_age:.1f} 세")
card3.metric("고령화율 (65세 이상 비율)", f"{aging_rate:.1f} %")

# 고령화율이 20%를 넘으면(통계청 기준 '초고령사회' 기준선) 주의 표시를 붙여줘요.
if aging_rate >= 20:
    card3.markdown("⚠️ **초고령사회 기준(20%) 초과**")

st.divider()

# =========================================================
# 4단계. 인구 피라미드 그리기 (Plotly)
# =========================================================
st.subheader(f"'{selected_dong}'의 인구 피라미드")
st.write(
    "왼쪽 파란 막대는 **남자**, 오른쪽 분홍 막대는 **여자** 인구예요. "
    "남자 쪽은 그래프를 왼쪽으로 그리기 위해 값에 마이너스(-)를 붙였을 뿐, "
    "실제로는 모두 양수(플러스) 인구수예요. 마우스를 막대에 올리면 정확한 인구수가 보여요."
)

fig = go.Figure()

# --- 남자 막대 (왼쪽) ---
# x값에 마이너스를 붙여서 왼쪽으로 그려지게 해요.
# customdata에는 원래(양수) 인구수를 넣어두고, hovertemplate에서 그 값을 보여줘요.
fig.add_trace(
    go.Bar(
        y=age_labels,
        x=-male_pop,
        orientation="h",
        name="남자",
        marker=dict(color="#4C72B0"),
        customdata=male_pop,
        hovertemplate="나이: %{y}<br>남자 인구: %{customdata:,.0f}명<extra></extra>",
    )
)

# --- 여자 막대 (오른쪽) ---
fig.add_trace(
    go.Bar(
        y=age_labels,
        x=female_pop,
        orientation="h",
        name="여자",
        marker=dict(color="#DD8452"),
        customdata=female_pop,
        hovertemplate="나이: %{y}<br>여자 인구: %{customdata:,.0f}명<extra></extra>",
    )
)

fig.update_layout(
    title=f"{selected_sido} {selected_sigungu} {selected_dong} ({latest_year}년) 인구 피라미드",
    xaxis_title="인구 수 (명) · 왼쪽=남자, 오른쪽=여자",
    yaxis_title="나이",
    barmode="overlay",
    bargap=0.05,
    template="plotly_white",
    height=900,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)

# -----------------------------------------------------------------
# ⭐ 세로축(나이) 순서를 직접 고정하는 부분이에요. 아주 중요해요!
#
# 나이 라벨이 '0세', '1세', ..., '10세', '100세 이상' 같은 '글자(문자열)'
# 이기 때문에, 아무 설정도 안 하면 Plotly가 사전 순서(가나다순 비슷하게)로
# 정렬해버려서 '10세'가 '2세'보다 앞에 오는 등 순서가 뒤죽박죽될 수 있어요.
#
# 그래서 categoryorder를 "array"로 지정하고, categoryarray에 우리가
# 원하는 순서(0세 -> 1세 -> ... -> 100세 이상)를 직접 넣어줘요.
# 이렇게 하면 이 배열의 '첫 번째 항목이 축의 맨 아래'에 오고,
# '마지막 항목이 축의 맨 위'에 오게 돼요.
#
# 즉, age_labels를 0세부터 100세 이상까지 오름차순으로 그대로 넣으면
# -> 맨 아래 눈금 = 0세, 맨 위 눈금 = 100세 이상 이 됩니다. (원하는 결과!)
# -----------------------------------------------------------------
fig.update_yaxes(
    categoryorder="array",
    categoryarray=age_labels,
)

st.plotly_chart(fig, use_container_width=True)

st.caption(
    "💡 그래프를 다 그린 뒤에는 항상 세로축을 눈으로 확인해보는 습관을 들이면 좋아요. "
    "맨 아래 눈금이 '0세', 맨 위 눈금이 '100세 이상'으로 보이면 정상이에요."
)

# =========================================================
# 5단계. '아이가 많은 동네인가요, 어르신이 많은 동네인가요?' 자동 설명
# =========================================================
# 유소년 비율(young_rate)과 고령화율(aging_rate)을 비교해서,
# 어느 쪽이 더 두드러지는지에 따라 다른 문장을 보여줘요.
age_gap = aging_rate - young_rate  # 양수면 어르신 쪽이 더 많다는 뜻

if age_gap >= 10:
    summary_text = "🧓 **어르신이 많은, 고령화된 동네**예요."
elif age_gap <= -5:
    summary_text = "👶 **아이가 많은, 젊은 동네**예요."
else:
    summary_text = "⚖️ **아이와 어르신 비율이 비교적 균형 잡힌 동네**예요."

st.info(
    f"{summary_text}\n\n"
    f"(유소년 비율(0~14세) {young_rate:.1f}% · 고령화율(65세 이상) {aging_rate:.1f}%)"
)

st.divider()
st.caption(
    "💡 데이터 출처: greatsong/modudata (population_yearly.csv.gz) · "
    "이 앱은 학습·연습 목적으로 만들어졌어요."
)
