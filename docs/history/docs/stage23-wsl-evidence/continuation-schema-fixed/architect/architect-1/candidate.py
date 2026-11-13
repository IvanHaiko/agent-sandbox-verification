def normalize_labels(value: str) -> list[str]:
    labels: list[str] = []
    seen: set[str] = set()
    characters: list[str] = []
    quoted = False
    escaped = False
    pending_whitespace = False
    ascii_whitespace = " \t\r\n\v\f"

    def finish_label() -> None:
        label = "".join(characters)
        if label and label not in seen:
            seen.add(label)
            labels.append(label)
        characters.clear()

    for character in value:
        if escaped:
            escaped = False
        elif character == "\\":
            escaped = True
            continue
        elif character == '"':
            quoted = not quoted
            continue
        elif character == "," and not quoted:
            finish_label()
            pending_whitespace = False
            continue
        elif character in ascii_whitespace and not quoted:
            pending_whitespace = bool(characters)
            continue

        # Defer ordinary whitespace so boundary runs are discarded, while
        # each protected character is emitted exactly and ends any such run.
        if pending_whitespace:
            characters.append(" ")
            pending_whitespace = False
        if "A" <= character <= "Z":
            character = chr(ord(character) + 32)
        characters.append(character)

    if escaped:
        raise ValueError("Trailing unpaired backslash")
    if quoted:
        raise ValueError("Unclosed double quote")
    finish_label()
    return labels
