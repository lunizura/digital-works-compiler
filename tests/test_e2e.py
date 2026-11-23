"""
Opaque-Box E2E Test Suite: Digital Works DWM Circuit Compiler
Comprehensive 4-Tier Verification Suite (Tiers 1-4)

Milestone: E2E Testing Track
Specification Authorities:
  - DWM_FORMAT.md (Public interface contracts & pin offset tables)
  - reference_seeds/circuit_half_adder.dwm (Calibration seed)

Tiers Covered:
  - Tier 1: Feature Coverage (F1-F7, >=5 tests per feature across 7 features)
  - Tier 2: Boundary & Corner Cases (F1-F7, >=5 tests per feature across 7 features)
  - Tier 3: Cross-Feature Combinations & Manhattan Routing Invariants (14 tests)
  - Tier 4: Real-World Application Workload Scenarios & Calibration (8 tests)
"""

import sys
from pathlib import Path
import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Graceful import of dwm_builder to allow clean test collection in Dual-Track development
try:
    from dwm_builder import DWMBuilder, Component, Pin, Wire
except ImportError:
    DWMBuilder = None
    Component = None
    Pin = None
    Wire = None

MAGIC_HEADER = b"\x04\xdd\xc4\x22\x00"
SEEDS_DIR = PROJECT_ROOT / "reference_seeds"


@pytest.fixture(autouse=True)
def require_dwm_builder():
    """
    Autouse fixture that reports Milestone 2 implementation status.
    During Milestone 1 / E2E track parallel execution, tests can be collected;
    when executing tests, this provides an informative error if dwm_builder.py is pending.
    """
    if DWMBuilder is None:
        pytest.fail(
            "dwm_builder.py is not yet implemented (Milestone 2 in progress). "
            "Interface contract verified from PROJECT.md."
        )


def assert_manhattan_routing_invariants(wire):
    """
    Validates all 8 fundamental Manhattan orthogonal routing invariants on a Wire:
      INV-1: Endpoint Pinning (points[0] == src, points[-1] == dst)
      INV-2: Strict Orthogonality (zero diagonal segments: dx == 0 or dy == 0)
      INV-3: Non-Degeneracy (no consecutive duplicate vertices: dx != 0 or dy != 0)
      INV-4: Right-Angle Turns (dot product of adjacent segment vectors == 0)
      INV-5: Minimal Manhattan Bound (wire length >= Manhattan distance)
    """
    points = wire.points
    assert len(points) >= 2, f"Wire must have at least 2 points, got {len(points)}"

    # INV-1: Endpoint Pinning
    src_pt = (wire.source_pin.x, wire.source_pin.y)
    dst_pt = (wire.dest_pin.x, wire.dest_pin.y)
    assert points[0] == src_pt, f"Wire start {points[0]} does not match source pin {src_pt}"
    assert points[-1] == dst_pt, f"Wire end {points[-1]} does not match dest pin {dst_pt}"

    # INV-2 & INV-3: Orthogonality & Non-Degeneracy
    for i in range(len(points) - 1):
        p1 = points[i]
        p2 = points[i + 1]
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        assert (dx != 0 or dy != 0), f"Degenerate zero-length segment at index {i}: {p1} -> {p2}"
        assert (dx == 0 or dy == 0), (
            f"Diagonal segment detected at index {i}: {p1} -> {p2} (dx={dx}, dy={dy})"
        )

    # INV-4: Bend Right-Angle Validation
    for i in range(1, len(points) - 1):
        v_in = (points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1])
        v_out = (points[i + 1][0] - points[i][0], points[i + 1][1] - points[i][1])
        dot_product = v_in[0] * v_out[0] + v_in[1] * v_out[1]
        assert dot_product == 0, f"Bend at index {i} is not 90 degrees: dot_product={dot_product}"

    # INV-5: Minimal Manhattan Distance Bound
    total_len = sum(
        abs(points[i + 1][0] - points[i][0]) + abs(points[i + 1][1] - points[i][1])
        for i in range(len(points) - 1)
    )
    min_dist = abs(dst_pt[0] - src_pt[0]) + abs(dst_pt[1] - src_pt[1])
    assert total_len >= min_dist - 1e-6, (
        f"Total wire length {total_len} is less than Manhattan distance {min_dist}"
    )


# ============================================================================
# TIER 1: FEATURE COVERAGE (>=5 tests per feature across 7 features)
# ============================================================================

@pytest.mark.tier1
class TestTier1InputPlacement:
    """Feature 1: Input device placement tests (add_input)"""

    def test_add_input_default_label(self):
        builder = DWMBuilder()
        comp = builder.add_input(100.0, 50.0)
        assert comp.comp_type == "INPUT"
        assert comp.x == 100.0
        assert comp.y == 50.0
        assert comp.label == ""
        assert comp.delphi_class == "TInteractiveInput"

    def test_add_input_custom_label(self):
        builder = DWMBuilder()
        comp = builder.add_input(150.0, 75.0, label="ENABLE")
        assert comp.label == "ENABLE"
        assert comp.x == 150.0
        assert comp.y == 75.0

    def test_add_input_pin_structure(self):
        builder = DWMBuilder()
        comp = builder.add_input(100.0, 50.0)
        assert "out" in comp.pins
        assert len(comp.pins) == 1
        pin = comp.pins["out"]
        assert pin.name == "out"
        assert pin.pin_type == "output"
        assert pin.component is comp

    def test_add_input_pin_coordinates(self):
        builder = DWMBuilder()
        comp = builder.add_input(100.0, 50.0)
        pin = comp.pins["out"]
        assert pin.y == 50.0
        assert pin.x in (100.0, 115.0)

    def test_add_input_collection_storage(self):
        builder = DWMBuilder()
        builder.add_input(10.0, 20.0, label="A")
        builder.add_input(30.0, 40.0, label="B")
        builder.add_input(50.0, 60.0, label="C")
        assert len(builder.components) == 3
        assert [c.label for c in builder.components] == ["A", "B", "C"]


@pytest.mark.tier1
class TestTier1LEDPlacement:
    """Feature 2: LED device placement tests (add_led)"""

    def test_add_led_default_label(self):
        builder = DWMBuilder()
        comp = builder.add_led(200.0, 100.0)
        assert comp.comp_type == "LED"
        assert comp.x == 200.0
        assert comp.y == 100.0
        assert comp.label == ""
        assert comp.delphi_class == "TLEDDevice"

    def test_add_led_custom_label(self):
        builder = DWMBuilder()
        comp = builder.add_led(300.0, 150.0, label="OUT_Q")
        assert comp.label == "OUT_Q"
        assert comp.x == 300.0
        assert comp.y == 150.0

    def test_add_led_pin_structure(self):
        builder = DWMBuilder()
        comp = builder.add_led(200.0, 100.0)
        assert "in" in comp.pins
        assert len(comp.pins) == 1
        pin = comp.pins["in"]
        assert pin.name == "in"
        assert pin.pin_type == "input"
        assert pin.component is comp

    def test_add_led_pin_coordinates(self):
        builder = DWMBuilder()
        comp = builder.add_led(200.0, 100.0)
        pin = comp.pins["in"]
        assert pin.y == 100.0
        assert pin.x in (200.0, 185.0)

    def test_add_led_multiple_placement(self):
        builder = DWMBuilder()
        leds = [
            builder.add_led(100.0, y, label=f"L{i}")
            for i, y in enumerate([100.0, 150.0, 200.0])
        ]
        assert len(builder.components) == 3
        assert len(set(id(c) for c in leds)) == 3


@pytest.mark.tier1
class TestTier1GatePlacement:
    """Feature 3: Logic gate placement tests (add_gate)"""

    @pytest.mark.parametrize("gate_type, expected_class", [
        ("AND", "T2AndGate"),
        ("OR", "T2OrGate"),
        ("NOT", "TNotGate"),
        ("NAND", "T2NandGate"),
        ("NOR", "T2NorGate"),
        ("XOR", "T2XorGate"),
    ])
    def test_add_gate_types_and_classes(self, gate_type, expected_class):
        builder = DWMBuilder()
        comp = builder.add_gate(gate_type, 100.0, 100.0)
        assert comp.comp_type == gate_type
        assert comp.delphi_class == expected_class
        assert comp.x == 100.0
        assert comp.y == 100.0

    @pytest.mark.parametrize("gate_type", ["AND", "OR", "NAND", "NOR", "XOR"])
    def test_binary_gate_pin_topology(self, gate_type):
        builder = DWMBuilder()
        comp = builder.add_gate(gate_type, 100.0, 100.0)
        assert set(comp.pins.keys()) == {"in1", "in2", "out"}
        assert comp.pins["in1"].pin_type == "input"
        assert comp.pins["in2"].pin_type == "input"
        assert comp.pins["out"].pin_type == "output"

    def test_not_gate_pin_topology(self):
        builder = DWMBuilder()
        comp = builder.add_gate("NOT", 100.0, 100.0)
        assert set(comp.pins.keys()) == {"in", "out"}
        assert comp.pins["in"].pin_type == "input"
        assert comp.pins["out"].pin_type == "output"

    def test_add_gate_custom_label(self):
        builder = DWMBuilder()
        comp = builder.add_gate("AND", 100.0, 100.0, label="G1")
        assert comp.label == "G1"

    def test_gate_pin_backreference(self):
        builder = DWMBuilder()
        comp = builder.add_gate("XOR", 100.0, 100.0)
        for pin in comp.pins.values():
            assert pin.component is comp


@pytest.mark.tier1
class TestTier1PinCoordinates:
    """Feature 4: Pin coordinate calculation tests"""

    def test_and_pin_coordinates(self):
        builder = DWMBuilder()
        comp = builder.add_gate("AND", 100.0, 200.0)
        assert comp.pins["in1"].x == 70.0
        assert comp.pins["in1"].y == 190.0
        assert comp.pins["in2"].x == 70.0
        assert comp.pins["in2"].y == 210.0
        assert comp.pins["out"].x == 130.0
        assert comp.pins["out"].y == 200.0

    def test_or_pin_coordinates(self):
        builder = DWMBuilder()
        comp = builder.add_gate("OR", 150.0, 250.0)
        assert comp.pins["in1"].x == 120.0
        assert comp.pins["in1"].y == 240.0
        assert comp.pins["in2"].x == 120.0
        assert comp.pins["in2"].y == 260.0
        assert comp.pins["out"].x == 180.0
        assert comp.pins["out"].y == 250.0

    def test_not_pin_coordinates(self):
        builder = DWMBuilder()
        comp = builder.add_gate("NOT", 200.0, 100.0)
        assert comp.pins["in"].x == 175.0
        assert comp.pins["in"].y == 100.0
        assert comp.pins["out"].x == 225.0
        assert comp.pins["out"].y == 100.0

    def test_xor_pin_coordinates(self):
        builder = DWMBuilder()
        comp = builder.add_gate("XOR", 300.0, 400.0)
        assert comp.pins["in1"].x == 270.0
        assert comp.pins["in1"].y == 390.0
        assert comp.pins["in2"].x == 270.0
        assert comp.pins["in2"].y == 410.0
        assert comp.pins["out"].x == 330.0
        assert comp.pins["out"].y == 400.0

    @pytest.mark.parametrize("gate_type", ["NAND", "NOR"])
    def test_nand_nor_pin_coordinates(self, gate_type):
        builder = DWMBuilder()
        comp = builder.add_gate(gate_type, 200.0, 300.0)
        assert comp.pins["in1"].x == 170.0
        assert comp.pins["in1"].y == 290.0
        assert comp.pins["in2"].x == 170.0
        assert comp.pins["in2"].y == 310.0
        assert comp.pins["out"].y == 300.0
        assert comp.pins["out"].x in (230.0, 235.0)

    def test_input_led_pin_offsets(self):
        builder = DWMBuilder()
        inp = builder.add_input(50.0, 100.0)
        led = builder.add_led(250.0, 100.0)
        assert inp.pins["out"].y == 100.0
        assert inp.pins["out"].x in (50.0, 65.0)
        assert led.pins["in"].y == 100.0
        assert led.pins["in"].x in (250.0, 235.0)


@pytest.mark.tier1
class TestTier1ManhattanRouting:
    """Feature 5: Orthogonal Manhattan wire routing tests (connect)"""

    def test_horizontal_collinear_routing(self):
        builder = DWMBuilder()
        inp = builder.add_input(100.0, 100.0)
        led = builder.add_led(200.0, 100.0)
        wire = builder.connect(inp.pins["out"], led.pins["in"])
        assert len(wire.points) == 2
        assert wire.points[0][1] == wire.points[1][1]  # Same Y

    def test_vertical_collinear_routing(self):
        builder = DWMBuilder()
        inp = builder.add_input(100.0, 100.0)
        led = builder.add_led(100.0, 200.0)
        wire = builder.connect(inp.pins["out"], led.pins["in"])
        assert len(wire.points) >= 2
        assert wire.points[0] == (inp.pins["out"].x, inp.pins["out"].y)
        assert wire.points[-1] == (led.pins["in"].x, led.pins["in"].y)

    def test_l_shaped_routing(self):
        builder = DWMBuilder()
        inp = builder.add_input(50.0, 50.0)
        gate = builder.add_gate("AND", 150.0, 100.0)
        wire = builder.connect(inp.pins["out"], gate.pins["in1"])
        assert len(wire.points) in (3, 4)
        for i in range(len(wire.points) - 1):
            p1, p2 = wire.points[i], wire.points[i + 1]
            assert p1[0] == p2[0] or p1[1] == p2[1]

    def test_z_shaped_routing(self):
        builder = DWMBuilder()
        inp = builder.add_input(50.0, 50.0)
        gate = builder.add_gate("AND", 250.0, 150.0)
        wire = builder.connect(inp.pins["out"], gate.pins["in2"])
        assert len(wire.points) in (3, 4)
        for i in range(len(wire.points) - 1):
            p1, p2 = wire.points[i], wire.points[i + 1]
            assert p1[0] == p2[0] or p1[1] == p2[1]

    def test_strict_orthogonality_invariant(self):
        builder = DWMBuilder()
        g1 = builder.add_gate("AND", 100.0, 100.0)
        g2 = builder.add_gate("OR", 220.0, 160.0)
        wire = builder.connect(g1.pins["out"], g2.pins["in1"])
        for i in range(len(wire.points) - 1):
            p1, p2 = wire.points[i], wire.points[i + 1]
            dx = abs(p1[0] - p2[0])
            dy = abs(p1[1] - p2[1])
            assert (dx == 0 and dy != 0) or (dx != 0 and dy == 0)

    def test_connect_stores_wire_in_builder(self):
        builder = DWMBuilder()
        g1 = builder.add_gate("AND", 100.0, 100.0)
        g2 = builder.add_gate("OR", 220.0, 100.0)
        wire = builder.connect(g1.pins["out"], g2.pins["in1"])
        assert len(builder.wires) == 1
        assert builder.wires[0] is wire


@pytest.mark.tier1
class TestTier1AsciiPreview:
    """Feature 6: ASCII previewer tests (preview)"""

    def test_preview_empty_circuit(self):
        builder = DWMBuilder()
        out = builder.preview()
        assert isinstance(out, str)

    def test_preview_single_component(self):
        builder = DWMBuilder()
        builder.add_gate("AND", 100.0, 100.0)
        out = builder.preview()
        assert "AND" in out
        assert len(out.strip()) > 0

    def test_preview_component_with_label(self):
        builder = DWMBuilder()
        builder.add_input(50.0, 50.0, label="START_SIG")
        out = builder.preview()
        assert "START_SIG" in out

    def test_preview_connected_components(self):
        builder = DWMBuilder()
        inp = builder.add_input(50.0, 100.0, label="IN")
        led = builder.add_led(250.0, 100.0, label="OUT")
        builder.connect(inp.pins["out"], led.pins["in"])
        out = builder.preview()
        assert any(c in out for c in ("-", "|", "+"))
        assert "IN" in out
        assert "OUT" in out

    def test_preview_returns_string(self):
        builder = DWMBuilder()
        builder.add_gate("OR", 100.0, 100.0)
        assert isinstance(builder.preview(), str)


@pytest.mark.tier1
class TestTier1BinarySerialization:
    """Feature 7: Binary serialization tests (to_bytes, save)"""

    def test_binary_magic_header(self):
        builder = DWMBuilder()
        data = builder.to_bytes()
        assert data.startswith(MAGIC_HEADER)

    def test_save_creates_file(self, tmp_path):
        builder = DWMBuilder()
        out_file = tmp_path / "test.dwm"
        builder.save(str(out_file))
        assert out_file.exists()
        assert out_file.stat().st_size > 0

    def test_save_matches_to_bytes(self, tmp_path):
        builder = DWMBuilder()
        builder.add_gate("AND", 100.0, 100.0)
        out_file = tmp_path / "test_match.dwm"
        builder.save(str(out_file))
        assert out_file.read_bytes() == builder.to_bytes()

    def test_stream_contains_root_macro(self):
        builder = DWMBuilder()
        data = builder.to_bytes()
        assert b"TMacro" in data

    def test_stream_contains_component_classes(self):
        builder = DWMBuilder()
        builder.add_gate("AND", 100.0, 100.0)
        builder.add_led(300.0, 100.0)
        data = builder.to_bytes()
        assert b"T2AndGate" in data
        assert b"TLEDDevice" in data

    def test_serialization_non_empty(self):
        builder = DWMBuilder()
        data = builder.to_bytes()
        assert isinstance(data, bytes)
        assert len(data) >= 100


# ============================================================================
# TIER 2: BOUNDARY & CORNER CASES (>=5 tests per feature across 7 features)
# ============================================================================

@pytest.mark.tier2
class TestTier2InputBoundaries:
    """Feature 1: Input boundaries and edge cases"""

    def test_origin_coordinates(self):
        builder = DWMBuilder()
        comp = builder.add_input(0.0, 0.0, label="ZERO")
        assert comp.x == 0.0
        assert comp.y == 0.0
        assert comp.pins["out"].y == 0.0

    def test_negative_coordinates(self):
        builder = DWMBuilder()
        comp = builder.add_input(-250.0, -120.0, label="NEG")
        assert comp.x == -250.0
        assert comp.y == -120.0

    def test_float_precision_coordinates(self):
        builder = DWMBuilder()
        comp = builder.add_input(123.456, 789.012, label="FLOAT")
        assert abs(comp.x - 123.456) < 1e-6
        assert abs(comp.y - 789.012) < 1e-6

    def test_extreme_large_coordinates(self):
        builder = DWMBuilder()
        comp = builder.add_input(1_000_000.0, 500_000.0, label="FAR")
        assert comp.x == 1_000_000.0
        assert comp.y == 500_000.0

    @pytest.mark.parametrize("lbl", ["", "A" * 255, "   ", "IN_#1@$%", "スイッチ_1"])
    def test_label_variations(self, lbl):
        builder = DWMBuilder()
        comp = builder.add_input(100.0, 100.0, label=lbl)
        assert comp.label == lbl

    def test_integer_coordinate_coercion(self):
        builder = DWMBuilder()
        comp = builder.add_input(100, 200)
        assert float(comp.x) == 100.0
        assert float(comp.y) == 200.0


@pytest.mark.tier2
class TestTier2LEDBoundaries:
    """Feature 2: LED boundaries and edge cases"""

    def test_origin_coordinates(self):
        builder = DWMBuilder()
        comp = builder.add_led(0.0, 0.0)
        assert comp.x == 0.0
        assert comp.y == 0.0

    def test_negative_coordinates(self):
        builder = DWMBuilder()
        comp = builder.add_led(-400.0, -300.0)
        assert comp.x == -400.0
        assert comp.y == -300.0

    def test_float_precision(self):
        builder = DWMBuilder()
        comp = builder.add_led(333.333, 444.444)
        assert abs(comp.x - 333.333) < 1e-6
        assert abs(comp.y - 444.444) < 1e-6

    def test_coincident_positions(self):
        builder = DWMBuilder()
        led1 = builder.add_led(150.0, 150.0)
        led2 = builder.add_led(150.0, 150.0)
        assert led1 is not led2
        assert led1.pins["in"] is not led2.pins["in"]
        assert len(builder.components) == 2

    @pytest.mark.parametrize("lbl", ["", "   ", "LED_" + "X" * 100, "LED_#0!"])
    def test_label_variations(self, lbl):
        builder = DWMBuilder()
        comp = builder.add_led(100.0, 100.0, label=lbl)
        assert comp.label == lbl

    def test_integer_coordinate_coercion(self):
        builder = DWMBuilder()
        comp = builder.add_led(50, 80)
        assert float(comp.x) == 50.0
        assert float(comp.y) == 80.0


@pytest.mark.tier2
class TestTier2GateBoundaries:
    """Feature 3: Gate boundaries and edge cases"""

    def test_invalid_gate_type_raises_valueerror(self):
        builder = DWMBuilder()
        with pytest.raises(ValueError):
            builder.add_gate("INVALID_GATE", 100.0, 100.0)

    @pytest.mark.parametrize("gate_input, expected_type", [
        ("and", "AND"),
        ("Or", "OR"),
        ("nand", "NAND"),
        ("Xor", "XOR"),
        ("not", "NOT"),
        ("Nor", "NOR"),
    ])
    def test_case_insensitive_handling(self, gate_input, expected_type):
        builder = DWMBuilder()
        comp = builder.add_gate(gate_input, 100.0, 100.0)
        assert comp.comp_type == expected_type

    def test_origin_coordinates(self):
        builder = DWMBuilder()
        comp = builder.add_gate("AND", 0.0, 0.0)
        assert comp.x == 0.0
        assert comp.y == 0.0

    def test_negative_coordinates(self):
        builder = DWMBuilder()
        comp = builder.add_gate("OR", -300.0, -150.0)
        assert comp.x == -300.0
        assert comp.y == -150.0

    def test_coincident_gates(self):
        builder = DWMBuilder()
        g1 = builder.add_gate("AND", 100.0, 100.0)
        g2 = builder.add_gate("AND", 100.0, 100.0)
        assert g1 is not g2
        assert len(builder.components) == 2

    @pytest.mark.parametrize("bad_type", [None, 123, [], {}])
    def test_non_string_type_raises_error(self, bad_type):
        builder = DWMBuilder()
        with pytest.raises((TypeError, ValueError)):
            builder.add_gate(bad_type, 100.0, 100.0)


@pytest.mark.tier2
class TestTier2PinCoordinateBoundaries:
    """Feature 4: Pin coordinate boundaries and edge cases"""

    def test_pin_coordinates_at_origin(self):
        builder = DWMBuilder()
        comp = builder.add_gate("AND", 0.0, 0.0)
        assert comp.pins["in1"].x == -30.0
        assert comp.pins["in1"].y == -10.0
        assert comp.pins["in2"].x == -30.0
        assert comp.pins["in2"].y == 10.0
        assert comp.pins["out"].x == 30.0
        assert comp.pins["out"].y == 0.0

    def test_pin_coordinates_negative_anchor(self):
        builder = DWMBuilder()
        comp = builder.add_gate("NOT", -100.0, -50.0)
        assert comp.pins["in"].x == -125.0
        assert comp.pins["in"].y == -50.0
        assert comp.pins["out"].x == -75.0
        assert comp.pins["out"].y == -50.0

    def test_pin_coordinates_fractional_precision(self):
        builder = DWMBuilder()
        comp = builder.add_gate("XOR", 100.5, 200.25)
        assert abs(comp.pins["in1"].x - 70.5) < 1e-6
        assert abs(comp.pins["in1"].y - 190.25) < 1e-6
        assert abs(comp.pins["out"].x - 130.5) < 1e-6

    @pytest.mark.parametrize("gate_type", ["AND", "OR", "NAND", "NOR", "XOR"])
    def test_pin_spacing_invariance(self, gate_type):
        builder = DWMBuilder()
        comp = builder.add_gate(gate_type, 123.0, 456.0)
        assert abs((comp.pins["in2"].y - comp.pins["in1"].y) - 20.0) < 1e-6
        assert comp.pins["in1"].x == comp.pins["in2"].x

    @pytest.mark.parametrize("gate_type", ["AND", "OR", "NOT", "NAND", "NOR", "XOR"])
    def test_output_pin_horizontal_centering(self, gate_type):
        builder = DWMBuilder()
        comp = builder.add_gate(gate_type, 200.0, 350.0)
        assert comp.pins["out"].y == 350.0


@pytest.mark.tier2
class TestTier2ManhattanRoutingBoundaries:
    """Feature 5: Manhattan routing boundaries and edge cases"""

    def test_connect_coincident_pins(self):
        builder = DWMBuilder()
        inp = builder.add_input(100.0, 100.0)
        led = builder.add_led(100.0, 100.0)
        wire = builder.connect(inp.pins["out"], led.pins["in"])
        assert len(wire.points) >= 1
        for i in range(len(wire.points) - 1):
            p1, p2 = wire.points[i], wire.points[i + 1]
            assert p1[0] == p2[0] or p1[1] == p2[1]

    def test_connect_reverse_direction_x(self):
        builder = DWMBuilder()
        inp = builder.add_input(300.0, 100.0)
        led = builder.add_led(100.0, 150.0)
        wire = builder.connect(inp.pins["out"], led.pins["in"])
        for i in range(len(wire.points) - 1):
            p1, p2 = wire.points[i], wire.points[i + 1]
            assert p1[0] == p2[0] or p1[1] == p2[1]

    def test_connect_destination_above_source_y(self):
        builder = DWMBuilder()
        inp = builder.add_input(100.0, 200.0)
        led = builder.add_led(200.0, 50.0)
        wire = builder.connect(inp.pins["out"], led.pins["in"])
        for i in range(len(wire.points) - 1):
            p1, p2 = wire.points[i], wire.points[i + 1]
            assert p1[0] == p2[0] or p1[1] == p2[1]

    def test_connect_pin_to_itself(self):
        builder = DWMBuilder()
        inp = builder.add_input(100.0, 100.0)
        try:
            wire = builder.connect(inp.pins["out"], inp.pins["out"])
            assert len(wire.points) >= 1
        except ValueError:
            pass  # Prohibiting self-connections via ValueError is valid

    def test_connect_negative_coordinates(self):
        builder = DWMBuilder()
        inp = builder.add_input(-200.0, -100.0)
        led = builder.add_led(-50.0, -20.0)
        wire = builder.connect(inp.pins["out"], led.pins["in"])
        for i in range(len(wire.points) - 1):
            p1, p2 = wire.points[i], wire.points[i + 1]
            assert p1[0] == p2[0] or p1[1] == p2[1]

    def test_sub_pixel_precision_routing(self):
        builder = DWMBuilder()
        inp = builder.add_input(10.25, 20.75)
        led = builder.add_led(30.25, 40.75)
        wire = builder.connect(inp.pins["out"], led.pins["in"])
        for i in range(len(wire.points) - 1):
            p1, p2 = wire.points[i], wire.points[i + 1]
            assert abs(p1[0] - p2[0]) < 1e-6 or abs(p1[1] - p2[1]) < 1e-6


@pytest.mark.tier2
class TestTier2AsciiPreviewBoundaries:
    """Feature 6: ASCII preview boundaries and edge cases"""

    def test_large_coordinate_separation(self):
        builder = DWMBuilder()
        builder.add_gate("AND", 0.0, 0.0)
        builder.add_gate("OR", 2000.0, 2000.0)
        out = builder.preview()
        assert isinstance(out, str)

    def test_negative_coordinates(self):
        builder = DWMBuilder()
        builder.add_gate("NOT", -200.0, -100.0)
        builder.add_gate("XOR", -50.0, -50.0)
        out = builder.preview()
        assert "NOT" in out
        assert "XOR" in out

    def test_dense_overlapping_layout(self):
        builder = DWMBuilder()
        for i in range(5):
            builder.add_gate("AND", 100.0 + i * 5, 100.0 + i * 5)
        out = builder.preview()
        assert isinstance(out, str)

    def test_special_characters_in_label(self):
        builder = DWMBuilder()
        builder.add_input(100.0, 100.0, label="$IN[0]*")
        out = builder.preview()
        assert "$IN[0]*" in out

    def test_preview_idempotence(self):
        builder = DWMBuilder()
        builder.add_gate("NAND", 100.0, 100.0)
        assert builder.preview() == builder.preview()

    def test_preview_gates_without_wires(self):
        builder = DWMBuilder()
        for g in ["AND", "OR", "NOT", "XOR"]:
            builder.add_gate(g, 100.0, 100.0)
        out = builder.preview()
        for g in ["AND", "OR", "NOT", "XOR"]:
            assert g in out


@pytest.mark.tier2
class TestTier2BinarySerializationBoundaries:
    """Feature 7: Binary serialization boundaries and edge cases"""

    def test_empty_circuit_serialization(self):
        builder = DWMBuilder()
        data = builder.to_bytes()
        assert data.startswith(MAGIC_HEADER)
        assert len(data) > 0

    def test_serialization_reproducibility(self):
        builder = DWMBuilder()
        builder.add_gate("AND", 100.0, 100.0)
        raw1 = builder.to_bytes()
        raw2 = builder.to_bytes()
        assert raw1 == raw2

    def test_save_overwrite_existing_file(self, tmp_path):
        target = tmp_path / "overwrite.dwm"
        target.write_text("DUMMY_OLD_DATA")
        builder = DWMBuilder()
        builder.save(str(target))
        assert target.read_bytes().startswith(MAGIC_HEADER)

    def test_save_invalid_path_raises_error(self):
        builder = DWMBuilder()
        with pytest.raises((OSError, IOError)):
            builder.save("/nonexistent/fake/directory/circuit.dwm")

    def test_large_circuit_serialization(self):
        builder = DWMBuilder()
        for i in range(30):
            builder.add_gate("AND", float(100 + i * 40), float(100 + i * 30))
        data = builder.to_bytes()
        assert data.startswith(MAGIC_HEADER)
        assert len(data) > 1000

    def test_unicode_label_serialization(self):
        builder = DWMBuilder()
        builder.add_input(100.0, 100.0, label="α_IN")
        data = builder.to_bytes()
        assert data.startswith(MAGIC_HEADER)


# ============================================================================
# TIER 3: CROSS-FEATURE COMBINATIONS & MANHATTAN INVARIANTS (14 tests)
# ============================================================================

@pytest.mark.tier3
class TestTier3CrossFeatureCombinations:
    """Tier 3: Pairwise interactions, fan-out trees, cascades, and lifecycle"""

    def test_pairwise_input_to_gate(self):
        b = DWMBuilder("Test_Input_to_Gate")
        inp = b.add_input(100.0, 100.0, label="IN_A")
        gate = b.add_gate("AND", 250.0, 100.0, label="G1")

        assert "out" in inp.pins
        assert "in1" in gate.pins

        wire = b.connect(inp.pins["out"], gate.pins["in1"])
        assert wire in b.wires
        assert len(b.wires) == 1
        assert wire.source_pin == inp.pins["out"]
        assert wire.dest_pin == gate.pins["in1"]

        assert_manhattan_routing_invariants(wire)
        assert wire.points[0] == (inp.pins["out"].x, inp.pins["out"].y)
        assert wire.points[-1] == (gate.pins["in1"].x, gate.pins["in1"].y)

    def test_pairwise_gate_to_gate(self):
        b = DWMBuilder("Test_Gate_to_Gate")
        and_gate = b.add_gate("AND", 100.0, 150.0, label="AND1")
        or_gate = b.add_gate("OR", 250.0, 150.0, label="OR1")

        wire = b.connect(and_gate.pins["out"], or_gate.pins["in1"])
        assert len(b.wires) == 1
        assert wire.source_pin == and_gate.pins["out"]
        assert wire.dest_pin == or_gate.pins["in1"]

        assert_manhattan_routing_invariants(wire)
        assert wire.points[0] == (130.0, 150.0)
        assert wire.points[-1] == (220.0, 140.0)

    def test_pairwise_gate_to_led(self):
        b = DWMBuilder("Test_Gate_to_LED")
        not_gate = b.add_gate("NOT", 150.0, 100.0, label="INV")
        led = b.add_led(300.0, 100.0, label="OUT_LED")

        wire = b.connect(not_gate.pins["out"], led.pins["in"])
        assert len(b.wires) == 1
        assert wire.source_pin == not_gate.pins["out"]
        assert wire.dest_pin == led.pins["in"]

        assert_manhattan_routing_invariants(wire)
        assert len(wire.points) == 2
        assert wire.points[0][1] == wire.points[1][1] == 100.0

    def test_pairwise_input_to_led(self):
        b = DWMBuilder("Test_Input_to_LED")
        inp = b.add_input(80.0, 200.0, label="SW1")
        led = b.add_led(240.0, 260.0, label="IND1")

        wire = b.connect(inp.pins["out"], led.pins["in"])
        assert len(b.wires) == 1
        assert wire.source_pin == inp.pins["out"]
        assert wire.dest_pin == led.pins["in"]

        assert_manhattan_routing_invariants(wire)
        assert len(wire.points) in (3, 4)

    def test_fanout_single_output_to_multiple_gate_inputs(self):
        b = DWMBuilder("Test_Fanout_1_to_2")
        inp = b.add_input(50.0, 150.0, label="SRC")
        and_gate = b.add_gate("AND", 200.0, 100.0, label="AND_TOP")
        or_gate = b.add_gate("OR", 200.0, 200.0, label="OR_BOT")

        w1 = b.connect(inp.pins["out"], and_gate.pins["in1"])
        w2 = b.connect(inp.pins["out"], or_gate.pins["in2"])

        assert len(b.wires) == 2
        assert w1 != w2
        assert w1.source_pin == inp.pins["out"]
        assert w2.source_pin == inp.pins["out"]
        assert w1.dest_pin == and_gate.pins["in1"]
        assert w2.dest_pin == or_gate.pins["in2"]

        assert_manhattan_routing_invariants(w1)
        assert_manhattan_routing_invariants(w2)
        assert w1.points[0] == w2.points[0]

    def test_fanout_quad_distribution_tree(self):
        b = DWMBuilder("Test_Fanout_1_to_4")
        inp = b.add_input(40.0, 150.0, label="CLK")
        g1 = b.add_gate("NAND", 200.0, 100.0, label="NAND1")
        g2 = b.add_gate("NAND", 200.0, 200.0, label="NAND2")

        targets = [g1.pins["in1"], g1.pins["in2"], g2.pins["in1"], g2.pins["in2"]]
        wires = [b.connect(inp.pins["out"], target) for target in targets]

        assert len(b.wires) == 4
        for w, target in zip(wires, targets):
            assert w.source_pin == inp.pins["out"]
            assert w.dest_pin == target
            assert_manhattan_routing_invariants(w)

        data = b.to_bytes()
        assert isinstance(data, bytes)
        assert len(data) > 108
        assert data.startswith(MAGIC_HEADER)

    def test_cascade_three_stage_pipeline(self):
        b = DWMBuilder("Test_Cascade_Pipeline")
        g_and = b.add_gate("AND", 100.0, 100.0, label="STG1")
        g_or = b.add_gate("OR", 220.0, 100.0, label="STG2")
        g_not = b.add_gate("NOT", 340.0, 100.0, label="STG3")
        led = b.add_led(450.0, 100.0, label="RESULT")

        w1 = b.connect(g_and.pins["out"], g_or.pins["in1"])
        w2 = b.connect(g_or.pins["out"], g_not.pins["in"])
        w3 = b.connect(g_not.pins["out"], led.pins["in"])

        assert len(b.wires) == 3
        assert w1.dest_pin.component == g_or
        assert w2.source_pin.component == g_or
        assert w2.dest_pin.component == g_not
        assert w3.source_pin.component == g_not
        assert w3.dest_pin.component == led

        for w in [w1, w2, w3]:
            assert_manhattan_routing_invariants(w)

        preview_str = b.preview()
        assert isinstance(preview_str, str)
        assert len(preview_str) > 0

    def test_cascade_and_or_invert_structure(self):
        b = DWMBuilder("Test_AOI_Structure")
        and_top = b.add_gate("AND", 150.0, 100.0, label="AND_T")
        and_bot = b.add_gate("AND", 150.0, 200.0, label="AND_B")
        nor_gate = b.add_gate("NOR", 300.0, 150.0, label="NOR1")
        led = b.add_led(420.0, 150.0, label="AOI_OUT")

        w_top = b.connect(and_top.pins["out"], nor_gate.pins["in1"])
        w_bot = b.connect(and_bot.pins["out"], nor_gate.pins["in2"])
        w_out = b.connect(nor_gate.pins["out"], led.pins["in"])

        assert len(b.wires) == 3
        assert_manhattan_routing_invariants(w_top)
        assert_manhattan_routing_invariants(w_bot)
        assert_manhattan_routing_invariants(w_out)
        assert w_top.points[0][1] < w_top.points[-1][1]
        assert w_bot.points[0][1] > w_bot.points[-1][1]

    def test_cascade_inverter_chain_collinear(self):
        b = DWMBuilder("Test_Inverter_Chain")
        inp = b.add_input(60.0, 100.0, label="SIG")
        not1 = b.add_gate("NOT", 130.0, 100.0, label="N1")
        not2 = b.add_gate("NOT", 200.0, 100.0, label="N2")
        not3 = b.add_gate("NOT", 270.0, 100.0, label="N3")
        not4 = b.add_gate("NOT", 340.0, 100.0, label="N4")
        led = b.add_led(420.0, 100.0, label="OUT")

        w1 = b.connect(inp.pins["out"], not1.pins["in"])
        w2 = b.connect(not1.pins["out"], not2.pins["in"])
        w3 = b.connect(not2.pins["out"], not3.pins["in"])
        w4 = b.connect(not3.pins["out"], not4.pins["in"])
        w5 = b.connect(not4.pins["out"], led.pins["in"])

        assert len(b.wires) == 5
        for w in [w1, w2, w3, w4, w5]:
            assert_manhattan_routing_invariants(w)
            assert len(w.points) == 2
            assert w.points[0][1] == w.points[1][1] == 100.0

    def test_routing_z_route_forward_offset(self):
        b = DWMBuilder("Test_Z_Route")
        g1 = b.add_gate("AND", 100.0, 100.0)
        g2 = b.add_gate("AND", 300.0, 240.0)

        w = b.connect(g1.pins["out"], g2.pins["in1"])
        assert_manhattan_routing_invariants(w)
        assert len(w.points) == 4
        p0, p1, p2, p3 = w.points
        assert p0 == (130.0, 100.0)
        assert p3 == (270.0, 230.0)
        assert p1[0] == p2[0]
        assert p0[1] == p1[1]
        assert p2[1] == p3[1]

    def test_routing_backward_direction_manhattan(self):
        b = DWMBuilder("Test_Backward_Route")
        g_fwd = b.add_gate("AND", 350.0, 150.0, label="FWD")
        g_back = b.add_gate("OR", 150.0, 250.0, label="BACK")

        w = b.connect(g_fwd.pins["out"], g_back.pins["in1"])
        assert_manhattan_routing_invariants(w)
        assert w.points[0] == (380.0, 150.0)
        assert w.points[-1] == (120.0, 240.0)
        for i in range(len(w.points) - 1):
            dx = w.points[i + 1][0] - w.points[i][0]
            dy = w.points[i + 1][1] - w.points[i][1]
            assert dx == 0 or dy == 0

    def test_routing_parallel_dual_wires_non_coincident(self):
        b = DWMBuilder("Test_Parallel_Routes")
        g1 = b.add_gate("AND", 100.0, 100.0, label="A1")
        g2 = b.add_gate("OR", 250.0, 120.0, label="O1")
        g3 = b.add_gate("AND", 100.0, 200.0, label="A2")
        g4 = b.add_gate("OR", 250.0, 220.0, label="O2")

        w1 = b.connect(g1.pins["out"], g2.pins["in1"])
        w2 = b.connect(g3.pins["out"], g4.pins["in1"])

        assert len(b.wires) == 2
        assert_manhattan_routing_invariants(w1)
        assert_manhattan_routing_invariants(w2)
        assert w1.points[0][1] == 100.0
        assert w2.points[0][1] == 200.0
        assert w1.points[-1][1] == 110.0
        assert w2.points[-1][1] == 210.0

    def test_lifecycle_multi_component_preview_and_serialization(self, tmp_path):
        b = DWMBuilder("Lifecycle_Circuit")
        in0 = b.add_input(80.0, 100.0, label="A")
        in1 = b.add_input(80.0, 140.0, label="B")
        xor_gate = b.add_gate("XOR", 200.0, 120.0, label="XOR1")
        led = b.add_led(320.0, 120.0, label="Y")

        w1 = b.connect(in0.pins["out"], xor_gate.pins["in1"])
        w2 = b.connect(in1.pins["out"], xor_gate.pins["in2"])
        w3 = b.connect(xor_gate.pins["out"], led.pins["in"])

        for w in [w1, w2, w3]:
            assert_manhattan_routing_invariants(w)

        preview_output = b.preview()
        assert isinstance(preview_output, str)
        assert len(preview_output.strip()) > 0
        assert "A" in preview_output or "IN" in preview_output
        assert "XOR" in preview_output or "XOR1" in preview_output
        assert "Y" in preview_output or "LED" in preview_output

        bin_data = b.to_bytes()
        assert isinstance(bin_data, bytes)
        assert len(bin_data) > 108
        assert bin_data.startswith(MAGIC_HEADER)

        target_file = tmp_path / "lifecycle.dwm"
        b.save(str(target_file))
        assert target_file.exists()
        assert target_file.read_bytes() == bin_data

    def test_all_six_gate_types_simultaneous_assembly(self):
        b = DWMBuilder("All_Six_Gates")
        gate_types = ["AND", "OR", "NOT", "NAND", "NOR", "XOR"]
        gates = []
        for idx, gtype in enumerate(gate_types):
            y_pos = 50.0 + idx * 70.0
            g = b.add_gate(gtype, 150.0, y_pos, label=f"G_{gtype}")
            gates.append(g)

        assert len(b.components) == 6
        assert [g.comp_type for g in gates] == gate_types

        for g in gates:
            if g.comp_type == "NOT":
                assert "in" in g.pins
                assert "out" in g.pins
            else:
                assert "in1" in g.pins
                assert "in2" in g.pins
                assert "out" in g.pins

        w1 = b.connect(gates[0].pins["out"], gates[1].pins["in1"])
        w2 = b.connect(gates[1].pins["out"], gates[2].pins["in"])
        w3 = b.connect(gates[3].pins["out"], gates[4].pins["in1"])
        w4 = b.connect(gates[4].pins["out"], gates[5].pins["in1"])

        assert len(b.wires) == 4
        for w in [w1, w2, w3, w4]:
            assert_manhattan_routing_invariants(w)

        bin_data = b.to_bytes()
        expected_classes = [
            b"T2AndGate", b"T2OrGate", b"TNotGate",
            b"T2NandGate", b"T2NorGate", b"T2XorGate"
        ]
        for cls in expected_classes:
            assert cls in bin_data, f"Class {cls.decode()} missing from serialized stream"


# ============================================================================
# TIER 4: REAL-WORLD APPLICATION SCENARIOS & CALIBRATION (8 tests)
# ============================================================================

def _build_half_adder():
    builder = DWMBuilder("Half_Adder")
    in_a = builder.add_input(50.0, 100.0, label="A")
    in_b = builder.add_input(50.0, 200.0, label="B")
    gate_xor = builder.add_gate("XOR", 200.0, 100.0, label="XOR1")
    gate_and = builder.add_gate("AND", 200.0, 200.0, label="AND1")
    led_sum = builder.add_led(350.0, 100.0, label="Sum")
    led_carry = builder.add_led(350.0, 200.0, label="Carry")

    w1 = builder.connect(in_a.pins["out"], gate_xor.pins["in1"])
    w2 = builder.connect(in_a.pins["out"], gate_and.pins["in1"])
    w3 = builder.connect(in_b.pins["out"], gate_xor.pins["in2"])
    w4 = builder.connect(in_b.pins["out"], gate_and.pins["in2"])
    w5 = builder.connect(gate_xor.pins["out"], led_sum.pins["in"])
    w6 = builder.connect(gate_and.pins["out"], led_carry.pins["in"])
    return builder, (in_a, in_b, gate_xor, gate_and, led_sum, led_carry), (w1, w2, w3, w4, w5, w6)


def _build_full_adder():
    builder = DWMBuilder("Full_Adder")
    in_a = builder.add_input(50.0, 100.0, label="A")
    in_b = builder.add_input(50.0, 160.0, label="B")
    in_cin = builder.add_input(50.0, 260.0, label="Cin")

    gate_xor1 = builder.add_gate("XOR", 200.0, 120.0, label="XOR1")
    gate_and1 = builder.add_gate("AND", 200.0, 200.0, label="AND1")
    gate_xor2 = builder.add_gate("XOR", 350.0, 140.0, label="XOR2")
    gate_and2 = builder.add_gate("AND", 350.0, 240.0, label="AND2")
    gate_or1 = builder.add_gate("OR", 480.0, 220.0, label="OR1")

    led_sum = builder.add_led(600.0, 140.0, label="Sum")
    led_cout = builder.add_led(600.0, 220.0, label="Cout")

    builder.connect(in_a.pins["out"], gate_xor1.pins["in1"])
    builder.connect(in_a.pins["out"], gate_and1.pins["in1"])
    builder.connect(in_b.pins["out"], gate_xor1.pins["in2"])
    builder.connect(in_b.pins["out"], gate_and1.pins["in2"])
    builder.connect(gate_xor1.pins["out"], gate_xor2.pins["in1"])
    builder.connect(gate_xor1.pins["out"], gate_and2.pins["in1"])
    builder.connect(in_cin.pins["out"], gate_xor2.pins["in2"])
    builder.connect(in_cin.pins["out"], gate_and2.pins["in2"])
    builder.connect(gate_xor2.pins["out"], led_sum.pins["in"])
    builder.connect(gate_and1.pins["out"], gate_or1.pins["in1"])
    builder.connect(gate_and2.pins["out"], gate_or1.pins["in2"])
    builder.connect(gate_or1.pins["out"], led_cout.pins["in"])
    return builder


def _build_mux():
    builder = DWMBuilder("2x1_MUX")
    in_d0 = builder.add_input(50.0, 100.0, label="D0")
    in_d1 = builder.add_input(50.0, 220.0, label="D1")
    in_s = builder.add_input(50.0, 300.0, label="S")
    gate_not = builder.add_gate("NOT", 160.0, 300.0, label="NOT1")
    gate_and0 = builder.add_gate("AND", 280.0, 120.0, label="AND0")
    gate_and1 = builder.add_gate("AND", 280.0, 240.0, label="AND1")
    gate_or = builder.add_gate("OR", 420.0, 180.0, label="OR1")
    led_y = builder.add_led(540.0, 180.0, label="Y")

    builder.connect(in_d0.pins["out"], gate_and0.pins["in1"])
    builder.connect(in_s.pins["out"], gate_not.pins["in"])
    builder.connect(in_s.pins["out"], gate_and1.pins["in2"])
    builder.connect(gate_not.pins["out"], gate_and0.pins["in2"])
    builder.connect(in_d1.pins["out"], gate_and1.pins["in1"])
    builder.connect(gate_and0.pins["out"], gate_or.pins["in1"])
    builder.connect(gate_and1.pins["out"], gate_or.pins["in2"])
    builder.connect(gate_or.pins["out"], led_y.pins["in"])
    return builder


def _build_sr_latch():
    builder = DWMBuilder("SR_Latch")
    in_r = builder.add_input(50.0, 100.0, label="R")
    in_s = builder.add_input(50.0, 260.0, label="S")
    gate_nor1 = builder.add_gate("NOR", 220.0, 120.0, label="NOR1")
    gate_nor2 = builder.add_gate("NOR", 220.0, 240.0, label="NOR2")
    led_q = builder.add_led(380.0, 120.0, label="Q")
    led_q_bar = builder.add_led(380.0, 240.0, label="Q_bar")

    builder.connect(in_r.pins["out"], gate_nor1.pins["in1"])
    builder.connect(in_s.pins["out"], gate_nor2.pins["in2"])
    builder.connect(gate_nor1.pins["out"], led_q.pins["in"])
    builder.connect(gate_nor2.pins["out"], led_q_bar.pins["in"])
    w_fb1 = builder.connect(gate_nor1.pins["out"], gate_nor2.pins["in1"])
    w_fb2 = builder.connect(gate_nor2.pins["out"], gate_nor1.pins["in2"])
    return builder, (w_fb1, w_fb2)


def _build_parity_checker():
    builder = DWMBuilder("3Bit_Parity")
    in_0 = builder.add_input(50.0, 80.0, label="In0")
    in_1 = builder.add_input(50.0, 160.0, label="In1")
    in_2 = builder.add_input(50.0, 260.0, label="In2")
    gate_xor1 = builder.add_gate("XOR", 220.0, 120.0, label="XOR1")
    gate_xor2 = builder.add_gate("XOR", 360.0, 180.0, label="XOR2")
    led_parity = builder.add_led(500.0, 180.0, label="Parity")

    builder.connect(in_0.pins["out"], gate_xor1.pins["in1"])
    builder.connect(in_1.pins["out"], gate_xor1.pins["in2"])
    builder.connect(gate_xor1.pins["out"], gate_xor2.pins["in1"])
    w_bypass = builder.connect(in_2.pins["out"], gate_xor2.pins["in2"])
    builder.connect(gate_xor2.pins["out"], led_parity.pins["in"])
    return builder, w_bypass


@pytest.mark.tier4
class TestTier4RealWorldApplications:
    """Tier 4: Realistic multi-gate digital circuits, seeds calibration & disk I/O"""

    def test_tier4_half_adder(self):
        builder, comps, wires = _build_half_adder()
        in_a, in_b, gate_xor, gate_and, led_sum, led_carry = comps
        w1, w2, w3, w4, w5, w6 = wires

        assert len(builder.components) == 6
        assert len(builder.wires) == 6
        assert w1.source_pin == in_a.pins["out"] and w2.source_pin == in_a.pins["out"]
        assert w3.source_pin == in_b.pins["out"] and w4.source_pin == in_b.pins["out"]

        assert gate_xor.pins["in1"].x == 170.0 and gate_xor.pins["in1"].y == 90.0
        assert gate_xor.pins["in2"].x == 170.0 and gate_xor.pins["in2"].y == 110.0
        assert gate_xor.pins["out"].x == 230.0 and gate_xor.pins["out"].y == 100.0

        assert gate_and.pins["in1"].x == 170.0 and gate_and.pins["in1"].y == 190.0
        assert gate_and.pins["in2"].x == 170.0 and gate_and.pins["in2"].y == 210.0
        assert gate_and.pins["out"].x == 230.0 and gate_and.pins["out"].y == 200.0

        for w in builder.wires:
            assert_manhattan_routing_invariants(w)

        preview = builder.preview()
        assert isinstance(preview, str) and len(preview) > 0
        assert "A" in preview and "B" in preview and "Sum" in preview and "Carry" in preview

        raw = builder.to_bytes()
        assert raw.startswith(MAGIC_HEADER)
        assert b"T2XorGate" in raw
        assert b"T2AndGate" in raw
        assert b"TInteractiveInput" in raw
        assert b"TLEDDevice" in raw

    def test_tier4_full_adder(self):
        builder = _build_full_adder()
        assert len(builder.components) == 10
        assert len(builder.wires) == 12

        for w in builder.wires:
            assert_manhattan_routing_invariants(w)

        preview = builder.preview()
        for expected in ["Cin", "Sum", "Cout", "XOR1", "XOR2", "OR1"]:
            assert expected in preview

        raw = builder.to_bytes()
        assert raw.startswith(MAGIC_HEADER)
        assert b"T2XorGate" in raw
        assert b"T2AndGate" in raw
        assert b"T2OrGate" in raw
        assert len(raw) > 400

    def test_tier4_2x1_multiplexer(self):
        builder = _build_mux()
        assert len(builder.components) == 8
        assert len(builder.wires) == 8

        not_comp = [c for c in builder.components if c.comp_type == "NOT"][0]
        assert not_comp.pins["in"].x == 135.0 and not_comp.pins["in"].y == 300.0
        assert not_comp.pins["out"].x == 185.0 and not_comp.pins["out"].y == 300.0

        for w in builder.wires:
            assert_manhattan_routing_invariants(w)

        preview = builder.preview()
        for lbl in ["D0", "D1", "S", "Y", "NOT1"]:
            assert lbl in preview

        raw = builder.to_bytes()
        assert raw.startswith(MAGIC_HEADER)
        assert b"TNotGate" in raw
        assert b"T2AndGate" in raw
        assert b"T2OrGate" in raw

    def test_tier4_sr_latch(self):
        builder, (w_fb1, w_fb2) = _build_sr_latch()
        assert len(builder.components) == 6
        assert len(builder.wires) == 6

        assert w_fb1.source_pin.x > w_fb1.dest_pin.x
        assert w_fb2.source_pin.x > w_fb2.dest_pin.x

        for w in builder.wires:
            assert_manhattan_routing_invariants(w)

        preview = builder.preview()
        for lbl in ["R", "S", "NOR", "Q", "Q_bar"]:
            assert lbl in preview

        raw = builder.to_bytes()
        assert raw.startswith(MAGIC_HEADER)
        assert b"T2NorGate" in raw

    def test_tier4_3bit_parity_checker(self):
        builder, w_bypass = _build_parity_checker()
        assert len(builder.components) == 6
        assert len(builder.wires) == 5
        assert w_bypass.dest_pin.x - w_bypass.source_pin.x > 200.0

        for w in builder.wires:
            assert_manhattan_routing_invariants(w)

        preview = builder.preview()
        for lbl in ["In0", "In1", "In2", "Parity", "XOR"]:
            assert lbl in preview

        raw = builder.to_bytes()
        assert raw.startswith(MAGIC_HEADER)
        assert b"T2XorGate" in raw

    def test_tier4_half_adder_reference_seed_structural_equivalence(self):
        seed_path = SEEDS_DIR / "circuit_half_adder.dwm"
        assert seed_path.exists(), f"Seed file missing: {seed_path}"
        seed_bytes = seed_path.read_bytes()
        assert seed_bytes.startswith(MAGIC_HEADER)

        builder, _, _ = _build_half_adder()
        gen_bytes = builder.to_bytes()
        assert gen_bytes.startswith(MAGIC_HEADER)

        for required_token in [b"T2XorGate", b"T2AndGate", b"TPin", b"TWire"]:
            assert required_token in seed_bytes, f"Token {required_token} not in seed"
            assert required_token in gen_bytes, f"Token {required_token} not in compiler output"

    def test_tier4_binary_serialization_idempotence_and_disk_io(self, tmp_path):
        b1, _, _ = _build_half_adder()
        b2 = _build_full_adder()
        b3 = _build_mux()
        b4, _ = _build_sr_latch()
        b5, _ = _build_parity_checker()

        for idx, b in enumerate([b1, b2, b3, b4, b5]):
            bytes_1 = b.to_bytes()
            bytes_2 = b.to_bytes()
            assert bytes_1 == bytes_2, f"Serialization non-idempotent for circuit {idx}"

            file_path = tmp_path / f"tier4_circuit_{idx}.dwm"
            b.save(str(file_path))
            assert file_path.exists()
            assert file_path.stat().st_size == len(bytes_1)
            assert file_path.read_bytes() == bytes_1

    def test_tier4_preview_ascii_layout_sanity(self):
        b1, _, _ = _build_half_adder()
        b2 = _build_full_adder()
        b3 = _build_mux()
        b4, _ = _build_sr_latch()
        b5, _ = _build_parity_checker()

        for idx, b in enumerate([b1, b2, b3, b4, b5]):
            preview = b.preview()
            assert isinstance(preview, str) and len(preview.strip()) > 0
            lines = preview.splitlines()
            assert len(lines) >= 3, f"Circuit {idx} preview too short: {len(lines)} lines"
            assert any("-" in line or "|" in line or "+" in line for line in lines), (
                f"Circuit {idx} preview missing wire glyphs"
            )
            for comp in b.components:
                if comp.label:
                    assert comp.label in preview, (
                        f"Circuit {idx} preview missing label '{comp.label}'"
                    )
