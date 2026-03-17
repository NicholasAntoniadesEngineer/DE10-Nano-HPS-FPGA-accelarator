"""
KiCAD s-expression parsing and footprint modification utilities.
Handles reading, parsing, and modifying KiCAD footprint files (.kicad_mod)
with support for 3D model linking and formatting preservation.
"""

import logging
import re
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Token:
    """Represents a single token in s-expression with position info"""
    value: str
    position: int
    line: int
    column: int

    def __repr__(self) -> str:
        return f"Token({self.value!r}, pos={self.position}, line={self.line})"


class SExpressionTokenizer:
    """
    Tokenizes KiCAD s-expression format.
    Handles quoted strings, numbers, symbols, parentheses, and preserves
    formatting information (lines, columns) for intelligent re-serialization.
    """

    def __init__(self):
        """Initialize tokenizer"""
        self.tokens: List[Token] = []
        self.position = 0
        self.line = 1
        self.column = 0

    def tokenize(self, content: str) -> List[Token]:
        """
        Parse KiCAD s-expression content into tokens.

        Args:
            content: Raw s-expression string

        Returns:
            List of Token objects with position information

        Raises:
            ValueError: If unterminated string or unmatched parentheses
        """
        self.tokens = []
        self.position = 0
        self.line = 1
        self.column = 0

        i = 0
        while i < len(content):
            char = content[i]

            # Track line and column
            if char == '\n':
                self.line += 1
                self.column = 0
            else:
                self.column += 1

            # Skip whitespace (preserve info but don't tokenize)
            if char.isspace():
                i += 1
                continue

            # Quoted string
            if char == '"':
                token_start = i
                i += 1
                string_content = char
                while i < len(content) and content[i] != '"':
                    if content[i] == '\\' and i + 1 < len(content):
                        string_content += content[i:i+2]
                        i += 2
                    else:
                        string_content += content[i]
                        i += 1

                if i >= len(content):
                    raise ValueError(f"Unterminated string at line {self.line}")

                string_content += '"'
                token = Token(string_content, token_start, self.line, self.column)
                self.tokens.append(token)
                self.column += len(string_content)
                i += 1
                continue

            # Parentheses
            if char in '()':
                token = Token(char, i, self.line, self.column)
                self.tokens.append(token)
                i += 1
                continue

            # Symbol or number
            token_start = i
            token_content = ""
            while i < len(content) and not content[i].isspace() and content[i] not in '()':
                if content[i] == '"':
                    break
                token_content += content[i]
                i += 1

            if token_content:
                token = Token(token_content, token_start, self.line, self.column)
                self.tokens.append(token)
                self.column += len(token_content)

        return self.tokens


class SExpressionParser:
    """
    Parses tokenized s-expressions into a nested tree structure.
    Supports finding specific elements and querying the tree.
    """

    def __init__(self):
        """Initialize parser"""
        self.tokens: List[Token] = []
        self.index = 0

    def parse(self, tokens: List[Token]) -> Optional[List[Any]]:
        """
        Convert tokens to nested structure.

        Args:
            tokens: List of Token objects from tokenizer

        Returns:
            Root list of parsed s-expression, or None if empty

        Raises:
            ValueError: If mismatched parentheses
        """
        self.tokens = tokens
        self.index = 0

        if not tokens:
            return None

        result, _ = self._parse_expr()
        return result

    def _parse_expr(self) -> Tuple[Optional[Any], int]:
        """Parse single s-expression element"""
        if self.index >= len(self.tokens):
            return None, self.index

        token = self.tokens[self.index]

        if token.value == '(':
            # Parse list
            self.index += 1
            result = []
            while self.index < len(self.tokens) and self.tokens[self.index].value != ')':
                item, _ = self._parse_expr()
                if item is not None:
                    result.append(item)

            if self.index >= len(self.tokens):
                raise ValueError("Unmatched opening parenthesis")

            self.index += 1  # Skip closing )
            return result, self.index

        elif token.value == ')':
            # Unexpected closing paren
            return None, self.index

        else:
            # Atom (string, number, symbol)
            value = token.value
            # Remove quotes from strings
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            self.index += 1
            return value, self.index

    def find_elements(self, tree: List[Any], element_name: str) -> List[List[Any]]:
        """
        Find all elements with given name in the tree.

        Args:
            tree: Parsed s-expression tree
            element_name: Name of element to find (e.g., "pad", "model")

        Returns:
            List of matching elements
        """
        results = []

        def search(node: Any):
            if isinstance(node, list):
                if len(node) > 0 and node[0] == element_name:
                    results.append(node)
                for item in node:
                    search(item)

        search(tree)
        return results

    def find_element_at_index(self, tree: List[Any], element_name: str,
                              index: int = 0) -> Optional[List[Any]]:
        """
        Find single element by name and return it along with parent.

        Args:
            tree: Parsed s-expression tree
            element_name: Name of element to find
            index: Which occurrence to return (0-indexed)

        Returns:
            The element list, or None if not found
        """
        matches = self.find_elements(tree, element_name)
        if index < len(matches):
            return matches[index]
        return None

    def has_element(self, tree: List[Any], element_name: str) -> bool:
        """
        Check if tree contains element with given name.

        Args:
            tree: Parsed s-expression tree
            element_name: Name to search for

        Returns:
            True if element exists
        """
        return len(self.find_elements(tree, element_name)) > 0


class KiCADFootprintModifier:
    """
    Modifies KiCAD footprint files (.kicad_mod) to add 3D model references.
    Preserves file structure and formatting where possible.
    """

    # Indentation matching KiCAD style (tabs)
    DEFAULT_INDENT = "\t"

    def __init__(self, filepath: Path):
        """
        Initialize modifier with footprint file path.

        Args:
            filepath: Path to .kicad_mod footprint file
        """
        self.filepath = Path(filepath)
        self.content = ""
        self.tokens: List[Token] = []
        self.tree: Optional[List[Any]] = None

    def read_file(self) -> bool:
        """
        Read footprint file.

        Returns:
            True if successful, False otherwise
        """
        if not self.filepath.exists():
            logger.error(f"Footprint file not found: {self.filepath}")
            return False

        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                self.content = f.read()
            logger.debug(f"Read footprint file: {self.filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to read footprint file {self.filepath}: {e}")
            return False

    def parse(self) -> bool:
        """
        Parse footprint file content.

        Returns:
            True if successful, False otherwise
        """
        if not self.content:
            logger.error("No content to parse. Call read_file() first.")
            return False

        try:
            tokenizer = SExpressionTokenizer()
            self.tokens = tokenizer.tokenize(self.content)

            parser = SExpressionParser()
            self.tree = parser.parse(self.tokens)

            logger.debug(f"Parsed {len(self.tokens)} tokens")
            return True
        except Exception as e:
            logger.error(f"Failed to parse footprint: {e}")
            return False

    def has_model_reference(self) -> bool:
        """
        Check if footprint already contains (model ...) entry.

        Returns:
            True if model reference exists
        """
        if not self.tree:
            logger.warning("Tree not parsed. Call parse() first.")
            return False

        parser = SExpressionParser()
        return parser.has_element(self.tree, "model")

    def add_model_reference(self, model_path: str, relative: bool = True) -> bool:
        """
        Add (model ...) entry to footprint.

        Args:
            model_path: Path to 3D model file
            relative: If True, wrap path with ${KIPRJMOD}/

        Returns:
            True if successful, False otherwise

        Raises:
            RuntimeError: If tree not parsed or model already exists
        """
        if not self.tree:
            logger.error("Tree not parsed. Call parse() first.")
            return False

        if self.has_model_reference():
            logger.warning(f"Footprint already has model reference")
            return False

        try:
            # Build model entry
            model_entry = self._build_model_entry(model_path, relative)

            # Find insertion point (after last pad element)
            insertion_point = self._find_model_insertion_point()

            # Insert model entry
            if insertion_point is not None:
                self.tree.insert(insertion_point, model_entry)
                logger.info(f"Added model reference: {model_path}")
                return True
            else:
                logger.error("Could not find insertion point for model entry")
                return False

        except Exception as e:
            logger.error(f"Failed to add model reference: {e}")
            return False

    def write_file(self, output_path: Optional[Path] = None) -> bool:
        """
        Write modified footprint back to file.

        Args:
            output_path: Optional output path. If None, overwrites original.

        Returns:
            True if successful, False otherwise
        """
        if not self.tree:
            logger.error("No parsed tree to write. Call parse() first.")
            return False

        try:
            output_file = output_path or self.filepath
            # Root element needs special handling
            formatted_content = self._serialize_root(self.tree)

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(formatted_content)

            logger.info(f"Wrote footprint file: {output_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to write footprint file: {e}")
            return False

    def _serialize_root(self, tree: List[Any]) -> str:
        """
        Serialize root footprint element with opening paren.
        """
        if not tree or len(tree) == 0:
            return ""

        lines = []
        # Root element is always: (footprint "name" ...)
        lines.append("(")
        lines.append(self._serialize_tree(tree, 1))
        lines.append(")")

        return "\n".join(lines)

    def _find_model_insertion_point(self) -> Optional[int]:
        """
        Find where to insert (model ...) entry in tree.
        Inserts after the last (pad ...) element, before the closing paren.

        Returns:
            Index for insertion, or None if no suitable location found
        """
        if not self.tree or not isinstance(self.tree, list):
            return None

        # Find last pad element index
        last_pad_index = -1
        for i, item in enumerate(self.tree):
            if isinstance(item, list) and len(item) > 0 and item[0] == "pad":
                last_pad_index = i

        if last_pad_index >= 0:
            return last_pad_index + 1

        # If no pads, insert before closing paren (near end)
        return len(self.tree) - 1 if self.tree else 0

    def _build_model_entry(self, model_path: str, relative: bool = True) -> List[Any]:
        """
        Build (model ...) s-expression entry.

        Args:
            model_path: Path to 3D model
            relative: If True, wrap with ${KIPRJMOD}/

        Returns:
            Model entry as nested list
        """
        # Format path with project-relative prefix if requested
        if relative:
            # Normalize path separators for KiCAD (forward slashes)
            normalized_path = model_path.replace('\\', '/')
            if not normalized_path.startswith("${KIPRJMOD}/"):
                formatted_path = f"${{KIPRJMOD}}/{normalized_path}"
            else:
                formatted_path = normalized_path
        else:
            formatted_path = model_path.replace('\\', '/')

        # Build model entry structure
        model_entry = [
            "model",
            formatted_path,
            ["at", ["xyz", "0", "0", "0"]],
            ["scale", ["xyz", "1", "1", "1"]],
            ["rotate", ["xyz", "0", "0", "0"]]
        ]

        return model_entry

    def _serialize_tree(self, tree: List[Any], indent: int = 0) -> str:
        """
        Serialize parsed tree back to formatted s-expression.
        Uses compact single-line format for small elements, indentation for larger ones.

        Args:
            tree: Parsed s-expression tree
            indent: Current indentation level

        Returns:
            Formatted s-expression string
        """
        if not tree:
            return ""

        lines = []
        indent_str = self.DEFAULT_INDENT * indent

        for item in tree:
            if isinstance(item, list):
                # Check if this is a small inline element
                if self._is_inline_element(item):
                    # Render on single line
                    inline = self._serialize_inline(item)
                    lines.append(f"{indent_str}{inline}")
                else:
                    # Multi-line element
                    lines.append(f"{indent_str}(")
                    inner = self._serialize_tree(item, indent + 1)
                    lines.append(inner)
                    lines.append(f"{indent_str})")

            elif isinstance(item, str):
                lines.append(f"{indent_str}{item}")
            else:
                lines.append(f"{indent_str}{item}")

        return "\n".join(lines)

    def _is_inline_element(self, item: List[Any]) -> bool:
        """
        Determine if element should be rendered inline.
        Small elements like (xyz 0 0 0) are inline.
        """
        if not isinstance(item, list) or len(item) == 0:
            return False

        # Always expand top-level elements
        if len(item) > 5:
            return False

        # Special keyword elements that should be expanded
        expand_keywords = {"pad", "model", "fp_text", "footprint"}
        if item[0] in expand_keywords:
            return False

        # Inline for small utility elements
        inline_keywords = {"xyz", "at", "size", "scale", "rotate"}
        if item[0] in inline_keywords:
            return True

        return False

    def _serialize_inline(self, item: List[Any]) -> str:
        """
        Serialize element to single line.
        """
        parts = []
        for element in item:
            if isinstance(element, list):
                parts.append(f"({self._serialize_inline(element)})")
            else:
                parts.append(str(element))
        return " ".join(parts)


# Helper functions

def has_model_reference(footprint_content: str) -> bool:
    """
    Check if KiCAD footprint content contains (model ...) entry.

    Args:
        footprint_content: Raw footprint file content

    Returns:
        True if model reference exists
    """
    try:
        tokenizer = SExpressionTokenizer()
        tokens = tokenizer.tokenize(footprint_content)

        parser = SExpressionParser()
        tree = parser.parse(tokens)

        return parser.has_element(tree, "model") if tree else False
    except Exception as e:
        logger.debug(f"Error checking model reference: {e}")
        return False


def get_model_insertion_point(tokens: List[Token]) -> Optional[int]:
    """
    Find insertion point for (model ...) in token stream.
    Returns index after last pad token.

    Args:
        tokens: List of tokens from tokenizer

    Returns:
        Token index for insertion, or None if not found
    """
    last_pad_index = -1

    for i, token in enumerate(tokens):
        if token.value == "pad":
            # Find matching closing paren for this pad
            depth = 0
            for j in range(i - 1, -1, -1):
                if tokens[j].value == ")":
                    depth += 1
                elif tokens[j].value == "(":
                    depth -= 1
                    if depth == 0:
                        last_pad_index = j
                        break

    if last_pad_index >= 0:
        # Find the matching closing paren for the pad
        depth = 1
        for i in range(last_pad_index + 1, len(tokens)):
            if tokens[i].value == "(":
                depth += 1
            elif tokens[i].value == ")":
                depth -= 1
                if depth == 0:
                    return i + 1

    return None


def format_model_entry(model_path: str, relative: bool = True) -> str:
    """
    Format a (model ...) s-expression entry.

    Args:
        model_path: Path to 3D model file
        relative: If True, wrap with ${KIPRJMOD}/

    Returns:
        Formatted s-expression string
    """
    # Normalize path
    normalized_path = model_path.replace('\\', '/')

    if relative:
        if not normalized_path.startswith("${KIPRJMOD}/"):
            formatted_path = f"${{KIPRJMOD}}/{normalized_path}"
        else:
            formatted_path = normalized_path
    else:
        formatted_path = normalized_path

    # Build formatted entry with proper indentation
    entry = (
        '\t(model "{path}"\n'
        '\t\t(at (xyz 0 0 0))\n'
        '\t\t(scale (xyz 1 1 1))\n'
        '\t\t(rotate (xyz 0 0 0))\n'
        '\t)'
    ).format(path=formatted_path)

    return entry


if __name__ == "__main__":
    # Example usage
    print("KiCAD s-expression parser module")
    print("\nExample: Tokenizing simple s-expression")
    tokenizer = SExpressionTokenizer()
    tokens = tokenizer.tokenize('(footprint "Test" (pad "1" smd circle))')
    print(f"Tokens: {tokens}")

    print("\nExample: Parsing tokens")
    parser = SExpressionParser()
    tree = parser.parse(tokens)
    print(f"Tree: {tree}")

    print("\nExample: Finding elements")
    if tree:
        pads = parser.find_elements(tree, "pad")
        print(f"Found {len(pads)} pad(s)")
