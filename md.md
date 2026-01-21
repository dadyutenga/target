You are a senior Linux systems engineer + Python developer. Build a “Service Health Checker” tool for Ubuntu/Debian servers.

GOAL
Create a CLI tool that monitors specified systemd services, checks their health, and optionally restarts them. It must also support a one-shot mode and a daemon mode (loop). It should work on Ubuntu/Debian where systemd is present.

TECH CHOICES
- Language: Python 3 (must run on Ubuntu/Debian server)
- Use only Python standard library (subprocess, argparse, json, time, logging, os, signal, datetime, pathlib)
- Do NOT require external pip packages.
- Must interact with systemd via `systemctl` and optionally `journalctl`.

PROJECT OUTPUT
Generate a complete project folder:
service-health-checker/
  README.md
  checker.py
  config.example.json
  install.sh
  systemd/
    service-health-checker.service
  logs/ (created at runtime)
  tests/
    test_parser.py (basic unit tests)

FEATURE REQUIREMENTS
1) CLI
Command: `checker.py`
Arguments:
- `--config /etc/service-health-checker/config.json` (default: ./config.json if exists else error)
- `--once` run one check cycle then exit
- `--daemon` loop checks based on interval (default config interval)
- `--interval <seconds>` override config interval
- `--dry-run` do not restart services, only report actions
- `--verbose` show detailed output
- `--status` print a nice summary table of current service states and exit
- `--restart <service>` manually restart a single service and exit
- `--version`

2) Config File (JSON)
Config schema:
{
  "interval_seconds": 30,
  "services": [
    {
      "name": "ssh",
      "restart_on_failure": true,
      "max_restarts_per_hour": 3,
      "check": {
        "type": "systemd"
      }
    },
    {
      "name": "nginx",
      "restart_on_failure": true,
      "max_restarts_per_hour": 5,
      "check": {
        "type": "http",
        "url": "http://127.0.0.1",
        "timeout_seconds": 2,
        "expected_status": 200
      }
    }
  ],
  "logging": {
    "log_file": "/var/log/service-health-checker.log",
    "level": "INFO"
  }
}

Supported checks:
- systemd: check if service is active
- http: check if HTTP response code matches expected
