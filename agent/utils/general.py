import re


def parse_param(param: str) -> str:
    if param and len(param) >= 2 and param[0] == param[-1] and param[0] in ("'", '"'):
        return param[1:-1]
    return param


def parse_rift_floor_number(text: str) -> int:
    """
    Parse claimed floor number from text like "All Rewards for 28F Claimed"
    Returns the number or None if not found
    """
    if not text:
        return None

    # Look for number followed by "F" in claimed text
    pattern = r"(\d+)F"
    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        return int(match.group(1))

    return None
