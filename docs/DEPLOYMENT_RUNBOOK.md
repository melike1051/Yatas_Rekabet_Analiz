# Deployment Runbook

Bu runbook, sistemi Docker Compose ile production ortamina tasimak icin minimum operasyon adimlarini listeler.

## 1. Sunucu Hazirligi

- Ubuntu 22.04 LTS veya benzeri bir Linux sunucu tahsis edin.
- Docker Engine ve Docker Compose plugin kurun.
- En az 4 vCPU, 8 GB RAM ve hizli disk ayirin.
- Diskte kalici volume ve `backups/` klasoru icin alan ayirin.

## 2. Kodun Sunucuya Alinmasi

```bash
git clone <repo-url> /opt/competitor-analysis
cd /opt/competitor-analysis
cp .env.example .env
```

`.env` icine production degerlerini girin.

## 3. Temel Servisleri Baslatma

Ilk kurulumda:

```bash
docker compose up -d --build airflow-init airflow-webserver airflow-scheduler streamlit postgres
```

Sonraki restart senaryolarinda:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

## 4. Monitoring Stack

Prometheus ve Grafana'yi ayaga kaldirmak icin:

```bash
docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d prometheus grafana node-exporter cadvisor postgres-exporter
```

Varsayilan paneller:
- Grafana: `http://<sunucu-ip>:3000`
- Prometheus: `http://<sunucu-ip>:9090`

## 5. Backup Politikasi

Gunluk backup almak icin host cron ornegi:

```cron
0 2 * * * cd /opt/competitor-analysis && /opt/competitor-analysis/ops/backup_postgres.sh >> /var/log/competitor_backup.log 2>&1
```

Istege bagli S3 upload icin `.env` icine `BACKUP_S3_URI=s3://bucket/path` ekleyin.

Restore:

```bash
/opt/competitor-analysis/ops/restore_postgres.sh /opt/competitor-analysis/backups/postgres/<backup-file>.sql.gz
```

## 6. Guvenlik Kontrol Listesi

- PostgreSQL portunu internete acmayin.
- `.env` dosyasini sadece deploy kullanicisi okuyabilsin.
- Guvenlik grubunda sadece gerekli portlari acin:
  - `8080` Airflow
  - `8501` Streamlit
  - `3000` Grafana
  - `9090` Prometheus
- Mumkunse Airflow ve Grafana'yi VPN veya reverse proxy arkasina alin.
- `AIRFLOW_SECRET_KEY` ve `AIRFLOW_FERNET_KEY` production'da zorunlu olarak doldurulsun.

## 7. Operasyonel Kontroller

- `docker compose ps` ile container durumlarini kontrol edin.
- Airflow DAG sonuclarini her sabah dogrulayin.
- Grafana uzerinden CPU, RAM, container ve PostgreSQL metriklerini takip edin.
- Haftalik rapor e-postasinin geldigini kontrol edin.
