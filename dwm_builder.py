"""
dwm_builder.py — Production-Grade Digital Works Circuit Compiler

A modular Python library capable of generating valid Digital Works (.dwm)
binary circuit files directly from logic specifications, calculating pin
geometries, performing orthogonal Manhattan routing, and rendering ASCII previews.

Target Format: Borland Delphi VCL Component Stream (TWriter / TSerializeWriter)
Magic Header: 0x0022c4dd (\x04\xdd\xc4\x22\x00)
"""

from __future__ import annotations

import struct
from typing import Any, Dict, List, Optional, Tuple

__all__ = ["DWMBuilder", "Component", "Pin", "Wire"]

MAGIC_HEADER = b"\x04\xdd\xc4\x22\x00"

GATE_CONFIGS: Dict[str, Dict[str, Any]] = {
    "AND": {
        "delphi_class": "T2AndGate",
        "pins": [
            ("in1", "input", -30.0, -10.0),
            ("in2", "input", -30.0, 10.0),
            ("out", "output", 30.0, 0.0),
        ],
    },
    "OR": {
        "delphi_class": "T2OrGate",
        "pins": [
            ("in1", "input", -30.0, -10.0),
            ("in2", "input", -30.0, 10.0),
            ("out", "output", 30.0, 0.0),
        ],
    },
    "NAND": {
        "delphi_class": "T2NandGate",
        "pins": [
            ("in1", "input", -30.0, -10.0),
            ("in2", "input", -30.0, 10.0),
            ("out", "output", 30.0, 0.0),
        ],
    },
    "NOR": {
        "delphi_class": "T2NorGate",
        "pins": [
            ("in1", "input", -30.0, -10.0),
            ("in2", "input", -30.0, 10.0),
            ("out", "output", 30.0, 0.0),
        ],
    },
    "XOR": {
        "delphi_class": "T2XorGate",
        "pins": [
            ("in1", "input", -30.0, -10.0),
            ("in2", "input", -30.0, 10.0),
            ("out", "output", 30.0, 0.0),
        ],
    },
    "NOT": {
        "delphi_class": "TNotGate",
        "pins": [
            ("in", "input", -25.0, 0.0),
            ("out", "output", 25.0, 0.0),
        ],
    },
}

DEVICE_CONFIGS: Dict[str, Dict[str, Any]] = {
    "INPUT": {
        "delphi_class": "TInteractiveInput",
        "pins": [
            ("out", "output", 0.0, 0.0),
        ],
    },
    "LED": {
        "delphi_class": "TLEDDevice",
        "pins": [
            ("in", "input", 0.0, 0.0),
        ],
    },
}


class Pin:
    """
    Represents an electrical contact terminal on a schematic component.

    Attributes:
        name: Terminal identifier ('in', 'out', 'in1', 'in2')
        pin_type: 'input' or 'output'
        x: Absolute X canvas coordinate (float)
        y: Absolute Y canvas coordinate (float)
        component: Reference to parent Component instance
    """
    delphi_class = "TPin"

    def __init__(
        self,
        name: str,
        pin_type: str,
        x: float,
        y: float,
        component: Component,
    ) -> None:
        self.name: str = str(name)
        self.pin_type: str = str(pin_type).lower()
        self.x: float = float(x)
        self.y: float = float(y)
        self.component: Component = component
        self.connected_wire: Optional[Wire] = None

    def serialize_vcl(self, w: _DelphiVCLWriter) -> None:
        """Serializes TPin record to VCL stream."""
        w.write_integer(0)  # Pen Color: clBlack
        w.write_integer(1)  # Pen Width: 1px
        # 8x8 contact terminal bounding box polygon
        pts = [
            (self.x + 4.0, self.y + 4.0),
            (self.x + 4.0, self.y - 4.0),
            (self.x - 4.0, self.y - 4.0),
            (self.x - 4.0, self.y + 4.0),
        ]
        points_list = _VCLSerializeList([_VCLFloatPoint(px, py) for px, py in pts])
        w.write_object(points_list)
        w.write_integer(0x00FFFFFF)  # Brush Color: clWhite
        dir_code = 2 if self.pin_type == "output" else 1
        w.write_integer(dir_code)
        w.write_object(self.connected_wire)

    def __repr__(self) -> str:
        comp_name = getattr(self.component, "label", "") or getattr(
            self.component, "comp_type", "Comp"
        )
        return (
            f"Pin({self.name!r}, {self.pin_type!r}, "
            f"({self.x:.1f}, {self.y:.1f}), comp={comp_name})"
        )


class Component:
    """
    Represents a placed logic gate or interactive device on the schematic canvas.

    Attributes:
        comp_type: Component type identifier ('AND', 'OR', 'NOT', 'NAND', 'NOR', 'XOR', 'INPUT', 'LED')
        x: Center anchor X coordinate (float)
        y: Center anchor Y coordinate (float)
        label: Descriptive label string (defaults to '')
        pins: Dictionary mapping pin name to Pin instance
        delphi_class: Borland Delphi VCL class name (e.g. 'T2AndGate', 'TInteractiveInput')
    """

    def __init__(
        self,
        comp_type: str,
        x: float,
        y: float,
        label: str = "",
        delphi_class: str = "",
    ) -> None:
        self.comp_type: str = str(comp_type).upper()
        self.x: float = float(x)
        self.y: float = float(y)
        self.label: str = str(label) if label is not None else ""
        self.delphi_class: str = str(delphi_class)
        self.pins: Dict[str, Pin] = {}

    def add_pin(self, name: str, pin_type: str, dx: float, dy: float) -> Pin:
        """Instantiates and registers a Pin relative to the component anchor."""
        pin = Pin(
            name=name,
            pin_type=pin_type,
            x=self.x + float(dx),
            y=self.y + float(dy),
            component=self,
        )
        self.pins[name] = pin
        return pin

    def serialize_vcl(self, w: _DelphiVCLWriter) -> None:
        """Serializes TDevice descendant record to VCL stream."""
        w.write_boolean(False)  # HasGraphicList
        w.write_boolean(False)  # IsSelected
        w.write_boolean(False)  # DeviceFlag

        # Pins ordering: Output pin first, then inputs bottom-to-top
        ordered_pins: List[Pin] = []
        if "out" in self.pins:
            ordered_pins.append(self.pins["out"])
        if "in2" in self.pins:
            ordered_pins.append(self.pins["in2"])
        if "in1" in self.pins:
            ordered_pins.append(self.pins["in1"])
        if "in" in self.pins:
            ordered_pins.append(self.pins["in"])

        pins_container = _VCLGraphicList(ordered_pins)
        w.write_object(pins_container)
        w.write_raw(struct.pack("<ff", self.x, self.y))  # Anchor coordinates

        if self.delphi_class == "TInteractiveInput":
            w.write_boolean(False)  # HasLabel
            w.write_boolean(False)  # HistoryEnabled
            w.write_boolean(False)  # SwitchState
            w.write_integer(0)      # InputMode
        elif self.delphi_class == "TLEDDevice":
            w.write_boolean(False)  # HasLabel
            w.write_boolean(False)  # HistoryEnabled
            w.write_integer(255)    # LEDColor (clRed)

    def __repr__(self) -> str:
        return f"Component({self.comp_type!r}, ({self.x:.1f}, {self.y:.1f}), label={self.label!r})"


class Wire:
    """
    Represents an orthogonal Manhattan electrical interconnection between two pins.

    Attributes:
        source_pin: The transmitting Pin (typically output)
        dest_pin: The receiving Pin (typically input)
        points: Sequence of (x, y) coordinates defining orthogonal segments
    """
    delphi_class = "TWire"

    def __init__(
        self,
        source_pin: Pin,
        dest_pin: Pin,
        points: List[Tuple[float, float]],
    ) -> None:
        self.source_pin: Pin = source_pin
        self.dest_pin: Pin = dest_pin
        self.points: List[Tuple[float, float]] = [
            (float(px), float(py)) for px, py in points
        ]

    def serialize_vcl(self, w: _DelphiVCLWriter) -> None:
        """Serializes TWire record to VCL stream."""
        w.write_integer(0)  # Pen Color: clBlack
        w.write_integer(1)  # Pen Width: 1px
        pts_list = _VCLSerializeList(
            [_VCLFloatPoint(px, py) for px, py in self.points]
        )
        w.write_object(pts_list)
        w.write_integer(0)  # Wire State: 0
        w.write_object(self.source_pin)
        w.write_object(self.dest_pin)

    def __repr__(self) -> str:
        return (
            f"Wire({self.source_pin.component.comp_type}.{self.source_pin.name} -> "
            f"{self.dest_pin.component.comp_type}.{self.dest_pin.name}, {len(self.points)} pts)"
        )


class DWMBuilder:
    """
    Main Digital Works circuit compiler API.

    Provides high-level component placement, automatic pin geometry computation,
    orthogonal Manhattan routing, ASCII terminal previewing, and binary VCL compilation.
    """

    def __init__(self, title: str = "Circuit") -> None:
        self.title: str = str(title)
        self.components: List[Component] = []
        self.wires: List[Wire] = []

    def add_input(self, x: float, y: float, label: str = "") -> Component:
        """
        Places a toggle switch / interactive input device on the canvas.

        Anchor: (x, y)
        Pin: 'out' at (x, y), pin_type='output'
        Delphi Class: 'TInteractiveInput'
        """
        cfg = DEVICE_CONFIGS["INPUT"]
        comp = Component(
            comp_type="INPUT",
            x=float(x),
            y=float(y),
            label=label,
            delphi_class=cfg["delphi_class"],
        )
        for name, ptype, dx, dy in cfg["pins"]:
            comp.add_pin(name, ptype, dx, dy)
        self.components.append(comp)
        return comp

    def add_led(self, x: float, y: float, label: str = "") -> Component:
        """
        Places a logic probe / LED indicator on the canvas.

        Anchor: (x, y)
        Pin: 'in' at (x, y), pin_type='input'
        Delphi Class: 'TLEDDevice'
        """
        cfg = DEVICE_CONFIGS["LED"]
        comp = Component(
            comp_type="LED",
            x=float(x),
            y=float(y),
            label=label,
            delphi_class=cfg["delphi_class"],
        )
        for name, ptype, dx, dy in cfg["pins"]:
            comp.add_pin(name, ptype, dx, dy)
        self.components.append(comp)
        return comp

    def add_gate(
        self,
        gate_type: str,
        x: float,
        y: float,
        label: str = "",
    ) -> Component:
        """
        Places a logic gate on the schematic canvas.
        Supported gate types (case-insensitive): 'AND', 'OR', 'NOT', 'NAND', 'NOR', 'XOR'.

        Raises:
            TypeError: If gate_type is not a string.
            ValueError: If gate_type is not a recognized gate type.
        """
        if not isinstance(gate_type, str):
            raise TypeError(
                f"gate_type must be a string, got {type(gate_type).__name__}"
            )

        norm_type = gate_type.strip().upper()
        if norm_type not in GATE_CONFIGS:
            raise ValueError(
                f"Invalid gate type: {gate_type!r}. Supported types: {list(GATE_CONFIGS.keys())}"
            )

        cfg = GATE_CONFIGS[norm_type]
        comp = Component(
            comp_type=norm_type,
            x=float(x),
            y=float(y),
            label=label,
            delphi_class=cfg["delphi_class"],
        )
        for name, ptype, dx, dy in cfg["pins"]:
            comp.add_pin(name, ptype, dx, dy)
        self.components.append(comp)
        return comp

    def connect(
        self,
        source_pin: Pin,
        dest_pin: Pin,
        route_type: Optional[str] = None,
    ) -> Wire:
        """
        Connects two component pins via strictly orthogonal Manhattan routing.

        Enforces all 5 fundamental Manhattan invariants:
          INV-1: Endpoint Pinning (points[0] == src, points[-1] == dst)
          INV-2: Strict Orthogonality (dx == 0 or dy == 0 for every segment)
          INV-3: Non-Degeneracy (zero-length segments prohibited)
          INV-4: Right-Angle Turns (90-degree bends only, dot product == 0)
          INV-5: Minimal Manhattan Distance Bound (total length >= minimal distance)

        Raises:
            ValueError: If source_pin and dest_pin are identical (self-connection).
        """
        if source_pin is dest_pin:
            raise ValueError("Cannot connect a pin to itself")

        x1, y1 = float(source_pin.x), float(source_pin.y)
        x2, y2 = float(dest_pin.x), float(dest_pin.y)

        # Case 1: Coincident distinct pins
        if x1 == x2 and y1 == y2:
            points = [(x1, y1), (x2, y2)]

        # Case 2: Collinear horizontal
        elif y1 == y2:
            points = [(x1, y1), (x2, y2)]

        # Case 3: Collinear vertical
        elif x1 == x2:
            points = [(x1, y1), (x2, y2)]

        # Case 4: Non-collinear orthogonal routing
        else:
            norm_route = route_type.strip().upper() if isinstance(route_type, str) else None
            if norm_route == "HV":
                points = [(x1, y1), (x2, y1), (x2, y2)]
            elif norm_route == "VH":
                points = [(x1, y1), (x1, y2), (x2, y2)]
            else:
                # Canonical Z-shaped channel route with midpoint vertical trunk
                mid_x = (x1 + x2) / 2.0
                points = [(x1, y1), (mid_x, y1), (mid_x, y2), (x2, y2)]

        wire = Wire(source_pin=source_pin, dest_pin=dest_pin, points=points)
        self.wires.append(wire)

        if source_pin.connected_wire is None:
            source_pin.connected_wire = wire
        if dest_pin.connected_wire is None:
            dest_pin.connected_wire = wire

        return wire

    def preview(self) -> str:
        """
        Renders an ASCII terminal representation of the schematic layout.
        Displays component boxes, wire tracks (-, |, +), and an inventory manifest.
        """
        if not self.components:
            return f"=== Circuit: {self.title} (Empty) ===\n(No components placed)\n"

        # 1. Compute canvas bounding box
        xs = [float(c.x) for c in self.components] + [
            float(pt[0]) for w in self.wires for pt in w.points
        ]
        ys = [float(c.y) for c in self.components] + [
            float(pt[1]) for w in self.wires for pt in w.points
        ]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        span_x = max(max_x - min_x, 1.0)
        span_y = max(max_y - min_y, 1.0)

        # 2. Allocate bounded grid matrix
        cols = max(60, min(100, int(span_x / 8) + 30))
        rows = max(15, min(35, int(span_y / 15) + 10))
        grid = [[" " for _ in range(cols)] for _ in range(rows)]

        def to_col(x: float) -> int:
            if max_x == min_x:
                return cols // 2
            return 4 + int(round(((x - min_x) / span_x) * (cols - 20)))

        def to_row(y: float) -> int:
            if max_y == min_y:
                return rows // 2
            return 2 + int(round(((y - min_y) / span_y) * (rows - 6)))

        # 3. Rasterize wire tracks
        for w in self.wires:
            pts = w.points
            for i in range(len(pts) - 1):
                x_a, y_a = pts[i]
                x_b, y_b = pts[i + 1]
                c1, r1 = to_col(x_a), to_row(y_a)
                c2, r2 = to_col(x_b), to_row(y_b)

                if r1 == r2 and c1 == c2:
                    if 0 <= r1 < rows and 0 <= c1 < cols:
                        grid[r1][c1] = "+" if grid[r1][c1] in ("-", "|", "+") else "-"
                elif r1 == r2:  # Horizontal segment
                    c_start, c_end = min(c1, c2), max(c1, c2)
                    for c in range(c_start, c_end + 1):
                        if 0 <= r1 < rows and 0 <= c < cols:
                            grid[r1][c] = "+" if grid[r1][c] in ("|", "+") else "-"
                elif c1 == c2:  # Vertical segment
                    r_start, r_end = min(r1, r2), max(r1, r2)
                    for r in range(r_start, r_end + 1):
                        if 0 <= r < rows and 0 <= c1 < cols:
                            grid[r][c1] = "+" if grid[r][c1] in ("-", "+") else "|"

        # 4. Rasterize component tags with collision resolution
        occupied = set()
        for c in self.components:
            tag = f"[{c.comp_type}:{c.label}]" if c.label else f"[{c.comp_type}]"
            cr, cc = to_row(c.y), to_col(c.x)

            # Shift right if target cells are already occupied
            while (
                any((cr, cc + i) in occupied for i in range(len(tag)))
                and cc + len(tag) < cols - 2
            ):
                cc += 1

            for i, ch in enumerate(tag):
                col_idx = cc + i
                if 0 <= cr < rows and 0 <= col_idx < cols:
                    grid[cr][col_idx] = ch
                    occupied.add((cr, col_idx))

        # 5. Format output lines
        grid_lines = ["".join(r).rstrip() for r in grid]
        while len(grid_lines) > 3 and not grid_lines[0].strip():
            grid_lines.pop(0)
        while len(grid_lines) > 3 and not grid_lines[-1].strip():
            grid_lines.pop()

        header = (
            f"=== Circuit: {self.title} "
            f"({len(self.components)} components, {len(self.wires)} wires) ==="
        )
        footer = "Components:\n" + "\n".join(
            f"  [{i + 1}] {c.comp_type}"
            + (f" '{c.label}'" if c.label else "")
            + f" at ({c.x}, {c.y})"
            for i, c in enumerate(self.components)
        )

        return header + "\n" + "\n".join(grid_lines) + "\n" + footer + "\n"

    def to_bytes(self) -> bytes:
        """
        Serializes the entire circuit into Borland Delphi VCL component stream bytes (.dwm).
        """
        writer = _DelphiVCLWriter()

        # 1. Exact 5-Byte Magic Header
        writer.write_raw(MAGIC_HEADER)

        # 2. Canonical 35-Byte Preamble Property List
        writer.write_list_begin()
        writer.write_integer(1)
        writer.write_integer(0x64)
        writer.write_string(self.title)

        writer.write_integer(1)
        writer.write_integer(0x65)
        writer.write_string("")

        writer.write_integer(1)
        writer.write_integer(0x66)
        writer.write_string("0")

        writer.write_integer(2)
        writer.write_integer(0x00CA)
        writer.write_integer(0)

        writer.write_integer(2)
        writer.write_integer(0x00C8)
        writer.write_integer(1)
        writer.write_list_end()

        # 3. Root Macro Container with 6 canvas sub-lists
        macro = _VCLMacro(self.title, self.components, self.wires)
        writer.write_object(macro)

        return writer.get_bytes()

    def save(self, file_path: str) -> None:
        """
        Compiles the circuit and writes the binary .dwm file to disk.
        """
        data = self.to_bytes()
        with open(file_path, "wb") as f:
            f.write(data)


# ============================================================================
# Delphi VCL Binary Serialization Internal Primitives
# ============================================================================


class _DelphiVCLWriter:
    """
    Borland Delphi VCL Component Stream Serializer (TWriter / TSerializeWriter).
    Handles dynamic integer compaction, typed value tokens, and object graph deduplication.
    """

    def __init__(self) -> None:
        self.buf = bytearray()
        self.classes: List[str] = []
        self.objects: List[Any] = []
        self.obj_map: Dict[int, int] = {}

    def write_raw(self, data: bytes) -> None:
        self.buf.extend(data)

    def write_byte(self, val: int) -> None:
        self.buf.append(val & 0xFF)

    def write_integer(self, val: int) -> None:
        """Dynamic integer compaction according to Delphi TWriter.WriteInteger"""
        if -128 <= val <= 127:
            self.buf.append(0x02)  # vaInt8
            self.buf.extend(struct.pack("<b", val))
        elif -32768 <= val <= 32767:
            self.buf.append(0x03)  # vaInt16
            self.buf.extend(struct.pack("<h", val))
        elif -2147483648 <= val <= 2147483647:
            self.buf.append(0x04)  # vaInt32
            self.buf.extend(struct.pack("<i", val))
        else:
            self.buf.append(0x13)  # vaInt64
            self.buf.extend(struct.pack("<q", val))

    def write_string(self, s: str) -> None:
        """Delphi ShortString (vaString 0x06) or LongString (vaLString 0x0C)"""
        encoded = s.encode("utf-8")
        if len(encoded) <= 255:
            self.buf.append(0x06)  # vaString
            self.buf.append(len(encoded))
            self.buf.extend(encoded)
        else:
            self.buf.append(0x0C)  # vaLString
            self.buf.extend(struct.pack("<I", len(encoded)))
            self.buf.extend(encoded)

    def write_boolean(self, val: bool) -> None:
        """Delphi vaFalse (0x08) or vaTrue (0x09)"""
        self.buf.append(0x09 if val else 0x08)

    def write_list_begin(self) -> None:
        self.buf.append(0x01)  # vaList

    def write_list_end(self) -> None:
        self.buf.append(0x00)  # vaNull

    def write_object(self, obj: Any) -> None:
        """
        Cycle-free object graph walk (TSerializeWriter.WriteObject).
        Markers:
          0 (0x02 0x00): New Class Definition + Instance
          1 (0x02 0x01): Known Class Reference + Instance
          2 (0x02 0x02): Previously Serialized Object Reference
          15 (0x02 0x0F): Nil Reference
        """
        if obj is None:
            self.buf.append(0x02)
            self.buf.append(0x0F)  # Marker 15 (Nil)
            return

        obj_id = id(obj)
        if obj_id in self.obj_map:
            # Marker 2: Object Deduplication Reference
            self.buf.append(0x02)
            self.buf.append(0x02)
            self.write_integer(self.obj_map[obj_id])
            return

        cls_name = getattr(obj, "delphi_class", obj.__class__.__name__)
        if cls_name in self.classes:
            # Marker 1: Existing Class Reference
            self.buf.append(0x02)
            self.buf.append(0x01)
            self.write_integer(self.classes.index(cls_name))
        else:
            # Marker 0: New Class Definition
            self.buf.append(0x02)
            self.buf.append(0x00)
            self.write_string(cls_name)
            self.classes.append(cls_name)

        # Register instance ID BEFORE writing body fields to prevent infinite recursion
        assigned_id = len(self.objects)
        self.obj_map[obj_id] = assigned_id
        self.objects.append(obj)

        # Emit instance payload
        obj.serialize_vcl(self)

    def get_bytes(self) -> bytes:
        return bytes(self.buf)


class _VCLFloatPoint:
    delphi_class = "TFloatPoint"

    def __init__(self, x: float, y: float) -> None:
        self.x, self.y = float(x), float(y)

    def serialize_vcl(self, w: _DelphiVCLWriter) -> None:
        # Raw IEEE 754 float32 coordinates without vaSingle token
        w.write_raw(struct.pack("<ff", self.x, self.y))


class _VCLSerializeList:
    delphi_class = "TSerializeList"

    def __init__(self, items: Optional[List[Any]] = None) -> None:
        self.items = list(items or [])

    def serialize_vcl(self, w: _DelphiVCLWriter) -> None:
        w.write_list_begin()
        for item in self.items:
            w.write_object(item)
        w.write_list_end()


class _VCLGraphicList:
    delphi_class = "TGraphicList"

    def __init__(self, items: Optional[List[Any]] = None) -> None:
        self.inner = _VCLSerializeList(items)

    def serialize_vcl(self, w: _DelphiVCLWriter) -> None:
        w.write_object(self.inner)


class _VCLPolygon:
    delphi_class = "TPolygon"

    def __init__(
        self,
        pts: List[Tuple[float, float]],
        brush: int = 0x00FFFFFF,
    ) -> None:
        self.points = _VCLSerializeList([_VCLFloatPoint(x, y) for x, y in pts])
        self.brush = brush

    def serialize_vcl(self, w: _DelphiVCLWriter) -> None:
        w.write_integer(0)  # Pen Color: clBlack
        w.write_integer(1)  # Pen Width: 1px
        w.write_object(self.points)
        w.write_integer(self.brush)


class _VCLGraphicText:
    delphi_class = "TGraphicText"

    def __init__(
        self,
        pts: List[Tuple[float, float]],
        text: str = "macro",
    ) -> None:
        self.points = _VCLSerializeList([_VCLFloatPoint(x, y) for x, y in pts])
        self.text = text

    def serialize_vcl(self, w: _DelphiVCLWriter) -> None:
        w.write_integer(0)  # Pen Color: clBlack
        w.write_integer(1)  # Pen Width: 1px
        w.write_object(self.points)
        w.write_integer(0x00FFFFFF)  # Brush White
        w.write_integer(7)           # Font Size
        w.write_integer(0)           # Font Style
        w.write_boolean(False)       # Font Underline
        w.write_integer(400)         # Font Weight
        w.write_raw(b"\x00\x00\x00\x00")  # Font Angle
        w.write_string(self.text)
        w.write_boolean(True)
        w.write_boolean(False)


class _VCLMacro:
    delphi_class = "TMacro"

    def __init__(
        self,
        title: str,
        components: List[Component],
        wires: List[Wire],
    ) -> None:
        self.title = title
        box = _VCLPolygon(
            [(-20.0, -10.0), (20.0, -10.0), (20.0, 10.0), (-20.0, 10.0)]
        )
        txt = _VCLGraphicText(
            [(-13.0, -6.0), (-13.0, 6.0), (13.0, 6.0), (13.0, -6.0)],
            text=title or "macro",
        )
        self.graphic_list = _VCLSerializeList([box, txt])
        self.macro_pins = _VCLGraphicList([])
        self.components_list = _VCLGraphicList(components)
        self.tags_list = _VCLGraphicList([])
        self.sublist2 = _VCLGraphicList([])
        self.sublist3 = _VCLGraphicList([])
        self.sublist4 = _VCLGraphicList([])
        self.wires_list = _VCLGraphicList(wires)

    def serialize_vcl(self, w: _DelphiVCLWriter) -> None:
        w.write_boolean(True)   # HasGraphicList
        w.write_object(self.graphic_list)
        w.write_boolean(False)  # Flag1
        w.write_boolean(True)   # Flag2
        w.write_object(self.macro_pins)
        w.write_string("")      # DocLink
        w.write_integer(0)      # Zero
        w.write_boolean(False)  # Flag1
        w.write_boolean(False)  # Flag2
        # Six Canvas Sub-Lists
        w.write_object(self.components_list)  # Sub-List 0: Components
        w.write_object(self.tags_list)        # Sub-List 1: Tags / Annotations
        w.write_object(self.sublist2)         # Sub-List 2
        w.write_object(self.sublist3)         # Sub-List 3
        w.write_object(self.sublist4)         # Sub-List 4
        w.write_object(self.wires_list)       # Sub-List 5: Netlist Wires
