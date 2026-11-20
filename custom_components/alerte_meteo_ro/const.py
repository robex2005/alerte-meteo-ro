"""Constante pentru integrarea Alerte Meteo România (ANM + nowcasting)."""

DOMAIN = "alerte_meteo_ro"
NAME = "Alerte Meteo România"

# Configuration
CONF_API_URL = "api_url"
CONF_COUNTIES = "counties"  # județele pentru nowcasting
CONF_JUDET_COD = "judet_cod"  # județul pentru avertizările ANM (cod auto, ex. MS)
CONF_UPDATE_INTERVAL = "update_interval"  # minute, avertizări ANM
CONF_NOWCASTING = "nowcasting"  # activează senzorii nowcasting
# Notificări prin aplicația companion
CONF_NOTIFY_SERVICES = "notify_services"  # listă notify.mobile_app_*
CONF_NOTIFY_MIN_LEVEL = "notify_min_level"  # galben / portocaliu / rosu
CONF_NOTIFY_ANM = "notify_anm"
CONF_NOTIFY_NOWCASTING = "notify_nowcasting"
CONF_NOTIFY_END = "notify_end"
CONF_NOTIFY_TEXT = "notify_text_services"  # alte servicii notify (ex. WhatsApp), doar text
CONF_NOTIFY_URL = "notify_url"  # dashboard deschis la apăsarea notificării
DEFAULT_API_URL ="https://www.meteoromania.ro/avertizari-nowcasting-xml.php"
DEFAULT_ANM_INTERVAL = 10  # minute

# Județele României cu abrevierile oficiale (avertizări ANM)
JUDETE = {
    "AB": "Alba",
    "AR": "Arad",
    "AG": "Argeș",
    "BC": "Bacău",
    "BH": "Bihor",
    "BN": "Bistrița-Năsăud",
    "BT": "Botoșani",
    "BR": "Brăila",
    "BV": "Brașov",
    "B": "București",
    "BZ": "Buzău",
    "CL": "Călărași",
    "CS": "Caraș-Severin",
    "CJ": "Cluj",
    "CT": "Constanța",
    "CV": "Covasna",
    "DB": "Dâmbovița",
    "DJ": "Dolj",
    "GL": "Galați",
    "GR": "Giurgiu",
    "GJ": "Gorj",
    "HR": "Harghita",
    "HD": "Hunedoara",
    "IL": "Ialomița",
    "IS": "Iași",
    "IF": "Ilfov",
    "MM": "Maramureș",
    "MH": "Mehedinți",
    "MS": "Mureș",
    "NT": "Neamț",
    "OT": "Olt",
    "PH": "Prahova",
    "SJ": "Sălaj",
    "SM": "Satu Mare",
    "SB": "Sibiu",
    "SV": "Suceava",
    "TR": "Teleorman",
    "TM": "Timiș",
    "TL": "Tulcea",
    "VL": "Vâlcea",
    "VS": "Vaslui",
    "VN": "Vrancea",
}

# Defaults
DEFAULT_SCAN_INTERVAL = 300  # 5 minute
DEFAULT_NAME = "Alerta Nowcasting"

# Atribute senzor
ATTR_ALERTS = "alerts"
ATTR_ACTIVE_ALERTS = "active_alerts"
ATTR_COUNTIES = "counties"
ATTR_PHENOMENA = "phenomena"
ATTR_START_TIME = "start_time"
ATTR_END_TIME = "end_time"
ATTR_SEVERITY = "severity"
ATTR_DESCRIPTION = "description"
ATTR_LAST_UPDATE = "last_update"

# Tipuri fenomene
PHENOMENA_TYPES = {
    "ceata": "Ceață",
    "polei": "Polei",
    "ninsoare": "Ninsoare abundentă",
    "viscol": "Viscol",
    "ploi_torentiale": "Ploi torențiale",
    "grindina": "Grindină",
    "vijelie": "Vijelie",
    "fulger": "Descărcări electrice frecvente",
    "vant_puternic": "Vânt puternic",
    "instabilitate": "Instabilitate atmosferică",
}

# Niveluri severitate
SEVERITY_LEVELS = {
    "galben": "yellow",
    "portocaliu": "orange",
    "rosu": "red",
}

# Mapare coduri culoare din API
COLOR_CODES = {
    "0": "galben",
    "1": "portocaliu",
    "2": "rosu",
}

# Tipuri mesaje din API
MESSAGE_TYPES = {
    "1": "Avertizare nowcasting",
    "2": "Atentionare nowcasting",
    "3": "Informare nowcasting",
}

# Iconițe pentru diferite fenomene
PHENOMENA_ICONS = {
    "ceata": "mdi:weather-fog",
    "polei": "mdi:snowflake-melt",
    "ninsoare": "mdi:weather-snowy-heavy",
    "viscol": "mdi:weather-snowy",
    "ploi_torentiale": "mdi:weather-pouring",
    "grindina": "mdi:weather-hail",
    "vijelie": "mdi:weather-hurricane",
    "fulger": "mdi:weather-lightning",
    "vant_puternic": "mdi:weather-windy",
    "instabilitate": "mdi:alert-circle",
    "default": "mdi:weather-cloudy-alert",
}

# Lista județelor din România
ROMANIAN_COUNTIES = [
    "Alba",
    "Arad",
    "Argeș",
    "Bacău",
    "Bihor",
    "Bistrița-Năsăud",
    "Botoșani",
    "Brașov",
    "Brăila",
    "București",
    "Buzău",
    "Caraș-Severin",
    "Călărași",
    "Cluj",
    "Constanța",
    "Covasna",
    "Dâmbovița",
    "Dolj",
    "Galați",
    "Giurgiu",
    "Gorj",
    "Harghita",
    "Hunedoara",
    "Ialomița",
    "Iași",
    "Ilfov",
    "Maramureș",
    "Mehedinți",
    "Mureș",
    "Neamț",
    "Olt",
    "Prahova",
    "Satu Mare",
    "Sălaj",
    "Sibiu",
    "Suceava",
    "Teleorman",
    "Timiș",
    "Tulcea",
    "Vaslui",
    "Vâlcea",
    "Vrancea",
]
