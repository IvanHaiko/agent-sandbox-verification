def slugify(value: str) -> str:
    """Return a lowercase, hyphen-separated slug for an ASCII string."""
    slug: list[str] = []

    for character in value:
        if "A" <= character <= "Z":
            slug.append(character.lower())
        elif "a" <= character <= "z" or "0" <= character <= "9":
            slug.append(character)
        elif character == "-" or character.isspace():
            if slug and slug[-1] != "-":
                slug.append("-")

    if slug and slug[-1] == "-":
        slug.pop()

    return "".join(slug)
