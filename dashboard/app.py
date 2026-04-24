from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.data_loader import (
    load_executive_summary,
    load_latest_report_metadata,
    load_price_trend,
    load_visual_product_comparison,
)

try:
    from scraper.utils.campaigns import is_meaningful_campaign_message
except ModuleNotFoundError:
    _BANNED_EXACT_MESSAGES = {
        "kampanyalar",
        "kampanya sayfasi",
        "bellona kampanya sayfasi",
        "istikbal kampanya sayfasi",
        "dogtas kampanya sayfasi",
    }
    _BANNED_PARTIAL_MESSAGES = (
        "e-posta adresinizi girerek",
        "en yeni ürünler, kampanyalar ve avantajlardan haberdar olun",
        "en yeni urunler, kampanyalar ve avantajlardan haberdar olun",
    )

    def is_meaningful_campaign_message(message: str | None, promotion_type: str | None = None) -> bool:
        normalized = " ".join(str(message or "").split()).strip()
        lowered = normalized.casefold()
        if not normalized:
            return False
        if lowered in _BANNED_EXACT_MESSAGES:
            return False
        if any(partial in lowered for partial in _BANNED_PARTIAL_MESSAGES):
            return False
        if promotion_type in {"basket_discount", "rate_discount", "amount_discount", "installment", "financing"}:
            return True
        if any(token in lowered for token in ("%", "taksit", "sepette", "faizsiz", "vade", "tl", "fonu")):
            return True
        if lowered.endswith("kampanyası") or lowered.endswith("kampanyasi"):
            return False
        return len(normalized.split()) >= 5


def _safe_streamlit_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    safe_frame = frame.copy()
    for column in safe_frame.columns:
        if safe_frame[column].dtype == "object":
            safe_frame[column] = safe_frame[column].where(safe_frame[column].notna(), "").astype(str)
    return safe_frame


def _display_price_value(row: pd.Series) -> object:
    latest_price = row.get("latest_price")
    current_price = row.get("current_price")
    original_price = row.get("original_price")
    if pd.notna(latest_price) and pd.notna(original_price):
        return min(latest_price, original_price)
    if pd.notna(latest_price):
        return latest_price
    if pd.notna(current_price) and pd.notna(original_price):
        return min(current_price, original_price)
    if pd.notna(current_price):
        return current_price
    return None


def _list_price_value(row: pd.Series) -> object:
    latest_price = row.get("latest_price")
    current_price = row.get("current_price")
    original_price = row.get("original_price")
    if pd.notna(latest_price) and pd.notna(original_price):
        return max(latest_price, original_price)
    if pd.notna(original_price):
        return original_price
    if pd.notna(latest_price):
        return latest_price
    return current_price


def _format_price(value: object) -> str:
    if value is None or pd.isna(value):
        return "Veri yok"
    return f"{float(value):,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")


st.set_page_config(
    page_title="Urun Bazli Rakip Analiz Sistemi",
    layout="wide",
)

logo_col, title_col = st.columns([1, 5])
with logo_col:
    st.image("dashboard/assets/yatas_grup_logo.jpg", use_container_width=True)
with title_col:
    st.title("Urun Bazli Rakip Analiz Sistemi")
    st.caption("Executive Summary, resimli urun karsilastirma ve haftalik rapor paneli")

summary = load_executive_summary()
report_metadata = load_latest_report_metadata()

if not summary:
    st.warning("Executive summary henuz uretilmedi. Once daily scrape ve summary adimini calistirin.")
    st.stop()

overview = summary.get("overview", {})
price_summary = summary.get("price_summary", {})
promotion_summary = summary.get("promotion_summary", {})
ai_insights = summary.get("ai_insights", {})
visual_df = load_visual_product_comparison()

metric_1, metric_2, metric_3, metric_4 = st.columns(4)
metric_1.metric("Izlenen Rakip", str(overview.get("competitor_count", 0)))
metric_2.metric("Toplam Urun", str(overview.get("product_count", 0)))
metric_3.metric("Haftalik Kampanya", str(overview.get("weekly_promotion_count", 0)))
metric_4.metric("Stokta Yok", str(overview.get("out_of_stock_count", 0)))

tab_summary, tab_visual, tab_reports = st.tabs(
    ["Executive Summary", "Resimli Karsilastirma", "Haftalik Raporlar"]
)

with tab_summary:
    st.subheader("Gunluk Fiyat Ozetleri")
    top_discount_brand = price_summary.get("top_discount_brand") or "Veri yok"
    st.write(f"En fazla fiyat indiren marka: **{top_discount_brand}**")
    strategic_alerts = [
        f"En agresif fiyatlama hareketi: {top_discount_brand}",
        f"Haftalik kampanya adedi: {overview.get('weekly_promotion_count', 0)}",
        f"Stok riski tasiyan urun adedi: {overview.get('out_of_stock_count', 0)}",
    ]
    if promotion_summary.get("top_campaign_type"):
        strategic_alerts.append(f"En yaygin kampanya tipi: {promotion_summary.get('top_campaign_type')}")
    st.markdown("\n".join(f"- {item}" for item in strategic_alerts))
    promotion_brands = promotion_summary.get("brands", [])
    top_campaign_brand = promotion_brands[0]["competitor_name"] if promotion_brands else "Veri yok"
    total_installment = sum(int(row.get("installment_count", 0) or 0) for row in promotion_brands)
    total_basket_discount = sum(int(row.get("basket_discount_count", 0) or 0) for row in promotion_brands)
    total_rate_discount = sum(int(row.get("rate_discount_count", 0) or 0) for row in promotion_brands)
    metrics_frame = pd.DataFrame(
        [
            {"Metrik": "Fiyat Degisimi Gozlenen Urun", "Deger": price_summary.get("changed_product_count", 0)},
            {"Metrik": "Haftalik Kampanya Mesaji", "Deger": overview.get("weekly_promotion_count", 0)},
            {"Metrik": "Sepette Indirim Mesaji", "Deger": total_basket_discount},
            {"Metrik": "Taksit Kampanyasi", "Deger": total_installment},
            {"Metrik": "Oran Bazli Indirim", "Deger": total_rate_discount},
            {"Metrik": "Kampanyada One Cikan Marka", "Deger": top_campaign_brand},
        ]
    )
    st.dataframe(metrics_frame, use_container_width=True, hide_index=True)

    latest_changes = pd.DataFrame(summary.get("latest_price_changes", []))
    if not latest_changes.empty:
        latest_changes = latest_changes.rename(
            columns={
                "competitor_name": "Marka",
                "product_name": "Urun",
                "current_price": "Guncel Fiyat",
                "previous_price": "Onceki Fiyat",
                "price_change": "Degisim",
            }
        )
        st.dataframe(
            latest_changes[["Marka", "Urun", "Guncel Fiyat", "Onceki Fiyat", "Degisim"]],
            use_container_width=True,
        )
    else:
        st.caption("Son ozette fiyat degisimi kaydi bulunmadi; tablo kampanya ve genel rekabet metrikleriyle dolduruldu.")

    if ai_insights:
        st.subheader("AI Icgoruler")
        insight_cols = st.columns(2)
        with insight_cols[0]:
            st.write(f"Kaynak: **{ai_insights.get('generated_by', 'heuristic')}**")
            if ai_insights.get("campaign_insight"):
                st.markdown(f"**Kampanya:** {ai_insights['campaign_insight']}")
            if ai_insights.get("launch_delist_insight"):
                st.markdown(f"**Launch / Delist:** {ai_insights['launch_delist_insight']}")
        with insight_cols[1]:
            if ai_insights.get("pricing_insight"):
                st.markdown(f"**Fiyat:** {ai_insights['pricing_insight']}")
            if ai_insights.get("strategic_summary"):
                st.markdown(f"**Stratejik Ozet:** {ai_insights['strategic_summary']}")
        actions = ai_insights.get("recommended_actions") or []
        if actions:
            st.caption("Onerilen aksiyonlar")
            st.markdown("\n".join(f"- {item}" for item in actions))

    st.subheader("Fiyat Trendi")
    trend_window = st.selectbox("Trend periyodu", [30, 90, 180], index=0, format_func=lambda value: f"{value} gun")
    trend_df = load_price_trend(limit_days=trend_window)
    if trend_df.empty:
        st.info("Trend grafigi icin yeterli fiyat gecmisi henuz olusmadi.")
    else:
        trend_df["etiket"] = trend_df["competitor_name"] + " | " + trend_df["product_name"]
        figure = px.line(
            trend_df,
            x="captured_date",
            y="price",
            color="etiket",
            title=f"Son {trend_window} Gun Fiyat Gecmisi",
        )
        figure.update_layout(height=520, legend_title_text="Marka | Urun")
        st.plotly_chart(figure, use_container_width=True)

    promotion_df = pd.DataFrame(promotion_summary.get("brands", []))
    stock_df = pd.DataFrame(summary.get("stock_summary", []))
    promo_col, stock_col = st.columns(2)

    with promo_col:
        st.subheader("Kampanya Yogunlugu")
        if promotion_df.empty:
            st.write("Son 7 gunde kampanya verisi yok.")
        else:
            promotion_df = promotion_df.rename(
                columns={
                    "competitor_name": "Marka",
                    "promotion_count": "Kampanya Adedi",
                    "basket_discount_count": "Sepette Indirim",
                    "rate_discount_count": "Oran Bazli Indirim",
                    "installment_count": "Taksit",
                    "amount_discount_count": "TL Indirim",
                    "sample_message": "Ornek Mesaj",
                }
            )
            st.dataframe(
                promotion_df[
                    ["Marka", "Kampanya Adedi", "Sepette Indirim", "Oran Bazli Indirim", "Taksit", "TL Indirim", "Ornek Mesaj"]
                ],
                use_container_width=True,
                hide_index=True,
            )
            sample_messages = promotion_summary.get("sample_messages", [])
            if sample_messages:
                st.caption("Ornek kampanya mesajlari")
                st.markdown("\n".join(f"- {item}" for item in sample_messages))

            promotion_details = pd.DataFrame(summary.get("latest_promotions", []))
            st.subheader("Marka Bazli Kampanya Detaylari")
            grouped_messages: dict[str, list[str]] = {}
            if not promotion_details.empty:
                for _, row in promotion_details.iterrows():
                    brand = str(row.get("competitor_name") or "")
                    promotion_type = str(row.get("promotion_type") or "")
                    message = str(row.get("promotion_message") or row.get("title") or "").strip()
                    if not brand or not is_meaningful_campaign_message(message, promotion_type):
                        continue
                    grouped_messages.setdefault(brand, [])
                    if message not in grouped_messages[brand]:
                        grouped_messages[brand].append(message)
            for brand in ["dogtas", "bellona", "istikbal"]:
                messages = grouped_messages.get(brand, [])
                if messages:
                    joined_messages = "; ".join(messages[:4])
                    st.markdown(f"**{brand.upper()}**: {joined_messages}")
                else:
                    st.markdown(f"**{brand.upper()}**: Anlamli kampanya detayi yakalanamadi.")

    with stock_col:
        st.subheader("Stok Riski")
        if stock_df.empty:
            st.write("Stokta olmayan urun gorunmuyor.")
        else:
            stock_df = stock_df.rename(
                columns={"competitor_name": "Marka", "out_of_stock_count": "Stokta Yok"}
            )
            st.dataframe(stock_df, use_container_width=True, hide_index=True)

with tab_visual:
    st.subheader("Resimli Yemek Odasi Karsilastirma")
    if visual_df.empty:
        st.info("Resimli karsilastirma icin veri henuz olusmadi.")
    else:
        visual_df = visual_df.copy()
        visual_df["image_url"] = visual_df["image_url"].fillna("")
        visual_df["team_name"] = visual_df["team_name"].fillna("Bilinmiyor")
        visual_df["item_type"] = visual_df["item_type"].fillna("")
        visual_df["etiket"] = visual_df["competitor_name"].astype(str) + " | " + visual_df["product_name"].astype(str)
        visual_df["gosterim_fiyati"] = visual_df.apply(_display_price_value, axis=1)
        visual_df["liste_fiyati"] = visual_df.apply(_list_price_value, axis=1)

        available_teams = sorted(team for team in visual_df["team_name"].unique().tolist() if team)
        selected_team = st.selectbox("Takim filtresi", ["Tum Takimlar", *available_teams], index=0)
        filtered_visual_df = visual_df if selected_team == "Tum Takimlar" else visual_df.loc[visual_df["team_name"] == selected_team]

        compare_options = filtered_visual_df["etiket"].tolist() or visual_df["etiket"].tolist()
        left_visual = st.selectbox("Birinci gorsel urun", compare_options, index=0)
        right_visual = st.selectbox("Ikinci gorsel urun", compare_options, index=1 if len(compare_options) > 1 else 0)

        left_visual_row = visual_df.loc[visual_df["etiket"] == left_visual].iloc[0]
        right_visual_row = visual_df.loc[visual_df["etiket"] == right_visual].iloc[0]

        visual_cols = st.columns(2)
        for column, row in ((visual_cols[0], left_visual_row), (visual_cols[1], right_visual_row)):
            with column:
                st.markdown(f"**{row['competitor_name'].upper()} | {row['product_name']}**")
                if row["image_url"]:
                    st.image(row["image_url"], use_container_width=True)
                else:
                    st.caption("Bu urun icin gorsel henuz yok. Yeni scrape sonrasi dolacak.")
                st.write(f"Takim: {row['team_name']}")
                st.write(f"Urun Cesidi: {row['item_type'] or 'Veri yok'}")
                st.write(f"Guncel Fiyat: {_format_price(row['gosterim_fiyati'])}")
                st.write(f"Liste Fiyat: {_format_price(row['liste_fiyati'])}")
                if row["product_url"]:
                    st.link_button("Urun Sayfasi", str(row["product_url"]))

        gallery_df = filtered_visual_df.loc[
            filtered_visual_df["item_type"].isin(["Yemek Odasi", "Konsol", "Sabit Masa", "Acilir Masa", "Sandalye", "Bench / Puf", "Vitrin"])
        ].copy()
        gallery_df = gallery_df.loc[gallery_df["image_url"].astype(str).str.len() > 0]
        if gallery_df.empty:
            st.info("Secili filtrede gorsel galerisi icin uygun veri yok.")
        else:
            st.subheader("Resimli Galeri")
            for start in range(0, len(gallery_df), 3):
                row_cols = st.columns(3)
                for column, (_, item) in zip(row_cols, gallery_df.iloc[start:start + 3].iterrows()):
                    with column:
                        st.image(item["image_url"], use_container_width=True)
                        st.caption(
                            f"{item['competitor_name'].upper()} | {item['product_name']} | {_format_price(item['gosterim_fiyati'])}"
                        )

with tab_reports:
    st.subheader("Haftalik Rapor Merkezi")
    email_status = report_metadata.get("email_delivery", {}).get("status")
    if not report_metadata:
        st.info("Henuz rapor uretilmedi. `python -m scraper.pipeline report` veya Airflow weekly reporting DAG'ini calistirin.")
    else:
        st.caption(f"Son rapor tarihi: {report_metadata.get('generated_at', '-')}")
        if email_status == "sent":
            st.success("Haftalik rapor e-posta ile gonderildi.")
        elif email_status == "skipped":
            st.warning("Rapor uretildi ancak SMTP ayarlari eksik oldugu icin e-posta gonderimi atlandi.")
        elif email_status == "failed":
            st.error("Rapor uretildi fakat e-posta gonderimi basarisiz oldu.")
        else:
            st.info("Rapor artefaktlari olusturuldu.")

        notes = report_metadata.get("management_summary", [])
        if notes:
            st.markdown("\n".join(f"- {note}" for note in notes))

        file_cols = st.columns(2)
        files = report_metadata.get("files", {})
        for column, key, label in (
            (file_cols[0], "pdf", "PDF Rapor"),
            (file_cols[1], "excel", "Excel Rapor"),
        ):
            file_info = files.get(key)
            if not file_info:
                continue
            path = Path(file_info["path"])
            with column:
                st.write(label)
                if path.exists():
                    st.download_button(
                        label=f"{label} indir",
                        data=path.read_bytes(),
                        file_name=path.name,
                        mime="application/octet-stream",
                    )
                else:
                    st.write("Dosya bulunamadi.")
