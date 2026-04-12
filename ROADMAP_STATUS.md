# Urun Bazli Rakip Analiz Sistemi Roadmap Durum Raporu

Bu dokuman, mevcut kod tabaninin faz bazli durumunu netlestirmek ve bir sonraki uygulama sprintini odakli hale getirmek icin hazirlandi.

## Ozet

- Faz 1 buyuk olcude tamamlanmis durumda.
- Faz 2 ve Faz 3 cekirdek akis olarak calisiyor.
- Faz 4 temel seviyede devreye alinmis.
- Faz 5 tamamlandi; dashboard ve raporlama akisi mevcut.
- Faz 6 repo seviyesinde tamamlandi; deployment, monitoring, backup ve secret yonetimi icin operasyon paketi eklendi.

## Faz Bazli Durum

| Faz | Durum | Gozlem |
| --- | --- | --- |
| Faz 1: Altyapi ve Temel Kurulum | Tamamlandi | Klasor yapisi, `requirements.txt`, `docker-compose.yml`, Airflow/Streamlit/Postgres servisleri ve DB init SQL mevcut. |
| Faz 2: Veri Toplama Katmani | Tamamlandi | Base scraper, browser profile, marka bazli scraper modulleri, JSON ciktilari ve selector testleri mevcut. |
| Faz 3: Storage ve Orchestration | Tamamlandi | SQLAlchemy repository katmani, upsert mantigi, gunluk ve haftalik Airflow DAG'leri ile katalog diff analizi mevcut. |
| Faz 4: LLM ile Nitelik Cikarimi | Buyuk oranda tamamlandi | `llm_processor` altinda extractor, pipeline, schema ve detail fetcher mevcut; `product_specs` tablosu ile entegre. |
| Faz 5: Analiz, Gorsellestirme ve Raporlama | Tamamlandi | Streamlit dashboard, executive summary, trend, urun karsilastirma, PDF/Excel raporlama ve SMTP tabanli haftalik dagitim akisi mevcut. |
| Faz 6: Canliya Alma ve Guvenlik | Tamamlandi | Production compose override, monitoring stack, backup/restore scriptleri, deployment runbook ve secret yonetimi rehberi eklendi. |

## Kanitlanan Mevcut Yetenekler

### Faz 1

- Docker Compose ile `postgres`, `airflow-init`, `airflow-webserver`, `airflow-scheduler` ve `streamlit` servisleri tanimli.
- `db/init/001_init.sql` icinde `competitors`, `products`, `product_specs`, `price_history`, `promotions` ve `catalog_snapshots` tablolari var.
- `price_history` icin Timescale hypertable olusturuluyor.

### Faz 2

- `scraper/base/base_scraper.py` icinde retry, screenshot, HTML dump ve Playwright tabanli ortak akis bulunuyor.
- `scraper/base/browser_config.py` icinde random user-agent ve proxy rotasyonu destegi var.
- `scraper/brands/istikbal.py`, `scraper/brands/bellona.py`, `scraper/brands/dogtas.py` modulleri mevcut.
- `scraper/data/` altinda gunluk ve katalog JSON ornekleri uretilmis.

### Faz 3

- `db/repository.py` icinde product, promotion ve catalog snapshot icin upsert/CRUD katmani var.
- `airflow/dags/daily_competitor_scrape.py` her sabah 06:00 gunluk scrape ve executive summary uretimini planliyor.
- `airflow/dags/weekly_catalog_analysis.py` haftalik katalog scrape, diff ve spec extraction akisini planliyor.
- `analysis/catalog_diff.py` fark analizi uretiyor.

### Faz 4

- `llm_processor/pipeline.py` urunleri secip detay icerigiyle zenginlestiriyor, spec extraction calistiriyor ve sonucu DB'ye yaziyor.
- `product_specs` tablosu ve ilgili schema/repository entegrasyonu hazir.

### Faz 5

- `dashboard/app.py` icinde:
  - executive summary KPI'lari,
  - katalog diff alarmlari,
  - 30/90/180 gunluk fiyat trendi,
  - urun bazli ozellik karsilastirma,
  - spec extraction guven skoru gorseli,
  - haftalik rapor merkezi ve rapor indirme alanlari bulunuyor.
- `analysis/executive_summary.py` ozet veri paketini uretiyor.
- `analysis/reporting.py` haftalik PDF/Excel raporlarini ve e-posta dagitimini yonetiyor.
- Airflow uzerinde `weekly_reporting_delivery` DAG'i ile Pazartesi sabahi otomatik rapor dagitimi planlandi.

## Eksik veya Kismi Kalan Basliklar

### Operasyonel Notlar

- Reverse proxy ve SSO entegrasyonu kurum altyapisina gore uyarlanmalidir.
- S3 upload icin hostta `aws` CLI kurulu olmalidir.
- Monitoring stack temel metrikleri kapsar; kurum ici alert kurallari ayrica tanimlanmalidir.

## Sonraki Sprint Icin Onerilen Sira

1. SMTP gonderim basarilarini ve DAG metriklerini Grafana alarm kurallarina tasi.
2. Reverse proxy, SSL ve SSO katmanini kurum standartlarina gore ekle.
3. Scraping uyumluluk checklist'ini hukuki ve bilgi guvenligi ekipleriyle sonlandir.

## Karar

Mevcut repo durumuna gore proje Faz 1-6 kapsamindaki teknik teslimatlari repo seviyesinde tamamlamis durumda. Canli ortamda son mile kalan kisim, kurum altyapisina ozgu SSL, firewall, SSO ve hukuki onay adimlaridir.
