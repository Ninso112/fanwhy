"""
Core functionality for fanwhy: CPU load and process monitoring.

This module handles:
- CPU usage calculation from /proc/stat
- Process data collection from /proc/[PID]/stat
- Top process identification

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

import os
import pwd
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class ProcessInfo:
    """Information about a process."""
    pid: int
    name: str
    user: str
    cpu_percent: float


@dataclass
class CPUSnapshot:
    """CPU statistics snapshot."""
    user: int
    nice: int
    system: int
    idle: int
    iowait: int
    irq: int
    softirq: int
    steal: int
    guest: int
    guest_nice: int
    
    def total(self) -> int:
        """Calculate total CPU time."""
        return (self.user + self.nice + self.system + self.idle +
                self.iowait + self.irq + self.softirq + self.steal +
                self.guest + self.guest_nice)
    
    def active(self) -> int:
        """Calculate active (non-idle) CPU time."""
        return self.total() - self.idle


def read_cpu_stat() -> CPUSnapshot:
    """
    Read CPU statistics from /proc/stat.
    
    Returns a CPUSnapshot object.
    Raises IOError if /proc/stat cannot be read.
    """
    try:
        with open('/proc/stat', 'r') as f:
            line = f.readline()
            # Format: cpu  user nice system idle iowait irq softirq steal guest guest_nice
            parts = line.split()
            
            if len(parts) < 11 or parts[0] != 'cpu':
                raise IOError("Invalid /proc/stat format")
            
            return CPUSnapshot(
                user=int(parts[1]),
                nice=int(parts[2]),
                system=int(parts[3]),
                idle=int(parts[4]),
                iowait=int(parts[5]),
                irq=int(parts[6]),
                softirq=int(parts[7]),
                steal=int(parts[8]),
                guest=int(parts[9]) if len(parts) > 9 else 0,
                guest_nice=int(parts[10]) if len(parts) > 10 else 0,
            )
    except (OSError, IOError, ValueError, IndexError) as e:
        raise IOError(f"Failed to read /proc/stat: {e}")


def calculate_cpu_usage(interval: float = 1.0) -> float:
    """
    Calculate overall CPU usage percentage.
    
    Args:
        interval: Time interval in seconds between measurements (default: 1.0)
    
    Returns:
        CPU usage percentage (0.0 to 100.0)
    
    Raises:
        IOError: If /proc/stat cannot be read
    """
    snapshot1 = read_cpu_stat()
    time.sleep(interval)
    snapshot2 = read_cpu_stat()
    
    total_diff = snapshot2.total() - snapshot1.total()
    if total_diff == 0:
        return 0.0
    
    idle_diff = snapshot2.idle - snapshot1.idle
    active_diff = total_diff - idle_diff
    
    cpu_percent = (active_diff / total_diff) * 100.0
    return max(0.0, min(100.0, cpu_percent))


def get_username(uid: int) -> str:
    """
    Get username from UID.
    
    Returns the username, or the UID as string if lookup fails.
    """
    try:
        return pwd.getpwuid(uid).pw_name
    except (KeyError, OverflowError):
        return str(uid)


def read_process_stat(pid: int) -> Optional[tuple[int, str, int, int]]:
    """
    Read process statistics from /proc/[PID]/stat.
    
    Returns a tuple of (pid, name, utime, stime) or None if unavailable.
    utime and stime are in jiffies (clock ticks).
    """
    stat_path = f'/proc/{pid}/stat'
    
    try:
        with open(stat_path, 'r') as f:
            content = f.read()
            # Process name may contain spaces, so we need to handle it carefully
            # Format: pid (name) state ppid ...
            # Find the last ')' to split name from the rest
            end_paren = content.rfind(')')
            if end_paren == -1:
                return None
            
            name_part = content[:end_paren + 1]
            rest_part = content[end_paren + 1:].strip()
            
            # Extract pid and name
            space_idx = name_part.find(' ')
            if space_idx == -1:
                return None
            
            try:
                parsed_pid = int(name_part[:space_idx])
                # Name is between '(' and ')'
                name_start = name_part.find('(')
                name_end = name_part.rfind(')')
                if name_start == -1 or name_end == -1:
                    return None
                name = name_part[name_start + 1:name_end]
            except ValueError:
                return None
            
            # Parse the rest (state, ppid, ..., utime, stime, ...)
            parts = rest_part.split()
            if len(parts) < 13:
                return None
            
            # utime is field 13 (index 11), stime is field 14 (index 12)
            utime = int(parts[11])
            stime = int(parts[12])
            
            return (parsed_pid, name, utime, stime)
    
    except (OSError, IOError, ValueError, IndexError):
        return None


def read_process_uid(pid: int) -> Optional[int]:
    """
    Read process UID from /proc/[PID]/status.
    
    Returns UID or None if unavailable.
    """
    status_path = f'/proc/{pid}/status'
    
    try:
        with open(status_path, 'r') as f:
            for line in f:
                if line.startswith('Uid:'):
                    parts = line.split()
                    if len(parts) >= 2:
                        return int(parts[1])  # Real UID is the first value
    except (OSError, IOError, ValueError, IndexError):
        pass
    
    return None


def get_all_processes() -> list[ProcessInfo]:
    """
    Get information about all running processes.
    
    Returns a list of ProcessInfo objects.
    Note: CPU percentages are not calculated here (requires two snapshots).
    """
    processes = []
    
    try:
        for item in os.listdir('/proc'):
            try:
                pid = int(item)
            except ValueError:
                continue
            
            stat_data = read_process_stat(pid)
            if stat_data is None:
                continue
            
            _, name, _, _ = stat_data
            
            # Get UID
            uid = read_process_uid(pid)
            if uid is None:
                continue
            
            user = get_username(uid)
            
            processes.append(ProcessInfo(
                pid=pid,
                name=name,
                user=user,
                cpu_percent=0.0  # Will be calculated later
            ))
    
    except OSError:
        pass
    
    return processes


def calculate_process_cpu_usage(interval: float = 1.0) -> list[ProcessInfo]:
    """
    Calculate CPU usage for all processes.
    
    Args:
        interval: Time interval in seconds between measurements (default: 1.0)
    
    Returns:
        List of ProcessInfo objects with CPU percentages calculated
    """
    # First snapshot: collect PIDs and their CPU times
    snapshot1 = {}
    process_info_map = {}
    
    try:
        for item in os.listdir('/proc'):
            try:
                pid = int(item)
            except ValueError:
                continue
            
            stat_data = read_process_stat(pid)
            if stat_data is None:
                continue
            
            pid_val, name, utime, stime = stat_data
            total_time = utime + stime
            snapshot1[pid_val] = total_time
            
            # Store process info
            uid = read_process_uid(pid_val)
            if uid is None:
                continue
            
            user = get_username(uid)
            process_info_map[pid_val] = ProcessInfo(
                pid=pid_val,
                name=name,
                user=user,
                cpu_percent=0.0
            )
    
    except OSError:
        return []
    
    # Wait for the interval
    time.sleep(interval)
    
    # Get CPU clock ticks per second
    try:
        # SC_CLK_TCK may not be available on all systems
        if hasattr(os, 'sysconf_names') and 'SC_CLK_TCK' in os.sysconf_names:
            clock_ticks = os.sysconf(os.sysconf_names['SC_CLK_TCK'])
        else:
            clock_ticks = 100  # Default fallback
    except (OSError, KeyError, AttributeError):
        clock_ticks = 100  # Default fallback
    
    # Second snapshot: calculate CPU usage
    processes_with_usage = []
    
    for pid, info in process_info_map.items():
        stat_data = read_process_stat(pid)
        if stat_data is None:
            continue
        
        _, _, utime, stime = stat_data
        total_time2 = utime + stime
        
        # Calculate CPU percentage
        time_diff = total_time2 - snapshot1.get(pid, total_time2)
        cpu_percent = (time_diff / clock_ticks) / interval * 100.0
        
        info.cpu_percent = max(0.0, cpu_percent)
        processes_with_usage.append(info)
    
    return processes_with_usage


def get_top_processes(n: int = 5, interval: float = 1.0) -> list[ProcessInfo]:
    """
    Get the top N processes by CPU usage.
    
    Args:
        n: Number of top processes to return (default: 5)
        interval: Time interval in seconds for CPU calculation (default: 1.0)
    
    Returns:
        List of ProcessInfo objects sorted by CPU usage (highest first)
    """
    processes = calculate_process_cpu_usage(interval)
    processes.sort(key=lambda p: p.cpu_percent, reverse=True)
    return processes[:n]
