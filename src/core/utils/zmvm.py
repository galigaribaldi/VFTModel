"""
@author: Hernán Galileo Cabrera Garibaldi
@description: Catálogo oficial de demarcaciones de la Zona Metropolitana del Valle de México (ZMVM).
@route: src/core/utils/zmvm.py
@notes: Delimitación SEDATU-CONAPO-INEGI: 16 alcaldías de la CDMX, 59 municipios del
        Estado de México y 1 municipio de Hidalgo = 76 demarcaciones (Issue #26).
        Se usa como dominio ADICIONAL de cobertura; no reemplaza al dominio por entidades.
        Claves CVEGEO de INEGI (entidad 2 dígitos + municipio 3 dígitos).
"""

# Entidades federativas que aportan demarcaciones a la ZMVM
ZMVM_ENTIDADES = ["Ciudad de México", "Estado de México", "Hidalgo"]

ZMVM_CVEGEO_CDMX = frozenset([
    "09002",  # Azcapotzalco
    "09003",  # Coyoacán
    "09004",  # Cuajimalpa de Morelos
    "09005",  # Gustavo A. Madero
    "09006",  # Iztacalco
    "09007",  # Iztapalapa
    "09008",  # La Magdalena Contreras
    "09009",  # Milpa Alta
    "09010",  # Álvaro Obregón
    "09011",  # Tláhuac
    "09012",  # Tlalpan
    "09013",  # Xochimilco
    "09014",  # Benito Juárez
    "09015",  # Cuauhtémoc
    "09016",  # Miguel Hidalgo
    "09017",  # Venustiano Carranza
])

ZMVM_CVEGEO_MEXICO = frozenset([
    "15002",  # Acolman
    "15009",  # Amecameca
    "15010",  # Apaxco
    "15011",  # Atenco
    "15013",  # Atizapán de Zaragoza
    "15015",  # Atlautla
    "15016",  # Axapusco
    "15017",  # Ayapango
    "15020",  # Coacalco de Berriozábal
    "15022",  # Cocotitlán
    "15023",  # Coyotepec
    "15024",  # Cuautitlán
    "15025",  # Chalco
    "15028",  # Chiautla
    "15029",  # Chicoloapan
    "15030",  # Chiconcuac
    "15031",  # Chimalhuacán
    "15033",  # Ecatepec de Morelos
    "15034",  # Ecatzingo
    "15035",  # Huehuetoca
    "15036",  # Hueypoxtla
    "15037",  # Huixquilucan
    "15038",  # Isidro Fabela
    "15039",  # Ixtapaluca
    "15044",  # Jaltenco
    "15046",  # Jilotzingo
    "15050",  # Juchitepec
    "15053",  # Melchor Ocampo
    "15057",  # Naucalpan de Juárez
    "15058",  # Nezahualcóyotl
    "15059",  # Nextlalpan
    "15060",  # Nicolás Romero
    "15061",  # Nopaltepec
    "15065",  # Otumba
    "15068",  # Ozumba
    "15069",  # Papalotla
    "15070",  # La Paz
    "15075",  # San Martín de las Pirámides
    "15081",  # Tecámac
    "15083",  # Temamatla
    "15084",  # Temascalapa
    "15089",  # Tenango del Aire
    "15091",  # Teoloyucan
    "15092",  # Teotihuacán
    "15093",  # Tepetlaoxtoc
    "15094",  # Tepetlixpa
    "15095",  # Tepotzotlán
    "15096",  # Tequixquiac
    "15099",  # Texcoco
    "15100",  # Tezoyuca
    "15103",  # Tlalmanalco
    "15104",  # Tlalnepantla de Baz
    "15108",  # Tultepec
    "15109",  # Tultitlán
    "15112",  # Villa del Carbón
    "15120",  # Zumpango
    "15121",  # Cuautitlán Izcalli
    "15122",  # Valle de Chalco Solidaridad
    "15125",  # Tonanitla
])

ZMVM_CVEGEO_HIDALGO = frozenset([
    "13069",  # Tizayuca
])

ZMVM_CVEGEO = ZMVM_CVEGEO_CDMX | ZMVM_CVEGEO_MEXICO | ZMVM_CVEGEO_HIDALGO

assert len(ZMVM_CVEGEO) == 76, "La ZMVM oficial tiene 76 demarcaciones"
