import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import messagebox, filedialog # Standart ve sağlam mesaj kutuları
import sqlite3
import datetime
import os
import sys
import shutil
import pandas as pd

# --- AYARLAR ---
# Programın çalıştığı klasörü bul (Hem Python hem EXE modunda çalışır)
if getattr(sys, 'frozen', False):
    APP_PATH = os.path.dirname(sys.executable)
elif __file__:
    APP_PATH = os.path.dirname(__file__)

DB_NAME = os.path.join(APP_PATH, "leta_data.db")
BACKUP_DIR = os.path.join(APP_PATH, "Yedekler")

# --- VERİTABANI İŞLEMLERİ ---
def sistem_kontrol():
    # Yedek klasörü yoksa oluştur
    if not os.path.exists(BACKUP_DIR):
        try:
            os.makedirs(BACKUP_DIR)
        except Exception as e:
            messagebox.showerror("Hata", f"Yedek klasörü oluşturulamadı:\n{e}")

    # Veritabanı tablosunu oluştur
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Seans kayıtları tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kayitlar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarih TEXT,
                danisan_adi TEXT,
                terapist TEXT,
                hizmet_bedeli REAL,
                alinan_ucret REAL,
                kalan_borc REAL,
                notlar TEXT,
                son_islem_tarihi TEXT
            )
        """)
        
        # Kullanıcılar tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kullanicilar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kullanici_adi TEXT UNIQUE NOT NULL,
                sifre TEXT NOT NULL,
                ad_soyad TEXT,
                email TEXT,
                rol TEXT DEFAULT 'normal',
                olusturma_tarihi TEXT,
                son_giris_tarihi TEXT,
                aktif INTEGER DEFAULT 1
            )
        """)
        
        # Eski tabloda rol sütunu yoksa ekle
        try:
            cursor.execute("ALTER TABLE kullanicilar ADD COLUMN rol TEXT DEFAULT 'normal'")
        except:
            pass  # Sütun zaten varsa hata verme
        
        # Pervin Hanım kullanıcısını oluştur (eğer yoksa) - Kurum Müdürü rolü
        cursor.execute("SELECT COUNT(*) FROM kullanicilar WHERE kullanici_adi = 'pervin'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO kullanicilar (kullanici_adi, sifre, ad_soyad, rol, olusturma_tarihi, aktif)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ("pervin", "pervin123", "Pervin Hanım", "kurum_muduru", datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), 1))
        
        # Seans Takvimi Tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS seans_takvimi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarih TEXT NOT NULL,
                saat TEXT NOT NULL,
                danisan_adi TEXT NOT NULL,
                terapist TEXT NOT NULL,
                oda TEXT,
                durum TEXT DEFAULT 'planlandi',
                notlar TEXT,
                olusturma_tarihi TEXT,
                olusturan_kullanici_id INTEGER,
                FOREIGN KEY (olusturan_kullanici_id) REFERENCES kullanicilar(id)
            )
        """)
        
        # Danışan Bilgileri Tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS danisanlar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ad_soyad TEXT NOT NULL,
                telefon TEXT,
                email TEXT,
                adres TEXT,
                dogum_tarihi TEXT,
                veli_adi TEXT,
                veli_telefon TEXT,
                notlar TEXT,
                olusturma_tarihi TEXT,
                aktif INTEGER DEFAULT 1
            )
        """)
        
        # Oda Yönetimi Tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS odalar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                oda_adi TEXT UNIQUE NOT NULL,
                oda_tipi TEXT,
                kapasite INTEGER,
                aciklama TEXT,
                aktif INTEGER DEFAULT 1
            )
        """)
        
        # Varsayılan odaları ekle
        cursor.execute("SELECT COUNT(*) FROM odalar")
        if cursor.fetchone()[0] == 0:
            odalar = [
                ("Oyun Terapi Odası", "Terapi", 2, ""),
                ("Ergoterapi Odası", "Terapi", 2, ""),
                ("Büyük Oda", "Eğitim", 5, ""),
                ("Küçük Oda", "Eğitim", 3, "")
            ]
            cursor.executemany("""
                INSERT INTO odalar (oda_adi, oda_tipi, kapasite, aciklama, aktif)
                VALUES (?, ?, ?, ?, 1)
            """, odalar)
        
        # Görev Takibi Tablosu (Sekreterlik)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gorevler (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                baslik TEXT NOT NULL,
                aciklama TEXT,
                atanan_kullanici_id INTEGER,
                olusturan_kullanici_id INTEGER,
                durum TEXT DEFAULT 'beklemede',
                oncelik TEXT DEFAULT 'normal',
                baslangic_tarihi TEXT,
                bitis_tarihi TEXT,
                tamamlanma_tarihi TEXT,
                olusturma_tarihi TEXT,
                FOREIGN KEY (atanan_kullanici_id) REFERENCES kullanicilar(id),
                FOREIGN KEY (olusturan_kullanici_id) REFERENCES kullanicilar(id)
            )
        """)
        
        # Rol sistemi güncellemesi: Eski pervin_hanim rolünü kurum_muduru yap
        cursor.execute("UPDATE kullanicilar SET rol = 'kurum_muduru' WHERE rol = 'pervin_hanim'")
        
        conn.commit()
        conn.close()
    except Exception as e:
        messagebox.showerror("Kritik Hata", f"Veritabanı başlatılamadı:\n{e}")

# --- LOGIN EKRANI ---
class LoginPenceresi(ttk.Window):
    """
    Uygulamanın ana kök penceresi.
    Başarılı girişte sadece gizlenir, böylece Tk uygulaması yaşamaya devam eder.
    """
    def __init__(self):
        super().__init__(themename="cosmo")
        self.title("Giriş - Leta Yönetim")
        
        # Ekranı ortala
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x_c = int((screen_width/2) - (400/2))
        y_c = int((screen_height/2) - (400/2))
        self.geometry(f"400x400+{x_c}+{y_c}")
        self.resizable(False, False)

        ttk.Label(self, text="LETA YÖNETİM", font=("Arial", 16, "bold"), bootstyle="primary").pack(pady=20)

        frm = ttk.Frame(self, padding=20)
        frm.pack(fill=BOTH, expand=True, padx=20)

        ttk.Label(frm, text="Kullanıcı Adı:").pack(anchor=W, pady=(0, 5))
        self.ent_user = ttk.Entry(frm, bootstyle="primary")
        self.ent_user.pack(fill=X, pady=5)
        
        ttk.Label(frm, text="Şifre:").pack(anchor=W, pady=(10, 5))
        self.ent_pass = ttk.Entry(frm, show="*", bootstyle="primary")
        self.ent_pass.pack(fill=X, pady=5)
        
        ttk.Button(frm, text="GİRİŞ YAP", bootstyle="success", command=self.giris_yap).pack(fill=X, pady=(20, 10))
        ttk.Button(frm, text="KAYIT OL", bootstyle="info-outline", command=self.kayit_ol_penceresi).pack(fill=X, pady=5)
        
        ttk.Label(self, text="Varsayılan: pervin/pervin123", font=("Arial", 8), foreground="gray").pack(side=BOTTOM, pady=10)

    def giris_yap(self):
        kullanici_adi = self.ent_user.get().strip()
        sifre = self.ent_pass.get()
        
        if not kullanici_adi or not sifre:
            messagebox.showwarning("Uyarı", "Lütfen kullanıcı adı ve şifre giriniz.")
            return
        
        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, kullanici_adi, ad_soyad, rol, aktif 
                FROM kullanicilar 
                WHERE kullanici_adi = ? AND sifre = ? AND aktif = 1
            """, (kullanici_adi, sifre))
            kullanici = cursor.fetchone()
            
            if kullanici:
                # Son giriş tarihini güncelle
                cursor.execute("""
                    UPDATE kullanicilar 
                    SET son_giris_tarihi = ? 
                    WHERE id = ?
                """, (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), kullanici[0]))
                conn.commit()
                conn.close()
                
                # Kök pencereyi gizle
                self.withdraw()
                # Ana uygulamayı aç ve kullanıcı bilgisini gönder
                AnaUygulama(self, kullanici)
            else:
                conn.close()
                messagebox.showerror("Hata", "Kullanıcı adı veya şifre yanlış!\n\nVeya hesabınız pasif durumda olabilir.")
        except Exception as e:
            messagebox.showerror("Hata", f"Giriş hatası: {e}")
    
    def kayit_ol_penceresi(self):
        """Kayıt olma penceresini aç"""
        KayitOlPenceresi(self)

# --- KAYIT OL PENCERESİ ---
class KayitOlPenceresi(ttk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Yeni Kullanıcı Kaydı")
        self.geometry("400x450")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        # Ekranı ortala
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x_c = int((screen_width/2) - (400/2))
        y_c = int((screen_height/2) - (450/2))
        self.geometry(f"400x450+{x_c}+{y_c}")
        
        ttk.Label(self, text="YENİ KULLANICI KAYDI", font=("Arial", 14, "bold"), bootstyle="primary").pack(pady=20)
        
        frm = ttk.Frame(self, padding=20)
        frm.pack(fill=BOTH, expand=True)
        
        ttk.Label(frm, text="Kullanıcı Adı:").pack(anchor=W, pady=(5, 0))
        self.ent_kullanici = ttk.Entry(frm, bootstyle="primary")
        self.ent_kullanici.pack(fill=X, pady=5)
        
        ttk.Label(frm, text="Şifre:").pack(anchor=W, pady=(10, 0))
        self.ent_sifre = ttk.Entry(frm, show="*", bootstyle="primary")
        self.ent_sifre.pack(fill=X, pady=5)
        
        ttk.Label(frm, text="Şifre Tekrar:").pack(anchor=W, pady=(10, 0))
        self.ent_sifre_tekrar = ttk.Entry(frm, show="*", bootstyle="primary")
        self.ent_sifre_tekrar.pack(fill=X, pady=5)
        
        ttk.Label(frm, text="Ad Soyad:").pack(anchor=W, pady=(10, 0))
        self.ent_ad_soyad = ttk.Entry(frm, bootstyle="primary")
        self.ent_ad_soyad.pack(fill=X, pady=5)
        
        ttk.Label(frm, text="E-posta (Opsiyonel):").pack(anchor=W, pady=(10, 0))
        self.ent_email = ttk.Entry(frm, bootstyle="primary")
        self.ent_email.pack(fill=X, pady=5)
        
        btn_frame = ttk.Frame(frm)
        btn_frame.pack(fill=X, pady=20)
        
        ttk.Button(btn_frame, text="KAYDET", bootstyle="success", command=self.kayit_ol).pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        ttk.Button(btn_frame, text="İPTAL", bootstyle="secondary", command=self.destroy).pack(side=LEFT, fill=X, expand=True, padx=(5, 0))
    
    def kayit_ol(self):
        kullanici_adi = self.ent_kullanici.get().strip()
        sifre = self.ent_sifre.get()
        sifre_tekrar = self.ent_sifre_tekrar.get()
        ad_soyad = self.ent_ad_soyad.get().strip()
        email = self.ent_email.get().strip()
        
        # Validasyon
        if not kullanici_adi or not sifre:
            messagebox.showwarning("Uyarı", "Kullanıcı adı ve şifre zorunludur!")
            return
        
        if len(kullanici_adi) < 3:
            messagebox.showwarning("Uyarı", "Kullanıcı adı en az 3 karakter olmalıdır!")
            return
        
        if len(sifre) < 4:
            messagebox.showwarning("Uyarı", "Şifre en az 4 karakter olmalıdır!")
            return
        
        if sifre != sifre_tekrar:
            messagebox.showerror("Hata", "Şifreler eşleşmiyor!")
            return
        
        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            
            # Kullanıcı adı kontrolü
            cursor.execute("SELECT COUNT(*) FROM kullanicilar WHERE kullanici_adi = ?", (kullanici_adi,))
            if cursor.fetchone()[0] > 0:
                messagebox.showerror("Hata", "Bu kullanıcı adı zaten kullanılıyor!")
                conn.close()
                return
            
            # Yeni kullanıcı ekle
            cursor.execute("""
                INSERT INTO kullanicilar (kullanici_adi, sifre, ad_soyad, email, rol, olusturma_tarihi, aktif)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (kullanici_adi, sifre, ad_soyad, email, "normal", datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), 1))
            
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Başarılı", "Kayıt başarıyla oluşturuldu!\n\nArtık giriş yapabilirsiniz.")
            self.destroy()
            
        except Exception as e:
            messagebox.showerror("Hata", f"Kayıt hatası: {e}")

# --- ANA UYGULAMA ---
class AnaUygulama(ttk.Toplevel):
    """
    Asıl yönetim ekranı. Login penceresinin üzerinde çalışan bir Toplevel.
    """
    def __init__(self, master=None, kullanici=None):
        super().__init__(master=master)
        self.kullanici = kullanici  # (id, kullanici_adi, ad_soyad, rol, aktif)
        self.kullanici_rol = kullanici[3] if kullanici else "normal"
        self.title("Leta Aile ve Çocuk - Yönetim Sistemi v4.0 (Final)")
        self.geometry("1200x750")
        self.protocol("WM_DELETE_WINDOW", self.cikis_yap)
        
        # Menü Çubuğu - Rol bazlı
        menubar = ttk.Menu(self)
        self.config(menu=menubar)
        
        # Kurum Müdürü için tüm modüller
        if self.kullanici_rol in ["kurum_muduru", "admin"]:
            # Seans Takvimi Modülü
            seans_menu = ttk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Seans Takvimi", menu=seans_menu)
            seans_menu.add_command(label="Günlük Takvim", command=self.seans_takvimi_goster)
            seans_menu.add_command(label="Haftalık Takvim", command=self.haftalik_takvim_goster)
            seans_menu.add_command(label="Yeni Seans Ekle", command=self.yeni_seans_ekle)
            
            # Sekreterlik Modülü
            sekreter_menu = ttk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Sekreterlik", menu=sekreter_menu)
            sekreter_menu.add_command(label="Danışan Yönetimi", command=self.danisan_yonetimi)
            sekreter_menu.add_command(label="Randevu Yönetimi", command=self.randevu_yonetimi)
            sekreter_menu.add_command(label="Görev Takibi", command=self.gorev_takibi)
            
            # Muhasebe Modülü
            muhasebe_menu = ttk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Muhasebe", menu=muhasebe_menu)
            muhasebe_menu.add_command(label="Ücret Takibi", command=self.ucret_takibi_goster)
            muhasebe_menu.add_command(label="Gelir-Gider Raporu", command=self.gelir_gider_raporu)
            muhasebe_menu.add_command(label="Ödeme İşlemleri", command=self.odeme_islemleri)
            
            # Kullanıcı Yönetimi
            kullanici_menu = ttk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Kullanıcı Yönetimi", menu=kullanici_menu)
            kullanici_menu.add_command(label="Kullanıcıları Listele", command=self.kullanicilari_listele)
            kullanici_menu.add_command(label="Kullanıcı Sil", command=self.kullanici_sil)
        
        # Eğitim Görevlisi için sadece kendi seansları
        elif self.kullanici_rol == "egitim_gorevlisi":
            seans_menu = ttk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Seans Takvimi", menu=seans_menu)
            seans_menu.add_command(label="Kendi Seanslarım", command=self.kendi_seanslarim)
            seans_menu.add_command(label="Haftalık Takvim", command=self.haftalik_takvim_goster)
            
            muhasebe_menu = ttk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Ücret Takibi", menu=muhasebe_menu)
            muhasebe_menu.add_command(label="Kendi Ücretlerim", command=self.kendi_ucretlerim)
        
        # Dosya İşlemleri (Tüm kullanıcılar için)
        dosya_menu = ttk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Dosya İşlemleri", menu=dosya_menu)
        dosya_menu.add_command(label="Excel'e Aktar", command=self.excel_aktar)
        dosya_menu.add_command(label="Yedek Klasörünü Aç", command=self.yedek_klasoru_ac)
        dosya_menu.add_separator()
        dosya_menu.add_command(label="Çıkış", command=self.cikis_yap)
        
        yardim_menu = ttk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Yardım", menu=yardim_menu)
        yardim_menu.add_command(label="Hakkında", command=self.hakkinda_goster)

        # ANA DÜZEN - Rol bazlı gösterim
        ana_panel = ttk.Frame(self, padding=10)
        ana_panel.pack(fill=BOTH, expand=True)
        
        # Kullanıcı bilgisi göster
        kullanici_bilgi = ttk.Label(
            ana_panel, 
            text=f"Hoş Geldiniz: {kullanici[2] if kullanici else 'Kullanıcı'} | Rol: {self.kullanici_rol.replace('_', ' ').title()}", 
            font=("Arial", 10, "bold"),
            bootstyle="info"
        )
        kullanici_bilgi.pack(anchor=E, padx=10, pady=5)

        # Kurum Müdürü için tam ekran, Eğitim Görevlisi için sadece kendi seansları
        if self.kullanici_rol in ["kurum_muduru", "admin"]:
            self.ana_ekran_kurum_muduru(ana_panel)
        elif self.kullanici_rol == "egitim_gorevlisi":
            self.ana_ekran_egitim_gorevlisi(ana_panel)
        else:
            # Normal kullanıcı için basit görünüm
            self.ana_ekran_normal(ana_panel)
    
    def ana_ekran_kurum_muduru(self, ana_panel):
        """Kurum Müdürü için tam ekran"""
        # --- ÜST KISIM: VERİ GİRİŞİ ---
        giris_frame = ttk.Labelframe(ana_panel, text="Yeni Seans Kaydı", padding=15, bootstyle="primary")
        giris_frame.pack(fill=X, pady=(0, 10))

        # Grid sistemi ile düzenli giriş alanları
        self.tarih_var = ttk.StringVar(value=datetime.datetime.now().strftime("%d.%m.%Y"))
        
        # 1. Satır
        ttk.Label(giris_frame, text="Tarih:").grid(row=0, column=0, padx=5, sticky=W)
        ttk.Entry(giris_frame, textvariable=self.tarih_var, width=15).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(giris_frame, text="Danışan Adı:").grid(row=0, column=2, padx=5, sticky=W)
        self.ent_danisan = ttk.Entry(giris_frame, width=25)
        self.ent_danisan.grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(giris_frame, text="Terapist:").grid(row=0, column=4, padx=5, sticky=W)
        self.cmb_terapist = ttk.Combobox(
            giris_frame,
            values=["Pervin Hoca", "Çağlar Hoca", "Elif Hoca", "Arif Hoca", "Sena Hoca", "Name Hoca"],
            state="readonly"
        )
        self.cmb_terapist.current(0)
        self.cmb_terapist.grid(row=0, column=5, padx=5, pady=5)

        # 2. Satır
        ttk.Label(giris_frame, text="Hizmet Bedeli (TL):").grid(row=1, column=0, padx=5, sticky=W)
        self.ent_bedel = ttk.Entry(giris_frame, width=15)
        self.ent_bedel.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(giris_frame, text="Alınan Ücret (TL):").grid(row=1, column=2, padx=5, sticky=W)
        self.ent_alinan = ttk.Entry(giris_frame, width=25)
        self.ent_alinan.insert(0, "0")  # Varsayılan 0
        self.ent_alinan.grid(row=1, column=3, padx=5, pady=5)

        ttk.Label(giris_frame, text="Notlar:").grid(row=1, column=4, padx=5, sticky=W)
        self.ent_not = ttk.Entry(giris_frame, width=30)
        self.ent_not.grid(row=1, column=5, padx=5, pady=5)

        # Kaydet Butonu (Büyük)
        btn_kaydet = ttk.Button(
            giris_frame,
            text="KAYDET VE LİSTELE",
            bootstyle="success",
            command=self.kayit_ekle,
        )
        btn_kaydet.grid(row=0, column=6, rowspan=2, padx=20, sticky="nsew")

        # --- ORTA KISIM: ARAMA VE İSTATİSTİK ---
        orta_panel = ttk.Frame(ana_panel)
        orta_panel.pack(fill=X, pady=5)

        ttk.Label(orta_panel, text="Danışan Ara:", font=("Bold")).pack(side=LEFT)
        self.ent_ara = ttk.Entry(orta_panel)
        self.ent_ara.pack(side=LEFT, padx=10)
        self.ent_ara.bind("<KeyRelease>", self.listele)  # Her tuşta ara

        self.lbl_ozet = ttk.Label(
            orta_panel,
            text="Toplam Alacak: 0.00 TL",
            font=("Arial", 12, "bold"),
            bootstyle="danger",
        )
        self.lbl_ozet.pack(side=RIGHT, padx=10)

        # --- ALT KISIM: TABLO (TREEVIEW) ---
        # Tabloyu kapsayan frame
        tablo_frame = ttk.Frame(ana_panel)
        tablo_frame.pack(fill=BOTH, expand=True, pady=5)

        cols = ("ID", "Tarih", "Danışan", "Terapist", "Bedel", "Ödenen", "KALAN BORÇ", "Notlar")
        self.tree = ttk.Treeview(tablo_frame, columns=cols, show="headings", bootstyle="info")
        
        # Sütun Başlıkları
        for col in cols:
            self.tree.heading(col, text=col)
        
        # Sütun Genişlikleri
        self.tree.column("ID", width=0, stretch=False)  # ID'yi gizle
        self.tree.column("Tarih", width=100, anchor="center")
        self.tree.column("Danışan", width=200)
        self.tree.column("Terapist", width=150)
        self.tree.column("Bedel", width=100, anchor="e")
        self.tree.column("Ödenen", width=100, anchor="e")
        self.tree.column("KALAN BORÇ", width=120, anchor="e")
        self.tree.column("Notlar", width=200)

        # Scrollbar (Kaydırma Çubuğu)
        scrolly = ttk.Scrollbar(tablo_frame, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrolly.set)
        scrolly.pack(side=RIGHT, fill=Y)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)

        # Renk Etiketleri
        self.tree.tag_configure('borclu', background='#f8d7da', foreground='#721c24')  # Kırmızı ton
        self.tree.tag_configure('tamam', background='#d4edda', foreground='#155724')  # Yeşil ton

        # Sağ Tık Menüsü
        self.context_menu = ttk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Ödeme Ekle", command=self.odeme_guncelle)
        self.context_menu.add_command(label="Kaydı Sil", command=self.kayit_sil)
        self.tree.bind("<Button-3>", self.sag_tik)

        # İlk açılışta verileri yükle
        self.listele()
    
    def ana_ekran_egitim_gorevlisi(self, ana_panel):
        """Eğitim Görevlisi için sadece kendi seansları"""
        # Başlık
        ttk.Label(ana_panel, text="KENDİ SEANSLARIM", font=("Arial", 14, "bold"), bootstyle="primary").pack(pady=10)
        
        # Arama
        arama_frame = ttk.Frame(ana_panel)
        arama_frame.pack(fill=X, padx=10, pady=5)
        ttk.Label(arama_frame, text="Danışan Ara:").pack(side=LEFT)
        self.ent_ara_egitim = ttk.Entry(arama_frame)
        self.ent_ara_egitim.pack(side=LEFT, padx=10, fill=X, expand=True)
        self.ent_ara_egitim.bind("<KeyRelease>", self.kendi_seanslarim)
        
        # Tablo
        tablo_frame = ttk.Frame(ana_panel)
        tablo_frame.pack(fill=BOTH, expand=True, padx=10, pady=5)
        
        cols = ("ID", "Tarih", "Danışan", "Bedel", "Ödenen", "KALAN BORÇ", "Notlar")
        self.tree_egitim = ttk.Treeview(tablo_frame, columns=cols, show="headings", bootstyle="info")
        
        for col in cols:
            self.tree_egitim.heading(col, text=col)
            self.tree_egitim.column(col, width=100)
        
        self.tree_egitim.column("ID", width=0, stretch=False)
        self.tree_egitim.column("Tarih", width=100)
        self.tree_egitim.column("Danışan", width=200)
        self.tree_egitim.column("Bedel", width=100, anchor=E)
        self.tree_egitim.column("Ödenen", width=100, anchor=E)
        self.tree_egitim.column("KALAN BORÇ", width=120, anchor=E)
        self.tree_egitim.column("Notlar", width=200)
        
        scrollbar = ttk.Scrollbar(tablo_frame, orient=VERTICAL, command=self.tree_egitim.yview)
        self.tree_egitim.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=RIGHT, fill=Y)
        self.tree_egitim.pack(side=LEFT, fill=BOTH, expand=True)
        
        self.tree_egitim.tag_configure('borclu', background='#f8d7da', foreground='#721c24')
        self.tree_egitim.tag_configure('tamam', background='#d4edda', foreground='#155724')
        
        # İlk yükleme
        self.kendi_seanslarim()
    
    def ana_ekran_normal(self, ana_panel):
        """Normal kullanıcı için basit görünüm"""
        ttk.Label(ana_panel, text="Sisteme erişim yetkiniz bulunmamaktadır.", font=("Arial", 12), bootstyle="warning").pack(pady=50)

    # --- FONKSİYONLAR ---
    def veritabani_baglan(self):
        return sqlite3.connect(DB_NAME)

    def listele(self, event=None):
        try:
            kelime = self.ent_ara.get()
            # Tabloyu temizle
            for i in self.tree.get_children():
                self.tree.delete(i)
            
            conn = self.veritabani_baglan()
            cursor = conn.cursor()
            
            sql = "SELECT * FROM kayitlar"
            params = []
            where_conditions = []
            
            # Rol bazlı filtreleme
            if self.kullanici_rol == "egitim_gorevlisi":
                # Eğitim görevlisi sadece kendi seanslarını görür
                kullanici_adi = self.kullanici[1] if self.kullanici else ""
                # Kullanıcı adından terapist adını çıkar (örn: "pervin" -> "Pervin Hoca")
                terapist_adi = kullanici_adi.capitalize() + " Hoca"
                where_conditions.append("terapist = ?")
                params.append(terapist_adi)
            
            # Arama filtresi
            if kelime:
                where_conditions.append("danisan_adi LIKE ?")
                params.append(f"%{kelime}%")
            
            if where_conditions:
                sql += " WHERE " + " AND ".join(where_conditions)
            
            sql += " ORDER BY id DESC" # En yeni en üstte
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            conn.close()

            toplam_alacak = 0
            
            for row in rows:
                borc = row[6]
                toplam_alacak += borc
                tag = 'borclu' if borc > 0 else 'tamam'
                
                # Para birimi formatlama
                row_list = list(row)
                row_list[4] = f"{row[4]:.2f} ₺"
                row_list[5] = f"{row[5]:.2f} ₺"
                row_list[6] = f"{row[6]:.2f} ₺"
                
                self.tree.insert("", END, values=row_list, tags=(tag,))
            
            self.lbl_ozet.config(text=f"Toplam Alacak: {toplam_alacak:,.2f} ₺")

        except Exception as e:
            messagebox.showerror("Hata", f"Listeleme hatası: {e}")

    def kayit_ekle(self):
        try:
            tarih = self.tarih_var.get()
            danisan = self.ent_danisan.get()
            terapist = self.cmb_terapist.get()
            
            if not danisan:
                messagebox.showwarning("Eksik", "Lütfen Danışan Adı giriniz.")
                return

            try:
                bedel = float(self.ent_bedel.get())
                alinan = float(self.ent_alinan.get() or 0)
            except ValueError:
                messagebox.showerror("Hata", "Ücret kısımlarına sadece sayı giriniz (Örn: 2500)")
                return

            kalan = bedel - alinan
            notlar = self.ent_not.get()
            simdi = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

            conn = self.veritabani_baglan()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO kayitlar (tarih, danisan_adi, terapist, hizmet_bedeli, alinan_ucret, kalan_borc, notlar, son_islem_tarihi)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (tarih, danisan, terapist, bedel, alinan, kalan, notlar, simdi))
            conn.commit()
            conn.close()

            self.listele()
            messagebox.showinfo("Başarılı", "Kayıt eklendi.")
            
            # Alanları temizle (Tarih ve Terapist kalsın)
            self.ent_danisan.delete(0, END)
            self.ent_bedel.delete(0, END)
            self.ent_alinan.delete(0, END)
            self.ent_alinan.insert(0, "0")
            self.ent_not.delete(0, END)
            self.ent_danisan.focus() # İmleci isme odakla

        except Exception as e:
            messagebox.showerror("Hata", f"Kayıt eklenemedi: {e}")

    def sag_tik(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def odeme_guncelle(self):
        secili = self.tree.selection()
        if not secili: 
            messagebox.showwarning("Uyarı", "Lütfen ödeme yapılacak kaydı seçiniz.")
            return
        
        item = self.tree.item(secili[0])
        kayit_id = item['values'][0]
        isim = item['values'][2]
        
        # Mevcut kalan borcu göster (formatlanmış değerden temizle)
        try:
            mevcut_kalan_str = item['values'][6]
            # "2500.00 ₺" formatından sayıyı çıkar
            mevcut_kalan = float(mevcut_kalan_str.replace(" ₺", "").replace(",", ""))
        except:
            mevcut_kalan = 0
        
        # Basit input dialog (tkinter standard)
        from tkinter import simpledialog
        miktar = simpledialog.askfloat("Ödeme Al", 
                                       f"{isim} için ne kadar ödeme alındı?\n\nMevcut Kalan Borç: {mevcut_kalan:.2f} ₺",
                                       minvalue=0.01)
        
        if miktar is not None and miktar > 0:
            try:
                conn = self.veritabani_baglan()
                cursor = conn.cursor()
                
                # Mevcut veriyi çek
                cursor.execute("SELECT hizmet_bedeli, alinan_ucret, kalan_borc FROM kayitlar WHERE id=?", (kayit_id,))
                veri = cursor.fetchone()
                
                if veri:
                    hizmet_bedeli = veri[0]
                    mevcut_alinan = veri[1]
                    mevcut_kalan_borc = veri[2]
                    
                    # Yeni toplam alınan ücret
                    yeni_toplam_alinan = mevcut_alinan + miktar
                    
                    # Yeni kalan borç hesapla
                    yeni_kalan = hizmet_bedeli - yeni_toplam_alinan
                    
                    # Negatif borç kontrolü (fazla ödeme uyarısı)
                    if yeni_kalan < 0:
                        if not messagebox.askyesno("Fazla Ödeme", 
                                                  f"Ödenen miktar ({miktar:.2f} ₺) kalan borçtan ({mevcut_kalan_borc:.2f} ₺) fazla.\n\n"
                                                  f"Fazla ödeme: {abs(yeni_kalan):.2f} ₺\n\n"
                                                  f"Yine de devam etmek istiyor musunuz?"):
                            conn.close()
                            return
                    
                    # Güncelleme yap
                    simdi = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    cursor.execute("UPDATE kayitlar SET alinan_ucret=?, kalan_borc=?, son_islem_tarihi=? WHERE id=?", 
                                 (yeni_toplam_alinan, yeni_kalan, simdi, kayit_id))
                    conn.commit()
                    
                    if yeni_kalan <= 0:
                        messagebox.showinfo("Başarılı", f"Ödeme başarıyla işlendi.\n\nBorç tamamen ödendi!" if yeni_kalan == 0 
                                          else f"Ödeme başarıyla işlendi.\n\nFazla ödeme: {abs(yeni_kalan):.2f} ₺")
                    else:
                        messagebox.showinfo("Başarılı", f"Ödeme başarıyla işlendi.\n\nKalan borç: {yeni_kalan:.2f} ₺")
                
                conn.close()
                self.listele()
                
            except Exception as e:
                messagebox.showerror("Hata", f"Güncelleme hatası: {e}")
        elif miktar is not None:
            messagebox.showwarning("Uyarı", "Ödeme miktarı 0'dan büyük olmalıdır.")

    def kayit_sil(self):
        secili = self.tree.selection()
        if not secili: return
        
        if messagebox.askyesno("Sil", "Bu kaydı silmek istediğine emin misin?"):
            try:
                item = self.tree.item(secili[0])
                kayit_id = item['values'][0]
                
                conn = self.veritabani_baglan()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM kayitlar WHERE id=?", (kayit_id,))
                conn.commit()
                conn.close()
                self.listele()
            except Exception as e:
                messagebox.showerror("Hata", f"Silme hatası: {e}")

    def excel_aktar(self):
        try:
            dosya_yolu = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel Dosyası", "*.xlsx")])
            if not dosya_yolu: return

            conn = self.veritabani_baglan()
            df = pd.read_sql_query("SELECT * FROM kayitlar", conn)
            conn.close()
            
            df.to_excel(dosya_yolu, index=False)
            messagebox.showinfo("Başarılı", "Excel dosyası oluşturuldu.")
            os.startfile(dosya_yolu)
        except Exception as e:
            messagebox.showerror("Hata", f"Excel hatası: {e}")

    def yedek_klasoru_ac(self):
        try:
            if not os.path.exists(BACKUP_DIR):
                os.makedirs(BACKUP_DIR)
            os.startfile(BACKUP_DIR)
        except Exception as e:
            messagebox.showerror("Hata", f"Klasör açılamadı: {e}")

    def hakkinda_goster(self):
        messagebox.showinfo("Hakkında", "Leta Aile ve Çocuk Yönetim Sistemi\nSürüm: 4.0 (Final)\n\nÖzel Yazılım Çözümü")

    def kullanicilari_listele(self):
        """Kullanıcıları listeleyen pencere"""
        pencere = ttk.Toplevel(self)
        pencere.title("Kullanıcı Listesi")
        pencere.geometry("800x500")
        pencere.transient(self)
        pencere.grab_set()
        
        # Başlık
        ttk.Label(pencere, text="KAYITLI KULLANICILAR", font=("Arial", 14, "bold"), bootstyle="primary").pack(pady=10)
        
        # Tablo
        frame = ttk.Frame(pencere, padding=10)
        frame.pack(fill=BOTH, expand=True)
        
        cols = ("ID", "Kullanıcı Adı", "Ad Soyad", "E-posta", "Rol", "Oluşturma Tarihi", "Son Giriş", "Durum")
        tree = ttk.Treeview(frame, columns=cols, show="headings", bootstyle="info")
        
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=100)
        
        tree.column("ID", width=50)
        tree.column("Kullanıcı Adı", width=120)
        tree.column("Ad Soyad", width=150)
        tree.column("E-posta", width=150)
        tree.column("Rol", width=100)
        tree.column("Oluşturma Tarihi", width=120)
        tree.column("Son Giriş", width=120)
        tree.column("Durum", width=80)
        
        scrollbar = ttk.Scrollbar(frame, orient=VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=RIGHT, fill=Y)
        tree.pack(side=LEFT, fill=BOTH, expand=True)
        
        # Verileri yükle
        try:
            conn = self.veritabani_baglan()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, kullanici_adi, ad_soyad, email, rol, olusturma_tarihi, son_giris_tarihi, aktif
                FROM kullanicilar
                ORDER BY id DESC
            """)
            rows = cursor.fetchall()
            conn.close()
            
            for row in rows:
                durum = "Aktif" if row[7] == 1 else "Pasif"
                rol_text = {"admin": "Yönetici", "pervin_hanim": "Pervin Hanım", "normal": "Normal"}.get(row[4], row[4])
                tree.insert("", END, values=(row[0], row[1], row[2] or "", row[3] or "", rol_text, row[5] or "", row[6] or "", durum))
        except Exception as e:
            messagebox.showerror("Hata", f"Kullanıcılar yüklenemedi: {e}")
        
        ttk.Button(pencere, text="Kapat", bootstyle="secondary", command=pencere.destroy).pack(pady=10)
    
    def kullanici_sil(self):
        """Kullanıcı silme penceresi"""
        pencere = ttk.Toplevel(self)
        pencere.title("Kullanıcı Sil")
        pencere.geometry("500x400")
        pencere.transient(self)
        pencere.grab_set()
        
        ttk.Label(pencere, text="KULLANICI SİL", font=("Arial", 14, "bold"), bootstyle="danger").pack(pady=10)
        
        frame = ttk.Frame(pencere, padding=10)
        frame.pack(fill=BOTH, expand=True)
        
        cols = ("ID", "Kullanıcı Adı", "Ad Soyad", "Rol")
        tree = ttk.Treeview(frame, columns=cols, show="headings", bootstyle="info")
        
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=100)
        
        tree.column("ID", width=50)
        tree.column("Kullanıcı Adı", width=150)
        tree.column("Ad Soyad", width=150)
        tree.column("Rol", width=100)
        
        scrollbar = ttk.Scrollbar(frame, orient=VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=RIGHT, fill=Y)
        tree.pack(side=LEFT, fill=BOTH, expand=True)
        
        # Verileri yükle
        try:
            conn = self.veritabani_baglan()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, kullanici_adi, ad_soyad, rol
                FROM kullanicilar
                WHERE aktif = 1
                ORDER BY kullanici_adi
            """)
            rows = cursor.fetchall()
            conn.close()
            
            for row in rows:
                rol_text = {"admin": "Yönetici", "pervin_hanim": "Pervin Hanım", "normal": "Normal"}.get(row[3], row[3])
                tree.insert("", END, values=(row[0], row[1], row[2] or "", rol_text))
        except Exception as e:
            messagebox.showerror("Hata", f"Kullanıcılar yüklenemedi: {e}")
        
        def sil():
            secili = tree.selection()
            if not secili:
                messagebox.showwarning("Uyarı", "Lütfen silinecek kullanıcıyı seçiniz.")
                return
            
            item = tree.item(secili[0])
            kullanici_id = item['values'][0]
            kullanici_adi = item['values'][1]
            rol = item['values'][3]
            
            # Admin ve Kurum Müdürü silinemez
            if rol in ["Yönetici", "Kurum Müdürü"]:
                messagebox.showerror("Hata", "Bu kullanıcı silinemez!")
                return
            
            if messagebox.askyesno("Onay", f"'{kullanici_adi}' kullanıcısını silmek istediğinize emin misiniz?\n\nBu işlem geri alınamaz!"):
                try:
                    conn = self.veritabani_baglan()
                    cursor = conn.cursor()
                    # Fiziksel silme yerine pasif yap
                    cursor.execute("UPDATE kullanicilar SET aktif = 0 WHERE id = ?", (kullanici_id,))
                    conn.commit()
                    conn.close()
                    
                    messagebox.showinfo("Başarılı", f"'{kullanici_adi}' kullanıcısı silindi.")
                    pencere.destroy()
                except Exception as e:
                    messagebox.showerror("Hata", f"Silme hatası: {e}")
        
        btn_frame = ttk.Frame(pencere)
        btn_frame.pack(fill=X, pady=10, padx=10)
        ttk.Button(btn_frame, text="SİL", bootstyle="danger", command=sil).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="İptal", bootstyle="secondary", command=pencere.destroy).pack(side=LEFT, padx=5)

    # --- YENİ MODÜL FONKSİYONLARI ---
    def kendi_seanslarim(self, event=None):
        """Eğitim görevlisi için kendi seanslarını listele"""
        try:
            if not hasattr(self, 'tree_egitim'):
                return
                
            for i in self.tree_egitim.get_children():
                self.tree_egitim.delete(i)
            
            kelime = self.ent_ara_egitim.get() if hasattr(self, 'ent_ara_egitim') else ""
            kullanici_adi = self.kullanici[1] if self.kullanici else ""
            terapist_adi = kullanici_adi.capitalize() + " Hoca"
            
            conn = self.veritabani_baglan()
            cursor = conn.cursor()
            
            sql = "SELECT * FROM kayitlar WHERE terapist = ?"
            params = [terapist_adi]
            
            if kelime:
                sql += " AND danisan_adi LIKE ?"
                params.append(f"%{kelime}%")
            
            sql += " ORDER BY id DESC"
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            conn.close()
            
            for row in rows:
                borc = row[6]
                tag = 'borclu' if borc > 0 else 'tamam'
                
                row_list = list(row)
                row_list[4] = f"{row[4]:.2f} ₺"
                row_list[5] = f"{row[5]:.2f} ₺"
                row_list[6] = f"{row[6]:.2f} ₺"
                
                self.tree_egitim.insert("", END, values=(row_list[0], row_list[1], row_list[2], row_list[4], row_list[5], row_list[6], row_list[7]), tags=(tag,))
        except Exception as e:
            if hasattr(self, 'tree_egitim'):
                messagebox.showerror("Hata", f"Listeleme hatası: {e}")
    
    def kendi_ucretlerim(self):
        """Eğitim görevlisi için kendi ücretlerini göster"""
        self.kendi_seanslarim()
        messagebox.showinfo("Bilgi", "Kendi ücretleriniz yukarıda listelenmiştir.")
    
    def seans_takvimi_goster(self):
        """Günlük seans takvimi"""
        messagebox.showinfo("Bilgi", "Seans Takvimi modülü yakında eklenecek.")
    
    def haftalik_takvim_goster(self):
        """Haftalık seans takvimi"""
        messagebox.showinfo("Bilgi", "Haftalık Takvim modülü yakında eklenecek.")
    
    def yeni_seans_ekle(self):
        """Yeni seans ekleme penceresi"""
        messagebox.showinfo("Bilgi", "Yeni Seans Ekleme modülü yakında eklenecek.")
    
    def danisan_yonetimi(self):
        """Danışan yönetimi penceresi"""
        messagebox.showinfo("Bilgi", "Danışan Yönetimi modülü yakında eklenecek.")
    
    def randevu_yonetimi(self):
        """Randevu yönetimi penceresi"""
        messagebox.showinfo("Bilgi", "Randevu Yönetimi modülü yakında eklenecek.")
    
    def gorev_takibi(self):
        """Görev takibi penceresi"""
        messagebox.showinfo("Bilgi", "Görev Takibi modülü yakında eklenecek.")
    
    def ucret_takibi_goster(self):
        """Ücret takibi - mevcut ekranı göster"""
        messagebox.showinfo("Bilgi", "Ücret takibi ana ekranda görüntülenmektedir.")
    
    def gelir_gider_raporu(self):
        """Gelir-Gider raporu"""
        messagebox.showinfo("Bilgi", "Gelir-Gider Raporu modülü yakında eklenecek.")
    
    def odeme_islemleri(self):
        """Ödeme işlemleri"""
        messagebox.showinfo("Bilgi", "Ödeme İşlemleri modülü yakında eklenecek.")

    def cikis_yap(self):
        self.quit()

if __name__ == "__main__":
    sistem_kontrol()
    
    # Veri entegrasyonunu kontrol et ve çalıştır
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM danisanlar")
        danisan_sayisi = cursor.fetchone()[0]
        conn.close()
        
        # Eğer danışan yoksa ve Excel/DOCX dosyaları varsa entegre et
        if danisan_sayisi == 0:
            excel_files = ["SEANS ÜCRET TAKİP.xlsx", "ÖĞRENCİ LİSTESİ.docx", "ÖĞRENCİ AİLE NUMARALARI.docx"]
            if all(os.path.exists(f) for f in excel_files):
                try:
                    # Veri entegrasyon scriptini çalıştır
                    import subprocess
                    result = subprocess.run([sys.executable, "veri_entegrasyon.py"], 
                                          capture_output=True, text=True, timeout=30)
                    if result.returncode == 0:
                        print("Veriler başarıyla entegre edildi.")
                except Exception as e:
                    print(f"Veri entegrasyonu hatası: {e}")
    except Exception as e:
        print(f"Veri kontrolü hatası: {e}")
    
    try:
        app = LoginPenceresi()
        app.mainloop()
    except Exception as e:
        # Program hiç açılmazsa hatayı görelim
        messagebox.showerror("Kritik Başlatma Hatası", str(e))