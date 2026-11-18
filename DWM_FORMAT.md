# Digital Works 3.04 Binary File Format Specification (`.dwm`)

**Document Revision**: 1.0.0 (Publication-Grade Standard)  
**Target Environment**: Digital Works 3.04 / 3.4 (`DigitalWorks.exe`, Borland Delphi VCL)  
**Applicability**: Authoritative binary serialization reference for the `dwm_circuit_compiler` suite (`dwm_builder.py`, `test_builder.py`, and E2E validation harness)  
**Authors**: Teamwork Reverse-Engineering Special Task Force (Milestone 1)  
**Date**: November 2026  

---

## Table of Contents

1. [Section 1: File Header, Magic Signature, Versioning & Preamble](#section-1-file-header-magic-signature-versioning--preamble)
   - 1.1 [Exact 5-Byte File Signature & Magic Constant](#11-exact-5-byte-file-signature--magic-constant)
   - 1.2 [Format Version Comparison Matrix](#12-format-version-comparison-matrix)
   - 1.3 [Container Macro Preamble Metadata (`0x22`)](#13-container-macro-preamble-metadata-0x22)
   - 1.4 [Minimal Canonical Preamble Byte Sequence](#14-minimal-canonical-preamble-byte-sequence)
2. [Section 2: Borland Delphi VCL Serialization Stream Protocol](#section-2-borland-delphi-vcl-serialization-stream-protocol)
   - 2.1 [Delphi VCL Streaming Architecture (`TWriter` / `TReader`)](#21-delphi-vcl-streaming-architecture-twriter--treader)
   - 2.2 [Complete `TValueType` Enum Reference Table (0..19)](#22-complete-tvaluetype-enum-reference-table-019)
   - 2.3 [Dynamic Integer & String Compaction Rules](#23-dynamic-integer--string-compaction-rules)
   - 2.4 [Critical Exception: Un-tagged Coordinate Serialization (`TFloatPoint`)](#24-critical-exception-un-tagged-coordinate-serialization-tfloatpoint)
3. [Section 3: Object Serialization & Graph Deduplication Engine (`TSerializeWriter`)](#section-3-object-serialization--graph-deduplication-engine-tserializewriter)
   - 3.1 [Architectural Overview & Dynamic Registries](#31-architectural-overview--dynamic-registries)
   - 3.2 [The Four Serialization Markers (0, 1, 2, 15)](#32-the-four-serialization-markers-0-1-2-15)
   - 3.3 [Object Graph Walk & Cycle-Free Serialization Algorithm](#33-object-graph-walk--cycle-free-serialization-algorithm)
   - 3.4 [Container List Serialization (`TSerializeList`)](#34-container-list-serialization-tserializelist)
4. [Section 4: Component Record Structures & RTTI Class Hierarchy](#section-4-component-record-structures--rtti-class-hierarchy)
   - 4.1 [Complete Delphi VCL Class Hierarchy](#41-complete-delphi-vcl-class-hierarchy)
   - 4.2 [Virtual Method Table (VMT) Dispatch & Instance Sizes](#42-virtual-method-table-vmt-dispatch--instance-sizes)
   - 4.3 [Concrete Serialization Schemas for Logic Gates](#43-concrete-serialization-schemas-for-logic-gates)
   - 4.4 [Concrete Serialization Schemas for Interactive I/O & Displays](#44-concrete-serialization-schemas-for-interactive-io--displays)
   - 4.5 [Concrete Serialization Schemas for Connectivity Primitives](#45-concrete-serialization-schemas-for-connectivity-primitives)
5. [Section 5: Coordinate System & Geometry Specification](#section-5-coordinate-system--geometry-specification)
   - 5.1 [Canvas Plane, Orientation & Origin](#51-canvas-plane-orientation--origin)
   - 5.2 [5 px Grid Snapping Invariants & Formulations](#52-5-px-grid-snapping-invariants--formulations)
   - 5.3 [IEEE 754 32-Bit Float Coordinate Storage](#53-ieee-754-32-bit-float-coordinate-storage)
   - 5.4 [Pin Contact Terminal Bounding Box Geometry](#54-pin-contact-terminal-bounding-box-geometry)
6. [Section 6: Pin Coordinate Calculation Formulas & Offset Tables](#section-6-pin-coordinate-calculation-formulas--offset-tables)
   - 6.1 [Mathematical Formulation for Absolute Pin Coordinates](#61-mathematical-formulation-for-absolute-pin-coordinates)
   - 6.2 [Empirical Ground Truth: Asymmetric NOT Gate Geometry](#62-empirical-ground-truth-asymmetric-not-gate-geometry)
   - 6.3 [Master Pin Relative Offset Table (All 26 Components)](#63-master-pin-relative-offset-table-all-26-components)
   - 6.4 [Multi-Input Gate Vertical Spacing Geometry](#64-multi-input-gate-vertical-spacing-geometry)
7. [Section 7: Wire Record Layout & Manhattan Orthogonal Routing](#section-7-wire-record-layout--manhattan-orthogonal-routing)
   - 7.1 [Wire Serialization Model (`TWire`)](#71-wire-serialization-model-twire)
   - 7.2 [Manhattan Routing Invariants & Prohibited Topologies](#72-manhattan-routing-invariants--prohibited-topologies)
   - 7.3 [Canonical Routing Topologies (Collinear, L-Shaped, Z-Shaped)](#73-canonical-routing-topologies-collinear-l-shaped-z-shaped)
   - 7.4 [Multi-Drop Nets & `TSolder` Joint Topology](#74-multi-drop-nets--tsolder-joint-topology)
8. [Section 8: Comprehensive Annotated Reference Seed Hex Dumps](#section-8-comprehensive-annotated-reference-seed-hex-dumps)
   - 8.1 [Minimal Empty Macro Seed (`empty_macro_minimal.dwm`, 380 Bytes)](#81-minimal-empty-macro-seed-empty_macro_minimaldwm-380-bytes)
   - 8.2 [2-Input AND Gate Seed (`gate_and_2in.dwm`, 1,913 Bytes)](#82-2-input-and-gate-seed-gate_and_2indwm-1913-bytes)
   - 8.3 [Interactive Input, LED & Wire Seed (`io_switch_led_wire.dwm`, 2,520 Bytes)](#83-interactive-input-led--wire-seed-io_switch_led_wiredwm-2520-bytes)
   - 8.4 [Circuit Half Adder with Solder Joints (`circuit_half_adder.dwm`, 3,581 Bytes)](#84-circuit-half-adder-with-solder-joints-circuit_half_adderdwm-3581-bytes)
9. [Section 9: Compiler Implementation Checklist & Verification Harness](#section-9-compiler-implementation-checklist--verification-harness)

---

# Section 1: File Header, Magic Signature, Versioning & Preamble

## 1.1 Exact 5-Byte File Signature & Magic Constant

Every authentic Digital Works 3.04 circuit document (`.dwm`) begins with an invariant 5-byte sequence:

```hex
04 DD C4 22 00
```

### Disassembly Proof & Origin in `DigitalWorks.exe`
Binary disassembly of the document serialization procedure in `DigitalWorks.exe` (PE32 executable, base `0x400000`, compiled with Borland Delphi 4) reveals the exact origin of these five bytes:

```x86asm
; DigitalWorks.exe - Save Document Routine (Virtual Address 0x484810)
0x484810: mov eax, dword ptr [0x4525d8]    ; Load TSerializeWriter class reference
0x484815: call 0x452954                   ; Instantiate TSerializeWriter (Create)
0x48481a: mov ebx, eax                    ; ebx = writer instance pointer
0x48481c: mov dword ptr [ebx + 0x58], 0xc4dd  ; Format Signature Constant = 0xC4DD (50,397)
0x484823: mov byte ptr [ebx + 0x60], 0x22    ; Format Version Code = 0x22 (34 decimal)
0x484827: mov eax, ebx
0x484829: call 0x452c78                   ; Call WriteHeader(writer)

; DigitalWorks.exe - WriteHeader Routine (Virtual Address 0x452c78)
0x452c78: xor edx, edx
0x452c7a: mov dl, byte ptr [eax + 0x60]   ; Load version byte (0x22)
0x452c7d: shl edx, 0x10                   ; Shift left by 16: edx = 0x00220000
0x452c80: or edx, dword ptr [eax + 0x58]  ; Bitwise OR with signature: edx = 0x0022C4DD
0x452c83: call 0x4147c4                   ; Call TWriter.WriteInteger(edx)
0x452c88: ret
```

### Breakdown of the 5-Byte Header:
1. **Byte 0 (`0x04`)**: Delphi VCL type tag `vaInt32`. Because the integer argument `0x0022C4DD` equals $2,278,621$ decimal, it exceeds the 16-bit signed integer boundary ($[-32768, 32767]$). Therefore, `TWriter.WriteInteger` selects `vaInt32` (`0x04`).
2. **Bytes 1..4 (`\xdd\xc4\x22\x00`)**: Little-endian 32-bit unsigned/signed integer representing `0x0022C4DD`:
   - `0xDD, 0xC4` (low word = `0xC4DD` = 50,397): Unique application magic constant for Digital Works.
   - `0x22, 0x00` (high word = `0x0022` = 34 decimal): Format version indicator (Digital Works 3.04 / 3.4).

---

## 1.2 Format Version Comparison Matrix

Inspection of the entire Digital Works 3.04 distribution and legacy project archives reveals three historical formats:

| Format Version | Magic Dword (Hex) | 5-Byte Header | Release Era | Preamble Structure | Distribution Prevalence |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`0x14`** (20 dec) | `0x0014C4DD` | `04 DD C4 14 00` | Digital Works 2.0 (16-bit Windows 3.1) | **None**: Followed immediately by root `TMacro` object (`02 00 06 06 54 4D 61 63 72 6F...`). | 3 files (e.g., `TRISTATE.DWM`) |
| **`0x1E`** (30 dec) | `0x001EC4DD` | `04 DD C4 1E 00` | Digital Works 3.0 (Win95 Release) | **Sequential Untagged Fields**: `08` (`vaFalse`), `vaString` Title, `vaString` Doc Link, `02 00` (`vaInt8` 0), followed by root `TMacro`. | 51 files (e.g., `74hc76.dwm`, `circuit_jk_flipflop.dwm`) |
| **`0x22`** (34 dec) | **`0x0022C4DD`** | **`04 DD C4 22 00`** | **Digital Works 3.04 / 3.4 (Current)** | **Tagged Property List**: Opening `vaList` (`0x01`), typed key-value pairs, terminated by `vaNull` (`0x00`). Followed by root `TMacro`. | **311 files (87% of all library circuits)** |

*Requirement for Downstream Compiler*: `dwm_builder.py` must emit version `0x22` (`04 DD C4 22 00`).

---

## 1.3 Container Macro Preamble Metadata (`0x22`)

Immediately following the 5-byte header in version `0x22`, `DigitalWorks.exe` writes a tagged metadata property list describing document authoring attributes.

### Assembly Disassembly of Preamble Writer (`VA 0x452c8c` - `0x452d0a`)
```x86asm
0x452c92: mov eax, esi
0x452c94: call 0x414890    ; TWriter.WriteListBegin() -> emits 0x01 (vaList)
... [loop over registered document properties]
0x452cb3: mov edx, [ebx + 8]   ; Property Data Type (1 = String, 2 = Integer, 3 = Boolean)
0x452cb8: call 0x4147c4       ; TWriter.WriteInteger(item_type) -> emits 0x02 <item_type>
0x452cbd: mov edx, [ebx + 4]   ; Tag Identifier (e.g. 0x64, 0x65, 0x66, 0xCA, 0xC8)
0x452cc2: call 0x4147c4       ; TWriter.WriteInteger(tag_id) -> emits 0x02 <tag_id> or 0x03 <tag_id_le16>
; Value serialization based on item_type:
; If item_type == 1 (String):  call TWriter.WriteString  -> 0x06 <len> <chars>
; If item_type == 2 (Integer): call TWriter.WriteInteger -> 0x02/0x03/0x04 <value>
; If item_type == 3 (Boolean): call TWriter.WriteBoolean -> 0x08 (False) or 0x09 (True)
...
0x452cff: mov eax, esi
0x452d01: call 0x414898    ; TWriter.WriteListEnd() -> emits 0x00 (vaNull)
```

### Complete Preamble Property Tag Dictionary

| Tag ID (Hex) | Tag ID (Dec) | Data Type | Value Encoding | Field Semantics | Standard Emission Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`0x64`** | 100 | 1 (`vaString`) | `06 <len> <string>` | Circuit Title / Macro Label | `""` (empty string) or title (e.g., `"Half Adder"`) |
| **`0x65`** | 101 | 1 (`vaString`) | `06 <len> <string>` | External Documentation HTML Link / File Path | `""` (empty string) or path (e.g., `"hello.htm"`) |
| **`0x66`** | 102 | 1 (`vaString`) | `06 <len> <string>` | Circuit Revision String | `"0"` (`06 01 30`) or `""` |
| **`0xCA`** | 202 | 2 (`vaInt8` / `vaInt16`) | `03 CA 00 02 <val>` | Display & Visibility Flags | `0` (`0x02 0x00`) |
| **`0xC8`** | 200 | 2 (`vaInt8` / `vaInt16`) | `03 C8 00 02 <val>` | Macro Palette Template Flags | `1` (`0x02 0x01`) or `0` (`0x02 0x00`) |
| **`0xC9`** | 201 | 1 (`vaString`) | `06 08 <8 bytes>` | Internal Library GUID / Timestamp | Optional: 8 binary bytes (present in IC library parts) |

*Important Integer Encoding Rule for Tags `0xCA` and `0xC8`*: Because tag numbers $202$ and $200$ exceed the signed 8-bit limit ($127$), Delphi encodes the Tag ID parameter as `vaInt16` (`0x03 0xCA 0x00` and `0x03 0xC8 0x00`).

---

## 1.4 Minimal Canonical Preamble Byte Sequence

The exact, standard 35-byte preamble sequence used for standalone circuit compilation (with empty title and documentation) is:

```hex
01 02 01 02 64 06 00 02 01 02 65 06 00 02 01 02 66 06 01 30 02 02 03 CA 00 02 00 02 02 03 C8 00 02 01 00
```

### Detailed Byte-by-Byte Breakdown:
```
01                      ; vaList begin
  02 01                 ; Item type = 1 (String)
  02 64                 ; Tag ID = 0x64 (Circuit Title)
  06 00                 ; vaString length = 0 ("")
  
  02 01                 ; Item type = 1 (String)
  02 65                 ; Tag ID = 0x65 (Doc Link)
  06 00                 ; vaString length = 0 ("")
  
  02 01                 ; Item type = 1 (String)
  02 66                 ; Tag ID = 0x66 (Revision)
  06 01 30              ; vaString length = 1 ("0")
  
  02 02                 ; Item type = 2 (Integer)
  03 CA 00              ; Tag ID = 202 (Display Flags, vaInt16 0x00CA)
  02 00                 ; Integer value = 0 (vaInt8 0)
  
  02 02                 ; Item type = 2 (Integer)
  03 C8 00              ; Tag ID = 200 (Template Options, vaInt16 0x00C8)
  02 01                 ; Integer value = 1 (vaInt8 1)
00                      ; vaNull end of list
```

---

# Section 2: Borland Delphi VCL Serialization Stream Protocol

## 2.1 Delphi VCL Streaming Architecture (`TWriter` / `TReader`)

The `.dwm` format is a direct binary implementation of the Borland Delphi VCL Component Streaming Protocol (`Classes.pas`). The stream is structured as a typed, tagged byte stream where every primitive data value is preceded by a 1-byte `TValueType` token indicator.

```
┌────────────────────────────────────────────────────────┐
│ [1 Byte: TValueType Token] + [0..N Bytes: Data Payload] │
└────────────────────────────────────────────────────────┘
```

---

## 2.2 Complete `TValueType` Enum Reference Table (0..19)

Disassembly of `DigitalWorks.exe` at `VA 0x4158f8` (`TWriter.WriteValue`) and all its callers establishes the complete Delphi 4 `TValueType` token table:

| Token Byte | Enum Identifier | Value Semantics | Payload Specification | Endianness |
| :--- | :--- | :--- | :--- | :--- |
| **`0x00`** | `vaNull` | List / Collection Terminator | 0 bytes (No payload) | N/A |
| **`0x01`** | `vaList` | List / Collection Begin Marker | 0 bytes (No payload) | N/A |
| **`0x02`** | `vaInt8` | 8-bit signed integer | 1 byte: `int8` ($-128 \dots 127$) | N/A |
| **`0x03`** | `vaInt16` | 16-bit signed integer | 2 bytes: `int16` ($-32,768 \dots 32,767$) | Little-Endian |
| **`0x04`** | `vaInt32` | 32-bit signed integer | 4 bytes: `int32` ($-2^{31} \dots 2^{31}-1$) | Little-Endian |
| **`0x05`** | `vaExtended` | 80-bit IEEE 754 extended float | 10 bytes: 80-bit float | Intel 80-bit |
| **`0x06`** | `vaString` | Short string ($\le 255$ chars) | 1 byte unsigned length $N$, followed by $N$ ASCII/ANSI characters | N/A |
| **`0x07`** | `vaIdent` | Pascal Identifier | 1 byte unsigned length $N$, followed by $N$ ASCII characters | N/A |
| **`0x08`** | `vaFalse` | Boolean False | 0 bytes (Token itself conveys `False`) | N/A |
| **`0x09`** | `vaTrue` | Boolean True | 0 bytes (Token itself conveys `True`) | N/A |
| **`0x0A`** | `vaBinary` | Raw Binary Data Block | 4 bytes unsigned length $N$ (`<I`), followed by $N$ raw bytes | Little-Endian |
| **`0x0B`** | `vaSet` | Pascal Bitmask Set | Packed set bitmask bytes | N/A |
| **`0x0C`** | `vaLString` | Long String ($> 255$ chars) | 4 bytes unsigned length $N$ (`<I`), followed by $N$ ASCII/ANSI bytes | Little-Endian |
| **`0x0D`** | `vaNil` | VCL Component Nil pointer | 0 bytes (No payload) | N/A |
| **`0x0E`** | `vaCollection`| TCollection container marker | Collection items stream | N/A |
| **`0x0F`** | `vaSingle` | 32-bit IEEE 754 single float | 4 bytes: single-precision float (`<f`) | Little-Endian |
| **`0x10`** | `vaCurrency` | 64-bit Currency fixed point | 8 bytes: `int64` scaled by $10,000$ | Little-Endian |
| **`0x11`** | `vaDate` | Date/Time (`TDateTime`) | 8 bytes: IEEE 754 double (`<d`, days since 1899-12-30) | Little-Endian |
| **`0x12`** | `vaWString` | UTF-16 Wide String | 4 bytes char count $N$ (`<I`), followed by $2N$ UTF-16LE bytes | Little-Endian |
| **`0x13`** | `vaInt64` | 64-bit signed integer | 8 bytes: `int64` | Little-Endian |

---

## 2.3 Dynamic Integer & String Compaction Rules

### 1. Dynamic Integer Compaction in `TWriter.WriteInteger` (`VA 0x4147c4`)
Delphi does not allocate fixed 32-bit slots for integers. It dynamically compacts integers based on value magnitude:

```python
def write_integer(val: int) -> bytes:
    if -128 <= val <= 127:
        return struct.pack('<Bb', 0x02, val)          # vaInt8
    elif -32768 <= val <= 32767:
        return struct.pack('<Bh', 0x03, val)          # vaInt16
    elif -2147483648 <= val <= 2147483647:
        return struct.pack('<Bi', 0x04, val)          # vaInt32
    else:
        return struct.pack('<Bq', 0x13, val)          # vaInt64
```

### 2. String Compaction in `TWriter.WriteString` (`VA 0x415860`)
- If string length $L \le 255$: Emits token `0x06` (`vaString`), followed by 1 byte length $L$, followed by $L$ ASCII bytes.
- If string length $L > 255$: Emits token `0x0C` (`vaLString`), followed by 4-byte unsigned length $L$ (`<I`), followed by $L$ ASCII bytes.

### 3. Boolean Emission
- `False`: Emits exactly 1 byte: `0x08` (`vaFalse`).
- `True`: Emits exactly 1 byte: `0x09` (`vaTrue`).

---

## 2.4 Critical Exception: Un-tagged Coordinate Serialization (`TFloatPoint`)

A critical deviation from standard Delphi VCL streaming exists in Digital Works' coordinate serialization.

### Disassembly Proof of `TFloatPoint.Serialize` (`VA 0x453294`):
```x86asm
0x45329a: push dword ptr [ebx + 0xc]      ; Load X coordinate (32-bit single float)
0x45329d: mov eax, esi                    ; eax = TSerializeWriter instance
0x45329f: call 0x452b3c                   ; Call WriteFloatDirect(X)
0x4532a4: push dword ptr [ebx + 0x10]     ; Load Y coordinate (32-bit single float)
0x4532a7: mov eax, esi                    ; eax = TSerializeWriter instance
0x4532a9: call 0x452b3c                   ; Call WriteFloatDirect(Y)
```
Where `WriteFloatDirect` (`VA 0x452b3c`) is:
```x86asm
0x452b3f: lea edx, [ebp + 8]              ; Pointer to 4-byte float buffer
0x452b42: mov ecx, 4                      ; Count = 4 bytes
0x452b47: call 0x414014                   ; Direct Stream.Write(buffer, 4) -- NO TOKEN!
```

### Invariant Rule:
Whenever coordinates $(X, Y)$ are serialized within `TFloatPoint`, `TDevice` anchor, or `TSolder` coordinates, they are written as **raw, un-tagged 32-bit IEEE 754 little-endian floats (`<f`)**, exactly 8 bytes total (4 bytes X, 4 bytes Y).  
**Emitting `vaSingle` (`0x0F`) before coordinates is a fatal error** that desynchronizes the VCL reader.

---

# Section 3: Object Serialization & Graph Deduplication Engine (`TSerializeWriter`)

## 3.1 Architectural Overview & Dynamic Registries

Digital Works circuits are complex cyclic graphs where wires reference component pins, pins reference their parent gates, and gates reference wire collections. To serialize this graph without recursion loops or redundant component copies, Digital Works implements a custom RTTI serialization engine: `TSerializeWriter` (writer) and `TSerializeReader` (reader).

`TSerializeWriter` maintains two dynamic indexing tables during serialization:
1. `Classes: TStringList`: An ordered list of unique Delphi class names encountered in the stream (e.g., `["TMacro", "TSerializeList", "TPolygon", "TFloatPoint", ...]`).
2. `Objects: TList`: An ordered list of all serialized object instance pointers. Every object is assigned an incremental 0-based `ObjectID` (`0, 1, 2, 3, ...`) the first time it is written.

---

## 3.2 The Four Serialization Markers (0, 1, 2, 15)

In `DigitalWorks.exe`, `TSerializeWriter.WriteObject` (`VA 0x452b50`) communicates object references and class declarations using four distinct marker integers. Because each marker is passed to `TWriter.WriteInteger`, they are encoded as `vaInt8` (`0x02 <marker_code>`):

```
┌─────────────────┬─────────────────────────────────────────────────────────────┐
│ Byte Sequence   │ Marker Definition & Semantics                               │
├─────────────────┼─────────────────────────────────────────────────────────────┤
│ 0x02 0x00       │ Marker 0: New Class Definition + Instance Declaration        │
│ 0x02 0x01       │ Marker 1: Existing Class Reference + Instance Declaration   │
│ 0x02 0x02       │ Marker 2: Previously Serialized Object Pointer Reference    │
│ 0x02 0x0F       │ Marker 15: Nil / Null Object Pointer                        │
└─────────────────┴─────────────────────────────────────────────────────────────┘
```

### Detailed Marker Semantics:

#### Marker 0 (`0x02 0x00`): New Class Definition
Emitted when an object of a class not yet present in `Classes` is encountered:
1. Emits `0x02 0x00`.
2. Emits `vaString` containing the Delphi class name (e.g., `06 09 54 32 41 6e 64 47 61 74 65` for `"T2AndGate"`).
3. The writer appends the class name to `Classes` (index = `len(Classes) - 1`).
4. The writer registers the object instance in `Objects` (assigning `ObjectID = len(Objects) - 1`).
5. Calls the object's virtual serialization routine `Object.Write(Writer)` to emit its field payload.

#### Marker 1 (`0x02 0x01`): Existing Class Reference
Emitted when an object belongs to a class that is already registered in `Classes`:
1. Emits `0x02 0x01`.
2. Emits `WriteInteger(ClassID)` (typically `vaInt8`: `0x02 <ClassID>`).
3. The writer registers the object instance in `Objects` (assigning `ObjectID = len(Objects) - 1`).
4. Calls the object's virtual serialization routine `Object.Write(Writer)` to emit its field payload.

#### Marker 2 (`0x02 0x02`): Object Deduplication Reference
Emitted when an object instance pointer that has **already been serialized** is referenced again:
1. Emits `0x02 0x02`.
2. Emits `WriteInteger(ObjectID)` referencing the earlier instance index (e.g., `0x02 0x45` for object 69).
3. **No field payload is emitted**. The reader looks up `Objects[ObjectID]` and re-establishes the pointer in memory.

#### Marker 15 (`0x02 0x0F`): Nil Pointer
Emitted when an object reference field is `nil` / `None` (such as an unconnected pin's wire reference):
1. Emits `0x02 0x0F`.
2. **0 payload bytes follow**.

---

## 3.3 Object Graph Walk & Cycle-Free Serialization Algorithm

The following flowchart illustrates the cycle-free graph serialization algorithm implemented in `DigitalWorks.exe` at `VA 0x452b50`:

```
                 [WriteObject(obj)]
                         │
                 Is obj == None / nil?
                ├─── YES ───► Emit [0x02 0x0F] (Marker 15) ──► Return
                │
                NO
                ▼
        Has obj been serialized?
      (obj.is_serialized == True)
        ├─── YES ───► Emit [0x02 0x02] (Marker 2)
        │             Emit WriteInteger(obj.object_id) ──► Return
        │
        NO
        ▼
   Is obj.class_name in Classes?
        ├─── YES ───► Emit [0x02 0x01] (Marker 1)
        │             Emit WriteInteger(class_id)
        │
        └─── NO ────► Emit [0x02 0x00] (Marker 0)
                      Emit WriteString(obj.class_name)
                      Classes.append(obj.class_name)
        │
        ▼
   Assign obj.object_id = len(Objects)
   Objects.append(obj)
   Set obj.is_serialized = True
        │
        ▼
   Call obj.Write(writer) (Emit field payload)
        │
        ▼
     Return
```

---

## 3.4 Container List Serialization (`TSerializeList`)

Dynamic collections of objects (e.g., list of components, list of pins, list of wire vertices) are held in `TSerializeList` containers. In the stream, a `TSerializeList` is serialized as:

1. Object Marker for `TSerializeList` (Marker 0 `0x02 0x00 06 0E "TSerializeList"` or Marker 1 `0x02 0x01 02 <class_id>`).
2. List Begin Token: `0x01` (`vaList`).
3. Sequential elements: Each child item is serialized via `WriteObject(child)`.
4. List End Token: `0x00` (`vaNull`).

*Empty List Representation*: An empty `TSerializeList` (e.g., empty wire list or unused subcircuit list) emits Marker 1 + `01 00` (`vaList vaNull`).

---

# Section 4: Component Record Structures & RTTI Class Hierarchy

## 4.1 Complete Delphi VCL Class Hierarchy

Every entity placed on the Digital Works schematic canvas inherits from the Delphi VCL base classes:

```
TObject (size 4)
  └─ TPersistent (size 4)
       └─ TSerialize (size 12, VMT 0x4524ac)
            ├─ TGraphicObject (size 20, VMT 0x453fb0)
            │    ├─ TSegment (size 40)
            │    │    ├─ TPolygon (size 48)
            │    │    │    ├─ TPin (size 68, VMT 0x4556a4)
            │    │    │    │    └─ TMacroPin (size 72, VMT 0x455758)
            │    │    │    └─ TSolder (size 72, VMT 0x4558c8)
            │    │    └─ TPolyline (size 52)
            │    │         └─ TWire (size 96, VMT 0x455814)
            │    └─ TGraphicList (size 28, VMT 0x454d18)
            │         └─ TDevice (size 48, VMT 0x457200)
            │              ├─ TGateDevice (size 52, VMT 0x459f0c)
            │              │    ├─ TNotGate (size 52, VMT 0x459ffc)
            │              │    ├─ TAndGate (size 52, VMT 0x45a0e8)
            │              │    │    ├─ T2AndGate (size 52, VMT 0x45a1d4)
            │              │    │    ├─ T3AndGate (size 52, VMT 0x45a2c0)
            │              │    │    └─ T4AndGate (size 52, VMT 0x45a3ac)
            │              │    ├─ TNandGate (size 52)
            │              │    │    ├─ T2NandGate (size 52, VMT 0x45a584)
            │              │    │    ├─ T3NandGate (size 52, VMT 0x45a670)
            │              │    │    └─ T4NandGate (size 52, VMT 0x45a75c)
            │              │    ├─ TOrGate (size 52, VMT 0x45a848)
            │              │    │    ├─ T2OrGate (size 52, VMT 0x45a930)
            │              │    │    ├─ T3OrGate (size 52, VMT 0x45aa1c)
            │              │    │    └─ T4OrGate (size 52, VMT 0x45ab08)
            │              │    ├─ TNorGate (size 52)
            │              │    │    ├─ T2NorGate (size 52, VMT 0x45ace0)
            │              │    │    ├─ T3NorGate (size 52, VMT 0x45adcc)
            │              │    │    └─ T4NorGate (size 52, VMT 0x45aeb8)
            │              │    ├─ TXorGate (size 52)
            │              │    │    └─ T2XorGate (size 52, VMT 0x45b090)
            │              │    └─ TXnorGate (size 52)
            │              │         └─ T2XnorGate (size 52, VMT 0x45b268)
            │              ├─ TTextDevice (size 56)
            │              │    ├─ TInteractiveSwitch (size 64, VMT 0x480d5c)
            │              │    └─ THistoryDevice (size 64)
            │              │         ├─ TInputDevice (size 64)
            │              │         │    ├─ TInteractiveInput (size 72, VMT 0x480e5c)
            │              │         │    └─ TSeqInputDevice (size 84)
            │              │         │         └─ TClockDevice (size 84, VMT 0x45e834)
            │              │         └─ TOutputDevice (size 68)
            │              │              ├─ TLEDDevice (size 72, VMT 0x45f3fc)
            │              │              ├─ TLEDSegmentDevice (size 76, VMT 0x45f4e8)
            │              │              └─ TNumericDevice (size 104, VMT 0x45f5e4)
            │              └─ TMacro (size 84, VMT 0x462344)
```

---

## 4.2 Virtual Method Table (VMT) Dispatch & Instance Sizes

In Delphi, `WriteObject` invokes virtual method slot 4 (offset `+0x10` from VMT base) to serialize an object:
```x86asm
0x452c4f: mov ecx, dword ptr [eax]     ; ecx = VMT table pointer
0x452c51: call dword ptr [ecx + 0x10]  ; Call virtual Write method
```

Verified Virtual Method Entry Points:
- `TDevice.Write` (all logic gates): `VA 0x4575a4`
- `TPin.Write`: `VA 0x455a1c`
- `TMacroPin.Write`: `VA 0x455b9c`
- `TWire.Write`: `VA 0x455cd4`
- `TSolder.Write`: `VA 0x456630`
- `TInteractiveInput.Write`: `VA 0x4815c4`
- `TInteractiveSwitch.Write`: `VA 0x481254`
- `TClockDevice.Write`: `VA 0x45ee58`
- `TLEDDevice.Write`: `VA 0x45f6cc`
- `TLEDSegmentDevice.Write`: `VA 0x45fecc`
- `TNumericDevice.Write`: `VA 0x4603dc`

---

## 4.3 Concrete Serialization Schemas for Logic Gates

### 1. `TDevice` Base Layout (`VA 0x4575a4`)
All basic and derived logic gates (`T2AndGate`, `T3AndGate`, `T4AndGate`, `TNotGate`, `T2NandGate`, `T3NandGate`, `T4NandGate`, `T2OrGate`, `T3OrGate`, `T4OrGate`, `T2NorGate`, `T3NorGate`, `T4NorGate`, `T2XorGate`, `T2XnorGate`) inherit directly from `TDevice`. Their payload format is identical:

| Field Index | Field Name | Delphi Type | Token / Size | Semantics & Default Values |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `HasGraphicList` | `Boolean` | `0x08` (`vaFalse`) | Gate body uses vector primitives built into runtime |
| 2 | `IsSelected` | `Boolean` | `0x08` (`vaFalse`) | Canvas selection state flag |
| 3 | `DeviceFlag` | `Boolean` | `0x08` (`vaFalse`) | Internal simulation evaluation flag |
| 4 | `Pins` | `TGraphicList` | Object Record | Container holding the ordered list of `TPin` objects |
| 5 | `Anchor X` | `Single` | 4 raw bytes (`<f`) | X canvas coordinate of component center anchor |
| 6 | `Anchor Y` | `Single` | 4 raw bytes (`<f`) | Y canvas coordinate of component center anchor |

### 2. Logic Gate Pin Sequencing Invariant
Inside the `Pins` container of any logic gate:
- **Pin 0** is ALWAYS the **Output Pin** (Type = 2).
- **Pin 1..N** are the **Input Pins** (Type = 1), serialized from **bottom to top**:
  - For 2-input gates: Pin 1 = `in2` (bottom, $dy = +10$), Pin 2 = `in1` (top, $dy = -10$).
  - For 3-input gates: Pin 1 = `in3` (bottom, $dy = +10$), Pin 2 = `in2` (middle, $dy = 0$), Pin 3 = `in1` (top, $dy = -10$).
  - For 4-input gates: Pin 1 = `in4` (bottom, $dy = +15$), Pin 2 = `in3` ($dy = +5$), Pin 3 = `in2` ($dy = -5$), Pin 4 = `in1` (top, $dy = -15$).

---

## 4.4 Concrete Serialization Schemas for Interactive I/O & Displays

### 1. `TInteractiveInput` (Toggle Switch / Push Button, `VA 0x4815c4`)
- Inherits from `THistoryDevice` $\to$ `TTextDevice` $\to$ `TDevice`.
- **Pins**: Exactly 1 output pin at $(dx=0.0, dy=0.0)$ relative to anchor.
- **Fields following base `TDevice` layout**:
  1. `HasLabel`: `Boolean` (`0x08` = False, `0x09` = True). If True, followed by `Alignment` (`vaInt8`) + `TGraphicText` record.
  2. `HistoryEnabled`: `Boolean` (`0x08` = False).
  3. `SwitchState`: `Boolean` (`0x08` = Logic 0 / Low, `0x09` = Logic 1 / High).
  4. `InputMode`: `Integer` (`0x02 0x00` = Toggle Switch, `0x02 0x01` = Push Button).

### 2. `TInteractiveSwitch` (SPST Two-Terminal Switch, `VA 0x481254`)
- Inherits from `TTextDevice` $\to$ `TDevice`.
- **Pins**: Exactly 2 bidirectional switch terminal pins (Type = 3) at $dx = -15.0$ and $dx = +15.0$.
- **Fields following base `TDevice` layout**:
  1. `HasLabel`: `Boolean` (`0x08` or `0x09`).
  2. `SwitchState`: `Boolean` (`0x08` = Open circuit, `0x09` = Closed circuit).

### 3. `TClockDevice` (Square Wave Clock Generator, `VA 0x45ee58`)
- Inherits from `TSeqInputDevice` $\to$ `THistoryDevice`.
- **Pins**: Exactly 1 output pin at $(dx=+15.0, dy=0.0)$.
- **Fields following base `TDevice` layout**:
  1. `HasLabel`: `Boolean` (`0x08` or `0x09`).
  2. `HistoryEnabled`: `Boolean` (`0x08`).
  3. `Frequency`: `Integer` (`vaInt16` or `vaInt32` tick half-period).

### 4. `TLEDDevice` (Logic Probe LED, `VA 0x45f6cc`)
- Inherits from `TOutputDevice` $\to$ `THistoryDevice`.
- **Pins**: Exactly 1 input pin at $(dx=0.0, dy=0.0)$ relative to anchor.
- **Fields following base `TDevice` layout**:
  1. `HasLabel`: `Boolean` (`0x08` or `0x09`).
  2. `LEDColor`: `Integer` (`vaInt32` Delphi `TColor`: `0x000000FF` = Red, `0x0000FF00` = Green).

### 5. `TLEDSegmentDevice` (7-Segment Display, `VA 0x45fecc`)
- **Pins**: 7 input pins along bottom edge at $dy = +50.0$, spaced at $dx = [-15, -10, -5, 0, +5, +10, +15]$ for segments $a, b, c, d, e, f, g$.
- Uses compact $4 \times 4$ px terminal bounding boxes.

### 6. `TNumericDevice` (4-Bit Hexadecimal/Decimal Display, `VA 0x4603dc`)
- **Pins**: 4 input pins along top edge at $dy = -10.0$, spaced at $dx = [-15.0, -5.0, +5.0, +15.0]$ for bits $D_0, D_1, D_2, D_3$.

---

## 4.5 Concrete Serialization Schemas for Connectivity Primitives

### 1. `TPin` Schema (`VA 0x455a1c`)
```
[Pen Color]             vaInt8 (02 00 = clBlack)
[Pen Width]             vaInt8 (02 01 = 1 pixel)
[Points List]           TSerializeList containing 4 TFloatPoint objects (8x8 px square)
[Brush Color]           vaInt32 (04 ff ff ff 00 = clWhite fill)
[Pin Direction / Type]  vaInt8:
                          02 01 = Input Pin
                          02 02 = Output Pin
                          02 03 = Bidirectional Switch Terminal
                          02 00 = Macro Pin
[Connected Wire Ref]    WriteObject reference:
                          02 0f (Marker 15 = nil, if unconnected)
                          02 02 <wire_id> (Marker 2, if connected)
```

### 2. `TMacroPin` Schema (`VA 0x455b9c`)
Extends `TPin` (Direction tag = `0x00`) followed by an external component terminal reference pointer.

### 3. `TWire` Schema (`VA 0x455cd4`)
```
[Pen Color]             vaInt8 (02 00 = clBlack)
[Pen Width]             vaInt8 (02 01 = 1 pixel)
[Points List]           TSerializeList of TFloatPoint objects (ordered Manhattan vertices)
[Wire State / ID]       vaInt8 (02 00)
[Start Pin Ref]         WriteObject reference (Marker 2 to source TPin or TSolder)
[End Pin Ref]           WriteObject reference (Marker 2 to destination TPin or TSolder)
```

### 4. `TSolder` Schema (`VA 0x456630`)
```
[Solder X Coordinate]   4 raw bytes (<f, IEEE 754 float X)
[Solder Y Coordinate]   4 raw bytes (<f, IEEE 754 float Y)
[Branch Wire 1 Ref]     WriteObject reference (Marker 1/2 to incoming trunk wire)
[Branch Wire 2 Ref]     WriteObject reference (Marker 1/2 to continuation wire)
[Branch Wire 3 Ref]     WriteObject reference (Marker 1/2 to branch wire)
```

---

# Section 5: Coordinate System & Geometry Specification

## 5.1 Canvas Plane, Orientation & Origin

Digital Works schematic drawings are defined on a standard 2D computer graphics plane:

```
(0, 0) ──────────────────────────► +X (pixels)
  │
  │      Schematic Canvas
  │      1.0 Unit = 1 Screen Pixel
  │
  ▼
 +Y (pixels)
```

- **Origin `(0.0, 0.0)`**: The extreme top-left corner of the schematic canvas.
- **Horizontal Axis (+X)**: Extends positively to the right.
- **Vertical Axis (+Y)**: Extends positively downwards.
- **Coordinate Domain**: Positive real numbers ($\mathbb{R}^+$). Coordinates placed at negative values are clipped off-screen by the GUI.

---

## 5.2 5 px Grid Snapping Invariants & Formulations

Digital Works enforces a rigid 5-pixel grid snap frequency (`GridSetup.htm`). To ensure that wires connect reliably to pin terminals without drawing diagonal artifacts or missing contact triggers:

### Snapping Invariant:
All component anchors $(x, y)$, pin terminal centers $(px, py)$, wire vertices $(wx, wy)$, and solder dot coordinates $(sx, sy)$ must be exact integer multiples of 5.0 pixels:

$$x \equiv 0 \pmod{5.0}, \quad y \equiv 0 \pmod{5.0}$$

### Quantization Transformation:
```python
def snap_to_grid(coord: float, grid: float = 5.0) -> float:
    return round(coord / grid) * grid
```

---

## 5.3 IEEE 754 32-Bit Float Coordinate Storage

All coordinates in the `.dwm` format are stored as **IEEE 754 single-precision (32-bit) floating-point numbers in Little-Endian byte order** (`<f` in Python `struct`):

- Size: 4 bytes (32 bits).
- Sign: Bit 31.
- Exponent: Bits 23..30 (bias 127).
- Mantissa: Bits 0..22 (fractional part).

### Standard Coordinate Examples:
| Decimal Value | IEEE 754 Hex (Big-Endian) | Little-Endian Stream Bytes |
| :--- | :--- | :--- |
| `0.0` | `0x00000000` | `00 00 00 00` |
| `5.0` | `0x40A00000` | `00 00 A0 40` |
| `10.0` | `0x41200000` | `00 00 20 41` |
| `-10.0` | `0xC1200000` | `00 00 20 C1` |
| `20.0` | `0x41A00000` | `00 00 A0 41` |
| `-20.0` | `0xC1A00000` | `00 00 A0 C1` |
| `30.0` | `0x41F00000` | `00 00 F0 41` |
| `-30.0` | `0xC1F00000` | `00 00 F0 C1` |
| `120.0` | `0x42F00000` | `00 00 F0 42` |
| `200.0` | `0x43480000` | `00 00 48 43` |

---

## 5.4 Pin Contact Terminal Bounding Box Geometry

Every `TPin` is serialized as a small closed vector polygon (`TPolygon`) representing the interactive contact handle on the schematic canvas.

### 1. Standard Components ($8 \times 8$ Pixel Bounding Box)
For all logic gates, interactive inputs, toggle switches, clocks, LEDs, and numeric displays, the contact box is an $8 \times 8$ pixel square centered at absolute pin coordinate $(px, py)$.  
The 4 polygon vertices are serialized in clockwise order starting from the bottom-right:

```
 Vertex 3: (px - 4, py - 4) ┌──────────────┐ Vertex 2: (px + 4, py - 4)
                            │              │
                            │   (px, py)   │
                            │              │
 Vertex 4: (px - 4, py + 4) └──────────────┘ Vertex 1: (px + 4, py + 4)
```

$$\begin{aligned}
P_1 &= (px + 4.0, \; py + 4.0) \quad \text{[Bottom-Right]} \\
P_2 &= (px + 4.0, \; py - 4.0) \quad \text{[Top-Right]} \\
P_3 &= (px - 4.0, \; py - 4.0) \quad \text{[Top-Left]} \\
P_4 &= (px - 4.0, \; py + 4.0) \quad \text{[Bottom-Left]}
\end{aligned}$$

### 2. 7-Segment Display Pins ($4 \times 4$ Pixel Bounding Box)
Because the 7 input pins of `TLEDSegmentDevice` are packed at 5-pixel intervals along the bottom edge, they use a compact $4 \times 4$ pixel box ($\pm 2.0$ px from center) to prevent bounding box overlap.

---

# Section 6: Pin Coordinate Calculation Formulas & Offset Tables

## 6.1 Mathematical Formulation for Absolute Pin Coordinates

When placing a component at canvas anchor coordinate $(x, y)$, the absolute coordinate $(px_i, py_i)$ of pin $i$ is calculated by:

$$\begin{aligned}
px_i &= x + dx_i \\
py_i &= y + dy_i
\end{aligned}$$

where $(dx_i, dy_i)$ is the relative offset defined in the component's constructor.

---

## 6.2 Empirical Ground Truth: Asymmetric NOT Gate Geometry

### Disproof of Tentative Symmetric Heuristics:
Initial heuristics suggested that NOT gates might be symmetric around anchor $x \pm 25.0$. **Disassembly of `TNotGate.Create` (`VA 0x45b610`) conclusively disproved this hypothesis**:

```x86asm
; DigitalWorks.exe - TNotGate.Create (VA 0x45b610)
0x45b778: mov byte ptr [ebx + 0x34], 2       ; Pin Type = Output (2)
0x45b77c: push 0x41f00000                    ; Float +30.0
0x45b781: push 0                             ; Float 0.0
0x45b783: call TPin.SetPosition              ; Output pin at (dx = +30.0, dy = 0.0)

0x45b7a8: mov byte ptr [ebx + 0x34], 1       ; Pin Type = Input (1)
0x45b7ac: push 0xc1a00000                    ; Float -20.0
0x45b7b1: push 0                             ; Float 0.0
0x45b7b3: call TPin.SetPosition              ; Input pin at (dx = -20.0, dy = 0.0)
```

The physical body of the NOT gate is 50 pixels wide:
- Triangular body extends from $x - 20.0$ to $x + 20.0$ (40 px).
- Inversion bubble extends from $x + 20.0$ to $x + 30.0$ (10 px).
- Total span: $x - 20.0$ to $x + 30.0$.
- **Downstream compilers MUST use $dx_{in} = -20.0$ and $dx_{out} = +30.0$**.

---

## 6.3 Master Pin Relative Offset Table (All 26 Components)

The following table provides the authoritative, machine-code-verified pin offsets and direction tags for all Digital Works components:

| Component Type | Delphi Class | Pin Index | Pin Name | Role | Dir Tag | dx (px) | dy (px) | Box Size |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **NOT Gate** | `TNotGate` | 0 | `out` | Output | 2 | **+30.0** | **0.0** | $8 \times 8$ |
| | | 1 | `in` | Input | 1 | **-20.0** | **0.0** | $8 \times 8$ |
| **2-Input AND** | `T2AndGate` | 0 | `out` | Output | 2 | **+30.0** | **0.0** | $8 \times 8$ |
| | | 1 | `in2` | Input 2 (Bottom) | 1 | **-30.0** | **+10.0** | $8 \times 8$ |
| | | 2 | `in1` | Input 1 (Top) | 1 | **-30.0** | **-10.0** | $8 \times 8$ |
| **3-Input AND** | `T3AndGate` | 0 | `out` | Output | 2 | +30.0 | 0.0 | $8 \times 8$ |
| | | 1 | `in3` | Input 3 (Bottom) | 1 | -30.0 | +10.0 | $8 \times 8$ |
| | | 2 | `in2` | Input 2 (Middle) | 1 | -30.0 | 0.0 | $8 \times 8$ |
| | | 3 | `in1` | Input 1 (Top) | 1 | -30.0 | -10.0 | $8 \times 8$ |
| **4-Input AND** | `T4AndGate` | 0 | `out` | Output | 2 | +30.0 | 0.0 | $8 \times 8$ |
| | | 1 | `in4` | Input 4 (Bottom) | 1 | -30.0 | +15.0 | $8 \times 8$ |
| | | 2 | `in3` | Input 3 (Mid-Low) | 1 | -30.0 | +5.0 | $8 \times 8$ |
| | | 3 | `in2` | Input 2 (Mid-High)| 1 | -30.0 | -5.0 | $8 \times 8$ |
| | | 4 | `in1` | Input 1 (Top) | 1 | -30.0 | -15.0 | $8 \times 8$ |
| **2-Input NAND** | `T2NandGate` | 0 | `out` | Output | 2 | +30.0 | 0.0 | $8 \times 8$ |
| | | 1 | `in2` | Input 2 (Bottom) | 1 | -30.0 | +10.0 | $8 \times 8$ |
| | | 2 | `in1` | Input 1 (Top) | 1 | -30.0 | -10.0 | $8 \times 8$ |
| **3-Input NAND** | `T3NandGate` | 0 | `out` | Output | 2 | +30.0 | 0.0 | $8 \times 8$ |
| | | 1 | `in3` | Input 3 (Bottom) | 1 | -30.0 | +10.0 | $8 \times 8$ |
| | | 2 | `in2` | Input 2 (Middle) | 1 | -30.0 | 0.0 | $8 \times 8$ |
| | | 3 | `in1` | Input 1 (Top) | 1 | -30.0 | -10.0 | $8 \times 8$ |
| **4-Input NAND** | `T4NandGate` | 0 | `out` | Output | 2 | +30.0 | 0.0 | $8 \times 8$ |
| | | 1 | `in4` | Input 4 (Bottom) | 1 | -30.0 | +15.0 | $8 \times 8$ |
| | | 2 | `in3` | Input 3 (Mid-Low) | 1 | -30.0 | +5.0 | $8 \times 8$ |
| | | 3 | `in2` | Input 2 (Mid-High)| 1 | -30.0 | -5.0 | $8 \times 8$ |
| | | 4 | `in1` | Input 1 (Top) | 1 | -30.0 | -15.0 | $8 \times 8$ |
| **2-Input OR** | `T2OrGate` | 0 | `out` | Output | 2 | +30.0 | 0.0 | $8 \times 8$ |
| | | 1 | `in2` | Input 2 (Bottom) | 1 | -30.0 | +10.0 | $8 \times 8$ |
| | | 2 | `in1` | Input 1 (Top) | 1 | -30.0 | -10.0 | $8 \times 8$ |
| **3-Input OR** | `T3OrGate` | 0 | `out` | Output | 2 | +30.0 | 0.0 | $8 \times 8$ |
| | | 1 | `in3` | Input 3 (Bottom) | 1 | -30.0 | +10.0 | $8 \times 8$ |
| | | 2 | `in2` | Input 2 (Middle) | 1 | -30.0 | 0.0 | $8 \times 8$ |
| | | 3 | `in1` | Input 1 (Top) | 1 | -30.0 | -10.0 | $8 \times 8$ |
| **4-Input OR** | `T4OrGate` | 0 | `out` | Output | 2 | +30.0 | 0.0 | $8 \times 8$ |
| | | 1 | `in4` | Input 4 (Bottom) | 1 | -30.0 | +15.0 | $8 \times 8$ |
| | | 2 | `in3` | Input 3 (Mid-Low) | 1 | -30.0 | +5.0 | $8 \times 8$ |
| | | 3 | `in2` | Input 2 (Mid-High)| 1 | -30.0 | -5.0 | $8 \times 8$ |
| | | 4 | `in1` | Input 1 (Top) | 1 | -30.0 | -15.0 | $8 \times 8$ |
| **2-Input NOR** | `T2NorGate` | 0 | `out` | Output | 2 | +30.0 | 0.0 | $8 \times 8$ |
| | | 1 | `in2` | Input 2 (Bottom) | 1 | -30.0 | +10.0 | $8 \times 8$ |
| | | 2 | `in1` | Input 1 (Top) | 1 | -30.0 | -10.0 | $8 \times 8$ |
| **3-Input NOR** | `T3NorGate` | 0 | `out` | Output | 2 | +30.0 | 0.0 | $8 \times 8$ |
| | | 1 | `in3` | Input 3 (Bottom) | 1 | -30.0 | +10.0 | $8 \times 8$ |
| | | 2 | `in2` | Input 2 (Middle) | 1 | -30.0 | 0.0 | $8 \times 8$ |
| | | 3 | `in1` | Input 1 (Top) | 1 | -30.0 | -10.0 | $8 \times 8$ |
| **4-Input NOR** | `T4NorGate` | 0 | `out` | Output | 2 | +30.0 | 0.0 | $8 \times 8$ |
| | | 1 | `in4` | Input 4 (Bottom) | 1 | -30.0 | +15.0 | $8 \times 8$ |
| | | 2 | `in3` | Input 3 (Mid-Low) | 1 | -30.0 | +5.0 | $8 \times 8$ |
| | | 3 | `in2` | Input 2 (Mid-High)| 1 | -30.0 | -5.0 | $8 \times 8$ |
| | | 4 | `in1` | Input 1 (Top) | 1 | -30.0 | -15.0 | $8 \times 8$ |
| **2-Input XOR** | `T2XorGate` | 0 | `out` | Output | 2 | +30.0 | 0.0 | $8 \times 8$ |
| | | 1 | `in2` | Input 2 (Bottom) | 1 | -30.0 | +10.0 | $8 \times 8$ |
| | | 2 | `in1` | Input 1 (Top) | 1 | -30.0 | -10.0 | $8 \times 8$ |
| **2-Input XNOR** | `T2XnorGate` | 0 | `out` | Output | 2 | +30.0 | 0.0 | $8 \times 8$ |
| | | 1 | `in2` | Input 2 (Bottom) | 1 | -30.0 | +10.0 | $8 \times 8$ |
| | | 2 | `in1` | Input 1 (Top) | 1 | -30.0 | -10.0 | $8 \times 8$ |
| **Interactive Input** | `TInteractiveInput` | 0 | `out` | Output | 2 | **0.0** | **0.0** | $8 \times 8$ |
| **Interactive Switch** | `TInteractiveSwitch`| 0 | `t1` | Terminal 1 (Left) | 3 | **-15.0** | **0.0** | $8 \times 8$ |
| | | 1 | `t2` | Terminal 2 (Right) | 3 | **+15.0** | **0.0** | $8 \times 8$ |
| **Clock Generator** | `TClockDevice` | 0 | `out` | Output | 2 | **+15.0** | **0.0** | $8 \times 8$ |
| **LED Indicator** | `TLEDDevice` | 0 | `in` | Input | 1 | **0.0** | **0.0** | $8 \times 8$ |
| **7-Segment Display** | `TLEDSegmentDevice` | 0..6 | `a`..`g` | Segment Inputs | 1 | -15, -10, -5, 0, +5, +10, +15 | +50.0 | $4 \times 4$ |
| **Numeric Display** | `TNumericDevice` | 0..3 | `D0`..`D3` | Data Inputs | 1 | -15.0, -5.0, +5.0, +15.0 | -10.0 | $8 \times 8$ |
| **Macro Boundary Pin** | `TMacroPin` | 0 | `pin` | Terminal | 0 | 0.0 | 0.0 | $8 \times 8$ |

---

## 6.4 Multi-Input Gate Vertical Spacing Geometry

All logic gates preserve an overall width of 60 pixels (spanning $x - 30.0$ to $x + 30.0$), but expand vertical pin spacing while maintaining strict 5-pixel grid snap:

```
  2-Input Gate (dy = ±10):               4-Input Gate (dy = ±15, ±5):
  
   in1 (-30, -10) ──┐                     in1 (-30, -15) ──┐
                    │                                      │
                    ├─── out (+30, 0)     in2 (-30,  -5) ──┤
                    │                                      ├─── out (+30, 0)
   in2 (-30, +10) ──┘                     in3 (-30,  +5) ──┤
                                                           │
                                          in4 (-30, +15) ──┘
```

---

# Section 7: Wire Record Layout & Manhattan Orthogonal Routing

## 7.1 Wire Serialization Model (`TWire`)

A wire interconnects two electrical contact pins (`TPin` or `TSolder`). In the VCL stream, `TWire` inherits from `TPolyline` and contains:
1. Pen styling: Pen Color (`vaInt8` 0 = black) and Pen Width (`vaInt8` 1 = 1 pixel).
2. Points List: A `TSerializeList` containing the ordered sequence of 2D vertex coordinates (`TFloatPoint`).
3. Wire Simulation ID/State: `vaInt8` 0.
4. Terminal Pin References:
   - `StartPin`: Marker 2 (`0x02 0x02 <id>`) pointing to the source pin.
   - `EndPin`: Marker 2 (`0x02 0x02 <id>`) pointing to the destination pin.

---

## 7.2 Manhattan Routing Invariants & Prohibited Topologies

Digital Works schematics strictly demand right-angle orthogonal routing. Downstream compilers and verification suites must enforce the following invariants:

### Invariant 1: Strictly Orthogonal Segments (Zero Diagonals)
For every consecutive pair of vertices $P_i = (x_i, y_i)$ and $P_{i+1} = (x_{i+1}, y_{i+1})$ in a wire:

$$(x_{i+1} == x_i \land y_{i+1} \neq y_i) \lor (x_{i+1} \neq x_i \land y_{i+1} == y_i)$$

Diagonal segments ($dx \neq 0 \land dy \neq 0$) are strictly prohibited.

### Invariant 2: Snap Grid Adherence
Every vertex coordinate must be an exact multiple of 5.0 pixels:
$$x_i \equiv 0 \pmod{5.0}, \quad y_i \equiv 0 \pmod{5.0}$$

---

## 7.3 Canonical Routing Topologies (Collinear, L-Shaped, Z-Shaped)

Connecting a source pin at $(x_1, y_1)$ to a destination pin at $(x_2, y_2)$ is achieved via one of three canonical routing strategies:

```
1. Collinear (0 Bends, 2 Vertices):
   (x1, y1) ──────────────────────────────────► (x2, y2)   (y1 == y2)

2. L-Shaped (1 Bend, 3 Vertices):
   (x1, y1) ────────────────┐ (x2, y1)
                            │
                            ▼ (x2, y2)

3. Z-Shaped Channel (2 Bends, 4 Vertices):
   (x1, y1) ───────┐ (x_mid, y1)
                   │
                   └───────► (x2, y2)
                (x_mid, y2)
```

### 1. Collinear Routing (2 Vertices, 0 Bends)
- Condition: Pins are horizontally aligned ($y_1 == y_2$) or vertically aligned ($x_1 == x_2$).
- Route: $[(x_1, y_1), (x_2, y_2)]$.

### 2. L-Shaped Routing (3 Vertices, 1 Bend)
- Condition: Pins are unaligned ($x_1 \neq x_2$ and $y_1 \neq y_2$).
- Horizontal-First (HV): $[(x_1, y_1), (x_2, y_1), (x_2, y_2)]$.
- Vertical-First (VH): $[(x_1, y_1), (x_1, y_2), (x_2, y_2)]$.

### 3. Z-Shaped Channel Routing (4 Vertices, 2 Bends)
- Standard schematic channel routing: Wire exits source horizontally, turns vertically into a routing channel, and enters destination horizontally:
  $$x_{mid} = \operatorname{round}\left(\frac{x_1 + x_2}{2 \times 5.0}\right) \times 5.0$$
- Route: $[(x_1, y_1), (x_{mid}, y_1), (x_{mid}, y_2), (x_2, y_2)]$.

---

## 7.4 Multi-Drop Nets & `TSolder` Joint Topology

When an output pin drives multiple input pins (fan-out $\ge 2$), Digital Works decomposes the tree into individual 2-pin wire segments joined by `TSolder` junction dots.

```
                  ┌──────────────────────────────► To Input 1 (Wire 2)
 Source Pin       │ (sx, sy) [TSolder Joint]
   ───────────────┴──────────────────────────────► To Input 2 (Wire 3)
     (Wire 1)
```

### Electrical Node Topology Rules for `TSolder`:
1. **Coordinate**: Located at the exact branching vertex $(sx, sy)$.
2. **Trunk Wire 1**: Starts at source pin, terminates at `TSolder` (`EndPin = solder`).
3. **Continuation Wire 2**: Starts at `TSolder` (`StartPin = solder`), terminates at Target 1.
4. **Branch Wire 3**: Starts at `TSolder` (`StartPin = solder`), terminates at Target 2.
5. **No 4-Way Crossings**: If fanout $> 2$, Digital Works inserts sequential 3-way `TSolder` joints spaced by at least 5 pixels along the trunk line.

---

# Section 8: Comprehensive Annotated Reference Seed Hex Dumps

## 8.1 Minimal Empty Macro Seed (`empty_macro_minimal.dwm`, 380 Bytes)

The following complete, byte-by-byte breakdown annotates all 380 bytes of `reference_seeds/empty_macro_minimal.dwm`:

| Offset Range | Hex Bytes | Field / Token | Semantic Description |
| :--- | :--- | :--- | :--- |
| `0x0000..0x0005` | `04 dd c4 22 00` | Header: `vaInt32` | Magic `0x0022c4dd` (Digital Works 3.04 format signature) |
| `0x0005..0x0006` | `01` | Preamble: `vaList` | List begin marker for preamble metadata properties |
| `0x0006..0x000C` | `02 01 02 64 06 00` | Property `0x64` | Type 1 (String), Tag `0x64` (Title), value `""` (empty) |
| `0x000C..0x001B` | `02 01 02 65 06 09 68 65 6c 6c 6f 2e 68 74 6d` | Property `0x65` | Type 1, Tag `0x65` (Doc Link), value `"hello.htm"` |
| `0x001B..0x0022` | `02 01 02 66 06 01 30` | Property `0x66` | Type 1, Tag `0x66` (Revision), value `"0"` |
| `0x0022..0x0029` | `02 02 03 ca 00 02 00` | Property `0xCA` | Type 2 (Integer), Tag `0x00CA` (202), value `0` |
| `0x0029..0x0030` | `02 02 03 c8 00 02 00` | Property `0xC8` | Type 2 (Integer), Tag `0x00C8` (200), value `0` |
| `0x0030..0x003F` | `02 01 03 c9 00 06 08 81 ef 60 a8 0e d6 bc 16` | Property `0xC9` | Type 1, Tag `0x00C9` (201), value 8-byte GUID/timestamp |
| `0x003F..0x0040` | `00` | Preamble: `vaNull` | List end terminator for preamble |
| `0x0040..0x004A` | `02 00 06 06 54 4d 61 63 72 6f` | Root Container | Marker 0, Class Name `"TMacro"` (Registered as Class ID 0) |
| `0x004A..0x004B` | `09` | `TMacro` [Obj#0] | `HasGraphicList = True` (`vaTrue`) |
| `0x004B..0x005D` | `02 00 06 0e 54 53 65 72 ...` | GraphicList Container | Marker 0, Class Name `"TSerializeList"` (Class ID 1) |
| `0x005D..0x005E` | `01` | `TSerializeList` [Obj#1]| `vaList` begin for macro graphic vector shapes |
| `0x005E..0x006A` | `02 00 06 08 54 50 6f 6c 79 67 6f 6e` | Shape Item 0 | Marker 0, Class Name `"TPolygon"` (Class ID 2) |
| `0x006A..0x006E` | `02 00 02 01` | `TPolygon` [Obj#2] | Pen Color = 0 (`vaInt8` 0), Pen Width = 1 (`vaInt8` 1) |
| `0x006E..0x0073` | `02 01 02 01 01` | Points List | Marker 1, Class 1 (`TSerializeList`), `vaList` begin |
| `0x0073..0x008A` | `02 00 06 0b 54 46 6c 6f 61 74 50 6f 69 6e 74 00 00 a0 c1 00 00 20 c1` | Vertex 0 | Marker 0, `"TFloatPoint"` (Class 3), raw floats `(-20.0, -10.0)` |
| `0x008A..0x0096` | `02 01 02 03 00 00 a0 41 00 00 20 c1` | Vertex 1 | Marker 1, Class 3 (`TFloatPoint`), raw floats `(20.0, -10.0)` |
| `0x0096..0x00A2` | `02 01 02 03 00 00 a0 41 00 00 20 41` | Vertex 2 | Marker 1, Class 3 (`TFloatPoint`), raw floats `(20.0, 10.0)` |
| `0x00A2..0x00AE` | `02 01 02 03 00 00 a0 c1 00 00 20 41` | Vertex 3 | Marker 1, Class 3 (`TFloatPoint`), raw floats `(-20.0, 10.0)` |
| `0x00AE..0x00B4` | `00 04 ff ff ff 00` | `TPolygon` End | `vaNull` (points end), Brush Color `0x00FFFFFF` (`vaInt32`) |
| `0x00B4..0x00C4` | `02 00 06 0c 54 47 72 61 70 68 69 63 54 65 78 74` | Shape Item 1 | Marker 0, Class Name `"TGraphicText"` (Class ID 4) |
| `0x00C4..0x00CD` | `02 00 02 01 02 01 02 01 01` | `TGraphicText` [Obj#7] | Pen Color 0, Pen Width 1, Points `TSerializeList`, `vaList` |
| `0x00CD..0x00FD` | `...` (4 TFloatPoints) | Text Box | Vertices: `(-13,-6), (-13,6), (13,6), (13,-6)` (48 bytes: 4 × 12 bytes [tag 02 01 + class ref 02 03 + 8 raw float bytes]) |
| `0x00FD..0x0116` | `00 04 ff ff ff 00 02 07 02 00 08 03 90 01 00 00 00 00 06 05 6d 61 63 72 6f` | Text Props | Brush White, Font size 7, Weight 400, Angle 0, Text `"macro"` |
| `0x0116..0x0119` | `09 08 00` | GraphicList End | Flag2 = True, HasSubObject = False, `vaNull` end of list |
| `0x0119..0x0131` | `08 09 02 00 06 0c 54 47 72 61 70 68 69 63 4c 69 73 74 02 01 02 01 01 00` | Macro Pins | Flags, Marker 0 `"TGraphicList"` (Class 5), empty pin list (`01 00`) |
| `0x0131..0x0140` | `06 09 68 65 6c 6c 6f 2e 68 74 6d 02 00 08 08` | Macro Tail | Title `"hello.htm"`, Zero = 0, Flag1 = False, Flag2 = False |
| `0x0140..0x017C` | `(6 × 02 01 02 05 02 01 02 01 01 00)` | Sub-Lists 1..6 | Six empty `TGraphicList` containers (`01 00`) representing empty circuit canvas |

---

## 8.2 2-Input AND Gate Seed (`gate_and_2in.dwm`, 1,913 Bytes)

Key structural breakdown of the 2-input AND gate component definition (bytes `0x0370..0x05CB` in `reference_seeds/gate_and_2in.dwm`):

```
Offset 0x0371: 01                                ; Components TSerializeList begin
Offset 0x0372: 02 00 06 09 54 32 41 6e 64 47 61 74 65  ; Marker 0, "T2AndGate" (Class ID 8)
Offset 0x037F: 08                                ; HasGraphicList = False
Offset 0x0380: 08                                ; IsSelected = False
Offset 0x0381: 08                                ; DeviceFlag = False
Offset 0x0382: 02 01 02 06                       ; Pins Container: Marker 1, Class 6 (TGraphicList)
Offset 0x0386: 02 01 02 01                       ; Inner List: Marker 1, Class 1 (TSerializeList)
Offset 0x038A: 01                                ; vaList begin (3 pins follow)

  ; --- PIN 0: OUTPUT PIN ---
  Offset 0x038B: 02 00 06 04 54 50 69 6e         ; Marker 0, "TPin" (Class ID 9)
  Offset 0x0393: 02 00 02 01                     ; Pen Color = 0, Pen Width = 1
  Offset 0x0397: 02 01 02 01 01                  ; Points List: Marker 1, Class 1, vaList
  Offset 0x039C: 02 01 02 03 00 80 86 43 00 00 01 43 ; Vertex 1: (269.0, 129.0)
  Offset 0x03A8: 02 01 02 03 00 80 86 43 00 00 f2 42 ; Vertex 2: (269.0, 121.0)
  Offset 0x03B4: 02 01 02 03 00 80 82 43 00 00 f2 42 ; Vertex 3: (261.0, 121.0)
  Offset 0x03C0: 02 01 02 03 00 80 82 43 00 00 01 43 ; Vertex 4: (261.0, 129.0)
  ; Pin Center: px = (269+261)/2 = 265.0, py = (129+121)/2 = 125.0 (dx = +30.0, dy = 0.0)
  Offset 0x03CC: 00                              ; vaNull end of pin points
  Offset 0x03CD: 04 ff ff ff 00                  ; Brush Color: 0x00FFFFFF (White)
  Offset 0x03D2: 02 02                           ; Pin Direction = 2 (OUTPUT PIN)
  Offset 0x03D4: 02 00 06 05 54 57 69 72 65 ...  ; Wire connected to output pin (0x03D4..0x044E)

  ; --- PIN 1: INPUT 2 (BOTTOM) ---
  Offset 0x044E: 02 01 02 09                     ; Marker 1, Class 9 ("TPin")
  Offset 0x0452: 02 00 02 01                     ; Pen Color = 0, Pen Width = 1
  Offset 0x0456: 02 01 02 01 01                  ; Points List: Marker 1, Class 1, vaList
  Offset 0x045B: 02 01 02 03 00 00 51 43 00 00 0b 43 ; Vertex 1: (209.0, 139.0)
  Offset 0x0467: 02 01 02 03 00 00 51 43 00 00 03 43 ; Vertex 2: (209.0, 131.0)
  Offset 0x0473: 02 01 02 03 00 00 49 43 00 00 03 43 ; Vertex 3: (201.0, 131.0)
  Offset 0x047F: 02 01 02 03 00 00 49 43 00 00 0b 43 ; Vertex 4: (201.0, 139.0)
  ; Pin Center: px = (209+201)/2 = 205.0, py = (139+131)/2 = 135.0 (dx = -30.0, dy = +10.0)
  Offset 0x048B: 00                              ; vaNull end of pin points
  Offset 0x048C: 04 ff ff ff 00                  ; Brush Color: 0x00FFFFFF (White)
  Offset 0x0491: 02 01                           ; Pin Direction = 1 (INPUT PIN)
  Offset 0x0493: 02 01 02 0a ...                 ; Wire connected to Pin 1 (0x0493..0x0508)

  ; --- PIN 2: INPUT 1 (TOP) ---
  Offset 0x0508: 02 01 02 09                     ; Marker 1, Class 9 ("TPin")
  Offset 0x050C: 02 00 02 01                     ; Pen Color = 0, Pen Width = 1
  Offset 0x0510: 02 01 02 01 01                  ; Points List: Marker 1, Class 1, vaList
  Offset 0x0515: 02 01 02 03 00 00 51 43 00 00 ee 42 ; Vertex 1: (209.0, 119.0)
  Offset 0x0521: 02 01 02 03 00 00 51 43 00 00 de 42 ; Vertex 2: (209.0, 111.0)
  Offset 0x052D: 02 01 02 03 00 00 49 43 00 00 de 42 ; Vertex 3: (201.0, 111.0)
  Offset 0x0539: 02 01 02 03 00 00 49 43 00 00 ee 42 ; Vertex 4: (201.0, 119.0)
  ; Pin Center: px = (209+201)/2 = 205.0, py = (119+111)/2 = 115.0 (dx = -30.0, dy = -10.0)
  Offset 0x0545: 00                              ; vaNull end of pin points
  Offset 0x0546: 04 ff ff ff 00                  ; Brush Color: 0x00FFFFFF (White)
  Offset 0x054B: 02 01                           ; Pin Direction = 1 (INPUT PIN)
  Offset 0x054D: 02 01 02 0a ...                 ; Wire connected to Pin 2 (0x054D..0x05C2)
  Offset 0x05C2: 00                              ; vaNull end of pins list

Offset 0x05C3: 00 00 6b 43 00 00 fa 42           ; Anchor Coordinates: (235.0, 125.0) (raw floats)
```

---

## 8.3 Interactive Input, LED & Wire Seed (`io_switch_led_wire.dwm`, 2,520 Bytes)

Annotated breakdown of components in `reference_seeds/io_switch_led_wire.dwm`:

### 1. `TInteractiveInput` [Obj#183] (bytes `0x08BC..0x08F0`)
```
Offset 0x08BC: 02 00 06 11 54 49 6e 74 65 72 61 63 74 69 76 65 49 6e 70 75 74 ; Marker 0, "TInteractiveInput"
Offset 0x08D1: 08                                ; HasGraphicList = False
Offset 0x08D2: 09                                ; IsSelected = True
Offset 0x08D3: 08                                ; DeviceFlag = False
Offset 0x08D4: 02 01 02 05 02 01 02 01           ; Pins Container: TGraphicList wrapping TSerializeList
Offset 0x08DC: 01 02 02 03 99 00 00              ; vaList, contains Marker 2 Ref(Obj#153) (TPin)
Offset 0x08E3: 00 00 a5 43                       ; Anchor X = 330.0 (IEEE 754 float <f)
Offset 0x08E7: 00 00 7a 43                       ; Anchor Y = 250.0 (IEEE 754 float <f)
Offset 0x08EB: 08                                ; HasLabel = False
Offset 0x08EC: 08                                ; HistoryEnabled = False
Offset 0x08ED: 08                                ; SwitchState = False (Logic 0 / Low)
Offset 0x08EE: 02 00                             ; InputMode = 0 (Toggle Switch)
```

### 2. `TLEDDevice` [Obj#188] (bytes `0x08FA..0x0927`)
```
Offset 0x08FA: 02 00 06 0a 54 4c 45 44 44 65 76 69 63 65 ; Marker 0, "TLEDDevice"
Offset 0x0908: 08                                ; HasGraphicList = False
Offset 0x0909: 08                                ; IsSelected = False
Offset 0x090A: 08                                ; DeviceFlag = False
Offset 0x090B: 02 01 02 05 02 01 02 01           ; Pins Container
Offset 0x0913: 01 02 02 03 89 00 00              ; vaList, contains Marker 2 Ref(Obj#137) (TPin)
Offset 0x091A: 00 00 be 43                       ; Anchor X = 380.0 (IEEE 754 float <f)
Offset 0x091E: 00 00 57 43                       ; Anchor Y = 215.0 (IEEE 754 float <f)
Offset 0x0922: 08                                ; HasLabel = False
Offset 0x0923: 08                                ; HistoryEnabled = False
Offset 0x0924: 03 ff 00                          ; LED Color = 255 (clRed, vaInt16 0x00FF)
```

### 3. Connecting Wire `TWire` [Obj#52] (bytes `0x02B8..0x0336`)
```
Offset 0x02B8: 02 00 06 05 54 57 69 72 65        ; Marker 0, "TWire"
Offset 0x02C1: 02 00 02 01                       ; Pen Color = 0, Pen Width = 1
Offset 0x02C5: 02 01 02 01 01                    ; Points List: Marker 1, Class 1, vaList
Offset 0x02CA: 02 01 02 03 00 00 61 43 00 00 57 43 ; Vertex 0: (225.0, 215.0)
Offset 0x02D6: 02 01 02 03 00 80 84 43 00 00 57 43 ; Vertex 1: (265.0, 215.0) [Collinear Horizontal]
Offset 0x02E2: 00                                ; vaNull end of wire points
Offset 0x02E3: 02 00                             ; Wire State = 0
Offset 0x02E5: 02 00 06 04 54 50 69 6e ...       ; Start Pin (Obj#56 TPin at 225.0, 215.0)
Offset 0x0332: 02 02 02 2e                       ; End Pin: Marker 2 Ref(Obj#46 MacroPin)
```

---

## 8.4 Circuit Half Adder with Solder Joints (`circuit_half_adder.dwm`, 3,581 Bytes)

Breakdown of the branching multi-drop network in `circuit_half_adder.dwm` (bytes `0x06CA..0x0796`):

```
Offset 0x06CA: 02 00 06 07 54 53 6f 6c 64 65 72  ; Marker 0, "TSolder" (Class ID 11)
Offset 0x06D5: 00 00 48 43 00 00 0c 43           ; TSolder [Obj#135] Coordinate: (200.0, 140.0)

; Branch Wire 1: Trunk incoming from Input B (Obj#136)
Offset 0x06DD: 02 01 02 0a 02 00 02 01 02 01 02 01 01 ; Marker 1, Class 10 (TWire), Points List
Offset 0x06EA: 02 01 02 03 00 00 20 43 00 00 0c 43 ; Vertex 0: (160.0, 140.0) [Input B Pin]
Offset 0x06F6: 02 01 02 03 00 00 48 43 00 00 0c 43 ; Vertex 1: (200.0, 140.0) [TSolder Joint]
Offset 0x0702: 00 02 00                          ; vaNull, Wire State = 0
Offset 0x0705: 02 01 02 09 ...                   ; StartPin: Input B Pin at (160.0, 140.0)
Offset 0x074F: 02 02 03 87 00                    ; EndPin: Marker 2 Ref(Obj#135 TSolder)

; Branch Wire 2: Continuation to XOR Gate (Obj#131)
Offset 0x0754: 02 02 03 83 00                    ; TSolder wire2: Marker 2 Ref(Obj#131 TWire)

; Branch Wire 3: L-Shaped Branch to AND Gate (Obj#146)
Offset 0x0759: 02 01 02 0a 02 00 02 01 02 01 02 01 01 ; Marker 1, Class 10 (TWire)
Offset 0x0766: 02 01 02 03 00 00 48 43 00 00 0c 43 ; Vertex 0: (200.0, 140.0) [Starts at TSolder]
Offset 0x0772: 02 01 02 03 00 00 48 43 00 00 48 43 ; Vertex 1: (200.0, 200.0) [Orthogonal Bend, dy=+60]
Offset 0x077E: 02 01 02 03 00 00 6b 43 00 00 48 43 ; Vertex 2: (235.0, 200.0) [Horizontal Run, dx=+35]
Offset 0x078A: 00 02 00                          ; vaNull, Wire State = 0
Offset 0x078D: 02 02 03 87 00                    ; StartPin: Marker 2 Ref(Obj#135 TSolder)
Offset 0x0792: 02 01 02 09 ...                   ; EndPin: Marker 1, Class 9 (TPin on AND Gate)
```

---

# Section 9: Compiler Implementation Checklist & Verification Harness

To ensure that downstream Milestones (`dwm_builder.py`, `test_builder.py`, and E2E validation) achieve 100% binary compatibility with Digital Works 3.04, the compiler implementation must satisfy the following checklist:

- [ ] **Header Invariant**: File begins with exact 5 bytes `\x04\xdd\xc4\x22\x00`.
- [ ] **Preamble Invariant**: Follows with 35-byte tagged metadata list (`01 02 01 02 64 ... 00`).
- [ ] **Integer Compaction**: Integer parameters dynamically encoded as `vaInt8` ($-128..127$), `vaInt16` ($-32768..32767$), or `vaInt32`.
- [ ] **Raw Coordinates**: `TFloatPoint` coordinates written as 8 contiguous raw IEEE 754 floats (`<ff`) without `vaSingle` (`0x0F`).
- [ ] **Object Deduplication**: Serializer tracks `Classes` and `Objects`; emits Marker 2 (`0x02 0x02 <id>`) for previously serialized instances.
- [ ] **NOT Gate Offsets**: Input placed at $dx = -20.0$, Output placed at $dx = +30.0$.
- [ ] **2-Input Gate Offsets**: Output at $dx = +30.0$; Input 2 (bottom) at $(-30.0, +10.0)$; Input 1 (top) at $(-30.0, -10.0)$.
- [ ] **Interactive I/O Offsets**: Input Switch at $(0.0, 0.0)$; LED at $(0.0, 0.0)$; Toggle Switch at $(-15.0, 0.0)$ and $(+15.0, 0.0)$.
- [ ] **Pin Bounding Box**: $8 \times 8$ px box vertices at $[(px+4, py+4), (px+4, py-4), (px-4, py-4), (px-4, py+4)]$.
- [ ] **Orthogonal Routing**: Wire vertex lists strictly orthogonal ($dx == 0 \lor dy == 0$), zero diagonal segments, snapped to 5 px grid.
- [ ] **Solder Joints**: `TSolder` inserted at 3-way wire junction vertices with references to all three connected branches.

---
*End of Specification — Digital Works 3.04 Binary Format Standard*
