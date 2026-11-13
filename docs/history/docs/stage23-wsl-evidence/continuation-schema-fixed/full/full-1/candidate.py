def normalize_labels(value: str) -> list[str]:
    labels: list[str] = []
    seen: set[str] = set()
    characters: list[str] = []
    quoted = False
    escaped = False
    pending_whitespace = False
    whitespace = " \t\r\n\v\f"

    def finish_label() -> None:
        nonlocal pending_whitespace
        label = "".join(characters)
        if label and label not in seen:
            seen.add(label)
            labels.append(label)
        characters.clear()
        pending_whitespace = False

    for character in value:
        protected = quoted or escaped
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
            continue

        if character in whitespace and not protected:
            pending_whitespace = True
            continue

        if pending_whitespace:
            if characters:
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
