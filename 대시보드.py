"""실행: streamlit run 대시보드.py"""

from pathlib import Path
from io import BytesIO

import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent
CSV_NAME = "달빛팹_검사기록.csv"
PROCESS_COLUMNS = ["챔버온도", "챔버압력", "증착두께", "세정농도", "파티클수"]
EXPECTED_COLUMNS = ["웨이퍼ID", "검사일", "라인", *PROCESS_COLUMNS, "판정"]


def configure_page():
    st.set_page_config(page_title="달빛 팹 관리실 v0.2", page_icon="🌙", layout="wide")
    st.markdown(
        """<style>
        .block-container {max-width: 1500px; padding-top: 2.5rem;}
        [data-testid="stMetric"] {
            border: 1px solid #334155; border-radius: 12px; padding: 18px;
        }
        [data-testid="stMetricValue"] {font-variant-numeric: tabular-nums;}
        </style>""",
        unsafe_allow_html=True,
    )
    st.title("🌙 달빛 팹 관리실 v0.2")
    st.write("반도체 공정 검사 데이터 실시간 분석 대시보드")
    st.caption("FAB QUALITY MONITOR · 검사 현황과 라인별 점검 우선순위를 확인하세요.")


def find_local_csv_files():
    """대시보드 폴더와 하위 폴더에서 CSV를 안전하게 찾는다."""
    try:
        exact = sorted(BASE_DIR.rglob(CSV_NAME))
        if exact:
            return exact

        moonlight = sorted(BASE_DIR.rglob("달빛팹*.csv"))
        if moonlight:
            return moonlight

        return sorted(BASE_DIR.rglob("*.csv"))
    except OSError as exc:
        st.error(f"프로젝트 폴더를 검색할 수 없습니다: {exc}")
        return []


def read_csv_safely(source, source_name):
    """UTF-8/CP949/UTF-16 CSV를 순서대로 시도해 읽는다."""
    try:
        raw_bytes = source.read() if hasattr(source, "read") else Path(source).read_bytes()
    except OSError as exc:
        st.error(f"CSV 파일을 열 수 없습니다: {exc}")
        return None, source_name

    for encoding in ("utf-8-sig", "utf-8", "cp949", "euc-kr", "utf-16"):
        try:
            # 웨이퍼 ID 앞자리 0 등을 보존하기 위해 먼저 문자열로 읽는다.
            data = pd.read_csv(BytesIO(raw_bytes), encoding=encoding, dtype="string")
            data.columns = data.columns.str.strip().str.lstrip("\ufeff")

            if data.columns.duplicated().any():
                st.error("CSV에 중복되는 열 이름이 있습니다. 열 이름을 확인해 주세요.")
                return None, source_name

            return data, source_name
        except UnicodeError:
            continue
        except pd.errors.EmptyDataError:
            st.error("CSV 파일이 비어 있습니다.")
            return None, source_name
        except (pd.errors.ParserError, OSError, ValueError) as exc:
            st.error(f"CSV 파일을 읽지 못했습니다: {exc}")
            return None, source_name

    st.error("CSV 인코딩을 확인하지 못했습니다. UTF-8 또는 CP949로 저장해 주세요.")
    return None, source_name


def load_data(uploaded_file):
    """업로드 파일을 우선 사용하고, 없으면 프로젝트의 기본 CSV를 읽는다."""
    if uploaded_file is not None:
        data, name = read_csv_safely(uploaded_file, uploaded_file.name)
        if data is not None:
            st.sidebar.success(f"업로드 데이터 사용 중: {uploaded_file.name}")
        return data, name

    candidates = find_local_csv_files()
    if not candidates:
        st.error("기본 CSV 파일을 찾을 수 없습니다.")
        st.info("왼쪽의 '새 CSV 불러오기'에서 CSV를 선택하면 바로 분석할 수 있습니다.")
        return None, None

    if len(candidates) == 1:
        path = candidates[0]
    else:
        names = [str(path.relative_to(BASE_DIR)) for path in candidates]
        selected = st.sidebar.selectbox("프로젝트 CSV 선택", names)
        path = candidates[names.index(selected)]

    return read_csv_safely(path, path.name)


def map_columns(data):
    """실제 열 목록을 확인하고, 이름이 다르면 사용자가 직접 연결한다."""
    missing = [column for column in EXPECTED_COLUMNS if column not in data.columns]
    if not missing:
        return data

    st.info("일부 항목의 열 이름이 다르거나 없습니다. 아래에서 실제 열을 연결할 수 있습니다. 없는 항목은 해당 분석만 생략합니다.")
    with st.expander("CSV 열 확인 및 연결", expanded=True):
        st.write("읽은 열: " + ", ".join(data.columns))
        available = [column for column in data.columns if column not in EXPECTED_COLUMNS]
        mapping = {}
        for target in missing:
            source = st.selectbox(
                f"{target}에 사용할 열", [None, *available],
                format_func=lambda value: "연결 안 함" if value is None else value,
                key=f"column_{target}",
            )
            if source is not None:
                if source in mapping:
                    st.warning(f"'{source}' 열을 중복 선택했습니다. 각 항목에 서로 다른 열을 연결해 주세요.")
                    continue
                mapping[source] = target
    return data.rename(columns=mapping)


def prepare_data(data):
    """변환할 수 없는 값은 결측값으로 처리하고 화면에 알린다."""
    data = data.copy()
    messages = []
    for column in data.columns:
        data[column] = data[column].str.strip().replace("", pd.NA)

    for column in PROCESS_COLUMNS:
        if column not in data:
            continue
        original = data[column]
        converted = pd.to_numeric(original.str.replace(",", "", regex=False), errors="coerce")
        converted = converted.replace([float("inf"), float("-inf")], pd.NA)
        invalid = int((original.notna() & converted.isna()).sum())
        if invalid:
            messages.append(f"{column}: 숫자로 변환할 수 없는 {invalid}건을 결측값으로 처리했습니다.")
        data[column] = converted

    if "검사일" in data:
        original = data["검사일"]
        converted = pd.to_datetime(original, errors="coerce", format="mixed")
        # 일반적인 날짜 문자열 외의 형식도 앱 전체를 중단시키지 않는다.
        try:
            data["검사일"] = converted.dt.normalize()
        except AttributeError:
            data["검사일"] = pd.to_datetime(original, errors="coerce", format="mixed", utc=True).dt.tz_convert(None).dt.normalize()
        invalid = int((original.notna() & data["검사일"].isna()).sum())
        if invalid:
            messages.append(f"검사일: 날짜 변환에 실패한 {invalid}건은 날짜 차트에서 제외됩니다.")

    if "판정" in data:
        unknown = int((~data["판정"].isin(["합격", "불합격"])).sum())
        if unknown:
            messages.append(f"판정 미입력 또는 합격/불합격 이외의 값이 {unknown}건 있습니다. 전체 검사 건수에는 포함되지만 합격·불합격 건수에는 포함되지 않습니다.")
    missing = [column for column in EXPECTED_COLUMNS if column not in data]
    if missing:
        messages.append("연결되지 않은 항목: " + ", ".join(missing))
    if data.isna().any().any():
        messages.append("결측값은 표에 비어 있는 값으로 표시하며, 평균 계산에서는 제외합니다.")
    return data, messages


def show_filters(data):
    st.sidebar.header("🔎 데이터 필터")
    lines = sorted(data["라인"].dropna().unique().tolist()) if "라인" in data else []
    line = st.sidebar.selectbox("라인 선택", [None, *lines],
                                format_func=lambda value: "전체" if value is None else value,
                                disabled=not lines)
    result = st.sidebar.selectbox("판정 필터", ["전체", "합격", "불합격"], disabled="판정" not in data)
    target = st.sidebar.slider("목표 합격률 (%)", 80, 99, 95)
    minimum = None
    if "파티클수" in data and data["파티클수"].notna().any():
        particles = data["파티클수"].dropna()
        low, high = float(particles.min()), float(particles.max())
        if low < high:
            is_integer = bool((particles % 1 == 0).all())
            if is_integer:
                minimum = st.sidebar.slider("최소 파티클수", int(low), int(high), int(low), step=1)
            else:
                minimum = st.sidebar.slider("최소 파티클수", low, high, low)
            # 기본 위치는 결측값을 포함한 전체 데이터 표시를 의미한다.
            if minimum == low:
                minimum = None
            st.sidebar.caption("최솟값에서는 결측값을 포함해 전체를 표시합니다. 값을 높이면 파티클수 미입력 행은 제외됩니다.")
        else:
            st.sidebar.caption(f"유효한 파티클수가 모두 {low:g}으로 같아 전체를 표시합니다.")
    else:
        st.sidebar.caption("파티클수 데이터가 없어 파티클 필터를 사용할 수 없습니다.")
    st.sidebar.caption("필터는 모든 지표·차트·표에 동시에 적용됩니다. 탐정 보고만 전체 원본 데이터를 사용합니다.")
    return line, result, target, minimum


def apply_filters(data, line, result, minimum):
    filtered = data.copy()
    if line is not None and "라인" in filtered:
        filtered = filtered.loc[filtered["라인"] == line]
    if result != "전체" and "판정" in filtered:
        filtered = filtered.loc[filtered["판정"] == result]
    if minimum is not None and "파티클수" in filtered:
        filtered = filtered.loc[filtered["파티클수"] >= minimum]
    return filtered


def show_metrics(data, target):
    total = len(data)
    passed = int(data["판정"].eq("합격").sum()) if "판정" in data else None
    failed = int(data["판정"].eq("불합격").sum()) if "판정" in data else None
    rate = passed / total * 100 if total and passed is not None else None
    values = [f"{total:,}건", f"{passed:,}건" if passed is not None else "—",
              f"{failed:,}건" if failed is not None else "—", f"{rate:.1f}%" if rate is not None else "—"]
    for column, label, value in zip(st.columns(4), ["전체 검사 건수", "합격 건수", "불합격 건수", "합격률"], values):
        column.metric(label, value)
    st.caption("합격률 = 합격 건수 ÷ 현재 필터의 전체 검사 건수 × 100")
    with st.container(border=True):
        if rate is None:
            st.subheader("목표 판정 불가")
            st.info("검사 데이터 또는 판정 열이 없어 합격률을 계산할 수 없습니다.")
        else:
            st.subheader("✅ 목표 달성" if rate >= target else "⚠️ 목표 미달")
            st.write(f"현재 {rate:.1f}% / 목표 {target}%")
            st.caption(f"목표와의 차이: {rate - target:+.2f}%p · 판정은 반올림 전 수치 기준")


def line_summary(data):
    """불합격이 없는 라인도 0건으로 포함한다."""
    if not {"라인", "판정"}.issubset(data.columns):
        return pd.DataFrame()
    known = data.dropna(subset=["라인"]).copy()
    known["불합격 건수"] = known["판정"].eq("불합격").fillna(False).astype(int)
    summary = known.groupby("라인").agg(
        **{"전체 검사 건수": ("판정", "size"), "불합격 건수": ("불합격 건수", "sum")}
    ).reset_index()
    summary["불합격률 (%)"] = summary["불합격 건수"] / summary["전체 검사 건수"] * 100
    return summary.sort_values(["불합격 건수", "라인"], ascending=[False, True])


def show_charts(data):
    left, right = st.columns([1, 2])
    with left:
        st.subheader("판정별 검사 결과")
        if "판정" in data and not data.empty:
            counts = data["판정"].value_counts().reindex(["합격", "불합격"], fill_value=0)
            st.bar_chart(counts.rename("검사 건수"), color="#60a5fa", height=300)
        else:
            st.info("표시할 판정 데이터가 없습니다.")
    with right:
        st.subheader("라인별 불합격 건수")
        summary = line_summary(data)
        if not summary.empty:
            chart_data = summary.set_index("라인")[["불합격 건수"]]
            st.bar_chart(chart_data, color="#fb923c", height=300)
            st.caption("불합격 건수 내림차순 · 검사량이 많은 라인은 건수도 커질 수 있으므로 불합격률을 함께 확인하세요.")
        else:
            st.info("라인과 판정 데이터가 있어야 차트를 표시할 수 있습니다.")
    st.subheader("검사일별 검사 건수")
    if "검사일" in data and data["검사일"].notna().any():
        daily = data.dropna(subset=["검사일"]).groupby("검사일").size().sort_index().rename("검사 건수")
        st.line_chart(daily, color="#38bdf8", height=230)
    else:
        st.info("유효한 검사일 데이터가 없습니다.")


def show_detective_report(data):
    st.subheader("🕵️ 오늘의 탐정 보고")
    st.caption("사이드바 필터와 무관하게 CSV 전체 기간·전체 데이터를 분석합니다. 원인 확정이 아닌 점검 우선순위 안내입니다.")
    summary = line_summary(data)
    if summary.empty:
        st.info("탐정 보고를 만들려면 검사 데이터와 라인·판정 열이 필요합니다.")
        return
    missing_lines = int(data["라인"].isna().sum())
    if missing_lines:
        st.warning(f"라인 미입력 {missing_lines}건은 라인 비교에서 제외했습니다.")
    maximum = int(summary["불합격 건수"].max())
    if maximum == 0:
        st.success("라인이 확인된 데이터에서 불합격 기록이 없습니다.")
        return
    leaders = summary.loc[summary["불합격 건수"] == maximum]
    names = ", ".join(leaders["라인"].astype(str))
    qualifier = "각각 " if len(leaders) > 1 else ""
    st.warning(f"관리자에게 보고: {names}을(를) 먼저 점검해야 합니다. 전체 라인 중 불합격 {qualifier}{maximum:,}건으로 가장 많습니다.")
    with st.container(border=True):
        st.markdown("**⚠️ 집중 점검 필요**")
        st.dataframe(leaders, hide_index=True, column_config={"불합격률 (%)": st.column_config.NumberColumn(format="%.1f%%")})
    with st.expander("전체 라인의 검사 건수와 불합격률 비교"):
        st.dataframe(summary, hide_index=True, column_config={"불합격률 (%)": st.column_config.NumberColumn(format="%.1f%%")})


def show_process_comparison(data):
    st.subheader("🔬 합격 vs 불합격 공정 비교")
    columns = [column for column in PROCESS_COLUMNS if column in data]
    if "판정" not in data or not columns or data.empty:
        st.info("비교할 판정 또는 공정 수치 데이터가 없습니다.")
        return
    comparison = data.groupby("판정")[columns].mean().reindex(["합격", "불합격"]).T
    comparison.columns = ["합격 평균", "불합격 평균"]
    comparison.index.name = "항목"
    st.dataframe(comparison.reset_index(), hide_index=True, column_config={
        name: st.column_config.NumberColumn(format="%.2f") for name in comparison.columns
    })
    st.caption("현재 필터 기준 · 각 항목의 결측값은 제외 · 해당 판정 데이터가 없으면 평균은 비어 있습니다.")


def display_table(data):
    display = data.copy()
    if "검사일" in display:
        display["검사일"] = display["검사일"].dt.strftime("%Y-%m-%d")
    return display


def show_particle_table(data):
    st.subheader("⚠️ 파티클 집중 확인")
    if "파티클수" not in data or not data["파티클수"].notna().any():
        st.info("확인할 파티클수 데이터가 없습니다.")
        return
    top = data.dropna(subset=["파티클수"]).sort_values("파티클수", ascending=False, kind="stable").head(10)
    columns = [column for column in ["웨이퍼ID", "라인", "검사일", "파티클수", "판정"] if column in top]
    st.caption("현재 필터 내 파티클수 상위 10건 · 높은 수치는 우선 확인 대상이며 불합격을 뜻하지는 않습니다.")
    st.dataframe(display_table(top[columns]), hide_index=True)


def show_data_table(data):
    st.subheader("📋 검사 데이터")
    st.write(f"현재 표시 데이터: {len(data):,}건")
    display = display_table(data)
    with st.expander("전체 검사 데이터 보기"):
        st.dataframe(display, hide_index=True, height=400)
    st.download_button("필터 결과 CSV 다운로드", display.to_csv(index=False).encode("utf-8-sig"),
                       file_name="달빛팹_필터결과.csv", mime="text/csv", disabled=data.empty)


def main():
    configure_page()
    st.sidebar.header("📁 데이터 불러오기")
    uploaded_file = st.sidebar.file_uploader(
        "새 CSV 불러오기",
        type=["csv"],
        help="파일을 선택하지 않으면 ZIP에 포함된 기본 검사 데이터를 사용합니다.",
    )
    st.sidebar.caption("새 파일을 선택하면 기본 CSV 대신 즉시 분석합니다.")

    raw, source_name = load_data(uploaded_file)
    if raw is None:
        st.stop()
    data, messages = prepare_data(map_columns(raw))
    st.success(f"✅ 데이터 연결 완료: {source_name}")
    st.caption(f"원본 검사 {len(data):,}건 · 필터를 바꾸면 지표와 차트가 자동 계산됩니다.")
    if messages:
        with st.expander("데이터 확인 안내", expanded=True):
            for message in messages:
                st.warning(message)
    if data.empty:
        st.info("CSV에 열 이름은 있지만 검사 기록이 없습니다.")
    line, result, target, minimum = show_filters(data)
    filtered = apply_filters(data, line, result, minimum)
    if filtered.empty and not data.empty:
        st.warning("필터 조건에 맞는 데이터가 없습니다. 라인·판정을 전체로 바꾸거나 최소 파티클수를 낮춰 주세요.")
    show_metrics(filtered, target)
    show_charts(filtered)
    st.divider()
    show_detective_report(data)
    st.divider()
    show_process_comparison(filtered)
    show_particle_table(filtered)
    show_data_table(filtered)


if __name__ == "__main__":
    main()
