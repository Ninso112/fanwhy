"""
Tests for sensors_integration module.

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

import tempfile
import unittest
from unittest.mock import MagicMock, mock_open, patch

from fanwhy.sensors_integration import (
    get_max_temperature,
    get_temperature_summary,
    read_sensors_command,
    read_sysfs_temperatures,
)


class TestSensorsIntegration(unittest.TestCase):
    """Test cases for sensor integration."""
    
    def test_read_sysfs_temperatures(self):
        """Test reading temperatures from sysfs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create mock thermal zone files
            zone0 = f"{tmpdir}/thermal_zone0_temp"
            zone1 = f"{tmpdir}/thermal_zone1_temp"
            
            with patch('fanwhy.sensors_integration.glob.glob') as mock_glob:
                mock_glob.return_value = [zone0, zone1]
                
                with patch('builtins.open', mock_open(read_data="45000\n")):
                    temps = read_sysfs_temperatures()
                    self.assertEqual(len(temps), 2)
                    self.assertEqual(temps[0], 45.0)
                    self.assertEqual(temps[1], 45.0)
    
    def test_read_sysfs_temperatures_invalid_file(self):
        """Test handling of invalid sysfs files."""
        with patch('fanwhy.sensors_integration.glob.glob') as mock_glob:
            mock_glob.return_value = ['/nonexistent/file']
            
            temps = read_sysfs_temperatures()
            self.assertEqual(len(temps), 0)
    
    def test_read_sensors_command(self):
        """Test reading temperature from sensors command."""
        mock_output = """
coretemp-isa-0000
Adapter: ISA adapter
Package id 0:  +45.0°C  (high = +80.0°C, crit = +100.0°C)
Core 0:       +42.0°C  (high = +80.0°C, crit = +100.0°C)
Core 1:       +43.0°C  (high = +80.0°C, crit = +100.0°C)
"""
        with patch('fanwhy.sensors_integration.subprocess.run') as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = mock_output
            mock_run.return_value = mock_result
            
            temp = read_sensors_command()
            self.assertIsNotNone(temp)
            self.assertEqual(temp, 45.0)
    
    def test_read_sensors_command_not_available(self):
        """Test handling when sensors command is not available."""
        with patch('fanwhy.sensors_integration.subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError()
            
            temp = read_sensors_command()
            self.assertIsNone(temp)
    
    def test_get_max_temperature(self):
        """Test getting maximum temperature from available sources."""
        with patch('fanwhy.sensors_integration.read_sysfs_temperatures') as mock_sysfs:
            mock_sysfs.return_value = [50.0, 55.0, 48.0]
            
            with patch('fanwhy.sensors_integration.read_sensors_command') as mock_sensors:
                mock_sensors.return_value = None
                
                max_temp = get_max_temperature()
                self.assertEqual(max_temp, 55.0)
    
    def test_get_temperature_summary(self):
        """Test getting temperature summary string."""
        with patch('fanwhy.sensors_integration.get_max_temperature') as mock_max:
            mock_max.return_value = 75.5
            summary = get_temperature_summary()
            self.assertEqual(summary, "75.5°C")
        
        with patch('fanwhy.sensors_integration.get_max_temperature') as mock_max:
            mock_max.return_value = None
            summary = get_temperature_summary()
            self.assertIsNone(summary)


if __name__ == '__main__':
    unittest.main()
