# production_line_monitor.py
# Infineon Technologies - Regensburg Plant / Power Module Production
# Real-time monitoring script for automated production line status
# Aggregates machine state, error codes, and throughput from line PLCs
# Author: plant-automation@infineon.internal | Created: 2010 | Python 2.7

import sys
import time
import thread
import threading
import Queue
import socket
import string
import shelve

PLC_HOST = "plc-controller-01.regensburg.infineon.corp"
PLC_PORT = 5020
POLL_INTERVAL_SEC = 5
ERROR_LOG = "/var/log/infineon/production_errors.log"

# Machine state codes from Siemens S7 PLC protocol
STATE_CODES = {
    0: 'IDLE',
    1: 'RUNNING',
    2: 'WARNING',
    3: 'ERROR',
    4: 'MAINTENANCE',
    5: 'SHUTDOWN'
}

# Global event queue (Python 2 Queue module)
event_queue = Queue.Queue()
stop_flag = threading.Event()


class PLCConnectionError(Exception):
    pass


class MachineState:
    """Snapshot of a single machine's state at a point in time."""

    def __init__(self, machine_id, state_code, throughput, error_code=None):
        self.machine_id = machine_id
        self.state_code = state_code
        self.state_name = STATE_CODES.get(state_code, 'UNKNOWN')
        self.throughput = throughput  # units per hour
        self.error_code = error_code
        self.timestamp = time.time()

    def is_critical(self):
        return self.state_code == 3  # ERROR state

    def __str__(self):
        return "[%s] Machine %s: %s | Throughput: %d/hr%s" % (
            time.strftime('%H:%M:%S', time.localtime(self.timestamp)),
            self.machine_id,
            self.state_name,
            self.throughput,
            (" | ERROR: %s" % self.error_code) if self.error_code else ""
        )


def poll_plc(host, port):
    """Connect to PLC and retrieve current machine states."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((host, port))
        s.sendall("GET_STATE_ALL\r\n")
        data = ""
        while True:
            chunk = s.recv(1024)
            if not chunk:
                break
            data += chunk
        s.close()
        return parse_plc_response(data)
    except socket.timeout:
        raise PLCConnectionError("Timeout connecting to PLC at %s:%d" % (host, port))
    except socket.error, e:
        raise PLCConnectionError("Socket error: %s" % e)


def parse_plc_response(raw):
    """Parse PLC ASCII response into MachineState objects."""
    machines = []
    for line in string.split(raw, '\n'):
        line = string.strip(line)
        if not line:
            continue
        parts = string.split(line, '|')
        if len(parts) < 3:
            continue
        machine_id = parts[0]
        try:
            state_code = int(parts[1])
            throughput = int(parts[2])
            error_code = parts[3] if len(parts) > 3 else None
            machines.append(MachineState(machine_id, state_code, throughput, error_code))
        except ValueError:
            print "Bad data from PLC for machine: %s" % machine_id
    return machines


def log_error(machine_state):
    """Write critical machine errors to the error log."""
    try:
        f = open(ERROR_LOG, 'a')
        f.write("%s | Machine %s | Error: %s\n" % (
            time.strftime('%Y-%m-%d %H:%M:%S'),
            machine_state.machine_id,
            machine_state.error_code or 'UNSPECIFIED'
        ))
        f.close()
    except IOError, e:
        print "Cannot write to error log: %s" % e


def monitoring_thread_func():
    """Background thread: polls PLC and pushes states to event queue."""
    while not stop_flag.is_set():
        try:
            states = poll_plc(PLC_HOST, PLC_PORT)
            for state in states:
                event_queue.put(state)
        except PLCConnectionError, e:
            print "PLC polling failed: %s" % e
        time.sleep(POLL_INTERVAL_SEC)


def persist_state_snapshot(states, db_path):
    """Persist current state snapshot using shelve (Python 2 style)."""
    db = shelve.open(db_path)
    for s in states:
        db[str(s.machine_id)] = {
            'state': s.state_name,
            'throughput': s.throughput,
            'timestamp': s.timestamp
        }
    db.close()


def run_monitor():
    """Main monitoring loop."""
    print "Starting Infineon Production Line Monitor..."
    print "Connecting to PLC: %s:%d" % (PLC_HOST, PLC_PORT)

    # Start background polling thread (Python 2 thread module)
    thread.start_new_thread(monitoring_thread_func, ())

    critical_count = 0

    try:
        while True:
            try:
                state = event_queue.get(timeout=POLL_INTERVAL_SEC + 2)
                print str(state)
                if state.is_critical():
                    critical_count += 1
                    log_error(state)
                    if critical_count >= 3:
                        print "*** ALERT: 3+ critical errors detected - notify line supervisor ***"
                        critical_count = 0
            except Queue.Empty:
                print "[%s] No data received from PLC" % time.strftime('%H:%M:%S')
    except KeyboardInterrupt:
        print "\nShutting down monitor..."
        stop_flag.set()
        sys.exit(0)


if __name__ == '__main__':
    run_monitor()
