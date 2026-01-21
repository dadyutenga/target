#!/usr/bin/env python3
import sys
import os
import time
import json
import logging
import argparse
import subprocess
import signal
import datetime
import urllib.request
import urllib.error
from pathlib import Path

# Defaults
DEFAULT_CONFIG_PATH = "./config.json"
DEFAULT_INTERVAL = 30
DEFAULT_LOG_FILE = "/var/log/service-health-checker.log"

# Setup logging placeholder, will be re-configured after config load
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ServiceCheck:
    def __init__(self, service_config):
        self.name = service_config['name']
        self.config = service_config
        self.restart_on_failure = service_config.get('restart_on_failure', False)
        self.max_restarts = service_config.get('max_restarts_per_hour', 0)
        self.restart_history = []  # List of timestamps

    def check(self):
        """Returns True if healthy, False if unhealthy."""
        raise NotImplementedError

    def restart(self):
        """Restart the service."""
        raise NotImplementedError

    def prune_restart_history(self):
        """Remove restart timestamps older than 1 hour."""
        now = time.time()
        self.restart_history = [t for t in self.restart_history if now - t < 3600]

    def can_restart(self):
        """Check if restart limit allows another restart."""
        self.prune_restart_history()
        if len(self.restart_history) < self.max_restarts:
            return True
        return False

    def record_restart(self):
        self.restart_history.append(time.time())

class SystemdCheck(ServiceCheck):
    def check(self):
        try:
            # Check if active
            cmd = ["systemctl", "is-active", self.name]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error checking systemd service {self.name}: {e}")
            return False

    def restart(self):
        try:
            logger.info(f"Restarting systemd service: {self.name}")
            subprocess.run(["systemctl", "restart", self.name], check=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to restart service {self.name}: {e}")
            return False

class HttpCheck(ServiceCheck):
    def check(self):
        check_config = self.config['check']
        url = check_config.get('url')
        timeout = check_config.get('timeout_seconds', 5)
        expected_status = check_config.get('expected_status', 200)

        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                return response.status == expected_status
        except urllib.error.HTTPError as e:
            logger.warning(f"HTTP check failed for {self.name}: {e.code}")
            return e.code == expected_status
        except Exception as e:
            logger.error(f"HTTP connection error for {self.name}: {e}")
            return False

    def restart(self):
        # HTTP check might still correspond to a systemd service to restart
        # We assume the service name in config is the systemd service name
        try:
            logger.info(f"Restarting associated systemd service for HTTP check: {self.name}")
            subprocess.run(["systemctl", "restart", self.name], check=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to restart service {self.name}: {e}")
            return False

def load_config(path):
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config from {path}: {e}")
        sys.exit(1)

def get_checker_class(check_type):
    if check_type == 'systemd':
        return SystemdCheck
    elif check_type == 'http':
        return HttpCheck
    else:
        raise ValueError(f"Unknown check type: {check_type}")

def main():
    parser = argparse.ArgumentParser(description="Service Health Checker")
    parser.add_argument('--config', default=DEFAULT_CONFIG_PATH, help="Path to config file")
    parser.add_argument('--once', action='store_true', help="Run once and exit")
    parser.add_argument('--daemon', action='store_true', help="Run in daemon mode")
    parser.add_argument('--interval', type=int, help="Override check interval (seconds)")
    parser.add_argument('--dry-run', action='store_true', help="Do not restart services")
    parser.add_argument('--verbose', action='store_true', help="Enable verbose logging")
    parser.add_argument('--status', action='store_true', help="Show status and exit")
    parser.add_argument('--restart', help="Manually restart a service")
    parser.add_argument('--version', action='version', version='%(prog)s 1.0')

    args = parser.parse_args()

    # Determine config path. If not provided or default doesn't exist, try /etc
    config_path = args.config
    if config_path == DEFAULT_CONFIG_PATH and not os.path.exists(config_path):
        etc_path = "/etc/service-health-checker/config.json"
        if os.path.exists(etc_path):
            config_path = etc_path
    
    if not os.path.exists(config_path):
        print(f"Error: Configuration file not found at {config_path}")
        sys.exit(1)

    config = load_config(config_path)

    # Logging Setup
    log_file = config.get('logging', {}).get('log_file', DEFAULT_LOG_FILE)
    log_level = config.get('logging', {}).get('level', 'INFO')
    
    if args.verbose:
        log_level = "DEBUG"

    # Configure logging to file if possible, otherwise stdout is already default
    # We want both potentially
    handlers = [logging.StreamHandler(sys.stdout)]
    try:
        # Create log directory if needed
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir, exist_ok=True)
            except OSError:
                pass # Might not have permission, fallback to stdout only

        file_handler = logging.FileHandler(log_file)
        handlers.append(file_handler)
    except Exception as e:
        print(f"Warning: Could not set up file logging: {e}")

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers,
        force=True
    )

    services = []
    for svc_conf in config.get('services', []):
        try:
            check_type = svc_conf['check']['type']
            cls = get_checker_class(check_type)
            services.append(cls(svc_conf))
        except Exception as e:
            logger.error(f"Failed to initialize service check for {svc_conf.get('name')}: {e}")

    # Handle --restart command
    if args.restart:
        svc = next((s for s in services if s.name == args.restart), None)
        if svc:
            if args.dry_run:
                logger.info(f"[DRY-RUN] Would restart {svc.name}")
            else:
                svc.restart()
        else:
            logger.error(f"Service {args.restart} not found in config.")
        return

    # Handle --status command
    if args.status:
        print(f"{'Service':<20} {'Type':<10} {'Status':<10}")
        print("-" * 40)
        for svc in services:
            healthy = svc.check()
            status = "UP" if healthy else "DOWN"
            print(f"{svc.name:<20} {svc.config['check']['type']:<10} {status:<10}")
        return

    interval = args.interval or config.get('interval_seconds', DEFAULT_INTERVAL)

    # Main Loop
    logger.info("Starting Service Health Checker")
    running = True
    
    def signal_handler(sig, frame):
        nonlocal running
        logger.info("Stopping...")
        running = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    while running:
        for svc in services:
            is_healthy = svc.check()
            if is_healthy:
                logger.debug(f"Service {svc.name} is HEALTHY")
            else:
                logger.warning(f"Service {svc.name} is UNHEALTHY")
                if svc.restart_on_failure:
                    if svc.can_restart():
                        if args.dry_run:
                            logger.info(f"[DRY-RUN] Would restart {svc.name}")
                        else:
                            svc.restart()
                            svc.record_restart()
                    else:
                        logger.error(f"Max restarts reached for {svc.name}. Skipping restart.")
        
        if args.once:
            break
        
        # Sleep in chunks to handle signals faster? or just sleep
        # Simple sleep is fine for this granular interval
        if running:
             time.sleep(interval)

if __name__ == "__main__":
    main()
