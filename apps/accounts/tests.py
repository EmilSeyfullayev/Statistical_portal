from django.contrib.auth.models import Group, User
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from apps.accounts.middleware import AdminAccessMiddleware
from apps.accounts.services import ADMIN_GROUP, get_user_display_name, is_admin


class UserDisplayNameTests(TestCase):
    def test_uses_first_and_last_name(self):
        user = User(username="jdoe", first_name="Əli", last_name="Məmmədov")
        self.assertEqual(get_user_display_name(user), "Əli Məmmədov")

    def test_falls_back_to_username(self):
        user = User(username="jdoe")
        self.assertEqual(get_user_display_name(user), "jdoe")

    def test_returns_empty_for_anonymous_user(self):
        from django.contrib.auth.models import AnonymousUser

        self.assertEqual(get_user_display_name(AnonymousUser()), "")


class AdminAccessTests(TestCase):
    def setUp(self):
        self.admin_group = Group.objects.create(name=ADMIN_GROUP)
        self.admin_user = User.objects.create_user(username="admin_user", password="test")
        self.admin_user.groups.add(self.admin_group)
        self.worker_user = User.objects.create_user(username="worker_user", password="test")
        self.client = Client()

    def test_is_admin_for_group_member(self):
        self.assertTrue(is_admin(self.admin_user))
        self.assertFalse(is_admin(self.worker_user))

    def test_statistics_redirects_non_admin(self):
        self.client.force_login(self.worker_user)
        response = self.client.get(reverse("analytics:statistics"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dashboard:home"))

    def test_statistics_allows_admin(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("analytics:statistics"))
        self.assertEqual(response.status_code, 200)

    def test_admin_site_redirects_non_admin(self):
        self.client.force_login(self.worker_user)
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dashboard:home"))

    def test_middleware_allows_admin_paths_for_admin(self):
        request = RequestFactory().get("/admin/")
        request.user = self.admin_user
        response = AdminAccessMiddleware(lambda req: "ok")(request)
        self.assertEqual(response, "ok")
