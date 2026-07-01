import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


def _stock_row(**overrides):
    row = {
        "material_index": "895-26-452-09",
        "warehouse": "Glasshouse",
        "material_type": "Komponenty",
        "receipt_date": pd.Timestamp("2024-01-15"),
        "stock_value": 100.0,
        "material_name": "10 NOWAX, OEM",
        "rodzaj_indeksu": None,
        "type_of_materials": None,
        "aging_bucket": None,
    }
    row.update(overrides)
    return pd.DataFrame([row])


BASE = Path(__file__).parent.parent


class TestReadStockFile:
    def test_returns_standard_columns(self):
        from import_stock import read_stock_file
        path = BASE / "material_stat_daystock (63).xlsx"
        if not path.exists():
            pytest.skip("Sample file not present")
        df = read_stock_file(path)
        for col in ("material_index", "warehouse", "material_type", "receipt_date", "stock_value"):
            assert col in df.columns, f"Missing column: {col}"

    def test_no_repeated_header_row(self):
        from import_stock import read_stock_file
        path = BASE / "material_stat_daystock (63).xlsx"
        if not path.exists():
            pytest.skip("Sample file not present")
        df = read_stock_file(path)
        assert df.iloc[0]["material_index"] != "Index materiałowy"

    def test_row_count_komponenty(self):
        from import_stock import read_stock_file
        path = BASE / "material_stat_daystock (63).xlsx"
        if not path.exists():
            pytest.skip("Sample file not present")
        df = read_stock_file(path)
        assert len(df) == 506

    def test_row_count_magazynowy(self):
        from import_stock import read_stock_file
        path = BASE / "material_stat_daystock (64).xlsx"
        if not path.exists():
            pytest.skip("Sample file not present")
        df = read_stock_file(path)
        assert len(df) == 1921

    def test_stock_value_is_numeric(self):
        from import_stock import read_stock_file
        path = BASE / "material_stat_daystock (63).xlsx"
        if not path.exists():
            pytest.skip("Sample file not present")
        df = read_stock_file(path)
        assert pd.api.types.is_numeric_dtype(df["stock_value"])


class TestMergeStockFiles:
    def test_concat_two_frames(self):
        from import_stock import merge_stock_files
        df1 = _stock_row(material_type="Komponenty")
        df2 = _stock_row(material_type="Magazynowy / Stock")
        merged = merge_stock_files(df1, df2)
        assert len(merged) == 2
        assert set(merged["material_type"]) == {"Komponenty", "Magazynowy / Stock"}

    def test_index_reset(self):
        from import_stock import merge_stock_files
        merged = merge_stock_files(_stock_row(), _stock_row())
        assert list(merged.index) == [0, 1]


class TestApplyMapping:
    def test_mapp1_column_b_indexes_are_prowax(self):
        from import_stock import apply_mapping
        mapp1 = pd.DataFrame({0: [None, None], 1: ["Row Labels", "895-26-452-09"]})
        mapp2 = pd.DataFrame({
            "Type of materials": ["RW"],
            "Magazyn": ["Glasshouse"],
            "Typ surowca": ["Komponenty"],
        })
        result = apply_mapping(_stock_row(), mapp1, mapp2)
        assert result.iloc[0]["rodzaj_indeksu"] == "PROWAX"

    def test_index_missing_from_mapp1_is_non_prowax(self):
        from import_stock import apply_mapping
        mapp1 = pd.DataFrame({"prowax_index": ["OTHER"]})
        mapp2 = pd.DataFrame({
            "Type of materials": ["RW"],
            "Magazyn": ["Glasshouse"],
            "Typ surowca": ["Komponenty"],
        })
        result = apply_mapping(_stock_row(), mapp1, mapp2)
        assert result.iloc[0]["rodzaj_indeksu"] == "NON PROWAX"

    def test_mapp2_type_x_is_unmapped(self):
        from import_stock import apply_mapping, calculate_reserves
        mapp1 = pd.DataFrame({"prowax_index": ["895-26-452-09"]})
        mapp2 = pd.DataFrame({
            "Type of materials": ["x"],
            "Magazyn": ["Glasshouse"],
            "Typ surowca": ["Komponenty"],
        })
        df = apply_mapping(_stock_row(), mapp1, mapp2)
        df["aging_bucket"] = "pow 12 mcy"
        result = calculate_reserves(df)
        assert result.iloc[0]["type_of_materials"] == "UNMAPPED"
        assert result.iloc[0]["reserve_amount"] == 0.0


class TestCalculateAging:
    @pytest.mark.parametrize("receipt,bucket", [
        ("2026-05-01", "0-3 mcy"),
        ("2026-01-01", "3-6 mcy"),
        ("2025-10-01", "6-9 mcy"),
        ("2025-07-01", "9-12 mcy"),
        ("2024-01-01", "pow 12 mcy"),
    ])
    def test_bucket_assignment(self, receipt, bucket):
        from import_stock import calculate_aging
        df = _stock_row(receipt_date=pd.Timestamp(receipt))
        result = calculate_aging(df, date(2026, 6, 27))
        assert result.iloc[0]["aging_bucket"] == bucket

    def test_invalid_date_gets_blad_daty(self):
        from import_stock import calculate_aging
        df = _stock_row(receipt_date=pd.NaT)
        result = calculate_aging(df, date(2026, 6, 27))
        assert result.iloc[0]["aging_bucket"] == "błąd daty"

    def test_string_date_is_parsed(self):
        from import_stock import calculate_aging
        df = _stock_row(receipt_date="2026-05-01")
        result = calculate_aging(df, date(2026, 6, 27))
        assert result.iloc[0]["aging_bucket"] == "0-3 mcy"

    def test_blad_daty_gets_zero(self):
        from import_stock import calculate_reserves
        df = _stock_row(type_of_materials="WIP", stock_value=100.0)
        df["aging_bucket"] = "błąd daty"
        result = calculate_reserves(df)
        assert result.iloc[0]["reserve_pct"] == 0.0
        assert result.iloc[0]["reserve_amount"] == 0.0


class TestCalculateReserves:
    @pytest.mark.parametrize("mat_type,bucket,expected_pct", [
        ("RW",      "0-3 mcy",    0.0),
        ("RW",      "9-12 mcy",   0.5),
        ("RW",      "pow 12 mcy", 1.0),
        ("WIP",     "3-6 mcy",    0.5),
        ("WIP",     "6-9 mcy",    1.0),
        ("FG",      "3-6 mcy",    0.0),
        ("FG",      "6-9 mcy",    1.0),
        ("UNMAPPED","pow 12 mcy", 0.0),
    ])
    def test_reserve_pct(self, mat_type, bucket, expected_pct):
        from import_stock import calculate_reserves
        df = _stock_row(type_of_materials=mat_type, stock_value=200.0)
        df["aging_bucket"] = bucket
        result = calculate_reserves(df)
        assert result.iloc[0]["reserve_pct"] == expected_pct

    def test_reserve_amount_is_value_times_pct(self):
        from import_stock import calculate_reserves
        df = _stock_row(type_of_materials="RW", stock_value=200.0)
        df["aging_bucket"] = "pow 12 mcy"
        result = calculate_reserves(df)
        assert result.iloc[0]["reserve_amount"] == pytest.approx(200.0)

    def test_blad_daty_gets_zero(self):
        from import_stock import calculate_reserves
        df = _stock_row(type_of_materials="WIP", stock_value=100.0)
        df["aging_bucket"] = "błąd daty"
        result = calculate_reserves(df)
        assert result.iloc[0]["reserve_pct"] == 0.0
        assert result.iloc[0]["reserve_amount"] == 0.0
