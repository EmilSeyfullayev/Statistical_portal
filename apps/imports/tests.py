from django.test import TestCase
import pandas as pd

from apps.catalog.models import Module, Submodule
from apps.filesync.models import StoredFile
from apps.imports.base import BaseImporter
from apps.imports.models import ImportJob
from apps.imports.services.transit_merge import (
    OMITTED_SOURCE_TABLES,
    date_cast_expression,
    merged_type_for,
)
from apps.imports.services.transit_portal import process_transit_data


class EmptyImporter(BaseImporter):
    parser_key = "empty"

    def import_rows(self, job):
        return 0


class ImportDuplicateTests(TestCase):
    def test_already_imported_file_is_skipped_without_replace(self):
        module = Module.objects.create(name="Datalar", slug="datalar")
        submodule = Submodule.objects.create(module=module, name="Tranzit", slug="tranzit")
        stored_file = StoredFile.objects.create(
            submodule=submodule,
            original_name="transit.xlsx",
            server_path="/tmp/transit.xlsx",
            checksum="abc",
            import_status=StoredFile.STATUS_IMPORTED,
        )

        job = EmptyImporter(stored_file).run()

        self.assertEqual(job.status, ImportJob.STATUS_SKIPPED)
        self.assertEqual(job.duplicate_decision, "prevented")


class TransitMergeDateCastTests(TestCase):
    def test_january_2026_table_is_omitted_from_merge(self):
        self.assertIn("transit_2026_2026_01", OMITTED_SOURCE_TABLES)
        self.assertIn("cumulative", OMITTED_SOURCE_TABLES["transit_2026_2026_01"].lower())

    def test_merged_date_columns_use_timestamptz(self):
        self.assertEqual(merged_type_for("giris_tarixi"), "timestamp with time zone")
        self.assertEqual(merged_type_for("cixis_tarixi"), "timestamp with time zone")

    def test_date_cast_expression_handles_text_and_timestamptz_sources(self):
        text_cast = date_cast_expression("giris_tarixi", "text")
        self.assertIn("to_timestamp", text_cast)
        self.assertIn("MM/DD/YYYY", text_cast)

        timestamp_cast = date_cast_expression("giris_tarixi", "timestamp with time zone")
        self.assertIn("::timestamp with time zone", timestamp_cast)
        self.assertNotIn("to_timestamp", timestamp_cast)


class TransitPortalProcessorTests(TestCase):
    def test_processes_lowercase_merged_columns_and_goods_nomenclature(self):
        raw_frame = pd.DataFrame(
            [
                {
                    "giris_tarixi": "2026-05-01",
                    "giris_nv_novu": "AVTOMOBIL",
                    "giris_go": "Samur",
                    "giris_dehliz": "SIMAL",
                    "bosaltma_yukleme_go": "",
                    "cixis_tarixi": "2026-05-03",
                    "cixis_nv_novu": "DEMIRYOLU",
                    "cixis_go": "Böyük Kəsik",
                    "cixis_dehliz": "QERB",
                    "mal_gonderen_olke": "Rusiya",
                    "mal_teyinat_olke": "Türkiyə",
                    "mal_kodu": "10",
                    "mal_ceki_ton": "12.5",
                },
                {
                    "giris_tarixi": "2026-05-01",
                    "giris_nv_novu": "AVTOMOBIL",
                    "giris_go": "Samur",
                    "giris_dehliz": "SIMAL",
                    "bosaltma_yukleme_go": "",
                    "cixis_tarixi": "2026-05-03",
                    "cixis_nv_novu": "DEMIRYOLU",
                    "cixis_go": "Böyük Kəsik",
                    "cixis_dehliz": "QERB",
                    "mal_gonderen_olke": "Rusiya",
                    "mal_teyinat_olke": "Türkiyə",
                    "mal_kodu": "10",
                    "mal_ceki_ton": "7.5",
                },
            ]
        )
        goods_data = [
            {
                "section": "II - BİTKİ MƏNŞƏLİ QİDALAR",
                "categories": [{"code": "10", "name": "Dənli bitkilər"}],
            }
        ]
        goods_short_data = [
            {
                "section": "Bitki mənşəli məhsullar",
                "categories": [{"code": "10", "name": "Dənli bitkilər"}],
            }
        ]

        result = process_transit_data(
            raw_frame,
            goods_data=goods_data,
            goods_short_data=goods_short_data,
        )

        self.assertEqual(len(result), 1)
        row = result.iloc[0]
        self.assertEqual(row["Yük həcmi (ton)"], 20.0)
        self.assertEqual(row["Dəhliz"], "Şimal-Qərb")
        self.assertEqual(row["Nəqliyyat növü"], "Dəmiryolu")
        self.assertEqual(row["Məhsulun adı"], "Dənli bitkilər")
        self.assertEqual(row["Məhsul qrupu"], "BİTKİ MƏNŞƏLİ QİDALAR")
        self.assertEqual(row["Məhsul adı (qısaldılmış)"], "Dənli bitkilər")
        self.assertEqual(row["Məhsul qrupu (qısaldılmış)"], "Bitki mənşəli məhsullar")
        self.assertEqual(row["Başlangıc-Təyinat ölkəsi"], "Rusiya-Türkiyə")
