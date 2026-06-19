from django.test import TestCase
import pandas as pd

from apps.catalog.models import Module, Submodule
from apps.filesync.models import StoredFile
from apps.imports.base import BaseImporter
from apps.imports.handlers.foreign_trucks import normalize_foreign_trucks_frame, sql_type_for
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


class ForeignTrucksFramePreparationTests(TestCase):
    def test_preparation_fixes_text_dates_and_weight(self):
        frame = pd.DataFrame(
            [
                {
                    "SHORT_NAME": "AzÉ™rbaycan",
                    "FROMTO": "TÃ¼rkiyÉ™-AzÉ™rbaycan",
                    "AVTO_NO": "DartÄ±cÄ± :- 10AA100",
                    "CUST_NAME": "QÄ±rmÄ±zÄ± kÃ¶rpÃ¼ g/p",
                    "HES_NAME": "YÃ¼klÃ¼ giriÅŸ",
                    "CONS_NAME": "Yoxdur",
                    "DATESIGN": "31.01.2018 23:53:58",
                    "ENTER_DATE": "31.01.2018 23:12:40",
                    "WEIGHT": "not-number",
                }
            ]
        )

        normalized = normalize_foreign_trucks_frame(frame)

        self.assertEqual(normalized.loc[0, "SHORT_NAME"], "Azərbaycan")
        self.assertEqual(normalized.loc[0, "FROMTO"], "Türkiyə-Azərbaycan")
        self.assertEqual(normalized.loc[0, "AVTO_NO"], "Dartıcı :- 10AA100")
        self.assertEqual(normalized.loc[0, "CUST_NAME"], "Qırmızı körpü g/p")
        self.assertEqual(normalized.loc[0, "HES_NAME"], "Yüklü giriş")
        self.assertTrue(pd.isna(normalized.loc[0, "WEIGHT"]))
        self.assertEqual(sql_type_for("DATESIGN", normalized["DATESIGN"]), "timestamp with time zone")
        self.assertEqual(sql_type_for("ENTER_DATE", normalized["ENTER_DATE"]), "timestamp with time zone")
        self.assertEqual(sql_type_for("WEIGHT", normalized["WEIGHT"]), "double precision")

    def test_preparation_fixes_control_character_country_names_and_hes_variants(self):
        frame = pd.DataFrame(
            [
                {
                    "SHORT_NAME": "Amerika Birləşmiş Ş\x9etatları",
                    "FROMTO": "ABŞ\x9e-nın uzaq xırda adaları-Azərbaycan",
                    "HES_NAME": "Yüklü giriş, yüksüz Çıxış və tranzit keçid üçün",
                },
                {
                    "SHORT_NAME": "BelÇika",
                    "FROMTO": "Azərbaycan-Çin",
                    "HES_NAME": "ÜÇüncü ölkəyə və ya üÇüncü ölkədən daşınmalar üÇün",
                },
                {
                    "SHORT_NAME": "Çexiya",
                    "FROMTO": "Azərbaycan-Çinin xüs. inz. r-nu Honkonq",
                    "HES_NAME": "Yüksüz giriş üçıün",
                },
                {
                    "SHORT_NAME": "Belarus",
                    "FROMTO": "Azərbaycan-SuriyaƏrəb Respublikası",
                    "HES_NAME": "Yüklü giriş, yüksüzıxış və tranzit keçid üçün",
                },
                {
                    "SHORT_NAME": "Belarus",
                    "FROMTO": "Belarus-BirləşmişƏrəbƏmirlikləri",
                    "HES_NAME": "Yüklü giriş, yüksüzçıxış və tranzit keçid üçün",
                },
            ]
        )

        normalized = normalize_foreign_trucks_frame(frame)

        self.assertEqual(normalized.loc[0, "SHORT_NAME"], "Amerika Birləşmiş Ştatları")
        self.assertEqual(normalized.loc[0, "FROMTO"], "ABŞ-nın uzaq xırda adaları-Azərbaycan")
        self.assertEqual(normalized.loc[0, "HES_NAME"], "Yüklü giriş, yüksüz çıxış və tranzit keçid üçün")
        self.assertEqual(normalized.loc[1, "SHORT_NAME"], "Belçika")
        self.assertEqual(normalized.loc[1, "FROMTO"], "Azərbaycan-Çin")
        self.assertEqual(normalized.loc[1, "HES_NAME"], "Üçüncü ölkəyə və ya üçüncü ölkədən daşınmalar üçün")
        self.assertEqual(normalized.loc[2, "SHORT_NAME"], "Çexiya")
        self.assertEqual(normalized.loc[2, "FROMTO"], "Azərbaycan-Çinin xüs. inz. r-nu Honkonq")
        self.assertEqual(normalized.loc[2, "HES_NAME"], "Yüksüz giriş üçün")
        self.assertEqual(normalized.loc[3, "FROMTO"], "Azərbaycan-Suriya Ərəb Respublikası")
        self.assertEqual(normalized.loc[3, "HES_NAME"], "Yüklü giriş, yüksüz çıxış və tranzit keçid üçün")
        self.assertEqual(normalized.loc[4, "FROMTO"], "Belarus-Birləşmiş Ərəb Əmirlikləri")
        self.assertEqual(normalized.loc[4, "HES_NAME"], "Yüklü giriş, yüksüz çıxış və tranzit keçid üçün")


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
