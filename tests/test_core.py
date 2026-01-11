"""
Tests for core module.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import unittest
from unittest.mock import MagicMock, mock_open, patch

from fanwhy.core import (
    CPUSnapshot,
    ProcessInfo,
    calculate_cpu_usage,
    get_username,
    read_cpu_stat,
    read_process_stat,
)


class TestCore(unittest.TestCase):
    """Test cases for core functionality."""
    
    def test_cpu_snapshot_total(self):
        """Test CPU snapshot total calculation."""
        snapshot = CPUSnapshot(
            user=100, nice=10, system=50, idle=500,
            iowait=20, irq=5, softirq=10, steal=0,
            guest=0, guest_nice=0
        )
        self.assertEqual(snapshot.total(), 695)
        self.assertEqual(snapshot.active(), 195)
    
    def test_read_cpu_stat(self):
        """Test reading CPU statistics from /proc/stat."""
        mock_content = "cpu  100 10 50 500 20 5 10 0 0 0\n"
        with patch('builtins.open', mock_open(read_data=mock_content)):
            snapshot = read_cpu_stat()
            self.assertEqual(snapshot.user, 100)
            self.assertEqual(snapshot.nice, 10)
            self.assertEqual(snapshot.system, 50)
            self.assertEqual(snapshot.idle, 500)
    
    def test_read_cpu_stat_invalid(self):
        """Test handling of invalid /proc/stat format."""
        mock_content = "invalid format\n"
        with patch('builtins.open', mock_open(read_data=mock_content)):
            with self.assertRaises(IOError):
                read_cpu_stat()
    
    def test_get_username(self):
        """Test getting username from UID."""
        mock_passwd = MagicMock()
        mock_passwd.pw_name = 'testuser'
        
        with patch('fanwhy.core.pwd.getpwuid', return_value=mock_passwd):
            username = get_username(1000)
            self.assertEqual(username, 'testuser')
    
    def test_get_username_fallback(self):
        """Test fallback to UID string when lookup fails."""
        with patch('fanwhy.core.pwd.getpwuid', side_effect=KeyError()):
            username = get_username(9999)
            self.assertEqual(username, '9999')
    
    def test_read_process_stat(self):
        """Test reading process statistics from /proc/[PID]/stat."""
        mock_content = "1234 (test_process) S 1 1234 1234 0 -1 4194560 100 0 0 0 50 30 0 0 20 0 1 0 100 200 0 0\n"
        with patch('builtins.open', mock_open(read_data=mock_content)):
            result = read_process_stat(1234)
            self.assertIsNotNone(result)
            pid, name, utime, stime = result
            self.assertEqual(pid, 1234)
            self.assertEqual(name, 'test_process')
            self.assertEqual(utime, 50)
            self.assertEqual(stime, 30)
    
    def test_read_process_stat_with_spaces(self):
        """Test reading process stat with spaces in process name."""
        mock_content = "1234 (test process name) S 1 1234 1234 0 -1 4194560 100 0 0 0 50 30 0 0 20 0 1 0 100 200 0 0\n"
        with patch('builtins.open', mock_open(read_data=mock_content)):
            result = read_process_stat(1234)
            self.assertIsNotNone(result)
            pid, name, utime, stime = result
            self.assertEqual(pid, 1234)
            self.assertEqual(name, 'test process name')
    
    def test_read_process_stat_nonexistent(self):
        """Test handling of nonexistent process."""
        with patch('builtins.open', side_effect=FileNotFoundError()):
            result = read_process_stat(99999)
            self.assertIsNone(result)
    
    def test_calculate_cpu_usage(self):
        """Test CPU usage calculation."""
        mock_stat1 = "cpu  100 10 50 500 20 5 10 0 0 0\n"
        mock_stat2 = "cpu  200 20 100 600 40 10 20 0 0 0\n"
        
        with patch('builtins.open', side_effect=[
            mock_open(read_data=mock_stat1).return_value,
            mock_open(read_data=mock_stat2).return_value,
        ]):
            with patch('time.sleep'):  # Don't actually sleep
                # Mock read_cpu_stat to return different snapshots
                snapshot1 = CPUSnapshot(100, 10, 50, 500, 20, 5, 10, 0, 0, 0)
                snapshot2 = CPUSnapshot(200, 20, 100, 600, 40, 10, 20, 0, 0, 0)
                
                with patch('fanwhy.core.read_cpu_stat', side_effect=[snapshot1, snapshot2]):
                    cpu_usage = calculate_cpu_usage(interval=0.1)
                    # Should be approximately: (195 active / 695 total) * 100
                    # But we need to calculate based on differences
                    # snapshot1: total=695, active=195, idle=500
                    # snapshot2: total=1000, active=400, idle=600
                    # diff: total=305, active=205, idle=100
                    # usage = 205/305 * 100 ≈ 67.2%
                    self.assertGreater(cpu_usage, 0)
                    self.assertLessEqual(cpu_usage, 100)


if __name__ == '__main__':
    unittest.main()
