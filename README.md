# Infineon Technologies — Legacy Systems Codebase (Demo)

This repository contains legacy Python scripts from Infineon Technologies' internal manufacturing and embedded systems operations. These scripts were written between 2007–2014 using **Python 2.6/2.7** and are representative of the technical debt found across large semiconductor manufacturers.

## Files

| File | Division | Purpose |
|---|---|---|
| `sensor_data_processor.py` | Power Semiconductors | Reads temperature & voltage data from chip test rigs |
| `chip_yield_calculator.py` | Dresden Fab (IGBT Line) | Wafer yield statistics for quality reporting |
| `firmware_update_manager.py` | Embedded Systems (AURIX) | Firmware version tracking for automotive MCUs |
| `production_line_monitor.py` | Regensburg Plant | Real-time production line status aggregation |

## Legacy Issues Present

- `print` statements (Python 2 syntax — breaks in Python 3)
- `xrange()` — removed in Python 3
- `dict.iteritems()` — removed in Python 3
- `string` module functions (deprecated — use str methods instead)
- `urllib2`, `httplib`, `cPickle`, `ConfigParser`, `Queue`, `thread` — all renamed/restructured in Python 3
- `except ExceptionType, e:` syntax — Python 2 only (Python 3 uses `except ExceptionType as e:`)
- `raise ValueError, "message"` syntax — Python 2 only
- `__cmp__` method — removed in Python 3 (use `__lt__`, `__eq__` etc.)
- `exceptions` module — removed in Python 3
- Files opened without context managers (`with` statements)
- No type hints, no docstring standards, inconsistent error handling patterns
- `shelve` used for persistence (fragile, not portable)

## Modernisation Scope

A full Python 3 migration would address all syntax changes, replace deprecated standard library imports, introduce `with` statements for file handling, add type hints, replace `__cmp__` with rich comparison methods, and improve error handling patterns throughout.

This represents a common modernisation challenge for semiconductor manufacturers running production-critical scripts written before Python 2's end-of-life (January 2020).
