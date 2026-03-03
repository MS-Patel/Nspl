import csv
import os
import re
from datetime import datetime
from dateutil import parser as date_parser
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from apps.users.models import InvestorProfile, BankAccount, Nominee
from apps.investments.models import Mandate

User = get_user_model()

class Command(BaseCommand):
    help = 'Imports old BSE data (Clients and Mandates) from CSV files.'

    TAX_STATUS_MAP = {
        'INDIVIDUAL': InvestorProfile.INDIVIDUAL,
        'MINOR': InvestorProfile.MINOR,
        'HUF': InvestorProfile.HUF,
        'COMPANY': InvestorProfile.COMPANY,
        'NRI': InvestorProfile.NRI_REPATRIABLE,
        'NRI REPATRIABLE': InvestorProfile.NRI_REPATRIABLE,
        'NRI NON REPATRIABLE': InvestorProfile.NRI_NON_REPATRIABLE,
        'NRI-REPATRIABLE': InvestorProfile.NRI_REPATRIABLE,
        'NRI-NON-REPATRIABLE': InvestorProfile.NRI_NON_REPATRIABLE,
        'SOLE PROPRIETOR': InvestorProfile.INDIVIDUAL,
    }

    OCCUPATION_MAP = {
        'BUSINESS': InvestorProfile.BUSINESS,
        'SERVICE': InvestorProfile.SERVICE,
        'PROFESSIONAL': InvestorProfile.PROFESSIONAL,
        'AGRICULTURIST': InvestorProfile.AGRICULTURIST,
        'RETIRED': InvestorProfile.RETIRED,
        'HOUSEWIFE': InvestorProfile.HOUSEWIFE,
        'STUDENT': InvestorProfile.STUDENT,
        'OTHERS': InvestorProfile.OTHERS,
        'PUBLIC SECTOR SERVICE': InvestorProfile.SERVICE,
        'PRIVATE SECTOR SERVICE': InvestorProfile.SERVICE,
        'GOVERNMENT SERVICE': InvestorProfile.SERVICE,
        'DOCTOR': InvestorProfile.PROFESSIONAL,
    }

    HOLDING_MAP = {
        'SINGLE': InvestorProfile.SINGLE,
        'JOINT': InvestorProfile.JOINT,
        'ANYONE OR SURVIVOR': InvestorProfile.ANYONE_SURVIVOR,
        'AS': InvestorProfile.ANYONE_SURVIVOR,
        'SI': InvestorProfile.SINGLE,
        'JO': InvestorProfile.JOINT,
    }

    BANK_ACCT_TYPE_MAP = {
        'SAVINGS': 'SB',
        'CURRENT': 'CB',
        'NRE': 'NE',
        'NRO': 'NO',
        'SB': 'SB',
        'CB': 'CB',
        'NE': 'NE',
        'NO': 'NO',
    }

    RELATIONSHIP_MAP = {
        'SPOUSE': 'Spouse',
        'FATHER': 'Father',
        'MOTHER': 'Mother',
        'SON': 'Son',
        'DAUGHTER': 'Daughter',
        'BROTHER': 'Others',
        'SISTER': 'Others',
        'OTHERS': 'Others',
    }

    def add_arguments(self, parser):
        parser.add_argument(
            '--clients-file',
            type=str,
            default='docs/old data/bse clients.csv',
            help='Path to the BSE Clients CSV file'
        )
        parser.add_argument(
            '--mandates-file',
            type=str,
            default='docs/old data/bse mandates.csv',
            help='Path to the BSE Mandates CSV file'
        )

    def handle(self, *args, **options):
        clients_file = options['clients_file']
        mandates_file = options['mandates_file']

        if not os.path.exists(clients_file):
            self.stdout.write(self.style.ERROR(f"Clients file not found: {clients_file}"))
            return

        if not os.path.exists(mandates_file):
            self.stdout.write(self.style.ERROR(f"Mandates file not found: {mandates_file}"))
            return

        self.stdout.write(self.style.SUCCESS('Starting Import Process...'))

        # 1. Import Clients
        self.import_clients(clients_file)

        # 2. Import Mandates
        self.import_mandates(mandates_file)

        self.stdout.write(self.style.SUCCESS('Import Process Completed Successfully.'))

    def parse_date(self, date_str):
        if not date_str:
            return None
        date_str = date_str.strip()
        if not date_str:
            return None

        formats = [
            '%d/%m/%Y',
            '%d/%m/%Y %I:%M:%S %p',
            '%m/%d/%y',
            '%d-%b-%y'
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        try:
            return date_parser.parse(date_str).date()
        except Exception:
            return None

    def map_tax_status(self, value):
        if not value: return InvestorProfile.INDIVIDUAL
        norm = value.upper().strip()
        return self.TAX_STATUS_MAP.get(norm, InvestorProfile.INDIVIDUAL)

    def map_occupation(self, value):
        if not value: return InvestorProfile.OTHERS
        norm = value.upper().strip()
        return self.OCCUPATION_MAP.get(norm, InvestorProfile.OTHERS)

    def map_holding(self, value):
        if not value: return InvestorProfile.SINGLE
        norm = value.upper().strip()
        return self.HOLDING_MAP.get(norm, InvestorProfile.SINGLE)

    def map_bank_type(self, value):
        if not value: return 'SB'
        norm = value.upper().strip()
        return self.BANK_ACCT_TYPE_MAP.get(norm, 'SB')

    def map_relationship(self, value):
        if not value: return 'Others'
        norm = value.upper().strip()
        return self.RELATIONSHIP_MAP.get(norm, 'Others')

    def import_clients(self, filepath):
        self.stdout.write(f"Reading clients from {filepath}...")

        count_created = 0
        count_errors = 0

        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    with transaction.atomic():
                        self.process_client_row(row)
                        count_created += 1
                except Exception as e:
                    count_errors += 1
                    client_code = row.get('Client Code', 'Unknown')
                    # self.stdout.write(self.style.ERROR(f"Error processing client {client_code}: {str(e)}"))

        self.stdout.write(self.style.SUCCESS(f"Clients Processed. Success: {count_created}, Errors: {count_errors}"))

    def process_client_row(self, row):
        client_code = row['Client Code'].strip()
        pan = row['Primary Holder PAN'].strip()

        if not client_code or not pan:
            raise ValueError("Client Code or PAN missing")

        first_name = row.get('Primary Holder First Name', '').strip()
        middle_name = row.get('Primary Holder Middle Name', '').strip()
        last_name = row.get('Primary Holder Last Name', '').strip()

        full_name = f"{first_name} {middle_name} {last_name}".replace('  ', ' ').strip()
        email = row.get('Email', '').strip()
        mobile = row.get('Indian Mobile No.', '').strip()

        # 1. Create/Update User
        user, created = User.objects.get_or_create(username=pan)
        if created:
            user.set_password(pan)
            user.force_password_change = True
            user.email = email
            user.first_name = first_name
            user.last_name = last_name
            user.name = full_name
            user.user_type = User.Types.INVESTOR
            user.save()
        else:
            if not user.email and email:
                user.email = email
                user.save()

        # 2. Create/Update InvestorProfile
        dob_str = row.get('Primary Holder DOB/Incorporation', '')
        dob = self.parse_date(dob_str)

        tax_status = self.map_tax_status(row.get('Tax Status'))
        occupation = self.map_occupation(row.get('Occupation Code'))
        holding = self.map_holding(row.get('Holding Nature'))

        profile, p_created = InvestorProfile.objects.update_or_create(
            user=user,
            defaults={
                'pan': pan,
                'dob': dob,
                'gender': 'M' if row.get('Gender', '').upper().startswith('M') else 'F',
                'mobile': mobile,
                'email': email,
                'address_1': row.get('Address 1', '')[:40],
                'address_2': row.get('Address 2', '')[:40],
                'address_3': row.get('Address 3', '')[:40],
                'city': row.get('City', '')[:35],
                'state': row.get('State', '')[:30],
                'pincode': row.get('Pincode', '')[:6],
                'country': row.get('Country', 'India')[:35],
                'tax_status': tax_status,
                'occupation': occupation,
                'holding_nature': holding,
                'ucc_code': client_code,
                'nomination_opt': row.get('Nomination Opt', 'N'),
                'nomination_auth_mode': 'O' if row.get('Nomination Authentication Mode') == 'Z' else 'P',
                'kyc_status': True,
            }
        )

        # 3. Bank Accounts
        self.process_bank_accounts(profile, row)

        # 4. Nominees
        self.process_nominees(profile, row)

    def process_bank_accounts(self, profile, row):
        for i in range(1, 6):
            acc_no = row.get(f'Account No {i}', '').strip()
            if not acc_no:
                continue

            ifsc = row.get(f'IFSC Code {i}', '').strip()
            bank_name = row.get(f'Bank Name {i}', '').strip()
            branch_name = row.get(f'Bank Branch {i}', '').strip()
            acc_type_str = row.get(f'Account Type {i}', '')
            acc_type = self.map_bank_type(acc_type_str)
            is_default = (row.get(f'Default Bank Flag {i}', 'N') == 'Y')

            # UPDATE OR CREATE logic
            # Explicitly passing bse_index = i because import file has fixed slots 1-5

            BankAccount.objects.update_or_create(
                investor=profile,
                account_number=acc_no,
                defaults={
                    'ifsc_code': ifsc,
                    'bank_name': bank_name,
                    'branch_name': branch_name,
                    'account_type': acc_type,
                    'is_default': is_default,
                    'bse_index': i  # Explicitly set index from CSV column 1-5
                }
            )

    def process_nominees(self, profile, row):
        for i in range(1, 4):
            name = row.get(f'Nominee {i} Name', '').strip()
            if not name:
                continue

            rel_str = row.get(f'Nominee {i} Relationship', '')
            relationship = self.map_relationship(rel_str)

            perc_str = row.get(f'Nominee {i} Applicable(%)', '0')
            try:
                percentage = float(perc_str)
            except ValueError:
                percentage = 0.0

            n_add1 = row.get(f'NOM{i}_ADD1', '')[:40]
            n_city = row.get(f'NOM{i}_CITY', '')[:35]
            n_pin = row.get(f'NOM{i}_PIN', '')[:6]
            n_country = row.get(f'NOM{i}_CON', 'India')[:35]

            Nominee.objects.update_or_create(
                investor=profile,
                name=name,
                defaults={
                    'relationship': relationship,
                    'percentage': percentage,
                    'address_1': n_add1,
                    'city': n_city,
                    'pincode': n_pin,
                    'country': n_country,
                    'mobile': row.get(f'NOM{i}_MOB', ''),
                    'email': row.get(f'NOM{i}_EMAIL', ''),
                }
            )

    def import_mandates(self, filepath):
        self.stdout.write(f"Reading mandates from {filepath}...")

        count_created = 0
        count_errors = 0

        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    self.process_mandate_row(row)
                    count_created += 1
                except Exception as e:
                    count_errors += 1
                    # self.stdout.write(self.style.ERROR(f"Error processing mandate: {str(e)}"))

        self.stdout.write(self.style.SUCCESS(f"Mandates Processed. Success: {count_created}, Errors: {count_errors}"))

    def process_mandate_row(self, row):
        client_code = row['CLIENT CODE'].strip()
        mandate_id = row['MANDATE CODE'].strip()

        if not client_code or not mandate_id:
            raise ValueError("Client Code or Mandate ID missing")

        # Find Investor
        try:
            investor = InvestorProfile.objects.get(ucc_code=client_code)
        except InvestorProfile.DoesNotExist:
            raise ValueError(f"Investor with UCC {client_code} not found")

        # Parse Fields
        amount_str = row.get('AMOUNT', '0').strip()
        try:
            amount = float(amount_str)
        except ValueError:
            amount = 0.0

        start_date = self.parse_date(row.get('START DATE'))
        end_date = self.parse_date(row.get('END DATE'))
        if not start_date:
             # Default to today if missing? Or raise error?
             # Mandate must have start date.
             start_date = datetime.today().date()

        status_str = row.get('STATUS', '').upper()
        if status_str == 'APPROVED':
            status = Mandate.APPROVED
        elif status_str == 'REJECTED':
            status = Mandate.REJECTED
        else:
            status = Mandate.PENDING

        mandate_type_str = row.get('MANDATE TYPE', '').upper()
        if 'E-MANDATE' in mandate_type_str:
            mandate_type = Mandate.ISIP # Defaulting to ISIP
        elif 'PHYSICAL' in mandate_type_str:
            mandate_type = Mandate.PHYSICAL
        else:
            mandate_type = Mandate.ISIP

        # Link Bank Account
        bank_acc_no = row.get('BANK ACCOUNT NUMBER', '').strip()
        bank_account = None
        if bank_acc_no:
            bank_account = investor.bank_accounts.filter(account_number=bank_acc_no).first()

        # Fallback to default if not found or empty
        if not bank_account:
            bank_account = investor.bank_accounts.filter(is_default=True).first()

        # Update or Create
        Mandate.objects.update_or_create(
            mandate_id=mandate_id,
            defaults={
                'investor': investor,
                'bank_account': bank_account,
                'amount_limit': amount,
                'start_date': start_date,
                'end_date': end_date,
                'status': status,
                'mandate_type': mandate_type
            }
        )
