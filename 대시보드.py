"""실행: streamlit run 대시보드.py"""

from pathlib import Path

import pandas as pd
import streamlit as st


# =========================================================
# 기본 설정
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

CSV_NAME = "달빛팹_검사기록.csv"

PROCESS_COLUMNS = [
    "챔버온도",
    "챔버압력",
    "증착두께",
    "세정농도",
    "파티클수",
]

EXPECTED_COLUMNS = [
    "웨이퍼ID",
    "검사일",
    "라인",
    *PROCESS_COLUMNS,
    "판정",
]


# =========================================================
# 페이지 설정
# =========================================================

def configure_page():

    st.set_page_config(
        page_title="달빛 팹 관리실 v0.2",
        page_icon="🌙",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(
        """
        <style>

        .block-container {
            max-width: 1500px;
            padding-top: 2.5rem;
        }

        [data-testid="stMetric"] {
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 18px;
        }

        [data-testid="stMetricValue"] {
            font-variant-numeric: tabular-nums;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("🌙 달빛 팹 관리실 v0.2")

    st.write(
        "반도체 공정 검사 데이터 실시간 분석 대시보드"
    )

    st.caption(
        "FAB QUALITY MONITOR · 검사 현황과 라인별 점검 우선순위를 확인하세요."
    )


# =========================================================
# CSV 검색
# =========================================================

def find_csv_files():

    csv_files = []

    try:

        # -------------------------------------------------
        # 1순위
        # 정확한 파일명
        # -------------------------------------------------

        exact_files = list(
            BASE_DIR.rglob(CSV_NAME)
        )

        if exact_files:

            return sorted(exact_files)

        # -------------------------------------------------
        # 2순위
        # 달빛팹으로 시작하는 CSV
        #
        # 예:
        # 달빛팹_검사기록 (1).csv
        # -------------------------------------------------

        moonlight_files = list(
            BASE_DIR.rglob("달빛팹*.csv")
        )

        if moonlight_files:

            return sorted(moonlight_files)

        # -------------------------------------------------
        # 3순위
        # 프로젝트 전체의 CSV
        # -------------------------------------------------

        csv_files = list(
            BASE_DIR.rglob("*.csv")
        )

        return sorted(csv_files)

    except OSError as exc:

        st.error(
            f"프로젝트 폴더를 검색할 수 없습니다: {exc}"
        )

        return []


# =========================================================
# 데이터 불러오기
# =========================================================

def load_data():

    candidates = find_csv_files()

    # CSV가 하나도 없는 경우
    if not candidates:

        st.error(
            "CSV 파일을 찾을 수 없습니다."
        )

        st.warning(
            "GitHub 저장소에 달빛팹 검사 CSV 파일을 업로드해 주세요."
        )

        st.code(
            """
moonlight_pab/
├── 대시보드.py
├── requirements.txt
└── 달빛팹_검사기록.csv
            """
        )

        st.caption(
            f"검색한 프로젝트 폴더: {BASE_DIR}"
        )

        return None, None

    # -----------------------------------------------------
    # CSV 파일 선택
    # -----------------------------------------------------

    if len(candidates) == 1:

        path = candidates[0]

    else:

        relative_names = []

        for csv_path in candidates:

            try:

                relative_name = str(
                    csv_path.relative_to(BASE_DIR)
                )

            except ValueError:

                relative_name = csv_path.name

            relative_names.append(relative_name)

        selected = st.sidebar.selectbox(
            "분석할 CSV 파일",
            relative_names,
        )

        selected_index = relative_names.index(
            selected
        )

        path = candidates[selected_index]

    # -----------------------------------------------------
    # 여러 인코딩 자동 시도
    # -----------------------------------------------------

    encodings = [
        "utf-8-sig",
        "utf-8",
        "cp949",
        "euc-kr",
        "utf-16",
    ]

    for encoding in encodings:

        try:

            data = pd.read_csv(
                path,
                encoding=encoding,
                dtype="string",
            )

            # 열 이름 앞뒤 공백 제거
            data.columns = (
                data.columns
                .str.strip()
                .str.lstrip("\ufeff")
            )

            # 중복 열 확인
            if data.columns.duplicated().any():

                st.error(
                    "CSV에 중복되는 열 이름이 있습니다."
                )

                return None, path

            return data, path

        except UnicodeError:

            continue

        except pd.errors.EmptyDataError:

            st.error(
                "CSV 파일이 비어 있습니다."
            )

            return None, path

        except pd.errors.ParserError as exc:

            st.error(
                f"CSV 구조를 읽지 못했습니다: {exc}"
            )

            return None, path

        except OSError as exc:

            st.error(
                f"CSV 파일을 열 수 없습니다: {exc}"
            )

            return None, path

        except ValueError as exc:

            st.error(
                f"CSV 파일을 처리하지 못했습니다: {exc}"
            )

            return None, path

    st.error(
        "CSV 인코딩을 확인하지 못했습니다."
    )

    st.info(
        "CSV 파일을 UTF-8 또는 CP949 형식으로 저장해 주세요."
    )

    return None, path


# =========================================================
# CSV 열 연결
# =========================================================

def map_columns(data):

    missing = [
        column
        for column in EXPECTED_COLUMNS
        if column not in data.columns
    ]

    if not missing:

        return data

    st.info(
        "일부 항목의 열 이름이 다르거나 없습니다."
    )

    with st.expander(
        "CSV 열 확인 및 연결",
        expanded=True,
    ):

        st.write(
            "읽은 열:"
        )

        st.write(
            ", ".join(data.columns)
        )

        available = [
            column
            for column in data.columns
            if column not in EXPECTED_COLUMNS
        ]

        mapping = {}

        used_sources = set()

        for target in missing:

            source = st.selectbox(
                f"{target}에 사용할 열",
                [None, *available],
                format_func=lambda value:
                    "연결 안 함"
                    if value is None
                    else value,
                key=f"column_{target}",
            )

            if source is None:

                continue

            if source in used_sources:

                st.warning(
                    f"'{source}' 열을 이미 사용했습니다."
                )

                continue

            mapping[source] = target

            used_sources.add(source)

    return data.rename(
        columns=mapping
    )


# =========================================================
# 데이터 정리
# =========================================================

def prepare_data(data):

    data = data.copy()

    messages = []

    # -----------------------------------------------------
    # 문자열 공백 제거
    # -----------------------------------------------------

    for column in data.columns:

        if pd.api.types.is_string_dtype(
            data[column]
        ):

            data[column] = (
                data[column]
                .str.strip()
                .replace("", pd.NA)
            )

    # -----------------------------------------------------
    # 공정 수치 숫자로 변환
    # -----------------------------------------------------

    for column in PROCESS_COLUMNS:

        if column not in data.columns:

            continue

        original = data[column]

        converted = pd.to_numeric(
            original
            .str.replace(
                ",",
                "",
                regex=False,
            ),
            errors="coerce",
        )

        converted = converted.replace(
            [
                float("inf"),
                float("-inf"),
            ],
            pd.NA,
        )

        invalid = int(
            (
                original.notna()
                & converted.isna()
            ).sum()
        )

        if invalid:

            messages.append(
                f"{column}: 숫자로 변환할 수 없는 "
                f"{invalid}건을 결측값으로 처리했습니다."
            )

        data[column] = converted

    # -----------------------------------------------------
    # 날짜 변환
    # -----------------------------------------------------

    if "검사일" in data.columns:

        original = data["검사일"]

        try:

            converted = pd.to_datetime(
                original,
                errors="coerce",
                format="mixed",
            )

        except Exception:

            converted = pd.to_datetime(
                original,
                errors="coerce",
            )

        try:

            data["검사일"] = (
                converted
                .dt
                .normalize()
            )

        except Exception:

            data["검사일"] = pd.to_datetime(
                original,
                errors="coerce",
                utc=True,
            ).dt.tz_convert(
                None
            ).dt.normalize()

        invalid = int(
            (
                original.notna()
                & data["검사일"].isna()
            ).sum()
        )

        if invalid:

            messages.append(
                f"검사일: 날짜 변환 실패 "
                f"{invalid}건은 날짜 차트에서 제외됩니다."
            )

    # -----------------------------------------------------
    # 판정 값 확인
    # -----------------------------------------------------

    if "판정" in data.columns:

        data["판정"] = (
            data["판정"]
            .astype("string")
            .str.strip()
        )

        unknown = int(
            (
                data["판정"].notna()
                & ~data["판정"].isin(
                    [
                        "합격",
                        "불합격",
                    ]
                )
            ).sum()
        )

        if unknown:

            messages.append(
                f"합격/불합격 이외의 판정이 "
                f"{unknown}건 있습니다."
            )

    # -----------------------------------------------------
    # 없는 열 확인
    # -----------------------------------------------------

    missing = [
        column
        for column in EXPECTED_COLUMNS
        if column not in data.columns
    ]

    if missing:

        messages.append(
            "연결되지 않은 항목: "
            + ", ".join(missing)
        )

    if data.isna().any().any():

        messages.append(
            "결측값은 평균 계산에서 제외됩니다."
        )

    return data, messages


# =========================================================
# 사이드바 필터
# =========================================================

def show_filters(data):

    st.sidebar.header(
        "🔎 데이터 필터"
    )

    # -----------------------------------------------------
    # 라인 필터
    # -----------------------------------------------------

    if "라인" in data.columns:

        lines = sorted(
            data["라인"]
            .dropna()
            .unique()
            .tolist()
        )

    else:

        lines = []

    line = st.sidebar.selectbox(
        "라인 선택",
        [None, *lines],
        format_func=lambda value:
            "전체"
            if value is None
            else value,
        disabled=not lines,
    )

    # -----------------------------------------------------
    # 판정 필터
    # -----------------------------------------------------

    result = st.sidebar.selectbox(
        "판정 필터",
        [
            "전체",
            "합격",
            "불합격",
        ],
        disabled="판정" not in data.columns,
    )

    # -----------------------------------------------------
    # 목표 합격률
    # -----------------------------------------------------

    target = st.sidebar.slider(
        "목표 합격률 (%)",
        min_value=80,
        max_value=99,
        value=95,
        step=1,
    )

    # -----------------------------------------------------
    # 파티클 필터
    # -----------------------------------------------------

    minimum = None

    if (
        "파티클수" in data.columns
        and data["파티클수"].notna().any()
    ):

        particles = (
            data["파티클수"]
            .dropna()
        )

        low = float(
            particles.min()
        )

        high = float(
            particles.max()
        )

        if low < high:

            is_integer = bool(
                (
                    particles % 1 == 0
                ).all()
            )

            if is_integer:

                minimum = st.sidebar.slider(
                    "최소 파티클수",
                    min_value=int(low),
                    max_value=int(high),
                    value=int(low),
                    step=1,
                )

            else:

                minimum = st.sidebar.slider(
                    "최소 파티클수",
                    min_value=float(low),
                    max_value=float(high),
                    value=float(low),
                )

            # 최솟값이면 필터 사용 안 함
            if float(minimum) == float(low):

                minimum = None

        else:

            st.sidebar.caption(
                f"파티클수가 모두 {low:g}으로 같습니다."
            )

    else:

        st.sidebar.caption(
            "파티클수 데이터가 없어 파티클 필터를 사용할 수 없습니다."
        )

    st.sidebar.divider()

    st.sidebar.caption(
        "필터는 지표·차트·표에 동시에 적용됩니다."
    )

    return (
        line,
        result,
        target,
        minimum,
    )


# =========================================================
# 필터 적용
# =========================================================

def apply_filters(
    data,
    line,
    result,
    minimum,
):

    filtered = data.copy()

    if (
        line is not None
        and "라인" in filtered.columns
    ):

        filtered = filtered.loc[
            filtered["라인"] == line
        ]

    if (
        result != "전체"
        and "판정" in filtered.columns
    ):

        filtered = filtered.loc[
            filtered["판정"] == result
        ]

    if (
        minimum is not None
        and "파티클수" in filtered.columns
    ):

        filtered = filtered.loc[
            filtered["파티클수"]
            >= minimum
        ]

    return filtered


# =========================================================
# 핵심 지표
# =========================================================

def show_metrics(
    data,
    target,
):

    total = len(data)

    if "판정" in data.columns:

        passed = int(
            data["판정"]
            .eq("합격")
            .sum()
        )

        failed = int(
            data["판정"]
            .eq("불합격")
            .sum()
        )

    else:

        passed = None

        failed = None

    if (
        total > 0
        and passed is not None
    ):

        rate = (
            passed
            / total
            * 100
        )

    else:

        rate = None

    values = [
        f"{total:,}건",
        (
            f"{passed:,}건"
            if passed is not None
            else "—"
        ),
        (
            f"{failed:,}건"
            if failed is not None
            else "—"
        ),
        (
            f"{rate:.1f}%"
            if rate is not None
            else "—"
        ),
    ]

    labels = [
        "전체 검사 건수",
        "합격 건수",
        "불합격 건수",
        "합격률",
    ]

    metric_columns = st.columns(4)

    for column, label, value in zip(
        metric_columns,
        labels,
        values,
    ):

        column.metric(
            label,
            value,
        )

    st.caption(
        "합격률 = 합격 건수 ÷ 현재 필터 검사 건수 × 100"
    )

    # -----------------------------------------------------
    # 목표 달성 여부
    # -----------------------------------------------------

    with st.container(
        border=True
    ):

        if rate is None:

            st.subheader(
                "목표 판정 불가"
            )

            st.info(
                "판정 데이터가 없어 합격률을 계산할 수 없습니다."
            )

        elif rate >= target:

            st.subheader(
                "🟢 목표 달성"
            )

            st.success(
                f"현재 합격률 {rate:.1f}% / 목표 {target}%"
            )

            st.caption(
                f"목표보다 {rate - target:+.2f}%p 높습니다."
            )

        else:

            st.subheader(
                "🔴 목표 미달"
            )

            st.error(
                f"현재 합격률 {rate:.1f}% / 목표 {target}%"
            )

            st.caption(
                f"목표보다 {rate - target:+.2f}%p 낮습니다."
            )


# =========================================================
# 라인 요약
# =========================================================

def line_summary(data):

    if not {
        "라인",
        "판정",
    }.issubset(
        data.columns
    ):

        return pd.DataFrame()

    known = (
        data
        .dropna(
            subset=["라인"]
        )
        .copy()
    )

    if known.empty:

        return pd.DataFrame()

    known["불합격 건수"] = (
        known["판정"]
        .eq("불합격")
        .fillna(False)
        .astype(int)
    )

    summary = (
        known
        .groupby(
            "라인"
        )
        .agg(
            **{
                "전체 검사 건수":
                    (
                        "판정",
                        "size",
                    ),
                "불합격 건수":
                    (
                        "불합격 건수",
                        "sum",
                    ),
            }
        )
        .reset_index()
    )

    summary["불합격률 (%)"] = (
        summary["불합격 건수"]
        / summary["전체 검사 건수"]
        * 100
    )

    return summary.sort_values(
        [
            "불합격 건수",
            "라인",
        ],
        ascending=[
            False,
            True,
        ],
    )


# =========================================================
# 차트
# =========================================================

def show_charts(data):

    st.header(
        "📊 검사 현황"
    )

    left, right = st.columns(
        [
            1,
            2,
        ]
    )

    # -----------------------------------------------------
    # 판정별 검사 결과
    # -----------------------------------------------------

    with left:

        st.subheader(
            "판정별 검사 결과"
        )

        if (
            "판정" in data.columns
            and not data.empty
        ):

            counts = (
                data["판정"]
                .value_counts()
                .reindex(
                    [
                        "합격",
                        "불합격",
                    ],
                    fill_value=0,
                )
            )

            st.bar_chart(
                counts.rename(
                    "검사 건수"
                ),
                height=300,
            )

        else:

            st.info(
                "표시할 판정 데이터가 없습니다."
            )

    # -----------------------------------------------------
    # 라인별 불합격
    # -----------------------------------------------------

    with right:

        st.subheader(
            "라인별 불합격 건수"
        )

        summary = line_summary(
            data
        )

        if not summary.empty:

            chart_data = (
                summary[
                    [
                        "라인",
                        "불합격 건수",
                    ]
                ]
                .set_index(
                    "라인"
                )
            )

            st.bar_chart(
                chart_data,
                height=300,
            )

            st.caption(
                "불합격 건수가 높은 라인을 우선 확인하세요."
            )

        else:

            st.info(
                "라인과 판정 데이터가 있어야 차트를 표시할 수 있습니다."
            )

    # -----------------------------------------------------
    # 일별 검사량
    # -----------------------------------------------------

    st.subheader(
        "검사일별 검사 건수"
    )

    if (
        "검사일" in data.columns
        and data["검사일"].notna().any()
    ):

        daily = (
            data
            .dropna(
                subset=["검사일"]
            )
            .groupby(
                "검사일"
            )
            .size()
            .sort_index()
            .rename(
                "검사 건수"
            )
        )

        st.line_chart(
            daily,
            height=250,
        )

    else:

        st.info(
            "유효한 검사일 데이터가 없습니다."
        )


# =========================================================
# 탐정 보고
# =========================================================

def show_detective_report(data):

    st.header(
        "🕵️ 오늘의 탐정 보고"
    )

    st.caption(
        "CSV 전체 데이터를 기준으로 점검 우선순위를 분석합니다."
    )

    summary = line_summary(
        data
    )

    if summary.empty:

        st.info(
            "탐정 보고를 만들려면 라인과 판정 데이터가 필요합니다."
        )

        return

    maximum = int(
        summary[
            "불합격 건수"
        ].max()
    )

    if maximum == 0:

        st.success(
            "현재 기록에서 불합격이 발생한 라인이 없습니다."
        )

        return

    leaders = summary.loc[
        summary[
            "불합격 건수"
        ] == maximum
    ]

    names = ", ".join(
        leaders[
            "라인"
        ].astype(str)
    )

    if len(leaders) == 1:

        row = leaders.iloc[0]

        total = int(
            row[
                "전체 검사 건수"
            ]
        )

        failed = int(
            row[
                "불합격 건수"
            ]
        )

        failure_rate = float(
            row[
                "불합격률 (%)"
            ]
        )

        st.warning(
            f"관리자에게 보고: "
            f"{names}을(를) 먼저 점검해야 합니다. "
            f"전체 라인 중 불합격 {failed:,}건으로 가장 많습니다."
        )

        col1, col2, col3 = st.columns(
            3
        )

        col1.metric(
            "검사 건수",
            f"{total:,}건",
        )

        col2.metric(
            "불합격 건수",
            f"{failed:,}건",
        )

        col3.metric(
            "불합격률",
            f"{failure_rate:.1f}%",
        )

    else:

        st.warning(
            f"관리자에게 보고: "
            f"{names} 라인을 우선 점검해야 합니다. "
            f"각각 불합격 {maximum:,}건으로 공동 최다입니다."
        )

        st.dataframe(
            leaders,
            hide_index=True,
            use_container_width=True,
        )

    with st.expander(
        "전체 라인 비교"
    ):

        st.dataframe(
            summary,
            hide_index=True,
            use_container_width=True,
            column_config={
                "불합격률 (%)":
                    st.column_config.NumberColumn(
                        format="%.1f%%"
                    )
            },
        )


# =========================================================
# 공정 조건 비교
# =========================================================

def show_process_comparison(data):

    st.header(
        "🔬 합격 vs 불합격 공정 비교"
    )

    columns = [
        column
        for column in PROCESS_COLUMNS
        if column in data.columns
    ]

    if (
        "판정" not in data.columns
        or not columns
        or data.empty
    ):

        st.info(
            "비교할 공정 데이터가 없습니다."
        )

        return

    valid = data[
        data["판정"].isin(
            [
                "합격",
                "불합격",
            ]
        )
    ]

    if valid.empty:

        st.info(
            "합격/불합격 데이터가 없습니다."
        )

        return

    comparison = (
        valid
        .groupby(
            "판정"
        )[columns]
        .mean()
        .reindex(
            [
                "합격",
                "불합격",
            ]
        )
        .T
    )

    comparison.columns = [
        "합격 평균",
        "불합격 평균",
    ]

    comparison.index.name = "항목"

    st.dataframe(
        comparison.reset_index(),
        hide_index=True,
        use_container_width=True,
        column_config={
            "합격 평균":
                st.column_config.NumberColumn(
                    format="%.2f"
                ),
            "불합격 평균":
                st.column_config.NumberColumn(
                    format="%.2f"
                ),
        },
    )

    st.caption(
        "현재 필터 기준 평균값입니다. 결측값은 평균 계산에서 제외됩니다."
    )


# =========================================================
# 날짜 표시용
# =========================================================

def display_table(data):

    display = data.copy()

    if (
        "검사일" in display.columns
        and pd.api.types.is_datetime64_any_dtype(
            display["검사일"]
        )
    ):

        display["검사일"] = (
            display["검사일"]
            .dt
            .strftime(
                "%Y-%m-%d"
            )
        )

    return display


# =========================================================
# 파티클 상위 웨이퍼
# =========================================================

def show_particle_table(data):

    st.header(
        "⚠️ 파티클 집중 확인"
    )

    if (
        "파티클수" not in data.columns
        or not data["파티클수"]
        .notna()
        .any()
    ):

        st.info(
            "확인할 파티클수 데이터가 없습니다."
        )

        return

    top = (
        data
        .dropna(
            subset=["파티클수"]
        )
        .sort_values(
            "파티클수",
            ascending=False,
            kind="stable",
        )
        .head(10)
    )

    columns = [
        column
        for column in [
            "웨이퍼ID",
            "라인",
            "검사일",
            "파티클수",
            "판정",
        ]
        if column in top.columns
    ]

    st.caption(
        "현재 필터 기준 파티클수가 높은 상위 10건입니다."
    )

    st.dataframe(
        display_table(
            top[columns]
        ),
        hide_index=True,
        use_container_width=True,
    )


# =========================================================
# 전체 데이터 표
# =========================================================

def show_data_table(data):

    st.header(
        "📋 검사 데이터"
    )

    st.write(
        f"현재 표시 데이터: {len(data):,}건"
    )

    display = display_table(
        data
    )

    with st.expander(
        "전체 검사 데이터 보기"
    ):

        st.dataframe(
            display,
            hide_index=True,
            height=450,
            use_container_width=True,
        )

    csv_bytes = (
        display
        .to_csv(
            index=False
        )
        .encode(
            "utf-8-sig"
        )
    )

    st.download_button(
        "📥 필터 결과 CSV 다운로드",
        data=csv_bytes,
        file_name="달빛팹_필터결과.csv",
        mime="text/csv",
        disabled=data.empty,
    )


# =========================================================
# 메인
# =========================================================

def main():

    configure_page()

    # -----------------------------------------------------
    # CSV 로드
    # -----------------------------------------------------

    raw, path = load_data()

    if raw is None:

        st.stop()

    # -----------------------------------------------------
    # 열 확인 및 데이터 정리
    # -----------------------------------------------------

    mapped = map_columns(
        raw
    )

    data, messages = prepare_data(
        mapped
    )

    st.success(
        f"✅ 데이터 연결 완료: {path.name}"
    )

    st.caption(
        f"원본 검사 데이터 {len(data):,}건"
    )

    # -----------------------------------------------------
    # 데이터 확인 메시지
    # -----------------------------------------------------

    if messages:

        with st.expander(
            "데이터 확인 안내"
        ):

            for message in messages:

                st.warning(
                    message
                )

    if data.empty:

        st.info(
            "CSV에 검사 데이터가 없습니다."
        )

    # -----------------------------------------------------
    # 필터
    # -----------------------------------------------------

    (
        line,
        result,
        target,
        minimum,
    ) = show_filters(
        data
    )

    filtered = apply_filters(
        data,
        line,
        result,
        minimum,
    )

    if (
        filtered.empty
        and not data.empty
    ):

        st.warning(
            "필터 조건에 해당하는 데이터가 없습니다."
        )

    # -----------------------------------------------------
    # 지표
    # -----------------------------------------------------

    show_metrics(
        filtered,
        target,
    )

    st.divider()

    # -----------------------------------------------------
    # 차트
    # -----------------------------------------------------

    show_charts(
        filtered
    )

    st.divider()

    # -----------------------------------------------------
    # 탐정 보고
    # -----------------------------------------------------

    show_detective_report(
        data
    )

    st.divider()

    # -----------------------------------------------------
    # 공정 비교
    # -----------------------------------------------------

    show_process_comparison(
        filtered
    )

    st.divider()

    # -----------------------------------------------------
    # 파티클 분석
    # -----------------------------------------------------

    show_particle_table(
        filtered
    )

    st.divider()

    # -----------------------------------------------------
    # 데이터 표
    # -----------------------------------------------------

    show_data_table(
        filtered
    )


# =========================================================
# 실행
# =========================================================

if __name__ == "__main__":
 
    main() 