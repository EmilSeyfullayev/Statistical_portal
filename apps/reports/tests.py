from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import TestCase, override_settings

from apps.catalog.models import Module, Submodule
from apps.reports.models import ReportDefinition
from apps.reports.services import generate_report_file


class ReportGenerationTests(TestCase):
    def test_transit_report_generates_docx_file(self):
        module = Module.objects.create(name="Datalar", slug="datalar")
        submodule = Submodule.objects.create(module=module, name="Tranzit", slug="tranzit")
        report = ReportDefinition.objects.create(
            submodule=submodule,
            name="Transit report",
            slug="transit-report",
            generator_key="transit_docx_v1",
        )

        with TemporaryDirectory() as tempdir, override_settings(REPORT_OUTPUT_DIR=tempdir):
            output_path = generate_report_file(report)

            self.assertTrue(Path(output_path).exists())
            self.assertEqual(Path(output_path).suffix, ".docx")

    def test_transit_report_generates_pdf_file(self):
        module = Module.objects.create(name="Datalar", slug="datalar")
        submodule = Submodule.objects.create(module=module, name="Tranzit", slug="tranzit")
        report = ReportDefinition.objects.create(
            submodule=submodule,
            name="Transit PDF report",
            slug="transit-pdf-report",
            format=ReportDefinition.FORMAT_PDF,
            generator_key="transit_pdf_v1",
        )

        with TemporaryDirectory() as tempdir, override_settings(REPORT_OUTPUT_DIR=tempdir):
            output_path = generate_report_file(report)

            self.assertTrue(Path(output_path).exists())
            self.assertEqual(Path(output_path).suffix, ".pdf")

# Create your tests here.
