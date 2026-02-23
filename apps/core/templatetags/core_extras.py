from django import template
from django.contrib.humanize.templatetags.humanize import intcomma

register = template.Library()

@register.filter
def indian_large_number(value):
    """
    Formats large numbers into Indian denominations (Lacs, Crores).
    Small numbers are formatted with standard Indian comma separation.

    Examples:
    12345 -> 12,345
    150000 -> 1.50 Lacs
    12500000 -> 1.25 Cr
    """
    if value is None or value == "":
        return ""

    try:
        val = float(value)
    except (ValueError, TypeError):
        return value

    abs_val = abs(val)

    if abs_val >= 10000000:  # 1 Crore
        return "{:.2f} Cr".format(val / 10000000)
    elif abs_val >= 100000:  # 1 Lakh
        return "{:.2f} Lacs".format(val / 100000)
    else:
        # Use intcomma for standard formatting below 1 Lakh
        # Pass the original value type if possible to preserve integer formatting
        if isinstance(value, int):
             return intcomma(value)
        elif val.is_integer():
             return intcomma(int(val))
        return intcomma(val)
