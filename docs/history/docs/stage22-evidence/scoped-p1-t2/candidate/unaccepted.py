"""Normalize comma-separated labels with quoting and escaping."""


_ASCII_WHITESPACE = " \t\r\n\v\f"


def _lower_ascii(character: str) -> str:
    code = ord(character)
    if 65 <= code <= 90:
        return chr(code + 32)
    return character


def _normalize_label(parts: list[tuple[str, bool]]) -> str:
    """Normalize a parsed label; the bool marks protected characters."""
    start = 0
    end = len(parts)
    while start < end and not parts[start][1] and parts[start][0] in _ASCII_WHITESPACE:
        start += 1
    while end > start and not parts[end - 1][1] and parts[end - 1][0] in _ASCII_WHITESPACE:
        end -= 1

    result: list[str] = []
    index = start
    while index < end:
        character, protected = parts[index]
        if not protected and character in _ASCII_WHITESPACE:
            while index < end:
                next_character, next_protected = parts[index]
                if next_protected or next_character not in _ASCII_WHITESPACE:
                    break
                index += 1
            result.append(" ")
            continue
        result.append(_lower_ascii(character))
        index += 1
    return "".join(result)


def normalize_labels(value: str) -> list[str]:
    """Parse and normalize an ASCII label string."""
    labels: list[str] = []
    current: list[tuple[str, bool]] = []
    quoted = False
    index = 0

    while index < len(value):
        character = value[index]
        if character == "\\":
            if index + 1 >= len(value):
                raise ValueError("trailing escape")
            current.append((value[index + 1], True))
            index += 2
            continue
        if character == '"':
            quoted = not quoted
            index += 1
            continue
        if character == "," and not quoted:
            normalized = _normalize_label(current)
            if normalized:
                labels.append(normalized)
            current = []
            index += 1
            continue
        current.append((character, quoted))
        index += 1

    if quoted:
        raise ValueError("unclosed quote")
    normalized = _normalize_label(current)
    if normalized:
        labels.append(normalized)

    unique: list[str] = []
    seen: set[str] = set()
    for label in labels:
        if label not in seen:
            seen.add(label)
            unique.append(label)
    return unique
