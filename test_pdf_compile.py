import sys
import os
try:
    import django
    from django.conf import settings

    settings.configure(
        BASE_DIR=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    django.setup()

    # Mocking investment_extras so it doesn't try to load template tags
    import sys
    import types
    mod = types.ModuleType("apps.investments.templatetags.investment_extras")
    mod.readable_txn_type = lambda x: x
    sys.modules["apps.investments.templatetags.investment_extras"] = mod
    sys.modules["apps.investments.templatetags"] = types.ModuleType("apps.investments.templatetags")
    sys.modules["apps.investments"] = types.ModuleType("apps.investments")

    from apps.reports.services.pdf_generator import generate_wealth_report_pdf, generate_pl_report_pdf, generate_capital_gain_pdf, generate_transaction_statement_pdf
    print("Compiled successfully!")
except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)
