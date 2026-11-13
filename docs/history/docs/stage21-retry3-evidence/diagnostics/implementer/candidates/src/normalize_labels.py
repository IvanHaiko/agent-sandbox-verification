_ASCII_WHITESPACE = " \t\r\n\v\f"


def _ascii_lower(character: str) -> str:
    if "A" <= character <= "Z":
        return chr(ord(character) + (ord("a") - ord("A")))
    return character


def _normalize_label(characters: list[tuple[str, bool]]) -> str:
    """Normalize one parsed label.

    The boolean attached to each character identifies ordinary (unquoted and
    unescaped) ASCII whitespace.  Keeping that provenance allows protected
    whitespace to remain exact and to interrupt collapsible whitespace runs.
    """
    start = 0
    end = len(characters)
    while start < end and characters[start][1]:
        start += 1
    while end > start and characters[end - 1][1]:
        end -= 1

    result: list[str] = []
    ordinary_whitespace_pending = False
    for character, is_ordinary_whitespace in characters[start:end]:
        if is_ordinary_whitespace:
            ordinary_whitespace_pending = True
            continue
        if ordinary_whitespace_pending:
            result.append(" ")
            ordinary_whitespace_pending = False
        result.append(_ascii_lower(character))
    return "".join(result)


def normalize_labels(value: str) -> list[str]:
    """Parse, normalize, and stably deduplicate a comma-separated label list."""
    labels: list[str] = []
    seen: set[str] = set()
    current: list[tuple[str, bool]] = []
    quoted = False
    index = 0

    def finish_label() -> None:
        normalized = _normalize_label(current)
        if normalized and normalized not in seen:
            seen.add(normalized)
            labels.append(normalized)
        current.clear()

    while index < len(value):
        character = value[index]

        if character == "\\":
            index += 1
            if index == len(value):
                raise ValueError("trailing escape")
            current.append((value[index], False))
        elif character == '"':
            quoted = not quoted
        elif character == "," and not quoted:
            finish_label()
        else:
            is_ordinary_whitespace = (
                not quoted and character in _ASCII_WHITESPACE
            )
            current.append((character, is_ordinary_whitespace))
        index += 1

    if quoted:
        raise ValueError("unclosed quote")

    finish_label()
    return labels
