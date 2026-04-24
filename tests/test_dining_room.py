from scraper.utils.dining_room import classify_product, clean_product_name, derive_team_name, infer_item_type, is_team_row


def test_infer_item_type_for_team_components() -> None:
    assert infer_item_type("Angelic Konsol") == "Konsol"
    assert infer_item_type("Angelic Sabit Masa") == "Sabit Masa"
    assert infer_item_type("Angelic Acilir Masa") == "Acilir Masa"
    assert infer_item_type("Angelic Bench Puf") == "Bench / Puf"


def test_team_rows_are_detected() -> None:
    assert is_team_row("Angelic Yemek Odasi Takimi") is True
    assert classify_product("Angelic Yemek Odasi Takimi")["is_team_row"] is True


def test_derive_team_name_prefers_collection_name() -> None:
    assert derive_team_name("Angelic Acilir Masa") == "Angelic"
    assert derive_team_name("Rozy Bohem Yemek Odasi Takimi") == "Rozy Bohem"
    assert derive_team_name("MARLIN Açılır Yemek Masası") == "MARLIN"
    assert derive_team_name("KALIA Ayakucu Puf - Bank") == "KALIA"
    assert derive_team_name("Arte Sandalye 6135 2 li") == "Arte"
    assert derive_team_name("Boheems Açılır Alternatif Yemek Masası") == "Boheems"
    assert derive_team_name("Destina Aynası") == "Destina"


def test_classify_product_cleans_card_text_and_detects_team_row() -> None:
    dirty_name = (
        "MARLIN\nYemek Odası Takımı\n31.098,00 TL\n27.988,20 TL\n"
        "Sepette %10 İndirim + Her 89.900 TL'lik Alışverişte 5.000 TL İndirim"
    )
    assert clean_product_name(dirty_name) == "MARLIN Yemek Odası Takımı"
    payload = classify_product(dirty_name)
    assert payload["item_type"] == "Yemek Odasi"
    assert payload["is_team_row"] is True
    assert payload["team_name"] == "MARLIN"
