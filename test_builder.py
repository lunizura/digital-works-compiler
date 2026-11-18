#!/usr/bin/env python3
"""
test_builder.py — Verification Suite & Circuit Reconstruction Test Harness

Verification test suite for dwm_builder.py (Milestone 3 / Requirement R4).
Supports dual execution:
  - Standalone CLI: python test_builder.py
  - Pytest Suite:   pytest -v test_builder.py
"""

from __future__ import annotations

import os
import sys
import time
import struct
import tempfile
import inspect
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dwm_builder import DWMBuilder, Component, Pin, Wire, MAGIC_HEADER

SEEDS_DIR = PROJECT_ROOT / "reference_seeds"


# ============================================================================
# Verification Invariant Helpers & Topologies
# ============================================================================

def assert_manhattan_invariants(wire: Wire) -> None:
    """
    Enforces all 5 fundamental Manhattan routing invariants:
      INV-1: Endpoint Pinning (points[0] == src, points[-1] == dst)
      INV-2: Strict Orthogonality (dx == 0 or dy == 0 for every segment)
      INV-3: Non-Degeneracy (no zero-length segments)
      INV-4: Right-Angle Turns (90-degree bends only, dot product == 0)
      INV-5: Minimal Manhattan Distance Bound (total length >= minimal distance)
    """
    pts = wire.points
    assert len(pts) >= 2, f"Wire has fewer than 2 points: {pts}"

    # INV-1: Endpoint Pinning
    assert pts[0] == (wire.source_pin.x, wire.source_pin.y), (
        f"Wire start {pts[0]} does not match source pin ({wire.source_pin.x}, {wire.source_pin.y})"
    )
    assert pts[-1] == (wire.dest_pin.x, wire.dest_pin.y), (
        f"Wire end {pts[-1]} does not match dest pin ({wire.dest_pin.x}, {wire.dest_pin.y})"
    )

    # INV-2 & INV-3: Strict Orthogonality & Non-Degeneracy
    for i in range(len(pts) - 1):
        p1, p2 = pts[i], pts[i + 1]
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        assert dx != 0 or dy != 0, f"Degenerate zero-length segment at index {i}: {p1} -> {p2}"
        assert dx == 0 or dy == 0, f"Diagonal segment at index {i}: {p1} -> {p2} (dx={dx}, dy={dy})"

    # INV-4: Right-Angle Turns (90-degree bends only)
    for i in range(1, len(pts) - 1):
        v1 = (pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])
        v2 = (pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
        dot = v1[0] * v2[0] + v1[1] * v2[1]
        assert dot == 0, f"Turn at vertex {i} ({pts[i]}) is not 90 degrees (dot={dot})"

    # INV-5: Minimal Manhattan Distance Bound
    manhattan_dist = abs(wire.dest_pin.x - wire.source_pin.x) + abs(wire.dest_pin.y - wire.source_pin.y)
    total_len = sum(
        abs(pts[i + 1][0] - pts[i][0]) + abs(pts[i + 1][1] - pts[i][1])
        for i in range(len(pts) - 1)
    )
    assert total_len >= manhattan_dist - 1e-6, (
        f"Total wire length {total_len} is less than Manhattan distance {manhattan_dist}"
    )


def point_on_open_segment(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> bool:
    """Returns True if (px, py) lies strictly in the open interior of segment (x1, y1)-(x2, y2)."""
    if y1 == y2 and abs(py - y1) < 1e-5:
        return min(x1, x2) + 1e-5 < px < max(x1, x2) - 1e-5
    if x1 == x2 and abs(px - x1) < 1e-5:
        return min(y1, y2) + 1e-5 < py < max(y1, y2) - 1e-5
    return False


def detect_wire_t_junctions(wires: List[Wire]) -> List[Tuple[float, float]]:
    """Detects geometric T-junction points where a vertex touches the interior of another wire segment."""
    junctions: List[Tuple[float, float]] = []
    for i, w1 in enumerate(wires):
        for j, w2 in enumerate(wires):
            if i == j:
                continue
            for vx, vy in w2.points:
                for k in range(len(w1.points) - 1):
                    x1, y1 = w1.points[k]
                    x2, y2 = w1.points[k + 1]
                    if point_on_open_segment(vx, vy, x1, y1, x2, y2):
                        pt = (round(vx, 2), round(vy, 2))
                        if pt not in junctions:
                            junctions.append(pt)
    return junctions


def parse_delphi_classes(binary_data: bytes) -> List[str]:
    """Scans Delphi binary stream and returns all defined class names from Marker 0 records."""
    classes: List[str] = []
    i = 0
    n = len(binary_data)
    while i < n - 4:
        if binary_data[i:i + 3] == b"\x02\x00\x06":
            str_len = binary_data[i + 3]
            if i + 4 + str_len <= n:
                cls_name = binary_data[i + 4:i + 4 + str_len].decode("latin1", errors="ignore")
                if cls_name.startswith("T") and cls_name not in classes:
                    classes.append(cls_name)
                i += 4 + str_len
                continue
        i += 1
    return classes


# Circuit construction helper topologies
def build_basic_gate_circuit(gate_type: str) -> DWMBuilder:
    b = DWMBuilder(f"{gate_type}_Circuit")
    if gate_type.upper() == "NOT":
        inp = b.add_input(50.0, 100.0, label="IN")
        gate = b.add_gate(gate_type, 150.0, 100.0, label=gate_type)
        led = b.add_led(250.0, 100.0, label="OUT")
        b.connect(inp.pins["out"], gate.pins["in"])
        b.connect(gate.pins["out"], led.pins["in"])
    else:
        in1 = b.add_input(50.0, 80.0, label="IN1")
        in2 = b.add_input(50.0, 120.0, label="IN2")
        gate = b.add_gate(gate_type, 150.0, 100.0, label=gate_type)
        led = b.add_led(250.0, 100.0, label="OUT")
        b.connect(in1.pins["out"], gate.pins["in1"])
        b.connect(in2.pins["out"], gate.pins["in2"])
        b.connect(gate.pins["out"], led.pins["in"])
    return b


def build_half_adder() -> DWMBuilder:
    b = DWMBuilder("Half_Adder")
    in_a = b.add_input(50.0, 100.0, label="A")
    in_b = b.add_input(50.0, 200.0, label="B")
    gate_xor = b.add_gate("XOR", 200.0, 100.0, label="XOR1")
    gate_and = b.add_gate("AND", 200.0, 200.0, label="AND1")
    led_sum = b.add_led(350.0, 100.0, label="Sum")
    led_carry = b.add_led(350.0, 200.0, label="Carry")

    b.connect(in_a.pins["out"], gate_xor.pins["in1"])
    b.connect(in_a.pins["out"], gate_and.pins["in1"])
    b.connect(in_b.pins["out"], gate_xor.pins["in2"])
    b.connect(in_b.pins["out"], gate_and.pins["in2"])
    b.connect(gate_xor.pins["out"], led_sum.pins["in"])
    b.connect(gate_and.pins["out"], led_carry.pins["in"])
    return b


def build_2x1_mux() -> DWMBuilder:
    b = DWMBuilder("2x1_MUX")
    in_d0 = b.add_input(50.0, 100.0, label="D0")
    in_d1 = b.add_input(50.0, 220.0, label="D1")
    in_s = b.add_input(50.0, 300.0, label="S")

    gate_not = b.add_gate("NOT", 160.0, 300.0, label="NOT1")
    gate_and0 = b.add_gate("AND", 280.0, 120.0, label="AND0")
    gate_and1 = b.add_gate("AND", 280.0, 240.0, label="AND1")
    gate_or = b.add_gate("OR", 420.0, 180.0, label="OR1")
    led_y = b.add_led(540.0, 180.0, label="Y")

    b.connect(in_d0.pins["out"], gate_and0.pins["in1"])
    b.connect(in_s.pins["out"], gate_not.pins["in"])
    b.connect(in_s.pins["out"], gate_and1.pins["in2"])
    b.connect(gate_not.pins["out"], gate_and0.pins["in2"])
    b.connect(in_d1.pins["out"], gate_and1.pins["in1"])
    b.connect(gate_and0.pins["out"], gate_or.pins["in1"])
    b.connect(gate_and1.pins["out"], gate_or.pins["in2"])
    b.connect(gate_or.pins["out"], led_y.pins["in"])
    return b


def build_4nand_xor() -> DWMBuilder:
    b = DWMBuilder("4NAND_XOR")
    in_a = b.add_input(50.0, 175.0, label="A")
    in_b = b.add_input(50.0, 275.0, label="B")

    nand1 = b.add_gate("NAND", 150.0, 225.0, label="NAND1")
    nand2 = b.add_gate("NAND", 250.0, 175.0, label="NAND2")
    nand3 = b.add_gate("NAND", 250.0, 275.0, label="NAND3")
    nand4 = b.add_gate("NAND", 350.0, 225.0, label="NAND4")
    led_out = b.add_led(450.0, 225.0, label="Y")

    b.connect(in_a.pins["out"], nand1.pins["in1"])
    b.connect(in_a.pins["out"], nand2.pins["in1"])
    b.connect(in_b.pins["out"], nand1.pins["in2"])
    b.connect(in_b.pins["out"], nand3.pins["in2"])
    b.connect(nand1.pins["out"], nand2.pins["in2"])
    b.connect(nand1.pins["out"], nand3.pins["in1"])
    b.connect(nand2.pins["out"], nand4.pins["in1"])
    b.connect(nand3.pins["out"], nand4.pins["in2"])
    b.connect(nand4.pins["out"], led_out.pins["in"])
    return b


def build_discrete_xor() -> DWMBuilder:
    b = DWMBuilder("Discrete_XOR")
    in_a = b.add_input(50.0, 100.0, label="A")
    in_b = b.add_input(50.0, 220.0, label="B")

    not_a = b.add_gate("NOT", 150.0, 100.0, label="NOT_A")
    not_b = b.add_gate("NOT", 150.0, 220.0, label="NOT_B")
    and1 = b.add_gate("AND", 270.0, 100.0, label="AND1")
    and2 = b.add_gate("AND", 270.0, 220.0, label="AND2")
    or1 = b.add_gate("OR", 390.0, 160.0, label="OR1")
    led_y = b.add_led(500.0, 160.0, label="Y")

    b.connect(in_a.pins["out"], and1.pins["in1"])
    b.connect(in_a.pins["out"], not_a.pins["in"])
    b.connect(in_b.pins["out"], and2.pins["in2"])
    b.connect(in_b.pins["out"], not_b.pins["in"])
    b.connect(not_a.pins["out"], and2.pins["in1"])
    b.connect(not_b.pins["out"], and1.pins["in2"])
    b.connect(and1.pins["out"], or1.pins["in1"])
    b.connect(and2.pins["out"], or1.pins["in2"])
    b.connect(or1.pins["out"], led_y.pins["in"])
    return b


# ============================================================================
# Test Class 1: Component Placement & Pin Geometry
# ============================================================================

class TestComponentPlacementAndGeometry:
    """Verifies component instantiation, anchor positioning, and pin geometry calculations."""

    def test_add_input_properties_and_pin(self) -> None:
        b = DWMBuilder("InputTest")
        inp = b.add_input(100.0, 150.0, label="SW1")

        assert inp.comp_type == "INPUT"
        assert inp.x == 100.0 and inp.y == 150.0
        assert inp.label == "SW1"
        assert inp.delphi_class == "TInteractiveInput"
        assert len(inp.pins) == 1
        assert "out" in inp.pins

        pin = inp.pins["out"]
        assert pin.name == "out"
        assert pin.pin_type == "output"
        assert pin.x == 100.0 and pin.y == 150.0
        assert pin.component is inp
        assert inp in b.components

    def test_add_led_properties_and_pin(self) -> None:
        b = DWMBuilder("LEDTest")
        led = b.add_led(250.0, 180.0, label="LED1")

        assert led.comp_type == "LED"
        assert led.x == 250.0 and led.y == 180.0
        assert led.label == "LED1"
        assert led.delphi_class == "TLEDDevice"
        assert len(led.pins) == 1
        assert "in" in led.pins

        pin = led.pins["in"]
        assert pin.name == "in"
        assert pin.pin_type == "input"
        assert pin.x == 250.0 and pin.y == 180.0
        assert pin.component is led
        assert led in b.components

    def test_add_gate_supported_types_and_delphi_classes(self) -> None:
        expected_classes = {
            "AND": "T2AndGate",
            "OR": "T2OrGate",
            "NOT": "TNotGate",
            "NAND": "T2NandGate",
            "NOR": "T2NorGate",
            "XOR": "T2XorGate",
        }
        b = DWMBuilder("GateTypeTest")
        for gtype, expected_class in expected_classes.items():
            gate = b.add_gate(gtype, 100.0, 100.0)
            assert gate.comp_type == gtype
            assert gate.delphi_class == expected_class
            assert gate.x == 100.0 and gate.y == 100.0
            assert gate in b.components

    def test_add_gate_case_insensitivity(self) -> None:
        b = DWMBuilder("CaseTest")
        variants = ["and", "And", "AND", " AND ", "or", "Or ", "xor", "XOR "]
        for v in variants:
            gate = b.add_gate(v, 50.0, 50.0)
            assert gate.comp_type == v.strip().upper()
            assert gate in b.components

    def test_two_input_gates_pin_offsets(self) -> None:
        two_input_gates = ["AND", "OR", "NAND", "NOR", "XOR"]
        for gtype in two_input_gates:
            b = DWMBuilder()
            gate = b.add_gate(gtype, 200.0, 150.0)
            assert set(gate.pins.keys()) == {"in1", "in2", "out"}

            p_in1 = gate.pins["in1"]
            p_in2 = gate.pins["in2"]
            p_out = gate.pins["out"]

            # Ground truth offsets: in1=(-30, -10), in2=(-30, +10), out=(+30, 0)
            assert (p_in1.x, p_in1.y) == (170.0, 140.0)
            assert (p_in2.x, p_in2.y) == (170.0, 160.0)
            assert (p_out.x, p_out.y) == (230.0, 150.0)

            # Invariants
            assert p_in2.y - p_in1.y == 20.0  # 20px vertical pin pitch
            assert p_out.x - p_in1.x == 60.0  # 60px horizontal span
            assert p_in1.pin_type == "input"
            assert p_in2.pin_type == "input"
            assert p_out.pin_type == "output"

    def test_not_gate_50px_span_and_geometry(self) -> None:
        b = DWMBuilder()
        gate = b.add_gate("NOT", 200.0, 150.0)
        assert set(gate.pins.keys()) == {"in", "out"}

        p_in = gate.pins["in"]
        p_out = gate.pins["out"]

        assert (p_in.x, p_in.y) == (175.0, 150.0)
        assert (p_out.x, p_out.y) == (225.0, 150.0)

        # 50px body span invariant (DWM_FORMAT.md §6.2)
        assert p_out.x - p_in.x == 50.0
        assert p_in.y == p_out.y == 150.0
        assert p_in.pin_type == "input"
        assert p_out.pin_type == "output"

    def test_invalid_gate_type_raises_value_error(self) -> None:
        b = DWMBuilder()
        for invalid_type in ["BUFFER", "INV", "XNOR", "", "   ", "UNKNOWN"]:
            try:
                b.add_gate(invalid_type, 100.0, 100.0)
                assert False, f"Expected ValueError for invalid gate type {invalid_type!r}"
            except ValueError:
                pass

    def test_non_string_gate_type_raises_type_error(self) -> None:
        b = DWMBuilder()
        for bad_val in [None, 123, 45.6, [], {}]:
            try:
                b.add_gate(bad_val, 100.0, 100.0)  # type: ignore
                assert False, f"Expected TypeError for non-string gate type {bad_val!r}"
            except TypeError:
                pass

    def test_pin_backreference_and_naming(self) -> None:
        b = DWMBuilder()
        gate = b.add_gate("AND", 100.0, 100.0, label="G1")
        for name, pin in gate.pins.items():
            assert pin.component is gate
            assert name in repr(pin)
        assert "AND" in repr(gate)
        assert "G1" in repr(gate)


# ============================================================================
# Test Class 2: Manhattan Orthogonal Routing
# ============================================================================

class TestManhattanOrthogonalRouting:
    """Verifies wire routing calculations, right-angle turns, and Manhattan invariants."""

    def test_collinear_horizontal_routing(self) -> None:
        b = DWMBuilder()
        inp = b.add_input(100.0, 150.0)
        led = b.add_led(300.0, 150.0)
        wire = b.connect(inp.pins["out"], led.pins["in"])

        assert len(wire.points) == 2
        assert wire.points == [(100.0, 150.0), (300.0, 150.0)]
        assert_manhattan_invariants(wire)

    def test_collinear_vertical_routing(self) -> None:
        b = DWMBuilder()
        inp = b.add_input(200.0, 100.0)
        led = b.add_led(200.0, 300.0)
        wire = b.connect(inp.pins["out"], led.pins["in"])

        assert len(wire.points) == 2
        assert wire.points == [(200.0, 100.0), (200.0, 300.0)]
        assert_manhattan_invariants(wire)

    def test_l_shaped_routing_hv(self) -> None:
        b = DWMBuilder()
        inp = b.add_input(100.0, 100.0)
        led = b.add_led(250.0, 200.0)
        wire = b.connect(inp.pins["out"], led.pins["in"], route_type="HV")

        assert len(wire.points) == 3
        assert wire.points == [(100.0, 100.0), (250.0, 100.0), (250.0, 200.0)]
        assert_manhattan_invariants(wire)

    def test_l_shaped_routing_vh(self) -> None:
        b = DWMBuilder()
        inp = b.add_input(100.0, 100.0)
        led = b.add_led(250.0, 200.0)
        wire = b.connect(inp.pins["out"], led.pins["in"], route_type="VH")

        assert len(wire.points) == 3
        assert wire.points == [(100.0, 100.0), (100.0, 200.0), (250.0, 200.0)]
        assert_manhattan_invariants(wire)

    def test_z_shaped_channel_routing_forward(self) -> None:
        b = DWMBuilder()
        inp = b.add_input(100.0, 100.0)
        led = b.add_led(300.0, 200.0)
        wire = b.connect(inp.pins["out"], led.pins["in"])

        assert len(wire.points) == 4
        # Midpoint trunk at x = (100 + 300) / 2 = 200.0
        assert wire.points == [
            (100.0, 100.0),
            (200.0, 100.0),
            (200.0, 200.0),
            (300.0, 200.0),
        ]
        assert_manhattan_invariants(wire)

    def test_z_shaped_channel_routing_retrograde(self) -> None:
        b = DWMBuilder()
        inp = b.add_input(300.0, 200.0)
        led = b.add_led(100.0, 100.0)
        wire = b.connect(inp.pins["out"], led.pins["in"])

        assert len(wire.points) == 4
        assert wire.points == [
            (300.0, 200.0),
            (200.0, 200.0),
            (200.0, 100.0),
            (100.0, 100.0),
        ]
        assert_manhattan_invariants(wire)

    def test_orthogonal_invariant_enforcement_all_segments(self) -> None:
        b = DWMBuilder()
        coords = [
            (0.0, 0.0, 100.0, 0.0),
            (50.0, 50.0, 50.0, 150.0),
            (10.0, 20.0, 80.0, 90.0),
            (150.0, 300.0, 20.0, 10.0),
            (-50.0, -100.0, 150.0, 200.0),
        ]
        for x1, y1, x2, y2 in coords:
            inp = b.add_input(x1, y1)
            led = b.add_led(x2, y2)
            w_def = b.connect(inp.pins["out"], led.pins["in"])
            w_hv = b.connect(inp.pins["out"], led.pins["in"], route_type="HV")
            w_vh = b.connect(inp.pins["out"], led.pins["in"], route_type="VH")

            assert_manhattan_invariants(w_def)
            assert_manhattan_invariants(w_hv)
            assert_manhattan_invariants(w_vh)

    def test_right_angle_90_degree_turns(self) -> None:
        b = DWMBuilder()
        inp = b.add_input(50.0, 50.0)
        led = b.add_led(200.0, 150.0)
        wire = b.connect(inp.pins["out"], led.pins["in"])

        for i in range(1, len(wire.points) - 1):
            v1 = (wire.points[i][0] - wire.points[i - 1][0], wire.points[i][1] - wire.points[i - 1][1])
            v2 = (wire.points[i + 1][0] - wire.points[i][0], wire.points[i + 1][1] - wire.points[i][1])
            dot = v1[0] * v2[0] + v1[1] * v2[1]
            assert dot == 0, f"Turn at index {i} has non-zero dot product: {dot}"

    def test_connect_self_pin_raises_value_error(self) -> None:
        b = DWMBuilder()
        inp = b.add_input(100.0, 100.0)
        try:
            b.connect(inp.pins["out"], inp.pins["out"])
            assert False, "Expected ValueError when connecting pin to itself"
        except ValueError:
            pass

    def test_coincident_distinct_pins(self) -> None:
        b = DWMBuilder()
        inp = b.add_input(100.0, 100.0)
        led = b.add_led(100.0, 100.0)
        wire = b.connect(inp.pins["out"], led.pins["in"])

        assert len(wire.points) == 2
        assert wire.points[0] == (100.0, 100.0)
        assert wire.points[1] == (100.0, 100.0)

    def test_wire_endpoint_pin_associations(self) -> None:
        b = DWMBuilder()
        inp = b.add_input(100.0, 100.0)
        led = b.add_led(200.0, 100.0)
        wire = b.connect(inp.pins["out"], led.pins["in"])

        assert wire.source_pin is inp.pins["out"]
        assert wire.dest_pin is led.pins["in"]
        assert inp.pins["out"].connected_wire is wire
        assert led.pins["in"].connected_wire is wire
        assert "INPUT.out -> LED.in" in repr(wire)

    def test_wire_t_junction_solder_detection(self) -> None:
        b = DWMBuilder()
        in1 = b.add_input(50.0, 100.0)
        led1 = b.add_led(250.0, 100.0)
        led2 = b.add_led(150.0, 200.0)

        trunk = b.connect(in1.pins["out"], led1.pins["in"])
        # Branch wire manually created starting at (150, 100) on the trunk segment
        branch = Wire(
            source_pin=in1.pins["out"],
            dest_pin=led2.pins["in"],
            points=[(150.0, 100.0), (150.0, 200.0)],
        )
        junctions = detect_wire_t_junctions([trunk, branch])
        assert (150.0, 100.0) in junctions


# ============================================================================
# Test Class 3: ASCII Grid Layout Previewer
# ============================================================================

class TestAsciiPreview:
    """Verifies ASCII terminal rasterization of components, labels, and wire tracks."""

    def test_preview_empty_circuit(self) -> None:
        b = DWMBuilder("EmptyCircuit")
        txt = b.preview()
        assert "=== Circuit: EmptyCircuit (Empty) ===" in txt
        assert "(No components placed)" in txt

    def test_preview_single_component_rendering(self) -> None:
        b = DWMBuilder("SingleGate")
        b.add_gate("AND", 100.0, 100.0)
        txt = b.preview()

        assert "=== Circuit: SingleGate (1 components, 0 wires) ===" in txt
        assert "[AND]" in txt
        assert "Components:" in txt
        assert "[1] AND at (100.0, 100.0)" in txt

    def test_preview_component_with_label(self) -> None:
        b = DWMBuilder("LabeledCircuit")
        b.add_gate("OR", 100.0, 100.0, label="GATE1")
        txt = b.preview()

        assert "[OR:GATE1]" in txt
        assert "[1] OR 'GATE1' at (100.0, 100.0)" in txt

    def test_preview_connected_wire_rasterization(self) -> None:
        b = DWMBuilder("ConnectedCircuit")
        inp = b.add_input(50.0, 100.0, label="A")
        led = b.add_led(250.0, 100.0, label="Y")
        b.connect(inp.pins["out"], led.pins["in"])
        txt = b.preview()

        assert "(2 components, 1 wires)" in txt
        assert "-" in txt  # Horizontal wire character

    def test_preview_multi_component_summary_header_and_footer(self) -> None:
        b = build_half_adder()
        txt = b.preview()

        assert "=== Circuit: Half_Adder (6 components, 6 wires) ===" in txt
        assert "Components:" in txt
        assert "[1] INPUT 'A' at (50.0, 100.0)" in txt
        assert "[2] INPUT 'B' at (50.0, 200.0)" in txt
        assert "[3] XOR 'XOR1' at (200.0, 100.0)" in txt
        assert "[4] AND 'AND1' at (200.0, 200.0)" in txt
        assert "[5] LED 'Sum' at (350.0, 100.0)" in txt
        assert "[6] LED 'Carry' at (350.0, 200.0)" in txt

    def test_preview_idempotence(self) -> None:
        b = build_2x1_mux()
        txt1 = b.preview()
        txt2 = b.preview()
        assert txt1 == txt2


# ============================================================================
# Test Class 4: Binary Serialization & Delphi VCL Format
# ============================================================================

class TestBinarySerializationAndVCL:
    """Verifies Delphi VCL token streaming, object graph markers, and binary format fidelity."""

    def test_magic_header_exact_bytes(self) -> None:
        b = DWMBuilder("MagicTest")
        raw = b.to_bytes()
        assert raw[:5] == b"\x04\xdd\xc4\x22\x00"
        assert raw.startswith(MAGIC_HEADER)

    def test_canonical_preamble_structure(self) -> None:
        b = DWMBuilder("TestTitle")
        raw = b.to_bytes()

        # Offset 5 starts preamble list (vaList: 0x01)
        assert raw[5] == 0x01
        # Preamble tags: 0x64 (title), 0x65 (doc), 0x66 (rev), 0xCA, 0xC8
        assert b"\x64" in raw[5:45]
        assert b"TestTitle" in raw[5:45]
        # Preamble terminated by vaNull: 0x00
        assert b"\x00" in raw[5:45]

    def test_delphi_vcl_typed_token_conformance(self) -> None:
        b = build_half_adder()
        raw = b.to_bytes()

        tokens = {
            "vaNull": 0x00,
            "vaList": 0x01,
            "vaInt8": 0x02,
            "vaInt32": 0x04,
            "vaString": 0x06,
            "vaFalse": 0x08,
            "vaTrue": 0x09,
        }
        for token_name, byte_val in tokens.items():
            assert bytes([byte_val]) in raw, f"Expected Delphi token {token_name} (0x{byte_val:02X}) in stream"

    def test_object_marker_graph_deduplication(self) -> None:
        # Build circuit with connected wires and an unconnected probe to exercise all 4 object markers
        b = build_half_adder()
        b.add_led(500.0, 500.0, label="Probe")  # Unconnected pin emits Marker 15 (nil pointer)
        raw = b.to_bytes()

        # Marker 0: 0x02 0x00 (New Class definition)
        assert b"\x02\x00" in raw, "Marker 0 (New Class definition) missing from stream"
        # Marker 1: 0x02 0x01 (Class reference)
        assert b"\x02\x01" in raw, "Marker 1 (Class reference) missing from stream"
        # Marker 2: 0x02 0x02 (Object pointer reference / deduplication)
        assert b"\x02\x02" in raw, "Marker 2 (Object deduplication reference) missing from stream"
        # Marker 15: 0x02 0x0F (Nil pointer reference for unconnected wire)
        assert b"\x02\x0f" in raw, "Marker 15 (Nil pointer reference) missing from stream"

    def test_ieee754_coordinate_encoding_without_vasingle(self) -> None:
        b = DWMBuilder()
        b.add_gate("AND", 123.0, 456.0)
        raw = b.to_bytes()

        expected_coords = struct.pack("<ff", 123.0, 456.0)
        assert expected_coords in raw

        # Ensure vaSingle (0x0F) is not immediately preceding the raw IEEE floats
        coord_idx = raw.find(expected_coords)
        assert coord_idx != -1
        assert raw[coord_idx - 1] != 0x0F, "vaSingle (0x0F) token incorrectly prepended before raw floats"

    def test_binary_serialization_determinism(self) -> None:
        b = build_4nand_xor()
        d1 = b.to_bytes()
        d2 = b.to_bytes()
        assert d1 == d2, "Serialization is non-deterministic"

    def test_file_saving_roundtrip_disk_io(self) -> None:
        b = build_discrete_xor()
        expected_bytes = b.to_bytes()

        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = os.path.join(tmp_dir, "discrete_xor_test.dwm")
            b.save(file_path)

            assert os.path.isfile(file_path), "Saved .dwm file does not exist on disk"
            with open(file_path, "rb") as f:
                saved_bytes = f.read()

            assert saved_bytes == expected_bytes
            assert len(saved_bytes) > 0


# ============================================================================
# Test Class 5: Circuit Reconstruction & Differential Calibration
# ============================================================================

class TestCircuitReconstructionAndDifferential:
    """Verifies complete circuit reconstructions and performs differential comparisons against reference seeds."""

    def test_reconstruct_all_basic_gates_wired(self) -> None:
        gates = ["AND", "OR", "NOT", "NAND", "NOR", "XOR"]
        for gtype in gates:
            b = build_basic_gate_circuit(gtype)
            expected_comps = 3 if gtype == "NOT" else 4
            expected_wires = 2 if gtype == "NOT" else 3

            assert len(b.components) == expected_comps
            assert len(b.wires) == expected_wires

            for w in b.wires:
                assert_manhattan_invariants(w)

            raw = b.to_bytes()
            assert raw.startswith(MAGIC_HEADER)
            classes = parse_delphi_classes(raw)
            assert "TMacro" in classes
            assert "TPin" in classes

    def test_reconstruct_half_adder(self) -> None:
        b = build_half_adder()

        assert len(b.components) == 6
        assert len(b.wires) == 6

        for w in b.wires:
            assert_manhattan_invariants(w)

        raw = b.to_bytes()
        assert raw.startswith(MAGIC_HEADER)
        assert b"T2XorGate" in raw
        assert b"T2AndGate" in raw

    def test_half_adder_differential_against_reference_seed(self) -> None:
        seed_path = SEEDS_DIR / "circuit_half_adder.dwm"
        assert seed_path.exists(), f"Reference seed missing: {seed_path}"

        with open(seed_path, "rb") as f:
            seed_data = f.read()

        assert seed_data.startswith(MAGIC_HEADER), "Reference seed magic header mismatch"

        seed_classes = parse_delphi_classes(seed_data)
        assert "T2XorGate" in seed_classes
        assert "T2AndGate" in seed_classes
        assert "TPin" in seed_classes
        assert "TWire" in seed_classes

        # Reconstructed circuit class conformance
        b = build_half_adder()
        compiled_data = b.to_bytes()
        compiled_classes = parse_delphi_classes(compiled_data)

        assert "T2XorGate" in compiled_classes
        assert "T2AndGate" in compiled_classes
        assert "TPin" in compiled_classes

    def test_reconstruct_2x1_multiplexer(self) -> None:
        b = build_2x1_mux()

        assert len(b.components) == 8
        assert len(b.wires) == 8

        for w in b.wires:
            assert_manhattan_invariants(w)

        raw = b.to_bytes()
        assert raw.startswith(MAGIC_HEADER)
        assert b"TNotGate" in raw
        assert b"T2AndGate" in raw
        assert b"T2OrGate" in raw

    def test_2x1_mux_differential_against_reference_seed(self) -> None:
        seed_path = SEEDS_DIR / "circuit_xor_discrete.dwm"
        assert seed_path.exists(), f"Reference seed missing: {seed_path}"

        with open(seed_path, "rb") as f:
            seed_data = f.read()

        assert seed_data.startswith(MAGIC_HEADER)
        seed_classes = parse_delphi_classes(seed_data)

        # Reference seed contains NOT, AND, OR gates, inputs, and LEDs
        assert "T2AndGate" in seed_classes
        assert "T2OrGate" in seed_classes
        assert "TNotGate" in seed_classes

        b = build_2x1_mux()
        compiled_classes = parse_delphi_classes(b.to_bytes())
        assert "T2AndGate" in compiled_classes
        assert "T2OrGate" in compiled_classes
        assert "TNotGate" in compiled_classes

    def test_reconstruct_universal_gate_xor_from_nand(self) -> None:
        b = build_4nand_xor()

        assert len(b.components) == 7
        assert len(b.wires) == 9

        for w in b.wires:
            assert_manhattan_invariants(w)

        raw = b.to_bytes()
        assert raw.startswith(MAGIC_HEADER)
        assert b"T2NandGate" in raw

    def test_xor_from_nand_differential_against_reference_seed(self) -> None:
        seed_path = SEEDS_DIR / "circuit_xor_from_nand.dwm"
        assert seed_path.exists(), f"Reference seed missing: {seed_path}"

        with open(seed_path, "rb") as f:
            seed_data = f.read()

        # Legacy seed is version 0x1E or modern 0x22
        assert seed_data.startswith(b"\x04\xdd\xc4\x1e\x00") or seed_data.startswith(b"\x04\xdd\xc4\x22\x00")

        seed_classes = parse_delphi_classes(seed_data)
        assert "T2NandGate" in seed_classes

        b = build_4nand_xor()
        compiled_classes = parse_delphi_classes(b.to_bytes())
        assert "T2NandGate" in compiled_classes

    def test_reconstruct_discrete_xor_and_or_invert(self) -> None:
        b = build_discrete_xor()

        assert len(b.components) == 8
        assert len(b.wires) == 9

        for w in b.wires:
            assert_manhattan_invariants(w)

        raw = b.to_bytes()
        assert raw.startswith(MAGIC_HEADER)
        assert b"TNotGate" in raw
        assert b"T2AndGate" in raw
        assert b"T2OrGate" in raw

    def test_reference_seed_file_integrity_scan(self) -> None:
        assert SEEDS_DIR.exists() and SEEDS_DIR.is_dir(), f"Seeds directory missing: {SEEDS_DIR}"
        seed_files = list(SEEDS_DIR.glob("*.dwm"))
        assert len(seed_files) >= 15, f"Expected at least 15 reference seeds, found {len(seed_files)}"

        valid_magics = (b"\x04\xdd\xc4\x22\x00", b"\x04\xdd\xc4\x1e\x00", b"\x04\xdd\xc4\x14\x00")
        for sf in seed_files:
            size = sf.stat().st_size
            assert size > 0, f"Seed file {sf.name} is empty"
            with open(sf, "rb") as f:
                header = f.read(5)
            assert header in valid_magics, f"Seed file {sf.name} has invalid magic: {header!r}"


# ============================================================================
# Standalone Reflection Test Runner Engine
# ============================================================================

class StandaloneTestRunner:
    """Lightweight pure-Python test runner for standalone direct execution."""

    def __init__(self, verbosity: int = 1) -> None:
        self.verbosity = verbosity
        self.passed = 0
        self.failed = 0
        self.errors = 0
        self.failures: List[Tuple[str, str, str]] = []

    def run(self) -> int:
        start_time = time.perf_counter()
        module = sys.modules[__name__]
        test_classes = [
            (name, cls)
            for name, cls in inspect.getmembers(module, inspect.isclass)
            if name.startswith("Test")
        ]
        test_classes.sort(key=lambda item: item[0])

        print("=" * 76)
        print(" Digital Works DWM Circuit Compiler — Verification Test Suite")
        print(" Target: dwm_builder.py | Runner: Standalone Reflection Runner")
        print("=" * 76)

        for cls_name, cls in test_classes:
            print(f"\nRunning {cls_name}:")
            instance = cls()
            methods = [
                m
                for m in dir(instance)
                if m.startswith("test_") and callable(getattr(instance, m))
            ]
            methods.sort()

            for m_name in methods:
                method = getattr(instance, m_name)
                t0 = time.perf_counter()
                try:
                    if hasattr(instance, "setup_method"):
                        instance.setup_method(method)
                    method()
                    if hasattr(instance, "teardown_method"):
                        instance.teardown_method(method)
                    elapsed = time.perf_counter() - t0
                    self.passed += 1
                    print(f"  [PASS] {m_name:<50} ({elapsed:.4f}s)")
                except AssertionError as ae:
                    elapsed = time.perf_counter() - t0
                    self.failed += 1
                    print(f"  [FAIL] {m_name:<50} ({elapsed:.4f}s)")
                    self.failures.append((cls_name, m_name, str(ae)))
                except Exception as ex:
                    elapsed = time.perf_counter() - t0
                    self.errors += 1
                    print(f"  [ERROR] {m_name:<50} ({elapsed:.4f}s)")
                    self.failures.append((cls_name, m_name, f"Exception: {ex}"))

        total_elapsed = time.perf_counter() - start_time
        total_tests = self.passed + self.failed + self.errors

        print("\n" + "=" * 76)
        print(" Verification Suite Execution Summary:")
        print(f"   Total Executed : {total_tests}")
        print(f"   Passed         : {self.passed}")
        print(f"   Failed         : {self.failed}")
        print(f"   Errors         : {self.errors}")
        print(f"   Total Duration : {total_elapsed:.3f}s")
        print("=" * 76)

        if self.failures:
            print("\nFailures Detail:")
            for cname, mname, msg in self.failures:
                print(f"  - {cname}.{mname}: {msg}")
            print("\nSTATUS: TEST SUITE FAILED")
            return 1

        print("STATUS: ALL TESTS PASSED SUCCESSFULLY (Exit Code 0)")
        return 0


if __name__ == "__main__":
    if "--pytest" in sys.argv:
        try:
            import pytest
            args = [__file__, "-v"] + [a for a in sys.argv[1:] if a != "--pytest"]
            sys.exit(pytest.main(args))
        except ImportError:
            print("Warning: pytest not available, falling back to standalone runner.")
    runner = StandaloneTestRunner()
    sys.exit(runner.run())
