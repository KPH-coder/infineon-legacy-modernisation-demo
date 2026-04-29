# sensor_data_processor.py
# Infineon Technologies - Power Semiconductor Division
# Legacy script: reads temperature and voltage sensor data from chip test rigs
# Written: 2009 | Author: embedded-systems-team@infineon.internal
# Last modified: 2014
# WARNING: Do not modify without consulting legacy systems team

import sys
import string

TEMP_THRESHOLD = 125  # Max junction temperature in Celsius (IGBT spec)
VOLTAGE_LEVELS = [12, 24, 48, 400, 800]  # Supported DC bus voltages (V)

def read_sensor_file(filepath):
    """Read raw sensor output from chip test rig CSV export."""
    data = []
    f = open(filepath, 'r')
    for line in f.readlines():
        line = string.strip(line)
        if line == '' or line.startswith('#'):
            continue
        parts = string.split(line, ',')
        data.append(parts)
    f.close()
    return data


def validate_temperature(temp_str):
    """Check junction temperature is within safe operating range."""
    try:
        temp = float(temp_str)
        if temp > TEMP_THRESHOLD:
            print "WARNING: Junction temperature exceeded threshold: %s C" % temp
            return False
        elif temp < -40:
            print "WARNING: Temperature below minimum operating range: %s C" % temp
            return False
        else:
            return True
    except ValueError:
        print "ERROR: Invalid temperature value: %s" % temp_str
        return False


def process_voltage_readings(readings):
    """Validate and bucket voltage readings into supported levels."""
    results = {}
    for i in xrange(len(readings)):
        row = readings[i]
        if len(row) < 2:
            print "Skipping malformed row %d" % i
            continue
        chip_id = row[0]
        try:
            voltage = float(row[1])
        except ValueError:
            print "Bad voltage at row %d: %s" % (i, row[1])
            continue

        # Find nearest supported voltage level
        matched = None
        for v in VOLTAGE_LEVELS:
            if abs(voltage - v) <= 5:
                matched = v
                break

        if matched is None:
            print "ALERT: Chip %s voltage %s not in supported range" % (chip_id, voltage)
        else:
            if matched not in results:
                results[matched] = []
            results[matched].append(chip_id)

    return results


def generate_report(processed_data, output_path):
    """Write summary report to file."""
    f = open(output_path, 'w')
    f.write("Infineon Power Semiconductor - Voltage Bucketing Report\n")
    f.write("=" * 55 + "\n")
    for voltage, chips in processed_data.iteritems():
        f.write("Voltage %dV: %d chips\n" % (voltage, len(chips)))
        for chip in chips:
            f.write("  - %s\n" % chip)
    f.close()
    print "Report written to: %s" % output_path


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print "Usage: python sensor_data_processor.py <input_file> <output_file>"
        sys.exit(1)
    raw = read_sensor_file(sys.argv[1])
    processed = process_voltage_readings(raw)
    generate_report(processed, sys.argv[2])
