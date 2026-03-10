#!/usr/bin/env python3
"""
Taara Mandal — Vedic Kundli App (Kivy / Android)
North Indian Chart Style | Parashari System
"""

import math, datetime, io, threading
import urllib.request, urllib.parse, json

# ── Kivy must be configured BEFORE any kivy imports ──────────────────
from kivy.config import Config
Config.set('graphics', 'resizable', True)

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.widget import Widget
from kivy.graphics import Color, Line, Rectangle, Ellipse
from kivy.graphics.instructions import InstructionGroup
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.image import Image as KivyImage

# Try matplotlib for chart rendering
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    import numpy as np
    MPL_AVAILABLE = True
except ImportError:
    MPL_AVAILABLE = False

try:
    import swisseph as swe
    SWE_AVAILABLE = True
except ImportError:
    SWE_AVAILABLE = False

# ─────────────────────────────────────────────────────────────────────
#  COLOUR PALETTE
# ─────────────────────────────────────────────────────────────────────
BG_DARK   = (0.047, 0.102, 0.271, 1)
BG_MED    = (0.067, 0.133, 0.333, 1)
BG_LIGHT  = (0.102, 0.200, 0.439, 1)
GOLD      = (1.0,   0.843, 0.0,   1)
GOLD_HEX  = "#FFD700"
ACCENT    = (0.831, 0.565, 0.039, 1)
FG_LIGHT  = (0.784, 0.847, 0.941, 1)
BTN_GREEN = (0.102, 0.420, 0.235, 1)
BTN_RED   = (0.482, 0.102, 0.102, 1)
BTN_BLUE  = (0.102, 0.231, 0.478, 1)
WHITE     = (1, 1, 1, 1)

# ─────────────────────────────────────────────────────────────────────
#  CONSTANTS  (copied verbatim from original engine)
# ─────────────────────────────────────────────────────────────────────
PLANETS = {
    "Su": {"name": "Sun",     "color": "#E67E22", "swe_id": 0},
    "Mo": {"name": "Moon",    "color": "#C0392B", "swe_id": 1},
    "Ma": {"name": "Mars",    "color": "#C0392B", "swe_id": 4},
    "Me": {"name": "Mercury", "color": "#1A5276", "swe_id": 2},
    "Ju": {"name": "Jupiter", "color": "#7B2FBE", "swe_id": 5},
    "Ve": {"name": "Venus",   "color": "#C0392B", "swe_id": 3},
    "Sa": {"name": "Saturn",  "color": "#784212", "swe_id": 6},
    "Ra": {"name": "Rahu",    "color": "#784212", "swe_id": 10},
    "Ke": {"name": "Ketu",    "color": "#D4700A", "swe_id": None},
    "Ur": {"name": "Uranus",  "color": "#1A8B8B", "swe_id": 7},
    "Ne": {"name": "Neptune", "color": "#1a1a80", "swe_id": 8},
    "Pl": {"name": "Pluto",   "color": "#6B2FBE", "swe_id": 9},
}
RASHI_NAMES = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
               "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]
RASHI_SHORT = ["Ar","Ta","Ge","Ca","Le","Vi","Li","Sc","Sa","Cp","Aq","Pi"]
NAKSHATRA_NAMES = [
    "Ashwini","Bharani","Krittika","Rohini","Mrigashira","Ardra",
    "Punarvasu","Pushya","Ashlesha","Magha","Purva Phalguni","Uttara Phalguni",
    "Hasta","Chitra","Swati","Vishakha","Anuradha","Jyeshtha",
    "Mula","Purva Ashadha","Uttara Ashadha","Shravana","Dhanishtha","Shatabhisha",
    "Purva Bhadrapada","Uttara Bhadrapada","Revati"
]
NAKSHATRA_LORDS = ["Ke","Ve","Su","Mo","Ma","Ra","Ju","Sa","Me"] * 3
EXALTATION   = {"Su":(0,10),"Mo":(1,3),"Ma":(9,28),"Me":(5,15),"Ju":(3,5),"Ve":(11,27),"Sa":(6,20)}
DEBILITATION = {"Su":(6,10),"Mo":(7,3),"Ma":(3,28),"Me":(11,15),"Ju":(9,5),"Ve":(5,27),"Sa":(0,20)}
DASHA_YEARS  = {"Ke":7,"Ve":20,"Su":6,"Mo":10,"Ma":7,"Ra":18,"Ju":16,"Sa":19,"Me":17}
DASHA_ORDER  = ["Ke","Ve","Su","Mo","Ma","Ra","Ju","Sa","Me"]
TOTAL_YEARS  = sum(DASHA_YEARS.values())
_CC_TZ = {
    "IN":5.5,"LK":5.5,"NP":5.75,"MM":6.5,"BD":6.0,"PK":5.0,
    "AF":4.5,"IR":3.5,"SA":3.0,"AE":4.0,"QA":3.0,"KW":3.0,
    "GB":0.0,"DE":1.0,"FR":1.0,"IT":1.0,"ES":1.0,"RU":3.0,
    "CN":8.0,"JP":9.0,"KR":9.0,"SG":8.0,"AU":10.0,
    "US":-5.0,"CA":-5.0,"BR":-3.0,"AR":-3.0,
}
_SLOT_KEYS = [9, 10, 11, 12, 1, 2, 3, 4, 5, 6, 7, 8]

# ─────────────────────────────────────────────────────────────────────
#  ASTRONOMICAL ENGINE  (identical to original, no tkinter dependency)
# ─────────────────────────────────────────────────────────────────────

def geocode_place(place_name: str):
    try:
        q   = urllib.parse.quote(place_name)
        url = (f"https://nominatim.openstreetmap.org/search"
               f"?q={q}&format=json&limit=1&addressdetails=1")
        req = urllib.request.Request(url, headers={"User-Agent": "TaaraMandal/1.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
        if not data:
            return None
        lat = float(data[0]["lat"]); lon = float(data[0]["lon"])
        cc  = data[0].get("address", {}).get("country_code", "").upper()
        tz  = None
        try:
            tz_url = (f"https://timeapi.io/api/TimeZone/coordinate"
                      f"?latitude={lat:.4f}&longitude={lon:.4f}")
            with urllib.request.urlopen(
                    urllib.request.Request(tz_url, headers={"User-Agent": "TaaraMandal/1.0"}),
                    timeout=5) as r2:
                tz_data = json.loads(r2.read())
            offset_s = tz_data.get("currentUtcOffset", {}).get("seconds", None)
            if offset_s is not None:
                tz = round(offset_s / 1800) * 0.5
        except Exception:
            pass
        if tz is None: tz = _CC_TZ.get(cc)
        if tz is None: tz = round(lon / 15 * 2) / 2
        return lat, lon, tz
    except Exception:
        return None

def julian_day(dt, tz_offset):
    ut = dt - datetime.timedelta(hours=tz_offset)
    y, m, d = ut.year, ut.month, ut.day
    h = ut.hour + ut.minute/60 + ut.second/3600
    if m <= 2: y -= 1; m += 12
    A = int(y/100); B = 2 - A + int(A/4)
    return int(365.25*(y+4716)) + int(30.6001*(m+1)) + d + h/24 + B - 1524.5

def sidereal_time(jd, lon):
    T = (jd - 2451545.0) / 36525.0
    theta = 280.46061837 + 360.98564736629*(jd-2451545) + 0.000387933*T**2
    return (theta + lon) % 360

def planet_longitude_approx(planet_key, jd):
    T = (jd - 2451545.0) / 36525.0
    ayanamsa = 23.85 + 50.2388475 / 3600.0 * (jd - 2451545.0) / 365.25
    if planet_key == "Su":
        L = 280.46646 + 36000.76983*T; M = math.radians(357.52911 + 35999.05029*T)
        lon = L + (1.914602 - 0.004817*T)*math.sin(M) + 0.019993*math.sin(2*M)
    elif planet_key == "Mo":
        L = 218.3165 + 481267.8813*T; M = math.radians(134.9634 + 477198.8676*T)
        D = math.radians(297.8502 + 445267.1115*T); F = math.radians(93.2721 + 483202.0175*T)
        lon = L + 6.2888*math.sin(M) + 1.2740*math.sin(2*D-M) + 0.6583*math.sin(2*D) + 0.2136*math.sin(2*M)
    elif planet_key == "Ma":
        L = 355.433 + 19140.2993*T; M = math.radians(319.9940 + 19139.8585*T)
        lon = L + 10.691*math.sin(M) + 0.623*math.sin(2*M)
    elif planet_key == "Me":
        L = 252.251 + 149472.6746*T; M = math.radians(168.6562 + 149472.5153*T)
        lon = L + 23.440*math.sin(M) + 2.996*math.sin(2*M)
    elif planet_key == "Ju":
        L = 34.351 + 3034.9057*T; M = math.radians(20.020 + 3034.6960*T)
        lon = L + 5.555*math.sin(M) + 0.168*math.sin(2*M)
    elif planet_key == "Ve":
        L = 181.979 + 58517.8157*T; M = math.radians(212.2794 + 58517.8039*T)
        lon = L + 0.7758*math.sin(M) + 0.0033*math.sin(2*M)
    elif planet_key == "Sa":
        L = 50.0774 + 1222.1138*T; M = math.radians(317.020 + 1221.5515*T)
        lon = L + 6.3585*math.sin(M) + 0.240*math.sin(2*M)
    elif planet_key == "Ur":
        L = 314.055 + 429.8640561*T; M = math.radians(92.431 + 428.9666270*T)
        lon = L + 0.773*math.sin(M) + 0.038*math.sin(2*M)
    elif planet_key == "Ne":
        L = 304.349 + 219.8554080*T; M = math.radians(276.340 + 219.8812010*T)
        lon = L + 1.258*math.sin(M) + 0.030*math.sin(2*M)
    elif planet_key == "Pl":
        L = 238.929 + 144.9600000*T; M = math.radians(14.882 + 144.9600000*T)
        lon = L + 28.30*math.sin(M) + 4.58*math.sin(2*M)
    elif planet_key == "Ra":
        return calc_rahu(jd)
    else:
        lon = 0.0
    sid = (lon - ayanamsa) % 360
    return sid if sid >= 0 else sid + 360

def calc_ascendant(jd, lat, lon):
    T = (jd - 2451545.0) / 36525.0
    ayanamsa = 23.85 + 50.2388475 / 3600.0 * (jd - 2451545.0) / 365.25
    lst = sidereal_time(jd, lon); ramc = math.radians(lst)
    lat_r = math.radians(lat); eps = math.radians(23.4397 - 0.013 * T)
    num = math.cos(ramc)
    den = -(math.sin(ramc) * math.cos(eps) + math.tan(lat_r) * math.sin(eps))
    asc_trop = math.degrees(math.atan2(num, den))
    if asc_trop < 0: asc_trop += 360
    return (asc_trop - ayanamsa) % 360

def calc_rahu(jd):
    T = (jd - 2451545.0) / 36525.0
    ayanamsa = 23.85 + 50.2388475 / 3600.0 * (jd - 2451545.0) / 365.25
    omega = 125.0445 - 1934.1362*T
    sid = (omega - ayanamsa) % 360
    return sid if sid >= 0 else sid + 360

def get_nakshatra(lon):
    nak_idx = int(lon / (360/27))
    pada = int((lon % (360/27)) / (360/108)) + 1
    return NAKSHATRA_NAMES[nak_idx], pada, NAKSHATRA_LORDS[nak_idx]

def get_sign_degree(lon):
    return int(lon / 30), lon % 30

def is_retrograde(planet_key, jd):
    if planet_key in ("Su","Mo","Ra","Ke"): return False
    l1 = planet_longitude_approx(planet_key, jd - 1)
    l2 = planet_longitude_approx(planet_key, jd + 1)
    return ((l2 - l1 + 360) % 360) > 180

def is_exalted(pk, sign, deg):
    if pk not in EXALTATION: return False
    es, ed = EXALTATION[pk]; return sign == es and abs(deg - ed) < 3

def is_debilitated(pk, sign, deg):
    if pk not in DEBILITATION: return False
    ds, dd = DEBILITATION[pk]; return sign == ds and abs(deg - dd) < 3

def house_from_lagna(planet_sign, lagna_sign):
    return ((planet_sign - lagna_sign) % 12) + 1

def calc_dasha(birth_dt, moon_lon, tz):
    nak_idx = int(moon_lon / (360/27))
    nak_lord = NAKSHATRA_LORDS[nak_idx]
    nak_fraction = (moon_lon % (360/27)) / (360/27)
    start_idx = DASHA_ORDER.index(nak_lord)
    elapsed = DASHA_YEARS[nak_lord] * nak_fraction
    birth_moment = birth_dt - datetime.timedelta(hours=tz)
    start_dt = birth_moment - datetime.timedelta(days=elapsed*365.25)
    dashas = []
    cur = start_dt
    for i in range(9):
        lord = DASHA_ORDER[(start_idx + i) % 9]
        end = cur + datetime.timedelta(days=DASHA_YEARS[lord]*365.25)
        dashas.append((lord, cur, end)); cur = end
    return dashas

def calc_antardasha(maha_lord, maha_start, maha_end):
    dur = (maha_end - maha_start).days
    start_idx = DASHA_ORDER.index(maha_lord)
    antardashas = []; cur = maha_start
    for i in range(9):
        lord = DASHA_ORDER[(start_idx + i) % 9]
        end = cur + datetime.timedelta(days=dur * DASHA_YEARS[lord]/TOTAL_YEARS)
        antardashas.append((lord, cur, end)); cur = end
    return antardashas

# ─────────────────────────────────────────────────────────────────────
#  KUNDLI DATA CLASS
# ─────────────────────────────────────────────────────────────────────

class KundliData:
    def __init__(self):
        self.name = ""; self.dob = None; self.tob = None
        self.place = ""; self.lat = 0.0; self.lon = 0.0; self.tz = 5.5
        self.jd = 0.0; self.lagna_lon = 0.0; self.lagna_sign = 0; self.lagna_deg = 0.0
        self.planet_data = {}; self.lagna_chart = {}; self.navamsa_chart = {}
        self.moon_chart = {}; self.chalit_chart = {}; self.ashtakavarga = {}
        self.transit_chart = {}; self.dashas = []; self.antardashas = []

    def calculate(self):
        dt = datetime.datetime.combine(self.dob, self.tob)
        self.jd = julian_day(dt, self.tz)
        self.lagna_lon = calc_ascendant(self.jd, self.lat, self.lon)
        self.lagna_sign, self.lagna_deg = get_sign_degree(self.lagna_lon)
        planet_keys = ["Su","Mo","Ma","Me","Ju","Ve","Sa","Ra","Ur","Ne","Pl"]
        for pk in planet_keys:
            if SWE_AVAILABLE:
                swe.set_sid_mode(swe.SIDM_LAHIRI)
                result, _ = swe.calc_ut(self.jd, PLANETS[pk]["swe_id"],
                                        swe.FLG_SIDEREAL | swe.FLG_SPEED)
                lon = result[0] % 360; retro = result[3] < 0
            else:
                lon = planet_longitude_approx(pk, self.jd)
                retro = is_retrograde(pk, self.jd)
            sign, deg = get_sign_degree(lon)
            house = house_from_lagna(sign, self.lagna_sign)
            nak, pada, nak_lord = get_nakshatra(lon)
            self.planet_data[pk] = {
                "lon": lon, "sign": sign, "deg": deg, "house": house,
                "nak": nak, "pada": pada, "retro": retro,
                "exalt": is_exalted(pk, sign, deg),
                "debil": is_debilitated(pk, sign, deg),
                "nak_lord": nak_lord,
            }
        ra_lon = self.planet_data["Ra"]["lon"]
        ke_lon = (ra_lon + 180) % 360
        ke_sign, ke_deg = get_sign_degree(ke_lon)
        nak, pada, nl = get_nakshatra(ke_lon)
        self.planet_data["Ke"] = {
            "lon": ke_lon, "sign": ke_sign, "deg": ke_deg,
            "house": house_from_lagna(ke_sign, self.lagna_sign),
            "nak": nak, "pada": pada, "retro": False,
            "exalt": False, "debil": False, "nak_lord": nl,
        }
        self.lagna_chart  = self._build_chart(self.lagna_sign)
        moon_sign = self.planet_data["Mo"]["sign"]
        self.moon_chart   = self._build_chart(moon_sign)
        self.navamsa_chart = self._build_navamsa_chart()
        self.chalit_chart  = self._build_chalit_chart()
        self.ashtakavarga  = self._calc_ashtakavarga()
        now_jd = julian_day(datetime.datetime.utcnow(), 0)
        self.transit_chart = self._build_transit_chart(now_jd)
        la_entry = ("La", f"{int(self.lagna_deg)}", "#D4700A", "")
        self.lagna_chart.setdefault(1, []).insert(0, la_entry)
        mo_lon = self.planet_data["Mo"]["lon"]
        self.dashas = calc_dasha(dt, mo_lon, self.tz)
        now = datetime.datetime.utcnow()
        current_maha = next(((l,s,e) for l,s,e in self.dashas if s <= now <= e), None)
        if current_maha:
            self.antardashas = calc_antardasha(*current_maha)

    def _build_chart(self, lagna_sign):
        chart = {}
        for pk in ["Su","Mo","Ma","Me","Ju","Ve","Sa","Ra","Ke","Ur","Ne","Pl"]:
            pd = self.planet_data[pk]
            house = house_from_lagna(pd["sign"], lagna_sign)
            suffix = ("*" if pd["retro"] else "") + ("↑" if pd["exalt"] else "") + ("↓" if pd["debil"] else "")
            chart.setdefault(house, []).append((pk, f"{int(pd['deg'])}", PLANETS[pk]["color"], suffix))
        return chart

    def _build_navamsa_chart(self):
        nav_lagna_sign = self._navamsa_sign(self.lagna_lon)
        chart = {}
        for pk in ["Su","Mo","Ma","Me","Ju","Ve","Sa","Ra","Ke","Ur","Ne","Pl"]:
            pd = self.planet_data[pk]
            nav_sign = self._navamsa_sign(pd["lon"])
            house = house_from_lagna(nav_sign, nav_lagna_sign)
            chart.setdefault(house, []).append((pk, f"{int(pd['deg'])}", PLANETS[pk]["color"], "*" if pd["retro"] else ""))
        return chart

    def _build_chalit_chart(self):
        chart = {}
        cusps = [(self.lagna_lon + i*30.0) % 360.0 for i in range(12)]
        def bhava_house(plon):
            for h in range(11, -1, -1):
                if ((plon - cusps[h]) % 360.0) < 30.0: return h + 1
            return 1
        for pk in ["Su","Mo","Ma","Me","Ju","Ve","Sa","Ra","Ke","Ur","Ne","Pl"]:
            pd = self.planet_data[pk]
            house = bhava_house(pd["lon"])
            suffix = ("*" if pd["retro"] else "") + ("↑" if pd["exalt"] else "") + ("↓" if pd["debil"] else "")
            chart.setdefault(house, []).append((pk, f"{int(pd['deg'])}", PLANETS[pk]["color"], suffix))
        return chart

    def _calc_ashtakavarga(self):
        RULES = {
            "Su":{"Su":[1,2,4,7,8,9,10,11],"Mo":[3,6,10,11],"Ma":[1,2,4,7,8,9,10,11],
                  "Me":[3,5,6,9,10,11,12],"Ju":[5,6,9,11],"Ve":[6,7,12],"Sa":[1,2,4,7,8,9,10,11],"La":[3,4,6,10,11,12]},
            "Mo":{"Su":[3,6,7,8,10,11],"Mo":[1,3,6,7,10,11],"Ma":[2,3,5,6,9,10,11],
                  "Me":[1,3,4,5,7,8,10,11],"Ju":[1,4,7,8,10,11,12],"Ve":[3,4,5,7,9,10,11],"Sa":[3,5,6,11],"La":[3,6,10,11]},
            "Ma":{"Su":[3,5,6,10,11],"Mo":[3,6,11],"Ma":[1,2,4,7,8,10,11],
                  "Me":[3,5,6,11],"Ju":[6,10,11,12],"Ve":[6,8,11,12],"Sa":[1,4,7,8,9,10,11],"La":[1,3,6,10,11]},
            "Me":{"Su":[5,6,9,11,12],"Mo":[2,4,6,8,10,11],"Ma":[1,2,4,7,8,9,10,11],
                  "Me":[1,3,5,6,9,10,11,12],"Ju":[6,8,11,12],"Ve":[1,2,3,4,5,8,9,11],"Sa":[1,2,4,7,8,9,10,11],"La":[1,2,4,6,8,10,11]},
            "Ju":{"Su":[1,2,3,4,7,8,9,10,11],"Mo":[2,5,7,9,11],"Ma":[1,2,4,7,8,10,11],
                  "Me":[1,2,4,5,6,9,10,11],"Ju":[1,2,3,4,7,8,10,11],"Ve":[2,5,6,9,10,11],"Sa":[3,5,6,12],"La":[1,2,4,5,6,7,9,10,11]},
            "Ve":{"Su":[8,11,12],"Mo":[1,2,3,4,5,8,9,11,12],"Ma":[3,4,6,9,11,12],
                  "Me":[3,5,6,9,11],"Ju":[5,8,9,10,11],"Ve":[1,2,3,4,5,8,9,10,11],"Sa":[3,4,5,8,9,10,11],"La":[1,2,3,4,5,8,9,11]},
            "Sa":{"Su":[1,2,4,7,8,10,11],"Mo":[3,6,11],"Ma":[3,5,6,10,11,12],
                  "Me":[6,8,9,10,11,12],"Ju":[5,6,11,12],"Ve":[6,11,12],"Sa":[3,5,6,11],"La":[1,3,4,6,10,11]},
        }
        ps = {pk: self.planet_data[pk]["sign"] for pk in ["Su","Mo","Ma","Me","Ju","Ve","Sa"]}
        result = {}
        for planet, rules in RULES.items():
            bindus = [0]*12
            for contributor, positions in rules.items():
                ref = self.lagna_sign if contributor == "La" else ps.get(contributor, 0)
                for pos in positions:
                    bindus[(ref + pos - 1) % 12] += 1
            result[planet] = bindus
        result["SAV"] = [sum(result[p][r] for p in RULES) for r in range(12)]
        return result

    def _build_transit_chart(self, jd):
        chart = {}
        for pk in ["Su","Mo","Ma","Me","Ju","Ve","Sa","Ra","Ur","Ne","Pl"]:
            lon = planet_longitude_approx(pk, jd)
            sign, deg = get_sign_degree(lon)
            house = house_from_lagna(sign, self.lagna_sign)
            chart.setdefault(house, []).append((pk, f"{int(deg)}", PLANETS[pk]["color"], ""))
        ke_lon = (planet_longitude_approx("Ra", jd) + 180) % 360
        ke_sign, ke_deg = get_sign_degree(ke_lon)
        chart.setdefault(house_from_lagna(ke_sign, self.lagna_sign), []).append(
            ("Ke", f"{int(ke_deg)}", PLANETS["Ke"]["color"], ""))
        return chart

    def _navamsa_sign(self, lon):
        sign = int(lon/30); pos = lon % 30
        return (sign*9 + int(pos/(30/9))) % 12

    def manglik_check(self):
        return self.planet_data.get("Ma", {}).get("house", 0) in (1,2,4,7,8,12)

    def kaal_sarp_check(self):
        ra_lon = self.planet_data.get("Ra", {}).get("lon", 0)
        ke_lon = self.planet_data.get("Ke", {}).get("lon", 0)
        lons = [self.planet_data[p]["lon"] for p in ["Su","Mo","Ma","Me","Ju","Ve","Sa"] if p in self.planet_data]
        span = (ke_lon - ra_lon) % 360
        if span > 0 and all(((l - ra_lon) % 360) < span for l in lons):
            names = {1:"Anant",2:"Kulik",3:"Vasuki",4:"Shankhpal",5:"Padma",6:"Mahapadma",
                     7:"Takshak",8:"Karkotak",9:"Shankhnaad",10:"Patak",11:"Vishadhar",12:"Sheshnag"}
            return True, names.get(self.planet_data.get("Ra",{}).get("house",1), "Kaal Sarp")
        return False, ""

    def sadhesati_check(self):
        mo_s = self.planet_data.get("Mo",{}).get("sign",-1)
        sa_s = self.planet_data.get("Sa",{}).get("sign",-1)
        return mo_s >= 0 and sa_s >= 0 and ((sa_s - mo_s) % 12) in (0,1,11)

# ─────────────────────────────────────────────────────────────────────
#  CHART DRAWING  (matplotlib → PNG bytes → Kivy Image)
# ─────────────────────────────────────────────────────────────────────

def compute_house_positions():
    pad = 0.06; L,R,T,B = pad, 1-pad, pad, 1-pad
    MX = (L+R)/2; MY = (T+B)/2; W = R-L; H = B-T
    P1 = (L+W/4, T+H/4); P2 = (R-W/4, T+H/4)
    P3 = (R-W/4, T+3*H/4); P4 = (L+W/4, T+3*H/4)
    C  = (MX, MY)
    def avg(*pts):
        return (sum(p[0] for p in pts)/len(pts), sum(p[1] for p in pts)/len(pts))
    raw = {
        9: avg((MX,T),P2,C,P1), 8: avg((MX,T),(R,T),P2), 7: avg((R,T),(R,MY),P2),
        6: avg(P2,(R,MY),P3,C), 5: avg((R,MY),P3,(R,B)), 4: avg(P3,(MX,B),(R,B)),
        3: avg(C,P3,(MX,B),P4), 2: avg((MX,B),P4,(L,B)), 1: avg(P4,(L,MY),(L,B)),
       12: avg(P1,C,P4,(L,MY)),11: avg((L,T),P1,(L,MY)),10: avg((L,T),(MX,T),P1),
    }
    positions = {(idx+1): raw[slot] for idx, slot in enumerate(_SLOT_KEYS)}
    return positions, (L,R,T,B,MX,MY,W,H,P1,P2,P3,P4)

def render_kundli_chart_to_png(chart_data, title, lagna_sign, size=600):
    if not MPL_AVAILABLE:
        return None
    fig, ax = plt.subplots(figsize=(size/100, size/100), dpi=100)
    fig.patch.set_facecolor("#0c1a45")
    ax.set_xlim(0,1); ax.set_ylim(0,1); ax.set_aspect("equal"); ax.axis("off")
    ax.set_facecolor("#0c1a45")
    positions, geo = compute_house_positions()
    L,R,T,B,MX,MY,W,H,P1,P2,P3,P4 = geo
    def fy(y): return 1.0 - y
    ax.add_patch(patches.Rectangle((L, fy(B)), W, H, linewidth=0, facecolor="white", zorder=1))
    GOLD = "#D4900A"; LW = 1.5
    def line(x0,y0,x1,y1):
        ax.plot([x0,x1],[fy(y0),fy(y1)], color=GOLD, linewidth=LW, zorder=3)
    line(L,T,R,T); line(R,T,R,B); line(R,B,L,B); line(L,B,L,T)
    line(L,T,R,B); line(R,T,L,B)
    line(MX,T,R,MY); line(R,MY,MX,B); line(MX,B,L,MY); line(L,MY,MX,T)
    OFF=0.040; FS_H=7; FS_R=14; FS_D=7; FS_P=12; LH=0.060
    for house_num, (cx,cy) in positions.items():
        vis_y = fy(cy)
        planets = chart_data.get(house_num, [])
        rashi_idx = (lagna_sign + house_num - 1) % 12
        ax.text(cx-OFF, vis_y+OFF, str(house_num), ha="center", va="center",
                fontsize=FS_H, color="#AAAAAA", fontfamily="serif", zorder=4)
        ax.text(cx+OFF, vis_y+OFF, str(rashi_idx+1), ha="center", va="center",
                fontsize=FS_R, color="#0A2A8B", fontfamily="serif", fontweight="bold", zorder=5)
        if not planets: continue
        total_h = len(planets)*LH
        start_y = vis_y - total_h/2 + LH*0.4
        for i, (name, deg_str, color, suffix) in enumerate(planets):
            py = start_y + i*LH
            ax.text(cx, py-0.015, deg_str, ha="center", va="center",
                    fontsize=FS_D, color=color, fontweight="bold", fontfamily="serif", zorder=5)
            ax.text(cx, py+0.013, name+suffix, ha="center", va="center",
                    fontsize=FS_P, color=color, fontweight="bold", fontfamily="serif", zorder=5)
    ax.set_title(title, color="#FFD700", fontsize=12, fontweight="bold", pad=6, fontfamily="serif")
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return buf.read()

# ─────────────────────────────────────────────────────────────────────
#  HELPER WIDGETS
# ─────────────────────────────────────────────────────────────────────

def gold_label(text, font_size=sp(14), bold=False, **kwargs):
    return Label(text=text, color=GOLD, font_size=font_size,
                 bold=bold, **kwargs)

def styled_button(text, bg_color=BTN_BLUE, font_size=sp(14), **kwargs):
    btn = Button(text=text, font_size=font_size,
                 background_normal="", background_color=bg_color,
                 color=GOLD, bold=True, **kwargs)
    return btn

def styled_input(hint="", default="", **kwargs):
    return TextInput(
        text=default, hint_text=hint,
        background_color=(0.118, 0.235, 0.478, 1),
        foreground_color=WHITE,
        hint_text_color=(0.5, 0.6, 0.8, 1),
        cursor_color=GOLD,
        font_size=sp(15),
        multiline=False, **kwargs
    )

def section_divider():
    w = Widget(size_hint_y=None, height=dp(1))
    with w.canvas:
        Color(*ACCENT)
        Rectangle(pos=w.pos, size=w.size)
    w.bind(pos=lambda i, v: setattr(w.canvas.children[-1], 'pos', v))
    w.bind(size=lambda i, v: setattr(w.canvas.children[-1], 'size', v))
    return w

# ─────────────────────────────────────────────────────────────────────
#  SCREENS
# ─────────────────────────────────────────────────────────────────────

class HomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10))
        with root.canvas.before:
            Color(*BG_DARK)
            self._bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=self._update_bg, size=self._update_bg)

        # Title
        root.add_widget(Widget(size_hint_y=None, height=dp(20)))
        root.add_widget(gold_label("✦  TAARA MANDAL  ✦", font_size=sp(26), bold=True,
                                   size_hint_y=None, height=dp(50)))
        root.add_widget(gold_label("Vedic Kundli · North Indian Style", font_size=sp(14),
                                   color=FG_LIGHT, size_hint_y=None, height=dp(30)))
        root.add_widget(section_divider())
        root.add_widget(Widget(size_hint_y=None, height=dp(20)))

        # Buttons
        btn_gen = styled_button("⊕  New Kundli", BTN_GREEN, size_hint_y=None, height=dp(55))
        btn_gen.bind(on_press=lambda x: self._go("input"))
        root.add_widget(btn_gen)

        root.add_widget(Widget(size_hint_y=None, height=dp(10)))

        btn_about = styled_button("ℹ  About", BTN_BLUE, size_hint_y=None, height=dp(45))
        btn_about.bind(on_press=self._show_about)
        root.add_widget(btn_about)

        root.add_widget(Widget())  # spacer
        self.add_widget(root)

    def _update_bg(self, *args):
        self._bg.pos = self.children[0].pos
        self._bg.size = self.children[0].size

    def _go(self, screen):
        self.manager.transition = SlideTransition(direction="left")
        self.manager.current = screen

    def _show_about(self, *args):
        content = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(8))
        content.add_widget(Label(
            text="Taara Mandal\nVedic Kundli Software\n\nNorth Indian Style | Parashari System\n\nAstronomical engine uses VSOP87 approximations\n(pyswisseph when available)\n\nGeocoding: OpenStreetMap Nominatim\nTimezone: timeapi.io",
            color=FG_LIGHT, font_size=sp(13), halign="center", valign="middle"
        ))
        close = styled_button("Close", BTN_BLUE, size_hint_y=None, height=dp(44))
        content.add_widget(close)
        popup = Popup(title="About", content=content,
                      size_hint=(0.85, 0.6),
                      title_color=list(GOLD),
                      background_color=list(BG_MED))
        close.bind(on_press=popup.dismiss)
        popup.open()


class InputScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._kundli = None
        root = BoxLayout(orientation="vertical")
        with root.canvas.before:
            Color(*BG_DARK)
            self._bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=self._upbg, size=self._upbg)

        # Top bar
        topbar = BoxLayout(size_hint_y=None, height=dp(50),
                           padding=[dp(8),0], spacing=dp(8))
        with topbar.canvas.before:
            Color(*BG_MED)
            self._tbbg = Rectangle(pos=topbar.pos, size=topbar.size)
        topbar.bind(pos=self._uptb, size=self._uptb)
        back = styled_button("← Back", BTN_BLUE, size_hint_x=None, width=dp(80))
        back.bind(on_press=lambda x: self._go_back())
        topbar.add_widget(back)
        topbar.add_widget(gold_label("Birth Details", font_size=sp(18), bold=True))
        root.add_widget(topbar)

        scroll = ScrollView()
        form = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10),
                         size_hint_y=None)
        form.bind(minimum_height=form.setter("height"))

        def row(label, widget):
            r = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
            r.add_widget(Label(text=label, color=FG_LIGHT, font_size=sp(13),
                               size_hint_x=0.32, halign="right", valign="middle"))
            r.add_widget(widget)
            form.add_widget(r)

        self.inp_name  = styled_input("Full name", "")
        self.inp_place = styled_input("City, Country", "")
        self.inp_lat   = styled_input("e.g. 28.6139", "")
        self.inp_lon   = styled_input("e.g. 77.2090", "")
        self.inp_tz    = styled_input("e.g. 5.5", "5.5")

        row("Name", self.inp_name)
        row("Place", self.inp_place)

        # Date row
        date_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(4))
        date_row.add_widget(Label(text="Date", color=FG_LIGHT, font_size=sp(13),
                                  size_hint_x=0.28, halign="right", valign="middle"))
        self.inp_day   = styled_input("DD",   "1",   size_hint_x=0.22)
        self.inp_month = styled_input("MM",   "1",   size_hint_x=0.22)
        self.inp_year  = styled_input("YYYY", "1990",size_hint_x=0.28)
        date_row.add_widget(self.inp_day)
        date_row.add_widget(Label(text="/", color=FG_LIGHT, font_size=sp(16), size_hint_x=None, width=dp(12)))
        date_row.add_widget(self.inp_month)
        date_row.add_widget(Label(text="/", color=FG_LIGHT, font_size=sp(16), size_hint_x=None, width=dp(12)))
        date_row.add_widget(self.inp_year)
        form.add_widget(date_row)

        # Time row
        time_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(4))
        time_row.add_widget(Label(text="Time", color=FG_LIGHT, font_size=sp(13),
                                  size_hint_x=0.28, halign="right", valign="middle"))
        self.inp_hour = styled_input("HH", "12", size_hint_x=0.22)
        self.inp_min  = styled_input("MM", "0",  size_hint_x=0.22)
        self.inp_sec  = styled_input("SS", "0",  size_hint_x=0.22)
        time_row.add_widget(self.inp_hour)
        time_row.add_widget(Label(text=":", color=FG_LIGHT, font_size=sp(16), size_hint_x=None, width=dp(12)))
        time_row.add_widget(self.inp_min)
        time_row.add_widget(Label(text=":", color=FG_LIGHT, font_size=sp(16), size_hint_x=None, width=dp(12)))
        time_row.add_widget(self.inp_sec)
        form.add_widget(time_row)

        row("Latitude",  self.inp_lat)
        row("Longitude", self.inp_lon)
        row("Timezone",  self.inp_tz)

        # Auto locate button
        btn_loc = styled_button("📍  Auto Lat / Lon / TZ from Place", BTN_BLUE,
                                size_hint_y=None, height=dp(44))
        btn_loc.bind(on_press=self._auto_locate)
        form.add_widget(btn_loc)

        self.status_lbl = Label(text="Enter birth details above.",
                                color=FG_LIGHT, font_size=sp(12),
                                size_hint_y=None, height=dp(40))
        form.add_widget(self.status_lbl)

        btn_gen = styled_button("⊕  Generate Kundli", BTN_GREEN,
                                size_hint_y=None, height=dp(55))
        btn_gen.bind(on_press=self._generate)
        form.add_widget(btn_gen)
        form.add_widget(Widget(size_hint_y=None, height=dp(30)))

        scroll.add_widget(form)
        root.add_widget(scroll)
        self.add_widget(root)

    def _upbg(self, *a):
        self._bg.pos = self.children[0].pos
        self._bg.size = self.children[0].size
    def _uptb(self, *a):
        self._tbbg.pos = self.children[0].children[-1].pos
        self._tbbg.size = self.children[0].children[-1].size
    def _go_back(self):
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "home"

    def _auto_locate(self, *args):
        place = self.inp_place.text.strip()
        if not place:
            self.status_lbl.text = "Please enter a place name first."; return
        self.status_lbl.text = "🔍 Looking up location… (needs internet)"
        def lookup():
            result = geocode_place(place)
            def update(dt):
                if result:
                    lat, lon, tz = result
                    self.inp_lat.text = f"{lat:.4f}"
                    self.inp_lon.text = f"{lon:.4f}"
                    self.inp_tz.text  = str(tz)
                    self.status_lbl.text = f"✓ Found: {lat:.3f}, {lon:.3f}  TZ={tz}"
                else:
                    self.status_lbl.text = "✗ Place not found. Check internet / spelling."
            Clock.schedule_once(update)
        threading.Thread(target=lookup, daemon=True).start()

    def _generate(self, *args):
        try:
            day   = int(self.inp_day.text)
            month = int(self.inp_month.text)
            year  = int(self.inp_year.text)
            hour  = int(self.inp_hour.text)
            minute= int(self.inp_min.text)
            sec   = int(self.inp_sec.text)
            lat   = float(self.inp_lat.text)
            lon_v = float(self.inp_lon.text)
            tz    = float(self.inp_tz.text)
        except ValueError as e:
            self.status_lbl.text = f"✗ Invalid input: {e}"; return

        self.status_lbl.text = "⏳ Calculating…"

        def calc():
            try:
                k = KundliData()
                k.name  = self.inp_name.text.strip() or "Unknown"
                k.place = self.inp_place.text.strip()
                k.dob   = datetime.date(year, month, day)
                k.tob   = datetime.time(hour, minute, sec)
                k.lat = lat; k.lon = lon_v; k.tz = tz
                k.calculate()
                def go(dt):
                    self.status_lbl.text = "✓ Done!"
                    self.manager.get_screen("result").load_kundli(k)
                    self.manager.transition = SlideTransition(direction="left")
                    self.manager.current = "result"
                Clock.schedule_once(go)
            except Exception as e:
                def err(dt):
                    self.status_lbl.text = f"✗ Error: {e}"
                Clock.schedule_once(err)

        threading.Thread(target=calc, daemon=True).start()


class ResultScreen(Screen):
    TABS = ["Basic", "Lagna", "Navamsa", "Moon", "Chalit", "Transit", "Dasha", "Doshas"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._kundli = None
        self._active_tab = "Basic"
        root = BoxLayout(orientation="vertical")
        with root.canvas.before:
            Color(*BG_DARK)
            self._bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=self._upbg, size=self._upbg)

        # Top bar
        topbar = BoxLayout(size_hint_y=None, height=dp(50),
                           padding=[dp(8),0], spacing=dp(8))
        with topbar.canvas.before:
            Color(*BG_MED)
            self._tbbg = Rectangle(pos=topbar.pos, size=topbar.size)
        topbar.bind(pos=self._uptb, size=self._uptb)
        back = styled_button("← Back", BTN_BLUE, size_hint_x=None, width=dp(80))
        back.bind(on_press=lambda x: self._go_back())
        topbar.add_widget(back)
        self.title_lbl = gold_label("Kundli", font_size=sp(17), bold=True)
        topbar.add_widget(self.title_lbl)
        root.add_widget(topbar)

        # Tab bar (scrollable)
        tab_scroll = ScrollView(size_hint_y=None, height=dp(44),
                                do_scroll_y=False, bar_width=0)
        tab_inner = BoxLayout(size_hint_x=None, spacing=dp(4), padding=[dp(4),dp(4)])
        tab_inner.bind(minimum_width=tab_inner.setter("width"))
        self._tab_buttons = {}
        for t in self.TABS:
            btn = Button(
                text=t, font_size=sp(13), bold=True,
                size_hint=(None, None), width=dp(80), height=dp(36),
                background_normal="", background_color=list(BG_LIGHT),
                color=list(FG_LIGHT)
            )
            btn.bind(on_press=lambda x, t=t: self._switch_tab(t))
            tab_inner.add_widget(btn)
            self._tab_buttons[t] = btn
        tab_scroll.add_widget(tab_inner)
        root.add_widget(tab_scroll)

        # Content area
        self.content_area = BoxLayout(orientation="vertical")
        root.add_widget(self.content_area)
        self.add_widget(root)

    def _upbg(self, *a):
        self._bg.pos = self.children[0].pos
        self._bg.size = self.children[0].size
    def _uptb(self, *a):
        self._tbbg.pos = self.children[0].children[-1].pos
        self._tbbg.size = self.children[0].children[-1].size
    def _go_back(self):
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "input"

    def load_kundli(self, k: KundliData):
        self._kundli = k
        self.title_lbl.text = f"✦ {k.name}"
        self._switch_tab("Basic")

    def _switch_tab(self, tab):
        self._active_tab = tab
        for t, btn in self._tab_buttons.items():
            btn.background_color = list(ACCENT) if t == tab else list(BG_LIGHT)
            btn.color = [1,1,1,1] if t == tab else list(FG_LIGHT)
        self.content_area.clear_widgets()
        if self._kundli is None: return
        k = self._kundli
        if tab == "Basic":       self.content_area.add_widget(self._build_basic(k))
        elif tab == "Lagna":     self._build_chart_tab(k.lagna_chart, f"Lagna — {RASHI_NAMES[k.lagna_sign]}", k.lagna_sign)
        elif tab == "Navamsa":   self._build_chart_tab(k.navamsa_chart, f"Navamsa (D9) — {RASHI_NAMES[k._navamsa_sign(k.lagna_lon)]}", k._navamsa_sign(k.lagna_lon))
        elif tab == "Moon":      self._build_chart_tab(k.moon_chart, f"Moon Chart — {RASHI_NAMES[k.planet_data['Mo']['sign']]}", k.planet_data["Mo"]["sign"])
        elif tab == "Chalit":    self._build_chart_tab(k.chalit_chart, f"Chalit (Bhava) — {RASHI_NAMES[k.lagna_sign]}", k.lagna_sign)
        elif tab == "Transit":   self._build_chart_tab(k.transit_chart, "Transit — Current Sky", k.lagna_sign)
        elif tab == "Dasha":     self.content_area.add_widget(self._build_dasha(k))
        elif tab == "Doshas":    self.content_area.add_widget(self._build_doshas(k))

    def _build_basic(self, k: KundliData):
        scroll = ScrollView()
        layout = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(6), size_hint_y=None)
        layout.bind(minimum_height=layout.setter("height"))

        def hdr(text):
            layout.add_widget(gold_label(text, font_size=sp(15), bold=True,
                                         size_hint_y=None, height=dp(30)))
            layout.add_widget(section_divider())

        def kv(k_txt, v_txt, v_color=None):
            row = BoxLayout(size_hint_y=None, height=dp(28), spacing=dp(8))
            row.add_widget(Label(text=k_txt, color=FG_LIGHT, font_size=sp(13),
                                 size_hint_x=0.42, halign="right", valign="middle"))
            vc = v_color or list(WHITE)
            row.add_widget(Label(text=v_txt, color=vc, font_size=sp(13), bold=True,
                                 size_hint_x=0.58, halign="left", valign="middle"))
            layout.add_widget(row)

        # Birth info
        hdr("BIRTH DETAILS")
        kv("Name", k.name)
        kv("Date", k.dob.strftime("%d %B %Y") if k.dob else "—")
        kv("Time", k.tob.strftime("%H:%M:%S") if k.tob else "—")
        kv("Place", k.place or "—")
        kv("Lat / Lon", f"{k.lat:.3f} / {k.lon:.3f}")
        kv("Timezone", f"UTC+{k.tz}")
        kv("Lagna", f"{RASHI_NAMES[k.lagna_sign]} ({k.lagna_deg:.1f}°)")
        kv("Moon Sign", RASHI_NAMES[k.planet_data["Mo"]["sign"]])
        mo = k.planet_data["Mo"]
        kv("Moon Nakshatra", f"{mo['nak']} Pada {mo['pada']}")

        layout.add_widget(Widget(size_hint_y=None, height=dp(8)))
        hdr("PLANET POSITIONS")

        # Planet table header
        hdr_row = BoxLayout(size_hint_y=None, height=dp(26))
        for txt, sx in [("Planet",0.22),("Sign",0.22),("Deg°",0.14),
                        ("H",0.08),("Nakshatra",0.24),("Status",0.10)]:
            hdr_row.add_widget(Label(text=txt, color=list(GOLD), font_size=sp(11),
                                     bold=True, size_hint_x=sx))
        layout.add_widget(hdr_row)
        layout.add_widget(section_divider())

        all_pks = ["Su","Mo","Ma","Me","Ju","Ve","Sa","Ra","Ke","Ur","Ne","Pl"]
        for i, pk in enumerate(all_pks):
            if pk not in k.planet_data: continue
            pd = k.planet_data[pk]
            tags = []
            if pd.get("exalt"): tags.append("Ex")
            if pd.get("debil"): tags.append("Db")
            if pd.get("retro"): tags.append("Re")
            row = BoxLayout(size_hint_y=None, height=dp(26),
                            background_color=BG_LIGHT if i%2==0 else BG_MED)
            def lbl(txt, sx, col=None):
                return Label(text=txt, color=col or list(FG_LIGHT), font_size=sp(11),
                             size_hint_x=sx, halign="center", valign="middle")
            row.add_widget(lbl(PLANETS[pk]["name"], 0.22))
            row.add_widget(lbl(RASHI_NAMES[pd["sign"]], 0.22))
            row.add_widget(lbl(f"{pd['deg']:.1f}", 0.14))
            row.add_widget(lbl(str(pd["house"]), 0.08))
            row.add_widget(lbl(pd["nak"], 0.24))
            row.add_widget(lbl(",".join(tags) if tags else "—", 0.10,
                              col=[1,0.4,0.4,1] if "Db" in tags else
                                  [0.4,1,0.4,1] if "Ex" in tags else list(FG_LIGHT)))
            layout.add_widget(row)

        scroll.add_widget(layout)
        return scroll

    def _build_chart_tab(self, chart_data, title, lagna_sign):
        if not MPL_AVAILABLE:
            self.content_area.add_widget(Label(
                text="matplotlib not available.\nInstall matplotlib to view charts.",
                color=FG_LIGHT, font_size=sp(15)))
            return

        loading = Label(text="⏳ Rendering chart…", color=list(GOLD),
                        font_size=sp(16))
        self.content_area.add_widget(loading)

        def render():
            png = render_kundli_chart_to_png(chart_data, title, lagna_sign, size=700)
            def show(dt):
                self.content_area.clear_widgets()
                if png is None:
                    self.content_area.add_widget(Label(text="Chart render failed.",
                                                       color=list(FG_LIGHT)))
                    return
                from kivy.core.image import Image as CoreImage
                core_img = CoreImage(io.BytesIO(png), ext="png")
                img_widget = KivyImage(texture=core_img.texture)
                scroll = ScrollView()
                scroll.add_widget(img_widget)
                self.content_area.add_widget(scroll)
            Clock.schedule_once(show)

        threading.Thread(target=render, daemon=True).start()

    def _build_dasha(self, k: KundliData):
        scroll = ScrollView()
        layout = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(6), size_hint_y=None)
        layout.bind(minimum_height=layout.setter("height"))
        layout.add_widget(gold_label("VIMSHOTTARI DASHA", font_size=sp(15), bold=True,
                                     size_hint_y=None, height=dp(30)))
        layout.add_widget(section_divider())

        now = datetime.datetime.utcnow()
        for lord, start, end in k.dashas:
            is_active = start <= now <= end
            row = BoxLayout(size_hint_y=None, height=dp(36),
                            padding=[dp(8),0])
            with row.canvas.before:
                Color(*ACCENT if is_active else BG_LIGHT)
                Rectangle(pos=row.pos, size=row.size)
            row.bind(pos=lambda w,v: None, size=lambda w,v: None)
            row.add_widget(Label(
                text=("▶ " if is_active else "  ") + PLANETS.get(lord, {}).get("name", lord),
                color=[1,1,0.4,1] if is_active else list(FG_LIGHT),
                font_size=sp(13), bold=is_active, size_hint_x=0.25))
            row.add_widget(Label(text=start.strftime("%b %Y"), color=list(FG_LIGHT),
                                 font_size=sp(12), size_hint_x=0.25))
            row.add_widget(Label(text=end.strftime("%b %Y"), color=list(FG_LIGHT),
                                 font_size=sp(12), size_hint_x=0.25))
            yrs = round((end-start).days/365.25, 1)
            row.add_widget(Label(text=f"{yrs} yr", color=list(FG_LIGHT),
                                 font_size=sp(12), size_hint_x=0.25))
            layout.add_widget(row)

        if k.antardashas:
            layout.add_widget(Widget(size_hint_y=None, height=dp(12)))
            layout.add_widget(gold_label("CURRENT ANTARDASHA", font_size=sp(14), bold=True,
                                         size_hint_y=None, height=dp(28)))
            layout.add_widget(section_divider())
            for lord, start, end in k.antardashas:
                is_active = start <= now <= end
                row = BoxLayout(size_hint_y=None, height=dp(30), padding=[dp(8),0])
                row.add_widget(Label(
                    text=("▶ " if is_active else "  ") + PLANETS.get(lord, {}).get("name", lord),
                    color=[1,1,0.4,1] if is_active else list(FG_LIGHT),
                    font_size=sp(12), bold=is_active, size_hint_x=0.30))
                mo = round((end-start).days/30.44)
                row.add_widget(Label(text=f"{start.strftime('%b %Y')} – {end.strftime('%b %Y')}  ({mo} mo)",
                                     color=list(FG_LIGHT), font_size=sp(11), size_hint_x=0.70))
                layout.add_widget(row)

        scroll.add_widget(layout)
        return scroll

    def _build_doshas(self, k: KundliData):
        scroll = ScrollView()
        layout = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8), size_hint_y=None)
        layout.bind(minimum_height=layout.setter("height"))

        def dosha_row(name, present, detail=""):
            row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(10), padding=[dp(4),0])
            color_bg = [0.5,0.1,0.1,0.7] if present else [0.1,0.4,0.1,0.7]
            with row.canvas.before:
                Color(*color_bg)
                Rectangle(pos=row.pos, size=row.size)
            row.add_widget(Label(text=name, color=list(GOLD), font_size=sp(13), bold=True,
                                 size_hint_x=0.38))
            row.add_widget(Label(
                text="YES — " + detail if present else "No",
                color=[1,0.5,0.5,1] if present else [0.5,1,0.5,1],
                font_size=sp(12), size_hint_x=0.62, halign="left", valign="middle"))
            layout.add_widget(row)

        layout.add_widget(gold_label("DOSHAS & YOGAS", font_size=sp(15), bold=True,
                                     size_hint_y=None, height=dp(30)))
        layout.add_widget(section_divider())

        manglik = k.manglik_check()
        dosha_row("Manglik Dosha", manglik,
                  f"Mars in H{k.planet_data['Ma']['house']}" if manglik else "")

        ks, ks_name = k.kaal_sarp_check()
        dosha_row("Kaal Sarp Yoga", ks, ks_name)

        sadhe = k.sadhesati_check()
        dosha_row("Sade Sati", sadhe, "Saturn near Moon sign")

        # Gaja Kesari
        mo_h = k.planet_data.get("Mo",{}).get("house",0)
        ju_h = k.planet_data.get("Ju",{}).get("house",0)
        gk = mo_h and ju_h and (((ju_h-mo_h)%12)+1) in (1,4,7,10)
        dosha_row("Gaja Kesari Yoga", gk, "Jupiter kendra from Moon")

        # Budha-Aditya
        ba = k.planet_data.get("Su",{}).get("sign") == k.planet_data.get("Me",{}).get("sign")
        dosha_row("Budha-Aditya Yoga", ba, "Sun + Mercury same sign")

        # Pitra Dosha
        su_h = k.planet_data.get("Su",{}).get("house",0)
        ra_h = k.planet_data.get("Ra",{}).get("house",0)
        pitra = su_h == ra_h or su_h == 9
        dosha_row("Pitra Dosha", pitra,
                  f"Sun-Rahu H{su_h}" if su_h==ra_h else "Sun in H9" if su_h==9 else "")

        layout.add_widget(Widget(size_hint_y=None, height=dp(16)))
        layout.add_widget(gold_label("PLANET STATUS SUMMARY", font_size=sp(14), bold=True,
                                     size_hint_y=None, height=dp(28)))
        layout.add_widget(section_divider())

        for pk in ["Su","Mo","Ma","Me","Ju","Ve","Sa"]:
            if pk not in k.planet_data: continue
            pd = k.planet_data[pk]
            tags = []
            if pd.get("exalt"): tags.append("Exalted ↑")
            if pd.get("debil"): tags.append("Debilitated ↓")
            if pd.get("retro"): tags.append("Retrograde")
            if not tags: tags = ["Normal"]
            row = BoxLayout(size_hint_y=None, height=dp(30))
            row.add_widget(Label(text=PLANETS[pk]["name"], color=list(GOLD),
                                 font_size=sp(13), size_hint_x=0.30))
            row.add_widget(Label(text=RASHI_NAMES[pd["sign"]] + f" H{pd['house']}",
                                 color=list(FG_LIGHT), font_size=sp(12), size_hint_x=0.35))
            row.add_widget(Label(text=" | ".join(tags),
                                 color=[0.4,1,0.4,1] if "Exalted" in tags[0] else
                                       [1,0.4,0.4,1] if "Debil" in tags[0] else list(FG_LIGHT),
                                 font_size=sp(11), size_hint_x=0.35))
            layout.add_widget(row)

        scroll.add_widget(layout)
        return scroll


# ─────────────────────────────────────────────────────────────────────
#  APP
# ─────────────────────────────────────────────────────────────────────

class TaaraMandal(App):
    def build(self):
        Window.clearcolor = BG_DARK
        sm = ScreenManager()
        sm.add_widget(HomeScreen(name="home"))
        sm.add_widget(InputScreen(name="input"))
        sm.add_widget(ResultScreen(name="result"))
        return sm

    def on_start(self):
        Window.softinput_mode = "below_target"


if __name__ == "__main__":
    TaaraMandal().run()
