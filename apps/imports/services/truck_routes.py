COUNTRIES_WITH_DASHES = [
    "ABŞ-nın uzaq xırda adaları",
    "Bruney-Darüssalam",
    "Burkina-Faso",
    "Cəbəli-Tariq",
    "Kabo-Verde",
    "Kosta-Rika",
    "Kot-divuar",
    "Papua-Yeni Qvineya",
    "Puerto-Riko (ABŞ)",
    "Qvineya-Bissau",
    "San-Marino",
    "San-Tome və Prinsipi",
    "Sen-Bartelemi",
    "Sent-Lüsiya",
    "Syerra-Leone",
    "Timor-Leste",
    "Şri-Lanka",
]


def split_fromto_value(value):
    if value is None:
        return None, None

    text = str(value).strip()
    if not text:
        return None, None

    for country in sorted(COUNTRIES_WITH_DASHES, key=len, reverse=True):
        prefix = f"{country}-"
        suffix = f"-{country}"
        if text.startswith(prefix):
            return country, text[len(prefix):].strip() or None
        if text.endswith(suffix):
            return text[:-len(suffix)].strip() or None, country

    if "-" not in text:
        return text, None

    origin, destination = text.split("-", 1)
    return origin.strip() or None, destination.strip() or None


def _sql_literal(value):
    return "'" + value.replace("'", "''") + "'"


def fromto_from_sql_expression(fromto_expression):
    clean_expression = f"NULLIF(btrim({fromto_expression}::text), '')"
    cases = []
    for country in sorted(COUNTRIES_WITH_DASHES, key=len, reverse=True):
        country_literal = _sql_literal(country)
        prefix_literal = _sql_literal(f"{country}-")
        suffix_literal = _sql_literal(f"-{country}")
        cases.append(
            f"WHEN left({clean_expression}, {len(country) + 1}) = {prefix_literal} "
            f"THEN {country_literal}"
        )
        cases.append(
            f"WHEN right({clean_expression}, {len(country) + 1}) = {suffix_literal} "
            f"THEN NULLIF(btrim(left({clean_expression}, length({clean_expression}) - {len(country) + 1})), '')"
        )
    case_sql = " ".join(cases)
    return (
        "CASE "
        f"WHEN {clean_expression} IS NULL THEN NULL "
        f"{case_sql} "
        f"WHEN strpos({clean_expression}, '-') > 0 THEN NULLIF(btrim(split_part({clean_expression}, '-', 1)), '') "
        f"ELSE {clean_expression} "
        "END"
    )


def fromto_to_sql_expression(fromto_expression):
    clean_expression = f"NULLIF(btrim({fromto_expression}::text), '')"
    cases = []
    for country in sorted(COUNTRIES_WITH_DASHES, key=len, reverse=True):
        country_literal = _sql_literal(country)
        prefix_literal = _sql_literal(f"{country}-")
        suffix_literal = _sql_literal(f"-{country}")
        cases.append(
            f"WHEN left({clean_expression}, {len(country) + 1}) = {prefix_literal} "
            f"THEN NULLIF(btrim(substr({clean_expression}, {len(country) + 2})), '')"
        )
        cases.append(
            f"WHEN right({clean_expression}, {len(country) + 1}) = {suffix_literal} "
            f"THEN {country_literal}"
        )
    case_sql = " ".join(cases)
    return (
        "CASE "
        f"WHEN {clean_expression} IS NULL THEN NULL "
        f"{case_sql} "
        f"WHEN strpos({clean_expression}, '-') > 0 THEN NULLIF(btrim(substr({clean_expression}, strpos({clean_expression}, '-') + 1)), '') "
        "ELSE NULL "
        "END"
    )
