from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.data_loader import (
    load_executive_summary,
    load_latest_report_metadata,
    load_price_trend,
    load_product_specs,
)


st.set_page_config(
    page_title="Urun Bazli Rakip Analiz Sistemi",
    layout="wide",
)

summary = load_executive_summary()
report_metadata = load_latest_report_metadata()

st.title("Urun Bazli Rakip Analiz Sistemi")
st.caption("Executive Summary, katalog diff ve urun ozellik karsilastirma paneli")

if not summary:
    st.warning("Executive summary henuz uretilmedi. Once daily scrape ve summary adimini calistirin.")
    st.stop()

overview = summary.get("overview", {})
price_summary = summary.get("price_summary", {})
catalog_diff = summary.get("catalog_diff_summary", {}).get("brands", {})
specs_df = load_product_specs()

metric_1, metric_2, metric_3, metric_4 = st.columns(4)
metric_1.metric("Izlenen Rakip", str(overview.get("competitor_count", 0)))
metric_2.metric("Toplam Urun", str(overview.get("product_count", 0)))
metric_3.metric("Haftalik Kampanya", str(overview.get("weekly_promotion_count", 0)))
metric_4.metric("Stokta Yok", str(overview.get("out_of_stock_count", 0)))

tab_summary, tab_compare, tab_reports = st.tabs(["Executive Summary", "Urun Karsilastirma", "Haftalik Raporlar"])

with tab_summary:
    summary_col, diff_col = st.columns((3, 2))

    with summary_col:
        st.subheader("Gunluk Fiyat Ozetleri")
        top_discount_brand = price_summary.get("top_discount_brand") or "Veri yok"
        st.write(f"En fazla fiyat indiren marka: **{top_discount_brand}**")
        strategic_alerts = [
            f"En agresif fiyatlama hareketi: {top_discount_brand}",
            f"Haftalik kampanya adedi: {overview.get('weekly_promotion_count', 0)}",
            f"Stok riski tasiyan urun adedi: {overview.get('out_of_stock_count', 0)}",
        ]
        st.markdown("\n".join(f"- {item}" for item in strategic_alerts))
        price_metrics = pd.DataFrame(
            [
                {"metrik": "Artan", "adet": price_summary.get("price_increased_count", 0)},
                {"metrik": "Azalan", "adet": price_summary.get("price_decreased_count", 0)},
                {"metrik": "Degismeyen", "adet": price_summary.get("price_unchanged_count", 0)},
            ]
        )
        st.dataframe(price_metrics, use_container_width=True, hide_index=True)

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

    with diff_col:
        st.subheader("Haftalik Katalog Alarmi")
        diff_rows = []
        for brand, payload in catalog_diff.items():
            summary_block = payload.get("summary", {})
            diff_rows.append(
                {
                    "Marka": brand,
                    "Durum": payload.get("status"),
                    "Yeni Urun": summary_block.get("new_count", 0),
                    "Kalkan Urun": summary_block.get("removed_count", 0),
                }
            )
        st.dataframe(pd.DataFrame(diff_rows), use_container_width=True, hide_index=True)

        bellona_new = catalog_diff.get("bellona", {}).get("new_products", [])
        if bellona_new:
            st.info(f"Ornek yeni urun: {bellona_new[0]['product_name']}")

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

    promotion_df = pd.DataFrame(summary.get("latest_promotions", []))
    stock_df = pd.DataFrame(summary.get("stock_summary", []))
    promo_col, stock_col = st.columns(2)

    with promo_col:
        st.subheader("Kampanya Yogunlugu")
        if promotion_df.empty:
            st.write("Son 7 gunde kampanya verisi yok.")
        else:
            promotion_df = promotion_df.rename(
                columns={"competitor_name": "Marka", "promotion_count": "Kampanya Adedi"}
            )
            st.dataframe(promotion_df, use_container_width=True, hide_index=True)

    with stock_col:
        st.subheader("Stok Riski")
        if stock_df.empty:
            st.write("Stokta olmayan urun gorunmuyor.")
        else:
            stock_df = stock_df.rename(
                columns={"competitor_name": "Marka", "out_of_stock_count": "Stokta Yok"}
            )
            st.dataframe(stock_df, use_container_width=True, hide_index=True)

with tab_compare:
    st.subheader("Urun Bazli Ozellik Karsilastirma")
    if specs_df.empty:
        st.info("Karsilastirma icin product_specs verisi henuz olusmadi.")
    else:
        specs_df["etiket"] = (
            specs_df["competitor_name"].astype(str)
            + " | "
            + specs_df["product_name"].astype(str)
        )
        options = specs_df["etiket"].tolist()
        default_right = 1 if len(options) > 1 else 0
        left_label = st.selectbox("Birinci urun", options, index=0)
        right_label = st.selectbox("Ikinci urun", options, index=default_right)

        left_row = specs_df.loc[specs_df["etiket"] == left_label].iloc[0]
        right_row = specs_df.loc[specs_df["etiket"] == right_label].iloc[0]

        comparison_df = pd.DataFrame(
            [
                {"Alan": "Marka", left_label: left_row["competitor_name"], right_label: right_row["competitor_name"]},
                {"Alan": "Urun", left_label: left_row["product_name"], right_label: right_row["product_name"]},
                {"Alan": "SKU", left_label: left_row["competitor_sku"], right_label: right_row["competitor_sku"]},
                {"Alan": "Fiyat", left_label: left_row["current_price"], right_label: right_row["current_price"]},
                {"Alan": "Malzeme", left_label: left_row["material_type"], right_label: right_row["material_type"]},
                {"Alan": "Tabla Kalinligi (mm)", left_label: left_row["tabletop_thickness_mm"], right_label: right_row["tabletop_thickness_mm"]},
                {"Alan": "Genislik (cm)", left_label: left_row["width_cm"], right_label: right_row["width_cm"]},
                {"Alan": "Derinlik (cm)", left_label: left_row["depth_cm"], right_label: right_row["depth_cm"]},
                {"Alan": "Yukseklik (cm)", left_label: left_row["height_cm"], right_label: right_row["height_cm"]},
                {"Alan": "Iskelet Tipi", left_label: left_row["skeleton_type"], right_label: right_row["skeleton_type"]},
                {"Alan": "Renk", left_label: left_row["color"], right_label: right_row["color"]},
                {"Alan": "Parse Kaynagi", left_label: left_row["parsed_by"], right_label: right_row["parsed_by"]},
                {"Alan": "Guven Skoru", left_label: left_row["confidence_score"], right_label: right_row["confidence_score"]},
            ]
        )
        st.dataframe(comparison_df, use_container_width=True, hide_index=True)

        confidence_df = pd.DataFrame(
            [
                {"Urun": left_label, "Guven Skoru": left_row["confidence_score"] or 0},
                {"Urun": right_label, "Guven Skoru": right_row["confidence_score"] or 0},
            ]
        )
        confidence_chart = px.bar(
            confidence_df,
            x="Urun",
            y="Guven Skoru",
            color="Urun",
            title="Spec Extraction Guven Skoru",
        )
        confidence_chart.update_layout(height=360, showlegend=False)
        st.plotly_chart(confidence_chart, use_container_width=True)

        specs_overview = specs_df.rename(
            columns={
                "competitor_name": "Marka",
                "product_name": "Urun",
                "material_type": "Malzeme",
                "skeleton_type": "Iskelet",
                "parsed_by": "Kaynak",
                "confidence_score": "Guven",
            }
        )
        st.subheader("Tum Spec Kayitlari")
        st.dataframe(
            specs_overview[["Marka", "Urun", "Malzeme", "Iskelet", "Kaynak", "Guven"]],
            use_container_width=True,
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
