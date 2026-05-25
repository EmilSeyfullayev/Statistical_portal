from apps.imports.handlers.transit import TransitExcelImporter


IMPORTERS = {
    TransitExcelImporter.parser_key: TransitExcelImporter,
}


def get_importer(parser_key):
    try:
        return IMPORTERS[parser_key]
    except KeyError as exc:
        raise ValueError(f"No importer registered for parser key '{parser_key}'.") from exc
