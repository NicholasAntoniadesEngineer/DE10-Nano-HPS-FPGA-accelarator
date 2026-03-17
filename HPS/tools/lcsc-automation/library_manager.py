"""
KiCAD library management.
Download and organize symbols, footprints, and 3D models from easyeda2kicad.
"""

import logging
import subprocess
import json
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import get_config
from utils import safe_filename, check_command_available, human_filesize

logger = logging.getLogger(__name__)


@dataclass
class LibraryPart:
    """Represents a part in the KiCAD library"""
    lcsc_id: str
    name: str
    symbol_file: Optional[Path] = None
    footprint_file: Optional[Path] = None
    model_3d_file: Optional[Path] = None
    metadata: Dict[str, Any] = None


class KiCADLibraryManager:
    """Manage KiCAD library organization and generation"""

    def __init__(self, library_base_dir: Optional[Path] = None):
        self.cfg = get_config()
        self.library_dir = library_base_dir or self.cfg.kicad.library_dir
        self.library_dir.mkdir(parents=True, exist_ok=True)

        # Library subdirectories
        self.symbols_dir = self.library_dir / "symbols"
        self.footprints_dir = self.library_dir / "footprints"
        self.models_dir = self.library_dir / "3dmodels"

        # Create subdirectories
        for d in [self.symbols_dir, self.footprints_dir, self.models_dir]:
            d.mkdir(parents=True, exist_ok=True)

        self.parts = {}

    def check_easyeda2kicad(self) -> bool:
        """Check if easyeda2kicad is installed"""
        if not check_command_available("easyeda2kicad"):
            logger.error("easyeda2kicad not found. Install with: pip install easyeda2kicad")
            return False
        return True

    def download_part_library(self, lcsc_id: str, download_symbols: bool = True,
                             download_footprints: bool = True,
                             download_3d: bool = True) -> bool:
        """Download symbols, footprints, and 3D models for a single part"""
        if not self.check_easyeda2kicad():
            return False

        lcsc_id = lcsc_id.upper()
        logger.info(f"Downloading library files for {lcsc_id}...")

        try:
            # Build easyeda2kicad command
            cmd = ["easyeda2kicad", "--full", f"--lcsc_id={lcsc_id}"]

            # Specify output directory
            output_dir = self.library_dir / "temp_parts" / lcsc_id
            output_dir.mkdir(parents=True, exist_ok=True)
            cmd.extend(["--output", str(output_dir)])
            cmd.append("--overwrite")

            # Run download
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                logger.warning(f"easyeda2kicad failed for {lcsc_id}: {result.stderr}")
                return False

            # Organize downloaded files
            self._organize_downloaded_files(lcsc_id, output_dir)

            logger.info(f"Successfully downloaded {lcsc_id}")
            return True

        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout downloading {lcsc_id}")
            return False
        except Exception as e:
            logger.error(f"Failed to download {lcsc_id}: {e}")
            return False

    def _organize_downloaded_files(self, lcsc_id: str, source_dir: Path):
        """Organize downloaded files into library structure"""
        try:
            # Move symbol files
            symbol_files = list(source_dir.glob("*.kicad_sym"))
            for sym_file in symbol_files:
                dest = self.symbols_dir / f"{lcsc_id}_{sym_file.name}"
                shutil.move(str(sym_file), str(dest))
                logger.debug(f"Moved symbol: {dest}")

            # Move footprint files
            fp_pretty_dirs = list(source_dir.glob("*.pretty"))
            for fp_dir in fp_pretty_dirs:
                dest = self.footprints_dir / f"{lcsc_id}_{fp_dir.name}"
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.move(str(fp_dir), str(dest))
                logger.debug(f"Moved footprints: {dest}")

            # Move 3D model files
            model_extensions = [".step", ".stp", ".wrl"]
            for ext in model_extensions:
                model_files = list(source_dir.glob(f"*{ext}"))
                for model_file in model_files:
                    dest = self.models_dir / f"{lcsc_id}_{model_file.name}"
                    shutil.move(str(model_file), str(dest))
                    logger.debug(f"Moved 3D model: {dest}")

            # Link 3D models to footprints
            self._link_3d_models_to_footprints(lcsc_id)

            # Cleanup temp directory
            if source_dir.exists():
                shutil.rmtree(source_dir)

        except Exception as e:
            logger.error(f"Failed to organize files for {lcsc_id}: {e}")

    def _link_3d_models_to_footprints(self, lcsc_id: str):
        """Link 3D models to footprints by inserting (model ...) s-expressions

        Scans for 3D model files matching the lcsc_id and adds (model ...) entries
        to corresponding footprint files if not already present.
        Prefers STEP files over VRML files if both exist.
        """
        try:
            # Find all 3D model files for this part (prefer .step over .wrl)
            model_files = {}  # Maps model base name to Path

            for ext in [".step", ".stp", ".wrl"]:
                for model_path in self.models_dir.glob(f"{lcsc_id}_*{ext}"):
                    # Extract base filename (e.g., "C2040_file" from "C2040_file.step")
                    base_name = model_path.stem

                    # Only add if we haven't already found a STEP/STP version
                    if base_name not in model_files or ext in [".step", ".stp"]:
                        model_files[base_name] = model_path

            if not model_files:
                logger.debug(f"No 3D models found for {lcsc_id}")
                return

            # Find all footprint .pretty directories for this part
            fp_pretty_dirs = list(self.footprints_dir.glob(f"{lcsc_id}_*.pretty"))

            if not fp_pretty_dirs:
                logger.debug(f"No footprints found for {lcsc_id}")
                return

            # Process each footprint directory
            for pretty_dir in fp_pretty_dirs:
                # Find all .kicad_mod files in this footprint directory
                kicad_mod_files = list(pretty_dir.glob("*.kicad_mod"))

                for kicad_mod_path in kicad_mod_files:
                    # Try to link the first available 3D model
                    # (In most cases there will be one model file per LCSC ID)
                    for base_name, model_path in model_files.items():
                        self._add_model_to_footprint(kicad_mod_path, model_path, pretty_dir)
                        # Link first model to this footprint, then move to next footprint
                        break

        except Exception as e:
            logger.error(f"Failed to link 3D models for {lcsc_id}: {e}")

    def _add_model_to_footprint(self, footprint_path: Path, model_path: Path,
                                footprint_dir: Path) -> bool:
        """Add (model ...) s-expression to a footprint file if not already present

        Args:
            footprint_path: Path to .kicad_mod file
            model_path: Path to 3D model file (.step, .stp, or .wrl)
            footprint_dir: Parent .pretty directory (for relative path calculation)

        Returns:
            True if model was added or already exists, False on error
        """
        try:
            # Read footprint file
            with open(footprint_path, 'r') as f:
                content = f.read()

            # Check if (model ...) entry already exists
            if "(model " in content:
                logger.debug(f"Footprint {footprint_path.name} already has model reference")
                return True

            # Calculate relative path from footprint location to model
            # Footprint is at: footprints/C2040_PAD1206.pretty/PAD1206.kicad_mod
            # Model is at: 3dmodels/C2040_file.step
            # Relative path: ../../3dmodels/C2040_file.step

            rel_path = Path("..") / ".." / "3dmodels" / model_path.name
            rel_path_str = str(rel_path).replace("\\", "/")  # Normalize to forward slashes

            # Create model s-expression
            # KiCAD model format: (model "relative/path/to/model.step" (offset ...) (scale ...) (rotate ...))
            model_entry = f'\n  (model "{rel_path_str}"\n    (offset (xyz 0 0 0))\n    (scale (xyz 1 1 1))\n    (rotate (xyz 0 0 0)))'

            # Insert model entry before the closing parenthesis
            # Find the last closing paren (end of footprint)
            if content.rstrip().endswith(")"):
                new_content = content.rstrip()[:-1] + model_entry + "\n)"

                # Write back to file
                with open(footprint_path, 'w') as f:
                    f.write(new_content)

                logger.info(f"Added 3D model to {footprint_path.name}: {model_path.name}")
                return True
            else:
                logger.warning(f"Unexpected footprint format in {footprint_path.name}")
                return False

        except Exception as e:
            logger.error(f"Failed to add model to {footprint_path.name}: {e}")
            return False

    def batch_download_parts(self, lcsc_ids: List[str], max_workers: int = 4) -> Dict[str, bool]:
        """Download libraries for multiple parts in parallel"""
        results = {}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.download_part_library, lcsc_id): lcsc_id
                for lcsc_id in lcsc_ids
            }

            for future in as_completed(futures):
                lcsc_id = futures[future]
                try:
                    results[lcsc_id] = future.result()
                except Exception as e:
                    logger.error(f"Error downloading {lcsc_id}: {e}")
                    results[lcsc_id] = False

        return results

    def generate_symbol_library(self, output_file: Optional[Path] = None) -> Path:
        """Generate consolidated KiCAD symbol library"""
        output_file = output_file or (self.symbols_dir / "lcsc_parts.kicad_sym")

        logger.info(f"Generating symbol library: {output_file}")

        # Consolidate all symbol files
        consolidated = self._consolidate_symbol_files()

        try:
            with open(output_file, 'w') as f:
                f.write(consolidated)
            logger.info(f"Wrote symbol library: {output_file}")
            return output_file
        except Exception as e:
            logger.error(f"Failed to write symbol library: {e}")
            return None

    def _consolidate_symbol_files(self) -> str:
        """Consolidate multiple .kicad_sym files into one"""
        header = "(kicad_symbol_lib (version 20211014) (generator easyeda2kicad)\n"
        footer = ")\n"

        symbols = []

        # Read all symbol files
        for sym_file in self.symbols_dir.glob("*.kicad_sym"):
            try:
                with open(sym_file, 'r') as f:
                    content = f.read()

                # Extract symbol definitions (between outer parens)
                # Simple extraction - assumes well-formed s-expression
                if content.startswith("(kicad_symbol_lib"):
                    # Remove header and footer, keep inner symbols
                    inner = content.split("(symbol", 1)[1]  # Remove header
                    symbol_defs = "(symbol" + inner.rsplit(")", 1)[0]  # Remove footer
                    symbols.append(symbol_defs)
                    logger.debug(f"Extracted symbols from {sym_file.name}")

            except Exception as e:
                logger.warning(f"Failed to read {sym_file}: {e}")

        # Consolidate
        consolidated = header
        for symbol_def in symbols:
            consolidated += symbol_def + "\n"
        consolidated += footer

        return consolidated

    def generate_footprint_library_table(self, output_file: Optional[Path] = None) -> Path:
        """Generate KiCAD footprint library table (fp-lib-table)"""
        output_file = output_file or (self.library_dir / "fp-lib-table")

        logger.info(f"Generating footprint library table: {output_file}")

        # Create fp-lib-table entry for each footprint library
        entries = []
        entries.append('(fp_lib_table')

        # Find all .pretty directories
        for pretty_dir in self.footprints_dir.glob("*.pretty"):
            lib_name = pretty_dir.name.replace('.pretty', '')
            rel_path = pretty_dir.relative_to(self.library_dir)
            entry = f'  (lib (name "{lib_name}") (type "KiCad") (uri "${{{rel_path}}}") (options "") (descr ""))'
            entries.append(entry)

        entries.append(')')

        try:
            with open(output_file, 'w') as f:
                f.write('\n'.join(entries))
            logger.info(f"Wrote fp-lib-table: {output_file}")
            return output_file
        except Exception as e:
            logger.error(f"Failed to write fp-lib-table: {e}")
            return None

    def get_library_statistics(self) -> Dict[str, Any]:
        """Get library statistics"""
        symbols = list(self.symbols_dir.glob("*.kicad_sym"))
        footprints = list(self.footprints_dir.glob("*.pretty"))
        models = list(self.models_dir.glob("*.*"))

        total_symbols_size = sum(f.stat().st_size for f in symbols)
        total_models_size = sum(f.stat().st_size for f in models)

        return {
            "symbol_files": len(symbols),
            "footprint_libraries": len(footprints),
            "3d_model_files": len(models),
            "symbols_size": human_filesize(total_symbols_size),
            "models_size": human_filesize(total_models_size),
            "library_dir": str(self.library_dir)
        }

    def verify_part_files(self, lcsc_id: str) -> Dict[str, bool]:
        """Verify that all files exist for a part"""
        lcsc_id = lcsc_id.upper()

        # Check for symbol
        symbol_exists = any(self.symbols_dir.glob(f"{lcsc_id}_*.kicad_sym"))

        # Check for footprint
        footprint_exists = any(self.footprints_dir.glob(f"{lcsc_id}_*.pretty"))

        # Check for 3D models
        models_exist = any(self.models_dir.glob(f"{lcsc_id}_*.*"))

        return {
            "symbol": symbol_exists,
            "footprint": footprint_exists,
            "models_3d": models_exist,
            "complete": symbol_exists and footprint_exists
        }

    def cleanup_library(self, remove_temp: bool = True):
        """Cleanup temporary files and unused libraries"""
        if remove_temp:
            temp_dir = self.library_dir / "temp_parts"
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temp directory: {temp_dir}")

        logger.info("Library cleanup complete")

    def print_statistics(self):
        """Print library statistics"""
        stats = self.get_library_statistics()
        print("\n=== KiCAD Library Statistics ===")
        print(f"Symbol files: {stats['symbol_files']}")
        print(f"Footprint libraries: {stats['footprint_libraries']}")
        print(f"3D models: {stats['3d_model_files']}")
        print(f"Symbols size: {stats['symbols_size']}")
        print(f"Models size: {stats['models_size']}")
        print(f"Library directory: {stats['library_dir']}")


if __name__ == "__main__":
    # Test library manager
    lib_mgr = KiCADLibraryManager()

    if not lib_mgr.check_easyeda2kicad():
        print("easyeda2kicad not available - install with: pip install easyeda2kicad")
    else:
        # Test single part download
        print("Testing library manager...")
        success = lib_mgr.download_part_library("C2040")
        if success:
            print("✓ Successfully downloaded C2040")
            stats = lib_mgr.verify_part_files("C2040")
            print(f"  Symbols: {stats['symbol']}")
            print(f"  Footprints: {stats['footprint']}")
            print(f"  3D Models: {stats['models_3d']}")

        # Print statistics
        lib_mgr.print_statistics()
