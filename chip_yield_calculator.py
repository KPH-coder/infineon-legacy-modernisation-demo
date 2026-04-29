# chip_yield_calculator.py
# Infineon Technologies - Dresden Fab (Module: Automotive IGBT Line)
# Calculates wafer yield statistics for quality reporting
# Author: fab-engineering@infineon.internal | Created: 2007
# Dependencies: Python 2.6+

import os
import sys
import exceptions

# Fab constants
WAFER_DIAMETER_MM = 300
CHIPS_PER_WAFER_TARGET = 400
ACCEPTABLE_YIELD_PCT = 92.0  # Minimum yield before line review triggered

class YieldDataError(exceptions.Exception):
    """Raised when yield data is malformed or out of expected bounds."""
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg


class WaferBatch:
    """Represents a production batch of wafers from the fab line."""

    def __init__(self, batch_id, wafer_count):
        self.batch_id = batch_id
        self.wafer_count = wafer_count
        self.wafer_results = {}  # wafer_id -> (good_chips, total_chips)

    def add_wafer_result(self, wafer_id, good_chips, total_chips):
        if total_chips <= 0:
            raise YieldDataError("Total chips must be positive for wafer %s" % wafer_id)
        if good_chips > total_chips:
            raise YieldDataError("Good chips cannot exceed total for wafer %s" % wafer_id)
        self.wafer_results[wafer_id] = (good_chips, total_chips)

    def calculate_batch_yield(self):
        if not self.wafer_results:
            raise YieldDataError("No wafer results recorded for batch %s" % self.batch_id)
        total_good = 0
        total_chips = 0
        for wafer_id, (good, total) in self.wafer_results.iteritems():
            total_good += good
            total_chips += total
        return (float(total_good) / float(total_chips)) * 100.0

    def flag_low_yield_wafers(self):
        """Return list of wafers below acceptable yield threshold."""
        flagged = []
        for wafer_id, (good, total) in self.wafer_results.iteritems():
            pct = (float(good) / float(total)) * 100.0
            if pct < ACCEPTABLE_YIELD_PCT:
                flagged.append((wafer_id, pct))
        return flagged

    def print_summary(self):
        print "Batch ID: %s" % self.batch_id
        print "Wafers processed: %d" % len(self.wafer_results)
        try:
            batch_yield = self.calculate_batch_yield()
            print "Batch yield: %.2f%%" % batch_yield
            if batch_yield < ACCEPTABLE_YIELD_PCT:
                print "*** YIELD BELOW THRESHOLD - LINE REVIEW REQUIRED ***"
        except YieldDataError, e:
            print "Error calculating yield: %s" % e
        flagged = self.flag_low_yield_wafers()
        if flagged:
            print "Low-yield wafers:"
            for wafer_id, pct in flagged:
                print "  Wafer %s: %.1f%%" % (wafer_id, pct)


def load_batch_from_file(filepath):
    """Parse a fab export file and return a WaferBatch object."""
    if not os.path.exists(filepath):
        raise YieldDataError("File not found: %s" % filepath)
    
    lines = open(filepath).readlines()
    if len(lines) < 2:
        raise YieldDataError("File too short to contain valid batch data")

    header = string.strip(lines[0]) if 'string' in dir() else lines[0].strip()
    batch_id = header.split(':')[-1].strip()
    batch = WaferBatch(batch_id, 0)

    for line in lines[1:]:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split(',')
        if len(parts) != 3:
            print "Skipping malformed line: %s" % line
            continue
        try:
            batch.add_wafer_result(parts[0].strip(), int(parts[1]), int(parts[2]))
        except YieldDataError, e:
            print "Data error: %s" % e

    return batch


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print "Usage: python chip_yield_calculator.py <batch_file>"
        sys.exit(1)
    try:
        batch = load_batch_from_file(sys.argv[1])
        batch.print_summary()
    except YieldDataError, e:
        print "Fatal error: %s" % e
        sys.exit(1)
