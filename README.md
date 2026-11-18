# Digital Works (`.dwm`) Circuit Compiler

A zero-dependency Python compiler and reverse-engineered binary specification for generating native **Digital Works 3.0** (`.dwm`) schematic files directly from Python logic descriptions.

## Features

- **Pure-Python `.dwm` Binary Serializer (`dwm_builder.py`)** — Emits Borland Delphi VCL `TWriter` / `TSerializeWriter` object-graph streams (`04 dd c4 22 00` magic header) with typed value tokens, dynamic integer compaction, IEEE-754 float coordinates, and pointer deduplication.
- **Component Placement & Pin Geometry** — Supports Interactive Inputs (`TInteractiveInput`), LEDs (`TLEDDevice`), and logic gates (`AND`, `OR`, `NOT`, `NAND`, `NOR`, `XOR`) with exact anchor-to-pin coordinate resolution.
- **Orthogonal Manhattan Wire Router** — Routes collinear, L-shaped (`HV` / `VH`), and Z-shaped channel wires with strictly horizontal/vertical 90° segments and zero diagonal lines.
- **Terminal ASCII Schematic Previewer** — Renders placed components, wire tracks (`-`, `|`, `+`), and a component manifest directly in the terminal via `preview()`.
- **Complete Format Specification (`DWM_FORMAT.md`)** — 1,092-line byte-level specification derived from 20 authentic Digital Works reference circuit files in `reference_seeds/`.

## Quick Start

Requires Python 3.9+ (no external runtime dependencies).

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
├── dwm_builder.py               # Core Python compiler, router, previewer, and VCL serializer
├── DWM_FORMAT.md                # Full reverse-engineered Digital Works .dwm binary specification
├── test_builder.py              # Standalone & pytest verification suite (43 tests)
├── tests/
│   ├── conftest.py              # Shared test fixtures
│   ├── test_e2e.py              # 4-tier E2E test suite (135 tests)
│   └── test_tier5_adversarial.py # White-box adversarial stress tests (48 tests)
└── reference_seeds/             # 20 authentic .dwm calibration files
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
- Magic header & canonical preamble property list
- Delphi VCL `TValueType` tokens and integer compaction rules
- `TSerializeWriter` object-graph markers (`0x02 0x00`, `0x02 0x01`, `0x02 0x02`, `0x02 0x0F`)
- Component class hierarchy, anchor geometry, pin offsets, and wire vertex records
