from __future__ import annotations

import mimetypes
import os
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import text

from analysis.executive_summary import generate_executive_summary
from db.session import engine
from scraper.utils.logging_config import get_logger
from scraper.utils.normalizers import dump_json


logger = get_logger("analysis.reporting")
REPORTS_DIR = Path("analysis/data/reports")
REPORT_METADATA_PATH = REPORTS_DIR / "latest_report.json"


def parse_email_recipients(raw_value: str | None) -> list[str]:
    if not raw_value:
        return []
    normalized = raw_value.replace(";", ",")
    return [item.strip() for item in normalized.split(",") if item.strip()]


def flatten_catalog_diff_rows(summary: dict[str, Any] | None) -> list[dict[str, Any]]:
    brands = ((summary or {}).get("catalog_diff_summary") or {}).get("brands") or {}
    rows: list[dict[str, Any]] = []
    for brand, payload in brands.items():
        summary_block = payload.get("summary", {})
        rows.append(
            {
                "Marka": brand,
                "Durum": payload.get("status"),
                "Onceki Katalog": summary_block.get("previous_count", 0),
                "Guncel Katalog": summary_block.get("current_count", 0),
                "Yeni Urun": summary_block.get("new_count", 0),
                "Kalkan Urun": summary_block.get("removed_count", 0),
                "Sabit Kalan": summary_block.get("unchanged_count", 0),
            }
        )
    return rows


def build_management_summary(summary: dict[str, Any]) -> list[str]:
    overview = summary.get("overview", {})
    price_summary = summary.get("price_summary", {})
    diff_rows = flatten_catalog_diff_rows(summary)
    total_new_products = sum(int(row.get("Yeni Urun", 0) or 0) for row in diff_rows)
    total_removed_products = sum(int(row.get("Kalkan Urun", 0) or 0) for row in diff_rows)
    top_discount_brand = price_summary.get("top_discount_brand") or "Veri yok"

    return [
        (
            f"Izlenen {overview.get('competitor_count', 0)} rakipte toplam "
            f"{overview.get('product_count', 0)} urun aktif olarak takip ediliyor."
        ),
        (
            f"Son 7 gunde {overview.get('weekly_promotion_count', 0)} kampanya ve "
            f"{overview.get('out_of_stock_count', 0)} stok riski tespit edildi."
        ),
        (
            f"Fiyat aksiyonunda en agresif marka {top_discount_brand}; "
            f"{price_summary.get('price_decreased_count', 0)} urunde fiyat dususu izlendi."
        ),
        f"Haftalik katalog hareketinde {total_new_products} yeni, {total_removed_products} pasif urun tespit edildi.",
    ]


def _load_product_specs_report_frame(limit: int = 250) -> pd.DataFrame:
    query = text(
        """
        SELECT
            c.name AS competitor_name,
            p.product_name,
            p.competitor_sku,
            p.current_price,
            ps.material_type,
            ps.tabletop_thickness_mm,
            ps.width_cm,
            ps.depth_cm,
            ps.height_cm,
            ps.skeleton_type,
            ps.color,
            ps.parsed_by,
            ps.confidence_score
        FROM product_specs ps
        JOIN products p ON p.id = ps.product_id
        JOIN competitors c ON c.id = p.competitor_id
        ORDER BY ps.updated_at DESC
        LIMIT :limit
        """
    )
    with engine.connect() as connection:
        return pd.read_sql_query(query, connection, params={"limit": limit})


def _load_price_changes_report_frame(summary: dict[str, Any]) -> pd.DataFrame:
    frame = pd.DataFrame(summary.get("latest_price_changes", []))
    if frame.empty:
        return frame
    return frame.rename(
        columns={
            "competitor_name": "Marka",
            "product_name": "Urun",
            "competitor_sku": "SKU",
            "current_price": "Guncel Fiyat",
            "previous_price": "Onceki Fiyat",
            "price_change": "Degisim",
            "captured_at": "Yakalandi",
        }
    )


def _load_promotion_report_frame(summary: dict[str, Any]) -> pd.DataFrame:
    frame = pd.DataFrame(summary.get("latest_promotions", []))
    if frame.empty:
        return frame
    return frame.rename(columns={"competitor_name": "Marka", "promotion_count": "Kampanya Adedi"})


def _load_stock_report_frame(summary: dict[str, Any]) -> pd.DataFrame:
    frame = pd.DataFrame(summary.get("stock_summary", []))
    if frame.empty:
        return frame
    return frame.rename(columns={"competitor_name": "Marka", "out_of_stock_count": "Stokta Yok"})


def _build_overview_frame(summary: dict[str, Any]) -> pd.DataFrame:
    overview = summary.get("overview", {})
    price_summary = summary.get("price_summary", {})
    metrics = [
        {"Metrik": "Izlenen Rakip", "Deger": overview.get("competitor_count", 0)},
        {"Metrik": "Toplam Urun", "Deger": overview.get("product_count", 0)},
        {"Metrik": "Haftalik Kampanya", "Deger": overview.get("weekly_promotion_count", 0)},
        {"Metrik": "Stokta Yok", "Deger": overview.get("out_of_stock_count", 0)},
        {"Metrik": "Fiyati Dusan Urun", "Deger": price_summary.get("price_decreased_count", 0)},
        {"Metrik": "Fiyati Artan Urun", "Deger": price_summary.get("price_increased_count", 0)},
        {"Metrik": "Top Discount Marka", "Deger": price_summary.get("top_discount_brand") or "Veri yok"},
    ]
    return pd.DataFrame(metrics)


def build_report_frames(summary: dict[str, Any]) -> dict[str, pd.DataFrame]:
    management_notes = pd.DataFrame({"Yonetici Ozeti": build_management_summary(summary)})
    catalog_diff = pd.DataFrame(flatten_catalog_diff_rows(summary))
    specs = _load_product_specs_report_frame()

    return {
        "overview": _build_overview_frame(summary),
        "management_summary": management_notes,
        "price_changes": _load_price_changes_report_frame(summary),
        "promotions": _load_promotion_report_frame(summary),
        "stock_risk": _load_stock_report_frame(summary),
        "catalog_diff": catalog_diff,
        "product_specs": specs,
    }


def _write_dataframe_sheet(writer: pd.ExcelWriter, sheet_name: str, frame: pd.DataFrame) -> None:
    if frame.empty:
        pd.DataFrame([{"Durum": "Veri bulunamadi"}]).to_excel(writer, sheet_name=sheet_name, index=False)
        return
    frame.to_excel(writer, sheet_name=sheet_name, index=False)
    worksheet = writer.sheets[sheet_name]
    for index, column in enumerate(frame.columns, start=1):
        max_length = max(len(str(column)), *(len(str(value)) for value in frame[column].head(200).tolist()))
        worksheet.column_dimensions[chr(64 + index)].width = min(max_length + 2, 32)


def export_weekly_report_excel(frames: dict[str, pd.DataFrame], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        for sheet_name, frame in frames.items():
            _write_dataframe_sheet(writer, sheet_name[:31], frame)
    return output_path


def _draw_wrapped_text(text_object: Any, text: str, width: int = 95) -> None:
    line = []
    for word in text.split():
        candidate = " ".join(line + [word])
        if len(candidate) > width and line:
            text_object.textLine(" ".join(line))
            line = [word]
        else:
            line.append(word)
    if line:
        text_object.textLine(" ".join(line))


def export_weekly_report_pdf(summary: dict[str, Any], output_path: Path) -> Path:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_canvas = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4

    report_canvas.setTitle("Haftalik Rakip Analiz Raporu")
    report_canvas.setFont("Helvetica-Bold", 16)
    report_canvas.drawString(40, height - 50, "Haftalik Rakip Analiz Raporu")
    report_canvas.setFont("Helvetica", 10)
    report_canvas.drawString(40, height - 68, f"Uretim Tarihi: {datetime.now(timezone.utc).astimezone().isoformat()}")

    y_position = height - 110
    report_canvas.setFont("Helvetica-Bold", 12)
    report_canvas.drawString(40, y_position, "Yonetici Ozeti")
    y_position -= 18

    text_object = report_canvas.beginText(50, y_position)
    text_object.setFont("Helvetica", 10)
    for note in build_management_summary(summary):
        _draw_wrapped_text(text_object, f"- {note}")
        text_object.textLine("")
    report_canvas.drawText(text_object)

    y_position = text_object.getY() - 12
    if y_position < 180:
        report_canvas.showPage()
        y_position = height - 50

    report_canvas.setFont("Helvetica-Bold", 12)
    report_canvas.drawString(40, y_position, "Kritik Metrikler")
    y_position -= 20
    report_canvas.setFont("Helvetica", 10)

    overview_frame = _build_overview_frame(summary)
    for _, row in overview_frame.iterrows():
        report_canvas.drawString(50, y_position, f"{row['Metrik']}: {row['Deger']}")
        y_position -= 14

    y_position -= 10
    report_canvas.setFont("Helvetica-Bold", 12)
    report_canvas.drawString(40, y_position, "Haftalik Katalog Hareketi")
    y_position -= 18
    report_canvas.setFont("Helvetica", 10)

    diff_rows = flatten_catalog_diff_rows(summary)
    if not diff_rows:
        report_canvas.drawString(50, y_position, "Katalog diff verisi bulunamadi.")
    else:
        for row in diff_rows:
            report_canvas.drawString(
                50,
                y_position,
                (
                    f"{row['Marka']}: +{row['Yeni Urun']} yeni, -{row['Kalkan Urun']} pasif, "
                    f"guncel katalog {row['Guncel Katalog']}"
                ),
            )
            y_position -= 14
            if y_position < 60:
                report_canvas.showPage()
                y_position = height - 50
                report_canvas.setFont("Helvetica", 10)

    report_canvas.save()
    return output_path


def _attachment_content_type(path: Path) -> tuple[str, str]:
    guessed, _ = mimetypes.guess_type(path.name)
    if not guessed:
        return ("application", "octet-stream")
    maintype, subtype = guessed.split("/", 1)
    return maintype, subtype


def _build_email_body(summary: dict[str, Any], metadata: dict[str, Any]) -> str:
    lines = [
        "Haftalik rakip analiz raporu ektedir.",
        "",
        "Yonetici Ozeti:",
    ]
    lines.extend(f"- {item}" for item in build_management_summary(summary))
    lines.extend(
        [
            "",
            f"PDF: {metadata['files']['pdf']['path']}",
            f"Excel: {metadata['files']['excel']['path']}",
        ]
    )
    return "\n".join(lines)


def send_weekly_report_email(summary: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    recipients = parse_email_recipients(os.getenv("SMTP_TO"))
    smtp_host = os.getenv("SMTP_HOST")
    smtp_from = os.getenv("SMTP_FROM")

    if not smtp_host or not smtp_from or not recipients:
        return {
            "status": "skipped",
            "reason": "SMTP ayarlari tamamlanmamis",
            "recipients": recipients,
        }

    message = EmailMessage()
    message["Subject"] = "Haftalik Urun Bazli Rakip Analiz Raporu"
    message["From"] = smtp_from
    message["To"] = ", ".join(recipients)
    message.set_content(_build_email_body(summary, metadata))

    for file_info in metadata.get("files", {}).values():
        path = Path(file_info["path"])
        if not path.exists():
            continue
        maintype, subtype = _attachment_content_type(path)
        message.add_attachment(path.read_bytes(), maintype=maintype, subtype=subtype, filename=path.name)

    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    use_ssl = os.getenv("SMTP_USE_SSL", "false").lower() == "true"
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    if use_ssl:
        with smtplib.SMTP_SSL(smtp_host, smtp_port) as smtp:
            if smtp_username and smtp_password:
                smtp.login(smtp_username, smtp_password)
            smtp.send_message(message)
    else:
        with smtplib.SMTP(smtp_host, smtp_port) as smtp:
            if use_tls:
                smtp.starttls()
            if smtp_username and smtp_password:
                smtp.login(smtp_username, smtp_password)
            smtp.send_message(message)

    return {
        "status": "sent",
        "recipients": recipients,
        "smtp_host": smtp_host,
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }


def generate_weekly_report(send_email: bool = False) -> dict[str, Any]:
    summary = generate_executive_summary()
    frames = build_report_frames(summary)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    excel_path = export_weekly_report_excel(frames, REPORTS_DIR / f"weekly_competitor_report_{timestamp}.xlsx")
    pdf_path = export_weekly_report_pdf(summary, REPORTS_DIR / f"weekly_competitor_report_{timestamp}.pdf")

    metadata: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "management_summary": build_management_summary(summary),
        "files": {
            "excel": {"path": str(excel_path), "name": excel_path.name},
            "pdf": {"path": str(pdf_path), "name": pdf_path.name},
        },
    }

    email_status = None
    if send_email:
        try:
            email_status = send_weekly_report_email(summary, metadata)
        except Exception as exc:
            logger.exception("Weekly report email delivery failed")
            email_status = {"status": "failed", "reason": str(exc)}
    else:
        email_status = {"status": "not_requested"}

    metadata["email_delivery"] = email_status
    dump_json(str(REPORT_METADATA_PATH), metadata)
    logger.info(
        "Weekly reporting completed",
        extra={
            "extra_fields": {
                "excel_report": str(excel_path),
                "pdf_report": str(pdf_path),
                "email_status": email_status.get("status"),
            }
        },
    )
    return metadata
