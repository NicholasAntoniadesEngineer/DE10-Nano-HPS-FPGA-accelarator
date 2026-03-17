# KiCAD S-Expression Parser - Usage Examples

This document provides practical examples for using the `kicad_sexpression.py` module to parse and modify KiCAD footprint files.

## Overview

The module provides three main classes:

1. **SExpressionTokenizer** - Converts raw KiCAD s-expression text into tokens
2. **SExpressionParser** - Converts tokens into a nested tree structure and provides search utilities
3. **KiCADFootprintModifier** - High-level interface for modifying footprint files

Plus helper functions for common tasks.

## Quick Start Example

### Read, Parse, and Add 3D Model to Footprint

```python
from pathlib import Path
from kicad_sexpression import KiCADFootprintModifier

# Create modifier instance
footprint_path = Path("footprints/capacitor_0402.kicad_mod")
modifier = KiCADFootprintModifier(footprint_path)

# Read and parse the footprint file
if not modifier.read_file():
    print("Failed to read footprint file")
    exit(1)

if not modifier.parse():
    print("Failed to parse footprint")
    exit(1)

# Check if model reference already exists
if modifier.has_model_reference():
    print("Footprint already has a model reference")
    exit(0)

# Add 3D model reference
model_path = "3dmodels/capacitor/C2040_0402.step"
if modifier.add_model_reference(model_path, relative=True):
    # Write modified footprint back
    if modifier.write_file():
        print(f"Successfully added model to {footprint_path}")
    else:
        print("Failed to write footprint file")
else:
    print("Failed to add model reference")
```

## Tokenizer Usage

### Basic Tokenization

```python
from kicad_sexpression import SExpressionTokenizer

tokenizer = SExpressionTokenizer()

# Simple s-expression
content = '(footprint "Test_Pad" (pad "1" smd circle))'
tokens = tokenizer.tokenize(content)

# Tokens are Token objects with position info
for token in tokens:
    print(f"{token.value:15} at line {token.line}, col {token.column}")
```

Output:
```
(               at line 1, col 0
footprint       at line 1, col 1
"Test_Pad"      at line 1, col 11
(               at line 1, col 22
pad             at line 1, col 23
"1"             at line 1, col 27
smd             at line 1, col 31
circle          at line 1, col 35
)               at line 1, col 41
)               at line 1, col 42
```

### Handling Complex Strings

```python
from kicad_sexpression import SExpressionTokenizer

tokenizer = SExpressionTokenizer()

# Path with escaped quotes
content = '(model "${KIPRJMOD}/3dmodels/test.step")'
tokens = tokenizer.tokenize(content)

# Quoted strings are preserved with quotes
model_path_token = tokens[2]
print(model_path_token.value)
# Output: "${KIPRJMOD}/3dmodels/test.step"
```

## Parser Usage

### Parse S-Expression into Tree

```python
from kicad_sexpression import SExpressionTokenizer, SExpressionParser

# Tokenize
tokenizer = SExpressionTokenizer()
content = '(footprint "C0402" (pad "1" smd circle) (pad "2" smd circle))'
tokens = tokenizer.tokenize(content)

# Parse
parser = SExpressionParser()
tree = parser.parse(tokens)

# Tree is nested list structure
print(tree)
# Output: ['footprint', 'C0402', ['pad', '1', 'smd', 'circle'], ['pad', '2', 'smd', 'circle']]
```

### Find Elements in Tree

```python
parser = SExpressionParser()
tree = ['footprint', 'C0402',
        ['pad', '1', 'smd', 'circle'],
        ['pad', '2', 'smd', 'circle']]

# Find all pads
pads = parser.find_elements(tree, "pad")
print(f"Found {len(pads)} pads")
# Output: Found 2 pads

# Check if element exists
has_model = parser.has_element(tree, "model")
print(f"Has model: {has_model}")
# Output: Has model: False
```

### Get Specific Element

```python
# Get first pad element
first_pad = parser.find_element_at_index(tree, "pad", 0)
print(first_pad)
# Output: ['pad', '1', 'smd', 'circle']

# Get second pad
second_pad = parser.find_element_at_index(tree, "pad", 1)
print(second_pad)
# Output: ['pad', '2', 'smd', 'circle']
```

## Footprint Modifier Usage

### Complete Example: Multi-Step Workflow

```python
from pathlib import Path
from kicad_sexpression import KiCADFootprintModifier

def process_footprints(footprints_dir: Path, models_dir: Path):
    """Add 3D models to all footprints in a directory"""

    for footprint_file in footprints_dir.glob("*.kicad_mod"):
        print(f"\nProcessing: {footprint_file.name}")

        modifier = KiCADFootprintModifier(footprint_file)

        # Read and parse
        if not modifier.read_file() or not modifier.parse():
            print(f"  ERROR: Could not parse {footprint_file}")
            continue

        # Check if already has model
        if modifier.has_model_reference():
            print(f"  SKIP: Already has model reference")
            continue

        # Determine model path
        footprint_name = footprint_file.stem
        model_path = f"3dmodels/{footprint_name}.step"

        # Add model reference
        if modifier.add_model_reference(model_path, relative=True):
            # Write back to same file
            if modifier.write_file():
                print(f"  SUCCESS: Added model {model_path}")
            else:
                print(f"  ERROR: Failed to write file")
        else:
            print(f"  ERROR: Failed to add model reference")

# Usage
footprints = Path("footprints")
models = Path("3dmodels")
process_footprints(footprints, models)
```

### Read Existing Footprint

```python
footprint_path = Path("footprints/my_component.kicad_mod")
modifier = KiCADFootprintModifier(footprint_path)

if modifier.read_file():
    print(f"Read {len(modifier.content)} characters")
    print("First 200 chars:")
    print(modifier.content[:200])
```

### Check for Model Before Adding

```python
modifier = KiCADFootprintModifier(footprint_path)

if not modifier.read_file() or not modifier.parse():
    exit(1)

# Three ways to check for model
if modifier.has_model_reference():
    print("Footprint has 3D model")
else:
    print("No 3D model - can add one")
    modifier.add_model_reference("3dmodels/component.step")
    modifier.write_file()
```

### Output to Different File

```python
modifier = KiCADFootprintModifier(footprint_path)

if modifier.read_file() and modifier.parse():
    modifier.add_model_reference("3dmodels/component.step")

    # Write to new file instead of overwriting
    output_path = Path("output/modified_footprint.kicad_mod")
    if modifier.write_file(output_path):
        print(f"Wrote to {output_path}")
```

## Helper Functions

### Check for Model in Raw Content

```python
from kicad_sexpression import has_model_reference

content = """(footprint "C0402"
  (pad "1" smd circle)
  (model "${KIPRJMOD}/3dmodels/c0402.step"
    (at (xyz 0 0 0))
    (scale (xyz 1 1 1))
    (rotate (xyz 0 0 0))
  )
)"""

if has_model_reference(content):
    print("This footprint has a 3D model")
else:
    print("No 3D model found")
```

### Format Model Entry

```python
from kicad_sexpression import format_model_entry

# Generate formatted model entry
entry = format_model_entry("3dmodels/capacitor.step", relative=True)
print(entry)

# Output:
# (model "${KIPRJMOD}/3dmodels/capacitor.step"
#     (at (xyz 0 0 0))
#     (scale (xyz 1 1 1))
#     (rotate (xyz 0 0 0))
# )
```

## Error Handling

### Graceful Failure

```python
from kicad_sexpression import KiCADFootprintModifier
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)

modifier = KiCADFootprintModifier(Path("nonexistent.kicad_mod"))

# Each method returns False on failure
if not modifier.read_file():
    print("Could not read file")
    exit(1)

if not modifier.parse():
    print("Could not parse file")
    exit(1)

if not modifier.add_model_reference("model.step"):
    print("Could not add model")
    exit(1)

if not modifier.write_file():
    print("Could not write file")
    exit(1)

print("Success!")
```

### Exception Handling

```python
from kicad_sexpression import SExpressionTokenizer

tokenizer = SExpressionTokenizer()

try:
    # Malformed s-expression
    tokens = tokenizer.tokenize('(unclosed')
except ValueError as e:
    print(f"Tokenization failed: {e}")

try:
    # Another invalid case
    tokens = tokenizer.tokenize('(unterminated "string)')
except ValueError as e:
    print(f"Parsing failed: {e}")
```

## Integration with LCSC Automation

### Batch Process Downloaded Footprints

```python
from pathlib import Path
from kicad_sexpression import KiCADFootprintModifier

def add_models_to_library(library_path: Path, models_base_dir: Path):
    """
    Add 3D model references to all footprints in a KiCAD library.
    Assumes model files named after footprint files.
    """
    footprints_dir = library_path / "footprints"

    if not footprints_dir.exists():
        print(f"Footprints directory not found: {footprints_dir}")
        return

    results = {"success": 0, "skipped": 0, "failed": 0}

    for footprint_file in footprints_dir.glob("**/*.kicad_mod"):
        relative_path = footprint_file.relative_to(footprints_dir)
        model_name = relative_path.with_suffix(".step").name
        model_path = f"3dmodels/{model_name}"

        modifier = KiCADFootprintModifier(footprint_file)

        if not modifier.read_file() or not modifier.parse():
            results["failed"] += 1
            continue

        if modifier.has_model_reference():
            results["skipped"] += 1
            continue

        if modifier.add_model_reference(model_path):
            if modifier.write_file():
                results["success"] += 1
            else:
                results["failed"] += 1
        else:
            results["failed"] += 1

    print(f"\nResults:")
    print(f"  Added models: {results['success']}")
    print(f"  Already had models: {results['skipped']}")
    print(f"  Failed: {results['failed']}")

# Usage
library = Path("kicad_library")
add_models_to_library(library, library / "3dmodels")
```

## Edge Cases and Gotchas

### Relative vs Absolute Paths

```python
# With relative=True (default), path is wrapped with ${KIPRJMOD}/
modifier.add_model_reference("3dmodels/component.step", relative=True)
# Result: "${KIPRJMOD}/3dmodels/component.step"

# With relative=False, path is used as-is (but backslashes are converted)
modifier.add_model_reference("C:/models/component.step", relative=False)
# Result: "C:/models/component.step"
```

### Path Separators

```python
# Both forward and backslashes are normalized to forward slashes
modifier.add_model_reference("3dmodels\\components\\cap.step")
# Normalized to: "${KIPRJMOD}/3dmodels/components/cap.step"
```

### Already Has Model

```python
modifier.parse()

# Returns False and logs warning
if not modifier.add_model_reference("model.step"):
    if modifier.has_model_reference():
        print("Model already exists - cannot add duplicate")
```

### Empty or Invalid Files

```python
modifier = KiCADFootprintModifier(Path("empty.kicad_mod"))

# Returns False
if not modifier.read_file():
    print("File read failed")

# File must be readable to proceed
if not modifier.parse():
    print("Parse failed or no tree")
```

### Indentation Preservation

The module uses tabs for indentation to match KiCAD's default formatting:

```python
# Output uses DEFAULT_INDENT = "\t"
entry = format_model_entry("3dmodels/test.step")
# Output will be tab-indented
```

## Performance Considerations

- **Tokenization**: O(n) where n is file size. Very fast for typical footprints.
- **Parsing**: O(n) with single pass. Minimal memory overhead.
- **Search**: O(n) for each find operation (linear tree scan).
- **Serialization**: O(n) to rebuild file content.

Typical .kicad_mod files are < 50KB, so performance is not a concern.

## Debugging Tips

### Enable Detailed Logging

```python
import logging

# Set module logger to DEBUG
logging.getLogger('kicad_sexpression').setLevel(logging.DEBUG)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(name)s - %(levelname)s - %(message)s'
)

# Now operations will log detailed information
modifier = KiCADFootprintModifier(path)
modifier.read_file()  # Will log read details
modifier.parse()      # Will log parse details
```

### Inspect Parsed Tree

```python
import json

parser = SExpressionParser()
tree = parser.parse(tokens)

# Pretty print tree structure
def pretty_tree(node, indent=0):
    if isinstance(node, list):
        print("  " * indent + "[")
        for item in node:
            pretty_tree(item, indent + 1)
        print("  " * indent + "]")
    else:
        print("  " * indent + repr(node))

pretty_tree(tree)
```

### Verify Token Stream

```python
tokenizer = SExpressionTokenizer()
tokens = tokenizer.tokenize(content)

print(f"Total tokens: {len(tokens)}")
for i, token in enumerate(tokens[:20]):  # First 20 tokens
    print(f"{i:3d}: {token}")
```
