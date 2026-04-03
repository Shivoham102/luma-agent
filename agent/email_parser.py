def normalize_spoken_email(spoken: str) -> str:
    """Convert a spoken email string into a valid email address.

    Handles common voice transcription patterns:
      - "at" -> "@"
      - "dot" -> "."
      - "underscore" -> "_"
      - "dash" -> "-"
      - strips whitespace
    """
    raise NotImplementedError
