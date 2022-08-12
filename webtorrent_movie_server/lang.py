"""
Language codes.
"""

# pylint: disable=too-many-return-statements, too-many-branches


def lang_label(
    langname: str,
) -> str:
    """Returns a label for a given name."""
    if langname.startswith("en"):
        return "English"
    if langname.startswith("es"):
        return "Spanish"
    if langname.startswith("fr"):
        return "French"
    if langname.startswith("pt"):
        return "Portuguese"
    if langname.startswith("it"):
        return "Italian"
    if langname.startswith("de"):
        return "German"
    if langname.startswith("ru"):
        return "Russian"
    if langname.startswith("ja"):
        return "Japanese"
    if langname.startswith("zh"):
        return "Chinese"
    if langname.startswith("ko"):
        return "Korean"
    if langname.startswith("ar"):
        return "Arabic"
    if langname.startswith("tr"):
        return "Turkish"
    if langname.startswith("pl"):
        return "Polish"
    if langname.startswith("nl"):
        return "Dutch"
    if langname.startswith("el"):
        return "Greek"
    if langname.startswith("hi"):
        return "Hindi"
    if langname.startswith("th"):
        return "Thai"
    if langname.startswith("vi"):
        return "Vietnamese"
    if langname.startswith("id"):
        return "Indonesian"
    if langname.startswith("fa"):
        return "Persian"
    if langname.startswith("he"):
        return "Hebrew"
    if langname.startswith("sq"):
        return "Albanian"
    if langname.startswith("ro"):
        return "Romanian"
    if langname.startswith("sr"):
        return "Serbian"
    if langname.startswith("uk"):
        return "Ukrainian"
    if langname.startswith("hr"):
        return "Croatian"
    if langname.startswith("cs"):
        return "Czech"
    if langname.startswith("sk"):
        return "Slovak"
    if langname.startswith("sl"):
        return "Slovenian"
    if langname.startswith("bg"):
        return "Bulgarian"
    if langname.startswith("hu"):
        return "Hungarian"
    if langname.startswith("lt"):
        return "Lithuanian"
    if langname.startswith("lv"):
        return "Latvian"
    if langname.startswith("mk"):
        return "Macedonian"
    if langname.startswith("fa"):
        return "Persian"
    return langname
