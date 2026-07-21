import os
import re

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# =========================================================
# 기본 설정
# =========================================================
st.set_page_config(
    page_title="연령별 인구 구조 대시보드",
    page_icon="📊",
    layout="wide",
)

# main.py와 같은 폴더에 아래 파일명 그대로 CSV를 올려주세요.
DATA_FILE = "202606_202606_연령별인구현황_월간.csv"


# =========================================================
# 데이터 로딩 & 전처리
# =========================================================
@st.cache_data
def load_data(file):
    df = pd.read_csv(file, encoding="cp949")

    # 첫 번째 컬럼(행정구역)을 제외한 모든 컬럼은 콤마가 섞인 숫자 문자열이므로 변환
    for col in df.columns[1:]:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.replace(" ", "", regex=False)
        )
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def get_month_prefix(df: pd.DataFrame) -> str:
    """컬럼명 앞의 '2026년06월' 같은 연월 접두어를 자동으로 추출"""
    match = re.match(r"^(\d{4}년\d{2}월)", df.columns[1])
    return match.group(1) if match else ""


def get_age_columns(df: pd.DataFrame, prefix: str, gender: str) -> list:
    """계 / 남 / 여 각각의 연령별 컬럼 목록을 나이 순서로 반환"""
    pattern = re.compile(rf"^{re.escape(prefix)}_{gender}_(\d+세|100세 이상)$")
    cols = [c for c in df.columns if pattern.match(c)]

    def age_key(col):
        m = re.search(r"(\d+)", col)
        return int(m.group(1)) if m else 999  # '100세 이상'을 맨 뒤로

    return sorted(cols, key=age_key)


def age_labels(cols: list) -> list:
    labels = []
    for c in cols:
        if "이상" in c:
            labels.append("100+")
        else:
            m = re.search(r"(\d+)세", c)
            labels.append(m.group(1) if m else c)
    return labels


# =========================================================
# 사이드바 - 데이터 불러오기
# =========================================================
st.sidebar.header("📁 데이터")
uploaded = st.sidebar.file_uploader("CSV 파일 업로드 (선택)", type="csv")

if uploaded is not None:
    df = load_data(uploaded)
elif os.path.exists(DATA_FILE):
    df = load_data(DATA_FILE)
else:
    st.warning(
        f"'{DATA_FILE}' 파일을 찾을 수 없습니다. "
        "리포지토리에 CSV를 포함시키거나, 왼쪽 사이드바에서 직접 업로드해주세요."
    )
    st.stop()

prefix = get_month_prefix(df)

age_cols_total = get_age_columns(df, prefix, "계")
age_cols_male = get_age_columns(df, prefix, "남")
age_cols_female = get_age_columns(df, prefix, "여")
ages = age_labels(age_cols_total)


# =========================================================
# 사이드바 - 지역 선택 (검색 입력 + 드롭다운 선택)
# =========================================================
st.sidebar.header("🔍 지역 선택")

search_kw = st.sidebar.text_input(
    "지역명 검색", placeholder="예: 강남, 해운대, 종로구 ..."
)

all_regions = df["행정구역"].dropna().tolist()

if search_kw:
    filtered_regions = [r for r in all_regions if search_kw.strip() in r]
else:
    filtered_regions = all_regions

if not filtered_regions:
    st.sidebar.warning("검색 결과가 없습니다. 다른 키워드를 입력해보세요.")
    st.stop()

selected_region = st.sidebar.selectbox(
    "행정구역 선택",
    filtered_regions,
    index=0,
)

st.sidebar.header("⚙️ 표시 옵션")
show_total = st.sidebar.checkbox("계 (전체)", value=True)
show_male = st.sidebar.checkbox("남자", value=True)
show_female = st.sidebar.checkbox("여자", value=True)


# =========================================================
# 메인 화면
# =========================================================
st.title("📊 지역별 연령별 인구 구조 대시보드")
st.caption(f"기준 시점: {prefix} · 데이터: 행정안전부 주민등록 연령별 인구현황")

row = df[df["행정구역"] == selected_region].iloc[0]

total_pop = row.get(f"{prefix}_계_총인구수", None)
male_pop = row.get(f"{prefix}_남_총인구수", None)
female_pop = row.get(f"{prefix}_여_총인구수", None)

col1, col2, col3 = st.columns(3)
col1.metric("총인구수", f"{total_pop:,.0f} 명" if pd.notna(total_pop) else "-")
col2.metric("남자", f"{male_pop:,.0f} 명" if pd.notna(male_pop) else "-")
col3.metric("여자", f"{female_pop:,.0f} 명" if pd.notna(female_pop) else "-")

st.subheader(f"'{selected_region}' 연령별 인구 구조")

fig = go.Figure()

if show_total:
    fig.add_trace(
        go.Scatter(
            x=ages,
            y=row[age_cols_total].values,
            mode="lines",
            name="계",
            line=dict(width=3, color="#1f77b4"),
        )
    )
if show_male:
    fig.add_trace(
        go.Scatter(
            x=ages,
            y=row[age_cols_male].values,
            mode="lines",
            name="남자",
            line=dict(width=2, color="#2ca02c"),
        )
    )
if show_female:
    fig.add_trace(
        go.Scatter(
            x=ages,
            y=row[age_cols_female].values,
            mode="lines",
            name="여자",
            line=dict(width=2, color="#d62728"),
        )
    )

fig.update_layout(
    xaxis_title="연령",
    yaxis_title="인구 수 (명)",
    hovermode="x unified",
    template="plotly_white",
    height=600,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)
fig.update_xaxes(tickangle=0, dtick=5)

st.plotly_chart(fig, use_container_width=True)

with st.expander("📋 원본 데이터 보기"):
    display_cols = ["행정구역"] + age_cols_total + age_cols_male + age_cols_female
    st.dataframe(
        df[df["행정구역"] == selected_region][display_cols].T.rename(
            columns={row.name: "값"}
        )
    )
