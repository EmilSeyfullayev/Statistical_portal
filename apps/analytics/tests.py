from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase

from apps.analytics.models import InteractionEvent
from apps.analytics.services import record_interaction
from apps.catalog.models import Module


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

# Create your tests here.
