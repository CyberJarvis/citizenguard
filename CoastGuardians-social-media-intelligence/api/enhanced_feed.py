"""
Enhanced Live Social Media Feed with Multi-language Support
Includes real-time alerts, configurable parameters, and Indian language support
"""

import threading
import queue
import time
import random
from datetime import datetime, timezone
from typing import Dict, List, Any
import uuid

# Enhanced feed configuration
feed_config = {
    "post_interval": 8,
    "disaster_probability": 0.3,
    "language_mix": True,
    "active_alerts": [],
    "alert_threshold": 7.0
}

feed_running = False
feed_thread = None
feed_queue = queue.Queue(maxsize=100)
# Store post history for retrieval (keeps last 100 posts)
posts_history = []
posts_history_lock = threading.Lock()

# Multi-language post templates
MULTI_LANGUAGE_POSTS = {
    "english": {
        "normal": [
            "Beautiful sunrise at {location} marina today! Perfect weather 🌅",
            "Great day for sailing in {location} waters. Calm seas 🌊",
            "Local fishermen report good catch near {location}. Fish market busy today",
            "Coast guard training exercise at {location}. Impressive display of skills",
            "Amazing whale watching experience near {location}. Spotted 3 dolphins!",
            "Port {location} handling record cargo volumes this month. Economy boosting",
            "Beach cleanup drive at {location} this weekend. Join us for a cleaner coast",
            "New marine conservation project launched in {location}. Protecting our oceans",
            "Had amazing seafood at {location} port today! Fresh catch 🐟",
            "Weather conditions perfect for fishing near {location} coast today",
            "Tourist season picking up at {location} beach. Hotels fully booked",
            "Local seafood restaurant in {location} serving fresh prawns today",
            "Morning boat ride to {location} was absolutely stunning 🚤",
            "Sea conditions ideal for water sports in {location} today",
            "Container ship docked at {location} port this morning",
            "Fishing boats returning to {location} harbor with today's catch",
            "Spectacular sunset view from {location} lighthouse 🌇",
            "Port workers at {location} completing infrastructure upgrades",
            "Marine biologists studying coral reefs near {location}",
            "Traditional fishing methods still practiced in {location} villages",
            "New ferry service launched between {location} and nearby islands",
            "Beach volleyball tournament happening at {location} this weekend",
            "Tide times favorable for fishing at {location} tonight",
            "Local fisherman celebrates 30 years at sea in {location}",
            "Navy ship visits {location} port for goodwill mission",
            "Children enjoying beach activities at {location} today",
            "Coastal patrol boat spotted near {location} this afternoon",
            "Fresh fish auction at {location} market drawing big crowds",
            "Sailing club in {location} hosting regatta next month",
            "Sea turtles spotted nesting on {location} beach last night 🐢"
        ],
        "disaster": [
            "URGENT: Massive tsunami waves approaching {location}! Wave height {magnitude}m! Evacuate immediately!",
            "CRITICAL: Cyclone {name} approaching {location} with winds {magnitude} kmph. Category {category} storm!",
            "ALERT: Massive oil spill at {location}. {magnitude} tonnes leaked. Coast Guard responding!",
            "Breaking: M{magnitude} earthquake strikes {location}. Depth: {depth}km. Damage assessment ongoing!",
            "Severe flooding in {location}! Water level {magnitude} meters above normal. Evacuate now!",
            "Emergency: Coast Guard rescuing fishermen trapped by rough seas near {location} ⛑️"
        ]
    },
    "hindi": {
        "normal": [
            "{location} में आज सुंदर सूर्योदय! अच्छा मौसम 🌅",
            "{location} में नौकायन के लिए बेहतरीन दिन। शांत समुद्र 🌊",
            "{location} के पास मछुआरों को अच्छी मछली मिली। मछली बाजार व्यस्त",
            "{location} में तट रक्षक प्रशिक्षण अभ्यास। कौशल का प्रभावशाली प्रदर्शन",
            "{location} के पास व्हेल देखने का अद्भुत अनुभव। 3 डॉल्फिन देखीं!",
            "{location} बंदरगाह आज नई नौका सेवा शुरू कर रहा है",
            "{location} समुद्र तट पर पर्यटकों की भीड़। होटल भरे हुए हैं",
            "{location} में ताजा समुद्री भोजन का आनंद। झींगे बहुत अच्छे थे 🦐",
            "{location} में आज मछली पकड़ने के लिए बढ़िया मौसम की स्थिति",
            "नौसेना जहाज {location} बंदरगाह का दौरा कर रहा है",
            "{location} में समुद्री जीवविज्ञानी मूंगा चट्टानों का अध्ययन कर रहे हैं",
            "{location} तट पर शाम का शानदार दृश्य 🌅",
            "{location} में मछली नीलामी में आज बड़ी भीड़",
            "{location} बीच पर सफाई अभियान इस सप्ताह",
            "{location} में पारंपरिक मछली पकड़ने के तरीके अभी भी प्रचलित"
        ],
        "disaster": [
            "आपातकाल: {location} में भीषण सुनामी लहरें! {magnitude}मीटर ऊंची लहरें! तुरंत निकलें!",
            "चक्रवात {name} {location} की ओर {magnitude} किमी/घंटा की रफ्तार से। श्रेणी {category} तूफान!",
            "तेल रिसाव: {location} में {magnitude} टन तेल रिसाव। तट रक्षक तुरंत कार्रवाई!",
            "भूकंप: {location} में {magnitude} तीव्रता का भूकंप। गहराई: {depth}किमी। नुकसान का आकलन जारी!"
        ]
    },
    "tamil": {
        "normal": [
            "{location} இல் இன்று அழகான சூர்யோதயம்! நல்ல வானிலை 🌅",
            "{location} நீரில் படகு சவாரிக்கு சிறந்த நாள். அமைதியான கடல் 🌊",
            "{location} அருகே மீனவர்களுக்கு நல்ல மீன் கிடைத்தது। மீன் சந்தை பரபரப்பு",
            "{location} துறைமுகத்தில் புதிய படகு சேவை தொடங்கப்பட்டது",
            "{location} கடற்கரையில் சுற்றுலா பயணிகள் கூட்டம். ஹோட்டல்கள் நிறைந்தன",
            "{location} இல் புதிய மீன் உணவகம் திறக்கப்பட்டது 🐟",
            "{location} இல் இன்று மீன் பிடிக்க சிறந்த வானிலை",
            "{location} கடற்கரையில் சூரிய அஸ்தமனம் அற்புதமாக இருந்தது 🌇",
            "கடலோர காவல் படகு {location} அருகே பார்த்தோம்",
            "{location} இல் பாரம்பரிய மீன் பிடிக்கும் முறைகள் இன்னும் உள்ளன",
            "{location} துறைமுகத்தில் கப்பல் வந்து சேர்ந்தது",
            "{location} இல் கடல் ஆமைகள் முட்டையிடுவதை பார்த்தோம் 🐢"
        ],
        "disaster": [
            "அவசரம்: {location} இல் பயங்கர சுனாமி அலைகள்! {magnitude} மீட்டர் உயரம்! உடனே வெளியேறுங்கள்!",
            "புயல் {name} {location} நோக்கி {magnitude} கிமீ/மணி வேகத்தில். வகை {category} புயல்!",
            "எண்ணெய் கசிவு: {location} இல் {magnitude} டன் எண்ணெய் கசிந்தது। கடலோர காவல்படை உடனடி நடவடிக்கை!"
        ]
    },
    "bengali": {
        "normal": [
            "{location} এ আজ সুন্দর সূর্যোদয়! চমৎকার আবহাওয়া 🌅",
            "{location} জলে নৌকা চালানোর জন্য দুর্দান্ত দিন। শান্ত সমুদ্র 🌊",
            "{location} এর কাছে জেলেরা ভালো মাছ পেয়েছেন। মাছের বাজার ব্যস্ত"
        ],
        "disaster": [
            "জরুরি: {location} এ ভয়াবহ সুনামি ঢেউ! {magnitude} মিটার উচ্চতা! অবিলম্বে সরে যান!",
            "ঘূর্ণিঝড় {name} {location} এর দিকে {magnitude} কিমি/ঘণ্টা গতিতে। শ্রেণি {category} ঝড়!"
        ]
    },
    "gujarati": {
        "normal": [
            "{location} માં આજે સુંદર સૂર્યોદય! સરસ હવામાન 🌅",
            "{location} પાણીમાં નૌકાવિહાર માટે સરસ દિવસ। શાંત સમુદ્ર 🌊",
            "{location} પાસે માછીમારોને સારી માછલી મળી। માછલીનું બજાર વ્યસ્ત"
        ],
        "disaster": [
            "કટોકટી: {location} માં ભયંકર સુનામી મોજા! {magnitude} મીટર ઊંચા! તાત્કાલિક બહાર નીકળો!",
            "ચક્રવાત {name} {location} તરફ {magnitude} કિમી/કલાકની ઝડપે. શ્રેણી {category} તોફાન!"
        ]
    },
    "marathi": {
        "normal": [
            "{location} मध्ये आज सुंदर सूर्योदय! छान हवामान 🌅",
            "{location} पाण्यात नौकाविहारासाठी उत्तम दिवस। शांत समुद्र 🌊",
            "{location} जवळ मच्छिमारांना चांगले मासे मिळाले। मासे बाजार गर्दीचा"
        ],
        "disaster": [
            "आपत्काळ: {location} मध्ये भयंकर त्सुनामी लाटा! {magnitude} मीटर उंची! ताबडतोब बाहेर पडा!",
            "चक्रीवादळ {name} {location} दिशेने {magnitude} कि.मी./तास वेगाने. श्रेणी {category} वादळ!"
        ]
    },
    "telugu": {
        "normal": [
            "{location} లో ఈ రోజు అందమైన సూర్యోదయం! మంచి వాతావరణం 🌅",
            "{location} నీటిలో పడవ రవాణాకు అద్భుతమైన రోజు। ప్రశాంత సముద్రం 🌊",
            "{location} దగ్గర మత్స్యకారులకు మంచి చేపలు దొరికాయి। చేప మార్కెట్ రద్దీ",
            "{location} ఓడరేవులో కొత్త పడవ సేవ ప్రారంభమైంది",
            "{location} బీచ్ లో పర్యాటకులు గుంపు। హోటళ్లు నిండిపోయాయి",
            "{location} లో తాజా సముద్ర ఆహారం అద్భుతంగా ఉంది 🦐",
            "{location} లో నేడు చేపలు పట్టడానికి మంచి వాతావరణం",
            "{location} తీరంలో సాయంత్రం అద్భుత దృశ్యం 🌇",
            "{location} ఓడరేవులో నౌకాదళ నౌక సందర్శన",
            "{location} లో సముద్ర జీవశాస్త్రవేత్తలు పగడపు దిబ్బలను అధ్యయనం చేస్తున్నారు",
            "{location} లో సాంప్రదాయ చేపలు పట్టే పద్ధతులు ఇప్పటికీ ఉన్నాయి",
            "{location} బీచ్ లో శుభ్రత ప్రచారం ఈ వారం"
        ],
        "disaster": [
            "అత్యవసరం: {location} లో భయంకర సునామీ అలలు! {magnitude} మీటర్ల ఎత్తు! వెంటనే వెళ్లిపొండి!",
            "తుఫాను {name} {location} వైపు {magnitude} కిమీ/గంట వేగంతో. కేటగిరీ {category} తుఫాను!"
        ]
    },
    "kannada": {
        "normal": [
            "{location} ನಲ್ಲಿ ಇಂದು ಸುಂದರವಾದ ಸೂರ್ಯೋದಯ! ಉತ್ತಮ ಹವಾಮಾನ 🌅",
            "{location} ನೀರಿನಲ್ಲಿ ದೋಣಿ ಸವಾರಿಗೆ ಅದ್ಭುತ ದಿನ. ಶಾಂತ ಸಮುದ್ರ 🌊",
            "{location} ಬಳಿ ಮೀನುಗಾರರಿಗೆ ಒಳ್ಳೆಯ ಮೀನು ಸಿಕ್ಕಿದೆ। ಮೀನು ಮಾರುಕಟ್ಟೆ ಜನರಿಂದ ತುಂಬಿದೆ",
            "{location} ಬಂದರಿನಲ್ಲಿ ಹೊಸ ದೋಣಿ ಸೇವೆ ಪ್ರಾರಂಭವಾಯಿತು",
            "{location} ಬೀಚ್ ನಲ್ಲಿ ಪ್ರವಾಸಿಗರ ಗುಂಪು. ಹೋಟೆಲ್‌ಗಳು ತುಂಬಿವೆ",
            "{location} ನಲ್ಲಿ ತಾಜಾ ಸಮುದ್ರ ಆಹಾರ ಅದ್ಭುತವಾಗಿತ್ತು 🐟",
            "{location} ನಲ್ಲಿ ಇಂದು ಮೀನು ಹಿಡಿಯಲು ಉತ್ತಮ ಹವಾಮಾನ",
            "{location} ತೀರದಲ್ಲಿ ಸಂಜೆ ಅದ್ಭುತ ದೃಶ್ಯ 🌇",
            "{location} ಬಂದರಿನಲ್ಲಿ ನೌಕಾಪಡೆ ಹಡಗು ಭೇಟಿ",
            "{location} ನಲ್ಲಿ ಸಮುದ್ರ ಜೀವಶಾಸ್ತ್ರಜ್ಞರು ಹವಳದ ಬಂಡೆಗಳನ್ನು ಅಧ್ಯಯನ ಮಾಡುತ್ತಿದ್ದಾರೆ",
            "{location} ನಲ್ಲಿ ಸಾಂಪ್ರದಾಯಿಕ ಮೀನುಗಾರಿಕೆ ವಿಧಾನಗಳು ಇನ್ನೂ ಇವೆ",
            "{location} ಬೀಚ್ ನಲ್ಲಿ ಸ್ವಚ್ಛತಾ ಅಭಿಯಾನ ಈ ವಾರ"
        ],
        "disaster": [
            "ತುರ್ತು: {location} ನಲ್ಲಿ ಭಯಾನಕ ಸುನಾಮಿ ಅಲೆಗಳು! {magnitude} ಮೀಟರ್ ಎತ್ತರ! ತಕ್ಷಣ ಹೊರಡಿ!",
            "ಚಂಡಮಾರುತ {name} {location} ಕಡೆಗೆ {magnitude} ಕಿಮೀ/ಗಂಟೆ ವೇಗದಲ್ಲಿ. ವರ್ಗ {category} ಚಂಡಮಾರುತ!"
        ]
    },
    "malayalam": {
        "normal": [
            "{location} ൽ ഇന്ന് മനോഹരമായ സൂര്യോദയം! മികച്ച കാലാവസ്ഥ 🌅",
            "{location} വെള്ളത്തിൽ ബോട്ട് യാത്രയ്ക്ക് അത്ഭുതകരമായ ദിവസം. ശാന്തമായ കടൽ 🌊",
            "{location} അടുത്ത് മത്സ്യത്തൊഴിലാളികൾക്ക് നല്ല മത്സ്യം കിട്ടി. മത്സ്യ മാർക്കറ്റ് തിരക്കിൽ",
            "{location} തുറമുഖത്ത് പുതിയ ബോട്ട് സേവനം ആരംഭിച്ചു",
            "{location} ബീച്ചിൽ വിനോദസഞ്ചാരികളുടെ തിരക്ക്. ഹോട്ടലുകൾ നിറഞ്ഞു",
            "{location} ൽ പുതിയ മത്സ്യ ഭക്ഷണശാല അദ്ഭുതകരം 🦐",
            "{location} ൽ ഇന്ന് മീൻപിടിത്തത്തിന് നല്ল കാലാവസ്ഥ",
            "{location} തീരത്ത് സന്ധ്യ അത്ഭുതകരമായിരുന്നു 🌇",
            "{location} തുറമുഖത്ത് നാവിക കപ്പൽ സന്ദർശനം",
            "{location} ൽ സമുദ്ര ജീവശാസ്ത്രജ്ഞർ പവിഴപ്പുറ്റുകൾ പഠിക്കുന്നു",
            "{location} ൽ പരമ്പരാഗത മീൻപിടിത്ത രീതികൾ ഇപ്പോഴും ഉണ്ട്",
            "{location} ബീച്ചിൽ വൃത്തിയാക്കൽ കാമ്പയിൻ ഈ ആഴ്ച"
        ],
        "disaster": [
            "അടിയന്തിരം: {location} ൽ ഭയാനകമായ സുനാമി തിരമാലകൾ! {magnitude} മീറ്റർ ഉയരം! ഉടനെ പോകുക!",
            "ചുഴലിക്കാറ്റ് {name} {location} ലേക്ക് {magnitude} കിമീ/മണിക്കൂർ വേഗത്തിൽ. വിഭാഗം {category} കാറ്റ്!"
        ]
    }
}

# Indian coastal locations - Comprehensive list covering all major ports and coastal cities
INDIAN_COASTAL_LOCATIONS = [
    # Major Metro Coastal Cities
    "Mumbai", "Chennai", "Kolkata", "Visakhapatnam", "Kochi", "Surat",

    # Major Ports
    "JNPT", "Kandla", "Paradip", "Haldia", "Tuticorin", "Ennore",
    "New Mangalore", "Kakinada", "Mundra", "Pipavav", "Dahej",

    # Maharashtra Coast
    "Alibag", "Uran", "Ratnagiri", "Raigad", "Sindhudurg", "Malvan",
    "Murud", "Dapoli", "Harnai", "Vengurla",

    # Gujarat Coast
    "Veraval", "Bhavnagar", "Porbandar", "Okha", "Dwarka", "Diu",
    "Jamnagar", "Khambhat", "Magdalla", "Hazira", "Umbergaon",

    # Goa
    "Goa", "Panaji", "Vasco", "Mormugao", "Margao", "Calangute",

    # Karnataka Coast
    "Mangalore", "Karwar", "Udupi", "Malpe", "Kundapura", "Kumta",
    "Bhatkal", "Honnavar", "Ullal",

    # Kerala Coast
    "Thiruvananthapuram", "Kollam", "Alappuzha", "Kozhikode",
    "Kannur", "Kasaragod", "Beypore", "Ponnani", "Vypeen", "Munambam",

    # Tamil Nadu Coast
    "Rameswaram", "Nagapattinam", "Cuddalore", "Puducherry", "Kanyakumari",
    "Thoothukudi", "Thiruchendur", "Mahabalipuram", "Mamallapuram", "Tranquebar",

    # Andhra Pradesh Coast
    "Machilipatnam", "Nellore", "Bapatla", "Chirala", "Nizampatnam",
    "Bheemunipatnam", "Yanam",

    # Odisha Coast
    "Puri", "Gopalpur", "Chandipur", "Dhamra", "Astaranga",

    # West Bengal Coast
    "Digha", "Bakkhali", "Sagar Island", "Shankarpur", "Mandarmani",

    # Andaman & Nicobar
    "Port Blair", "Havelock", "Neil Island", "Car Nicobar", "Diglipur",

    # Lakshadweep
    "Kavaratti", "Agatti", "Minicoy", "Andrott",

    # Daman & Diu
    "Daman", "Silvassa"
]

# Cyclone names (used for disaster posts)
CYCLONE_NAMES = ["Tej", "Hamoon", "Midhili", "Mandous", "Sitrang", "Nalgae", "Mocha",
                "Biparjoy", "Remal", "Michaung", "Nivar"]

# Dynamic username generation components
USERNAME_PREFIXES = [
    "coastal", "ocean", "marine", "sailor", "fisher", "sea", "wave", "beach", "port",
    "bay", "tide", "surf", "anchor", "boat", "ship", "vessel", "catch", "net",
    "harbor", "dock", "shore", "reef", "current", "whale", "dolphin", "fish",
    "captain", "crew", "navy", "maritime", "nautical", "aqua", "blue", "deep",
    "salt", "tropical", "storm", "wind", "breeze", "island", "lagoon", "coral"
]

USERNAME_SUFFIXES = [
    "explorer", "watcher", "news", "india", "updates", "live", "alert", "info",
    "daily", "reports", "tracker", "monitor", "watch", "patrol", "guard", "safety",
    "rescue", "crew", "life", "tales", "stories", "diary", "blog", "lover",
    "enthusiast", "observer", "hunter", "seeker", "finder", "scout", "official",
    "channel", "network", "station", "zone", "hub", "central", "connect", "link"
]

USERNAME_LOCATIONS = [
    # Major cities
    "mumbai", "chennai", "kolkata", "vizag", "kochi", "surat", "goa",
    # Maharashtra
    "alibag", "uran", "ratnagiri", "raigad", "malvan", "murud",
    # Gujarat
    "kandla", "porbandar", "dwarka", "jamnagar", "bhavnagar", "diu",
    # Karnataka
    "mangalore", "karwar", "udupi", "malpe", "bhatkal", "kumta",
    # Kerala
    "trivandrum", "kollam", "alappuzha", "kozhikode", "kannur", "beypore",
    # Tamil Nadu
    "rameswaram", "tuticorin", "cuddalore", "puducherry", "kanyakumari",
    # Andhra Pradesh
    "kakinada", "nellore", "machilipatnam", "chirala",
    # Odisha & Bengal
    "paradip", "puri", "digha", "haldia", "mandarmani",
    # Islands
    "portblair", "havelock", "kavaratti", "minicoy",
    # States (for variety)
    "maharashtra", "gujarat", "karnataka", "kerala", "tamilnadu", "andhra", "odisha", "bengal"
]

USERNAME_STYLES = [
    "fisher", "sailor", "captain", "marine", "coast", "ocean", "beach", "port",
    "nav", "sea", "wave", "tide", "surf", "dock", "bay", "reef", "island"
]

USERNAME_NUMBERS = list(range(1, 999))

def generate_dynamic_username() -> str:
    """Generate a unique, realistic social media username"""
    style = random.choice([
        "prefix_suffix",      # coastal_news, ocean_watcher
        "style_location",     # fisher_mumbai, sailor_goa
        "prefix_number",      # marine007, ocean_42
        "location_suffix",    # mumbai_updates, kerala_news
        "prefix_location",    # coastal_kerala, marine_goa
        "style_number",       # fisher123, captain_99
        "word_word_number",   # sea_wave_21, ocean_tide_7
        "simple_word"         # oceanlife, marineworld
    ])

    if style == "prefix_suffix":
        return f"@{random.choice(USERNAME_PREFIXES)}_{random.choice(USERNAME_SUFFIXES)}"
    elif style == "style_location":
        return f"@{random.choice(USERNAME_STYLES)}_{random.choice(USERNAME_LOCATIONS)}"
    elif style == "prefix_number":
        num = random.choice(USERNAME_NUMBERS)
        if random.random() > 0.5:
            return f"@{random.choice(USERNAME_PREFIXES)}{num}"
        else:
            return f"@{random.choice(USERNAME_PREFIXES)}_{num}"
    elif style == "location_suffix":
        return f"@{random.choice(USERNAME_LOCATIONS)}_{random.choice(USERNAME_SUFFIXES)}"
    elif style == "prefix_location":
        return f"@{random.choice(USERNAME_PREFIXES)}_{random.choice(USERNAME_LOCATIONS)}"
    elif style == "style_number":
        num = random.choice(USERNAME_NUMBERS)
        if random.random() > 0.5:
            return f"@{random.choice(USERNAME_STYLES)}{num}"
        else:
            return f"@{random.choice(USERNAME_STYLES)}_{num}"
    elif style == "word_word_number":
        return f"@{random.choice(USERNAME_PREFIXES)}_{random.choice(USERNAME_STYLES)}_{random.randint(1, 99)}"
    else:  # simple_word
        word = random.choice(USERNAME_PREFIXES + USERNAME_STYLES)
        suffix = random.choice(["life", "world", "zone", "hub", "spot", "view", "gram", "feed"])
        return f"@{word}{suffix}"

def generate_multilingual_post() -> Dict[str, Any]:
    """Generate a social media post in random Indian language"""
    languages = list(MULTI_LANGUAGE_POSTS.keys())
    language = random.choice(languages)
    location = random.choice(INDIAN_COASTAL_LOCATIONS)

    # Determine if this should be a disaster post
    is_disaster = random.random() < feed_config["disaster_probability"]

    if is_disaster:
        post_type = "disaster"
        template = random.choice(MULTI_LANGUAGE_POSTS[language]["disaster"])

        # Add disaster-specific parameters
        magnitude = random.randint(15, 25) if "tsunami" in template.lower() else random.randint(3, 9)
        if "cyclone" in template.lower() or "चक्रवात" in template or "புயல்" in template:
            magnitude = random.randint(120, 200)

        expected_disaster = "tsunami" if "tsunami" in template.lower() or "सुनामी" in template or "சுனாமி" in template else \
                          "cyclone" if any(word in template.lower() for word in ["cyclone", "चक्रवात", "புயல்", "ঘূর্ণিঝড়", "ચક્રવાત", "चक्रीवादळ", "తుఫాను", "ಚಂಡಮಾರುತ", "ചുഴലിക്കാറ്റ്"]) else \
                          "oil_spill" if any(word in template.lower() for word in ["oil", "तेल", "எண்ணெய்", "तेल", "તેલ", "तेल", "నూనె", "ತೈಲ", "എണ്ണ"]) else \
                          "earthquake" if any(word in template.lower() for word in ["earthquake", "भूकंप", "भूकंप", "भूकंप", "ભૂકંપ", "भूकंप", "భూకంపం", "ಭೂಕಂಪ", "ഭൂകമ്പം"]) else \
                          "flooding" if any(word in template.lower() for word in ["flood", "बाढ़", "வெள்ளம்", "बाढ़", "પૂર", "पूर", "వరద", "ಪ್ರವಾಹ", "വെള്ളപ്പൊക്കം"]) else "none"

        text = template.format(
            location=location,
            magnitude=magnitude,
            name=random.choice(CYCLONE_NAMES),
            category=random.randint(3, 5),
            depth=random.randint(10, 100)
        )
    else:
        post_type = "normal"
        template = random.choice(MULTI_LANGUAGE_POSTS[language]["normal"])
        expected_disaster = "none"
        text = template.format(location=location)

    platforms = ["twitter", "facebook", "instagram", "news"]
    platform = random.choice(platforms)

    # Generate a unique username for this post
    username = generate_dynamic_username()

    # Vary verification status based on follower count (more followers = more likely verified)
    follower_count = random.randint(100, 100000)
    verified = follower_count > 25000 and random.random() > 0.6

    post = {
        "id": f"post_{int(time.time())}_{random.randint(1000, 9999)}",
        "text": text,
        "platform": platform,
        "language": language,
        "user": {
            "username": username,
            "verified": verified,
            "follower_count": follower_count
        },
        "location": location,  # Use the same location as in the post text
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "engagement": {
            "likes": random.randint(1, 5000) if verified else random.randint(1, 500),
            "shares": random.randint(0, 800) if verified else random.randint(0, 80),
            "comments": random.randint(0, 200) if verified else random.randint(0, 30)
        },
        "expected_disaster_type": expected_disaster,
        "post_type": post_type,
        "analysis_pending": True
    }

    return post

def analyze_post_for_alerts(post: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze post and generate alerts if needed"""
    disaster_keywords = {
        "tsunami": ["tsunami", "सुनामी", "சுனாமி", "সুনামি", "સુનામી", "त्सुनामी", "సునామీ", "ಸುನಾಮಿ", "സുനാമി"],
        "cyclone": ["cyclone", "चक्रवात", "புயல்", "ঘূর্ণিঝড়", "ચક્રવાત", "चक्रीवादळ", "తుఫాను", "ಚಂಡಮಾರುತ", "ചുഴലിക്കാറ്റ്"],
        "earthquake": ["earthquake", "भूकंप", "भूकंप", "भूकंप", "ભૂકંપ", "भूकंप", "భూకంపం", "ಭೂಕಂಪ", "ഭൂകമ്പം"],
        "oil_spill": ["oil spill", "तेल रिसाव", "எண்ணெய் கசிவு", "তেল ছিটে", "તેલ લીકેજ", "तेल गळती", "నూనె కారుట", "ತೈಲ ಸೋರಿಕೆ", "എണ്ണ ചോർച്ച"],
        "flooding": ["flood", "बाढ़", "வெள்ளம்", "বন্যা", "પૂર", "पूर", "వరద", "ಪ್ರವಾಹ", "വെള്ളപ്പൊക്കം"]
    }

    text_lower = post["text"].lower()
    urgency_keywords = ["urgent", "emergency", "critical", "immediate", "evacuate",
                       "आपातकाल", "तुरंत", "अवसर", "తక్షణం", "அவசர", "জরুরি", "તાત્કાલિક"]

    alert_level = "LOW"
    disaster_type = "none"
    relevance_score = 1.0

    # Check for disaster keywords
    for d_type, keywords in disaster_keywords.items():
        for keyword in keywords:
            if keyword in text_lower:
                disaster_type = d_type
                relevance_score = 6.0

                # Check urgency level
                urgency_count = sum(1 for word in urgency_keywords if word in text_lower)
                if urgency_count >= 2:
                    alert_level = "CRITICAL"
                    relevance_score = 9.0
                elif urgency_count == 1:
                    alert_level = "HIGH"
                    relevance_score = 8.0
                else:
                    alert_level = "MEDIUM"
                    relevance_score = 7.0
                break
        if disaster_type != "none":
            break

    # Generate alert if relevance score is high enough
    alert_data = None
    if relevance_score >= feed_config["alert_threshold"]:
        alert_data = {
            "alert_id": str(uuid.uuid4()),
            "post_id": post["id"],
            "disaster_type": disaster_type,
            "alert_level": alert_level,
            "relevance_score": relevance_score,
            "location": post["location"],
            "language": post["language"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": f"{alert_level} {disaster_type} alert detected in {post['location']} ({post['language']})",
            "post_excerpt": post["text"][:100] + "..." if len(post["text"]) > 100 else post["text"]
        }

        # Add to active alerts
        feed_config["active_alerts"].append(alert_data)

        # Keep only last 10 alerts
        if len(feed_config["active_alerts"]) > 10:
            feed_config["active_alerts"] = feed_config["active_alerts"][-10:]

    # Map alert_level to urgency for frontend consistency
    urgency_map = {
        "CRITICAL": "critical",
        "HIGH": "high",
        "MEDIUM": "medium",
        "LOW": "low"
    }

    # Update post with analysis - include 'analysis' object for frontend consistency
    post.update({
        "analysis_pending": False,
        "disaster_type": disaster_type,
        "alert_level": alert_level,
        "relevance_score": relevance_score,
        "alert_generated": alert_data is not None,
        # Add analysis object that frontend expects
        "analysis": {
            "disaster_type": disaster_type,
            "urgency": urgency_map.get(alert_level, "low"),
            "relevance_score": relevance_score * 10,  # Scale to 0-100
            "is_disaster": disaster_type != "none"
        }
    })

    return post

def enhanced_feed_generator():
    """Enhanced background thread function for generating posts"""
    global feed_running, feed_queue, posts_history

    print("🚀 Enhanced multilingual feed generator started")
    print(f"📈 Configuration: Post every {feed_config['post_interval']}s, {feed_config['disaster_probability']*100:.1f}% disaster probability")

    post_count = 0
    alert_count = 0

    while feed_running:
        try:
            # Generate post
            post = generate_multilingual_post()

            # Analyze for alerts
            analyzed_post = analyze_post_for_alerts(post)

            # Add to queue if not full
            if not feed_queue.full():
                feed_queue.put(analyzed_post)

            # Add to history (thread-safe) - keeps last 200 posts
            with posts_history_lock:
                posts_history.append(analyzed_post)
                # Keep only last 200 posts in history
                if len(posts_history) > 200:
                    posts_history[:] = posts_history[-200:]

            post_count += 1

            if analyzed_post.get("alert_generated"):
                alert_count += 1
                print(f"🚨 ALERT #{alert_count}: {analyzed_post['alert_level']} {analyzed_post['disaster_type']} in {analyzed_post['location']} ({analyzed_post['language']})")
                print(f"   Text: {analyzed_post['text'][:80]}...")
            else:
                print(f"📱 Generated post #{post_count}: {analyzed_post['text'][:60]}... ({analyzed_post['language']}, {analyzed_post['disaster_type']})")

            # Status update every 10 posts
            if post_count % 10 == 0:
                print(f"📊 Enhanced Feed Status: {post_count} posts ({post_count * feed_config['post_interval'] / 60:.1f}min), {alert_count} alerts, history: {len(posts_history)}")

            # Wait for next post
            time.sleep(feed_config["post_interval"])

        except Exception as e:
            print(f"❌ Enhanced feed generator error: {e}")
            time.sleep(5)

    print(f"📊 Enhanced feed stopped - {post_count} posts sent, {alert_count} alerts generated")

def start_enhanced_feed(post_interval: int = 8, disaster_probability: float = 0.3) -> Dict[str, Any]:
    """Start the enhanced multilingual feed"""
    global feed_running, feed_thread, feed_queue, posts_history

    if feed_running:
        return {"status": "already_running", "message": "Enhanced feed is already running"}

    # Clear previous session data for fresh start
    feed_config["active_alerts"] = []  # Clear old alerts

    # Clear posts history
    with posts_history_lock:
        posts_history.clear()

    # Clear feed queue
    while not feed_queue.empty():
        try:
            feed_queue.get_nowait()
        except:
            break

    # Update configuration
    feed_config["post_interval"] = max(3, min(30, post_interval))
    feed_config["disaster_probability"] = max(0.0, min(1.0, disaster_probability))

    try:
        feed_running = True
        feed_thread = threading.Thread(target=enhanced_feed_generator, daemon=True)
        feed_thread.start()

        return {
            "status": "started",
            "message": "Enhanced multilingual social media feed started successfully",
            "config": {
                "post_interval": feed_config["post_interval"],
                "disaster_probability": feed_config["disaster_probability"],
                "languages": list(MULTI_LANGUAGE_POSTS.keys())
            }
        }
    except Exception as e:
        feed_running = False
        return {"status": "error", "message": f"Failed to start enhanced feed: {e}"}

def stop_enhanced_feed() -> Dict[str, Any]:
    """Stop the enhanced feed"""
    global feed_running

    if not feed_running:
        return {"status": "not_running", "message": "Enhanced feed is not running"}

    feed_running = False
    return {
        "status": "stopped",
        "message": "Enhanced multilingual social media feed stopped successfully"
    }

def update_feed_config(post_interval: int = None, disaster_probability: float = None) -> Dict[str, Any]:
    """Update feed configuration dynamically"""
    if post_interval is not None:
        feed_config["post_interval"] = max(3, min(30, post_interval))

    if disaster_probability is not None:
        feed_config["disaster_probability"] = max(0.0, min(1.0, disaster_probability))

    return {
        "status": "updated",
        "config": {
            "post_interval": feed_config["post_interval"],
            "disaster_probability": feed_config["disaster_probability"],
            "languages": list(MULTI_LANGUAGE_POSTS.keys())
        }
    }

def get_enhanced_feed_status() -> Dict[str, Any]:
    """Get enhanced feed status"""
    with posts_history_lock:
        history_count = len(posts_history)

    return {
        "feed_running": feed_running,
        "queue_size": feed_queue.qsize(),
        "max_queue_size": feed_queue.maxsize,
        "history_count": history_count,
        "max_history_size": 200,
        "thread_alive": feed_thread.is_alive() if feed_thread else False,
        "config": feed_config.copy(),
        "languages_supported": list(MULTI_LANGUAGE_POSTS.keys()),
        "locations": INDIAN_COASTAL_LOCATIONS,
        "active_alerts_count": len(feed_config["active_alerts"]),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

def get_enhanced_posts(limit: int = 100) -> Dict[str, Any]:
    """Get recent posts from enhanced feed history"""
    # Get posts from history (thread-safe)
    with posts_history_lock:
        # Return most recent posts first (reversed order)
        all_posts = list(reversed(posts_history))
        posts = all_posts[:limit]
        total_count = len(posts_history)

    return {
        "posts": posts,
        "count": len(posts),
        "total_available": total_count,
        "feed_running": feed_running,
        "total_languages": len(MULTI_LANGUAGE_POSTS),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

def get_active_alerts() -> Dict[str, Any]:
    """Get active alerts from the feed"""
    return {
        "alerts": feed_config["active_alerts"],
        "count": len(feed_config["active_alerts"]),
        "alert_threshold": feed_config["alert_threshold"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }