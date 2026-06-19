from apps.imports.handlers.foreign_trucks import ForeignTrucksExcelImporter
from apps.imports.handlers.transit import TransitExcelImporter


IMPORTERS = {
    ForeignTrucksExcelImporter.parser_key: ForeignTrucksExcelImporter,
    TransitExcelImporter.parser_key: TransitExcelImporter,
}


def get_importer(parser_key):
    try:
        return IMPORTERS[parser_key]
    except KeyError as exc:
        raise ValueError(f"No importer registered for parser key '{parser_key}'.") from exc
