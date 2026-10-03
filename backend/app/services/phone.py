import phonenumbers

from app.config import get_settings


class InvalidPhoneError(ValueError):
    pass


def normalize_phone(raw: str, region: str | None = None) -> str:
    """Parse any user/OS formatted number and return it in E.164, or raise InvalidPhoneError."""
    region = region or get_settings().default_region
    candidate = (raw or "").strip()
    if not candidate:
        raise InvalidPhoneError("Phone number is empty")
    try:
        parsed = phonenumbers.parse(candidate, region)
    except phonenumbers.NumberParseException as exc:
        raise InvalidPhoneError("Phone number cannot be parsed") from exc
    if not phonenumbers.is_valid_number(parsed):
        raise InvalidPhoneError("Phone number is not valid")
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def mask_phone(phone: str | None) -> str:
    """Hide the middle of a number for logs: +37369123456 -> +3736*****56."""
    if not phone:
        return "<empty>"
    if len(phone) <= 6:
        return "*" * len(phone)
    head, tail = phone[:5], phone[-2:]
    return f"{head}{'*' * (len(phone) - len(head) - len(tail))}{tail}"
