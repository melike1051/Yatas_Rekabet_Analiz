# Secret Yonetimi Rehberi

Bu proje gelistirme ortami icin `.env` dosyasi kullanir. Production ortaminda hassas degerleri repository disinda tutun.

## Onerilen Yaklasim

1. Uygulama sunucusunda `.env` dosyasini deploy pipeline veya secret manager uzerinden olusturun.
2. Bu dosyayi repository icinde tutmayin.
3. Asagidaki alanlari mutlaka secret olarak yonetin:
   - `POSTGRES_PASSWORD`
   - `AIRFLOW_FERNET_KEY`
   - `AIRFLOW_SECRET_KEY`
   - `LLM_API_KEY`
   - `SMTP_PASSWORD`
   - `GRAFANA_ADMIN_PASSWORD`

## Secret Manager Onerileri

- AWS: Secrets Manager veya SSM Parameter Store
- GCP: Secret Manager
- On-prem: Vault veya kurum ici sifre kasasi

## Minumum Uygulama Standardi

- Sunucuda `chmod 600 .env`
- Yedeklerde secret barindiran dosyalari ayri sifreleyin
- SMTP ve LLM anahtarlarini sadece gerekli hostlarda bulundurun
- Secret rotasyonu icin aylik kontrol listesi tanimlayin
