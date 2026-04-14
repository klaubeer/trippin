"""
Endpoint de busca de cidades/aeroportos para o autocomplete do formulário.

Por que airportsdata em vez de lista hardcoded?
- Cobre ~7.800 aeroportos com IATA — sem manutenção de lista
- Carregado uma vez no startup, servido em memória (<1ms por busca)
- Dados ricos: cidade, país (ISO), coordenadas, fuso horário
- Lista hardcoded de 1000+ seria impraticável de manter atualizada

Estratégia de nomes em português:
- Override map cobre os ~200 destinos mais buscados por brasileiros
  com nomes na forma esperada (Lisboa, não Lisbon; Tóquio, não Tokyo)
- Para o restante, usa o nome inglês do airportsdata
- Busca funciona nos dois — "Lisboa" e "Lisbon" retornam LIS

Fluxo de prioridade:
1. Amadeus API (se configurada) — dados em tempo real
2. airportsdata (fallback) — cobertura total sem dependência externa
"""
from fastapi import APIRouter, Query
import httpx

from config import configuracoes

roteador_locais = APIRouter(prefix="/locais", tags=["locais"])

AMADEUS_TOKEN_URL = "https://test.api.amadeus.com/v1/security/oauth2/token"
AMADEUS_LOCAIS_URL = "https://test.api.amadeus.com/v1/reference-data/locations"

# Nomes em português para os principais destinos — overrides do nome inglês do airportsdata
# Formato: iata -> (nome_pt, pais_pt)
OVERRIDES_PT: dict[str, tuple[str, str]] = {
    # Brasil
    "GRU": ("São Paulo", "Brasil"),
    "CGH": ("São Paulo (Congonhas)", "Brasil"),
    "VCP": ("Campinas", "Brasil"),
    "GIG": ("Rio de Janeiro (Galeão)", "Brasil"),
    "SDU": ("Rio de Janeiro (Santos Dumont)", "Brasil"),
    "BSB": ("Brasília", "Brasil"),
    "SSA": ("Salvador", "Brasil"),
    "FOR": ("Fortaleza", "Brasil"),
    "REC": ("Recife", "Brasil"),
    "CNF": ("Belo Horizonte", "Brasil"),
    "MAO": ("Manaus", "Brasil"),
    "POA": ("Porto Alegre", "Brasil"),
    "CWB": ("Curitiba", "Brasil"),
    "BEL": ("Belém", "Brasil"),
    "FLN": ("Florianópolis", "Brasil"),
    "NAT": ("Natal", "Brasil"),
    "MCZ": ("Maceió", "Brasil"),
    "GYN": ("Goiânia", "Brasil"),
    "THE": ("Teresina", "Brasil"),
    "JPA": ("João Pessoa", "Brasil"),
    "AJU": ("Aracaju", "Brasil"),
    "CGR": ("Campo Grande", "Brasil"),
    "CGB": ("Cuiabá", "Brasil"),
    "PVH": ("Porto Velho", "Brasil"),
    "RBR": ("Rio Branco", "Brasil"),
    "STM": ("Santarém", "Brasil"),
    "IMP": ("Imperatriz", "Brasil"),
    "MCP": ("Macapá", "Brasil"),
    "BVB": ("Boa Vista", "Brasil"),
    "PMW": ("Palmas", "Brasil"),
    "VDC": ("Vitória da Conquista", "Brasil"),
    "VIX": ("Vitória", "Brasil"),
    "UDI": ("Uberlândia", "Brasil"),
    "CFB": ("Cabo Frio", "Brasil"),
    "IOS": ("Ilhéus", "Brasil"),
    "LDB": ("Londrina", "Brasil"),
    "IGU": ("Foz do Iguaçu", "Brasil"),
    "MII": ("Marília", "Brasil"),
    "PPB": ("Presidente Prudente", "Brasil"),
    "RAO": ("Ribeirão Preto", "Brasil"),
    "JOI": ("Joinville", "Brasil"),
    "NVT": ("Navegantes", "Brasil"),
    "XAP": ("Chapecó", "Brasil"),
    "PFB": ("Passo Fundo", "Brasil"),
    "GEL": ("Santo Ângelo", "Brasil"),
    "BPS": ("Porto Seguro", "Brasil"),
    "TOW": ("Toledo", "Brasil"),
    "PMG": ("Ponta Porã", "Brasil"),
    "CXJ": ("Caxias do Sul", "Brasil"),
    "BHZ": ("Belo Horizonte (Pampulha)", "Brasil"),
    # Europa
    "LIS": ("Lisboa", "Portugal"),
    "OPO": ("Porto", "Portugal"),
    "FAO": ("Faro", "Portugal"),
    "MAD": ("Madri", "Espanha"),
    "BCN": ("Barcelona", "Espanha"),
    "AGP": ("Málaga", "Espanha"),
    "PMI": ("Palma de Mallorca", "Espanha"),
    "CDG": ("Paris (Charles de Gaulle)", "França"),
    "ORY": ("Paris (Orly)", "França"),
    "NCE": ("Nice", "França"),
    "LYS": ("Lyon", "França"),
    "MRS": ("Marselha", "França"),
    "LHR": ("Londres (Heathrow)", "Reino Unido"),
    "LGW": ("Londres (Gatwick)", "Reino Unido"),
    "STN": ("Londres (Stansted)", "Reino Unido"),
    "LTN": ("Londres (Luton)", "Reino Unido"),
    "MAN": ("Manchester", "Reino Unido"),
    "EDI": ("Edimburgo", "Reino Unido"),
    "FCO": ("Roma (Fiumicino)", "Itália"),
    "CIA": ("Roma (Ciampino)", "Itália"),
    "MXP": ("Milão (Malpensa)", "Itália"),
    "LIN": ("Milão (Linate)", "Itália"),
    "VCE": ("Veneza", "Itália"),
    "FLR": ("Florença", "Itália"),
    "NAP": ("Nápoles", "Itália"),
    "BLQ": ("Bolonha", "Itália"),
    "FRA": ("Frankfurt", "Alemanha"),
    "MUC": ("Munique", "Alemanha"),
    "TXL": ("Berlim (Tegel)", "Alemanha"),
    "BER": ("Berlim", "Alemanha"),
    "DUS": ("Düsseldorf", "Alemanha"),
    "HAM": ("Hamburgo", "Alemanha"),
    "CGN": ("Colônia", "Alemanha"),
    "STR": ("Stuttgart", "Alemanha"),
    "AMS": ("Amsterdã", "Holanda"),
    "EIN": ("Eindhoven", "Holanda"),
    "BRU": ("Bruxelas", "Bélgica"),
    "ZRH": ("Zurique", "Suíça"),
    "GVA": ("Genebra", "Suíça"),
    "BSL": ("Basileia", "Suíça"),
    "VIE": ("Viena", "Áustria"),
    "PRG": ("Praga", "República Tcheca"),
    "BUD": ("Budapeste", "Hungria"),
    "WAW": ("Varsóvia", "Polônia"),
    "KRK": ("Cracóvia", "Polônia"),
    "CPH": ("Copenhague", "Dinamarca"),
    "ARN": ("Estocolmo", "Suécia"),
    "HEL": ("Helsinque", "Finlândia"),
    "OSL": ("Oslo", "Noruega"),
    "DUB": ("Dublin", "Irlanda"),
    "ATH": ("Atenas", "Grécia"),
    "SKG": ("Tessalônica", "Grécia"),
    "HER": ("Heraklion (Creta)", "Grécia"),
    "RHO": ("Rodes", "Grécia"),
    "OTP": ("Bucareste", "Romênia"),
    "SOF": ("Sófia", "Bulgária"),
    "LJU": ("Liubliana", "Eslovênia"),
    "ZAG": ("Zagreb", "Croácia"),
    "SPU": ("Split", "Croácia"),
    "DBV": ("Dubrovnik", "Croácia"),
    "BEG": ("Belgrado", "Sérvia"),
    "TBS": ("Tbilisi", "Geórgia"),
    "EVN": ("Yerevan", "Armênia"),
    "RIX": ("Riga", "Letônia"),
    "TLL": ("Tallinn", "Estônia"),
    "VNO": ("Vilnius", "Lituânia"),
    "IST": ("Istambul", "Turquia"),
    "SAW": ("Istambul (Sabiha)", "Turquia"),
    "ESB": ("Ancara", "Turquia"),
    "AYT": ("Antalya", "Turquia"),
    "BJV": ("Bodrum", "Turquia"),
    "DLM": ("Dalaman", "Turquia"),
    "LCA": ("Larnaca (Chipre)", "Chipre"),
    "TLV": ("Tel Aviv", "Israel"),
    # América do Norte
    "JFK": ("Nova York (JFK)", "Estados Unidos"),
    "EWR": ("Nova York (Newark)", "Estados Unidos"),
    "LGA": ("Nova York (LaGuardia)", "Estados Unidos"),
    "MIA": ("Miami", "Estados Unidos"),
    "FLL": ("Fort Lauderdale", "Estados Unidos"),
    "MCO": ("Orlando", "Estados Unidos"),
    "LAX": ("Los Angeles", "Estados Unidos"),
    "SFO": ("São Francisco", "Estados Unidos"),
    "SEA": ("Seattle", "Estados Unidos"),
    "ORD": ("Chicago (O'Hare)", "Estados Unidos"),
    "MDW": ("Chicago (Midway)", "Estados Unidos"),
    "ATL": ("Atlanta", "Estados Unidos"),
    "DFW": ("Dallas", "Estados Unidos"),
    "IAH": ("Houston", "Estados Unidos"),
    "DEN": ("Denver", "Estados Unidos"),
    "PHX": ("Phoenix", "Estados Unidos"),
    "LAS": ("Las Vegas", "Estados Unidos"),
    "MSP": ("Minneapolis", "Estados Unidos"),
    "DTW": ("Detroit", "Estados Unidos"),
    "BOS": ("Boston", "Estados Unidos"),
    "DCA": ("Washington (Reagan)", "Estados Unidos"),
    "IAD": ("Washington (Dulles)", "Estados Unidos"),
    "PHL": ("Filadélfia", "Estados Unidos"),
    "CLT": ("Charlotte", "Estados Unidos"),
    "TPA": ("Tampa", "Estados Unidos"),
    "SAN": ("San Diego", "Estados Unidos"),
    "PDX": ("Portland", "Estados Unidos"),
    "HNL": ("Honolulu", "Estados Unidos"),
    "ANC": ("Anchorage", "Estados Unidos"),
    "MSY": ("Nova Orleans", "Estados Unidos"),
    "SLC": ("Salt Lake City", "Estados Unidos"),
    "YYZ": ("Toronto", "Canadá"),
    "YVR": ("Vancouver", "Canadá"),
    "YUL": ("Montreal", "Canadá"),
    "YOW": ("Ottawa", "Canadá"),
    "YEG": ("Edmonton", "Canadá"),
    "YYC": ("Calgary", "Canadá"),
    "CUN": ("Cancún", "México"),
    "MEX": ("Cidade do México", "México"),
    "GDL": ("Guadalajara", "México"),
    "MTY": ("Monterrey", "México"),
    "PVR": ("Puerto Vallarta", "México"),
    "SJD": ("Los Cabos", "México"),
    "HMO": ("Hermosillo", "México"),
    # América do Sul
    "EZE": ("Buenos Aires (Ezeiza)", "Argentina"),
    "AEP": ("Buenos Aires (Aeroparque)", "Argentina"),
    "COR": ("Córdoba", "Argentina"),
    "MDZ": ("Mendoza", "Argentina"),
    "BRC": ("Bariloche", "Argentina"),
    "IGR": ("Puerto Iguazú", "Argentina"),
    "USH": ("Ushuaia", "Argentina"),
    "SCL": ("Santiago", "Chile"),
    "LIM": ("Lima", "Peru"),
    "CUZ": ("Cusco", "Peru"),
    "BOG": ("Bogotá", "Colômbia"),
    "MDE": ("Medellín", "Colômbia"),
    "CTG": ("Cartagena", "Colômbia"),
    "MVD": ("Montevidéu", "Uruguai"),
    "PDP": ("Punta del Este", "Uruguai"),
    "ASU": ("Assunção", "Paraguai"),
    "LPB": ("La Paz", "Bolívia"),
    "VVI": ("Santa Cruz de la Sierra", "Bolívia"),
    "UIO": ("Quito", "Equador"),
    "GYE": ("Guayaquil", "Equador"),
    "GEO": ("Georgetown", "Guiana"),
    "CCS": ("Caracas", "Venezuela"),
    "GUA": ("Cidade da Guatemala", "Guatemala"),
    "SAL": ("San Salvador", "El Salvador"),
    "MGA": ("Manágua", "Nicarágua"),
    "SJO": ("San José", "Costa Rica"),
    "PTY": ("Cidade do Panamá", "Panamá"),
    "HAV": ("Havana", "Cuba"),
    "NAS": ("Nassau", "Bahamas"),
    "MBJ": ("Montego Bay", "Jamaica"),
    "KIN": ("Kingston", "Jamaica"),
    "PUJ": ("Punta Cana", "Rep. Dominicana"),
    "SDQ": ("Santo Domingo", "Rep. Dominicana"),
    "SXM": ("Sint Maarten", "Sint Maarten"),
    "AUA": ("Aruba", "Aruba"),
    "CUR": ("Curaçao", "Curaçao"),
    "BGI": ("Bridgetown (Barbados)", "Barbados"),
    # Ásia
    "NRT": ("Tóquio (Narita)", "Japão"),
    "HND": ("Tóquio (Haneda)", "Japão"),
    "KIX": ("Osaka", "Japão"),
    "ITM": ("Osaka (Itami)", "Japão"),
    "CTS": ("Sapporo", "Japão"),
    "FUK": ("Fukuoka", "Japão"),
    "OKA": ("Okinawa", "Japão"),
    "ICN": ("Seul (Incheon)", "Coreia do Sul"),
    "GMP": ("Seul (Gimpo)", "Coreia do Sul"),
    "PUS": ("Busan", "Coreia do Sul"),
    "PEK": ("Pequim", "China"),
    "PKX": ("Pequim (Daxing)", "China"),
    "PVG": ("Xangai (Pudong)", "China"),
    "SHA": ("Xangai (Hongqiao)", "China"),
    "CAN": ("Guangzhou", "China"),
    "SZX": ("Shenzhen", "China"),
    "CTU": ("Chengdu", "China"),
    "HKG": ("Hong Kong", "Hong Kong"),
    "MFM": ("Macau", "Macau"),
    "TPE": ("Taipei", "Taiwan"),
    "KHH": ("Kaohsiung", "Taiwan"),
    "BKK": ("Bangkok (Suvarnabhumi)", "Tailândia"),
    "DMK": ("Bangkok (Don Mueang)", "Tailândia"),
    "HKT": ("Phuket", "Tailândia"),
    "CNX": ("Chiang Mai", "Tailândia"),
    "KBV": ("Krabi", "Tailândia"),
    "SIN": ("Cingapura", "Singapura"),
    "KUL": ("Kuala Lumpur", "Malásia"),
    "CGK": ("Jacarta", "Indonésia"),
    "DPS": ("Bali (Denpasar)", "Indonésia"),
    "SUB": ("Surabaya", "Indonésia"),
    "MNL": ("Manila", "Filipinas"),
    "CEB": ("Cebu", "Filipinas"),
    "SGN": ("Cidade Ho Chi Minh", "Vietnã"),
    "HAN": ("Hanói", "Vietnã"),
    "DAD": ("Da Nang", "Vietnã"),
    "PNH": ("Phnom Penh", "Camboja"),
    "REP": ("Siem Reap (Angkor)", "Camboja"),
    "RGN": ("Yangon", "Mianmar"),
    "VTE": ("Vientiane", "Laos"),
    "CMB": ("Colombo", "Sri Lanka"),
    "DEL": ("Nova Delhi", "Índia"),
    "BOM": ("Mumbai", "Índia"),
    "BLR": ("Bangalore", "Índia"),
    "MAA": ("Chennai", "Índia"),
    "CCU": ("Calcutá", "Índia"),
    "HYD": ("Hyderabad", "Índia"),
    "COK": ("Kochi", "Índia"),
    "GOI": ("Goa", "Índia"),
    "KTM": ("Katmandu", "Nepal"),
    "DAC": ("Daca", "Bangladesh"),
    "KHI": ("Karachi", "Paquistão"),
    "ISB": ("Islamabad", "Paquistão"),
    "LHE": ("Lahore", "Paquistão"),
    "AMD": ("Ahmedabad", "Índia"),
    # Oriente Médio
    "DXB": ("Dubai", "Emirados Árabes"),
    "AUH": ("Abu Dhabi", "Emirados Árabes"),
    "SHJ": ("Sharjah", "Emirados Árabes"),
    "DOH": ("Doha", "Qatar"),
    "BAH": ("Manama (Bahrein)", "Bahrein"),
    "KWI": ("Kuwait City", "Kuwait"),
    "MCT": ("Mascate", "Omã"),
    "RUH": ("Riad", "Arábia Saudita"),
    "JED": ("Jeddah", "Arábia Saudita"),
    "AMM": ("Amã", "Jordânia"),
    "BEY": ("Beirute", "Líbano"),
    "BGW": ("Bagdá", "Iraque"),
    "IKA": ("Teerã", "Irã"),
    "THR": ("Teerã (Mehrabad)", "Irã"),
    "CAI": ("Cairo", "Egito"),
    "HRG": ("Hurghada", "Egito"),
    "SSH": ("Sharm el-Sheikh", "Egito"),
    "LXR": ("Luxor", "Egito"),
    # África
    "JNB": ("Joanesburgo", "África do Sul"),
    "CPT": ("Cidade do Cabo", "África do Sul"),
    "DUR": ("Durban", "África do Sul"),
    "NBO": ("Nairóbi", "Quênia"),
    "MBA": ("Mombasa", "Quênia"),
    "EBB": ("Entebbe (Uganda)", "Uganda"),
    "DAR": ("Dar es Salaam", "Tanzânia"),
    "JRO": ("Kilimanjaro", "Tanzânia"),
    "ZNZ": ("Zanzibar", "Tanzânia"),
    "ADD": ("Adis Abeba", "Etiópia"),
    "LOS": ("Lagos", "Nigéria"),
    "ABV": ("Abuja", "Nigéria"),
    "ACC": ("Acra", "Gana"),
    "ABJ": ("Abidjan", "Costa do Marfim"),
    "CMN": ("Casablanca", "Marrocos"),
    "RAK": ("Marrakech", "Marrocos"),
    "FEZ": ("Fez", "Marrocos"),
    "TNG": ("Tânger", "Marrocos"),
    "ALG": ("Argel", "Argélia"),
    "TUN": ("Túnis", "Tunísia"),
    "TIP": ("Trípoli", "Líbia"),
    "KRT": ("Cartum", "Sudão"),
    "MRU": ("Maurício", "Maurício"),
    "SEZ": ("Mahé (Seychelles)", "Seychelles"),
    "TNR": ("Antananarivo", "Madagascar"),
    "RUN": ("Reunião", "Reunião"),
    "MPM": ("Maputo", "Moçambique"),
    "LAD": ("Luanda", "Angola"),
    "DKR": ("Dakar", "Senegal"),
    # Oceania
    "SYD": ("Sydney", "Austrália"),
    "MEL": ("Melbourne", "Austrália"),
    "BNE": ("Brisbane", "Austrália"),
    "PER": ("Perth", "Austrália"),
    "ADL": ("Adelaide", "Austrália"),
    "DRW": ("Darwin", "Austrália"),
    "OOL": ("Gold Coast", "Austrália"),
    "CBR": ("Canberra", "Austrália"),
    "AKL": ("Auckland", "Nova Zelândia"),
    "CHC": ("Christchurch", "Nova Zelândia"),
    "WLG": ("Wellington", "Nova Zelândia"),
    "NAN": ("Nadi (Fiji)", "Fiji"),
    "PPT": ("Papeete (Taiti)", "Polinésia Francesa"),
    "NOU": ("Nouméa", "Nova Caledônia"),
    "HIR": ("Honiara", "Ilhas Salomão"),
    "APW": ("Apia (Samoa)", "Samoa"),
    "TBU": ("Nuku'alofa (Tonga)", "Tonga"),
}

# Mapa de países ISO → PT para os aeroportos sem override
PAISES_PT: dict[str, str] = {
    "AF": "Afeganistão", "AL": "Albânia", "DZ": "Argélia", "AD": "Andorra",
    "AO": "Angola", "AG": "Antígua e Barbuda", "AR": "Argentina", "AM": "Armênia",
    "AU": "Austrália", "AT": "Áustria", "AZ": "Azerbaijão", "BS": "Bahamas",
    "BH": "Bahrein", "BD": "Bangladesh", "BB": "Barbados", "BY": "Bielorrússia",
    "BE": "Bélgica", "BZ": "Belize", "BJ": "Benin", "BT": "Butão",
    "BO": "Bolívia", "BA": "Bósnia e Herzegovina", "BW": "Botsuana", "BR": "Brasil",
    "BN": "Brunei", "BG": "Bulgária", "BF": "Burkina Faso", "BI": "Burundi",
    "CV": "Cabo Verde", "KH": "Camboja", "CM": "Camarões", "CA": "Canadá",
    "CF": "Rep. Centro-Africana", "TD": "Chade", "CL": "Chile", "CN": "China",
    "CO": "Colômbia", "KM": "Comores", "CG": "Congo", "CD": "R.D. do Congo",
    "CR": "Costa Rica", "CI": "Costa do Marfim", "HR": "Croácia", "CU": "Cuba",
    "CW": "Curaçao", "CY": "Chipre", "CZ": "República Tcheca", "DK": "Dinamarca",
    "DJ": "Djibuti", "DM": "Dominica", "DO": "Rep. Dominicana", "EC": "Equador",
    "EG": "Egito", "SV": "El Salvador", "GQ": "Guiné Equatorial", "ER": "Eritreia",
    "EE": "Estônia", "SZ": "Essuatíni", "ET": "Etiópia", "FJ": "Fiji",
    "FI": "Finlândia", "FR": "França", "GA": "Gabão", "GM": "Gâmbia",
    "GE": "Geórgia", "DE": "Alemanha", "GH": "Gana", "GR": "Grécia",
    "GD": "Granada", "GT": "Guatemala", "GN": "Guiné", "GW": "Guiné-Bissau",
    "GY": "Guiana", "HT": "Haiti", "HN": "Honduras", "HK": "Hong Kong",
    "HU": "Hungria", "IS": "Islândia", "IN": "Índia", "ID": "Indonésia",
    "IR": "Irã", "IQ": "Iraque", "IE": "Irlanda", "IL": "Israel",
    "IT": "Itália", "JM": "Jamaica", "JP": "Japão", "JO": "Jordânia",
    "KZ": "Cazaquistão", "KE": "Quênia", "KI": "Quiribati", "KP": "Coreia do Norte",
    "KR": "Coreia do Sul", "KW": "Kuwait", "KG": "Quirguistão", "LA": "Laos",
    "LV": "Letônia", "LB": "Líbano", "LS": "Lesoto", "LR": "Libéria",
    "LY": "Líbia", "LI": "Liechtenstein", "LT": "Lituânia", "LU": "Luxemburgo",
    "MO": "Macau", "MG": "Madagascar", "MW": "Malawi", "MY": "Malásia",
    "MV": "Maldivas", "ML": "Mali", "MT": "Malta", "MH": "Ilhas Marshall",
    "MR": "Mauritânia", "MU": "Maurício", "MX": "México", "FM": "Micronésia",
    "MD": "Moldávia", "MC": "Mônaco", "MN": "Mongólia", "ME": "Montenegro",
    "MA": "Marrocos", "MZ": "Moçambique", "MM": "Mianmar", "NA": "Namíbia",
    "NR": "Nauru", "NP": "Nepal", "NL": "Holanda", "NZ": "Nova Zelândia",
    "NI": "Nicarágua", "NE": "Níger", "NG": "Nigéria", "NO": "Noruega",
    "OM": "Omã", "PK": "Paquistão", "PW": "Palau", "PA": "Panamá",
    "PG": "Papua Nova Guiné", "PY": "Paraguai", "PE": "Peru", "PH": "Filipinas",
    "PL": "Polônia", "PT": "Portugal", "QA": "Qatar", "RO": "Romênia",
    "RU": "Rússia", "RW": "Ruanda", "KN": "São Cristóvão e Névis",
    "LC": "Santa Lúcia", "VC": "São Vicente e Granadinas", "WS": "Samoa",
    "SM": "San Marino", "ST": "São Tomé e Príncipe", "SA": "Arábia Saudita",
    "SN": "Senegal", "RS": "Sérvia", "SC": "Seychelles", "SL": "Serra Leoa",
    "SG": "Singapura", "SK": "Eslováquia", "SI": "Eslovênia", "SB": "Ilhas Salomão",
    "SO": "Somália", "ZA": "África do Sul", "SS": "Sudão do Sul", "ES": "Espanha",
    "LK": "Sri Lanka", "SD": "Sudão", "SR": "Suriname", "SE": "Suécia",
    "CH": "Suíça", "SY": "Síria", "TW": "Taiwan", "TJ": "Tajiquistão",
    "TZ": "Tanzânia", "TH": "Tailândia", "TL": "Timor-Leste", "TG": "Togo",
    "TO": "Tonga", "TT": "Trinidad e Tobago", "TN": "Tunísia", "TR": "Turquia",
    "TM": "Turcomenistão", "TV": "Tuvalu", "UG": "Uganda", "UA": "Ucrânia",
    "AE": "Emirados Árabes", "GB": "Reino Unido", "US": "Estados Unidos",
    "UY": "Uruguai", "UZ": "Uzbequistão", "VU": "Vanuatu", "VE": "Venezuela",
    "VN": "Vietnã", "YE": "Iêmen", "ZM": "Zâmbia", "ZW": "Zimbábue",
    "AW": "Aruba", "BM": "Bermudas", "KY": "Ilhas Cayman", "GI": "Gibraltar",
    "GL": "Groenlândia", "GP": "Guadalupe", "MQ": "Martinica", "NC": "Nova Caledônia",
    "PF": "Polinésia Francesa", "PR": "Porto Rico", "RE": "Reunião",
    "SX": "Sint Maarten", "TC": "Ilhas Turks e Caicos", "VI": "Ilhas Virgens (EUA)",
}


def _carregar_aeroportos() -> list[dict]:
    """
    Carrega aeroportos do pacote airportsdata, aplica overrides PT e deduplica por cidade.

    Deduplica com prioridade: aeroportos com override PT ficam na frente,
    depois os demais ordenados por IATA (aprox. por relevância).
    """
    try:
        import airportsdata
        todos = airportsdata.load("IATA")
    except ImportError:
        return []

    resultado: list[dict] = []
    vistos_chave: set[str] = set()  # cidade_lower|país_iso

    # Primeiro: adiciona todos que têm override PT (garante que aparecem com o nome correto)
    for iata, (nome_pt, pais_pt) in OVERRIDES_PT.items():
        ap = todos.get(iata)
        if not ap:
            continue
        chave = f"{nome_pt.lower().split('(')[0].strip()}|{ap['country']}"
        if chave not in vistos_chave:
            vistos_chave.add(chave)
            resultado.append({"nome": nome_pt, "iata": iata, "pais": pais_pt, "_alias": ap.get("city", "").lower()})

    # Depois: adiciona os demais com nome inglês, sem duplicar cidade
    for iata, ap in sorted(todos.items()):
        if iata in OVERRIDES_PT:
            continue
        cidade = ap.get("city", "").strip()
        pais_iso = ap.get("country", "")
        if not cidade or not pais_iso:
            continue
        chave = f"{cidade.lower()}|{pais_iso}"
        if chave in vistos_chave:
            continue
        vistos_chave.add(chave)
        pais = PAISES_PT.get(pais_iso, pais_iso)
        resultado.append({"nome": cidade, "iata": iata, "pais": pais, "_alias": ""})

    return resultado


# Carregado uma vez no startup — servido em memória em todas as requisições
_AEROPORTOS = _carregar_aeroportos()


def _obter_token_amadeus() -> str:
    with httpx.Client() as cliente:
        resposta = cliente.post(
            AMADEUS_TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": configuracoes.amadeus_client_id,
                "client_secret": configuracoes.amadeus_client_secret,
            },
            timeout=10,
        )
        resposta.raise_for_status()
        return resposta.json()["access_token"]


def _buscar_amadeus(query: str) -> list[dict]:
    """Consulta Amadeus e retorna lista de {nome, iata, pais}."""
    try:
        token = _obter_token_amadeus()
        with httpx.Client() as cliente:
            resposta = cliente.get(
                AMADEUS_LOCAIS_URL,
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "keyword": query,
                    "subType": "CITY",
                    "page[limit]": 8,
                    "view": "LIGHT",
                },
                timeout=8,
            )
            resposta.raise_for_status()
            dados = resposta.json().get("data", [])

        return [
            {
                "nome": item["address"]["cityName"].title(),
                "iata": item["iataCode"],
                "pais": item["address"].get("countryName", "").title(),
            }
            for item in dados
            if item.get("iataCode") and item.get("address", {}).get("cityName")
        ]
    except Exception:
        return []


def _buscar_estatico(query: str) -> list[dict]:
    """
    Busca nos aeroportos carregados do airportsdata.
    Prioriza resultados que começam com a query, depois os que contêm.
    Também busca no alias (nome inglês) para compatibilidade.
    """
    q = query.lower().strip()
    comeca: list[dict] = []
    contem: list[dict] = []

    for ap in _AEROPORTOS:
        nome_lower = ap["nome"].lower()
        alias_lower = ap.get("_alias", "")
        if nome_lower.startswith(q) or alias_lower.startswith(q):
            comeca.append(ap)
        elif q in nome_lower or (alias_lower and q in alias_lower):
            contem.append(ap)

    resultado = comeca + contem
    # Remove campo interno _alias da resposta
    return [{"nome": a["nome"], "iata": a["iata"], "pais": a["pais"]} for a in resultado[:8]]


@roteador_locais.get("/")
async def buscar_locais(
    q: str = Query(..., min_length=2, description="Nome da cidade"),
) -> list[dict]:
    """
    Retorna sugestões de cidades com seus códigos IATA.

    Prioridade:
    1. Amadeus API (se configurada) — dados em tempo real
    2. airportsdata — ~7800 aeroportos, carregado em memória

    Resposta: [{"nome": "Lisboa", "iata": "LIS", "pais": "Portugal"}]
    """
    if configuracoes.amadeus_client_id:
        resultados = _buscar_amadeus(q)
        if resultados:
            return resultados

    return _buscar_estatico(q)
