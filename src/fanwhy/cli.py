"""
Command-line interface for fanwhy.

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

import argparse
import sys
import time
from collections import defaultdict
from typing import Optional

from fanwhy import __version__
from fanwhy.core import (
    ProcessInfo,
    calculate_cpu_usage,
    get_top_processes,
)
from fanwhy.sensors_integration import get_max_temperature, get_temperature_summary


def format_process_table(processes: list[ProcessInfo]) -> str:
    """Format a list of processes as a table."""
    if not processes:
        return "  (no processes found)"
    
    # Calculate column widths
    max_pid_len = max(len(str(p.pid)) for p in processes)
    max_name_len = max(len(p.name) for p in processes)
    max_user_len = max(len(p.user) for p in processes)
    
    # Ensure minimum widths
    pid_width = max(6, max_pid_len)
    name_width = max(20, min(40, max_name_len))
    user_width = max(8, max_user_len)
    
    lines = []
    lines.append(f"  {'PID':<{pid_width}} {'Process':<{name_width}} {'User':<{user_width}} {'CPU %':>8}")
    lines.append(f"  {'-' * pid_width} {'-' * name_width} {'-' * user_width} {'-' * 8}")
    
    for proc in processes:
        # Truncate name if too long
        name = proc.name[:name_width] if len(proc.name) <= name_width else proc.name[:name_width - 3] + '...'
        lines.append(f"  {proc.pid:<{pid_width}} {name:<{name_width}} {proc.user:<{user_width}} {proc.cpu_percent:>7.1f}%")
    
    return '\n'.join(lines)


def print_snapshot(top_n: int, show_temps: bool, raw: bool = False) -> None:
    """Print a single snapshot of system state."""
    try:
        # Calculate CPU usage
        cpu_percent = calculate_cpu_usage(interval=1.0)
        
        # Get top processes
        processes = get_top_processes(n=top_n, interval=1.0)
        
        # Get temperature
        temp_summary = None
        if show_temps:
            temp_summary = get_temperature_summary()
        
        if raw:
            # Raw output mode
            print(f"CPU: {cpu_percent:.1f}%")
            if temp_summary:
                print(f"Temperature: {temp_summary}")
            for proc in processes:
                print(f"{proc.pid}\t{proc.name}\t{proc.user}\t{proc.cpu_percent:.1f}")
        else:
            # Formatted output
            print("=== System Load Snapshot ===\n")
            print(f"Overall CPU Usage: {cpu_percent:.1f}%")
            
            if temp_summary:
                print(f"Highest Temperature: {temp_summary}")
            
            print(f"\nTop {len(processes)} CPU Processes:")
            print(format_process_table(processes))
            
            # Generate summary
            print("\n--- Summary ---")
            high_cpu_procs = [p for p in processes if p.cpu_percent > 5.0]
            if high_cpu_procs:
                proc_names = [p.name for p in high_cpu_procs[:3]]
                if len(proc_names) == 1:
                    summary = f"High CPU usage from process '{proc_names[0]}' is likely causing the fan to ramp up."
                elif len(proc_names) == 2:
                    summary = f"High CPU usage from processes '{proc_names[0]}' and '{proc_names[1]}' is likely causing the fan to ramp up."
                else:
                    summary = f"High CPU usage from processes '{proc_names[0]}', '{proc_names[1]}', and others is likely causing the fan to ramp up."
                print(summary)
            else:
                if cpu_percent > 50.0:
                    print("High overall CPU usage is likely causing the fan to ramp up.")
                elif temp_summary:
                    temp_val = float(temp_summary.replace('°C', ''))
                    if temp_val > 70.0:
                        print(f"High temperature ({temp_summary}) is likely causing the fan to ramp up.")
                    else:
                        print("CPU usage and temperature appear normal.")
                else:
                    print("CPU usage appears normal. Temperature data unavailable.")
    
    except IOError as e:
        print(f"Error: Failed to read system information: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error: Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


def print_monitor(interval: float, duration: Optional[float], samples: Optional[int],
                  top_n: int, show_temps: bool, raw: bool = False) -> None:
    """Monitor mode: repeated measurements over time."""
    if duration is None and samples is None:
        # Default to 60 seconds if neither specified
        duration = 60.0
    
    cpu_readings = []
    all_processes = defaultdict(lambda: {'name': '', 'user': '', 'cpu_sum': 0.0, 'count': 0})
    temperatures = []
    start_time = time.time()
    sample_count = 0
    
    try:
        while True:
            # Check if we should stop
            if duration is not None:
                elapsed = time.time() - start_time
                if elapsed >= duration:
                    break
            
            if samples is not None:
                if sample_count >= samples:
                    break
            
            # Take measurement
            try:
                cpu_percent = calculate_cpu_usage(interval=1.0)
                cpu_readings.append(cpu_percent)
                
                processes = get_top_processes(n=top_n, interval=1.0)
                for proc in processes:
                    all_processes[proc.pid]['name'] = proc.name
                    all_processes[proc.pid]['user'] = proc.user
                    all_processes[proc.pid]['cpu_sum'] += proc.cpu_percent
                    all_processes[proc.pid]['count'] += 1
                
                if show_temps:
                    temp = get_max_temperature()
                    if temp is not None:
                        temperatures.append(temp)
                
                sample_count += 1
                
                if raw:
                    print(f"{time.time():.0f}\t{cpu_percent:.1f}")
                else:
                    print(f"[{sample_count}] CPU: {cpu_percent:.1f}%", end='')
                    if show_temps and temperatures:
                        print(f" | Temp: {temperatures[-1]:.1f}°C", end='')
                    print()
            
            except IOError as e:
                print(f"Warning: Failed to read system information: {e}", file=sys.stderr)
                # Continue monitoring despite errors
            
            # Wait for next interval (except for the last iteration)
            if duration is not None:
                elapsed = time.time() - start_time
                if elapsed + interval < duration:
                    time.sleep(interval)
            elif samples is not None:
                if sample_count < samples:
                    time.sleep(interval)
            
            if duration is None and samples is not None and sample_count >= samples:
                break
        
        # Print summary
        if not raw:
            print("\n=== Monitoring Summary ===\n")
            
            if cpu_readings:
                avg_cpu = sum(cpu_readings) / len(cpu_readings)
                max_cpu = max(cpu_readings)
                print(f"Average CPU Usage: {avg_cpu:.1f}%")
                print(f"Maximum CPU Usage: {max_cpu:.1f}%")
            
            if temperatures:
                avg_temp = sum(temperatures) / len(temperatures)
                max_temp = max(temperatures)
                print(f"Average Temperature: {avg_temp:.1f}°C")
                print(f"Maximum Temperature: {max_temp:.1f}°C")
            
            # Calculate average CPU per process
            process_averages = []
            for pid, data in all_processes.items():
                if data['count'] > 0:
                    avg_cpu = data['cpu_sum'] / data['count']
                    process_averages.append(ProcessInfo(
                        pid=pid,
                        name=data['name'],
                        user=data['user'],
                        cpu_percent=avg_cpu
                    ))
            
            process_averages.sort(key=lambda p: p.cpu_percent, reverse=True)
            top_avg = process_averages[:top_n]
            
            if top_avg:
                print(f"\nMost Frequently High-CPU Processes (Average):")
                print(format_process_table(top_avg))
    
    except KeyboardInterrupt:
        if not raw:
            print("\n\nMonitoring interrupted by user.")
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Understand why your Linux system fans are spinning up',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  fanwhy                    # Take a single snapshot
  fanwhy --once             # Same as above (explicit)
  fanwhy --interval 5 --duration 60    # Monitor for 60 seconds, sample every 5 seconds
  fanwhy --interval 2 --samples 10     # Take 10 samples, 2 seconds apart
  fanwhy --top 10 --show-temps         # Show top 10 processes with temperatures
  fanwhy --no-temps                    # Suppress temperature display
        """
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version=f'fanwhy {__version__}'
    )
    
    parser.add_argument(
        '--once',
        action='store_true',
        default=False,
        help='Take a single snapshot (default behavior)'
    )
    
    parser.add_argument(
        '--interval',
        type=float,
        metavar='SECONDS',
        help='Sampling interval for monitor mode (default: 5.0 seconds)'
    )
    
    parser.add_argument(
        '--duration',
        type=float,
        metavar='SECONDS',
        help='Total duration for monitor mode'
    )
    
    parser.add_argument(
        '--samples',
        type=int,
        metavar='N',
        help='Number of samples for monitor mode (alternative to --duration)'
    )
    
    parser.add_argument(
        '--top',
        type=int,
        default=5,
        metavar='N',
        help='Number of top processes to show (default: 5)'
    )
    
    temp_group = parser.add_mutually_exclusive_group()
    temp_group.add_argument(
        '--show-temps',
        action='store_true',
        help='Explicitly show temperatures (default: auto-detect)'
    )
    temp_group.add_argument(
        '--no-temps',
        action='store_true',
        help='Suppress temperature display'
    )
    
    parser.add_argument(
        '--raw',
        action='store_true',
        help='Raw output mode (for debugging)'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.interval is not None and args.interval <= 0:
        parser.error("--interval must be positive")
    
    if args.duration is not None and args.duration <= 0:
        parser.error("--duration must be positive")
    
    if args.samples is not None and args.samples <= 0:
        parser.error("--samples must be positive")
    
    if args.top <= 0:
        parser.error("--top must be positive")
    
    # Determine if we're in monitor mode
    monitor_mode = (args.interval is not None) or (args.duration is not None) or (args.samples is not None)
    
    if monitor_mode and args.interval is None:
        args.interval = 5.0  # Default interval
    
    # Determine temperature display
    if args.no_temps:
        args.show_temps = False
    elif args.show_temps:
        args.show_temps = True
    else:
        # Auto-detect: show temps by default unless explicitly disabled
        args.show_temps = True
    
    return args


def main() -> None:
    """Main entry point."""
    args = parse_arguments()
    
    # Determine mode
    monitor_mode = (args.interval is not None) or (args.duration is not None) or (args.samples is not None)
    
    if monitor_mode:
        print_monitor(
            interval=args.interval or 5.0,
            duration=args.duration,
            samples=args.samples,
            top_n=args.top,
            show_temps=args.show_temps,
            raw=args.raw
        )
    else:
        print_snapshot(
            top_n=args.top,
            show_temps=args.show_temps,
            raw=args.raw
        )


if __name__ == '__main__':
    main()
