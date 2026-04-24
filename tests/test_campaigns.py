from decimal import Decimal

from scraper.utils.campaigns import classify_campaign_message, is_campaign_line, is_meaningful_campaign_message


def test_classify_campaign_message_detects_basket_discount() -> None:
    result = classify_campaign_message("Sepette %10 ekstra indirim")
    assert result["promotion_type"] == "basket_discount"
    assert result["discount_value"] == Decimal("10")
    assert result["campaign_scope"] == "basket"


def test_classify_campaign_message_detects_rate_discount() -> None:
    result = classify_campaign_message("%35'e varan indirim")
    assert result["promotion_type"] == "rate_discount"
    assert result["discount_value"] == Decimal("35")
    assert result["discount_unit"] == "percent"


def test_classify_campaign_message_detects_installment() -> None:
    result = classify_campaign_message("12 taksit faizsiz alisveris")
    assert result["promotion_type"] == "installment"
    assert result["installment_months"] == 12


def test_is_campaign_line_filters_non_campaign_text() -> None:
    assert is_campaign_line("Sepette %10 indirim")
    assert not is_campaign_line("Yemek odasi urun listesi")


def test_is_meaningful_campaign_message_filters_generic_labels() -> None:
    assert not is_meaningful_campaign_message("Kampanyalar", "generic_campaign")
    assert not is_meaningful_campaign_message("Bellona kampanya sayfasi", "campaign_page")
    assert is_meaningful_campaign_message("Pesin fiyatina 12 ay taksit firsati", "installment")
    assert is_meaningful_campaign_message("Yeni Yil Kampanyasi", "generic_campaign")
    assert is_meaningful_campaign_message("Kasim Indirimleri", "generic_campaign")
