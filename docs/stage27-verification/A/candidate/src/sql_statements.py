"""Statement boundaries for PostgreSQL migration files, not SQL grammar validation."""

import re


_DOLLAR_QUOTE = re.compile(r"\$(?:[A-Za-z_][A-Za-z_0-9]*)?\$")


def _identifier_character(char: str) -> bool:
    # PostgreSQL permits dollar signs and non-ASCII characters in identifiers.
    return char.isalnum() or char in "_$" or ord(char) >= 128


def _quoted_end(sql: str, start: int, quote: str, escapes: bool) -> int:
    """Return the position after the closing quote, respecting doubled quotes."""
    position = start + 1
    while position < len(sql):
        char = sql[position]
        if escapes and char == "\\":
            position += 2
        elif char == quote:
            if position + 1 < len(sql) and sql[position + 1] == quote:
                position += 2
            else:
                return position + 1
        else:
            position += 1
    region = "identifier" if quote == '"' else "string"
    raise ValueError(f"Unterminated SQL {region}")


def split_sql_statements(sql: str) -> list[str]:
    """Split outside quotes/comments, preserving each original statement's text.

    Strings use standard_conforming_strings=on unless prefixed with E/e.
    The whole input is validated before the resulting list is returned.
    """
    statements = []
    start = position = 0
    has_code = False
    identifier_text = False
    length = len(sql)

    while position < length:
        char = sql[position]
        if sql.startswith("--", position):
            identifier_text = False
            position += 2
            while position < length and sql[position] not in "\r\n":
                position += 1
        elif sql.startswith("/*", position):
            identifier_text = False
            depth = 1
            position += 2
            while position < length and depth:
                if sql.startswith("/*", position):
                    depth += 1
                    position += 2
                elif sql.startswith("*/", position):
                    depth -= 1
                    position += 2
                else:
                    position += 1
            if depth:
                raise ValueError("Unterminated SQL block comment")
        elif char in "'\"":
            has_code = True
            position = _quoted_end(sql, position, char, escapes=False)
            identifier_text = False
        elif (
            char in "Ee"
            and position + 1 < length
            and sql[position + 1] == "'"
            and not identifier_text
        ):
            has_code = True
            position = _quoted_end(sql, position + 1, "'", escapes=True)
            identifier_text = False
        elif (
            char == "$"
            and not identifier_text
            and (match := _DOLLAR_QUOTE.match(sql, position))
        ):
            has_code = True
            delimiter = match.group()
            end = sql.find(delimiter, match.end())
            if end == -1:
                raise ValueError("Unterminated SQL dollar quote")
            position = end + len(delimiter)
            identifier_text = False
        elif char == ";":
            if has_code:
                statements.append(sql[start:position].strip())
            position += 1
            start = position
            has_code = False
            identifier_text = False
        else:
            if not char.isspace():
                has_code = True
            identifier_text = _identifier_character(char)
            position += 1

    if has_code:
        statements.append(sql[start:].strip())
    return statements
