"""PostgreSQL statement boundaries, without parsing SQL grammar."""

import re


_DOLLAR_QUOTE = re.compile(r"\$(?:[A-Za-z_][A-Za-z_0-9]*)?\$")


def _identifier_char(char: str) -> bool:
    return char.isalnum() or char in "_$" or ord(char) >= 128


def _quoted_end(sql: str, start: int, quote: str, escapes: bool) -> int:
    index = start + 1
    while index < len(sql):
        if escapes and sql[index] == "\\":
            index += 2
        elif sql[index] == quote:
            if index + 1 < len(sql) and sql[index + 1] == quote:
                index += 2
            else:
                return index + 1
        else:
            index += 1
    kind = "string" if quote == "'" else "identifier"
    raise ValueError(f"Unterminated SQL {kind}")


def split_sql_statements(sql: str) -> list[str]:
    """Split outside quotes/comments, preserving text and discarding comments alone.

    Ordinary strings assume standard_conforming_strings=on. Escape strings,
    ASCII dollar tags and nested block comments follow PostgreSQL rules. The
    whole input is validated before the resulting list is returned.
    """
    statements = []
    start = index = 0
    has_code = False
    length = len(sql)

    while index < length:
        char = sql[index]
        if char.isspace():
            index += 1
        elif sql.startswith("--", index):
            index += 2
            while index < length and sql[index] not in "\r\n":
                index += 1
        elif sql.startswith("/*", index):
            depth = 1
            index += 2
            while index < length and depth:
                if sql.startswith("/*", index):
                    depth += 1
                    index += 2
                elif sql.startswith("*/", index):
                    depth -= 1
                    index += 2
                else:
                    index += 1
            if depth:
                raise ValueError("Unterminated SQL block comment")
        elif char == ";":
            if has_code:
                statements.append(sql[start:index].strip())
            index += 1
            start = index
            has_code = False
        else:
            has_code = True
            if (
                char in "Ee"
                and index + 1 < length
                and sql[index + 1] == "'"
                and (index == 0 or not _identifier_char(sql[index - 1]))
            ):
                index = _quoted_end(sql, index + 1, "'", escapes=True)
            elif char in "'\"":
                index = _quoted_end(sql, index, char, escapes=False)
            elif char == "$" and (match := _DOLLAR_QUOTE.match(sql, index)):
                delimiter = match.group()
                end = sql.find(delimiter, match.end())
                if end == -1:
                    raise ValueError("Unterminated SQL dollar quote")
                index = end + len(delimiter)
            elif char.isalpha() or char == "_" or ord(char) >= 128:
                # A dollar sequence within an unquoted identifier is just text.
                index += 1
                while index < length and _identifier_char(sql[index]):
                    index += 1
            else:
                index += 1

    if has_code:
        statements.append(sql[start:].strip())
    return statements
