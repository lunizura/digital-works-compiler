# Digital Works (`.dwm`) Circuit Compiler

[![CI](https://github.com/lunizura/digital-works-compiler/actions/workflows/ci.yml/badge.svg)](https://github.com/lunizura/digital-works-compiler/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)](#installation)

A zero-dependency Python compiler and reverse-engineered binary specification for generating native **Digital Works 3.0** (`.dwm`) schematic files directly from Python code.

## Why I Built This

Digital Works is widely used for digital logic coursework and lab assignments, but its native `.dwm` file format is an undocumented proprietary binary stream. Manually clicking, dragging, and wiring larger circuits (multiplexers, adders, flip-flops, or truth-table implementations) inside the GUI is tedious and error-prone.

I wanted a way to describe digital logic circuits cleanly in Python, preview their layout in the terminal, and compile them straight into authentic `.dwm` files that open directly in Digital Works—without relying on GUI macros or screenshots.

## Features

- **Pure-Python `.dwm` Binary Serializer (`dwm_builder.py`)** — Emits Borland Delphi VCL `TWriter` / `TSerializeWriter` object-graph streams (`04 dd c4 22 00` magic header) with typed value tokens, dynamic integer compaction, IEEE-754 float coordinates, and pointer deduplication.
- **Component Placement & Pin Geometry** — Supports Interactive Inputs (`TInteractiveInput`), LEDs (`TLEDDevice`), and logic gates (`AND`, `OR`, `NOT`, `NAND`, `NOR`, `XOR`) with exact anchor-to-pin coordinate resolution.
- **Orthogonal Manhattan Wire Router** — Routes collinear, L-shaped (`HV` / `VH`), and Z-shaped channel wires with strictly horizontal/vertical 90° segments and zero diagonal lines.
- **Terminal ASCII Schematic Previewer** — Renders placed components, wire tracks (`-`, `|`, `+`), and a component manifest directly in the terminal via `preview()`.
- **Complete Format Specification (`DWM_FORMAT.md`)** — 1,092-line byte-level specification derived from 20 authentic Digital Works reference circuit files in `reference_seeds/`.

## Installation

Requires Python 3.9+ with **zero external runtime dependencies**.

You can either copy `dwm_builder.py` directly into your project or install in editable mode:

```bash
git clone https://github.com/lunizura/digital-works-compiler.git
cd digital-works-compiler
pip install -e .
```

## Quick Start

```python
from dwm_builder import DWMBuilder

# Build a Half Adder circuit
circuit = DWMBuilder(title="Half Adder")

a = circuit.add_input(50, 100, label="A")
b = circuit.add_input(50, 200, label="B")

xor_gate = circuit.add_gate("XOR", 200, 120)
and_gate = circuit.add_gate("AND", 200, 220)

sum_led = circuit.add_led(350, 120, label="SUM")
carry_led = circuit.add_led(350, 220, label="CARRY")

circuit.connect(a.pins["out"], xor_gate.pins["in1"])
circuit.connect(b.pins["out"], xor_gate.pins["in2"])
circuit.connect(a.pins["out"], and_gate.pins["in1"])
circuit.connect(b.pins["out"], and_gate.pins["in2"])
circuit.connect(xor_gate.pins["out"], sum_led.pins["in"])
circuit.connect(and_gate.pins["out"], carry_led.pins["in"])

print(circuit.preview())
circuit.save("half_adder.dwm")
```

Example `preview()` output:

```text
=== Circuit: Half Adder (6 components, 6 wires) ===
    [INPUT:A]+
             +----------
             |              [XOR]------------------[LED:SUM]
             +----------
             |
             |
             |
             |
             |
    [INPUT:B]+
             +----------
             |              [AND]------------------[LED:CARRY]
             +----------
Components:
  [1] INPUT 'A' at (50.0, 100.0)
  [2] INPUT 'B' at (50.0, 200.0)
  [3] XOR at (200.0, 120.0)
  [4] AND at (200.0, 220.0)
  [5] LED 'SUM' at (350.0, 120.0)
  [6] LED 'CARRY' at (350.0, 220.0)
```

## API Overview

| Method | Description |
|---|---|
| `DWMBuilder(title="Circuit")` | Create a new circuit canvas |
| `add_input(x, y, label="")` | Place an Interactive Input (`TInteractiveInput`, pin `out`) |
| `add_led(x, y, label="")` | Place an LED probe (`TLEDDevice`, pin `in`) |
| `add_gate(gate_type, x, y, label="")` | Place `AND`, `OR`, `NAND`, `NOR`, `XOR` (`in1`, `in2`, `out`) or `NOT` (`in`, `out`) |
| `connect(source_pin, dest_pin, route_type=None)` | Route an orthogonal Manhattan wire (`None` for Z-channel, `"HV"`, or `"VH"`) |
| `preview()` | Render an ASCII grid preview of components and wires |
| `to_bytes()` | Compile and return the raw `.dwm` binary payload |
| `save(file_path)` | Compile and write the `.dwm` file to disk |

## Repository Structure

```text
.
├── dwm_builder.py                # Core Python compiler, router, previewer, and VCL serializer
├── DWM_FORMAT.md                 # Full reverse-engineered Digital Works .dwm binary specification
├── test_builder.py               # Standalone & pytest verification suite (43 tests)
├── tests/
│   ├── conftest.py               # Shared test fixtures
│   ├── test_e2e.py               # 4-tier E2E test suite (135 tests)
│   └── test_tier5_adversarial.py # White-box adversarial stress tests (48 tests)
├── reference_seeds/              # 20 authentic .dwm calibration files
├── pyproject.toml                # Package & pytest metadata
├── .github/workflows/ci.yml      # GitHub Actions CI across Python 3.10–3.13
└── LICENSE                       # MIT License
```

## Running Tests

Run the standalone verification runner (no pytest required):

```bash
python test_builder.py
```

Or run the full 226-test suite with `pytest`:

```bash
python -m pytest -v
```

## Binary Format Documentation

See [`DWM_FORMAT.md`](DWM_FORMAT.md) for the complete `.dwm` format specification, including:
- Magic header (`04 dd c4 22 00`) & canonical preamble property list
- Delphi VCL `TValueType` tokens and integer compaction rules
- `TSerializeWriter` object-graph markers (`0x02 0x00`, `0x02 0x01`, `0x02 0x02`, `0x02 0x0F`)
- Component class hierarchy, anchor geometry, pin offsets, and wire vertex records

## Note

This project was built with AI assistance for the tedious and complex reverse-engineering of the proprietary binary format, specification documentation, and test verification suite.

## License

Released under the [MIT License](LICENSE).
