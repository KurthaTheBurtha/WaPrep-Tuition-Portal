from pathlib import Path

from django.conf import settings
from django.core.mail import EmailMessage
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Email database schema PDF and tuition/models.py. "
        "Requires EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, and DEFAULT_FROM_EMAIL."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--to",
            default="353233460@qq.com",
            help="Recipient email address",
        )
        parser.add_argument(
            "--cc",
            default="",
            help="Comma-separated CC addresses (confirmation copy)",
        )
        parser.add_argument(
            "--pdf",
            default="",
            help="Path to database-schema.pdf (default: docs/database-schema.pdf)",
        )
        parser.add_argument(
            "--models",
            default="",
            help="Path to models.py (default: tuition/models.py)",
        )

    def handle(self, *args, **options):
        if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
            raise CommandError(
                "SMTP is not configured. Set EMAIL_HOST_USER and EMAIL_HOST_PASSWORD "
                "(e.g. in .env) and try again."
            )

        base_dir = Path(settings.BASE_DIR)
        pdf_path = Path(options["pdf"]) if options["pdf"] else base_dir / "docs" / "database-schema.pdf"
        models_path = Path(options["models"]) if options["models"] else base_dir / "tuition" / "models.py"

        for path, label in ((pdf_path, "PDF"), (models_path, "models.py")):
            if not path.is_file():
                raise CommandError(f"{label} not found: {path}")

        cc_raw = options["cc"].strip()
        cc_list = [a.strip() for a in cc_raw.split(",") if a.strip()]

        subject = "WaPrep Tuition Portal — database schema documentation"
        body = """Hello,

Please find attached:

1. database-schema.pdf — formatted overview of Django database tables and relationships
2. models.py — source-of-truth Django model definitions (tuition app)

If you have questions about the schema, reply to this message.

Best regards,
WaPrep Tuition Portal
""".strip()

        message = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[options["to"]],
            cc=cc_list,
        )
        message.attach_file(str(pdf_path), mimetype="application/pdf")
        message.attach_file(str(models_path), mimetype="text/x-python")

        sent = message.send(fail_silently=False)
        if sent != 1:
            raise CommandError(f"Unexpected send result: {sent}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Sent to {options['to']}"
                + (f" (CC: {', '.join(cc_list)})" if cc_list else "")
            )
        )
