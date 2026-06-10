from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase

from apps.analytics.models import InteractionEvent
from apps.analytics.services import record_interaction
from apps.catalog.models import Module, Submodule
from apps.dashboard.views import TRANSIT_DYNAMICS_REPORT_NAME, record_transit_dynamics_download
from apps.reports.models import ReportDownload


class InteractionTrackingTests(TestCase):
    def test_record_interaction_saves_user_module_and_url(self):
        user = User.objects.create_user(username="worker", password="test")
        module = Module.objects.create(name="Datalar", slug="datalar")
        request = RequestFactory().get("/modules/datalar/")
        request.user = user

        event = record_interaction(request, InteractionEvent.MODULE_VIEW, module=module)

        self.assertEqual(event.user, user)
        self.assertEqual(event.module, module)
        self.assertEqual(event.target_url, "/modules/datalar/")

    def test_record_interaction_merges_metadata(self):
        user = User.objects.create_user(username="worker", password="test")
        request = RequestFactory().get("/reports/example/?download=docx")
        request.user = user

        event = record_interaction(
            request,
            InteractionEvent.REPORT_DOWNLOAD_START,
            target_url=request.get_full_path(),
            metadata={"report_name": "Dinamika hesabatı", "format": "docx"},
        )

        self.assertEqual(event.target_url, "/reports/example/?download=docx")
        self.assertEqual(event.request_metadata["report_name"], "Dinamika hesabatı")
        self.assertEqual(event.request_metadata["format"], "docx")

    def test_dynamic_report_download_records_events_and_download(self):
        user = User.objects.create_user(
            username="worker",
            password="test",
            first_name="Rusif",
            last_name="Nəzərli",
        )
        module = Module.objects.create(name="Tranzit daşımalar", slug="tranzit-daşımalar")
        submodule = Submodule.objects.create(module=module, name="Dinamika arayışı", slug="dinamika-arayışı")
        request = RequestFactory().get("/modules/tranzit-daşımalar/dinamika-arayışı/?download=pdf")
        request.user = user
        report_context = {"report_number": "TR-001-2026/05-Dinamika"}

        record_transit_dynamics_download(request, submodule, report_context, "pdf", "TR-001-2026-05-Dinamika.pdf")

        events = InteractionEvent.objects.order_by("created_at")
        self.assertEqual(events.count(), 1)
        self.assertEqual(events[0].event_type, InteractionEvent.REPORT_LINK_CLICK)
        self.assertEqual(events[0].request_metadata["report_name"], TRANSIT_DYNAMICS_REPORT_NAME)
        self.assertEqual(events[0].request_metadata["format"], "pdf")
        self.assertIn("download=pdf", events[0].target_url)

        download = ReportDownload.objects.get()
        self.assertIsNone(download.report)
        self.assertEqual(download.module, module)
        self.assertEqual(download.submodule, submodule)
        self.assertEqual(download.format, "pdf")
        self.assertEqual(download.request_metadata["report_name"], TRANSIT_DYNAMICS_REPORT_NAME)

# Create your tests here.
