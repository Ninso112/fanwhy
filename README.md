# fanwhy

fanwhy is a small command-line tool for Linux that helps you understand why your laptop or PC fan is spinning up. It samples CPU load, top CPU-hungry processes, and (optionally) temperature sensors, then prints a concise summary so you can see which processes and components are most likely responsible for high fan activity.

## Installation

### From Source

Clone the repository and install using pip:

```bash
git clone <repository-url>
cd fanwhy
pip install .
```

Alternatively, you can run fanwhy directly from the source directory without installation:

```bash
cd fanwhy
python -m fanwhy.cli
```

Or install in development mode:

```bash
pip install -e .
```

## Usage

### Basic Snapshot Mode

Take a single snapshot of the current system state:

```bash
fanwhy
```

or explicitly:

```bash
fanwhy --once
```

This will display:
- Overall CPU usage percentage
- Top 5 CPU-consuming processes (by default)
- Highest temperature (if available)
- A summary explaining likely causes for fan activity

### Monitor Mode

Monitor the system over time with repeated measurements:

```bash
fanwhy --interval 5 --duration 60
```

This monitors for 60 seconds, taking measurements every 5 seconds.

Alternatively, specify the number of samples:

```bash
fanwhy --interval 2 --samples 10
```

This takes 10 samples, 2 seconds apart.

Monitor mode displays:
- Real-time CPU usage and temperature (if available) for each sample
- A summary at the end with:
  - Average and maximum CPU usage
  - Average and maximum temperature
  - Most frequently high-CPU processes (averaged over the monitoring period)

### Display Options

Show more processes:

```bash
fanwhy --top 10
```

Explicitly show temperatures:

```bash
fanwhy --show-temps
```

Suppress temperature display:

```bash
fanwhy --no-temps
```

Raw output mode (for debugging or scripting):

```bash
fanwhy --raw
```

## Command-Line Options

- `--help`: Show help message and exit
- `--version`: Show version number and exit
- `--once`: Take a single snapshot (default behavior)
- `--interval SECONDS`: Sampling interval for monitor mode (default: 5.0 seconds)
- `--duration SECONDS`: Total duration for monitor mode
- `--samples N`: Number of samples for monitor mode (alternative to `--duration`)
- `--top N`: Number of top processes to show (default: 5)
- `--show-temps`: Explicitly show temperatures (default: auto-detect)
- `--no-temps`: Suppress temperature display
- `--raw`: Raw output mode (for debugging)

## Limitations and Known Issues

### Temperature Display

- Temperature display depends on available sensors and proper permissions
- On systems with `/sys/class/thermal/thermal_zone*/temp` files, temperatures are read directly
- If available, the `sensors` command (from the `lm-sensors` package) is used as a fallback
- If no temperature sensors are accessible, the tool will continue without temperature information

### Fan Correlation

- This tool can only show **suspected** causes based on CPU usage and temperature
- There is no guarantee of exact fan correlation, as fan behavior depends on hardware-specific algorithms and firmware
- Different hardware manufacturers and BIOS/UEFI configurations may have different fan control logic

### System Differences

- Behavior may vary between Linux distributions and kernel versions
- Some systems may require elevated permissions to access certain `/proc` or `/sys` files (though this is uncommon)
- Process information is limited to what is accessible through `/proc/[PID]/stat` and `/proc/[PID]/status`

### Process CPU Calculation

- CPU usage calculations require two measurements over time (typically 1 second interval)
- Very short-lived processes may not appear in the results
- CPU percentages are calculated based on the time interval, so results may vary slightly depending on system load

## License

This project is licensed under the GNU General Public License v3.0 (GPLv3).

See the [LICENSE](LICENSE) file for the full license text.

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

## Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests.
