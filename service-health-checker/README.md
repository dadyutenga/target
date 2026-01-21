# Service Health Checker

A lightweight CLI tool to monitor systemd services and HTTP endpoints on Ubuntu/Debian servers.

## Features
- **Monitors** systemd services (via `systemctl`) and HTTP endpoints.
- **Auto-restart** unhealthy services with configurable limits.
- **Modes**: One-shot check (`--once`) or Daemon mode (`--daemon`).
- **Configurable** via JSON.
- **Logging** to file and console.

## Installation

1. Clone or download this repository.
2. Run the installer as root:
   ```bash
   sudo ./install.sh
   ```
   This will:
   - Install `checker.py` to `/usr/local/bin/service-health-checker`
   - Create config at `/etc/service-health-checker/config.json`
   - Enable and start the systemd service.

## Configuration

Edit `/etc/service-health-checker/config.json`:

```json
{
  "interval_seconds": 30,
  "services": [
    {
      "name": "ssh",
      "restart_on_failure": true,
      "max_restarts_per_hour": 3,
      "check": { "type": "systemd" }
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
  ]
}
```

## Usage

Run manually:
```bash
service-health-checker --status
service-health-checker --once
service-health-checker --dry-run
```

Restart a service manually via the tool:
```bash
service-health-checker --restart ssh
```

## Testing

Run unit tests:
```bash
python3 -m unittest discover service-health-checker/tests
```
