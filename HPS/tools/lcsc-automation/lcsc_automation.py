#!/usr/bin/env python3
"""
LCSC Automation Framework - Command-line interface
Complete BOM generation, component validation, and KiCAD library management.
"""

import sys
import json
import logging
from pathlib import Path
from typing import List, Dict, Any
import argparse

# Ensure local imports work
sys.path.insert(0, str(Path(__file__).parent))

from config import get_config, Config
from lcsc_fetcher import LCSCFetcher
from kicad_parser import KiCADParser
from bom_generator import BOMMFromSchematic
from library_manager import KiCADLibraryManager
from validator import ComponentValidator, DFMChecker
from utils import write_csv, natural_sort_key

__version__ = "1.0.0"


class LCSCAutomationCLI:
    """Command-line interface for LCSC automation"""

    def __init__(self):
        self.cfg = get_config()
        self.logger = self.cfg.logger
        self.fetcher = LCSCFetcher()
        self.parser = KiCADParser()
        self.validator = ComponentValidator()
        self.lib_manager = KiCADLibraryManager()

    def validate_parts(self, component_file: Path) -> bool:
        """Validate all parts in component definition file"""
        if not component_file.exists():
            self.logger.error(f"File not found: {component_file}")
            return False

        self.logger.info(f"Validating parts in {component_file}...")

        try:
            # This is a simple validation - in real use, would parse Python file
            # For now, just check file exists
            with open(component_file, 'r') as f:
                content = f.read()

            # Find LCSC codes
            import re
            lcsc_codes = re.findall(r'\bC\d{1,7}\b', content)
            if not lcsc_codes:
                self.logger.warning(f"No LCSC codes found in {component_file}")
                return True

            self.logger.info(f"Found {len(lcsc_codes)} LCSC codes")

            # Verify each part
            results = self.fetcher.verify_parts_list(lcsc_codes)

            found = sum(1 for p in results.values() if p)
            missing = len(results) - found

            print(f"\n=== Validation Results ===")
            print(f"Total parts: {len(results)}")
            print(f"Found: {found}")
            print(f"Missing: {missing}")

            if missing > 0:
                print(f"\nMissing parts:")
                for lcsc_id, part in results.items():
                    if not part:
                        print(f"  {lcsc_id}")

            return missing == 0

        except Exception as e:
            self.logger.error(f"Validation failed: {e}")
            return False

    def generate_bom(self, schematic_file: Path, output_dir: Path = None) -> bool:
        """Generate BOM and CPL from schematic"""
        if not schematic_file.exists():
            self.logger.error(f"Schematic not found: {schematic_file}")
            return False

        output_dir = output_dir or schematic_file.parent

        try:
            self.logger.info(f"Generating BOM from {schematic_file}...")

            # Parse schematic
            bom_gen = BOMMFromSchematic(schematic_file)

            # Validate
            if not bom_gen.validate():
                self.logger.warning("Schematic validation found issues")

            # Generate files
            results = bom_gen.generate_all(output_dir)

            # Print summary
            bom_gen.generator.print_summary()

            print(f"\nGenerated files:")
            print(f"  BOM: {results['bom']}")
            print(f"  CPL: {results['cpl']}")

            return True

        except Exception as e:
            self.logger.error(f"BOM generation failed: {e}")
            return False

    def download_library(self, bom_file: Path, max_workers: int = 4) -> bool:
        """Download KiCAD library files for parts in BOM"""
        if not bom_file.exists():
            self.logger.error(f"BOM file not found: {bom_file}")
            return False

        try:
            self.logger.info(f"Downloading library for {bom_file}...")

            # Parse BOM CSV
            from utils import parse_csv
            bom_data = parse_csv(bom_file)

            # Extract LCSC IDs
            lcsc_ids = []
            for row in bom_data:
                lcsc_id = row.get("LCSC Part #", "").strip()
                if lcsc_id:
                    lcsc_ids.append(lcsc_id)

            if not lcsc_ids:
                self.logger.error("No LCSC IDs found in BOM")
                return False

            self.logger.info(f"Found {len(lcsc_ids)} unique parts to download")

            # Batch download
            results = self.lib_manager.batch_download_parts(lcsc_ids, max_workers)

            # Print results
            successful = sum(1 for v in results.values() if v)
            print(f"\n=== Download Results ===")
            print(f"Successful: {successful}/{len(results)}")

            if successful < len(results):
                print(f"\nFailed parts:")
                for lcsc_id, success in results.items():
                    if not success:
                        print(f"  {lcsc_id}")

            # Print statistics
            self.lib_manager.print_statistics()

            return successful == len(results)

        except Exception as e:
            self.logger.error(f"Library download failed: {e}")
            return False

    def validate_stock(self, bom_file: Path) -> bool:
        """Validate stock availability for BOM"""
        if not bom_file.exists():
            self.logger.error(f"BOM file not found: {bom_file}")
            return False

        try:
            from utils import parse_csv
            bom_data = parse_csv(bom_file)

            self.logger.info(f"Validating stock for {len(bom_data)} parts...")

            result = self.validator.validate_bom_stock(bom_data)

            print(f"\n=== Stock Validation ===")
            print(f"Parts checked: {result['parts_checked']}")
            print(f"Valid: {result['valid']}")

            if result['issues']:
                print(f"\nIssues ({len(result['issues'])}):")
                for issue in result['issues']:
                    print(f"  {issue}")
            else:
                print("✓ All parts in stock!")

            print(f"\nStock breakdown:")
            for category, count in result['parts_by_stock'].items():
                print(f"  {category}: {count}")

            return result['valid']

        except Exception as e:
            self.logger.error(f"Stock validation failed: {e}")
            return False

    def full_refresh(self, schematic_file: Path, output_dir: Path = None) -> bool:
        """Complete refresh: validate → generate BOM/CPL → download library"""
        if not schematic_file.exists():
            self.logger.error(f"Schematic not found: {schematic_file}")
            return False

        output_dir = output_dir or schematic_file.parent

        print("=== Full Refresh ===")
        print("Step 1: Generating BOM/CPL...")
        if not self.generate_bom(schematic_file, output_dir):
            return False

        print("\nStep 2: Validating stock...")
        bom_file = output_dir / f"{schematic_file.stem}_BOM.csv"
        if not self.validate_stock(bom_file):
            self.logger.warning("Some parts have stock issues")

        print("\nStep 3: Downloading KiCAD library...")
        if not self.download_library(bom_file):
            self.logger.warning("Some library downloads failed")

        print("\n✓ Full refresh complete!")
        return True

    def print_config(self):
        """Print current configuration"""
        print("\n=== Configuration ===")
        import json
        print(json.dumps(self.cfg.to_dict(), indent=2))

    def print_dfm_limits(self):
        """Print DFM design rules"""
        DFMChecker.print_dfm_limits()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="LCSC Automation Framework - BOM generation and component sourcing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate parts in component definition
  lcsc_automation.py --validate drone_components.py

  # Generate BOM/CPL from schematic
  lcsc_automation.py --generate-bom daughter_board.kicad_sch

  # Download KiCAD library for parts
  lcsc_automation.py --download-library daughter_board_BOM.csv

  # Validate stock availability
  lcsc_automation.py --validate-stock daughter_board_BOM.csv

  # Complete refresh: BOM → validate → download
  lcsc_automation.py --full-refresh daughter_board.kicad_sch

  # Print configuration
  lcsc_automation.py --config

  # Print DFM design rules
  lcsc_automation.py --dfm-limits
        """
    )

    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    # Main operations
    group = parser.add_argument_group("Operations")
    group.add_argument("--validate", type=Path, metavar="FILE",
                      help="Validate all LCSC parts in component file")
    group.add_argument("--generate-bom", type=Path, metavar="FILE",
                      help="Generate BOM/CPL from KiCAD schematic")
    group.add_argument("--download-library", type=Path, metavar="FILE",
                      help="Download KiCAD library for BOM parts")
    group.add_argument("--validate-stock", type=Path, metavar="FILE",
                      help="Check stock availability for BOM parts")
    group.add_argument("--full-refresh", type=Path, metavar="FILE",
                      help="Complete refresh: BOM → validate → download")

    # Utility options
    group = parser.add_argument_group("Utilities")
    group.add_argument("--config", action="store_true",
                      help="Print current configuration")
    group.add_argument("--dfm-limits", action="store_true",
                      help="Print DFM design rules")

    # Options
    parser.add_argument("-o", "--output", type=Path, metavar="DIR",
                       help="Output directory (default: input file directory)")
    parser.add_argument("-w", "--workers", type=int, default=4, metavar="N",
                       help="Number of parallel workers for downloads (default: 4)")
    parser.add_argument("-v", "--verbose", action="store_true",
                       help="Verbose logging")

    args = parser.parse_args()

    # Setup logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create CLI instance
    cli = LCSCAutomationCLI()

    try:
        # Execute commands
        if args.validate:
            success = cli.validate_parts(args.validate)
            sys.exit(0 if success else 1)

        elif args.generate_bom:
            success = cli.generate_bom(args.generate_bom, args.output)
            sys.exit(0 if success else 1)

        elif args.download_library:
            success = cli.download_library(args.download_library, args.workers)
            sys.exit(0 if success else 1)

        elif args.validate_stock:
            success = cli.validate_stock(args.validate_stock)
            sys.exit(0 if success else 1)

        elif args.full_refresh:
            success = cli.full_refresh(args.full_refresh, args.output)
            sys.exit(0 if success else 1)

        elif args.config:
            cli.print_config()

        elif args.dfm_limits:
            cli.print_dfm_limits()

        else:
            parser.print_help()

    except Exception as e:
        cli.logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
