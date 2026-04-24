from analysis.reporting import (
    _choose_team_name,
    _build_panel_frame,
    _price_pair,
    _sum_series,
    _resolve_override,
    build_match_key,
    build_management_summary,
    derive_collection_name,
    flatten_catalog_diff_rows,
    infer_product_type,
    parse_email_recipients,
)
import pandas as pd


def test_parse_email_recipients_supports_comma_and_semicolon() -> None:
    recipients = parse_email_recipients("a@example.com; b@example.com, c@example.com")
    assert recipients == ["a@example.com", "b@example.com", "c@example.com"]


def test_flatten_catalog_diff_rows_builds_brand_rows() -> None:
    summary = {
        "catalog_diff_summary": {
            "brands": {
                "bellona": {
                    "status": "ok",
                    "summary": {
                        "previous_count": 10,
                        "current_count": 12,
                        "new_count": 3,
                        "removed_count": 1,
                        "unchanged_count": 8,
                    },
                }
            }
        }
    }

    rows = flatten_catalog_diff_rows(summary)

    assert rows == [
        {
            "Marka": "bellona",
            "Durum": "ok",
            "Onceki Katalog": 10,
            "Guncel Katalog": 12,
            "Yeni Urun": 3,
            "Kalkan Urun": 1,
            "Sabit Kalan": 8,
        }
    ]


def test_build_management_summary_contains_actionable_headlines() -> None:
    summary = {
        "overview": {
            "competitor_count": 3,
            "product_count": 250,
            "weekly_promotion_count": 6,
            "out_of_stock_count": 4,
        },
        "price_summary": {
            "top_discount_brand": "istikbal",
            "price_decreased_count": 12,
            "price_increased_count": 5,
        },
        "promotion_summary": {
            "brands": [
                {
                    "competitor_name": "bellona",
                    "promotion_count": 4,
                    "basket_discount_count": 2,
                }
            ]
        },
        "catalog_diff_summary": {
            "brands": {
                "istikbal": {"summary": {"new_count": 2, "removed_count": 1}},
                "bellona": {"summary": {"new_count": 1, "removed_count": 0}},
            }
        },
    }

    result = build_management_summary(summary)

    assert len(result) == 5
    assert "sepette 2" in result[2]
    assert "istikbal" in result[3]
    assert "3 yeni" in result[4]


def test_infer_product_type_handles_common_furniture_labels() -> None:
    assert infer_product_type("Legato Acilir Masa") == "Acilir Masa"
    assert infer_product_type("Angelic Konsol") == "Konsol"
    assert infer_product_type("Mayer Bench Puf") == "Bench / Puf"


def test_derive_collection_name_removes_generic_words() -> None:
    assert derive_collection_name("Mona Yemek Masasi") == "Mona"
    assert derive_collection_name("Angelic Acilir Masa") == "Angelic"


def test_build_match_key_groups_similar_products() -> None:
    assert build_match_key("Mona Acilir Yemek Masasi", "Acilir Masa") == "mona|acilir masa"
    assert build_match_key("Mona Sabit Masa", "Sabit Masa") == "mona|sabit masa"


def test_build_panel_frame_falls_back_to_latest_team_price_when_snapshot_missing() -> None:
    base_frame = pd.DataFrame(
        [
            {
                "Marka": "BELLONA",
                "competitor_sku": "team-1",
                "Takim": "Mona",
                "Urun Cesidi": "Yemek Odasi",
                "Team Display Name": "Takim (1) Min",
                "Display Order": 7,
                "Takim Satiri": True,
                "product_url": "https://example.com/team-1",
                "Liste Fiyat": 120000.0,
                "Ind. PRK Fiyat": 93000.0,
            }
        ]
    )
    snapshot_frame = pd.DataFrame(
        columns=["competitor_sku", "snapshot_date", "price", "original_price"]
    )

    panel = _build_panel_frame(base_frame, snapshot_frame, ["13.04.2026"])

    assert panel.loc[0, "13.04.2026|Liste fiyat"] == 120000.0
    assert panel.loc[0, "13.04.2026|IND. PRK FIYAT"] == 93000.0


def test_build_panel_frame_creates_team_min_max_rows() -> None:
    base_frame = pd.DataFrame(
        [
            {
                "Marka": "DOGTAS",
                "competitor_sku": "marlin-team-min",
                "Takim": "MARLIN",
                "Urun Cesidi": "Yemek Odasi",
                "Team Display Name": "MARLIN Yemek Odasi Takimi",
                "Display Order": 7,
                "Takim Satiri": True,
                "product_url": "https://example.com/marlin-team-min",
                "Liste Fiyat": 31098.0,
                "Ind. PRK Fiyat": 27988.2,
            },
            {
                "Marka": "DOGTAS",
                "competitor_sku": "marlin-team-max",
                "Takim": "MARLIN",
                "Urun Cesidi": "Yemek Odasi",
                "Team Display Name": "MARLIN Yemek Odasi Takimi Buyuk",
                "Display Order": 7,
                "Takim Satiri": True,
                "product_url": "https://example.com/marlin-team-max",
                "Liste Fiyat": 41098.0,
                "Ind. PRK Fiyat": 36988.2,
            },
            {
                "Marka": "DOGTAS",
                "competitor_sku": "marlin-konsol",
                "Takim": "MARLIN",
                "Urun Cesidi": "Konsol",
                "Team Display Name": "MARLIN Konsol",
                "Display Order": 1,
                "Takim Satiri": False,
                "product_url": "https://example.com/marlin-konsol",
                "Liste Fiyat": 11649.88,
                "Ind. PRK Fiyat": 10484.89,
            },
        ]
    )
    snapshot_frame = pd.DataFrame(columns=["competitor_sku", "snapshot_date", "price", "original_price"])

    panel = _build_panel_frame(base_frame, snapshot_frame, ["13.04.2026"])

    assert "Takim (1) Min" in panel["Urun Adi"].tolist()
    assert "Takim (2) Max" in panel["Urun Adi"].tolist()
    min_row = panel.loc[panel["Urun Adi"] == "Takim (1) Min"].iloc[0]
    max_row = panel.loc[panel["Urun Adi"] == "Takim (2) Max"].iloc[0]
    assert min_row["13.04.2026|IND. PRK FIYAT"] == 27988.2
    assert max_row["13.04.2026|IND. PRK FIYAT"] == 36988.2


def test_build_panel_frame_creates_team_total_row_from_components() -> None:
    base_frame = pd.DataFrame(
        [
            {
                "Marka": "BELLONA",
                "competitor_sku": "mona-konsol",
                "Takim": "Mona",
                "Urun Cesidi": "Konsol",
                "Team Display Name": "Mona Konsol",
                "Display Order": 1,
                "Takim Satiri": False,
                "product_url": "https://example.com/mona-konsol",
                "Liste Fiyat": 20000.0,
                "Ind. PRK Fiyat": 18000.0,
            },
            {
                "Marka": "BELLONA",
                "competitor_sku": "mona-masa",
                "Takim": "Mona",
                "Urun Cesidi": "Acilir Masa",
                "Team Display Name": "Mona Acilir Masa",
                "Display Order": 3,
                "Takim Satiri": False,
                "product_url": "https://example.com/mona-masa",
                "Liste Fiyat": 30000.0,
                "Ind. PRK Fiyat": 27000.0,
            },
            {
                "Marka": "BELLONA",
                "competitor_sku": "mona-sandalye",
                "Takim": "Mona",
                "Urun Cesidi": "Sandalye",
                "Team Display Name": "Mona Sandalye",
                "Display Order": 4,
                "Takim Satiri": False,
                "product_url": "https://example.com/mona-sandalye",
                "Liste Fiyat": 8000.0,
                "Ind. PRK Fiyat": 7200.0,
            },
        ]
    )
    snapshot_frame = pd.DataFrame(columns=["competitor_sku", "snapshot_date", "price", "original_price"])

    panel = _build_panel_frame(base_frame, snapshot_frame, ["13.04.2026"])

    total_row = panel.loc[panel["Urun Adi"] == "Takim Toplami"].iloc[0]
    assert total_row["Marka"] == "BELLONA"
    assert total_row["Takim"] == "Mona"
    assert total_row["13.04.2026|Liste fiyat"] == 58000.0
    assert total_row["13.04.2026|IND. PRK FIYAT"] == 52200.0


def test_price_pair_handles_reversed_price_columns() -> None:
    assert _price_pair(31098.0, 27988.2) == (31098.0, 27988.2)
    assert _price_pair(27988.2, 31098.0) == (31098.0, 27988.2)


def test_sum_series_ignores_nulls_and_returns_total() -> None:
    values = pd.Series([20000.0, None, 30000.0])
    assert _sum_series(values) == 50000.0


def test_choose_team_name_prefers_canonical_prefix() -> None:
    assert _choose_team_name("MARLIN Açılır", "MARLIN") == "MARLIN"
    assert _choose_team_name("KALIA Melanj", "KALIA") == "KALIA"
    assert _choose_team_name("Rozy Bohem", "Rozy Bohem") == "Rozy Bohem"


def test_resolve_override_supports_pattern_rules() -> None:
    override_payload = {
        "sku": {},
        "pattern": [
            {"brand": "dogtas", "name_contains": "ayakucu puf - bank", "team_name": "MARLIN"},
        ],
    }
    resolved = _resolve_override(
        override_payload,
        "sku-1",
        "dogtas",
        "MARLIN Ayakucu Puf - Bank",
        "MARLIN Ayakucu",
    )
    assert resolved["team_name"] == "MARLIN"
