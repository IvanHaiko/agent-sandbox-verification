def normalize_labels(value: str) -> list[str]:
    labels: list[str] = []
    seen: set[str] = set()
    characters: list[str] = []
    quoted = False
    escaped = False
    pending_space = False

    def finish_label() -> None:
        label = "".join(characters)
        if label and label not in seen:
            seen.add(label)
            labels.append(label)
        characters.clear()

    for character in value:
        protected = quoted
        if escaped:
            protected = True
            escaped = False
        elif character == "\\":
            escaped = True
            continue
        elif character == '"':
            quoted = not quoted
            continue
        elif character == "," and not quoted:
            finish_label()
            pending_space = False
            continue

        if not protected and character in " \t\r\n\v\f":
            if characters:
                pending_space = True
            continue

        if pending_space:
            characters.append(" ")
            pending_space = False
        if "A" <= character <= "Z":
            character = chr(ord(character) + 32)
        characters.append(character)

    if escaped:
        raise ValueError("Trailing unpaired backslash")
    if quoted:
        raise ValueError("Unclosed double quote")
    finish_label()
    return labels
