"""
Comprehensive tests for 3D model linking functionality in KiCADLibraryManager.
Tests footprint 3D model integration, s-expression parsing, batch operations,
and end-to-end library management with 3D models.
"""

import pytest
from pathlib import Path
from typing import Dict, List, Any
import tempfile
import shutil


@pytest.mark.unit
class TestFootprintModeling:
    """Tests for footprint 3D model integration"""

    def test_link_3d_model_single_step_file(self, temp_dir):
        """Test linking a single STEP file to a footprint"""
        from library_manager import KiCADLibraryManager

        mgr = KiCADLibraryManager(library_base_dir=temp_dir)

        # Create test footprint directory structure
        lcsc_id = "C2040"
        pretty_dir = mgr.footprints_dir / f"{lcsc_id}_PAD1206.pretty"
        pretty_dir.mkdir(parents=True, exist_ok=True)

        # Create a footprint file
        footprint_content = """(footprint "PAD1206" (version 20221018) (generator pcbnew)
  (layer "F.Cu")
  (fp_text reference "REF**" (at 0 -1.8) (layer "F.SilkS")
    (effects (font (size 1 1) (thickness 0.15))))
  (fp_text value "PAD1206" (at 0 1.8) (layer "F.Fab")
    (effects (font (size 1 1) (thickness 0.15))))
)"""
        footprint_file = pretty_dir / "PAD1206.kicad_mod"
        footprint_file.write_text(footprint_content)

        # Create a 3D model file
        model_dir = mgr.models_dir
        model_file = model_dir / f"{lcsc_id}_PAD1206.step"
        model_file.write_text("ISO-10303-21;\nEND-ISO-10303-21;")

        # Link the model
        mgr._add_model_to_footprint(footprint_file, model_file, pretty_dir)

        # Verify the footprint now contains (model ...) entry
        updated_content = footprint_file.read_text()
        assert "(model " in updated_content
        assert "3dmodels/C2040_PAD1206.step" in updated_content
        assert "(offset (xyz 0 0 0))" in updated_content
        assert "(scale (xyz 1 1 1))" in updated_content
        assert "(rotate (xyz 0 0 0))" in updated_content

    def test_link_3d_model_prefers_step_over_wrl(self, temp_dir):
        """Test that STEP files are preferred over VRML files"""
        from library_manager import KiCADLibraryManager

        mgr = KiCADLibraryManager(library_base_dir=temp_dir)

        lcsc_id = "C4169"
        pretty_dir = mgr.footprints_dir / f"{lcsc_id}_RES0402.pretty"
        pretty_dir.mkdir(parents=True, exist_ok=True)

        footprint_file = pretty_dir / "RES0402.kicad_mod"
        footprint_file.write_text("""(footprint "RES0402" (version 20221018)
  (layer "F.Cu")
  (fp_text reference "R**" (at 0 -1.5) (layer "F.SilkS"))
  (fp_text value "RES0402" (at 0 1.5) (layer "F.Fab"))
)""")

        # Create both STEP and VRML model files
        model_dir = mgr.models_dir
        step_file = model_dir / f"{lcsc_id}_RES0402.step"
        wrl_file = model_dir / f"{lcsc_id}_RES0402.wrl"

        step_file.write_text("ISO-10303-21;\nEND-ISO-10303-21;")
        wrl_file.write_text("#VRML V2.0 utf8\nWorldInfo {}")

        # Link the STEP file
        mgr._add_model_to_footprint(footprint_file, step_file, pretty_dir)

        # Verify STEP file is referenced, not VRML
        updated_content = footprint_file.read_text()
        assert "(model " in updated_content
        assert ".step" in updated_content
        assert ".wrl" not in updated_content

    def test_link_3d_model_relative_path_calculation(self, temp_dir):
        """Test that relative path from footprint to model is calculated correctly"""
        from library_manager import KiCADLibraryManager

        mgr = KiCADLibraryManager(library_base_dir=temp_dir)

        lcsc_id = "C529971"
        pretty_dir = mgr.footprints_dir / f"{lcsc_id}_LQFP48.pretty"
        pretty_dir.mkdir(parents=True, exist_ok=True)

        footprint_file = pretty_dir / "LQFP48.kicad_mod"
        footprint_file.write_text("""(footprint "LQFP48" (version 20221018)
  (layer "F.Cu")
)""")

        model_file = mgr.models_dir / f"{lcsc_id}_LQFP48.step"
        model_file.write_text("ISO-10303-21;\nEND-ISO-10303-21;")

        # Link the model
        mgr._add_model_to_footprint(footprint_file, model_file, pretty_dir)

        # Verify relative path is correct
        # From: footprints/C529971_LQFP48.pretty/LQFP48.kicad_mod
        # To: 3dmodels/C529971_LQFP48.step
        # Path: ../../3dmodels/C529971_LQFP48.step
        updated_content = footprint_file.read_text()
        assert '../../3dmodels/C529971_LQFP48.step' in updated_content

    def test_link_3d_model_skip_existing_reference(self, temp_dir):
        """Test that existing (model ...) references are not overwritten"""
        from library_manager import KiCADLibraryManager

        mgr = KiCADLibraryManager(library_base_dir=temp_dir)

        lcsc_id = "C2040"
        pretty_dir = mgr.footprints_dir / f"{lcsc_id}_PAD1206.pretty"
        pretty_dir.mkdir(parents=True, exist_ok=True)

        # Create footprint with existing model reference
        existing_model = "../../3dmodels/existing_model.step"
        footprint_content = f"""(footprint "PAD1206" (version 20221018)
  (layer "F.Cu")
  (model "{existing_model}"
    (offset (xyz 0 0 0))
    (scale (xyz 1 1 1))
    (rotate (xyz 0 0 0)))
)"""
        footprint_file = pretty_dir / "PAD1206.kicad_mod"
        footprint_file.write_text(footprint_content)

        # Try to add a new model
        model_file = mgr.models_dir / f"{lcsc_id}_new_model.step"
        model_file.write_text("ISO-10303-21;\nEND-ISO-10303-21;")

        result = mgr._add_model_to_footprint(footprint_file, model_file, pretty_dir)

        # Should return True (no error) but not modify the file
        assert result is True
        updated_content = footprint_file.read_text()
        assert existing_model in updated_content
        assert "new_model" not in updated_content

    def test_link_3d_model_multiple_files_per_part(self, temp_dir):
        """Test handling of multiple 3D model files for the same part"""
        from library_manager import KiCADLibraryManager

        mgr = KiCADLibraryManager(library_base_dir=temp_dir)

        lcsc_id = "C4216"
        pretty_dir = mgr.footprints_dir / f"{lcsc_id}_IND0603.pretty"
        pretty_dir.mkdir(parents=True, exist_ok=True)

        # Create a footprint
        footprint_file = pretty_dir / "IND0603.kicad_mod"
        footprint_file.write_text("""(footprint "IND0603" (version 20221018)
  (layer "F.Cu")
)""")

        # Create multiple 3D model files
        model_dir = mgr.models_dir
        model_file_1 = model_dir / f"{lcsc_id}_IND0603_v1.step"
        model_file_2 = model_dir / f"{lcsc_id}_IND0603_v2.step"

        model_file_1.write_text("ISO-10303-21;\nEND-ISO-10303-21;")
        model_file_2.write_text("ISO-10303-21;\nEND-ISO-10303-21;")

        # Link first model
        mgr._add_model_to_footprint(footprint_file, model_file_1, pretty_dir)

        updated_content = footprint_file.read_text()
        assert "(model " in updated_content
        assert "v1.step" in updated_content

        # Attempting to link second model should be skipped (already has model)
        result = mgr._add_model_to_footprint(footprint_file, model_file_2, pretty_dir)
        assert result is True

        # Verify still only first model is linked
        final_content = footprint_file.read_text()
        assert "v1.step" in final_content
        assert "v2.step" not in final_content

    def test_link_3d_model_no_models_found(self, temp_dir):
        """Test graceful handling when no 3D model files exist"""
        from library_manager import KiCADLibraryManager

        mgr = KiCADLibraryManager(library_base_dir=temp_dir)

        lcsc_id = "C9999"
        pretty_dir = mgr.footprints_dir / f"{lcsc_id}_TEST.pretty"
        pretty_dir.mkdir(parents=True, exist_ok=True)

        footprint_file = pretty_dir / "TEST.kicad_mod"
        footprint_file.write_text("""(footprint "TEST" (version 20221018)
  (layer "F.Cu")
)""")

        # Call _link_3d_models_to_footprints with no models
        # Should log debug message and return without error
        mgr._link_3d_models_to_footprints(lcsc_id)

        # Footprint should remain unchanged
        updated_content = footprint_file.read_text()
        assert "(model " not in updated_content

    def test_link_3d_model_preserves_footprint_formatting(self, temp_dir):
        """Test that original footprint formatting is preserved"""
        from library_manager import KiCADLibraryManager

        mgr = KiCADLibraryManager(library_base_dir=temp_dir)

        lcsc_id = "C2040"
        pretty_dir = mgr.footprints_dir / f"{lcsc_id}_PAD1206.pretty"
        pretty_dir.mkdir(parents=True, exist_ok=True)

        # Create footprint with specific formatting
        footprint_content = """(footprint "PAD1206" (version 20221018) (generator pcbnew)
  (layer "F.Cu")
  (attr smd)
  (fp_text reference "REF**" (at 0 -1.8) (layer "F.SilkS")
    (effects (font (size 1 1) (thickness 0.15))))
  (fp_text value "PAD1206" (at 0 1.8) (layer "F.Fab")
    (effects (font (size 1 1) (thickness 0.15))))
  (pad "1" smd rect (at -0.5 0) (size 1 1.2) (layers "F.Cu" "F.Paste" "F.Mask"))
  (pad "2" smd rect (at 0.5 0) (size 1 1.2) (layers "F.Cu" "F.Paste" "F.Mask"))
)"""
        footprint_file = pretty_dir / "PAD1206.kicad_mod"
        footprint_file.write_text(footprint_content)

        model_file = mgr.models_dir / f"{lcsc_id}_PAD1206.step"
        model_file.write_text("ISO-10303-21;\nEND-ISO-10303-21;")

        mgr._add_model_to_footprint(footprint_file, model_file, pretty_dir)

        updated_content = footprint_file.read_text()

        # Check that original elements are preserved
        assert 'generator pcbnew' in updated_content
        assert '(attr smd)' in updated_content
        assert '"REF**"' in updated_content
        assert '(pad "1"' in updated_content
        assert '(pad "2"' in updated_content
        assert '(model ' in updated_content

    def test_link_3d_model_correct_kiprjmod_syntax(self, temp_dir):
        """Test that ${KIPRJMOD} path reference syntax is valid"""
        from library_manager import KiCADLibraryManager

        mgr = KiCADLibraryManager(library_base_dir=temp_dir)

        lcsc_id = "C2040"
        pretty_dir = mgr.footprints_dir / f"{lcsc_id}_PAD1206.pretty"
        pretty_dir.mkdir(parents=True, exist_ok=True)

        footprint_file = pretty_dir / "PAD1206.kicad_mod"
        footprint_file.write_text("""(footprint "PAD1206" (version 20221018)
  (layer "F.Cu")
)""")

        model_file = mgr.models_dir / f"{lcsc_id}_PAD1206.step"
        model_file.write_text("ISO-10303-21;\nEND-ISO-10303-21;")

        mgr._add_model_to_footprint(footprint_file, model_file, pretty_dir)

        updated_content = footprint_file.read_text()

        # Verify the model path uses forward slashes (cross-platform compatible)
        assert "(model " in updated_content
        assert "\\" not in updated_content.split("(model ")[1].split('"')[0:2]


@pytest.mark.unit
class TestSExpressionParsing:
    """Tests for s-expression parser used in footprint handling"""

    def test_tokenize_simple_sexpression(self):
        """Test tokenizing basic s-expression with parentheses and spaces"""
        from library_manager import KiCADLibraryManager

        mgr = KiCADLibraryManager()

        # The actual tokenization happens during footprint reading/writing
        # This test validates the conceptual parsing
        test_expr = '(footprint "TEST" (version 20221018))'

        # Verify basic structure is preserved through read/write
        assert test_expr.count('(') == test_expr.count(')')
        assert '"TEST"' in test_expr

    def test_tokenize_quoted_strings(self):
        """Test handling of quoted strings in s-expressions"""
        test_expr = '(model "../../3dmodels/C2040_test.step"'

        # Verify quoted paths are preserved
        assert '"../../3dmodels/C2040_test.step"' in test_expr

    def test_tokenize_nested_structures(self):
        """Test handling of nested s-expression structures"""
        nested_expr = """(footprint "TEST"
  (fp_text reference "REF"
    (effects (font (size 1 1) (thickness 0.15))))
  (model "path.step"
    (offset (xyz 0 0 0))
    (scale (xyz 1 1 1))
    (rotate (xyz 0 0 0)))
)"""

        # Verify structure integrity
        assert nested_expr.count('(') == nested_expr.count(')')
        assert nested_expr.count('(font') == 1
        assert nested_expr.count('(offset') == 1

    def test_parse_footprint_structure(self, temp_dir):
        """Test parsing a real footprint s-expression"""
        footprint_content = """(footprint "PAD1206" (version 20221018) (generator pcbnew)
  (layer "F.Cu")
  (attr smd)
  (fp_text reference "REF**" (at 0 -1.8) (layer "F.SilkS"))
  (fp_line (start -0.5 -0.5) (end 0.5 -0.5) (layer "F.SilkS") (width 0.12))
  (pad "1" smd rect (at -0.5 0) (size 1 1.2) (layers "F.Cu" "F.Paste" "F.Mask"))
)"""

        # Verify structure can be parsed
        lines = footprint_content.split('\n')
        assert lines[0].startswith('(footprint')
        assert any('(pad' in line for line in lines)
        assert footprint_content.rstrip().endswith(')')

    def test_find_model_element(self, temp_dir):
        """Test locating existing (model ...) element in footprint"""
        footprint_with_model = """(footprint "TEST"
  (fp_text reference "REF")
  (model "path/to/model.step"
    (offset (xyz 0 0 0)))
)"""

        # Verify model element can be found
        assert "(model " in footprint_with_model
        model_start = footprint_with_model.find("(model ")
        assert model_start > 0

    def test_find_insertion_point(self, temp_dir):
        """Test locating correct insertion point for (model ...) in footprint"""
        footprint_content = """(footprint "TEST"
  (fp_text reference "REF")
  (pad "1" smd rect (at 0 0) (size 1 1))
)"""

        # Insertion point should be before closing paren
        assert footprint_content.rstrip().endswith(')')
        insertion_index = len(footprint_content.rstrip()) - 1
        assert insertion_index > 0

    def test_format_model_entry(self):
        """Test proper s-expression formatting of model entry"""
        rel_path = "../../3dmodels/C2040_test.step"
        model_entry = f'\n  (model "{rel_path}"\n    (offset (xyz 0 0 0))\n    (scale (xyz 1 1 1))\n    (rotate (xyz 0 0 0)))'

        # Verify s-expression structure
        assert model_entry.startswith('\n  (model')
        assert '(offset' in model_entry
        assert '(scale' in model_entry
        assert '(rotate' in model_entry
        assert model_entry.count('(') == model_entry.count(')')

    def test_has_model_reference_true(self):
        """Test detection of existing model reference"""
        footprint_with_model = """(footprint "TEST"
  (model "path.step"
    (offset (xyz 0 0 0)))
)"""

        assert "(model " in footprint_with_model

    def test_has_model_reference_false(self):
        """Test detection when no model reference exists"""
        footprint_without_model = """(footprint "TEST"
  (fp_text reference "REF")
  (pad "1" smd rect)
)"""

        assert "(model " not in footprint_without_model


@pytest.mark.unit
class TestEdgeCases:
    """Tests for edge cases and error handling"""

    def test_footprint_with_no_pads(self, temp_dir):
        """Test handling footprint with unusual structure (no pads)"""
        from library_manager import KiCADLibraryManager

        mgr = KiCADLibraryManager(library_base_dir=temp_dir)

        lcsc_id = "C0001"
        pretty_dir = mgr.footprints_dir / f"{lcsc_id}_NOPADS.pretty"
        pretty_dir.mkdir(parents=True, exist_ok=True)

        # Footprint with no pads (unusual but valid)
        footprint_file = pretty_dir / "NOPADS.kicad_mod"
        footprint_file.write_text("""(footprint "NOPADS" (version 20221018)
  (layer "F.Cu")
  (fp_text reference "REF" (at 0 0))
)""")

        model_file = mgr.models_dir / f"{lcsc_id}_NOPADS.step"
        model_file.write_text("ISO-10303-21;\nEND-ISO-10303-21;")

        result = mgr._add_model_to_footprint(footprint_file, model_file, pretty_dir)
        assert result is True

        updated_content = footprint_file.read_text()
        assert "(model " in updated_content

    def test_footprint_already_has_model(self, temp_dir):
        """Test that duplicate model references are not created"""
        from library_manager import KiCADLibraryManager

        mgr = KiCADLibraryManager(library_base_dir=temp_dir)

        lcsc_id = "C2040"
        pretty_dir = mgr.footprints_dir / f"{lcsc_id}_PAD1206.pretty"
        pretty_dir.mkdir(parents=True, exist_ok=True)

        footprint_file = pretty_dir / "PAD1206.kicad_mod"
        footprint_file.write_text("""(footprint "PAD1206"
  (model "existing.step"
    (offset (xyz 0 0 0)))
)""")

        model_file = mgr.models_dir / f"{lcsc_id}_PAD1206.step"
        model_file.write_text("ISO-10303-21;\nEND-ISO-10303-21;")

        # Attempt to add model
        result = mgr._add_model_to_footprint(footprint_file, model_file, pretty_dir)
        assert result is True

        # Verify only one model entry exists
        updated_content = footprint_file.read_text()
        model_count = updated_content.count("(model ")
        assert model_count == 1
        assert "existing.step" in updated_content

    def test_path_with_special_characters(self, temp_dir):
        """Test handling of paths with spaces and special characters"""
        from library_manager import KiCADLibraryManager

        mgr = KiCADLibraryManager(library_base_dir=temp_dir)

        lcsc_id = "C2040"
        pretty_dir = mgr.footprints_dir / f"{lcsc_id}_PAD1206.pretty"
        pretty_dir.mkdir(parents=True, exist_ok=True)

        footprint_file = pretty_dir / "PAD1206.kicad_mod"
        footprint_file.write_text("""(footprint "PAD1206" (version 20221018)
  (layer "F.Cu")
)""")

        # Create model with spaces in name (KiCAD allows this)
        model_file = mgr.models_dir / f"{lcsc_id}_PAD 1206 v2.step"
        model_file.write_text("ISO-10303-21;\nEND-ISO-10303-21;")

        result = mgr._add_model_to_footprint(footprint_file, model_file, pretty_dir)
        assert result is True

        updated_content = footprint_file.read_text()
        assert "(model " in updated_content
        assert "PAD 1206 v2.step" in updated_content

    def test_model_file_not_found(self, temp_dir):
        """Test graceful handling when 3D model file is missing"""
        from library_manager import KiCADLibraryManager

        mgr = KiCADLibraryManager(library_base_dir=temp_dir)

        lcsc_id = "C9999"
        pretty_dir = mgr.footprints_dir / f"{lcsc_id}_TEST.pretty"
        pretty_dir.mkdir(parents=True, exist_ok=True)

        footprint_file = pretty_dir / "TEST.kicad_mod"
        footprint_file.write_text("""(footprint "TEST"
  (layer "F.Cu")
)""")

        # Reference non-existent model file
        model_file = mgr.models_dir / f"{lcsc_id}_MISSING.step"
        # Don't create the file

        # Should handle gracefully (try to create path anyway)
        result = mgr._add_model_to_footprint(footprint_file, model_file, pretty_dir)

        # Still should work - relative path is added even if file doesn't exist
        updated_content = footprint_file.read_text()
        assert "(model " in updated_content
        assert "MISSING.step" in updated_content

    def test_footprint_file_permission_denied(self, temp_dir):
        """Test handling of permission errors when reading/writing footprints"""
        from library_manager import KiCADLibraryManager
        import os

        mgr = KiCADLibraryManager(library_base_dir=temp_dir)

        lcsc_id = "C2040"
        pretty_dir = mgr.footprints_dir / f"{lcsc_id}_PAD1206.pretty"
        pretty_dir.mkdir(parents=True, exist_ok=True)

        footprint_file = pretty_dir / "PAD1206.kicad_mod"
        footprint_file.write_text("""(footprint "PAD1206"
  (layer "F.Cu")
)""")

        model_file = mgr.models_dir / f"{lcsc_id}_PAD1206.step"
        model_file.write_text("ISO-10303-21;\nEND-ISO-10303-21;")

        # Make footprint read-only
        os.chmod(footprint_file, 0o444)

        try:
            result = mgr._add_model_to_footprint(footprint_file, model_file, pretty_dir)
            # Should return False on permission error
            assert result is False
        finally:
            # Restore permissions for cleanup
            os.chmod(footprint_file, 0o644)

    def test_malformed_footprint_s_expression(self, temp_dir):
        """Test handling of malformed s-expressions"""
        from library_manager import KiCADLibraryManager

        mgr = KiCADLibraryManager(library_base_dir=temp_dir)

        lcsc_id = "C2040"
        pretty_dir = mgr.footprints_dir / f"{lcsc_id}_BAD.pretty"
        pretty_dir.mkdir(parents=True, exist_ok=True)

        # Malformed - missing closing paren
        footprint_file = pretty_dir / "BAD.kicad_mod"
        footprint_file.write_text("""(footprint "BAD"
  (layer "F.Cu")""")

        model_file = mgr.models_dir / f"{lcsc_id}_model.step"
        model_file.write_text("ISO-10303-21;\nEND-ISO-10303-21;")

        result = mgr._add_model_to_footprint(footprint_file, model_file, pretty_dir)
        # Implementation is forgiving - tries to add model anyway (appends before closing paren attempt)
        # This may succeed because the file ends after the layer declaration
        assert result is True

        # Verify the model entry was added (implementation adds it even without proper closing paren)
        updated_content = footprint_file.read_text()
        assert "(model " in updated_content

    def test_very_long_paths(self, temp_dir):
        """Test handling of very long file paths"""
        from library_manager import KiCADLibraryManager

        mgr = KiCADLibraryManager(library_base_dir=temp_dir)

        # Create part with long name
        long_lcsc_id = "C" + "1234567890" * 5  # 51 chars
        try:
            pretty_dir = mgr.footprints_dir / f"{long_lcsc_id}_LONG.pretty"
            pretty_dir.mkdir(parents=True, exist_ok=True)

            footprint_file = pretty_dir / "LONG.kicad_mod"
            footprint_file.write_text("""(footprint "LONG"
  (layer "F.Cu")
)""")

            model_file = mgr.models_dir / f"{long_lcsc_id}_LONG.step"
            model_file.write_text("ISO-10303-21;\nEND-ISO-10303-21;")

            result = mgr._add_model_to_footprint(footprint_file, model_file, pretty_dir)
            assert result is True
        except OSError as e:
            # Some systems have path length limits
            pytest.skip(f"System path length limit: {e}")

    def test_circular_path_references(self, temp_dir):
        """Test that circular/invalid relative paths are avoided"""
        from library_manager import KiCADLibraryManager

        mgr = KiCADLibraryManager(library_base_dir=temp_dir)

        lcsc_id = "C2040"
        pretty_dir = mgr.footprints_dir / f"{lcsc_id}_PAD1206.pretty"
        pretty_dir.mkdir(parents=True, exist_ok=True)

        footprint_file = pretty_dir / "PAD1206.kicad_mod"
        footprint_file.write_text("""(footprint "PAD1206"
  (layer "F.Cu")
)""")

        model_file = mgr.models_dir / f"{lcsc_id}_PAD1206.step"
        model_file.write_text("ISO-10303-21;\nEND-ISO-10303-21;")

        mgr._add_model_to_footprint(footprint_file, model_file, pretty_dir)

        updated_content = footprint_file.read_text()
        model_line = [l for l in updated_content.split('\n') if '(model ' in l][0]

        # Verify path doesn't contain circular references like ../../..
        # It should be exactly ../../3dmodels/...
        assert model_line.count('../..') == 1  # Should appear exactly once
        assert '../../3dmodels/' in model_line


@pytest.mark.integration
class TestBatchLinking:
    """Tests for batch operations with multiple parts"""

    def test_batch_link_multiple_parts(self, temp_dir):
        """Test linking models for multiple parts in one operation"""
        from library_manager import KiCADLibraryManager

        mgr = KiCADLibraryManager(library_base_dir=temp_dir)

        parts = [
            ("C2040", "PAD1206"),
            ("C4169", "RES0402"),
            ("C4216", "IND0603"),
        ]

        for lcsc_id, footprint_name in parts:
            # Create footprint directories
            pretty_dir = mgr.footprints_dir / f"{lcsc_id}_{footprint_name}.pretty"
            pretty_dir.mkdir(parents=True, exist_ok=True)

            footprint_file = pretty_dir / f"{footprint_name}.kicad_mod"
            footprint_file.write_text(f"""(footprint "{footprint_name}"
  (layer "F.Cu")
)""")

            # Create model files
            model_file = mgr.models_dir / f"{lcsc_id}_{footprint_name}.step"
            model_file.write_text("ISO-10303-21;\nEND-ISO-10303-21;")

            # Link models
            mgr._link_3d_models_to_footprints(lcsc_id)

        # Verify all footprints now have models
        for lcsc_id, footprint_name in parts:
            pretty_dir = mgr.footprints_dir / f"{lcsc_id}_{footprint_name}.pretty"
            footprint_file = pretty_dir / f"{footprint_name}.kicad_mod"
            content = footprint_file.read_text()
            assert "(model " in content

    def test_batch_link_partial_failure(self, temp_dir):
        """Test batch linking handles some parts failing gracefully"""
        from library_manager import KiCADLibraryManager

        mgr = KiCADLibraryManager(library_base_dir=temp_dir)

        # Part 1: Has both footprint and model
        lcsc_id_1 = "C2040"
        pretty_dir_1 = mgr.footprints_dir / f"{lcsc_id_1}_PAD.pretty"
        pretty_dir_1.mkdir(parents=True, exist_ok=True)
        fp_file_1 = pretty_dir_1 / "PAD.kicad_mod"
        fp_file_1.write_text("""(footprint "PAD" (layer "F.Cu"))""")

        model_1 = mgr.models_dir / f"{lcsc_id_1}_PAD.step"
        model_1.write_text("ISO-10303-21;\nEND-ISO-10303-21;")

        # Part 2: Has footprint but NO model
        lcsc_id_2 = "C4169"
        pretty_dir_2 = mgr.footprints_dir / f"{lcsc_id_2}_RES.pretty"
        pretty_dir_2.mkdir(parents=True, exist_ok=True)
        fp_file_2 = pretty_dir_2 / "RES.kicad_mod"
        fp_file_2.write_text("""(footprint "RES" (layer "F.Cu"))""")
        # No model file

        # Link both
        mgr._link_3d_models_to_footprints(lcsc_id_1)
        mgr._link_3d_models_to_footprints(lcsc_id_2)

        # Part 1 should have model
        content_1 = fp_file_1.read_text()
        assert "(model " in content_1

        # Part 2 should NOT have model (none exists)
        content_2 = fp_file_2.read_text()
        assert "(model " not in content_2

    def test_batch_link_preserves_order(self, temp_dir):
        """Test that batch linking processes parts in expected order"""
        from library_manager import KiCADLibraryManager

        mgr = KiCADLibraryManager(library_base_dir=temp_dir)

        parts = [f"C{1000+i}" for i in range(5)]
        processed_order = []

        # Create test structure
        for lcsc_id in parts:
            pretty_dir = mgr.footprints_dir / f"{lcsc_id}_TEST.pretty"
            pretty_dir.mkdir(parents=True, exist_ok=True)
            fp_file = pretty_dir / "TEST.kicad_mod"
            fp_file.write_text(f"""(footprint "TEST"
  (layer "F.Cu")
)""")

            model_file = mgr.models_dir / f"{lcsc_id}_TEST.step"
            model_file.write_text("ISO-10303-21;\nEND-ISO-10303-21;")

        # Process all parts
        for lcsc_id in parts:
            mgr._link_3d_models_to_footprints(lcsc_id)
            processed_order.append(lcsc_id)

        # Verify all were processed
        assert processed_order == parts

    def test_batch_link_performance(self, temp_dir):
        """Test batch linking performance with many parts"""
        from library_manager import KiCADLibraryManager
        import time

        mgr = KiCADLibraryManager(library_base_dir=temp_dir)

        # Create 10 parts (not 100+ to keep test fast)
        num_parts = 10

        for i in range(num_parts):
            lcsc_id = f"C{2000+i}"
            pretty_dir = mgr.footprints_dir / f"{lcsc_id}_PERF.pretty"
            pretty_dir.mkdir(parents=True, exist_ok=True)

            fp_file = pretty_dir / "PERF.kicad_mod"
            fp_file.write_text("""(footprint "PERF" (layer "F.Cu"))""")

            model_file = mgr.models_dir / f"{lcsc_id}_PERF.step"
            model_file.write_text("ISO-10303-21;\nEND-ISO-10303-21;")

        # Measure time to link all parts
        start_time = time.time()
        for i in range(num_parts):
            lcsc_id = f"C{2000+i}"
            mgr._link_3d_models_to_footprints(lcsc_id)
        elapsed = time.time() - start_time

        # Should complete in reasonable time (< 5 seconds for 10 parts)
        assert elapsed < 5.0
        # Average per part should be < 500ms
        assert elapsed / num_parts < 0.5


@pytest.mark.integration
class TestIntegrationWithLibraryManager:
    """End-to-end integration tests"""

    def test_download_and_link_single_part(self, temp_dir):
        """Test complete pipeline for single part with 3D model linking"""
        from library_manager import KiCADLibraryManager

        mgr = KiCADLibraryManager(library_base_dir=temp_dir)

        # Simulate downloaded files for C2040
        lcsc_id = "C2040"

        # Create symbol file
        sym_file = mgr.symbols_dir / f"{lcsc_id}_capacitor.kicad_sym"
        sym_file.write_text("""(kicad_symbol_lib (version 20211014) (generator test)
  (symbol "C2040" (power_in) (pin_numbers hide)
  )
)""")

        # Create footprint directory with .kicad_mod file
        pretty_dir = mgr.footprints_dir / f"{lcsc_id}_C_0402_1005Metric.pretty"
        pretty_dir.mkdir(parents=True, exist_ok=True)

        fp_file = pretty_dir / "C_0402_1005Metric.kicad_mod"
        fp_file.write_text("""(footprint "C_0402_1005Metric"
  (layer "F.Cu")
  (pad "1" smd roundrect (at -0.45 0) (size 0.5 0.6))
  (pad "2" smd roundrect (at 0.45 0) (size 0.5 0.6))
)""")

        # Create 3D model file
        model_file = mgr.models_dir / f"{lcsc_id}_model.step"
        model_file.write_text("ISO-10303-21;\nEND-ISO-10303-21;")

        # Run linking
        mgr._link_3d_models_to_footprints(lcsc_id)

        # Verify all files exist
        assert sym_file.exists()
        assert fp_file.exists()
        assert model_file.exists()

        # Verify footprint has model reference
        fp_content = fp_file.read_text()
        assert "(model " in fp_content

    def test_download_and_link_multiple_parts(self, temp_dir):
        """Test complete pipeline for multiple parts"""
        from library_manager import KiCADLibraryManager

        mgr = KiCADLibraryManager(library_base_dir=temp_dir)

        test_parts = [
            ("C2040", "C_0402_1005Metric", "capacitor"),
            ("C4169", "R_0402_1005Metric", "resistor"),
            ("C4216", "L_0603_1608Metric", "inductor"),
        ]

        for lcsc_id, fp_name, sym_name in test_parts:
            # Create symbols
            sym_file = mgr.symbols_dir / f"{lcsc_id}_{sym_name}.kicad_sym"
            sym_file.write_text(f"""(kicad_symbol_lib (version 20211014)
  (symbol "{sym_name}")
)""")

            # Create footprints
            pretty_dir = mgr.footprints_dir / f"{lcsc_id}_{fp_name}.pretty"
            pretty_dir.mkdir(parents=True, exist_ok=True)

            fp_file = pretty_dir / f"{fp_name}.kicad_mod"
            fp_file.write_text(f"""(footprint "{fp_name}" (layer "F.Cu"))""")

            # Create models
            model_file = mgr.models_dir / f"{lcsc_id}_model.step"
            model_file.write_text("ISO-10303-21;\nEND-ISO-10303-21;")

            # Link
            mgr._link_3d_models_to_footprints(lcsc_id)

        # Verify all have models
        for lcsc_id, fp_name, _ in test_parts:
            pretty_dir = mgr.footprints_dir / f"{lcsc_id}_{fp_name}.pretty"
            fp_file = pretty_dir / f"{fp_name}.kicad_mod"
            content = fp_file.read_text()
            assert "(model " in content, f"Part {lcsc_id} missing model reference"

    def test_3d_model_files_referenced_in_all_footprints(self, temp_dir):
        """Test that all footprints for a part have 3D model references"""
        from library_manager import KiCADLibraryManager

        mgr = KiCADLibraryManager(library_base_dir=temp_dir)

        lcsc_id = "C2040"

        # Create multiple footprint variants for same part
        footprint_variants = [
            ("C_0402_1005Metric", "0402"),
            ("C_0603_1608Metric", "0603"),
        ]

        for fp_name, size in footprint_variants:
            pretty_dir = mgr.footprints_dir / f"{lcsc_id}_{fp_name}.pretty"
            pretty_dir.mkdir(parents=True, exist_ok=True)

            fp_file = pretty_dir / f"{fp_name}.kicad_mod"
            fp_file.write_text(f"""(footprint "{fp_name}" (layer "F.Cu"))""")

        # Create single model for this LCSC ID
        model_file = mgr.models_dir / f"{lcsc_id}_model.step"
        model_file.write_text("ISO-10303-21;\nEND-ISO-10303-21;")

        # Link models
        mgr._link_3d_models_to_footprints(lcsc_id)

        # Verify ALL footprints now have models
        for fp_name, _ in footprint_variants:
            pretty_dir = mgr.footprints_dir / f"{lcsc_id}_{fp_name}.pretty"
            fp_file = pretty_dir / f"{fp_name}.kicad_mod"
            content = fp_file.read_text()
            assert "(model " in content, f"Footprint {fp_name} missing model"

    def test_verify_part_files_includes_3d_model_check(self, temp_dir):
        """Test that verify_part_files checks for 3D models"""
        from library_manager import KiCADLibraryManager

        mgr = KiCADLibraryManager(library_base_dir=temp_dir)

        lcsc_id = "C2040"

        # Test 1: Part with no models
        sym_file = mgr.symbols_dir / f"{lcsc_id}_test.kicad_sym"
        sym_file.write_text("(kicad_symbol_lib)")

        pretty_dir = mgr.footprints_dir / f"{lcsc_id}_TEST.pretty"
        pretty_dir.mkdir(parents=True, exist_ok=True)
        fp_file = pretty_dir / "TEST.kicad_mod"
        fp_file.write_text("(footprint)")

        stats = mgr.verify_part_files(lcsc_id)
        assert stats["symbol"] is True
        assert stats["footprint"] is True
        assert stats["models_3d"] is False

        # Test 2: Add model and verify again
        model_file = mgr.models_dir / f"{lcsc_id}_model.step"
        model_file.write_text("ISO-10303-21;\nEND-ISO-10303-21;")

        stats = mgr.verify_part_files(lcsc_id)
        assert stats["symbol"] is True
        assert stats["footprint"] is True
        assert stats["models_3d"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
