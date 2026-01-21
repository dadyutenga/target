import unittest
from unittest.mock import MagicMock, patch, mock_open
import sys
import os
import subprocess

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import checker

class TestServiceHealthChecker(unittest.TestCase):
    
    def test_get_checker_class(self):
        self.assertEqual(checker.get_checker_class('systemd'), checker.SystemdCheck)
        self.assertEqual(checker.get_checker_class('http'), checker.HttpCheck)
        with self.assertRaises(ValueError):
            checker.get_checker_class('invalid')

    @patch('checker.time.time')
    def test_restart_limits(self, mock_time):
        mock_time.return_value = 1000
        config = {
            'name': 'test',
            'restart_on_failure': True,
            'max_restarts_per_hour': 2
        }
        svc = checker.ServiceCheck(config)
        
        self.assertTrue(svc.can_restart())
        
        svc.record_restart()
        self.assertTrue(svc.can_restart())
        
        svc.record_restart()
        self.assertFalse(svc.can_restart())
        
        mock_time.return_value = 1000 + 3601
        self.assertTrue(svc.can_restart())

    @patch('checker.subprocess.run')
    def test_systemd_check_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        config = {'name': 'ssh', 'check': {'type': 'systemd'}}
        svc = checker.SystemdCheck(config)
        self.assertTrue(svc.check())
        mock_run.assert_called_with(["systemctl", "is-active", "ssh"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    @patch('checker.subprocess.run')
    def test_systemd_check_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=3)
        config = {'name': 'ssh', 'check': {'type': 'systemd'}}
        svc = checker.SystemdCheck(config)
        self.assertFalse(svc.check())

    @patch('checker.urllib.request.urlopen')
    def test_http_check_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        config = {'name': 'web', 'check': {'type': 'http', 'url': 'http://test', 'expected_status': 200}}
        svc = checker.HttpCheck(config)
        self.assertTrue(svc.check())

if __name__ == '__main__':
    pass
