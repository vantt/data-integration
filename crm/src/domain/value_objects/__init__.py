"""Domain value objects — immutable, self-validating."""
from domain.value_objects.phone import PhoneNumber
from domain.value_objects.email import Email

__all__ = ["PhoneNumber", "Email"]
