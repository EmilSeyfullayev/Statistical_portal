from django.test import TestCase, override_settings

from apps.catalog.models import DataSource, Module, Submodule
from apps.filesync.services import build_rsync_command


class RsyncCommandTests(TestCase):
    def test_build_rsync_command_restricts_extensions(self):
        module = Module.objects.create(name="Datalar", slug="datalar")
        submodule = Submodule.objects.create(module=module, name="Tranzit", slug="tranzit")
        source = DataSource.objects.create(
            submodule=submodule,
            name="Transit source",
            accepted_extensions=".xlsx,.csv",
            destination_subdir="tranzit",
        )

        with override_settings(
            SYNC_SOURCE_RSYNC="desktop:/data_uploads/",
            SYNC_DESTINATION_DIR="/tmp/transport-portal-test-sync",
            SYNC_SSH_KEY="/tmp/key",
        ):
            command = build_rsync_command(source)

        self.assertIn("rsync", command[0])
        self.assertIn("--ignore-existing", command)
        self.assertIn("*.xlsx", command)
        self.assertIn("*.csv", command)
        self.assertIn("desktop:/data_uploads/", command)

# Create your tests here.
