from pathlib import Path


def test_phase6_compose_assets_exist() -> None:
    assert Path("docker-compose.prod.yml").exists()
    assert Path("docker-compose.monitoring.yml").exists()
    assert Path("docker/prometheus/prometheus.yml").exists()
    assert Path("docker/grafana/provisioning/datasources/datasource.yml").exists()


def test_phase6_ops_assets_exist() -> None:
    assert Path("ops/backup_postgres.sh").exists()
    assert Path("ops/restore_postgres.sh").exists()
    assert Path("ops/SECRETS.md").exists()
    assert Path("docs/DEPLOYMENT_RUNBOOK.md").exists()
