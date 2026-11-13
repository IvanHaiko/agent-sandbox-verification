"""Normalize comma-separated labels with quoting and escaping."""


_ASCII_WHITESPACE = " \t\r\n\v\f"


def _lower_ascii(char: str) -> str:
    if "A" <= char <= "Z":
        return chr(ord(char) + (ord("a") - ord("A")))
    return char


def _normalize_label(parts: list[tuple[str, bool]]) -> str:
    """Trim and collapse only unprotected whitespace."""
    result: list[str] = []
    index = 0
    length = len(parts)

    while index < length:
        char, protected = parts[index]
        if not protected and char in _ASCII_WHITESPACE:
            end = index + 1
            while (
                end < length
                and not parts[end][1]
                and parts[end][0] in _ASCII_WHITESPACE
            ):
                end += 1
            if result and end < length:
                result.append(" ")
            index = end
            continue
        result.append(_lower_ascii(char))
        index += 1

    return "".join(result)


def normalize_labels(value: str) -> list[str]:
    """Parse, normalize, and deduplicate comma-separated labels."""
    labels: list[str] = []
    current: list[tuple[str, bool]] = []
    quoted = False
    index = 0

    while index < len(value):
        char = value[index]
        if char == "\\":
            if index + 1 >= len(value):
                raise ValueError("trailing escape")
            current.append((value[index + 1], True))
            index += 2
        elif char == '"':
            quoted = not quoted
            index += 1
        elif char == "," and not quoted:
            labels.append(_normalize_label(current))
            current = []
            index += 1
        else:
            current.append((char, quoted))
            index += 1

    if quoted:
        raise ValueError("unclosed quote")
    labels.append(_normalize_label(current))

    result: list[str] = []
    seen: set[str] = set()
    for label in labels:
        if label and label not in seen:
            seen.add(label)
            result.append(label)
    return result
