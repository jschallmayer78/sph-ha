from __future__ import annotations
import base64, hashlib, random, re
from html import unescape
from Crypto.Cipher import AES, PKCS1_v1_5
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import unpad
import requests
from bs4 import BeautifulSoup
from .const import SPH_BASE, SPH_LOGIN, SPH_CONNECT

class SphClient:
    """SPH client following the current lanis-mobile/liblanis protocol."""
    def __init__(self, school_id, username, password):
        self.school_id, self.username, self.password = str(school_id), username, password
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Home Assistant SPH Stundenplan/0.2.0"
        self.key = None

    @staticmethod
    def _kdf(salt, key):
        out, previous = b"", b""
        while len(out) < 48:
            previous = hashlib.md5(previous + key + salt).digest()
            out += previous
        return out[:48]

    @classmethod
    def _decrypt(cls, payload, key):
        if len(payload) < 16 or payload[:8] != b"Salted__": return None
        k = cls._kdf(payload[8:16], key)
        return unpad(AES.new(k[:32], AES.MODE_CBC, k[32:48]).decrypt(payload[16:]), AES.block_size)

    def _decrypt_tags(self, html):
        if not self.key: return html
        def repl(m):
            try:
                data = self._decrypt(base64.b64decode(m.group(1)), self.key)
                return data.decode("utf-8") if data else ""
            except Exception: return ""
        return re.sub(r"<encoded>(.*?)</encoded>", repl, html, flags=re.S)

    def login(self):
        r = self.session.post(f"{SPH_LOGIN}?i={self.school_id}", data={"user":f"{self.school_id}.{self.username}","user2":self.username,"password":self.password}, allow_redirects=False, timeout=15)
        if r.status_code == 503: raise RuntimeError("Schulportal Hessen ist nicht verfügbar.")
        if not r.headers.get("Location"): raise RuntimeError("SPH-Anmeldung fehlgeschlagen. Zugangsdaten prüfen.")
        r2 = self.session.get(SPH_CONNECT, allow_redirects=False, timeout=15)
        if r2.status_code not in (200,302): raise RuntimeError("SPH-Anmeldung konnte nicht abgeschlossen werden.")
        self._handshake()

    def _handshake(self):
        r = self.session.post(f"{SPH_BASE}/ajax.php", params={"f":"rsaPublicKey"}, timeout=15); r.raise_for_status()
        public_key = RSA.import_key(r.json()["publickey"])
        self.key = get_random_bytes(46)
        encrypted = PKCS1_v1_5.new(public_key).encrypt(self.key)
        r = self.session.post(f"{SPH_BASE}/ajax.php", params={"f":"rsaHandshake","s":random.randrange(2000)}, data={"key":base64.b64encode(encrypted).decode()}, timeout=15); r.raise_for_status()
        if self._decrypt(base64.b64decode(r.json()["challenge"]), self.key) != self.key:
            self.key = None; raise RuntimeError("SPH RSA/AES-Handshake fehlgeschlagen.")

    def get_timetable(self):
        if not self.session.cookies: self.login()
        r = self.session.get(f"{SPH_BASE}/stundenplan.php", allow_redirects=False, timeout=20)
        if r.status_code == 302:
            location = r.headers.get("Location")
            if not location: raise RuntimeError("Keine SPH-Weiterleitung für Stundenplan.")
            r = self.session.get(location if location.startswith("http") else f"{SPH_BASE}/{location.lstrip('/')}", timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(self._decrypt_tags(r.text), "html.parser")
        badge = soup.select_one("#aktuelleWoche")
        all_table, own_table = soup.select_one("#all tbody"), soup.select_one("#own tbody")
        if all_table is None and own_table is None: raise RuntimeError("Kein Stundenplan für dieses Konto verfügbar.")
        return {"week_badge":badge.get_text(" ",strip=True) if badge else None,"all":self._parse(all_table) if all_table else [],"own":self._parse(own_table) if own_table else []}

    @staticmethod
    def _parse(tbody):
        rows = tbody.find_all("tr", recursive=False)
        if not rows: return []
        day_count = max(0, len(rows[0].find_all(["td","th"],recursive=False))-1)
        result, occupied, slots = [[] for _ in range(day_count)], [[False]*day_count for _ in range(len(rows)+32)], []
        for row in rows:
            e=row.select_one(".VonBis")
            if e:
                p=[x.strip() for x in e.get_text(" ",strip=True).split(" - ")]
                if len(p)==2: slots.append((p[0],p[1]))
        first=rows[0].find_all(["td","th"],recursive=False)
        offset=bool(first and first[0].get_text(strip=True))
        for y,row in enumerate(rows):
            if y==0: continue
            for x,cell in enumerate(row.find_all(["td","th"],recursive=False)):
                if x==0: continue
                span=int(cell.get("rowspan","1") or "1"); day=x-1
                while day<day_count and occupied[y][day]: day+=1
                if day>=day_count: continue
                for i in range(span):
                    if y+i<len(occupied): occupied[y+i][day]=True
                for lesson in cell.select(".stunde"):
                    b,sm,bd=lesson.select_one("b"),lesson.select_one("small"),lesson.select_one(".badge")
                    subject=b.get_text(" ",strip=True) if b else None; teacher=sm.get_text(" ",strip=True) if sm else None; badge=bd.get_text(" ",strip=True) if bd else None
                    room=unescape(" ".join(n.strip() for n in lesson.find_all(string=True,recursive=False) if n.strip()))
                    duration=int(lesson.parent.get("rowspan","1") or "1")
                    si=y if offset else y-1; ei=si+duration-1
                    start=slots[si][0] if 0<=si<len(slots) else "00:00"; end=slots[ei][1] if 0<=ei<len(slots) else "00:00"
                    result[day].append({"day":day,"subject":subject,"teacher":teacher,"room":room,"badge":badge,"duration":duration,"start":start,"end":end,"index":y})
        return result
