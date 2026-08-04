import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.utils import timezone

from apps.users.exporters import export_bbf_relationship_files


class Command(BaseCommand):
    help = (
        "Exports investor/distributor/RM relationships and folio distributor "
        "mappings from the currently configured database. SQLite is refused "
        "by default to prevent accidental exports from a local test database."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir",
            type=str,
            help=(
                "Destination directory. Defaults to a timestamped directory "
                "under export/."
            ),
        )
        parser.add_argument(
            "--allow-sqlite",
            action="store_true",
            help="Allow a SQLite source. Intended only for local testing.",
        )

    def handle(self, *args, **options):
        connection.ensure_connection()
        vendor = connection.vendor
        if vendor == "sqlite" and not options["allow_sqlite"]:
            raise CommandError(
                "Refusing to export from SQLite. Run this command in the "
                "production environment where DATABASE_URL points to the live "
                "database. Use --allow-sqlite only for local testing."
            )

        output_dir = options["output_dir"]
        if not output_dir:
            timestamp = timezone.localtime().strftime("%Y%m%d_%H%M%S")
            output_dir = f"export/bbf_production_relationships_{timestamp}"

        database_settings = connection.settings_dict
        self.stdout.write(f"Database vendor: {vendor}")
        self.stdout.write(
            f"Database host: {database_settings.get('HOST') or '(local)'}"
        )
        self.stdout.write(
            f"Database name: {database_settings.get('NAME') or '(unknown)'}"
        )

        files = export_bbf_relationship_files(output_dir)
        relationship_count = count_csv_rows(files["investor_relationships.csv"])
        folio_count = count_csv_rows(files["folio_distributor_mappings.csv"])

        self.stdout.write(self.style.SUCCESS("BBF relationship export completed."))
        self.stdout.write(f"Output directory: {Path(output_dir).resolve()}")
        self.stdout.write(f"Relationship rows: {relationship_count}")
        self.stdout.write(f"Folio mapping rows: {folio_count}")
        for name, path in files.items():
            self.stdout.write(f"{name}: {Path(path).resolve()}")


def count_csv_rows(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as file_obj:
        return sum(1 for _ in csv.DictReader(file_obj))
