import datetime
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
from apps.users.models import User, InvestorProfile, DistributorProfile
from apps.reconciliation.models import Holding
from apps.payouts.models import CommissionRule, Payout, PayoutDetail

def calculate_commission(year, month):
    """
    Calculates distributor commission for the given month/year.
    """
    # 1. Determine period date (1st of the month)
    period_date = datetime.date(year, month, 1)

    # 2. Get all active Distributors
    # Note: User type DISTRIBUTOR is what we loop over.
    distributors = User.objects.filter(user_type=User.Types.DISTRIBUTOR, is_active=True)

    payouts_created = []

    for dist in distributors:
        # Check if payout already exists for this period, delete to re-calculate?
        Payout.objects.filter(distributor=dist, period_date=period_date, status=Payout.STATUS_DRAFT).delete()

        # If PAID exists, skip
        if Payout.objects.filter(distributor=dist, period_date=period_date, status=Payout.STATUS_PAID).exists():
            print(f"Skipping {dist.username}: Payout already PAID for {period_date}")
            continue

        with transaction.atomic():
            # 3. Fetch Investors mapped to this Distributor
            # InvestorProfile has 'distributor' FK to DistributorProfile
            # So we need to get the DistributorProfile for the current User first.
            try:
                dist_profile = dist.distributor_profile
            except DistributorProfile.DoesNotExist:
                print(f"Skipping {dist.username}: No DistributorProfile found")
                continue

            investors = InvestorProfile.objects.filter(distributor=dist_profile)

            # 4. Fetch Holdings
            # Holding -> Investor (Profile) -> User
            holdings = Holding.objects.filter(investor__in=investors).select_related('scheme', 'scheme__category', 'scheme__amc', 'investor', 'investor__user')

            if not holdings.exists():
                # Even if no holdings, maybe we shouldn't create a payout? Or create zero payout?
                # User usually wants to see report even if zero. But 'transaction level' means empty.
                # Let's skip if no holdings.
                continue

            # 5. Group Holdings by (Category, AMC) to determine applicable AUM Slab
            # Key: (category_id, amc_id or None) -> Total AUM

            holding_rule_map = [] # List of (holding, rule)
            rule_aum_map = {} # { rule_id: Decimal(total_aum) }

            for holding in holdings:
                scheme = holding.scheme
                category = scheme.category
                amc = scheme.amc

                # Find Rule: Specific AMC first, then Global
                rule = CommissionRule.objects.filter(category=category, amc=amc).first()
                if not rule:
                    rule = CommissionRule.objects.filter(category=category, amc__isnull=True).first()

                if rule:
                    holding_rule_map.append((holding, rule))
                    current_aum = holding.current_value if holding.current_value else Decimal(0)
                    rule_aum_map[rule.id] = rule_aum_map.get(rule.id, Decimal(0)) + current_aum
                else:
                    # No rule found
                    holding_rule_map.append((holding, None))

            # 6. Create Payout Header
            payout = Payout.objects.create(
                distributor=dist,
                period_date=period_date,
                status=Payout.STATUS_DRAFT
            )

            total_comm = Decimal(0)
            total_payout_aum = Decimal(0)

            # 7. Calculate Commission per Holding
            for holding, rule in holding_rule_map:
                aum = holding.current_value if holding.current_value else Decimal(0)
                rate = Decimal(0)

                if rule:
                    total_rule_aum = rule_aum_map.get(rule.id, Decimal(0))

                    # Find Tier
                    # Slab Logic: Use total_rule_aum to find the tier.
                    tier = rule.tiers.filter(min_aum__lte=total_rule_aum).order_by('-min_aum').first()

                    if tier:
                        # Check max_aum if it exists
                        if tier.max_aum and total_rule_aum >= tier.max_aum:
                             # This should technically not happen if tiers are well defined covering all ranges,
                             # but if it does, it means the AUM is above the max of this tier,
                             # and since we ordered by min_aum desc, this WAS the highest start.
                             # If max is strict, then we fell off the chart (too rich).
                             # Assuming rate 0 if fall off.
                             pass
                        else:
                            rate = tier.rate

                commission = aum * (rate / Decimal(100))

                PayoutDetail.objects.create(
                    payout=payout,
                    holding=holding,
                    investor_name=holding.investor.user.name if holding.investor.user.name else f"User {holding.investor.user.id}",
                    scheme_name=holding.scheme.name,
                    folio_number=holding.folio_number,
                    category=holding.scheme.category.name if holding.scheme.category else "Unknown",
                    amc_name=holding.scheme.amc.name if holding.scheme.amc else "Unknown",
                    aum=aum,
                    applied_rate=rate,
                    commission_amount=commission
                )

                total_comm += commission
                total_payout_aum += aum

            # Update Payout Totals
            payout.total_aum = total_payout_aum
            payout.total_commission = total_comm
            payout.save()

            payouts_created.append(payout)

    return payouts_created
