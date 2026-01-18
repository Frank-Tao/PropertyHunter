import re


def parse_price_range(text: str | None) -> tuple[int | None, int | None]:
    if not text:
        return None, None
    lowered = text.lower()
    if any(
        marker in lowered
        for marker in ["contact", "auction", "tender", "price on application", "poa"]
    ):
        return None, None

    numbers = _extract_price_numbers(lowered)
    if not numbers:
        return None, None

    if len(numbers) >= 2:
        return numbers[0], numbers[1]

    value = numbers[0]
    if any(marker in lowered for marker in ["under", "up to", "maximum"]):
        return None, value
    if any(marker in lowered for marker in ["from", "offers over", "over", "starting"]):
        return value, None
    return value, None


def _extract_price_numbers(text: str) -> list[int]:
    numbers: list[int] = []
    normalized = text.replace("$", "").replace(",", "")
    for match in re.finditer(r"(\d+(?:\.\d+)?)\s*([mk])?", normalized):
        raw = match.group(1)
        suffix = match.group(2)
        try:
            value = float(raw)
        except ValueError:
            continue
        if suffix == "m":
            value *= 1_000_000
        elif suffix == "k":
            value *= 1_000
        numbers.append(int(value))
    return numbers
