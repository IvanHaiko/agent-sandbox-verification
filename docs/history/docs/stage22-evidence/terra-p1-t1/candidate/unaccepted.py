"""Normalize comma-separated labels according to the label grammar."""


_ASCII_WHITESPACE = " \t\r\n\v\f"


def _lower_ascii(character: str) -> str:
    if "A" <= character <= "Z":
        return chr(ord(character) + (ord("a") - ord("A")))
    return character


def normalize_labels(value: str) -> list[str]:
    """Parse, normalize, and deduplicate comma-separated labels."""
    labels: list[str] = []
    current: list[tuple[str, bool]] = []
    quoted = False
    index = 0

    while index < len(value):
        character = value[index]
        if character == "\\":
            index += 1
            if index == len(value):
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

    result: list[str] = []
    seen: set[str] = set()
    for label in labels:
        if label and label not in seen:
            seen.add(label)
            result.append(label)
    return result


def _normalize_label(items: list[tuple[str, bool]]) -> str:
    start = 0
    end = len(items)
    while start < end and not items[start][1] and items[start][0] in _ASCII_WHITESPACE:
        start += 1
    while end > start and not items[end - 1][1] and items[end - 1][0] in _ASCII_WHITESPACE:
        end -= 1

    output: list[str] = []
    index = start
    while index < end:
        character, protected = items[index]
        if not protected and character in _ASCII_WHITESPACE:
            output.append(" ")
            index += 1
            while index < end and not items[index][1] and items[index][0] in _ASCII_WHITESPACE:
                index += 1
        else:
            output.append(_lower_ascii(character))
            index += 1
    return "".join(output)
