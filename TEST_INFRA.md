# E2E Test Infra: Digital Works DWM Circuit Compiler

## Test Philosophy
- **Opaque-box, requirement-driven**: Tests are constructed strictly from user requirements (`ORIGINAL_REQUEST.md`) and the public interface contracts in `PROJECT.md`, without coupling to internal private implementation details of `dwm_builder.py`.
- **Methodology**: Systematic 4-tier design:
  - Category-Partition Testing (Equivalence Classes).
  - Boundary Value Analysis (BVA).
  - Pairwise Combinatorial Interaction Testing.
  - Real-World Application Workload Scenarios.

## Feature Inventory
| # | Feature | Source (requirement) | Tier 1 | Tier 2 | Tier 3 |
|---|---------|----------------------|:------:|:------:|:------:|
| 1 | Input Device Placement (`add_input`) | ORIGINAL_REQUEST §R3 | ≥5 | ≥5 | ✓ |
| 2 | LED Device Placement (`add_led`) | ORIGINAL_REQUEST §R3 | ≥5 | ≥5 | ✓ |
| 3 | Logic Gate Placement (`add_gate`) | ORIGINAL_REQUEST §R3 | ≥5 | ≥5 | ✓ |
| 4 | Pin Coordinate Calculation | ORIGINAL_REQUEST §R3 | ≥5 | ≥5 | ✓ |
| 5 | Orthogonal Manhattan Wire Routing | ORIGINAL_REQUEST §R3 | ≥5 | ≥5 | ✓ |
| 6 | ASCII Grid Layout Previewer (`preview`) | ORIGINAL_REQUEST §R3 | ≥5 | ≥5 | ✓ |
| 7 | Binary Serialization (`save`, `to_bytes`) | ORIGINAL_REQUEST §R3 | ≥5 | ≥5 | ✓ |

## Test Architecture
- **Test Runner**: `pytest`
- **Invocation**: `pytest -v tests/test_e2e.py`
- **Pass/Fail Semantics**: Exit code 0 indicates all assertions pass; non-zero indicates failure.
- **Test File**: `tests/test_e2e.py`
- **Directory Layout**:
  - `tests/`: Root test directory
  - `tests/test_e2e.py`: Opaque-box E2E test suite (Tiers 1-4)
  - `reference_seeds/`: Calibration seed circuits used for differential validation
- **Interface Tested**:
  - `DWMBuilder`:
    - `__init__(title: str = ...)`
    - `add_input(x: float, y: float, label: str = "") -> Component`
    - `add_led(x: float, y: float, label: str = "") -> Component`
    - `add_gate(gate_type: str, x: float, y: float, label: str = "") -> Component`
    - `connect(source_pin: Pin, dest_pin: Pin) -> Wire`
    - `preview() -> str`
    - `save(file_path: str) -> None`
    - `to_bytes() -> bytes`

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | Half Adder (XOR sum, AND carry) | F1, F2, F3, F4, F5, F6, F7 | Medium |
| 2 | Full Adder (2 XORs, 2 ANDs, 1 OR, Cin/Cout) | F1, F2, F3, F4, F5, F6, F7 | High |
| 3 | 2x1 Multiplexer (Select, D0, D1, NOT, 2 ANDs, OR) | F1, F2, F3, F4, F5, F6, F7 | High |
| 4 | SR Latch (Cross-coupled feedback logic) | F1, F2, F3, F4, F5, F6, F7 | High |
| 5 | 3-bit Parity Checker (Cascaded XOR tree) | F1, F2, F3, F4, F5, F6, F7 | Medium |

## Coverage Thresholds
- **Tier 1 (Feature Coverage)**: ≥5 tests per feature across all 7 features (minimum 35 tests)
- **Tier 2 (Boundary & Corner Cases)**: ≥5 tests per feature across all 7 features (minimum 35 tests)
- **Tier 3 (Cross-Feature Combinations)**: Pairwise coverage of all major feature interactions (minimum 10 tests)
- **Tier 4 (Real-World Application Scenarios)**: 5 realistic multi-component application workloads (minimum 5 tests)
- **Total Minimum Suite Size**: ≥85 test cases
