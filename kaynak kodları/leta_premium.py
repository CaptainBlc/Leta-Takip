import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from tkinter import filedialog
import sqlite3
import datetime
import os
import sys
import shutil
import pandas as pd

# --- AYARLAR VE YOL TANIMLARI ---
# Exe olduğunda çalışacağı yol
if getattr(sys, 'frozen', False):
    APP_PATH = os.path.dirname(sys.executable)
elif __file__:
    APP_PATH = os.path.dirname(__file__)

DB_NAME = os.path.join(APP_PATH, "leta_data.db")
BACKUP_DIR = os.path.join(APP_PATH, "Yedekler")

# --- VERİTABANI VE YEDEKLEME ---
def ilk_kurulum():
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    
    # Otomatik Yedekleme (Her açılışta)
    if os.path.exists(DB_NAME):
        tarih_damgasi = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        yedek_yolu = os.path.join(BACKUP_DIR, f"yedek_{tarih_damgasi}.db")
        shutil.copy2(DB_NAME, yedek_yolu)
        # Eski yedekleri temizle (Son 10 yedeği tut)
        yedekler = sorted(os.listdir(BACKUP_DIR))
        if len(yedekler) > 10:
            os.remove(os.path.join(BACKUP_DIR, yedekler[0]))

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
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
    conn.commit()
    conn.close()

# --- GİRİŞ EKRANI (LOGIN) ---
class LoginWindow(ttk.Window):
    def __init__(self):
        super().__init__(themename="cosmo") # "cosmo", "flatly", "journal" deneyebilirsin
        self.title("Güvenli Giriş - Leta Yönetim")
        self.geometry("400x350")
        self.resizable(False, False)
        
        # Ortala
        self.place_window_center()

        # Logo / Başlık Alanı
        lbl_baslik = ttk.Label(self, text="Leta Aile ve Çocuk", font=("Helvetica", 16, "bold"), bootstyle="primary")
        lbl_baslik.pack(pady=30)
        
        lbl_alt = ttk.Label(self, text="Yönetim Paneli Giriş", font=("Helvetica", 10))
        lbl_alt.pack(pady=(0, 20))

        # Form
        frm = ttk.Frame(self, padding=20)
        frm.pack(fill=BOTH, expand=True)

        self.ent_user = ttk.Entry(frm, bootstyle="info")
        self.ent_user.insert(0, "admin") # Varsayılan kullanıcı
        self.ent_user.pack(fill=X, pady=10)
        
        self.ent_pass = ttk.Entry(frm, show="*", bootstyle="info")
        self.ent_pass.pack(fill=X, pady=10)
        
        btn_giris = ttk.Button(frm, text="GİRİŞ YAP", bootstyle="success", command=self.kontrol)
        btn_giris.pack(fill=X, pady=20)

        lbl_info = ttk.Label(self, text="Varsayılan Şifre: 1234", font=("Arial", 8), foreground="gray")
        lbl_info.pack(side=BOTTOM, pady=10)

    def kontrol(self):
        user = self.ent_user.get()
        pasw = self.ent_pass.get()
        
        # Basit güvenlik (İstersen veritabanından çekebilirsin)
        if user == "admin" and pasw == "1234":
            self.destroy() # Login kapat
            app = AnaUygulama() # Ana ekranı aç
            app.mainloop()
        else:
            Messagebox.show_error("Hatalı kullanıcı adı veya şifre!", "Giriş Hatası")

# --- ANA UYGULAMA ---
class AnaUygulama(ttk.Toplevel):
    def __init__(self):
        super().__init__()
        self.title("Leta Aile ve Çocuk - Kurumsal Yönetim Sistemi v3.0")
        self.geometry("1200x800")
        self.protocol("WM_DELETE_WINDOW", self.kapat)
        
        # Üst Menü Barı
        self.menu_olustur()
        
        # Ana Konteyner
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=BOTH, expand=True)

        # --- SOL PANEL (İstatistikler) ---
        side_panel = ttk.Frame(main_frame, width=250, bootstyle="secondary")
        side_panel.pack(side=LEFT, fill=Y, padx=(0, 10))
        
        ttk.Label(side_panel, text="ÖZET DURUM", font=("Arial", 12, "bold"), bootstyle="inverse-secondary").pack(pady=10, fill=X, padx=5)
        
        self.meter_borc = ttk.Meter(
            side_panel,
            metersize=180,
            amountused=0,
            metertype="semi",
            subtext="Toplam Alacak",
            interactive=False,
            bootstyle="danger"
        )
        self.meter_borc.pack(pady=10)

        self.lbl_kasa = ttk.Label(side_panel, text="Kasa: 0.00 TL", font=("Arial", 14, "bold"), bootstyle="success")
        self.lbl_kasa.pack(pady=20)
        
        ttk.Separator(side_panel).pack(fill=X, pady=10, padx=5)
        ttk.Button(side_panel, text="Excel'e Aktar", bootstyle="success-outline", command=self.excel_export).pack(fill=X, padx=10, pady=5)
        ttk.Button(side_panel, text="Yedeği Aç", bootstyle="info-outline", command=lambda: os.startfile(BACKUP_DIR)).pack(fill=X, padx=10, pady=5)

        # --- SAĞ PANEL (İşlemler) ---
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=LEFT, fill=BOTH, expand=True)

        # 1. Giriş Formu (Collapsible gibi şık bir frame)
        entry_frame = ttk.LabelFrame(right_panel, text="Hızlı Seans Girişi", padding=15, bootstyle="primary")
        entry_frame.pack(fill=X, pady=(0, 10))

        # Grid Düzeni
        self.tarih_var = ttk.StringVar(value=datetime.datetime.now().strftime("%d.%m.%Y"))
        ttk.Label(entry_frame, text="Tarih:").grid(row=0, column=0, sticky=W)
        ttk.DateEntry(entry_frame, dateformat="%d.%m.%Y", firstweekday=0, variable=self.tarih_var).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(entry_frame, text="Danışan:").grid(row=0, column=2, sticky=W)
        self.ent_danisan = ttk.Entry(entry_frame)
        self.ent_danisan.grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(entry_frame, text="Terapist:").grid(row=0, column=4, sticky=W)
        self.cmb_terapist = ttk.Combobox(entry_frame, values=["Pervin Hoca", "Çağlar Hoca", "Elif Hoca", "Arif Hoca", "Sena Hoca", "Name Hoca"], state="readonly")
        self.cmb_terapist.current(0)
        self.cmb_terapist.grid(row=0, column=5, padx=5, pady=5)

        ttk.Label(entry_frame, text="Ücret (TL):").grid(row=1, column=0, sticky=W)
        self.ent_bedel = ttk.Entry(entry_frame)
        self.ent_bedel.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(entry_frame, text="Alınan (TL):").grid(row=1, column=2, sticky=W)
        self.ent_alinan = ttk.Entry(entry_frame)
        self.ent_alinan.insert(0, "0")
        self.ent_alinan.grid(row=1, column=3, padx=5, pady=5)

        ttk.Label(entry_frame, text="Not:").grid(row=1, column=4, sticky=W)
        self.ent_not = ttk.Entry(entry_frame)
        self.ent_not.grid(row=1, column=5, padx=5, pady=5)

        ttk.Button(entry_frame, text="KAYDET", bootstyle="primary", command=self.kayit_ekle).grid(row=0, column=6, rowspan=2, padx=15, sticky="ns")

        # 2. Arama ve Tablo
        filter_frame = ttk.Frame(right_panel)
        filter_frame.pack(fill=X, pady=5)
        ttk.Label(filter_frame, text="Danışan Ara:", bootstyle="primary").pack(side=LEFT)
        self.ent_ara = ttk.Entry(filter_frame)
        self.ent_ara.pack(side=LEFT, padx=5)
        self.ent_ara.bind("<KeyRelease>", self.listele)

        # Tablo
        cols = ("ID", "Tarih", "Danışan", "Terapist", "Bedel", "Ödenen", "KALAN BORÇ", "Notlar")
        self.tree = ttk.Treeview(right_panel, columns=cols, show="headings", bootstyle="info")
        
        for col in cols:
            self.tree.heading(col, text=col)
        
        self.tree.column("ID", width=0, stretch=False)
        self.tree.column("Tarih", width=90)
        self.tree.column("Danışan", width=150)
        self.tree.column("Bedel", width=80, anchor=E)
        self.tree.column("Ödenen", width=80, anchor=E)
        self.tree.column("KALAN BORÇ", width=100, anchor=E)
        
        # Scrollbar
        scrolly = ttk.Scrollbar(right_panel, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrolly.set)
        scrolly.pack(side=RIGHT, fill=Y)
        self.tree.pack(fill=BOTH, expand=True)

        # Tablo Renkleri
        self.tree.tag_configure('borclu', background='#f8d7da', foreground='#721c24') # Bootstrap Danger Light
        self.tree.tag_configure('tamam', background='#d4edda', foreground='#155724') # Bootstrap Success Light
        
        # Sağ Tık Menü
        self.context_menu = ttk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Ödeme Ekle", command=self.odeme_ekle_dialog)
        self.context_menu.add_command(label="Kaydı Sil", command=self.kayit_sil)
        self.tree.bind("<Button-3>", self.sag_tik)

        # Başlangıç Verileri
        self.listele()

    def menu_olustur(self):
        menubar = ttk.Menu(self)
        self.config(menu=menubar)
        dosya_menu = ttk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Dosya", menu=dosya_menu)
        dosya_menu.add_command(label="Yedek Al", command=self.manuel_yedek)
        dosya_menu.add_command(label="Çıkış", command=self.kapat)
        
        yardim_menu = ttk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Yardım", menu=yardim_menu)
        yardim_menu.add_command(label="Hakkında", command=lambda: Messagebox.show_info("Leta Yönetim Paneli v3.0\nGeliştirici: [Adınız]", "Hakkında"))

    def veritabani_baglan(self):
        return sqlite3.connect(DB_NAME)

    def listele(self, event=None):
        search = self.ent_ara.get()
        # Temizle
        for i in self.tree.get_children():
            self.tree.delete(i)
        
        conn = self.veritabani_baglan()
        cursor = conn.cursor()
        
        sql = "SELECT * FROM kayitlar"
        params = []
        if search:
            sql += " WHERE danisan_adi LIKE ?"
            params.append(f"%{search}%")
        sql += " ORDER BY id DESC"
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        toplam_alacak = 0
        toplam_kasa = 0

        for row in rows:
            borc = row[6]
            toplam_alacak += borc
            toplam_kasa += row[5]
            
            tag = 'borclu' if borc > 0 else 'tamam'
            
            # Para formatı
            gosterim = list(row)
            gosterim[4] = f"{row[4]:.2f} ₺"
            gosterim[5] = f"{row[5]:.2f} ₺"
            gosterim[6] = f"{row[6]:.2f} ₺"

            self.tree.insert("", END, values=gosterim, tags=(tag,))

        # İstatistikleri Güncelle
        self.meter_borc.configure(amountused=int(toplam_alacak))
        self.lbl_kasa.configure(text=f"Kasa: {toplam_kasa:,.2f} ₺")

    def kayit_ekle(self):
        try:
            tarih = self.tarih_var.get()
            danisan = self.ent_danisan.get()
            terapist = self.cmb_terapist.get()
            bedel = float(self.ent_bedel.get())
            alinan = float(self.ent_alinan.get() or 0)
            kalan = bedel - alinan
            notlar = self.ent_not.get()
            
            if not danisan: return

            conn = self.veritabani_baglan()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO kayitlar (tarih, danisan_adi, terapist, hizmet_bedeli, alinan_ucret, kalan_borc, notlar, son_islem_tarihi) VALUES (?,?,?,?,?,?,?,?)",
                           (tarih, danisan, terapist, bedel, alinan, kalan, notlar, datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))
            conn.commit()
            conn.close()
            
            self.listele()
            Messagebox.show_info("Kayıt başarıyla eklendi.", "Başarılı")
            
            # Temizle
            self.ent_danisan.delete(0, END)
            self.ent_bedel.delete(0, END)
            self.ent_alinan.delete(0, END)
            self.ent_alinan.insert(0, "0")
            self.ent_not.delete(0, END)

        except ValueError:
            Messagebox.show_error("Lütfen sayısal alanları doğru giriniz.", "Hata")

    def sag_tik(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def odeme_ekle_dialog(self):
        # Basit bir input dialog (ttkbootstrap yoksa standardı kullanırız ama burada var)
        sel = self.tree.selection()
        if not sel: return
        item = self.tree.item(sel[0])
        borc_str = item['values'][6].replace(" ₺", "").replace(",", "")
        
        try:
            from tkinter.simpledialog import askfloat
            miktar = askfloat("Ödeme Al", f"Ödenen Miktar?\n(Kalan Borç: {borc_str})")
            if miktar:
                # Veritabanı güncelleme mantığı (Basitleştirilmiş)
                kayit_id = item['values'][0]
                conn = self.veritabani_baglan()
                cursor = conn.cursor()
                
                # Mevcut veriyi al
                cursor.execute("SELECT hizmet_bedeli, alinan_ucret FROM kayitlar WHERE id=?", (kayit_id,))
                res = cursor.fetchone()
                yeni_alinan = res[1] + miktar
                yeni_kalan = res[0] - yeni_alinan
                
                cursor.execute("UPDATE kayitlar SET alinan_ucret=?, kalan_borc=? WHERE id=?", (yeni_alinan, yeni_kalan, kayit_id))
                conn.commit()
                conn.close()
                self.listele()
                Messagebox.show_info(f"{miktar} TL ödeme alındı.", "Güncellendi")
        except Exception as e:
            Messagebox.show_error(str(e), "Hata")

    def kayit_sil(self):
        sel = self.tree.selection()
        if not sel: return
        if Messagebox.yesno("Bu kaydı silmek istediğine emin misin?", "Silinsin mi?", alert=True):
            item = self.tree.item(sel[0])
            conn = self.veritabani_baglan()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM kayitlar WHERE id=?", (item['values'][0],))
            conn.commit()
            conn.close()
            self.listele()

    def excel_export(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel Dosyası", "*.xlsx")])
        if not file_path: return
        
        conn = self.veritabani_baglan()
        df = pd.read_sql_query("SELECT * FROM kayitlar", conn)
        conn.close()
        
        try:
            df.to_excel(file_path, index=False)
            os.startfile(file_path) # Dosyayı aç
        except Exception as e:
            Messagebox.show_error(f"Excel'e aktarırken hata: {e}", "Hata")

    def manuel_yedek(self):
        Messagebox.show_info(f"Yedekler otomatik olarak '{BACKUP_DIR}' klasörüne alınıyor.", "Bilgi")

    def kapat(self):
        self.quit()

if __name__ == "__main__":
    ilk_kurulum()
    # Uygulamayı Login ekranı ile başlat
    app = LoginWindow()
    app.mainloop()