"""
text_utils.py
~~~~~~~~~~~~~
Provides auxiliary text manipulation routines, including word-wrapping
and dynamic string truncation to manage interface spacing rules safely.
"""


def wrap_text(text, font, max_width):
    """Wrap text to fit within max_width. Returns list of lines."""
    words = str(text).split(" ")
    lines, current_line = [], []

    for word in words:
        test_line = " ".join(current_line + [word])
        if font.size(test_line)[0] <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]

    if current_line:
        lines.append(" ".join(current_line))
    return lines


def truncate_text(text, font, max_width, max_lines=4):
    """Truncates text to a maximum number of lines, appending an ellipsis."""
    lines = wrap_text(text, font, max_width)
    if len(lines) <= max_lines:
        return text, len(lines)

    kept_lines = lines[:max_lines]
    words_in_last = kept_lines[-1].split(" ")

    while words_in_last:
        if font.size(" ".join(words_in_last) + "...")[0] <= max_width:
            break
        words_in_last.pop()

    if not words_in_last:
        kept_lines[-1] = "..."
    else:
        kept_lines[-1] = " ".join(words_in_last) + "..."

    return " ".join(kept_lines), max_lines
