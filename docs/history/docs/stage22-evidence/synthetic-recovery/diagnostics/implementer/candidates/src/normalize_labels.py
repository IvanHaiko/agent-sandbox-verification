"""Normalize comma-separated labels with quoting and escaping."""


_ASCII_WHITESPACE = {" ", "\t", "\r", "\n", "\v", "\f"}


def _lower_ascii(character: str) -> str:
    if "A" <= character <= "Z":
        return chr(ord(character) + (ord("a") - ord("A")))
    return character


def _normalize_label(characters: list[tuple[str, bool]]) -> str:
    """Normalize a parsed label; the boolean marks protected characters."""
    start = 0
    end = len(characters)

    while start < end:
        character, protected = characters[start]
        if protected or character not in _ASCII_WHITESPACE:
            break
        start += 1
    while end > start:
        character, protected = characters[end - 1]
        if protected or character not in _ASCII_WHITESPACE:
            break
        end -= 1

    result: list[str] = []
    index = start
    while index < end:
        character, protected = characters[index]
        if not protected and character in _ASCII_WHITESPACE:
            result.append(" ")
            index += 1
            while index < end:
                next_character, next_protected = characters[index]
                if next_protected or next_character not in _ASCII_WHITESPACE:
                    break
                index += 1
            continue
        result.append(_lower_ascii(character))
        index += 1
    return "".join(result)


def normalize_labels(value: str) -> list[str]:
    """Parse and normalize an ASCII comma-separated label string."""
    labels: list[str] = []
    current: list[tuple[str, bool]] = []
    quoted = False
    index = 0

    while index < len(value):
        character = value[index]
        if character == "\\":
            index += 1
            if index >= len(value):
                raise ValueError("trailing escape")
            current.append((value[index], True))
        elif character == '"':
            quoted = not quoted
        elif character == "," and not quoted:
            labels.append(_normalize_label(current))
            current = []
        else:
            current.append((character, quoted))
        index += 1

    if quoted:
        raise ValueError("unclosed quote")
    labels.append(_normalize_label(current))

    unique: list[str] = []
    seen: set[str] = set()
    for label in labels:
        if label and label not in seen:
            seen.add(label)
            unique.append(label)
    return unique
