# systemd install notes for research pipeline

## Copy unit files

```bash
sudo cp deploy/systemd/crypto-trading-research-pipeline.service /etc/systemd/system/
sudo cp deploy/systemd/crypto-trading-research-pipeline.timer /etc/systemd/system/
sudo cp deploy/systemd/crypto-trading-research-anomaly-check.service /etc/systemd/system/
```

## Reload systemd

```bash
sudo systemctl daemon-reload
```

## Enable and start the timer

```bash
sudo systemctl enable --now crypto-trading-research-pipeline.timer
```

## Run one pipeline job manually

```bash
sudo systemctl start crypto-trading-research-pipeline.service
```

## Run anomaly checks manually

```bash
sudo systemctl start crypto-trading-research-anomaly-check.service
```

## Inspect status

```bash
systemctl status crypto-trading-research-pipeline.timer --no-pager
systemctl status crypto-trading-research-pipeline.service --no-pager -n 50
systemctl status crypto-trading-research-anomaly-check.service --no-pager -n 50
```

## Notes

- the timer runs the full machine-only research pipeline every hour
- anomaly checks are designed to be run after pipeline completion or on-demand
- agent participation should remain outside systemd; use the anomaly outputs under `logs/pipeline/state/` as the escalation boundary
