from types import SimpleNamespace

from django.test import TestCase
import pandas as pd

from apps.catalog.models import Module, Submodule
from apps.filesync.models import StoredFile
from apps.imports.base import BaseImporter
from apps.imports.handlers.foreign_trucks import (
    normalize_foreign_trucks_frame,
    prepare_frame as prepare_foreign_trucks_frame,
    sql_type_for,
)
from apps.imports.handlers.local_trucks import (
    normalize_local_trucks_frame,
    prepare_frame as prepare_local_trucks_frame,
    sql_type_for as local_trucks_sql_type_for,
)
from apps.imports.models import ImportJob
from apps.imports.handlers.transit import prepare_frame as prepare_transit_frame
from apps.imports.services.transit_merge import (
    OMITTED_SOURCE_TABLES,
    date_cast_expression,
    merged_type_for,
)
from apps.imports.services.transit_portal import process_transit_data
from apps.imports.services.truck_routes import split_fromto_value
from apps.imports.services import trucks, trucks_aggregated
from apps.imports.services.truck_translations import translated_column, translated_output_select_sql


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


class UploadedFramePreparationTests(TestCase):
    def test_unnamed_index_column_is_removed_from_truck_uploads(self):
        stored_file = SimpleNamespace(server_path="/tmp/source.xlsx")
        job = SimpleNamespace(id=1)
        frame = pd.DataFrame({"Unnamed: 0": [1], "SHORT_NAME": ["Azərbaycan"], "WEIGHT": ["2"]})

        local_frame, local_columns = prepare_local_trucks_frame(frame, stored_file, job, "Sheet1")
        foreign_frame, foreign_columns = prepare_foreign_trucks_frame(frame, stored_file, job, "Sheet1")

        self.assertNotIn("Unnamed: 0", local_frame.columns)
        self.assertNotIn("Unnamed: 0", foreign_frame.columns)
        self.assertNotIn("Unnamed: 0", local_columns)
        self.assertNotIn("Unnamed: 0", foreign_columns)

    def test_unnamed_index_column_is_removed_from_transit_uploads(self):
        stored_file = SimpleNamespace(server_path="/tmp/source.xlsx")
        job = SimpleNamespace(id=1)
        frame = pd.DataFrame({"Unnamed: 0": [1], "giris_tarixi": ["05/01/2026"]})

        prepared_frame, column_mapping = prepare_transit_frame(frame, stored_file, job, "Sheet1")

        self.assertNotIn("unnamed_0", prepared_frame.columns)
        self.assertNotIn("unnamed_0", column_mapping)


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
                {
                    "SHORT_NAME": "Gürcüstan",
                    "FROMTO": "İaq-Azərbaycan",
                    "HES_NAME": "Yüklü giriş",
                },
                {
                    "SHORT_NAME": "Tayvan (çinin əyaləti)",
                    "FROMTO": "Azərbaycan-Tayvan (çinin əyaləti)",
                    "HES_NAME": "Yüklü giriş",
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
        self.assertEqual(normalized.loc[5, "FROMTO"], "İraq-Azərbaycan")
        self.assertEqual(normalized.loc[6, "SHORT_NAME"], "Tayvan (Çinin əyaləti)")
        self.assertEqual(normalized.loc[6, "FROMTO"], "Azərbaycan-Tayvan (Çinin əyaləti)")


class LocalTrucksFramePreparationTests(TestCase):
    def test_preparation_parses_enter_date_and_weight_without_text_fixes(self):
        frame = pd.DataFrame(
            [
                {
                    "SHORT_NAME": "AzÉ™rbaycan",
                    "DATESIGN": "31.01.2018 23:53:58",
                    "ENTER_DATE": "31.01.2018 23:12:40",
                    "WEIGHT": "not-number",
                }
            ]
        )

        normalized = normalize_local_trucks_frame(frame)

        self.assertEqual(normalized.loc[0, "SHORT_NAME"], "AzÉ™rbaycan")
        self.assertTrue(pd.isna(normalized.loc[0, "WEIGHT"]))
        self.assertEqual(
            local_trucks_sql_type_for("ENTER_DATE", normalized["ENTER_DATE"]),
            "timestamp with time zone",
        )
        self.assertEqual(
            local_trucks_sql_type_for("WEIGHT", normalized["WEIGHT"]),
            "double precision",
        )
        self.assertEqual(
            local_trucks_sql_type_for("DATESIGN", normalized["DATESIGN"]),
            "timestamp with time zone",
        )


class TruckRouteSplitTests(TestCase):
    def test_split_fromto_handles_simple_routes(self):
        self.assertEqual(split_fromto_value("Türkiyə-Azərbaycan"), ("Türkiyə", "Azərbaycan"))
        self.assertEqual(split_fromto_value("Azərbaycan-Çin"), ("Azərbaycan", "Çin"))

    def test_split_fromto_handles_hyphenated_origin_country(self):
        self.assertEqual(
            split_fromto_value("ABŞ-nın uzaq xırda adaları-Azərbaycan"),
            ("ABŞ-nın uzaq xırda adaları", "Azərbaycan"),
        )
        self.assertEqual(
            split_fromto_value("Kosta-Rika-Azərbaycan"),
            ("Kosta-Rika", "Azərbaycan"),
        )
        self.assertEqual(
            split_fromto_value("Sen-Pyer və Mikelon-Gürcüstan"),
            ("Sen-Pyer və Mikelon", "Gürcüstan"),
        )

    def test_split_fromto_handles_hyphenated_destination_country(self):
        self.assertEqual(
            split_fromto_value("Azərbaycan-Papua-Yeni Qvineya"),
            ("Azərbaycan", "Papua-Yeni Qvineya"),
        )
        self.assertEqual(
            split_fromto_value("Azərbaycan-Şri-Lanka"),
            ("Azərbaycan", "Şri-Lanka"),
        )
        self.assertEqual(
            split_fromto_value("Azərbaycan-Çinin xüs. inz. r-nu Honkonq"),
            ("Azərbaycan", "Çinin xüs. inz. r-nu Honkonq"),
        )

    def test_split_fromto_handles_china_sar_origin_country(self):
        self.assertEqual(
            split_fromto_value("Çinin xüs. inz. r-nu Honkonq-Azərbaycan"),
            ("Çinin xüs. inz. r-nu Honkonq", "Azərbaycan"),
        )

    def test_split_fromto_handles_two_hyphenated_countries(self):
        self.assertEqual(
            split_fromto_value("Kosta-Rika-Papua-Yeni Qvineya"),
            ("Kosta-Rika", "Papua-Yeni Qvineya"),
        )


class TruckRegimeExpressionTests(TestCase):
    def test_direction_1_or_2_domestic_route_is_other_unless_interterritorial(self):
        other_branch = 'AND "DIRECTION" IN (1, 2) THEN \'Other\''
        domestic_check = '"IN_OUT" = \'domestic\''
        for module in [trucks, trucks_aggregated]:
            expression = module.regime_expression()

            self.assertIn('"DIRECTION" IN (1, 2)', expression)
            self.assertIn("THEN 'InterTerritorial'", expression)
            self.assertIn(other_branch, expression)
            self.assertIn("THEN 'Domestic'", expression)
            self.assertLess(expression.index("THEN 'Other'"), expression.index("THEN 'Domestic'"))
            self.assertNotIn(domestic_check, expression)
            self.assertNotIn("Inter-territorial", expression)

    def test_interterritorial_customs_include_qosha_tepe(self):
        for module in [trucks, trucks_aggregated]:
            expression = module.interterritorial_customs_expression()

            self.assertIn("Qoşa təpə", expression)
            self.assertIn("Qosa tepe", expression)

    def test_direction_8_and_9_are_domestic_in_out(self):
        for module in [trucks, trucks_aggregated]:
            expression = module.in_out_expression()

            self.assertIn('"DIRECTION" IN (8, 9)', expression)
            self.assertIn("THEN 'domestic'", expression)

    def test_final_aggregated_columns_and_categories_are_translated(self):
        select_sql = translated_output_select_sql(["YEAR", "MONTH", "CARRIER", "Loaded", "IN_OUT", "Regime", "FROMTO", "FROM", "TO"], trucks.quote_name)

        self.assertIn('"YEAR" AS "İl"', select_sql)
        self.assertIn("\"CARRIER\" WHEN 'Local' THEN 'Yerli'", select_sql)
        self.assertIn('AS "Daşıyıcı"', select_sql)
        self.assertIn('AS "Yüklü Boş"', select_sql)
        self.assertIn('AS "Giriş çıxış"', select_sql)
        self.assertIn('AS "Başlanğıc təyinat ölkəsi"', select_sql)
        self.assertIn("\"Regime\" WHEN 'Transit' THEN 'Tranzit'", select_sql)
        self.assertIn('AS "Rejim"', select_sql)
        self.assertEqual(translated_column("COUNT"), "Say")

    def test_empty_fromto_rows_are_filtered_before_truck_processing(self):
        for module in [trucks, trucks_aggregated]:
            where_sql = module.non_empty_fromto_where()

            self.assertIn('"FROMTO" IS NOT NULL', where_sql)
            self.assertIn("btrim(\"FROMTO\"::text) <> ''", where_sql)

    def test_weight_over_50000_is_divided_before_aggregation(self):
        for module in [trucks, trucks_aggregated]:
            weight_sql = module.normalized_weight_sql('"WEIGHT"')

            self.assertIn('WHEN "WEIGHT" > 50000 THEN "WEIGHT" / 10', weight_sql)


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
