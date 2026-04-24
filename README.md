# Urun Bazli Rakip Analiz Sistemi

Bu repository, Yatas icin urun bazli rakip analiz sisteminin temel altyapisini barindirir.

## Klasor Yapisi

- `scraper/`: Rakip sitelerden veri toplama katmani
- `db/`: SQL schema ve veritabani bootstrap dosyalari
- `airflow/`: DAG, plugin ve log klasorleri
- `dashboard/`: Streamlit dashboard uygulamasi
- `llm_processor/`: LLM tabanli nitelik cikarma katmani
- `docker/`: Docker imajlari ve servis bazli yardimci dosyalar
- `tests/`: Otomasyon ve entegrasyon testleri

## Hizli Baslangic

1. `.env.example` dosyasini `.env` olarak kopyalayin ve gerekirse degerleri guncelleyin.
   - Docker Compose ile ayaga kalkan servisler icin `POSTGRES_HOST=postgres` kullanin.
   - Uygulamayi container disinda, dogrudan host makinede calistiracaksaniz `POSTGRES_HOST=localhost` olarak guncelleyin.
2. Docker kuruluysa sistemi baslatin:

```bash
docker compose up --build
```

3. Arayuzler:
   - Streamlit: `http://localhost:8501`
   - Airflow: `http://localhost:8080`
   - PostgreSQL/TimescaleDB: `localhost:5432`

## Raporlama

- Haftalik rapor artefaktlarini uretmek icin:

```bash
python -m scraper.pipeline report
```

- SMTP ayarlari tanimliysa raporu mail ile gondermek icin:

```bash
python -m scraper.pipeline report --email-report
```

## Canliya Alma ve Izleme

- Production override ile servisleri kalici restart politikasi ile baslatmak icin:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

- Monitoring stack'i ayaga kaldirmak icin:

```bash
docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d prometheus grafana node-exporter cadvisor postgres-exporter
```

- Manual PostgreSQL backup:

```bash
./ops/backup_postgres.sh
```

- Ayrintili production adimlari icin:
  - `docs/DEPLOYMENT_RUNBOOK.md`
  - `ops/SECRETS.md`

## Notlar

- Veritabani schema'si `db/init/001_init.sql` ile otomatik yuklenir.
- Airflow icin varsayilan kullanici `admin / admin` olarak olusturulur.
- Faz bazli mevcut durum degerlendirmesi icin `ROADMAP_STATUS.md` dosyasina bakin.
