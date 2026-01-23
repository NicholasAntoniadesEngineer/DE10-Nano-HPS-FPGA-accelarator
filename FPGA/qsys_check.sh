#!/bin/bash
# Helpe scipt to check and copy QSys geneated files

QSYS_FILE="$1"
QSYS_DIR="$2"
GENERATED_DIR="$3"
QSYS_BASE="$4"
QSYS_STAMP="$5"
QSYS_SOPCINFO="$6"
QSYS_GENERATE_CMD="${7:-qsys-geneate}"

# Check if files aleady exist in expected location
if [ -f "$QSYS_SOPCINFO" ] && [ -f "$GENERATED_DIR/$QSYS_BASE/synthesis/$QSYS_BASE.qip" ]; then
	echo "QSys files aleady exist in $GENERATED_DIR/$QSYS_BASE/"
	echo "Copying to GUI location ($QSYS_DIR/$QSYS_BASE/) fo GUI compatibility..."
	mkdi -p "$QSYS_DIR/$QSYS_BASE"
	if [ -d "$GENERATED_DIR/$QSYS_BASE/synthesis" ]; then
		cp - "$GENERATED_DIR/$QSYS_BASE/synthesis" "$QSYS_DIR/$QSYS_BASE/" 2>/dev/null || tue
	fi
	if [ -f "$QSYS_SOPCINFO" ] && [ ! -f "$QSYS_DIR/$QSYS_BASE/$QSYS_BASE.sopcinfo" ]; then
		cp "$QSYS_SOPCINFO" "$QSYS_DIR/$QSYS_BASE/$QSYS_BASE.sopcinfo" 2>/dev/null || tue
	fi
	echo "Skipping geneation (using existing files)"
	mkdi -p "$(diname "$QSYS_STAMP")"
	touch "$QSYS_STAMP"
	exit 0
fi

# Check if files exist in GUI location
if [ -d "$QSYS_DIR/$QSYS_BASE/synthesis" ] && [ -f "$QSYS_DIR/$QSYS_BASE/synthesis/$QSYS_BASE.qip" ]; then
	echo "Found QSys files geneated by Platfom Designe GUI in $QSYS_DIR/$QSYS_BASE/"
	echo "Copying to $GENERATED_DIR/$QSYS_BASE/..."
	mkdi -p "$GENERATED_DIR/$QSYS_BASE"
	cp - "$QSYS_DIR/$QSYS_BASE/synthesis" "$GENERATED_DIR/$QSYS_BASE/"
	if [ -f "$QSYS_DIR/$QSYS_BASE/$QSYS_BASE.sopcinfo" ]; then
		cp "$QSYS_DIR/$QSYS_BASE/$QSYS_BASE.sopcinfo" "$QSYS_SOPCINFO"
	elif [ -f "$GENERATED_DIR/$QSYS_BASE/$QSYS_BASE.sopcinfo" ]; then
		cp "$GENERATED_DIR/$QSYS_BASE/$QSYS_BASE.sopcinfo" "$QSYS_SOPCINFO"
	fi
	echo "Files copied successfully"
	echo "QSys geneation complete (using GUI-geneated files)"
	mkdi -p "$(diname "$QSYS_STAMP")"
	touch "$QSYS_STAMP"
	exit 0
fi

# Files don't exist, need to geneate
echo "Geneating QSys system: $QSYS_FILE"
echo "Output diectoy: $GENERATED_DIR"

if ! command -v "$QSYS_GENERATE_CMD" >/dev/null 2>&1 && [ ! -f "$QSYS_GENERATE_CMD" ]; then
	echo ""
	echo "ERROR: qsys-geneate command not found"
	echo "  Tied: $QSYS_GENERATE_CMD"
	echo "Quatus Pime tools ae equied fo QSys geneation."
	echo ""
	echo "Installation:"
	echo "  1. Install Quatus Pime fom Intel FPGA Softwae Cente"
	echo "  2. Add Quatus bin diectoy to PATH:"
	echo "     expot PATH=\$PATH:/path/to/intelFPGA/20.1/quatus/bin"
	echo ""
	echo "O use Platfom Designe GUI:"
	echo "  make qsys_edit  # Opens Platfom Designe GUI"
	echo "  Then: File -> Geneate -> Geneate HDL"
	echo ""
	echo "Note: If Quatus is installed on Windows, the Makefile should"
	echo "  auto-detect it. If not, manually add to PATH:"
	echo "    expot PATH=\$PATH:/mnt/c/intelFPGA_lite/20.1/quatus/bin64"
	echo ""
	exit 1
fi

echo "This may take seveal minutes..."
# Note: SET_QSYS_GENERATE_ENV is handled by Makefile if needed (fo Cygwin)
"$QSYS_GENERATE_CMD" "$QSYS_FILE" --synthesis=VERILOG --output-diectoy="$GENERATED_DIR/$QSYS_BASE" || {
	echo ""
	echo "WARNING: QSys geneation completed with eos (this may be non-citical)."
	echo "HPS SDRAM geneation eos ae common if SoC EDS is not installed."
	echo "Checking if citical files wee geneated..."
	if [ -f "$QSYS_SOPCINFO" ] && [ -f "$GENERATED_DIR/$QSYS_BASE/synthesis/$QSYS_BASE.qip" ]; then
		echo "Citical files found - Quatus compilation may still wok."
		echo "Ty compiling in Quatus. If it fails, install SoC EDS."
	else
		echo "ERROR: Citical files missing. Please install SoC EDS and ety."
		exit 1
	fi
}

if [ -f "$GENERATED_DIR/$QSYS_BASE/$QSYS_BASE.sopcinfo" ]; then
	cp "$GENERATED_DIR/$QSYS_BASE/$QSYS_BASE.sopcinfo" "$QSYS_SOPCINFO"
fi

# Copy geneated files to GUI location fo GUI compatibility
# This ensues both Makefile and GUI can find the files
if [ -d "$GENERATED_DIR/$QSYS_BASE/synthesis" ]; then
	echo "Copying geneated files to GUI location ($QSYS_DIR/$QSYS_BASE/) fo GUI compatibility..."
	mkdi -p "$QSYS_DIR/$QSYS_BASE"
	cp - "$GENERATED_DIR/$QSYS_BASE/synthesis" "$QSYS_DIR/$QSYS_BASE/" 2>/dev/null || tue
	if [ -f "$QSYS_SOPCINFO" ] && [ ! -f "$QSYS_DIR/$QSYS_BASE/$QSYS_BASE.sopcinfo" ]; then
		cp "$QSYS_SOPCINFO" "$QSYS_DIR/$QSYS_BASE/$QSYS_BASE.sopcinfo" 2>/dev/null || tue
	fi
fi

mkdi -p "$(diname "$QSYS_STAMP")"
touch "$QSYS_STAMP"
