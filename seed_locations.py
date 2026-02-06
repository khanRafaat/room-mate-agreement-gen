"""
Seeder script for worldwide countries, states, and cities.
Run after migration to populate location data.

Usage:
    python seed_locations.py
"""
import uuid
import json
import os
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Major countries with their states/provinces and major cities
# This is a representative sample - full data would come from GeoNames or similar
LOCATION_DATA = {
    "US": {
        "name": "United States",
        "states": {
            "AL": {"name": "Alabama", "cities": ["Birmingham", "Montgomery", "Huntsville", "Mobile", "Tuscaloosa"]},
            "AK": {"name": "Alaska", "cities": ["Anchorage", "Fairbanks", "Juneau", "Sitka", "Ketchikan"]},
            "AZ": {"name": "Arizona", "cities": ["Phoenix", "Tucson", "Mesa", "Chandler", "Scottsdale", "Gilbert", "Tempe"]},
            "AR": {"name": "Arkansas", "cities": ["Little Rock", "Fort Smith", "Fayetteville", "Springdale", "Jonesboro"]},
            "CA": {"name": "California", "cities": ["Los Angeles", "San Diego", "San Jose", "San Francisco", "Fresno", "Sacramento", "Long Beach", "Oakland", "Bakersfield", "Anaheim", "Santa Ana", "Riverside", "Stockton", "Irvine"]},
            "CO": {"name": "Colorado", "cities": ["Denver", "Colorado Springs", "Aurora", "Fort Collins", "Lakewood", "Boulder"]},
            "CT": {"name": "Connecticut", "cities": ["Bridgeport", "New Haven", "Hartford", "Stamford", "Waterbury"]},
            "DE": {"name": "Delaware", "cities": ["Wilmington", "Dover", "Newark", "Middletown", "Bear"]},
            "FL": {"name": "Florida", "cities": ["Jacksonville", "Miami", "Tampa", "Orlando", "St. Petersburg", "Hialeah", "Tallahassee", "Fort Lauderdale", "Port St. Lucie", "Cape Coral"]},
            "GA": {"name": "Georgia", "cities": ["Atlanta", "Augusta", "Columbus", "Macon", "Savannah", "Athens", "Sandy Springs"]},
            "HI": {"name": "Hawaii", "cities": ["Honolulu", "Pearl City", "Hilo", "Kailua", "Waipahu"]},
            "ID": {"name": "Idaho", "cities": ["Boise", "Meridian", "Nampa", "Idaho Falls", "Caldwell"]},
            "IL": {"name": "Illinois", "cities": ["Chicago", "Aurora", "Naperville", "Joliet", "Rockford", "Springfield", "Elgin", "Peoria"]},
            "IN": {"name": "Indiana", "cities": ["Indianapolis", "Fort Wayne", "Evansville", "South Bend", "Carmel", "Bloomington"]},
            "IA": {"name": "Iowa", "cities": ["Des Moines", "Cedar Rapids", "Davenport", "Sioux City", "Iowa City"]},
            "KS": {"name": "Kansas", "cities": ["Wichita", "Overland Park", "Kansas City", "Olathe", "Topeka", "Lawrence"]},
            "KY": {"name": "Kentucky", "cities": ["Louisville", "Lexington", "Bowling Green", "Owensboro", "Covington"]},
            "LA": {"name": "Louisiana", "cities": ["New Orleans", "Baton Rouge", "Shreveport", "Lafayette", "Lake Charles"]},
            "ME": {"name": "Maine", "cities": ["Portland", "Lewiston", "Bangor", "South Portland", "Auburn"]},
            "MD": {"name": "Maryland", "cities": ["Baltimore", "Frederick", "Rockville", "Gaithersburg", "Bowie", "Annapolis"]},
            "MA": {"name": "Massachusetts", "cities": ["Boston", "Worcester", "Springfield", "Cambridge", "Lowell", "Brockton"]},
            "MI": {"name": "Michigan", "cities": ["Detroit", "Grand Rapids", "Warren", "Sterling Heights", "Ann Arbor", "Lansing", "Flint"]},
            "MN": {"name": "Minnesota", "cities": ["Minneapolis", "St. Paul", "Rochester", "Duluth", "Bloomington"]},
            "MS": {"name": "Mississippi", "cities": ["Jackson", "Gulfport", "Southaven", "Hattiesburg", "Biloxi"]},
            "MO": {"name": "Missouri", "cities": ["Kansas City", "St. Louis", "Springfield", "Columbia", "Independence"]},
            "MT": {"name": "Montana", "cities": ["Billings", "Missoula", "Great Falls", "Bozeman", "Butte"]},
            "NE": {"name": "Nebraska", "cities": ["Omaha", "Lincoln", "Bellevue", "Grand Island", "Kearney"]},
            "NV": {"name": "Nevada", "cities": ["Las Vegas", "Henderson", "Reno", "North Las Vegas", "Sparks", "Carson City"]},
            "NH": {"name": "New Hampshire", "cities": ["Manchester", "Nashua", "Concord", "Derry", "Rochester"]},
            "NJ": {"name": "New Jersey", "cities": ["Newark", "Jersey City", "Paterson", "Elizabeth", "Edison", "Trenton"]},
            "NM": {"name": "New Mexico", "cities": ["Albuquerque", "Las Cruces", "Rio Rancho", "Santa Fe", "Roswell"]},
            "NY": {"name": "New York", "cities": ["New York City", "Buffalo", "Rochester", "Yonkers", "Syracuse", "Albany"]},
            "NC": {"name": "North Carolina", "cities": ["Charlotte", "Raleigh", "Greensboro", "Durham", "Winston-Salem", "Fayetteville"]},
            "ND": {"name": "North Dakota", "cities": ["Fargo", "Bismarck", "Grand Forks", "Minot", "West Fargo"]},
            "OH": {"name": "Ohio", "cities": ["Columbus", "Cleveland", "Cincinnati", "Toledo", "Akron", "Dayton"]},
            "OK": {"name": "Oklahoma", "cities": ["Oklahoma City", "Tulsa", "Norman", "Broken Arrow", "Lawton"]},
            "OR": {"name": "Oregon", "cities": ["Portland", "Salem", "Eugene", "Gresham", "Hillsboro", "Beaverton"]},
            "PA": {"name": "Pennsylvania", "cities": ["Philadelphia", "Pittsburgh", "Allentown", "Reading", "Scranton", "Erie"]},
            "RI": {"name": "Rhode Island", "cities": ["Providence", "Warwick", "Cranston", "Pawtucket", "East Providence"]},
            "SC": {"name": "South Carolina", "cities": ["Charleston", "Columbia", "North Charleston", "Mount Pleasant", "Greenville"]},
            "SD": {"name": "South Dakota", "cities": ["Sioux Falls", "Rapid City", "Aberdeen", "Brookings", "Watertown"]},
            "TN": {"name": "Tennessee", "cities": ["Nashville", "Memphis", "Knoxville", "Chattanooga", "Clarksville"]},
            "TX": {"name": "Texas", "cities": ["Houston", "San Antonio", "Dallas", "Austin", "Fort Worth", "El Paso", "Arlington", "Corpus Christi", "Plano", "Laredo"]},
            "UT": {"name": "Utah", "cities": ["Salt Lake City", "West Valley City", "Provo", "West Jordan", "Orem", "Sandy"]},
            "VT": {"name": "Vermont", "cities": ["Burlington", "South Burlington", "Rutland", "Barre", "Montpelier"]},
            "VA": {"name": "Virginia", "cities": ["Virginia Beach", "Norfolk", "Chesapeake", "Richmond", "Newport News", "Alexandria"]},
            "WA": {"name": "Washington", "cities": ["Seattle", "Spokane", "Tacoma", "Vancouver", "Bellevue", "Kent", "Everett"]},
            "WV": {"name": "West Virginia", "cities": ["Charleston", "Huntington", "Morgantown", "Parkersburg", "Wheeling"]},
            "WI": {"name": "Wisconsin", "cities": ["Milwaukee", "Madison", "Green Bay", "Kenosha", "Racine"]},
            "WY": {"name": "Wyoming", "cities": ["Cheyenne", "Casper", "Laramie", "Gillette", "Rock Springs"]},
            "DC": {"name": "District of Columbia", "cities": ["Washington"]},
        }
    },
    "BD": {
        "name": "Bangladesh",
        "states": {
            "DHK": {"name": "Dhaka Division", "cities": ["Dhaka", "Gazipur", "Narayanganj", "Tangail", "Narsingdi", "Munshiganj", "Manikganj", "Faridpur"]},
            "CTG": {"name": "Chattogram Division", "cities": ["Chattogram", "Comilla", "Brahmanbaria", "Cox's Bazar", "Chandpur", "Feni", "Noakhali"]},
            "RAJ": {"name": "Rajshahi Division", "cities": ["Rajshahi", "Bogra", "Pabna", "Sirajganj", "Natore", "Naogaon", "Chapainawabganj"]},
            "KHU": {"name": "Khulna Division", "cities": ["Khulna", "Jessore", "Satkhira", "Bagerhat", "Narail", "Kushtia", "Meherpur"]},
            "SYL": {"name": "Sylhet Division", "cities": ["Sylhet", "Moulvibazar", "Habiganj", "Sunamganj"]},
            "BAR": {"name": "Barisal Division", "cities": ["Barisal", "Patuakhali", "Bhola", "Jhalokati", "Pirojpur", "Barguna"]},
            "RNG": {"name": "Rangpur Division", "cities": ["Rangpur", "Dinajpur", "Kurigram", "Nilphamari", "Lalmonirhat", "Gaibandha", "Thakurgaon"]},
            "MYM": {"name": "Mymensingh Division", "cities": ["Mymensingh", "Jamalpur", "Netrokona", "Sherpur"]},
        }
    },
    "GB": {
        "name": "United Kingdom",
        "states": {
            "ENG": {"name": "England", "cities": ["London", "Birmingham", "Manchester", "Liverpool", "Leeds", "Sheffield", "Bristol", "Newcastle", "Nottingham", "Leicester"]},
            "SCT": {"name": "Scotland", "cities": ["Edinburgh", "Glasgow", "Aberdeen", "Dundee", "Inverness"]},
            "WLS": {"name": "Wales", "cities": ["Cardiff", "Swansea", "Newport", "Wrexham", "Barry"]},
            "NIR": {"name": "Northern Ireland", "cities": ["Belfast", "Derry", "Lisburn", "Newry", "Bangor"]},
        }
    },
    "CA": {
        "name": "Canada",
        "states": {
            "ON": {"name": "Ontario", "cities": ["Toronto", "Ottawa", "Mississauga", "Brampton", "Hamilton", "London", "Markham", "Vaughan"]},
            "QC": {"name": "Quebec", "cities": ["Montreal", "Quebec City", "Laval", "Gatineau", "Longueuil", "Sherbrooke"]},
            "BC": {"name": "British Columbia", "cities": ["Vancouver", "Surrey", "Burnaby", "Richmond", "Victoria", "Coquitlam"]},
            "AB": {"name": "Alberta", "cities": ["Calgary", "Edmonton", "Red Deer", "Lethbridge", "Medicine Hat"]},
            "MB": {"name": "Manitoba", "cities": ["Winnipeg", "Brandon", "Steinbach", "Thompson", "Portage la Prairie"]},
            "SK": {"name": "Saskatchewan", "cities": ["Saskatoon", "Regina", "Prince Albert", "Moose Jaw", "Swift Current"]},
            "NS": {"name": "Nova Scotia", "cities": ["Halifax", "Dartmouth", "Sydney", "Truro", "New Glasgow"]},
            "NB": {"name": "New Brunswick", "cities": ["Saint John", "Moncton", "Fredericton", "Dieppe", "Miramichi"]},
            "NL": {"name": "Newfoundland and Labrador", "cities": ["St. John's", "Mount Pearl", "Corner Brook", "Conception Bay South", "Paradise"]},
            "PE": {"name": "Prince Edward Island", "cities": ["Charlottetown", "Summerside", "Stratford", "Cornwall", "Montague"]},
            "NT": {"name": "Northwest Territories", "cities": ["Yellowknife", "Hay River", "Inuvik", "Fort Smith"]},
            "YT": {"name": "Yukon", "cities": ["Whitehorse", "Dawson City", "Watson Lake", "Haines Junction"]},
            "NU": {"name": "Nunavut", "cities": ["Iqaluit", "Rankin Inlet", "Arviat", "Baker Lake"]},
        }
    },
    "AU": {
        "name": "Australia",
        "states": {
            "NSW": {"name": "New South Wales", "cities": ["Sydney", "Newcastle", "Wollongong", "Maitland", "Coffs Harbour"]},
            "VIC": {"name": "Victoria", "cities": ["Melbourne", "Geelong", "Ballarat", "Bendigo", "Shepparton"]},
            "QLD": {"name": "Queensland", "cities": ["Brisbane", "Gold Coast", "Sunshine Coast", "Townsville", "Cairns"]},
            "WA": {"name": "Western Australia", "cities": ["Perth", "Fremantle", "Rockingham", "Mandurah", "Bunbury"]},
            "SA": {"name": "South Australia", "cities": ["Adelaide", "Mount Gambier", "Whyalla", "Murray Bridge", "Port Augusta"]},
            "TAS": {"name": "Tasmania", "cities": ["Hobart", "Launceston", "Devonport", "Burnie", "Kingston"]},
            "ACT": {"name": "Australian Capital Territory", "cities": ["Canberra", "Queanbeyan"]},
            "NT": {"name": "Northern Territory", "cities": ["Darwin", "Alice Springs", "Palmerston", "Katherine"]},
        }
    },
    "IN": {
        "name": "India",
        "states": {
            "MH": {"name": "Maharashtra", "cities": ["Mumbai", "Pune", "Nagpur", "Thane", "Nashik", "Aurangabad"]},
            "DL": {"name": "Delhi", "cities": ["New Delhi", "Delhi"]},
            "KA": {"name": "Karnataka", "cities": ["Bangalore", "Mysore", "Hubli", "Mangalore", "Belgaum"]},
            "TN": {"name": "Tamil Nadu", "cities": ["Chennai", "Coimbatore", "Madurai", "Tiruchirappalli", "Salem"]},
            "WB": {"name": "West Bengal", "cities": ["Kolkata", "Howrah", "Durgapur", "Asansol", "Siliguri"]},
            "GJ": {"name": "Gujarat", "cities": ["Ahmedabad", "Surat", "Vadodara", "Rajkot", "Bhavnagar"]},
            "RJ": {"name": "Rajasthan", "cities": ["Jaipur", "Jodhpur", "Udaipur", "Kota", "Bikaner"]},
            "UP": {"name": "Uttar Pradesh", "cities": ["Lucknow", "Kanpur", "Agra", "Varanasi", "Allahabad", "Noida", "Ghaziabad"]},
            "MP": {"name": "Madhya Pradesh", "cities": ["Bhopal", "Indore", "Jabalpur", "Gwalior", "Ujjain"]},
            "TG": {"name": "Telangana", "cities": ["Hyderabad", "Warangal", "Nizamabad", "Karimnagar", "Khammam"]},
            "AP": {"name": "Andhra Pradesh", "cities": ["Visakhapatnam", "Vijayawada", "Guntur", "Nellore", "Tirupati"]},
            "KL": {"name": "Kerala", "cities": ["Thiruvananthapuram", "Kochi", "Kozhikode", "Thrissur", "Kollam"]},
            "PB": {"name": "Punjab", "cities": ["Ludhiana", "Amritsar", "Jalandhar", "Patiala", "Bathinda"]},
            "HR": {"name": "Haryana", "cities": ["Faridabad", "Gurgaon", "Panipat", "Ambala", "Rohtak"]},
            "BR": {"name": "Bihar", "cities": ["Patna", "Gaya", "Bhagalpur", "Muzaffarpur", "Darbhanga"]},
            "OR": {"name": "Odisha", "cities": ["Bhubaneswar", "Cuttack", "Rourkela", "Brahmapur", "Sambalpur"]},
        }
    },
    "DE": {
        "name": "Germany",
        "states": {
            "BY": {"name": "Bavaria", "cities": ["Munich", "Nuremberg", "Augsburg", "Regensburg", "Würzburg"]},
            "NW": {"name": "North Rhine-Westphalia", "cities": ["Cologne", "Düsseldorf", "Dortmund", "Essen", "Duisburg", "Bonn"]},
            "BW": {"name": "Baden-Württemberg", "cities": ["Stuttgart", "Mannheim", "Karlsruhe", "Freiburg", "Heidelberg"]},
            "NI": {"name": "Lower Saxony", "cities": ["Hanover", "Braunschweig", "Oldenburg", "Osnabrück", "Wolfsburg"]},
            "HE": {"name": "Hesse", "cities": ["Frankfurt", "Wiesbaden", "Kassel", "Darmstadt", "Offenbach"]},
            "BE": {"name": "Berlin", "cities": ["Berlin"]},
            "HH": {"name": "Hamburg", "cities": ["Hamburg"]},
            "SN": {"name": "Saxony", "cities": ["Leipzig", "Dresden", "Chemnitz", "Zwickau"]},
            "RP": {"name": "Rhineland-Palatinate", "cities": ["Mainz", "Ludwigshafen", "Koblenz", "Trier", "Kaiserslautern"]},
            "SH": {"name": "Schleswig-Holstein", "cities": ["Kiel", "Lübeck", "Flensburg", "Neumünster"]},
            "BB": {"name": "Brandenburg", "cities": ["Potsdam", "Cottbus", "Brandenburg an der Havel", "Frankfurt (Oder)"]},
            "TH": {"name": "Thuringia", "cities": ["Erfurt", "Jena", "Gera", "Weimar", "Gotha"]},
            "ST": {"name": "Saxony-Anhalt", "cities": ["Magdeburg", "Halle", "Dessau-Roßlau"]},
            "MV": {"name": "Mecklenburg-Vorpommern", "cities": ["Rostock", "Schwerin", "Stralsund", "Greifswald"]},
            "SL": {"name": "Saarland", "cities": ["Saarbrücken", "Neunkirchen", "Homburg"]},
            "HB": {"name": "Bremen", "cities": ["Bremen", "Bremerhaven"]},
        }
    },
    "FR": {
        "name": "France",
        "states": {
            "IDF": {"name": "Île-de-France", "cities": ["Paris", "Boulogne-Billancourt", "Saint-Denis", "Argenteuil", "Montreuil"]},
            "ARA": {"name": "Auvergne-Rhône-Alpes", "cities": ["Lyon", "Grenoble", "Saint-Étienne", "Villeurbanne", "Clermont-Ferrand"]},
            "NAQ": {"name": "Nouvelle-Aquitaine", "cities": ["Bordeaux", "Limoges", "Poitiers", "La Rochelle", "Pau"]},
            "OCC": {"name": "Occitanie", "cities": ["Toulouse", "Montpellier", "Nîmes", "Perpignan", "Béziers"]},
            "HDF": {"name": "Hauts-de-France", "cities": ["Lille", "Amiens", "Roubaix", "Tourcoing", "Dunkerque"]},
            "PAC": {"name": "Provence-Alpes-Côte d'Azur", "cities": ["Marseille", "Nice", "Toulon", "Aix-en-Provence", "Avignon"]},
            "PDL": {"name": "Pays de la Loire", "cities": ["Nantes", "Angers", "Le Mans", "Saint-Nazaire"]},
            "GES": {"name": "Grand Est", "cities": ["Strasbourg", "Reims", "Metz", "Mulhouse", "Nancy"]},
            "BRE": {"name": "Brittany", "cities": ["Rennes", "Brest", "Lorient", "Vannes", "Saint-Malo"]},
            "NOR": {"name": "Normandy", "cities": ["Rouen", "Le Havre", "Caen", "Cherbourg", "Évreux"]},
            "BFC": {"name": "Bourgogne-Franche-Comté", "cities": ["Dijon", "Besançon", "Belfort", "Auxerre"]},
            "CVL": {"name": "Centre-Val de Loire", "cities": ["Tours", "Orléans", "Bourges", "Blois"]},
            "COR": {"name": "Corsica", "cities": ["Ajaccio", "Bastia", "Corte"]},
        }
    },
    "JP": {
        "name": "Japan",
        "states": {
            "TK": {"name": "Tokyo", "cities": ["Tokyo", "Shibuya", "Shinjuku", "Hachioji"]},
            "OS": {"name": "Osaka", "cities": ["Osaka", "Sakai", "Higashiosaka", "Suita", "Takatsuki"]},
            "AI": {"name": "Aichi", "cities": ["Nagoya", "Toyota", "Okazaki", "Ichinomiya", "Kasugai"]},
            "KN": {"name": "Kanagawa", "cities": ["Yokohama", "Kawasaki", "Sagamihara", "Fujisawa"]},
            "ST": {"name": "Saitama", "cities": ["Saitama", "Kawaguchi", "Kawagoe", "Tokorozawa"]},
            "HK": {"name": "Hokkaido", "cities": ["Sapporo", "Asahikawa", "Hakodate", "Kushiro"]},
            "FK": {"name": "Fukuoka", "cities": ["Fukuoka", "Kitakyushu", "Kurume", "Omuta"]},
            "HG": {"name": "Hyogo", "cities": ["Kobe", "Himeji", "Nishinomiya", "Amagasaki"]},
            "KY": {"name": "Kyoto", "cities": ["Kyoto", "Uji", "Kameoka", "Maizuru"]},
            "CB": {"name": "Chiba", "cities": ["Chiba", "Funabashi", "Matsudo", "Ichikawa"]},
        }
    },
    "CN": {
        "name": "China",
        "states": {
            "BJ": {"name": "Beijing", "cities": ["Beijing"]},
            "SH": {"name": "Shanghai", "cities": ["Shanghai"]},
            "GD": {"name": "Guangdong", "cities": ["Guangzhou", "Shenzhen", "Dongguan", "Foshan", "Zhuhai"]},
            "JS": {"name": "Jiangsu", "cities": ["Nanjing", "Suzhou", "Wuxi", "Changzhou", "Xuzhou"]},
            "ZJ": {"name": "Zhejiang", "cities": ["Hangzhou", "Ningbo", "Wenzhou", "Shaoxing", "Jiaxing"]},
            "SC": {"name": "Sichuan", "cities": ["Chengdu", "Mianyang", "Leshan", "Nanchong"]},
            "HB": {"name": "Hubei", "cities": ["Wuhan", "Yichang", "Xiangyang", "Jingzhou"]},
            "HN": {"name": "Henan", "cities": ["Zhengzhou", "Luoyang", "Kaifeng", "Xinxiang"]},
            "SD": {"name": "Shandong", "cities": ["Jinan", "Qingdao", "Yantai", "Weihai", "Zibo"]},
            "FJ": {"name": "Fujian", "cities": ["Fuzhou", "Xiamen", "Quanzhou", "Zhangzhou"]},
            "TJ": {"name": "Tianjin", "cities": ["Tianjin"]},
            "CQ": {"name": "Chongqing", "cities": ["Chongqing"]},
        }
    },
    "BR": {
        "name": "Brazil",
        "states": {
            "SP": {"name": "São Paulo", "cities": ["São Paulo", "Guarulhos", "Campinas", "São Bernardo do Campo", "Santo André"]},
            "RJ": {"name": "Rio de Janeiro", "cities": ["Rio de Janeiro", "Niterói", "Duque de Caxias", "Nova Iguaçu"]},
            "MG": {"name": "Minas Gerais", "cities": ["Belo Horizonte", "Uberlândia", "Contagem", "Juiz de Fora"]},
            "BA": {"name": "Bahia", "cities": ["Salvador", "Feira de Santana", "Vitória da Conquista", "Camaçari"]},
            "RS": {"name": "Rio Grande do Sul", "cities": ["Porto Alegre", "Caxias do Sul", "Pelotas", "Canoas"]},
            "PR": {"name": "Paraná", "cities": ["Curitiba", "Londrina", "Maringá", "Ponta Grossa"]},
            "PE": {"name": "Pernambuco", "cities": ["Recife", "Jaboatão dos Guararapes", "Olinda", "Caruaru"]},
            "CE": {"name": "Ceará", "cities": ["Fortaleza", "Caucaia", "Juazeiro do Norte", "Maracanaú"]},
            "PA": {"name": "Pará", "cities": ["Belém", "Ananindeua", "Santarém", "Marabá"]},
            "SC": {"name": "Santa Catarina", "cities": ["Florianópolis", "Joinville", "Blumenau", "Criciúma"]},
            "DF": {"name": "Distrito Federal", "cities": ["Brasília"]},
        }
    },
    "MX": {
        "name": "Mexico",
        "states": {
            "CMX": {"name": "Ciudad de México", "cities": ["Mexico City"]},
            "JAL": {"name": "Jalisco", "cities": ["Guadalajara", "Zapopan", "Tlaquepaque", "Tonalá", "Puerto Vallarta"]},
            "NLE": {"name": "Nuevo León", "cities": ["Monterrey", "San Nicolás", "Apodaca", "Guadalupe", "Santa Catarina"]},
            "PUE": {"name": "Puebla", "cities": ["Puebla", "Tehuacán", "San Martín Texmelucan", "Atlixco"]},
            "GUA": {"name": "Guanajuato", "cities": ["León", "Irapuato", "Celaya", "Salamanca", "Guanajuato"]},
            "CHH": {"name": "Chihuahua", "cities": ["Ciudad Juárez", "Chihuahua", "Delicias", "Cuauhtémoc"]},
            "VER": {"name": "Veracruz", "cities": ["Veracruz", "Xalapa", "Coatzacoalcos", "Córdoba"]},
            "BCN": {"name": "Baja California", "cities": ["Tijuana", "Mexicali", "Ensenada", "Rosarito"]},
            "TAM": {"name": "Tamaulipas", "cities": ["Reynosa", "Matamoros", "Nuevo Laredo", "Tampico", "Ciudad Victoria"]},
            "SON": {"name": "Sonora", "cities": ["Hermosillo", "Ciudad Obregón", "Nogales", "San Luis Río Colorado"]},
            "QRO": {"name": "Querétaro", "cities": ["Querétaro", "San Juan del Río", "Corregidora"]},
            "YUC": {"name": "Yucatán", "cities": ["Mérida", "Kanasín", "Valladolid", "Tizimín"]},
        }
    },
    "AE": {
        "name": "United Arab Emirates",
        "states": {
            "DU": {"name": "Dubai", "cities": ["Dubai"]},
            "AZ": {"name": "Abu Dhabi", "cities": ["Abu Dhabi", "Al Ain"]},
            "SH": {"name": "Sharjah", "cities": ["Sharjah", "Khor Fakkan"]},
            "AJ": {"name": "Ajman", "cities": ["Ajman"]},
            "UQ": {"name": "Umm Al Quwain", "cities": ["Umm Al Quwain"]},
            "RK": {"name": "Ras Al Khaimah", "cities": ["Ras Al Khaimah"]},
            "FU": {"name": "Fujairah", "cities": ["Fujairah"]},
        }
    },
    "SG": {
        "name": "Singapore",
        "states": {
            "SG": {"name": "Singapore", "cities": ["Singapore"]},
        }
    },
    "PH": {
        "name": "Philippines",
        "states": {
            "NCR": {"name": "Metro Manila", "cities": ["Manila", "Quezon City", "Makati", "Pasig", "Taguig", "Pasay"]},
            "CEV": {"name": "Central Visayas", "cities": ["Cebu City", "Lapu-Lapu", "Mandaue", "Talisay"]},
            "DAV": {"name": "Davao Region", "cities": ["Davao City", "Tagum", "Panabo", "Digos"]},
            "CAL": {"name": "Calabarzon", "cities": ["Calamba", "Lucena", "Antipolo", "Batangas City"]},
            "CLU": {"name": "Central Luzon", "cities": ["Angeles City", "San Fernando", "Olongapo", "Malolos"]},
        }
    },
    "ZA": {
        "name": "South Africa",
        "states": {
            "GP": {"name": "Gauteng", "cities": ["Johannesburg", "Pretoria", "Soweto", "Benoni", "Germiston"]},
            "WC": {"name": "Western Cape", "cities": ["Cape Town", "Stellenbosch", "Paarl", "George"]},
            "KZN": {"name": "KwaZulu-Natal", "cities": ["Durban", "Pietermaritzburg", "Richards Bay", "Newcastle"]},
            "EC": {"name": "Eastern Cape", "cities": ["Port Elizabeth", "East London", "Mthatha", "Queenstown"]},
            "LP": {"name": "Limpopo", "cities": ["Polokwane", "Tzaneen", "Phalaborwa", "Mokopane"]},
            "MP": {"name": "Mpumalanga", "cities": ["Nelspruit", "Witbank", "Secunda", "Middelburg"]},
            "FS": {"name": "Free State", "cities": ["Bloemfontein", "Welkom", "Kroonstad", "Bethlehem"]},
            "NW": {"name": "North West", "cities": ["Rustenburg", "Klerksdorp", "Potchefstroom", "Mahikeng"]},
            "NC": {"name": "Northern Cape", "cities": ["Kimberley", "Upington", "Springbok", "De Aar"]},
        }
    },
    "NG": {
        "name": "Nigeria",
        "states": {
            "LA": {"name": "Lagos", "cities": ["Lagos", "Ikeja", "Mushin", "Oshodi-Isolo"]},
            "KN": {"name": "Kano", "cities": ["Kano"]},
            "RV": {"name": "Rivers", "cities": ["Port Harcourt", "Obio-Akpor"]},
            "FC": {"name": "Federal Capital Territory", "cities": ["Abuja"]},
            "OY": {"name": "Oyo", "cities": ["Ibadan", "Ogbomosho", "Oyo"]},
            "KD": {"name": "Kaduna", "cities": ["Kaduna", "Zaria"]},
            "AN": {"name": "Anambra", "cities": ["Onitsha", "Awka", "Nnewi"]},
            "EN": {"name": "Enugu", "cities": ["Enugu", "Nsukka"]},
        }
    },
    "EG": {
        "name": "Egypt",
        "states": {
            "C": {"name": "Cairo", "cities": ["Cairo"]},
            "GZ": {"name": "Giza", "cities": ["Giza", "6th of October City"]},
            "ALX": {"name": "Alexandria", "cities": ["Alexandria"]},
            "MNF": {"name": "Monufia", "cities": ["Shibin El Kom", "Menouf"]},
            "SHR": {"name": "Sharqia", "cities": ["Zagazig", "10th of Ramadan City"]},
            "ASN": {"name": "Aswan", "cities": ["Aswan", "Kom Ombo", "Edfu"]},
            "LX": {"name": "Luxor", "cities": ["Luxor"]},
            "RS": {"name": "Red Sea", "cities": ["Hurghada", "Safaga", "El Gouna"]},
        }
    },
    "SA": {
        "name": "Saudi Arabia",
        "states": {
            "RY": {"name": "Riyadh Region", "cities": ["Riyadh", "Kharj", "Dawadmi"]},
            "MK": {"name": "Makkah Region", "cities": ["Jeddah", "Mecca", "Taif", "Rabigh"]},
            "EP": {"name": "Eastern Province", "cities": ["Dammam", "Dhahran", "Khobar", "Jubail", "Hofuf"]},
            "MD": {"name": "Madinah Region", "cities": ["Medina", "Yanbu"]},
            "AS": {"name": "Asir Region", "cities": ["Abha", "Khamis Mushait"]},
        }
    },
    "KR": {
        "name": "South Korea",
        "states": {
            "SEO": {"name": "Seoul", "cities": ["Seoul"]},
            "PUS": {"name": "Busan", "cities": ["Busan"]},
            "ICN": {"name": "Incheon", "cities": ["Incheon"]},
            "DGU": {"name": "Daegu", "cities": ["Daegu"]},
            "DJN": {"name": "Daejeon", "cities": ["Daejeon"]},
            "KWJ": {"name": "Gwangju", "cities": ["Gwangju"]},
            "GGD": {"name": "Gyeonggi-do", "cities": ["Suwon", "Seongnam", "Goyang", "Yongin", "Bucheon"]},
        }
    },
    "IT": {
        "name": "Italy",
        "states": {
            "LOM": {"name": "Lombardy", "cities": ["Milan", "Brescia", "Bergamo", "Monza", "Como"]},
            "LAZ": {"name": "Lazio", "cities": ["Rome", "Latina", "Guidonia", "Fiumicino"]},
            "CAM": {"name": "Campania", "cities": ["Naples", "Salerno", "Giugliano in Campania", "Torre del Greco"]},
            "VEN": {"name": "Veneto", "cities": ["Venice", "Verona", "Padua", "Vicenza", "Treviso"]},
            "PIE": {"name": "Piedmont", "cities": ["Turin", "Novara", "Alessandria", "Asti"]},
            "EMR": {"name": "Emilia-Romagna", "cities": ["Bologna", "Modena", "Parma", "Reggio Emilia", "Ravenna"]},
            "TOS": {"name": "Tuscany", "cities": ["Florence", "Prato", "Livorno", "Arezzo", "Pisa"]},
            "SIC": {"name": "Sicily", "cities": ["Palermo", "Catania", "Messina", "Syracuse", "Marsala"]},
        }
    },
    "ES": {
        "name": "Spain",
        "states": {
            "MD": {"name": "Madrid", "cities": ["Madrid", "Móstoles", "Alcalá de Henares", "Fuenlabrada", "Getafe"]},
            "CT": {"name": "Catalonia", "cities": ["Barcelona", "L'Hospitalet", "Badalona", "Terrassa", "Sabadell"]},
            "AN": {"name": "Andalusia", "cities": ["Seville", "Málaga", "Córdoba", "Granada", "Jerez"]},
            "VC": {"name": "Valencia", "cities": ["Valencia", "Alicante", "Elche", "Castellón"]},
            "GA": {"name": "Galicia", "cities": ["Vigo", "A Coruña", "Ourense", "Lugo", "Santiago"]},
            "PV": {"name": "Basque Country", "cities": ["Bilbao", "Vitoria-Gasteiz", "San Sebastián"]},
            "CL": {"name": "Castile and León", "cities": ["Valladolid", "Burgos", "Salamanca", "León"]},
            "CN": {"name": "Canary Islands", "cities": ["Las Palmas", "Santa Cruz de Tenerife", "La Laguna"]},
        }
    },
    "PK": {
        "name": "Pakistan",
        "states": {
            "PB": {"name": "Punjab", "cities": ["Lahore", "Faisalabad", "Rawalpindi", "Multan", "Gujranwala"]},
            "SD": {"name": "Sindh", "cities": ["Karachi", "Hyderabad", "Sukkur", "Larkana"]},
            "KP": {"name": "Khyber Pakhtunkhwa", "cities": ["Peshawar", "Mardan", "Mingora", "Abbottabad"]},
            "BA": {"name": "Balochistan", "cities": ["Quetta", "Gwadar", "Turbat", "Khuzdar"]},
            "IS": {"name": "Islamabad Capital Territory", "cities": ["Islamabad"]},
        }
    },
    "TR": {
        "name": "Turkey",
        "states": {
            "IST": {"name": "Istanbul", "cities": ["Istanbul"]},
            "ANK": {"name": "Ankara", "cities": ["Ankara"]},
            "IZM": {"name": "Izmir", "cities": ["Izmir"]},
            "BUR": {"name": "Bursa", "cities": ["Bursa"]},
            "ANT": {"name": "Antalya", "cities": ["Antalya", "Alanya", "Manavgat"]},
            "ADA": {"name": "Adana", "cities": ["Adana"]},
            "GAZ": {"name": "Gaziantep", "cities": ["Gaziantep"]},
            "KON": {"name": "Konya", "cities": ["Konya"]},
        }
    },
    "RU": {
        "name": "Russia",
        "states": {
            "MOW": {"name": "Moscow", "cities": ["Moscow"]},
            "SPE": {"name": "Saint Petersburg", "cities": ["Saint Petersburg"]},
            "NVS": {"name": "Novosibirsk Oblast", "cities": ["Novosibirsk"]},
            "SVE": {"name": "Sverdlovsk Oblast", "cities": ["Yekaterinburg", "Nizhny Tagil"]},
            "NIZ": {"name": "Nizhny Novgorod Oblast", "cities": ["Nizhny Novgorod"]},
            "SAM": {"name": "Samara Oblast", "cities": ["Samara", "Tolyatti"]},
            "KDA": {"name": "Krasnodar Krai", "cities": ["Krasnodar", "Sochi"]},
            "ROS": {"name": "Rostov Oblast", "cities": ["Rostov-on-Don", "Taganrog"]},
            "TAT": {"name": "Tatarstan", "cities": ["Kazan", "Naberezhnye Chelny"]},
        }
    },
    "NL": {
        "name": "Netherlands",
        "states": {
            "NH": {"name": "North Holland", "cities": ["Amsterdam", "Haarlem", "Zaanstad", "Hilversum"]},
            "ZH": {"name": "South Holland", "cities": ["Rotterdam", "The Hague", "Leiden", "Dordrecht"]},
            "NB": {"name": "North Brabant", "cities": ["Eindhoven", "Tilburg", "Breda", "'s-Hertogenbosch"]},
            "GE": {"name": "Gelderland", "cities": ["Nijmegen", "Arnhem", "Apeldoorn"]},
            "UT": {"name": "Utrecht", "cities": ["Utrecht", "Amersfoort"]},
            "LI": {"name": "Limburg", "cities": ["Maastricht", "Venlo", "Heerlen"]},
        }
    },
}


def generate_uuid():
    return str(uuid.uuid4())


def seed_locations():
    """Seed all location data into the database."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not found in environment variables")
        return
    
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("Starting location data seeding...")
        
        countries_added = 0
        states_added = 0
        cities_added = 0
        
        for country_code, country_data in LOCATION_DATA.items():
            # Insert country
            country_id = generate_uuid()
            session.execute(
                text("INSERT INTO country (id, code, name, is_active, created_at) VALUES (:id, :code, :name, :is_active, :created_at)"),
                {"id": country_id, "code": country_code, "name": country_data["name"], "is_active": True, "created_at": datetime.utcnow()}
            )
            countries_added += 1
            
            # Insert states
            for state_code, state_data in country_data["states"].items():
                state_id = generate_uuid()
                session.execute(
                    text("INSERT INTO state (id, country_id, code, name, is_active, created_at) VALUES (:id, :country_id, :code, :name, :is_active, :created_at)"),
                    {"id": state_id, "country_id": country_id, "code": state_code, "name": state_data["name"], "is_active": True, "created_at": datetime.utcnow()}
                )
                states_added += 1
                
                # Insert cities
                for city_name in state_data["cities"]:
                    city_id = generate_uuid()
                    session.execute(
                        text("INSERT INTO city (id, state_id, name, is_active, created_at) VALUES (:id, :state_id, :name, :is_active, :created_at)"),
                        {"id": city_id, "state_id": state_id, "name": city_name, "is_active": True, "created_at": datetime.utcnow()}
                    )
                    cities_added += 1
        
        session.commit()
        print(f"✓ Seeding complete!")
        print(f"  - Countries: {countries_added}")
        print(f"  - States/Provinces: {states_added}")
        print(f"  - Cities: {cities_added}")
        
    except Exception as e:
        session.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_locations()
