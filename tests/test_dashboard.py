"""실제 CSV와 분리된 검증용 데이터. 실행: python -m unittest discover -s tests -v"""

import importlib
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
dashboard = importlib.import_module("대시보드")

SAMPLE = {
    "웨이퍼ID": ["001", "002", "003", "004", "005", "006"],
    "검사일": ["2026-09-22", "2026-09-21", "잘못된 날짜", "2026-09-21", None, "2026-09-22"],
    "라인": ["1라인", "2라인", "2라인", "1라인", "3라인", "3라인"],
    "판정": ["합격", "불합격", "불합격", "합격", "합격", "합격"],
    "파티클수": ["1", "100", "200", None, "3", "4"],
    "챔버온도": ["100", "200", "300", "잘못된 숫자", "120", "130"],
}


def run_with_sample(rows):
    import importlib
    from unittest.mock import patch
    import pandas as pd

    module = importlib.import_module("대시보드")
    with patch.object(module, "load_data", return_value=(pd.DataFrame(rows, dtype="string"), module.BASE_DIR / "검증용.csv")):
        module.main()


class DashboardTests(unittest.TestCase):
    def app(self, rows):
        app = AppTest.from_function(run_with_sample, args=(rows,), default_timeout=20).run()
        self.assertFalse(app.exception, str(app.exception))
        return app

    def test_missing_file(self):
        with patch.object(Path, "iterdir", return_value=iter([])):
            app = AppTest.from_file(str(dashboard.BASE_DIR / "대시보드.py"), default_timeout=20).run()
        self.assertFalse(app.exception)
        self.assertIn("CSV 파일을 찾을 수 없습니다", app.error[0].value)

    def test_statistics_charts_filters_and_report(self):
        app = self.app(SAMPLE)
        self.assertEqual([m.value for m in app.metric], ["6건", "4건", "2건", "66.7%"])
        self.assertEqual(len(app.get("vega_lite_chart")), 3)
        report = next(w.value for w in app.warning if "관리자에게 보고" in w.value)
        self.assertIn("2라인", report)
        self.assertIn("2건", report)
        controls = {item.label: item for item in app.sidebar.selectbox}
        controls["라인 선택"].select("2라인")
        controls["판정 필터"].select("불합격")
        next(s for s in app.sidebar.slider if s.label == "최소 파티클수").set_value(150)
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual([m.value for m in app.metric], ["1건", "0건", "1건", "0.0%"])
        self.assertIn(report, [w.value for w in app.warning])
        controls = {item.label: item for item in app.sidebar.selectbox}
        controls["판정 필터"].select("합격")
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "0건")
        self.assertIn("목표 판정 불가", [s.value for s in app.subheader])

    def test_target_changes(self):
        rows = {"라인": ["A"] * 20, "판정": ["합격"] * 19 + ["불합격"]}
        app = self.app(rows)
        self.assertIn("✅ 목표 달성", [s.value for s in app.subheader])
        next(s for s in app.sidebar.slider if s.label == "목표 합격률 (%)").set_value(96)
        app.run()
        self.assertFalse(app.exception)
        self.assertIn("⚠️ 목표 미달", [s.value for s in app.subheader])

    def test_empty_missing_and_invalid_columns(self):
        for rows in ({"ライン": []}, {"웨이퍼ID": ["001"]},
                     {"판정": [None, "미확인"], "라인": [None, None], "파티클수": ["NaN", "inf"], "검사일": ["오류", None]},
                     {"판정": ["합격"], "라인": ["A"], "파티클수": ["3"]}):
            with self.subTest(rows=rows):
                self.app(rows)

    def test_math_ties_and_export(self):
        data, messages = dashboard.prepare_data(pd.DataFrame(SAMPLE, dtype="string"))
        self.assertTrue(messages)
        self.assertEqual(len(dashboard.apply_filters(data, None, "전체", None)), 6)
        self.assertEqual(len(dashboard.apply_filters(data, "2라인", "불합격", 150)), 1)
        summary = dashboard.line_summary(data)
        self.assertEqual(summary.iloc[0]["라인"], "2라인")
        self.assertEqual(summary.iloc[0]["불합격률 (%)"], 100)
        export = dashboard.display_table(data).to_csv(index=False).encode("utf-8-sig")
        self.assertTrue(export.startswith(b"\xef\xbb\xbf"))
        self.assertIn("001", export.decode("utf-8-sig"))
        app = self.app({"라인": ["A", "B"], "판정": ["불합격", "불합격"]})
        report = next(w.value for w in app.warning if "관리자에게 보고" in w.value)
        self.assertIn("A, B", report)


if __name__ == "__main__":
    unittest.main()
