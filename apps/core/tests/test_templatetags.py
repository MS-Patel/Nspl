from django.test import SimpleTestCase, override_settings
from django.template import Context, Template
from django.contrib.humanize.templatetags.humanize import intcomma
from apps.core.templatetags.core_extras import indian_large_number
from django.utils import translation

class IndianLargeNumberFilterTest(SimpleTestCase):
    def test_small_numbers(self):
        self.assertEqual(indian_large_number(12345), "12,345")
        self.assertEqual(indian_large_number(99999), "99,999")
        self.assertEqual(indian_large_number(100), "100")

    def test_lakhs(self):
        self.assertEqual(indian_large_number(100000), "1.00 Lacs")
        self.assertEqual(indian_large_number(150000), "1.50 Lacs")
        self.assertEqual(indian_large_number(9950000), "99.50 Lacs")
        # Edge case: rounding to 100.00 Lacs is acceptable if it hasn't crossed the strict 1Cr threshold in logic
        self.assertEqual(indian_large_number(9999999), "100.00 Lacs")

    def test_crores(self):
        self.assertEqual(indian_large_number(10000000), "1.00 Cr")
        self.assertEqual(indian_large_number(12500000), "1.25 Cr")
        self.assertEqual(indian_large_number(125000000), "12.50 Cr")

    def test_floats(self):
        self.assertEqual(indian_large_number(123.45), "123.45")
        self.assertEqual(indian_large_number(100000.50), "1.00 Lacs")
        self.assertEqual(indian_large_number(10000000.99), "1.00 Cr")

    def test_strings(self):
        self.assertEqual(indian_large_number("12345"), "12,345")
        self.assertEqual(indian_large_number("150000"), "1.50 Lacs")

    def test_invalid(self):
        self.assertEqual(indian_large_number("abc"), "abc")
        self.assertEqual(indian_large_number(None), "")

    def test_negative(self):
        self.assertEqual(indian_large_number(-12345), "-12,345")
        self.assertEqual(indian_large_number(-150000), "-1.50 Lacs")
        self.assertEqual(indian_large_number(-12500000), "-1.25 Cr")

class IntCommaIndianFormatTest(SimpleTestCase):
    @override_settings(LANGUAGE_CODE='en-in', USE_L10N=True, USE_THOUSAND_SEPARATOR=True)
    def test_intcomma_indian(self):
        # We need to activate the language for format localization to take effect
        with translation.override('en-in'):
             # intcomma relies on the active locale
             # Standard Indian format: 1,23,456
             # Note: Django's 'en-in' format definition for THOUSAND_SEPARATOR might need verification.
             # Default Django 'en' format is 123,456. 'en-in' should be 1,23,456.
             # Let's see what happens.
             self.assertEqual(intcomma(123456), "1,23,456")
             self.assertEqual(intcomma(1234567), "12,34,567")
