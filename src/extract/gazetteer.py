"""Gazetteers and stoplists for extraction: Indian places, banks, and
Hinglish NER-noise defense."""

from __future__ import annotations

INDIAN_STATES: tuple[str, ...] = (
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya",
    "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim",
    "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand",
    "West Bengal", "Delhi", "Jammu and Kashmir", "Ladakh", "Chandigarh",
    "Puducherry", "Andaman and Nicobar Islands", "Lakshadweep",
    "Dadra and Nagar Haveli and Daman and Diu",
)

INDIAN_CITIES: tuple[str, ...] = (
    "Mumbai", "Pune", "Nagpur", "Nashik", "Aurangabad", "Thane", "Solapur",
    "Bengaluru", "Bangalore", "Mysuru", "Mysore", "Mangaluru", "Hubli",
    "Chennai", "Coimbatore", "Madurai", "Salem", "Tiruchirappalli",
    "Hyderabad", "Warangal", "Secunderabad", "Visakhapatnam", "Vijayawada",
    "Guntur", "Tirupati", "Kochi", "Thiruvananthapuram", "Kozhikode",
    "Thrissur", "Kolkata", "Howrah", "Durgapur", "Siliguri", "Asansol",
    "Bhubaneswar", "Cuttack", "Rourkela", "Patna", "Gaya", "Muzaffarpur",
    "Ranchi", "Jamshedpur", "Dhanbad", "Guwahati", "Dibrugarh", "Silchar",
    "Lucknow", "Kanpur", "Varanasi", "Agra", "Meerut", "Prayagraj",
    "Allahabad", "Ghaziabad", "Noida", "Greater Noida", "Aligarh", "Bareilly",
    "Gorakhpur", "Jhansi", "Mathura", "Dehradun", "Haridwar", "Rishikesh",
    "Jaipur", "Jodhpur", "Udaipur", "Kota", "Ajmer", "Bikaner", "Alwar",
    "Ahmedabad", "Surat", "Vadodara", "Rajkot", "Bhavnagar", "Gandhinagar",
    "Bhopal", "Indore", "Gwalior", "Jabalpur", "Ujjain", "Raipur", "Bhilai",
    "Bilaspur", "Chandigarh", "Ludhiana", "Amritsar", "Jalandhar", "Patiala",
    "Mohali", "Gurgaon", "Gurugram", "Faridabad", "Panipat", "Ambala",
    "Rohtak", "Hisar", "Shimla", "Jammu", "Srinagar", "Panaji", "Margao",
    "Imphal", "Shillong", "Aizawl", "Kohima", "Agartala", "Itanagar",
    "Gangtok", "Puducherry", "Nellore", "Belgaum", "Kolhapur", "Amravati",
    "Sangli", "Akola", "Latur", "Erode", "Vellore", "Tirunelveli",
    "Rajahmundry", "Kakinada", "Anantapur", "Kurnool", "Karimnagar",
    "Nizamabad", "Moradabad", "Saharanpur", "Firozabad", "Etawah",
)

BANKS: tuple[str, ...] = (
    "State Bank of India", "SBI", "HDFC Bank", "HDFC", "ICICI Bank", "ICICI",
    "Axis Bank", "Punjab National Bank", "PNB", "Bank of Baroda",
    "Canara Bank", "Union Bank", "Bank of India", "Indian Bank",
    "Central Bank of India", "IDBI Bank", "IDBI", "Kotak Mahindra Bank",
    "Kotak", "Yes Bank", "IndusInd Bank", "Federal Bank", "Karnataka Bank",
    "South Indian Bank", "Bandhan Bank", "IDFC First Bank", "RBL Bank",
    "UCO Bank", "Indian Overseas Bank", "Punjab and Sind Bank",
)

# Romanized-Hindi function words that spaCy NER sometimes tags as
# entities. Never accept these as an entity of any type.
HINGLISH_STOPLIST: frozenset[str] = frozenset(
    {
        "hai", "hain", "tha", "thi", "the", "ho", "hua", "hui", "gaya",
        "gayi", "gaye", "ka", "ki", "ke", "ko", "se", "me", "mein", "pe",
        "par", "aur", "ya", "na", "nahi", "nahin", "mat", "ab", "phir",
        "kya", "kaise", "kahan", "kab", "kyun", "wo", "woh", "ye", "yeh",
        "is", "us", "un", "in", "sab", "kuch", "koi", "bhi", "to", "hi",
        "bas", "bahut", "thoda", "zyada", "wala", "wale", "wali", "karo",
        "kar", "karna", "diya", "liya", "raha", "rahi", "rahe", "bol",
        "bola", "bole", "batao", "dedo", "ok", "sir", "ji", "bhai",
        "bhaisahab", "please", "malik", "makan", "paisa", "paise", "rupaye",
        "udhaar", "dukan", "dukaan", "gaon", "shahar", "mahina", "mahine",
        "pati", "patni", "vakil", "tareekh", "bacchon", "bachche", "beta",
        "beti", "ghar", "kaam", "kharch", "mushkil", "jaldi", "tarika",
        "chahiye", "milta", "gaya", "saal", "din", "hafta", "warna", "matlab",
    }
)

# Financial and legal acronyms that spaCy sometimes tags as ORG but are
# never parties to a dispute.
ACRONYM_STOPLIST: frozenset[str] = frozenset(
    {
        "neft", "rtgs", "upi", "imps", "otp", "emi", "kyc", "fir", "amc",
        "gst", "rc", "tc", "hr", "pf", "epfo", "noc", "rti", "rera", "mact",
        "cctv", "atm", "pan", "aadhaar", "whatsapp", "linkedin", "sms",
    }
)

_PLACE_LOOKUP: dict[str, str] = {
    p.lower(): p for p in (*INDIAN_STATES, *INDIAN_CITIES)
}


def lookup_indian_place(text: str) -> str | None:
    """Return the canonical place name if text is a known Indian place."""
    return _PLACE_LOOKUP.get(text.strip().lower())


def is_hinglish_noise(text: str) -> bool:
    """True if every token of text is on the Hinglish stoplist or non-alphabetic."""
    tokens = [t for t in text.replace(".", " ").replace(",", " ").split() if t]
    if not tokens:
        return True
    return all(t.lower() in HINGLISH_STOPLIST or not t.isalpha() for t in tokens)
