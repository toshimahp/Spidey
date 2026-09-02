"""
cli_utils.py

All input collection and validation for the terminal UI lives here.
Every function is defensive: bad, empty, or unexpected input is handled
by re-prompting or returning a clear failure — never by crashing.

No business logic here (no scoring, no incident rules) — only the
mechanics of getting a valid value out of a human at a keyboard.

Note on EOF/Ctrl+C: if the input stream genuinely ends (EOF) or the user
sends Ctrl+C, there is no possible input left to retry with — looping
forever asking for more would hang the program, which is itself a crash
in slow motion. Instead we raise SessionEnded so main.py can shut down
cleanly, the same way choosing "Exit" would.
"""


class SessionEnded(Exception):
    """Raised when the input stream ends or the user interrupts (Ctrl+C)."""


def _read_line(prompt_text: str) -> str:
    try:
        return input(prompt_text)
    except EOFError:
        print("\nInput stream ended. Shutting down.")
        raise SessionEnded from None
    except KeyboardInterrupt:
        print("\nInterrupted. Shutting down.")
        raise SessionEnded from None


def prompt_choice(prompt_label: str, items, formatter=None, allow_cancel: bool = True):
    """
    The one generic building block behind every decision in this app:
    print `items` as a numbered menu and return whichever item the user
    picks — never free text. Used for incident type, location, severity,
    description, status transitions, and even picking *which* incident
    to act on, so the operator is always choosing from a fixed set of
    options rather than typing something that could be mistyped.

    - `formatter(item) -> str` controls how each item is displayed
      (defaults to `str(item)`); the returned value is always the
      original item from `items`, never the display string.
    - If `allow_cancel` is True, a "0. Cancel" option is added and
      choosing it returns None.
    - If `items` is empty, there is nothing to choose from — this
      prints a note and returns None immediately rather than presenting
      an unanswerable menu (which would hang waiting for a choice that
      can never be valid).
    """
    if not items:
        print("(No options available.)")
        return None

    if formatter is None:
        formatter = str

    print(prompt_label)
    for index, item in enumerate(items, start=1):
        print(f"  {index}. {formatter(item)}")
    if allow_cancel:
        print("  0. Cancel")

    valid_choices = {str(i) for i in range(1, len(items) + 1)}
    if allow_cancel:
        valid_choices.add("0")

    choice = prompt_menu_choice("Choose an option: ", valid_choices)
    if allow_cancel and choice == "0":
        return None
    return items[int(choice) - 1]


def prompt_menu_choice(prompt_text: str, valid_choices) -> str:
    """Keep asking until the user enters one of valid_choices (strings)."""
    while True:
        raw = _read_line(prompt_text)
        choice = raw.strip()
        if choice in valid_choices:
            return choice

        print("X INVALID OPTION")
        print("Please select an option from the menu.\n")


def prompt_nonempty_text(prompt_text: str) -> str:
    """Keep asking until the user provides non-blank text."""
    while True:
        raw = _read_line(prompt_text)
        value = raw.strip()
        if value:
            return value

        print("This field can't be empty. Please try again.\n")


def prompt_non_negative_int(prompt_text: str) -> int:
    """Keep asking until the user provides a whole number >= 0."""
    while True:
        raw = _read_line(prompt_text)
        value = raw.strip()
        if not value:
            print("This field can't be empty. Please try again.\n")
            continue

        try:
            number = int(value)
        except ValueError:
            print("Please enter a whole number (e.g. 12).\n")
            continue

        if number < 0:
            print("Please enter a number that isn't negative.\n")
            continue

        return number


def prompt_free_text(prompt_text: str) -> str:
    """
    Genuinely free text, for the rare fields a fixed menu can't cover
    (e.g. "Other" type/location, a custom description, or an exact
    headcount). Still validated: blank input is rejected and re-asked.
    """
    return prompt_nonempty_text(prompt_text)
