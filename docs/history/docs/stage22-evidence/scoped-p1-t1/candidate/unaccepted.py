"""Parsing and normalization of comma-separated labels."""


_ASCII_WHITESPACE = " \t\r\n\v\f"


def _normalize(parts: list[tuple[str, bool]]) -> str:
    """Normalize a parsed label, retaining protection information as needed."""
    start = 0
    end = len(parts)
    while start < end and not parts[start][1] and parts[start][0] in _ASCII_WHITESPACE:
        start += 1
    while end > start and not parts[end - 1][1] and parts[end - 1][0] in _ASCII_WHITESPACE:
        end -= 1

    result: list[str] = []
    ordinary_space_pending = False
    for char, protected in parts[start:end]:
        if not protected and char in _ASCII_WHITESPACE:
            ordinary_space_pending = True
            continue
        if ordinary_space_pending:
            result.append(" ")
            ordinary_space_pending = False
        if "A" <= char <= "Z":
            char = char.lower()
        result.append(char)
    return "".join(result)


def normalize_labels(value: str) -> list[str]:
    """Parse, normalize, and deduplicate comma-separated labels."""
    labels: list[str] = []
    parts: list[tuple[str, bool]] = []
    quoted = False
    index = 0

    while index < len(value):
        char = value[index]
        if char == "\\":
            index += 1
            if index == len(value):
                raise ValueError("trailing unpaired backslash")
            parts.append((value[index], True))
        elif char == '"':
            quoted = not quoted
        elif char == "," and not quoted:
            labels.append(_normalize(parts))
            parts = []
        else:
            parts.append((char, quoted))
        index += 1

    if quoted:
        raise ValueError("unclosed double quote")
    labels.append(_normalize(parts))

    result: list[str] = []
    seen: set[str] = set()
    for label in labels:
        if label and label not in seen:
            seen.add(label)
            result.append(label)
    return result
