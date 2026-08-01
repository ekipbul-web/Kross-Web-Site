from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from functools import wraps
from datetime import datetime, timedelta
import json
import os
import uuid
import hashlib
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_page'

# -------------------- AYARLAR --------------------
SUPER_ADMIN = "skayblaze"  # Senin Discord kullanıcı adın
ADMIN_DOSYASI = "admins.json"
VERI_DOSYASI = "../sentinel_data.json"  # Bot ile aynı veriyi kullan

# -------------------- VERİ YÖNETİMİ --------------------
def admin_yukle():
    try:
        if os.path.exists(ADMIN_DOSYASI):
            with open(ADMIN_DOSYASI, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return {"admins": [], "pending": []}

def admin_kaydet(veri):
    try:
        with open(ADMIN_DOSYASI, 'w', encoding='utf-8') as f:
            json.dump(veri, f, ensure_ascii=False, indent=2)
    except:
        pass

def veri_yukle():
    try:
        if os.path.exists(VERI_DOSYASI):
            with open(VERI_DOSYASI, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    
    return {
        "tickets": {},
        "basvurular": [],
        "basvuru_sayac": 0,
        "oneriler": [],
        "oneri_sayac": 0,
        "puanlar": {},
        "izinler": [],
        "izin_sayac": 0,
        "istatistik": {
            "toplam_ticket": 0,
            "toplam_basvuru": 0,
            "onaylanan": 0,
            "reddedilen": 0,
            "toplam_oneri": 0,
            "toplam_izin": 0,
            "aktif_izin": 0
        },
        "web_tickets": [],
        "web_basvurular": [],
        "web_izinler": []
    }

def veri_kaydet(veri):
    try:
        with open(VERI_DOSYASI, 'w', encoding='utf-8') as f:
            json.dump(veri, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

def sure_parse(sure_str):
    sure_str = sure_str.strip().lower()
    if sure_str.endswith('m'):
        try: return int(sure_str[:-1])
        except: return None
    elif sure_str.endswith('h'):
        try: return int(sure_str[:-1]) * 60
        except: return None
    elif sure_str.endswith('d'):
        try: return int(sure_str[:-1]) * 24 * 60
        except: return None
    else:
        try: return int(sure_str)
        except: return None

def sure_format(dakika):
    if dakika < 60:
        return f"{dakika} dakika"
    elif dakika < 1440:
        saat = dakika // 60
        kalan_dk = dakika % 60
        if kalan_dk > 0:
            return f"{saat} saat {kalan_dk} dakika"
        return f"{saat} saat"
    else:
        gun = dakika // 1440
        kalan_saat = (dakika % 1440) // 60
        if kalan_saat > 0:
            return f"{gun} gün {kalan_saat} saat"
        return f"{gun} gün"

# -------------------- FLASK LOGIN --------------------
class AdminUser(UserMixin):
    def __init__(self, user_data):
        self.id = user_data["id"]
        self.username = user_data["username"]
        self.discord_id = user_data["discord_id"]
        self.role = user_data.get("role", "admin")
        self.is_super = user_data.get("is_super", False)

@login_manager.user_loader
def load_user(user_id):
    admin_veri = admin_yukle()
    for admin in admin_veri.get("admins", []):
        if admin["id"] == user_id:
            return AdminUser(admin)
    return None

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

def super_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login_page'))
        if not current_user.is_super:
            return render_template('index.html', page='403'), 403
        return f(*args, **kwargs)
    return decorated_function

# -------------------- SAYFALAR --------------------
@app.route('/')
def index():
    veri = veri_yukle()
    stats = {
        "tickets": veri["istatistik"].get("toplam_ticket", 0),
        "applications": veri["istatistik"].get("toplam_basvuru", 0),
        "permissions": veri["istatistik"].get("aktif_izin", 0),
        "approved": veri["istatistik"].get("onaylanan", 0)
    }
    return render_template('index.html', stats=stats, page='home')

@app.route('/login')
def login_page():
    return render_template('index.html', page='login')

@app.route('/register')
def register_page():
    return render_template('index.html', page='register')

@app.route('/panel')
@login_required
@admin_required
def panel():
    veri = veri_yukle()
    
    web_tickets = veri.get("web_tickets", [])
    web_basvurular = veri.get("web_basvurular", [])
    web_izinler = veri.get("web_izinler", [])
    
    discord_tickets = []
    for ticket_id, ticket in veri.get("tickets", {}).items():
        discord_tickets.append({
            "id": ticket_id[:8],
            "sahip": str(ticket.get("sahip", "")),
            "alan": str(ticket.get("alan", "")),
            "durum": ticket.get("durum", "bilinmiyor"),
            "acilis": ticket.get("acilis", "")
        })
    
    discord_basvurular = veri.get("basvurular", [])
    discord_izinler = veri.get("izinler", [])
    
    return render_template('index.html', 
                         page='panel',
                         web_tickets=web_tickets,
                         web_basvurular=web_basvurular,
                         web_izinler=web_izinler,
                         discord_tickets=discord_tickets,
                         discord_basvurular=discord_basvurular,
                         discord_izinler=discord_izinler,
                         current_user=current_user)

@app.route('/super-admin')
@login_required
@super_admin_required
def super_admin():
    admin_veri = admin_yukle()
    return render_template('index.html',
                         page='super_admin',
                         pending=admin_veri.get("pending", []),
                         admins=admin_veri.get("admins", []))

@app.route('/waiting')
def waiting():
    return render_template('index.html', page='waiting')

# -------------------- API --------------------
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    admin_veri = admin_yukle()
    
    for admin in admin_veri.get("admins", []):
        if admin["username"].lower() == username.lower():
            hashed = hashlib.sha256(password.encode()).hexdigest()
            if admin["password"] == hashed:
                user = AdminUser(admin)
                login_user(user)
                redirect_url = "/super-admin" if admin.get("is_super") else "/panel"
                return jsonify({"success": True, "redirect": redirect_url})
    
    return jsonify({"success": False, "error": "Kullanıcı adı veya şifre hatalı!"})

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.json
    username = data.get('username', '').strip()
    discord_id = data.get('discord_id', '').strip()
    password = data.get('password', '').strip()
    
    if not username or not discord_id or not password:
        return jsonify({"success": False, "error": "Tüm alanları doldurun!"})
    
    if len(password) < 6:
        return jsonify({"success": False, "error": "Şifre en az 6 karakter olmalı!"})
    
    admin_veri = admin_yukle()
    
    for admin in admin_veri.get("admins", []):
        if admin["username"].lower() == username.lower():
            return jsonify({"success": False, "error": "Bu kullanıcı adı zaten kullanılıyor!"})
    
    for pending in admin_veri.get("pending", []):
        if pending["username"].lower() == username.lower():
            return jsonify({"success": False, "error": "Bu kullanıcı adı onay bekliyor!"})
    
    hashed = hashlib.sha256(password.encode()).hexdigest()
    
    new_admin = {
        "id": str(uuid.uuid4()),
        "username": username,
        "discord_id": discord_id,
        "password": hashed,
        "role": "admin",
        "is_super": False,
        "created_at": datetime.now().isoformat(),
        "status": "pending"
    }
    
    admin_veri["pending"].append(new_admin)
    admin_kaydet(admin_veri)
    
    return jsonify({"success": True, "message": "Kaydınız onaya gönderildi! Onaylanınca giriş yapabilirsiniz."})

@app.route('/api/logout')
@login_required
def api_logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/api/super/approve', methods=['POST'])
@login_required
@super_admin_required
def api_approve_admin():
    data = request.json
    admin_id = data.get('admin_id')
    
    admin_veri = admin_yukle()
    
    for pending in admin_veri.get("pending", []):
        if pending["id"] == admin_id:
            pending["status"] = "active"
            pending["approved_at"] = datetime.now().isoformat()
            admin_veri["admins"].append(pending)
            admin_veri["pending"].remove(pending)
            admin_kaydet(admin_veri)
            return jsonify({"success": True})
    
    return jsonify({"success": False, "error": "Admin bulunamadı!"})

@app.route('/api/super/reject', methods=['POST'])
@login_required
@super_admin_required
def api_reject_admin():
    data = request.json
    admin_id = data.get('admin_id')
    
    admin_veri = admin_yukle()
    admin_veri["pending"] = [p for p in admin_veri.get("pending", []) if p["id"] != admin_id]
    admin_kaydet(admin_veri)
    
    return jsonify({"success": True})

@app.route('/api/super/delete', methods=['POST'])
@login_required
@super_admin_required
def api_delete_admin():
    data = request.json
    admin_id = data.get('admin_id')
    
    admin_veri = admin_yukle()
    admin_veri["admins"] = [a for a in admin_veri.get("admins", []) if a["id"] != admin_id]
    admin_kaydet(admin_veri)
    
    return jsonify({"success": True})

# Ticket API
@app.route('/api/ticket/create', methods=['POST'])
def api_ticket_create():
    data = request.json
    discord_id = data.get('discord_id', '').strip()
    username = data.get('username', '').strip()
    sorun = data.get('sorun', '').strip()
    
    if not discord_id or not username or not sorun:
        return jsonify({"success": False, "error": "Tüm alanları doldurun!"})
    
    veri = veri_yukle()
    ticket_no = len(veri.get("web_tickets", [])) + 1
    
    veri["web_tickets"].append({
        "no": ticket_no,
        "discord_id": discord_id,
        "username": username,
        "sorun": sorun,
        "durum": "bekliyor",
        "tarih": datetime.now().isoformat(),
        "alan": None,
        "onay_tarih": None
    })
    veri["istatistik"]["toplam_ticket"] = veri["istatistik"].get("toplam_ticket", 0) + 1
    veri_kaydet(veri)
    
    return jsonify({"success": True, "ticket_no": ticket_no})

@app.route('/api/ticket/approve', methods=['POST'])
@login_required
@admin_required
def api_ticket_approve():
    data = request.json
    ticket_no = data.get('ticket_no')
    
    veri = veri_yukle()
    for ticket in veri.get("web_tickets", []):
        if ticket["no"] == ticket_no:
            ticket["durum"] = "onaylandı"
            ticket["alan"] = current_user.username
            ticket["onay_tarih"] = datetime.now().isoformat()
            break
    
    veri_kaydet(veri)
    return jsonify({"success": True})

@app.route('/api/ticket/reject', methods=['POST'])
@login_required
@admin_required
def api_ticket_reject():
    data = request.json
    ticket_no = data.get('ticket_no')
    
    veri = veri_yukle()
    for ticket in veri.get("web_tickets", []):
        if ticket["no"] == ticket_no:
            ticket["durum"] = "reddedildi"
            ticket["alan"] = current_user.username
            ticket["onay_tarih"] = datetime.now().isoformat()
            break
    
    veri_kaydet(veri)
    return jsonify({"success": True})

# Başvuru API
@app.route('/api/basvuru/create', methods=['POST'])
def api_basvuru_create():
    data = request.json
    
    required = ['discord_id', 'username', 'isim', 'yas', 'tecrube', 'neden', 'sure']
    for field in required:
        if not data.get(field, '').strip():
            return jsonify({"success": False, "error": f"{field} alanı zorunlu!"})
    
    veri = veri_yukle()
    basvuru_no = len(veri.get("web_basvurular", [])) + 1
    
    veri["web_basvurular"].append({
        "no": basvuru_no,
        "discord_id": data['discord_id'],
        "username": data['username'],
        "isim": data['isim'],
        "yas": data['yas'],
        "tecrube": data['tecrube'],
        "neden": data['neden'],
        "sure": data['sure'],
        "durum": "bekliyor",
        "tarih": datetime.now().isoformat(),
        "yorumlar": [],
        "puan": 0
    })
    veri["istatistik"]["toplam_basvuru"] = veri["istatistik"].get("toplam_basvuru", 0) + 1
    veri_kaydet(veri)
    
    return jsonify({"success": True, "basvuru_no": basvuru_no})

@app.route('/api/basvuru/approve', methods=['POST'])
@login_required
@admin_required
def api_basvuru_approve():
    data = request.json
    basvuru_no = data.get('basvuru_no')
    
    veri = veri_yukle()
    for basvuru in veri.get("web_basvurular", []):
        if basvuru["no"] == basvuru_no:
            basvuru["durum"] = "onaylandı"
            veri["istatistik"]["onaylanan"] = veri["istatistik"].get("onaylanan", 0) + 1
            break
    
    veri_kaydet(veri)
    return jsonify({"success": True})

@app.route('/api/basvuru/reject', methods=['POST'])
@login_required
@admin_required
def api_basvuru_reject():
    data = request.json
    basvuru_no = data.get('basvuru_no')
    
    veri = veri_yukle()
    for basvuru in veri.get("web_basvurular", []):
        if basvuru["no"] == basvuru_no:
            basvuru["durum"] = "reddedildi"
            veri["istatistik"]["reddedilen"] = veri["istatistik"].get("reddedilen", 0) + 1
            break
    
    veri_kaydet(veri)
    return jsonify({"success": True})

@app.route('/api/basvuru/yorum', methods=['POST'])
@login_required
@admin_required
def api_basvuru_yorum():
    data = request.json
    basvuru_no = data.get('basvuru_no')
    yorum = data.get('yorum', '').strip()
    
    if not yorum:
        return jsonify({"success": False, "error": "Yorum boş olamaz!"})
    
    veri = veri_yukle()
    for basvuru in veri.get("web_basvurular", []):
        if basvuru["no"] == basvuru_no:
            if "yorumlar" not in basvuru:
                basvuru["yorumlar"] = []
            basvuru["yorumlar"].append({
                "yorum": yorum,
                "yapan": current_user.username,
                "tarih": datetime.now().isoformat()
            })
            break
    
    veri_kaydet(veri)
    return jsonify({"success": True})

@app.route('/api/basvuru/puan', methods=['POST'])
@login_required
@admin_required
def api_basvuru_puan():
    data = request.json
    basvuru_no = data.get('basvuru_no')
    puan = data.get('puan', 0)
    
    veri = veri_yukle()
    for basvuru in veri.get("web_basvurular", []):
        if basvuru["no"] == basvuru_no:
            basvuru["puan"] = int(puan)
            break
    
    veri_kaydet(veri)
    return jsonify({"success": True})

# İzin API
@app.route('/api/izin/create', methods=['POST'])
def api_izin_create():
    data = request.json
    discord_id = data.get('discord_id', '').strip()
    username = data.get('username', '').strip()
    sebep = data.get('sebep', '').strip()
    sure_str = data.get('sure', '').strip()
    
    if not all([discord_id, username, sebep, sure_str]):
        return jsonify({"success": False, "error": "Tüm alanları doldurun!"})
    
    dakika = sure_parse(sure_str)
    if not dakika:
        return jsonify({"success": False, "error": "Geçersiz süre! (30m, 1h, 3h, 24h, 7d)"})
    
    veri = veri_yukle()
    izin_no = len(veri.get("web_izinler", [])) + 1
    
    baslangic = datetime.now()
    bitis = baslangic + timedelta(minutes=dakika)
    
    veri["web_izinler"].append({
        "no": izin_no,
        "discord_id": discord_id,
        "username": username,
        "sebep": sebep,
        "sure_dk": dakika,
        "sure_str": sure_str,
        "baslangic": baslangic.isoformat(),
        "bitis": bitis.isoformat(),
        "durum": "bekliyor"
    })
    veri["istatistik"]["toplam_izin"] = veri["istatistik"].get("toplam_izin", 0) + 1
    veri_kaydet(veri)
    
    return jsonify({"success": True, "izin_no": izin_no})

@app.route('/api/izin/approve', methods=['POST'])
@login_required
@admin_required
def api_izin_approve():
    data = request.json
    izin_no = data.get('izin_no')
    
    veri = veri_yukle()
    for izin in veri.get("web_izinler", []):
        if izin["no"] == izin_no:
            izin["durum"] = "onaylandı"
            veri["istatistik"]["aktif_izin"] = veri["istatistik"].get("aktif_izin", 0) + 1
            break
    
    veri_kaydet(veri)
    return jsonify({"success": True})

@app.route('/api/izin/reject', methods=['POST'])
@login_required
@admin_required
def api_izin_reject():
    data = request.json
    izin_no = data.get('izin_no')
    
    veri = veri_yukle()
    for izin in veri.get("web_izinler", []):
        if izin["no"] == izin_no:
            izin["durum"] = "reddedildi"
            break
    
    veri_kaydet(veri)
    return jsonify({"success": True})

# İstatistik API
@app.route('/api/stats')
def api_stats():
    veri = veri_yukle()
    return jsonify(veri["istatistik"])

# -------------------- HATA SAYFALARI --------------------
@app.errorhandler(404)
def not_found(e):
    return render_template('index.html', page='404'), 404

# -------------------- BAŞLAT --------------------
if __name__ == '__main__':
    print("🌐 Kross Sentinel Web Panel başlatılıyor...")
    print("📍 http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
