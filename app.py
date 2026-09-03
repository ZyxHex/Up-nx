# ============================================================
# ZYXX GEN API - Free Fire Account Generator
# Version: 2.0 | Flask + Vercel Ready
# ============================================================

import sys
import os
import hmac
import hashlib
import requests
import string
import random
import json
import codecs
import time
import base64
import re
import threading
from datetime import datetime
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from flask import Flask, request, jsonify
from flask_cors import CORS
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# ============================================================
# CORS
# ============================================================
CORS(app, resources={r"/*": {"origins": "*"}})

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
    return response

# ============================================================
# KONFIGURASI
# ============================================================
HEX_KEY = "32656534343831396539623435393838343531343130363762323831363231383734643064356437616639643866376530306331653534373135623764316533"
KEY = bytes.fromhex(HEX_KEY)

REGION_LANG = {
    "ID": "id", "IND": "hi", "ME": "ar", "VN": "vi",
    "TH": "th", "BD": "bn", "PK": "ur", "TW": "zh",
    "CIS": "ru", "SAC": "es", "BR": "pt"
}

REGION_URLS = {
    "ID": "https://clientbp.ggblueshark.com/",
    "IND": "https://client.ind.freefiremobile.com/",
    "BR": "https://client.us.freefiremobile.com/",
    "ME": "https://clientbp.common.ggbluefox.com/",
    "TH": "https://clientbp.common.ggbluefox.com/",
}

# ============================================================
# RARE PATTERN
# ============================================================
PATTERNS = {
    "R4": [r"(\d)\1{3,}", 3],
    "S5": [r"(12345|23456|34567|45678|56789)", 4],
    "P6": [r"^(\d)(\d)(\d)\3\2\1$", 5],
    "QD": [r"(1111|2222|3333|4444|5555|6666|7777|8888|9999|0000)", 4],
    "SPH": [r"(69|420|1337|007)", 4],
}

def detect_rare(uid):
    uid_str = str(uid)
    max_score = 0
    matched = []
    for name, (pattern, score) in PATTERNS.items():
        if re.search(pattern, uid_str):
            matched.append({"name": name, "score": score})
            if score > max_score:
                max_score = score
    if matched:
        return True, matched[0]["name"], max_score, matched
    return False, None, 0, []

# ============================================================
# IP SPOOFER
# ============================================================
def get_ip():
    return f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"

def get_ua():
    return random.choice([
        "GarenaMSDK/4.0.19P8(ASUS_Z01QD;Android 12;en;US;)",
        "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_I005DA Build/PI)",
        "GarenaMSDK/4.0.19P8(Redmi Note 8;Android 10;en;US;)"
    ])

# ============================================================
# PROTOBUF
# ============================================================
def encode_varint(n):
    result = []
    while True:
        byte = n & 0x7F
        n >>= 7
        if n:
            byte |= 0x80
        result.append(byte)
        if not n:
            break
    return bytes(result)

def build_proto(fields):
    packet = bytearray()
    for field, value in fields.items():
        if isinstance(value, dict):
            nested = build_proto(value)
            header = (field << 3) | 2
            packet.extend(encode_varint(header))
            packet.extend(encode_varint(len(nested)))
            packet.extend(nested)
        elif isinstance(value, int):
            header = (field << 3) | 0
            packet.extend(encode_varint(header))
            packet.extend(encode_varint(value))
        elif isinstance(value, (str, bytes)):
            encoded = value.encode() if isinstance(value, str) else value
            header = (field << 3) | 2
            packet.extend(encode_varint(header))
            packet.extend(encode_varint(len(encoded)))
            packet.extend(encoded)
    return bytes(packet)

# ============================================================
# AES
# ============================================================
def aes_encrypt(data_hex):
    data = bytes.fromhex(data_hex)
    key = bytes([89,103,38,116,99,37,68,69,117,104,54,37,90,99,94,56])
    iv = bytes([54,111,121,90,68,114,50,50,69,51,121,99,104,106,77,37])
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return cipher.encrypt(pad(data, AES.block_size))

def encrypt_api(data_hex):
    data = bytes.fromhex(data_hex)
    key = bytes([89,103,38,116,99,37,68,69,117,104,54,37,90,99,94,56])
    iv = bytes([54,111,121,90,68,114,50,50,69,51,121,99,104,106,77,37])
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return cipher.encrypt(pad(data, AES.block_size)).hex()

# ============================================================
# GENERATE NAME / PASSWORD
# ============================================================
def random_name(prefix):
    return prefix + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def random_pass(prefix="ZYXX"):
    return f"{prefix}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}"

# ============================================================
# ACCOUNT CREATION
# ============================================================
def create_account(region, name_prefix, password_prefix, is_ghost=False):
    try:
        password = random_pass(password_prefix)
        session = requests.Session()
        session.verify = False
        
        # Step 1: Register
        url = "https://100067.connect.garena.com/api/v2/oauth/guest:register"
        payload = {"app_id": 100067, "client_type": 2, "password": password, "source": 2}
        headers = {
            "User-Agent": get_ua(),
            "Content-Type": "application/json",
            "X-Forwarded-For": get_ip(),
            "X-Real-IP": get_ip(),
        }
        resp = session.post(url, headers=headers, json=payload, timeout=10)
        if resp.status_code != 200:
            return None
        
        data = resp.json()
        uid = data.get("data", {}).get("uid")
        if not uid:
            return None
        
        # Step 2: Get Token
        url2 = "https://100067.connect.garena.com/oauth/guest/token/grant"
        body = {
            "uid": uid, "password": password,
            "response_type": "token", "client_type": "2",
            "client_secret": KEY, "client_id": "100067"
        }
        headers2 = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": get_ua(),
            "X-Forwarded-For": get_ip(),
        }
        resp2 = session.post(url2, headers=headers2, data=body, timeout=10)
        if resp2.status_code != 200:
            return None
        
        data2 = resp2.json()
        open_id = data2.get("open_id")
        access_token = data2.get("access_token")
        if not open_id or not access_token:
            return None
        
        # Step 3: Field encoding
        keystream = [0x30]*32
        encoded = ""
        for i in range(len(open_id)):
            encoded += chr(ord(open_id[i]) ^ keystream[i % 32])
        field = codecs.decode(''.join(c if 32 <= ord(c) <= 126 else f'\\u{ord(c):04x}' for c in encoded), 'unicode_escape').encode('latin1')
        
        # Step 4: Major Register
        url3 = "https://loginbp.ggblueshark.com/MajorRegister"
        name = random_name(name_prefix)
        lang = "pt" if is_ghost else REGION_LANG.get(region.upper(), "en")
        payload3 = {
            1: name, 2: access_token, 3: open_id,
            5: 102000007, 6: 4, 7: 1, 13: 1,
            14: field, 15: lang, 16: 1, 17: 1
        }
        pb = build_proto(payload3)
        encrypted = aes_encrypt(pb.hex())
        headers3 = {
            "Content-Type": "application/x-www-form-urlencoded",
            "ReleaseVersion": "OB54",
            "User-Agent": get_ua(),
            "X-GA": "v1 1",
            "X-Forwarded-For": get_ip(),
        }
        session.post(url3, headers=headers3, data=encrypted, timeout=10)
        
        # Step 5: Major Login
        account_id, jwt = major_login(uid, password, access_token, open_id, region, is_ghost)
        if account_id == "N/A":
            return None
        
        is_rare, rare_name, rare_score, matched = detect_rare(account_id)
        
        return {
            "uid": uid,
            "password": password,
            "name": name,
            "account_id": account_id,
            "jwt_token": jwt,
            "region": "GHOST" if is_ghost else region,
            "status": "success",
            "is_rare": is_rare,
            "rare_pattern": rare_name,
            "rare_score": rare_score,
            "matched_patterns": matched
        }
    except Exception as e:
        return None

def major_login(uid, password, access_token, open_id, region, is_ghost):
    try:
        lang = "pt" if is_ghost else REGION_LANG.get(region.upper(), "en")
        parts = [
            b'\x1a\x132025-08-30 05:19:21"\tfree fire(\x01:\x081.114.13B2Android OS 9 / API-28 (PI/rel.cjw.20220518.114133)J\x08HandheldR\nATM MobilsZ\x04WIFI`\xb6\nh\xee\x05r\x03300z\x1fARMv7 VFPv3 NEON VMH | 2400 | 2\x80\x01\xc9\x0f\x8a\x01\x0fAdreno (TM) 640\x92\x01\rOpenGL ES 3.2\x9a\x01+Google|dfa4ab4b-9dc4-454e-8065-e70c733fa53f\xa2\x01\x0e105.235.139.91\xaa\x01\x02',
            lang.encode("ascii"),
            b'\xb2\x01 1d8ec0240ede109973f3321b9354b44d\xba\x01\x014\xc2\x01\x08Handheld\xca\x01\x10Asus ASUS_I005DA\xea\x01@afcfbf13334be42036e4f742c80b956344bed760ac91b3aff9b607a610ab4390\xf0\x01\x01\xca\x02\nATM Mobils\xd2\x02\x04WIFI\xca\x03 7428b253defc164018c604a1ebbfebdf\xe0\x03\xa8\x81\x02\xe8\x03\xf6\xe5\x01\xf0\x03\xaf\x13\xf8\x03\x84\x07\x80\x04\xe7\xf0\x01\x88\x04\xa8\x81\x02\x90\x04\xe7\xf0\x01\x98\x04\xa8\x81\x02\xc8\x04\x01\xd2\x04=/data/app/com.dts.freefireth-PdeDnOilCSFn37p1AH_FLg==/lib/arm\xe0\x04\x01\xea\x04_2087f61c19f57f2af4e7feff0b24d9d9|/data/app/com.dts.freefireth-PdeDnOilCSFn37p1AH_FLg==/base.apk\xf0\x04\x03\xf8\x04\x01\x8a\x05\x0232\x9a\x05\n2019118692\xb2\x05\tOpenGLES2\xb8\x05\xff\x7f\xc0\x05\x04\xe0\x05\xf3F\xea\x05\x07android\xf2\x05pKqsHT5ZLWrYljNb5Vqh//yFRlaPHSO9NWSQsVvOmdhEEn7W+VHNUK+Q+fduA3ptNrGB0Ll0LRz3WW0jOwesLj6aiU7sZ40p8BfUE/FI/jzSTwRe2\xf8\x05\xfb\xe4\x06\x88\x06\x01\x90\x06\x01\x9a\x06\x014\xa2\x06\x014\xb2\x06"GQ@O\x00\x0e^\x00D\x06UA\x0ePM\r\x13hZ\x07T\x06\x0cm\\V\x0ejYV;\x0bU5'
        ]
        payload = b''.join(parts)
        
        url = "https://loginbp.ggblueshark.com/MajorLogin"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "ReleaseVersion": "OB54",
            "User-Agent": get_ua(),
            "X-GA": "v1 1",
            "X-Forwarded-For": get_ip(),
        }
        data = payload.replace(b'afcfbf13334be42036e4f742c80b956344bed760ac91b3aff9b607a610ab4390', access_token.encode())
        data = data.replace(b'1d8ec0240ede109973f3321b9354b44d', open_id.encode())
        d = encrypt_api(data.hex())
        session = requests.Session()
        session.verify = False
        resp = session.post(url, headers=headers, data=bytes.fromhex(d), timeout=10)
        
        if resp.status_code == 200 and len(resp.text) > 10:
            start = resp.text.find("eyJ")
            if start != -1:
                jwt = resp.text[start:]
                dot2 = jwt.find(".", jwt.find(".") + 1)
                if dot2 != -1:
                    jwt = jwt[:dot2 + 44]
                try:
                    parts = jwt.split('.')
                    if len(parts) >= 2:
                        p = parts[1]
                        pad = 4 - len(p) % 4
                        if pad != 4:
                            p += '=' * pad
                        dec = base64.urlsafe_b64decode(p)
                        d = json.loads(dec)
                        aid = d.get('account_id') or d.get('external_id')
                        if aid:
                            return str(aid), jwt
                except:
                    pass
        return "N/A", ""
    except Exception as e:
        return "N/A", ""

# ============================================================
# FLASK ROUTES
# ============================================================
@app.route('/', methods=['GET', 'OPTIONS'])
def home():
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"})
    return jsonify({
        "name": "ZYXX GEN API",
        "version": "2.0",
        "endpoint": "/gen?name=NAME&count=COUNT&region=REGION",
        "regions": list(REGION_LANG.keys())
    })

@app.route('/gen', methods=['GET', 'OPTIONS'])
def generate():
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"})
    
    name = request.args.get('name', 'ZYXX')
    count = int(request.args.get('count', '1'))
    region = request.args.get('region', 'IND').upper()
    password_prefix = request.args.get('password_prefix', 'ZYXX')
    is_ghost = request.args.get('ghost', 'false').lower() == 'true'
    
    if region not in REGION_LANG and not is_ghost:
        region = "IND"
    
    if count < 1:
        count = 1
    if count > 100:
        count = 100
    
    results = []
    rare_results = []
    
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(count, 10)) as executor:
        futures = []
        for i in range(count):
            futures.append(executor.submit(create_account, region, name, password_prefix, is_ghost))
        
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                results.append(result)
                if result.get('is_rare', False):
                    rare_results.append(result)
    
    return jsonify({
        "success": True,
        "total_requested": count,
        "total_created": len(results),
        "rare_count": len(rare_results),
        "accounts": results,
        "rare_accounts": rare_results
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"})

# ============================================================
# RUN
# ============================================================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=False)
