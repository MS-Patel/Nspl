from django.core.management.base import BaseCommand

from apps.users.exporters import export_new_portal_import_files


class Command(BaseCommand):
    help = "Exports CSV files in the new portal import format."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir",
            type=str,
            default="tmp/new_portal_imports",
            help="Directory where the generated CSV files will be written.",
        )
        parser.add_argument(
            "--member-code",
            type=str,
            default="24637",
            help="Member code required by the new portal's client-master import.",
        )

    def handle(self, *args, **options):
        files = export_new_portal_import_files(
            output_dir=options["output_dir"],
            member_code=options["member_code"],
        )

        self.stdout.write(self.style.SUCCESS("Generated new portal import files:"))
        for name, path in files.items():
            self.stdout.write(f"{name}: {path}")
