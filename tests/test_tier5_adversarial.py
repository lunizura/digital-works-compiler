"""
tests/test_tier5_adversarial.py — Milestone 4 Tier 5 Adversarial Routing & Serialization Suite

Comprehensive adversarial stress tests and independent Delphi VCL stream verification:
- Section 1: Adversarial Routing Stress Testing Suite (Challenger 1, 25 tests)
- Section 2: Independent Delphi VCL Stream Verification Oracle (DelphiVCLParser)
- Section 3: Adversarial Binary Serialization Stress Testing Suite (Challenger 2, 23 tests)

Total Tier 5 Tests: 48
"""

from __future__ import annotations

import io
import math
import os
import sys
import struct
import tempfile
from pathlib import Path
import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dwm_builder import DWMBuilder, Component, Pin, Wire, MAGIC_HEADER
from test_builder import assert_manhattan_invariants, detect_wire_t_junctions


# ============================================================================
# SECTION 1: Adversarial Routing Stress Testing Suite (Challenger 1, 25 Tests)
# ============================================================================

@pytest.mark.tier5
class TestTier5CoincidentAndDegenerateRouting:
    """Stress tests for coincident pins, degenerate geometries, and collinearity."""

    def test_coincident_pins_distinct_components_manhattan_orthogonality(self):
        """Coincident distinct pins connect with valid 2-point zero-displacement endpoints."""
        builder = DWMBuilder("CoincidentPins")
        inp = builder.add_input(100.0, 100.0)
        led = builder.add_led(100.0, 100.0)
        wire = builder.connect(inp.pins["out"], led.pins["in"])

        assert len(wire.points) == 2
        assert wire.points[0] == (100.0, 100.0)
        assert wire.points[1] == (100.0, 100.0)
        assert wire.points[0] == (wire.source_pin.x, wire.source_pin.y)
        assert wire.points[-1] == (wire.dest_pin.x, wire.dest_pin.y)
        p1, p2 = wire.points[0], wire.points[1]
        assert p1[0] == p2[0] or p1[1] == p2[1]

    def test_near_coincident_pins_micro_epsilon_separation(self):
        """Pins separated by micro-epsilon (< 1e-9) route strictly orthogonally."""
        builder = DWMBuilder("MicroEpsilon")
        p1 = Pin("out", "output", 100.0, 100.0, Component("INPUT", 100.0, 100.0))
        p2 = Pin("in", "input", 100.0 + 1e-10, 100.0 + 1e-10, Component("LED", 100.0, 100.0))
        wire = builder.connect(p1, p2)

        assert len(wire.points) == 4
        for i in range(len(wire.points) - 1):
            pt1, pt2 = wire.points[i], wire.points[i + 1]
            assert pt1[0] == pt2[0] or pt1[1] == pt2[1]

    def test_self_pin_connection_strictly_prohibited(self):
        """Connecting a pin to itself must raise ValueError."""
        builder = DWMBuilder("SelfConn")
        inp = builder.add_input(100.0, 100.0)
        with pytest.raises(ValueError, match="Cannot connect a pin to itself"):
            builder.connect(inp.pins["out"], inp.pins["out"])

    def test_collinear_horizontal_zero_bends_fwd_and_retrograde(self):
        """Collinear horizontal wires must produce exactly 2 points without redundant bends."""
        builder = DWMBuilder("CollinearH")
        i1 = builder.add_input(50.0, 100.0)
        l1 = builder.add_led(250.0, 100.0)
        w_fwd = builder.connect(i1.pins["out"], l1.pins["in"])
        assert w_fwd.points == [(50.0, 100.0), (250.0, 100.0)]
        assert_manhattan_invariants(w_fwd)

        i2 = builder.add_input(350.0, 100.0)
        l2 = builder.add_led(150.0, 100.0)
        w_rev = builder.connect(i2.pins["out"], l2.pins["in"])
        assert w_rev.points == [(350.0, 100.0), (150.0, 100.0)]
        assert_manhattan_invariants(w_rev)

    def test_collinear_vertical_zero_bends_fwd_and_retrograde(self):
        """Collinear vertical wires must produce exactly 2 points without redundant bends."""
        builder = DWMBuilder("CollinearV")
        i1 = builder.add_input(100.0, 50.0)
        l1 = builder.add_led(100.0, 250.0)
        w_fwd = builder.connect(i1.pins["out"], l1.pins["in"])
        assert w_fwd.points == [(100.0, 50.0), (100.0, 250.0)]
        assert_manhattan_invariants(w_fwd)

        i2 = builder.add_input(100.0, 350.0)
        l2 = builder.add_led(100.0, 150.0)
        w_rev = builder.connect(i2.pins["out"], l2.pins["in"])
        assert w_rev.points == [(100.0, 350.0), (100.0, 150.0)]
        assert_manhattan_invariants(w_rev)

    def test_collinear_route_type_specification_invariance(self):
        """Specifying route_type on already collinear pins preserves 2-point collinear path."""
        builder = DWMBuilder("CollinearOverride")
        i1 = builder.add_input(50.0, 100.0)
        l1 = builder.add_led(250.0, 100.0)
        w_hv = builder.connect(i1.pins["out"], l1.pins["in"], route_type="HV")
        w_vh = builder.connect(i1.pins["out"], l1.pins["in"], route_type="VH")

        assert len(w_hv.points) == 2
        assert len(w_vh.points) == 2
        assert w_hv.points == [(50.0, 100.0), (250.0, 100.0)]
        assert w_vh.points == [(50.0, 100.0), (250.0, 100.0)]


@pytest.mark.tier5
class TestTier5BoundaryGridExtremesRouting:
    """Stress tests for extreme coordinates, negative planes, and grid calculations."""

    def test_extreme_large_positive_coordinates_routing(self):
        """Coordinates at 10^6 boundary route and serialize without overflow."""
        builder = DWMBuilder("ExtremePos")
        inp = builder.add_input(1_000_000.0, 1_000_000.0)
        led = builder.add_led(1_000_500.0, 1_000_200.0)
        wire = builder.connect(inp.pins["out"], led.pins["in"])

        assert len(wire.points) == 4
        assert wire.points[0] == (1_000_000.0, 1_000_000.0)
        assert wire.points[1] == (1_000_250.0, 1_000_000.0)
        assert wire.points[2] == (1_000_250.0, 1_000_200.0)
        assert wire.points[3] == (1_000_500.0, 1_000_200.0)
        assert_manhattan_invariants(wire)

        raw = builder.to_bytes()
        assert raw.startswith(MAGIC_HEADER)

    def test_extreme_negative_coordinates_routing(self):
        """Coordinates at -10^6 boundary route and serialize correctly."""
        builder = DWMBuilder("ExtremeNeg")
        inp = builder.add_input(-1_000_000.0, -1_000_000.0)
        led = builder.add_led(-1_000_500.0, -1_000_200.0)
        wire = builder.connect(inp.pins["out"], led.pins["in"])

        assert len(wire.points) == 4
        assert_manhattan_invariants(wire)
        raw = builder.to_bytes()
        assert raw.startswith(MAGIC_HEADER)

    def test_mixed_sign_quadrant_spanning_origin_routing(self):
        """Wires spanning across quadrants (negative to positive) maintain strict orthogonality."""
        builder = DWMBuilder("SpanOrigin")
        inp = builder.add_input(-500.0, -300.0)
        led = builder.add_led(500.0, 300.0)
        wire = builder.connect(inp.pins["out"], led.pins["in"])

        assert len(wire.points) == 4
        assert wire.points[1][0] == 0.0
        assert_manhattan_invariants(wire)
        raw = builder.to_bytes()
        assert raw.startswith(MAGIC_HEADER)

    def test_sub_pixel_fractional_precision_routing(self):
        """Coordinates with non-integer floating-point offsets maintain orthogonality."""
        builder = DWMBuilder("Fractional")
        inp = builder.add_input(0.12345, 0.67891)
        led = builder.add_led(100.98765, 200.54321)
        wire = builder.connect(inp.pins["out"], led.pins["in"])

        for i in range(len(wire.points) - 1):
            pt1, pt2 = wire.points[i], wire.points[i + 1]
            assert abs(pt1[0] - pt2[0]) < 1e-6 or abs(pt1[1] - pt2[1]) < 1e-6

        raw = builder.to_bytes()
        assert raw.startswith(MAGIC_HEADER)

    def test_z_route_midpoint_calculation_odd_grid_spacing(self):
        """Z-channel midpoint between coordinates at odd grid intervals computes float mid."""
        builder = DWMBuilder("ZOddMid")
        p1 = Pin("out", "output", 100.0, 100.0, Component("INPUT", 100.0, 100.0))
        p2 = Pin("in", "input", 105.0, 200.0, Component("LED", 105.0, 200.0))
        wire = builder.connect(p1, p2)

        assert len(wire.points) == 4
        assert wire.points[1][0] == 102.5
        assert_manhattan_invariants(wire)


@pytest.mark.tier5
class TestTier5MultiBendAndSerpentineRouting:
    """Stress tests for multi-bend serpentine paths and custom wire vertex lists."""

    def test_multi_bend_serpentine_wire_structure(self):
        """Custom N-bend wire satisfies Manhattan invariants across all segments."""
        inp = Component("INPUT", 0.0, 0.0).add_pin("out", "output", 0.0, 0.0)
        led = Component("LED", 100.0, 500.0).add_pin("in", "input", 0.0, 0.0)

        pts = [(0.0, 0.0)]
        cur_x, cur_y = 0.0, 0.0
        for _ in range(5):
            cur_x += 20.0
            pts.append((cur_x, cur_y))
            cur_y += 100.0
            pts.append((cur_x, cur_y))

        wire = Wire(source_pin=inp, dest_pin=led, points=pts)
        assert len(wire.points) == 11
        assert_manhattan_invariants(wire)

    def test_serpentine_wire_serialization_and_vcl_stream(self):
        """A circuit with a multi-bend serpentine wire serializes valid VCL format."""
        builder = DWMBuilder("SerpentineCircuit")
        inp = builder.add_input(0.0, 0.0)
        led = builder.add_led(100.0, 500.0)

        pts = [(0.0, 0.0)]
        cur_x, cur_y = 0.0, 0.0
        for _ in range(4):
            cur_x += 25.0
            pts.append((cur_x, cur_y))
            cur_y += 125.0
            pts.append((cur_x, cur_y))

        wire = Wire(source_pin=inp.pins["out"], dest_pin=led.pins["in"], points=pts)
        builder.wires.append(wire)
        inp.pins["out"].connected_wire = wire
        led.pins["in"].connected_wire = wire

        raw = builder.to_bytes()
        assert raw.startswith(MAGIC_HEADER)
        assert b"TWire" in raw
        assert b"TFloatPoint" in raw

    def test_serpentine_wire_ascii_preview_rendering(self):
        """ASCII previewer rasterizes multi-bend serpentine wire tracks without crashing."""
        builder = DWMBuilder("SerpentinePreview")
        inp = builder.add_input(10.0, 10.0)
        led = builder.add_led(80.0, 80.0)
        wire = builder.connect(inp.pins["out"], led.pins["in"])

        prev = builder.preview()
        assert isinstance(prev, str)
        assert "INPUT" in prev
        assert "LED" in prev
        assert any(c in prev for c in ("-", "|", "+"))


@pytest.mark.tier5
class TestTier5CyclicAndFeedbackRouting:
    """Stress tests for feedback paths, cyclic topologies, and state-holding circuits."""

    def test_ring_oscillator_three_inverter_cyclic_routing(self):
        """3-inverter ring oscillator feedback loop compiles and preserves orthogonality."""
        builder = DWMBuilder("RingOscillator")
        not1 = builder.add_gate("NOT", 100.0, 100.0, label="NOT1")
        not2 = builder.add_gate("NOT", 200.0, 100.0, label="NOT2")
        not3 = builder.add_gate("NOT", 300.0, 100.0, label="NOT3")

        w1 = builder.connect(not1.pins["out"], not2.pins["in"])
        w2 = builder.connect(not2.pins["out"], not3.pins["in"])
        w3 = builder.connect(not3.pins["out"], not1.pins["in"])

        assert len(builder.wires) == 3
        for w in (w1, w2, w3):
            assert_manhattan_invariants(w)

        raw = builder.to_bytes()
        assert raw.startswith(MAGIC_HEADER)
        assert b"TNotGate" in raw

    def test_cross_coupled_nor_sr_latch_cyclic_routing(self):
        """SR latch with cross-coupled NOR gates passes all Manhattan invariants."""
        builder = DWMBuilder("SR_Latch")
        s_in = builder.add_input(50.0, 100.0, label="S")
        r_in = builder.add_input(50.0, 200.0, label="R")
        nor1 = builder.add_gate("NOR", 180.0, 100.0, label="NOR1")
        nor2 = builder.add_gate("NOR", 180.0, 200.0, label="NOR2")
        q_led = builder.add_led(320.0, 100.0, label="Q")
        qbar_led = builder.add_led(320.0, 200.0, label="Q_BAR")

        builder.connect(s_in.pins["out"], nor1.pins["in1"])
        builder.connect(r_in.pins["out"], nor2.pins["in2"])
        w_fb1 = builder.connect(nor1.pins["out"], nor2.pins["in1"])
        w_fb2 = builder.connect(nor2.pins["out"], nor1.pins["in2"])
        builder.connect(nor1.pins["out"], q_led.pins["in"])
        builder.connect(nor2.pins["out"], qbar_led.pins["in"])

        assert_manhattan_invariants(w_fb1)
        assert_manhattan_invariants(w_fb2)

        raw = builder.to_bytes()
        assert raw.startswith(MAGIC_HEADER)
        assert b"T2NorGate" in raw

    def test_gate_direct_self_feedback_routing(self):
        """Connecting a gate's output pin to its own input pin routes orthogonally."""
        builder = DWMBuilder("GateSelfFeedback")
        gate = builder.add_gate("AND", 100.0, 100.0)
        wire = builder.connect(gate.pins["out"], gate.pins["in1"])

        assert len(wire.points) == 4
        assert wire.points[0] == (gate.pins["out"].x, gate.pins["out"].y)
        assert wire.points[-1] == (gate.pins["in1"].x, gate.pins["in1"].y)
        assert_manhattan_invariants(wire)

        raw = builder.to_bytes()
        assert raw.startswith(MAGIC_HEADER)


@pytest.mark.tier5
class TestTier5HighDensityAndCrossingsRouting:
    """Stress tests for high-density crossings, mesh topologies, and fanout nets."""

    def test_high_density_10x10_wire_mesh_crossings(self):
        """10 horizontal wires crossing 10 vertical wires rasterize and serialize cleanly."""
        builder = DWMBuilder("WireMesh")
        h_inputs = [builder.add_input(50.0, 50.0 + i * 20.0) for i in range(10)]
        h_leds = [builder.add_led(350.0, 50.0 + i * 20.0) for i in range(10)]
        for i in range(10):
            builder.connect(h_inputs[i].pins["out"], h_leds[i].pins["in"])

        v_inputs = [builder.add_input(100.0 + j * 20.0, 20.0) for j in range(10)]
        v_leds = [builder.add_led(100.0 + j * 20.0, 300.0) for j in range(10)]
        for j in range(10):
            builder.connect(v_inputs[j].pins["out"], v_leds[j].pins["in"])

        assert len(builder.wires) == 20
        prev = builder.preview()
        assert "+" in prev
        raw = builder.to_bytes()
        assert raw.startswith(MAGIC_HEADER)

    def test_high_fanout_single_source_to_20_destinations(self):
        """Single source pin fanning out to 20 destination LEDs preserves wire records."""
        builder = DWMBuilder("HighFanout")
        src = builder.add_input(50.0, 200.0)
        leds = [builder.add_led(300.0, 50.0 + i * 15.0) for i in range(20)]
        for led in leds:
            w = builder.connect(src.pins["out"], led.pins["in"])
            assert_manhattan_invariants(w)

        assert len(builder.wires) == 20
        raw = builder.to_bytes()
        assert raw.startswith(MAGIC_HEADER)

    def test_t_junction_solder_detection_vs_wire_crossings(self):
        """Differentiates geometric wire crossings (no solder) from T-junctions (solder)."""
        w_h = Wire(
            source_pin=Pin("out", "output", 100.0, 200.0, Component("INPUT", 100.0, 200.0)),
            dest_pin=Pin("in", "input", 300.0, 200.0, Component("LED", 300.0, 200.0)),
            points=[(100.0, 200.0), (300.0, 200.0)]
        )
        w_cross = Wire(
            source_pin=Pin("out", "output", 200.0, 100.0, Component("INPUT", 200.0, 100.0)),
            dest_pin=Pin("in", "input", 200.0, 300.0, Component("LED", 200.0, 300.0)),
            points=[(200.0, 100.0), (200.0, 300.0)]
        )
        assert len(detect_wire_t_junctions([w_h, w_cross])) == 0

        w_t = Wire(
            source_pin=Pin("out", "output", 200.0, 200.0, Component("INPUT", 200.0, 200.0)),
            dest_pin=Pin("in", "input", 200.0, 300.0, Component("LED", 200.0, 300.0)),
            points=[(200.0, 200.0), (200.0, 300.0)]
        )
        junctions = detect_wire_t_junctions([w_h, w_t])
        assert (200.0, 200.0) in junctions

    def test_wire_pin_collision_invariance(self):
        """Bypass wire routed directly across intermediate component retains its endpoint pins."""
        builder = DWMBuilder("CollisionInvariance")
        inp = builder.add_input(50.0, 100.0)
        mid_gate = builder.add_gate("NOT", 150.0, 100.0)
        led = builder.add_led(250.0, 100.0)

        wire = builder.connect(inp.pins["out"], led.pins["in"])
        assert wire.points == [(50.0, 100.0), (250.0, 100.0)]
        assert wire.source_pin is inp.pins["out"]
        assert wire.dest_pin is led.pins["in"]
        assert mid_gate.pins["in"].connected_wire is None
        assert mid_gate.pins["out"].connected_wire is None


@pytest.mark.tier5
class TestTier5RoutingDeterminismAndInvariants:
    """Stress tests for reproducibility, determinism, and invariant checking."""

    def test_routing_determinism_across_identical_invocations(self):
        """Repeated routing on identical topology produces byte-for-byte identical results."""
        def make_circuit():
            b = DWMBuilder("DeterminismTest")
            i = b.add_input(50.0, 80.0)
            g = b.add_gate("AND", 150.0, 100.0)
            l = b.add_led(250.0, 100.0)
            b.connect(i.pins["out"], g.pins["in1"])
            b.connect(g.pins["out"], l.pins["in"])
            return b

        b1, b2 = make_circuit(), make_circuit()
        assert [w.points for w in b1.wires] == [w.points for w in b2.wires]
        assert b1.to_bytes() == b2.to_bytes()
        assert b1.preview() == b2.preview()

    @pytest.mark.parametrize("route_type", [None, "HV", "VH"])
    def test_manhattan_invariants_across_all_topologies(self, route_type):
        """Every routing topology satisfies strict right-angle Manhattan invariants."""
        builder = DWMBuilder("ManhattanMatrix")
        coords = [
            (50.0, 50.0, 200.0, 150.0),
            (200.0, 150.0, 50.0, 50.0),
            (-100.0, 50.0, 150.0, -80.0),
            (0.0, 0.0, 100.0, 100.0),
        ]
        for x1, y1, x2, y2 in coords:
            p1 = Pin("out", "output", x1, y1, Component("INPUT", x1, y1))
            p2 = Pin("in", "input", x2, y2, Component("LED", x2, y2))
            wire = builder.connect(p1, p2, route_type=route_type)
            assert_manhattan_invariants(wire)


# ============================================================================
# SECTION 2: Independent Delphi VCL Stream Verification Oracle
# ============================================================================

class DelphiVCLParser:
    """
    Independent Delphi VCL Component Stream Oracle.
    Parses and validates Delphi VCL binary streams emitted by DWMBuilder.
    """
    def __init__(self, data: bytes):
        self.data = data
        self.stream = io.BytesIO(data)
        self.classes: list[str] = []
        self.objects: list[dict] = []
        self.tokens_encountered: list[tuple[int, int]] = []
        self.markers_encountered: list[tuple[int, int]] = []

    def tell(self) -> int:
        return self.stream.tell()

    def read_exact(self, n: int) -> bytes:
        b = self.stream.read(n)
        if len(b) < n:
            raise EOFError(f"Unexpected EOF at offset {self.tell()}: wanted {n} bytes, got {len(b)}")
        return b

    def parse_header(self) -> bytes:
        hdr = self.read_exact(5)
        if hdr != MAGIC_HEADER:
            raise ValueError(f"Magic header mismatch: {hdr.hex()} != {MAGIC_HEADER.hex()}")
        return hdr

    def read_token(self) -> int:
        b = self.stream.read(1)
        if not b:
            raise EOFError(f"Unexpected EOF while reading token at {self.tell()}")
        tok = b[0]
        self.tokens_encountered.append((self.tell() - 1, tok))
        return tok

    def read_integer(self) -> int:
        tok = self.read_token()
        if tok == 0x02:  # vaInt8
            val = struct.unpack("<b", self.read_exact(1))[0]
        elif tok == 0x03:  # vaInt16
            val = struct.unpack("<h", self.read_exact(2))[0]
        elif tok == 0x04:  # vaInt32
            val = struct.unpack("<i", self.read_exact(4))[0]
        elif tok == 0x13:  # vaInt64
            val = struct.unpack("<q", self.read_exact(8))[0]
        else:
            raise ValueError(f"Expected integer token at {self.tell()-1}, got 0x{tok:02x}")
        return val

    def read_string(self) -> str:
        tok = self.read_token()
        if tok == 0x06:  # vaString
            length = self.read_exact(1)[0]
            raw = self.read_exact(length)
            return raw.decode("utf-8", errors="replace")
        elif tok == 0x0C:  # vaLString
            length = struct.unpack("<I", self.read_exact(4))[0]
            raw = self.read_exact(length)
            return raw.decode("utf-8", errors="replace")
        else:
            raise ValueError(f"Expected string token at {self.tell()-1}, got 0x{tok:02x}")

    def read_boolean(self) -> bool:
        tok = self.read_token()
        if tok == 0x08:
            return False
        elif tok == 0x09:
            return True
        else:
            raise ValueError(f"Expected boolean token at {self.tell()-1}, got 0x{tok:02x}")

    def parse_preamble(self) -> dict:
        tok = self.read_token()
        if tok != 0x01:  # vaList
            raise ValueError(f"Expected vaList (0x01) for preamble, got 0x{tok:02x}")
        props = {}
        while True:
            pos = self.tell()
            tok_byte = self.stream.read(1)
            if not tok_byte:
                raise EOFError("Unexpected EOF in preamble")
            if tok_byte[0] == 0x00:  # vaNull
                break
            self.stream.seek(pos)
            data_type = self.read_integer()
            tag_id = self.read_integer()
            if data_type == 1:
                val = self.read_string()
            elif data_type == 2:
                val = self.read_integer()
            elif data_type == 3:
                val = self.read_boolean()
            else:
                raise ValueError(f"Unknown property data type {data_type} at {self.tell()}")
            props[tag_id] = val
        return props

    def parse_object(self) -> dict:
        pos = self.tell()
        tok = self.read_token()
        if tok != 0x02:
            raise ValueError(f"Expected vaInt8 (0x02) for object marker at {pos}, got 0x{tok:02x}")
        marker_code = self.read_exact(1)[0]
        self.markers_encountered.append((pos, marker_code))

        if marker_code == 0x0F:  # Marker 15 (Nil)
            return {"type": "nil"}
        elif marker_code == 0x02:  # Marker 2 (Object Ref)
            ref_id = self.read_integer()
            if ref_id < 0 or ref_id >= len(self.objects):
                raise ValueError(f"Marker 2 ref_id {ref_id} out of bounds (len={len(self.objects)}) at {pos}")
            return {"type": "obj_ref", "id": ref_id, "target": self.objects[ref_id]}
        elif marker_code == 0x00:  # Marker 0 (New Class)
            cls_name = self.read_string()
            self.classes.append(cls_name)
            obj_idx = len(self.objects)
            obj_record = {"type": "instance", "class": cls_name, "id": obj_idx}
            self.objects.append(obj_record)
            self._parse_instance_body(cls_name, obj_record)
            return obj_record
        elif marker_code == 0x01:  # Marker 1 (Class Ref)
            cls_idx = self.read_integer()
            if cls_idx < 0 or cls_idx >= len(self.classes):
                raise ValueError(f"Marker 1 cls_idx {cls_idx} out of bounds (len={len(self.classes)}) at {pos}")
            cls_name = self.classes[cls_idx]
            obj_idx = len(self.objects)
            obj_record = {"type": "instance", "class": cls_name, "id": obj_idx}
            self.objects.append(obj_record)
            self._parse_instance_body(cls_name, obj_record)
            return obj_record
        else:
            raise ValueError(f"Unknown marker code 0x{marker_code:02x} at {pos}")

    def _parse_instance_body(self, cls_name: str, record: dict):
        if cls_name == "TMacro":
            record["has_graphic_list"] = self.read_boolean()
            record["graphic_list"] = self.parse_object()
            record["flag1"] = self.read_boolean()
            record["flag2"] = self.read_boolean()
            record["macro_pins"] = self.parse_object()
            record["doc_link"] = self.read_string()
            record["zero"] = self.read_integer()
            record["flag3"] = self.read_boolean()
            record["flag4"] = self.read_boolean()
            # 6 sub-lists
            record["components_list"] = self.parse_object()
            record["tags_list"] = self.parse_object()
            record["sublist2"] = self.parse_object()
            record["sublist3"] = self.parse_object()
            record["sublist4"] = self.parse_object()
            record["wires_list"] = self.parse_object()
        elif cls_name == "TGraphicList":
            record["inner"] = self.parse_object()
        elif cls_name == "TSerializeList":
            tok = self.read_token()
            if tok != 0x01:  # vaList
                raise ValueError(f"Expected vaList (0x01) in TSerializeList, got 0x{tok:02x}")
            items = []
            while True:
                pos = self.tell()
                tok_byte = self.stream.read(1)
                if not tok_byte:
                    raise EOFError("Unexpected EOF in TSerializeList")
                if tok_byte[0] == 0x00:  # vaNull
                    break
                self.stream.seek(pos)
                items.append(self.parse_object())
            record["items"] = items
        elif cls_name == "TPolygon":
            record["pen_color"] = self.read_integer()
            record["pen_width"] = self.read_integer()
            record["points"] = self.parse_object()
            record["brush"] = self.read_integer()
        elif cls_name == "TGraphicText":
            record["pen_color"] = self.read_integer()
            record["pen_width"] = self.read_integer()
            record["points"] = self.parse_object()
            record["brush"] = self.read_integer()
            record["font_size"] = self.read_integer()
            record["font_style"] = self.read_integer()
            record["font_underline"] = self.read_boolean()
            record["font_weight"] = self.read_integer()
            record["font_angle"] = self.read_exact(4)
            record["text"] = self.read_string()
            record["flag1"] = self.read_boolean()
            record["flag2"] = self.read_boolean()
        elif cls_name == "TFloatPoint":
            raw_coords = self.read_exact(8)
            record["coords"] = struct.unpack("<ff", raw_coords)
        elif cls_name == "TPin":
            record["pen_color"] = self.read_integer()
            record["pen_width"] = self.read_integer()
            record["points"] = self.parse_object()
            record["brush"] = self.read_integer()
            record["pin_dir"] = self.read_integer()
            record["connected_wire"] = self.parse_object()
        elif cls_name == "TWire":
            record["pen_color"] = self.read_integer()
            record["pen_width"] = self.read_integer()
            record["points"] = self.parse_object()
            record["wire_state"] = self.read_integer()
            record["source_pin"] = self.parse_object()
            record["dest_pin"] = self.parse_object()
        elif cls_name in (
            "T2AndGate", "T2OrGate", "T2NandGate", "T2NorGate", "T2XorGate",
            "TNotGate", "TInteractiveInput", "TLEDDevice"
        ):
            record["has_graphic_list"] = self.read_boolean()
            record["is_selected"] = self.read_boolean()
            record["device_flag"] = self.read_boolean()
            record["pins"] = self.parse_object()
            raw_coords = self.read_exact(8)
            record["anchor"] = struct.unpack("<ff", raw_coords)
            if cls_name == "TInteractiveInput":
                record["has_label"] = self.read_boolean()
                record["history_enabled"] = self.read_boolean()
                record["switch_state"] = self.read_boolean()
                record["input_mode"] = self.read_integer()
            elif cls_name == "TLEDDevice":
                record["has_label"] = self.read_boolean()
                record["history_enabled"] = self.read_boolean()
                record["led_color"] = self.read_integer()
        else:
            raise ValueError(f"Unrecognized class {cls_name} at offset {self.tell()}")

    def parse_full_stream(self) -> dict:
        hdr = self.parse_header()
        preamble = self.parse_preamble()
        root_macro = self.parse_object()
        remaining = self.stream.read()
        if len(remaining) > 0:
            raise ValueError(f"Stream has {len(remaining)} trailing unconsumed bytes: {remaining[:32].hex()}...")
        return {
            "header": hdr,
            "preamble": preamble,
            "root": root_macro,
            "classes": self.classes,
            "total_objects": len(self.objects),
            "tokens_count": len(self.tokens_encountered),
            "markers_count": len(self.markers_encountered),
        }


# ============================================================================
# SECTION 3: Adversarial Binary Serialization Stress Testing Suite (Challenger 2, 23 Tests)
# ============================================================================

@pytest.mark.tier5
class TestTier5AdversarialSerialization:
    """
    Tier 5: Adversarial binary format and serialization stress testing suite.
    Validates Delphi VCL component stream invariants, dynamic integer compaction,
    graph cycle resolution, marker integrity, label fuzzing, and extreme fan-out.
    """

    def test_tier5_empty_circuit_delphi_stream_integrity(self):
        """Verify circuit with 0 components and 0 wires satisfies the complete Delphi binary format."""
        builder = DWMBuilder("EmptyAdversarial")
        data = builder.to_bytes()

        assert data.startswith(MAGIC_HEADER), "Missing magic header 0x0022c4dd"
        assert len(data) >= 40, "Stream too short for header and preamble"

        parser = DelphiVCLParser(data)
        res = parser.parse_full_stream()

        assert res["preamble"][100] == "EmptyAdversarial"
        comps_container = res["root"]["components_list"]["inner"]["items"]
        assert len(comps_container) == 0
        wires_container = res["root"]["wires_list"]["inner"]["items"]
        assert len(wires_container) == 0

    def test_tier5_unconnected_component_nil_marker_15(self):
        """Verify unconnected component pins emit Marker 15 (nil pointer, 0x02 0x0F) for connected_wire."""
        builder = DWMBuilder("UnconnectedComponents")
        gate = builder.add_gate("AND", 100.0, 100.0)
        inp = builder.add_input(50.0, 100.0)
        led = builder.add_led(200.0, 100.0)

        data = builder.to_bytes()
        parser = DelphiVCLParser(data)
        res = parser.parse_full_stream()

        assert "T2AndGate" in res["classes"]
        assert "TInteractiveInput" in res["classes"]
        assert "TLEDDevice" in res["classes"]
        assert "TPin" in res["classes"]

        marker_codes = [m[1] for m in parser.markers_encountered]
        assert 0x0F in marker_codes
        assert marker_codes.count(0x0F) >= 5

    def test_tier5_class_registry_deduplication_marker_1(self):
        """Verify Marker 1 (existing class reference) is used for duplicate component classes."""
        builder = DWMBuilder("DuplicateClasses")
        for i in range(8):
            builder.add_gate("OR", 50.0 + i * 40, 100.0)

        data = builder.to_bytes()
        parser = DelphiVCLParser(data)
        res = parser.parse_full_stream()

        assert res["classes"].count("T2OrGate") == 1
        marker_codes = [m[1] for m in parser.markers_encountered]
        assert 0x01 in marker_codes

    def test_tier5_all_eight_component_types_in_single_circuit(self):
        """Verify heterogeneous circuit containing all 8 supported classes compiles with correct class indexing."""
        builder = DWMBuilder("HeterogeneousAllTypes")
        types = ["AND", "OR", "NOT", "NAND", "NOR", "XOR"]
        for i, gtype in enumerate(types):
            builder.add_gate(gtype, 100.0 + i * 60, 100.0)
        builder.add_input(50.0, 50.0)
        builder.add_led(500.0, 50.0)

        data = builder.to_bytes()
        parser = DelphiVCLParser(data)
        res = parser.parse_full_stream()

        expected_classes = [
            "T2AndGate", "T2OrGate", "TNotGate", "T2NandGate", "T2NorGate", "T2XorGate",
            "TInteractiveInput", "TLEDDevice", "TPin"
        ]
        for cls in expected_classes:
            assert cls in res["classes"], f"Class {cls} missing from registry"

    def test_tier5_object_deduplication_marker_2_graph_walk(self):
        """Verify Marker 2 (object pointer reference) deduplicates shared objects without cycle recursion."""
        builder = DWMBuilder("GraphDeduplication")
        inp = builder.add_input(50.0, 100.0)
        gate = builder.add_gate("AND", 150.0, 100.0)
        led = builder.add_led(250.0, 100.0)

        w1 = builder.connect(inp.pins["out"], gate.pins["in1"])
        w2 = builder.connect(gate.pins["out"], led.pins["in"])

        data = builder.to_bytes()
        parser = DelphiVCLParser(data)
        res = parser.parse_full_stream()

        marker_codes = [m[1] for m in parser.markers_encountered]
        assert 0x02 in marker_codes

        wires_sublist = res["root"]["wires_list"]["inner"]["items"]
        assert len(wires_sublist) == 2
        for w_item in wires_sublist:
            assert w_item["type"] == "obj_ref"

    def test_tier5_large_fanout_50_plus(self):
        """Adversarial stress test: 1 output pin driving 60 distinct gate inputs (60 wires)."""
        builder = DWMBuilder("LargeFanout")
        inp = builder.add_input(50.0, 500.0, label="HIGH_FANOUT_SRC")
        for i in range(60):
            gate = builder.add_gate("AND", 200.0, float(50 + i * 30), label=f"G_{i}")
            builder.connect(inp.pins["out"], gate.pins["in1"])

        assert len(builder.wires) == 60
        assert len(builder.components) == 61

        data = builder.to_bytes()
        assert data.startswith(MAGIC_HEADER)

        parser = DelphiVCLParser(data)
        res = parser.parse_full_stream()

        assert res["total_objects"] > 128
        assert 0x02 in [m[1] for m in parser.markers_encountered]

    def test_tier5_massive_circuit_100_components_cascade(self):
        """Adversarial stress test: 100 cascaded NOT inverters with 99 wires."""
        builder = DWMBuilder("MassiveCascade")
        prev = builder.add_gate("NOT", 50.0, 100.0)
        for i in range(1, 100):
            curr = builder.add_gate("NOT", 50.0 + i * 30, 100.0)
            builder.connect(prev.pins["out"], curr.pins["in"])
            prev = curr

        assert len(builder.components) == 100
        assert len(builder.wires) == 99

        data = builder.to_bytes()
        assert len(data) > 10000

        parser = DelphiVCLParser(data)
        res = parser.parse_full_stream()
        assert res["total_objects"] > 300

    def test_tier5_coordinate_conversions_extreme_and_subpixel(self):
        """Verify extreme coordinates (large, negative, sub-pixel precision) and IEEE 754 float32 encoding."""
        builder = DWMBuilder("CoordStress")
        builder.add_input(-999999.0, -888888.0, label="NEG")
        builder.add_led(1000000.0, 2000000.0, label="POS")
        builder.add_gate("AND", 12.34567, 98.76543, label="FLOAT")

        data = builder.to_bytes()
        parser = DelphiVCLParser(data)
        res = parser.parse_full_stream()

        comps = res["root"]["components_list"]["inner"]["items"]
        assert len(comps) == 3

        c0_anchor = comps[0]["anchor"]
        assert abs(c0_anchor[0] - (-999999.0)) < 1.0
        assert abs(c0_anchor[1] - (-888888.0)) < 1.0

        c1_anchor = comps[1]["anchor"]
        assert abs(c1_anchor[0] - (1000000.0)) < 1.0
        assert abs(c1_anchor[1] - (2000000.0)) < 1.0

        c2_anchor = comps[2]["anchor"]
        assert abs(c2_anchor[0] - 12.34567) < 1e-4
        assert abs(c2_anchor[1] - 98.76543) < 1e-4

        raw_float = struct.pack("<ff", 12.34567, 98.76543)
        idx = data.find(raw_float)
        assert idx != -1
        assert data[idx - 1] != 0x0F

    @pytest.mark.parametrize("title_str", [
        "",
        "A" * 255,  # vaString boundary
        "B" * 256,  # vaLString threshold
        "C" * 1024, # Large vaLString
        "Japanese: 論理回路設計",
        "Emoji: ⚡💡🔌🔥",
        "Special: !@#$%^&*()_+{}[]|:;\"'<>,.?/~`",
        "Embedded\x00Null\x00Byte",
        "Whitespace: \t\r\n   ",
    ])
    def test_tier5_label_and_title_fuzzing(self, title_str):
        """Fuzz circuit titles and labels with boundary lengths, UTF-8 unicode, null bytes, and symbols."""
        builder = DWMBuilder(title=title_str)
        builder.add_input(100.0, 100.0, label=title_str)
        builder.add_gate("AND", 200.0, 100.0, label=title_str)

        data = builder.to_bytes()
        parser = DelphiVCLParser(data)
        res = parser.parse_full_stream()

        assert res["preamble"][100] == title_str

    def test_tier5_serialization_determinism_and_idempotence(self):
        """Verify multiple consecutive serializations of complex circuits are 100% byte-identical."""
        builder = DWMBuilder("DeterminismCircuit")
        in1 = builder.add_input(50.0, 100.0, label="IN1")
        in2 = builder.add_input(50.0, 200.0, label="IN2")
        g1 = builder.add_gate("AND", 150.0, 150.0, label="G1")
        g2 = builder.add_gate("OR", 250.0, 150.0, label="G2")
        led = builder.add_led(350.0, 150.0, label="OUT")

        builder.connect(in1.pins["out"], g1.pins["in1"])
        builder.connect(in2.pins["out"], g1.pins["in2"])
        builder.connect(g1.pins["out"], g2.pins["in1"])
        builder.connect(g2.pins["out"], led.pins["in"])

        b1 = builder.to_bytes()
        b2 = builder.to_bytes()
        b3 = builder.to_bytes()
        b4 = builder.to_bytes()

        assert b1 == b2 == b3 == b4
        assert len(b1) > 0

    def test_tier5_file_roundtrip_disk_io(self, tmp_path):
        """Verify file saving roundtrip on disk produces exact byte match to to_bytes()."""
        builder = DWMBuilder("DiskRoundtrip")
        inp = builder.add_input(100.0, 100.0)
        gate = builder.add_gate("XOR", 200.0, 100.0)
        led = builder.add_led(300.0, 100.0)
        builder.connect(inp.pins["out"], gate.pins["in1"])
        builder.connect(gate.pins["out"], led.pins["in"])

        expected_data = builder.to_bytes()
        target_path = tmp_path / "roundtrip.dwm"
        builder.save(str(target_path))

        assert target_path.exists()
        saved_data = target_path.read_bytes()
        assert saved_data == expected_data

        parser = DelphiVCLParser(saved_data)
        res = parser.parse_full_stream()
        assert res["total_objects"] > 0

    def test_tier5_invalid_input_corruption_resilience(self):
        """Verify builder validates inputs and raises proper exceptions rather than emitting corrupt data."""
        builder = DWMBuilder()

        # Invalid gate types
        with pytest.raises(ValueError, match="Invalid gate type"):
            builder.add_gate("NON_EXISTENT_GATE", 100.0, 100.0)

        with pytest.raises(TypeError, match="must be a string"):
            builder.add_gate(None, 100.0, 100.0)

        with pytest.raises(TypeError, match="must be a string"):
            builder.add_gate(42, 100.0, 100.0)

        # Self-connection prohibition
        inp = builder.add_input(100.0, 100.0)
        with pytest.raises(ValueError, match="Cannot connect a pin to itself"):
            builder.connect(inp.pins["out"], inp.pins["out"])

        # Invalid save directory (cross-platform non-existent nested path)
        with pytest.raises((FileNotFoundError, OSError)):
            builder.save(os.path.join("nonexistent_directory_999", "nested_999", "circuit.dwm"))

    def test_tier5_feedback_loop_cyclic_wiring(self):
        """Verify cycle-free serialization algorithm handles feedback loops (e.g. SR latch) without infinite recursion."""
        builder = DWMBuilder("SRLatchFeedback")
        nor1 = builder.add_gate("NOR", 150.0, 100.0, label="NOR1")
        nor2 = builder.add_gate("NOR", 150.0, 200.0, label="NOR2")

        # Feedback cross-coupling
        builder.connect(nor1.pins["out"], nor2.pins["in1"])
        builder.connect(nor2.pins["out"], nor1.pins["in2"])

        data = builder.to_bytes()
        assert data.startswith(MAGIC_HEADER)

        parser = DelphiVCLParser(data)
        res = parser.parse_full_stream()
        assert res["total_objects"] > 0

    def test_tier5_preamble_tags_and_dynamic_compaction(self):
        """Verify Delphi dynamic integer compaction in preamble: 0xCA and 0xC8 encoded as vaInt16 (0x03)."""
        builder = DWMBuilder("PreambleCheck")
        data = builder.to_bytes()

        assert data[5] == 0x01  # vaList
        assert b"\x03\xca\x00" in data[5:50], "Tag 0x00CA must be encoded as vaInt16"
        assert b"\x03\xc8\x00" in data[5:50], "Tag 0x00C8 must be encoded as vaInt16"

    def test_tier5_circuit_with_no_wires(self):
        """Verify multi-component circuit with 0 wires serializes an empty wires container list."""
        builder = DWMBuilder("ZeroWires")
        builder.add_input(100.0, 100.0)
        builder.add_gate("AND", 200.0, 100.0)
        builder.add_led(300.0, 100.0)

        data = builder.to_bytes()
        parser = DelphiVCLParser(data)
        res = parser.parse_full_stream()

        wires_list = res["root"]["wires_list"]["inner"]["items"]
        assert len(wires_list) == 0
        comps_list = res["root"]["components_list"]["inner"]["items"]
        assert len(comps_list) == 3
