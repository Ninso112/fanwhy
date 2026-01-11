"""
Temperature sensor integration for fanwhy.

This module handles reading temperature data from various sources:
- /sys/class/thermal/thermal_zone*/temp (primary)
- sensors command output (secondary, optional)

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

import glob
import os
import re
import subprocess
from typing import Optional, Tuple


def read_sysfs_temperatures() -> list[float]:
    """
    Read temperature values from /sys/class/thermal/thermal_zone*/temp.
    
    Returns a list of temperature values in Celsius.
    Returns an empty list if no sensors are found or accessible.
    """
    temperatures = []
    thermal_zone_pattern = "/sys/class/thermal/thermal_zone*/temp"
    
    try:
        for temp_file in glob.glob(thermal_zone_pattern):
            try:
                with open(temp_file, 'r') as f:
                    temp_value = f.read().strip()
                    # Temperature is typically in millidegrees Celsius
                    temp_celsius = float(temp_value) / 1000.0
                    temperatures.append(temp_celsius)
            except (OSError, IOError, ValueError) as e:
                # Skip files that can't be read or contain invalid data
                continue
    except Exception:
        # If glob fails or any other error occurs, return empty list
        pass
    
    return temperatures


def read_sensors_command() -> Optional[float]:
    """
    Read CPU temperature from the 'sensors' command (lm-sensors).
    
    Returns the highest CPU temperature found, or None if unavailable.
    """
    try:
        result = subprocess.run(
            ['sensors'],
            capture_output=True,
            text=True,
            timeout=5,
            check=False
        )
        
        if result.returncode != 0:
            return None
        
        output = result.stdout
        
        # Look for CPU temperature patterns (common formats):
        # Core 0:       +45.0°C  (high = +80.0°C, crit = +100.0°C)
        # CPU Temperature: +45.0°C
        # Tdie:         +45.0°C
        cpu_temp_patterns = [
            r'Core\s+\d+:\s+\+?(-?\d+\.?\d*)°?C',
            r'CPU\s+Temperature[:\s]+\+?(-?\d+\.?\d*)°?C',
            r'Tdie[:\s]+\+?(-?\d+\.?\d*)°?C',
            r'Package\s+id\s+\d+:\s+\+?(-?\d+\.?\d*)°?C',
        ]
        
        cpu_temps = []
        for pattern in cpu_temp_patterns:
            matches = re.findall(pattern, output, re.IGNORECASE)
            for match in matches:
                try:
                    temp = float(match)
                    cpu_temps.append(temp)
                except ValueError:
                    continue
        
        if cpu_temps:
            return max(cpu_temps)
        
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        # sensors command not available or failed
        pass
    except Exception:
        # Any other error
        pass
    
    return None


def get_max_temperature() -> Optional[float]:
    """
    Get the maximum temperature from available sources.
    
    Tries sysfs first, then falls back to sensors command.
    Returns the highest temperature found, or None if unavailable.
    """
    # Try sysfs first (most reliable and always available on modern kernels)
    sysfs_temps = read_sysfs_temperatures()
    
    if sysfs_temps:
        max_sysfs_temp = max(sysfs_temps)
    else:
        max_sysfs_temp = None
    
    # Try sensors command as fallback
    sensors_temp = read_sensors_command()
    
    # Return the maximum of available temperatures
    available_temps = [t for t in [max_sysfs_temp, sensors_temp] if t is not None]
    
    if available_temps:
        return max(available_temps)
    
    return None


def get_temperature_summary() -> Optional[str]:
    """
    Get a human-readable temperature summary.
    
    Returns a string like "78°C" or None if no temperature data is available.
    """
    temp = get_max_temperature()
    if temp is not None:
        return f"{temp:.1f}°C"
    return None
