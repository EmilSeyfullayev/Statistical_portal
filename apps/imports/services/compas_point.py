import pandas as pd
from django.db import connection


FOREIGN_SCHEMA = "foreign_trucks"
FOREIGN_MERGED_TABLE = "foreign_trucks_merged"
LOCAL_SCHEMA = "local_trucks"
LOCAL_MERGED_TABLE = "local_trucks_merged"
CUST_NAME_COLUMN = "CUST_NAME"
COMPASS_POINT_COLUMN = "Giriş-çıxış nöqtəsi"
BORDER_CUSTOMS_COLUMN = "Sərhəd postu"
BORDER_CUSTOMS_YES = "Bəli"
BORDER_CUSTOMS_NO = "Xeyr"
OTHER_COMPASS_POINT = "Digər"

NORTH_CUSTOMS = [
    "Samur g/p",
    "Xanoba g/p",
    "Şirvanlı g/p",
    "Şimal Ərazi Baş Gömrük İdarəsi",
    "Xaçmaz Gömrük İdarəsi",
    "Xudat g/p",
    "Xudat  g/p",
]

WEST_CUSTOMS = [
    "Qırmızı körpü g/p",
    "Mazımqara g/p",
    "Mazımçay g/p",
    "Eyvazlı gömrük postu",
    "Tovuz G/İ",
    "Tovuz g/p",
    "Balakən G/İ",
    "Balakən g/p",
    "Qərb Ərazi BGİ",
    "Şərqi Zəngəzur Gömrük İdarəsi",

    "Qubadlı gömrük postu",
    "Sadıxlı g/p",
]

EAST_CUSTOMS = [
    "Beynəlxalq Dəniz Ticarət Limanı g/p",
    "Baki Beynalxalq Dəniz Limani",
    "Dəniz nəqliyyatı və Enerji resursları Baş Gömrük İdarəsi",
    "Enerji resursları və dəniz nəqliyyatında BG/İ",
    "Liman g/p",
    "Sahil g/p",
    "Hövsan Dəniz g/p",
    "Zirə Dəniz g/p",
    "Dübəndi g/p",
    "Yeni Sanqaçal g/p",
    "HNBGİ",
    "Abşeron Gömrük Postu",
    '"Logistika Mərkəzi" gömrük postu',
    "Azad və XIZ üzrə Gömrük İdarəsi",
    "Azad və Xüsusi İqtisadi Zonalar üzrə Gömrük İdarəsi",
    "Xırdalan g/p",
    "Xocahəsən g/p",
    "Xocəsən g/p",
    "Aksizli mallar üzrə BGİ",
    "Aksiz BG/İ",
    "Sumqayıt Gİ",
    "Sumqayıt BGİ",
    "Bakı BGİ",
    "Bakı Karqo Terminalı Hava Liman g/p",
    "Bakı KOB g/p",
    "Poçt göndərişləri g/p",
    '"Poçt və ekspres daşımalar" gömrük postu',
    "Qaradağ g/p",
    "Keşlə g/p",
    "Güzdək g/p",
    "Dübəndi g/p",
    "Yeni Sanqaçal g/p",
    "İpək Yolu g/p",
    "Azərterminalkompleks",
]

SOUTH_CUSTOMS = [
    "Astara g/p",
    "Astara G/İ",
    "Astara Keçid məntəqəsi",
    "Astara modul tipli g/p",
    "Astara Dəmiryolu g/p",
    "Cənub-Astara g/p",
    "Biləsuvar g/p",
    "Biləsuvar G/İ",
    "Biləsuvar Keçid məntəqəsi",
    "Lənkəran g/p",
    "Qoşa təpə g/p",
    "Cənub Ərazi BG/İ",
    "Xudafərin g/p",
    "Xudafərin Gömrük Postu",
    "Xudafərin G/İ",
]

NAXCIVAN_SOUTH_CUSTOMS = [
    "Şahtaxtı g/p",
    "Şahtaxtı G/İ",
    "Culfa g/p",
    "Culfa G/İ",
]

NAXCIVAN_WEST_CUSTOMS = [
    "Sədərək g/p",
    "Sədərək G/İ",
]

NAXCIVAN_OTHER_CUSTOMS = [
    '"Naxçıvan Karqo Terminalı" g/p',
    "Naxçıvan hava limanı g/p",
    "Naxçıvan BGİ",
    "NŞGİ",
    "NHNGİ",
    "NHLGP",
    "NDGK",
]

CENTER_CUSTOMS = [
    "Gəncə G/İ",
    "Gəncə hava limanı g/p",
    "Kürdəmir g/p",
    '"Kürdəmir" gömrük postu',
    "Şəki g/p",
    "Şəki Gömrük Postu",
    "Yevlax Gömrük Postu",
    "Yevlax g/p",
    "Yevlax G/İ",
    "Qəbələ g/p",
    "Qəbələ Gömrük Postu",
    "Mingəçevir Gömrük Postu",
    "Şirvan g/p",
    "Şirvan G/İ",
    '"Şirvan" gömrük postu',
]

OTHER_CUSTOMS = [
    "DGK",

    "Avtonəqliyyat BGİ",
    "Enerji G/İ",
    "Cargonyx GNZ",
    "COP29",
    "WUF13",
]

COMPASS_POINT_CUSTOMS = {
    "Şimal": NORTH_CUSTOMS,
    "Qərb": WEST_CUSTOMS,
    "Şərq": EAST_CUSTOMS,
    "Cənub": SOUTH_CUSTOMS,
    "Naxçıvan Cənub": NAXCIVAN_SOUTH_CUSTOMS,
    "Naxçıvan Qərb": NAXCIVAN_WEST_CUSTOMS,
    "Naxçıvan Digər": NAXCIVAN_OTHER_CUSTOMS,
    "Mərkəz": CENTER_CUSTOMS,
    OTHER_COMPASS_POINT: OTHER_CUSTOMS,
}

# Initial border-post review list is built from current unique foreign CUST_NAME
# values. Unknown values are assigned to Digər in the output column so this list
# can be corrected manually without changing source data.
FOREIGN_BORDER_CUSTOMS = [
    "Qırmızı körpü g/p",
    "Samur g/p",
    "Mazımqara g/p",
    "Sədərək g/p",
    "Astara g/p",
    "Biləsuvar g/p",
    "Culfa g/p",
    "Şahtaxtı g/p",
    "Beynəlxalq Dəniz Ticarət Limanı g/p",
    "Xanoba g/p",
    "Biləsuvar Keçid məntəqəsi",
    "Astara G/İ",
    "Astara Keçid məntəqəsi",
    "Biləsuvar G/İ",
    "Şirvanlı g/p",
    "Cənub-Astara g/p",
    "Qoşa təpə g/p",
    "Mazımçay g/p",
    "Eyvazlı gömrük postu",
    "Baki Beynalxalq Dəniz Limani",
    "Astara modul tipli g/p",
    "Sədərək G/İ",
    "Culfa G/İ",
    "Qubadlı gömrük postu",
    "Şahtaxtı G/İ",
    # "Bakı BGİ",
    # "Enerji resursları və dəniz nəqliyyatında BG/İ",
    # "Xaçmaz Gömrük İdarəsi",
    # "DGK",
    # "Gəncə hava limanı g/p",
    # "Azərterminalkompleks",
    # "Lənkəran g/p",
    # "Şimal Ərazi Baş Gömrük İdarəsi",
    # "Dəniz nəqliyyatı və Enerji resursları Baş Gömrük İdarəsi",
    # "Tovuz G/İ",
    "Liman g/p",
    "Sahil g/p",
    "Hövsan Dəniz g/p",
    "Zirə Dəniz g/p",
    "Dübəndi g/p",
    "Yeni Sanqaçal g/p",
]

# Aliases cover shortened or slightly misspelled names seen in notes and source files.
CUSTOMS_ALIASES = {
    "Samur": "Samur g/p",
    "Xanoba": "Xanoba g/p",
    "Şirvanlı": "Şirvanlı g/p",
    "Şimal Ərazi BGİ": "Şimal Ərazi Baş Gömrük İdarəsi",
    "Qırmızı körpü": "Qırmızı körpü g/p",
    "Mazımçay": "Mazımçay g/p",
    "Mazımqara": "Mazımqara g/p",
    "Eyvazl": "Eyvazlı gömrük postu",
    "Eyvazlı": "Eyvazlı gömrük postu",
    "BDT Limanı": "Beynəlxalq Dəniz Ticarət Limanı g/p",
    "Beynəlxalq Dəniz Ticarət Limanı": "Beynəlxalq Dəniz Ticarət Limanı g/p",
    "ERDN BGİ": "Dəniz nəqliyyatı və Enerji resursları Baş Gömrük İdarəsi",
    "Astara": "Astara g/p",
    "Biləsuvar": "Biləsuvar g/p",
    "Lənkəran": "Lənkəran g/p",
    "Astara modul": "Astara modul tipli g/p",
    "Cənub-Astara": "Cənub-Astara g/p",
    "Qoşa təpə g/p": "Qoşa təpə g/p",
    "Şahtaxtı": "Şahtaxtı g/p",
    "Culfa": "Culfa g/p",
    "Sədərək": "Sədərək g/p",
    "Tovuz": "Tovuz g/p",
    "Balakən": "Balakən g/p",
    "Gəncə": "Gəncə G/İ",
    "Kürdəmir": "Kürdəmir g/p",
    "Şəki": "Şəki g/p",
    "Yevlax": "Yevlax g/p",
    "Qəbələ": "Qəbələ g/p",
    "Sumqayıt": "Sumqayıt Gİ",
    "Xocahəsən": "Xocahəsən g/p",
    "Xocəsən": "Xocəsən g/p",
    "Şirvan": "Şirvan g/p",
}


def quote_name(name):
    return connection.ops.quote_name(name)


def qualified_name(schema, table):
    return f"{quote_name(schema)}.{quote_name(table)}"


def normalize_customs_name(value):
    if pd.isna(value):
        return None

    text = str(value).strip()
    if not text:
        return None

    return CUSTOMS_ALIASES.get(text, text)


def compass_point_for_customs_name(value):
    # Match customs names after normalizing known shortened or misspelled forms.
    normalized_value = normalize_customs_name(value)
    if normalized_value is None:
        return OTHER_COMPASS_POINT

    for compass_point, customs_names in COMPASS_POINT_CUSTOMS.items():
        if normalized_value in customs_names:
            return compass_point

    return OTHER_COMPASS_POINT


def border_customs_for_customs_name(value):
    normalized_value = normalize_customs_name(value)
    if normalized_value in FOREIGN_BORDER_CUSTOMS:
        return BORDER_CUSTOMS_YES
    return BORDER_CUSTOMS_NO


def add_compass_point_column(source_df):
    # Create review-friendly customs dimensions. Unknown compass points stay
    # Digər, while Sərhəd postu is a Bəli/Xeyr flag.
    source_df = source_df.copy()
    source_df[COMPASS_POINT_COLUMN] = source_df[CUST_NAME_COLUMN].map(
        compass_point_for_customs_name,
    )
    source_df[BORDER_CUSTOMS_COLUMN] = source_df[CUST_NAME_COLUMN].map(
        border_customs_for_customs_name,
    )
    return source_df


def read_unique_foreign_customs_names():
    query = f"""
        SELECT DISTINCT {quote_name(CUST_NAME_COLUMN)}
        FROM {qualified_name(FOREIGN_SCHEMA, FOREIGN_MERGED_TABLE)}
        WHERE {quote_name(CUST_NAME_COLUMN)} IS NOT NULL
          AND btrim({quote_name(CUST_NAME_COLUMN)}::text) <> ''
        ORDER BY {quote_name(CUST_NAME_COLUMN)}
    """
    return pd.read_sql_query(query, connection)[CUST_NAME_COLUMN].tolist()


def read_unique_merged_customs_names():
    query = f"""
        SELECT DISTINCT {quote_name(CUST_NAME_COLUMN)}
        FROM (
            SELECT {quote_name(CUST_NAME_COLUMN)}
            FROM {qualified_name(LOCAL_SCHEMA, LOCAL_MERGED_TABLE)}
            UNION
            SELECT {quote_name(CUST_NAME_COLUMN)}
            FROM {qualified_name(FOREIGN_SCHEMA, FOREIGN_MERGED_TABLE)}
        ) merged_customs
        WHERE {quote_name(CUST_NAME_COLUMN)} IS NOT NULL
          AND btrim({quote_name(CUST_NAME_COLUMN)}::text) <> ''
        ORDER BY {quote_name(CUST_NAME_COLUMN)}
    """
    return pd.read_sql_query(query, connection)[CUST_NAME_COLUMN].tolist()


def group_customs_by_compass_point(customs_names=None):
    # Returns exact unique CUST_NAME values grouped by compass point. Any values
    # not recognized by the corrected lists above go into Digər.
    if customs_names is None:
        customs_names = read_unique_merged_customs_names()

    grouped_customs = {compass_point: [] for compass_point in COMPASS_POINT_CUSTOMS.keys()}

    for customs_name in customs_names:
        compass_point = compass_point_for_customs_name(customs_name)
        grouped_customs[compass_point].append(customs_name)

    return grouped_customs


def group_foreign_customs_by_compass_point(customs_names=None):
    # Backward-compatible helper for callers that only want foreign CUST_NAME
    # values grouped by the same compass point categories.
    if customs_names is None:
        customs_names = read_unique_foreign_customs_names()
    return group_customs_by_compass_point(customs_names)
