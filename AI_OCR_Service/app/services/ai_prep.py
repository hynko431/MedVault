def prepare_text_for_ai(clean_text: str) -> str:
    """
    Prepare OCR-cleaned text for LLM consumption.
    DO NOT interpret.
    DO NOT expand abbreviations.
    """
    lines = clean_text.split("\n")

    prepared_lines = []
    buffer = []

    for line in lines:
        if line.strip() == "":
            if buffer:
                prepared_lines.append("\n".join(buffer))
                buffer = []
        else:
            buffer.append(line)

    if buffer:
        prepared_lines.append("\n".join(buffer))

    # Separate logical blocks with double newline
    return "\n\n".join(prepared_lines)
