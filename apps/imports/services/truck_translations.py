COLUMN_TRANSLATIONS = {
    "source_file_path": "Mənbə fayl yolu",
    "source_sheet_name": "Mənbə vərəq adı",
    "source_row_number": "Mənbə sətir nömrəsi",
    "import_job_id": "Import işi ID",
    "imported_at": "Import tarixi",
    "ENTER_DATE": "Giriş tarixi",
    "DATESIGN": "Çıxış tarixi",
    "IDN": "IDN",
    "CODE": "Kod",
    "SHORT_NAME": "Mənsubiyyət ölkəsi",
    "CUST_NAME": "Gömrük postu",
    "FROMTO": "Başlanğıc təyinat ölkəsi",
    "FROM": "Başlanğıc ölkə",
    "TO": "Təyinat ölkə",
    "DIRECTION": "İstiqamət kodu",
    "AVTO_NO": "Avtomobil nömrəsi",
    "AVTO": "Avtomobil",
    "NO": "Nömrə",
    "CARRIER": "Daşıyıcı",
    "Loaded": "Yüklü Boş",
    "IN_OUT": "Giriş çıxış",
    "Regime": "Rejim",
    "YEAR": "İl",
    "MONTH": "Ay",
    "COUNT": "Say",
    "WEIGHT": "Çəki",
    "TOTAL_WEIGHT": "Ümumi çəki",
    "WIDTH": "En",
    "HEIGHT": "Hündürlük",
    "WEIGHT_PER_AX": "Oxa düşən çəki",
    "PLACE_WHEEL_COUNT": "Təkər sayı",
    "CONCESSION_CODE": "Güzəşt kodu",
    "PERMISSION_PRICE": "İcazə qiyməti",
    "PERM_BLANK_NO": "İcazə blank nömrəsi",
    "HES_NAME": "Hesabat adı",
    "CONS_NAME": "Konsessiya adı",
    "TESDIQ": "Təsdiq",
    "CONTROL_ST": "Nəzarət statusu",
    "STATUS": "Status",
}

CATEGORY_TRANSLATIONS = {
    "CARRIER": {
        "Local": "Yerli",
        "Foreign": "Xarici",
    },
    "Loaded": {
        "loaded": "Yüklü",
        "unloaded": "Boş",
    },
    "IN_OUT": {
        "in": "Giriş",
        "out": "Çıxış",
        "domestic": "Daxili",
    },
    "Regime": {
        "Transit": "Tranzit",
        "InterTerritorial": "Ərazilər-arası",
        "Domestic": "Daxili",
        "Import": "İdxal",
        "Export": "İxrac",
        "Other": "Digər",
    },
}


def translated_column(column):
    return COLUMN_TRANSLATIONS.get(column, column)


def translated_category(column, value):
    return CATEGORY_TRANSLATIONS.get(column, {}).get(value, value)


def sql_literal(value):
    return "'" + value.replace("'", "''") + "'"


def translated_category_sql(column, value):
    return sql_literal(translated_category(column, value))


def translated_select_sql(columns, quote_name):
    parts = []
    for column in columns:
        translated = translated_column(column)
        quoted_column = quote_name(column)
        if translated == column:
            parts.append(quoted_column)
        else:
            parts.append(f"{quoted_column} AS {quote_name(translated)}")
    return ", ".join(parts)


def translated_output_select_sql(columns, quote_name):
    parts = []
    for column in columns:
        translated = translated_column(column)
        quoted_column = quote_name(column)
        output_column = quote_name(translated)
        value_translations = CATEGORY_TRANSLATIONS.get(column)
        if value_translations:
            cases = " ".join(
                f"WHEN {sql_literal(source)} THEN {sql_literal(target)}"
                for source, target in value_translations.items()
            )
            parts.append(f"CASE {quoted_column} {cases} ELSE {quoted_column} END AS {output_column}")
        elif translated == column:
            parts.append(quoted_column)
        else:
            parts.append(f"{quoted_column} AS {output_column}")
    return ", ".join(parts)
