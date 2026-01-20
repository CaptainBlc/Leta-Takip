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
        x_c = int((screen_width/2) - (350/2))
        y_c = int((screen_height/2) - (300/2))
        self.geometry(f"350x300+{x_c}+{y_c}")
        self.resizable(False, False)

        ttk.Label(self, text="LETA YÖNETİM", font=("Arial", 16, "bold"), bootstyle="primary").pack(pady=30)

        frm = ttk.Frame(self, padding=20)
        frm.pack(fill=BOTH, expand=True)

        self.ent_user = ttk.Entry(frm, bootstyle="primary")
        self.ent_user.insert(0, "admin")
        self.ent_user.pack(fill=X, pady=10)
        
        self.ent_pass = ttk.Entry(frm, show="*", bootstyle="primary")
        self.ent_pass.pack(fill=X, pady=10)
        
        ttk.Button(frm, text="GİRİŞ YAP", bootstyle="success", command=self.giris_yap).pack(fill=X, pady=10)
        ttk.Label(self, text="Şifre: 1234", font=("Arial", 8), foreground="gray").pack(side=BOTTOM, pady=5)

    def giris_yap(self):
        # Basit giriş kontrolü
        if self.ent_user.get() == "admin" and self.ent_pass.get() == "1234":
            # Kök pencereyi YOK ETMİYORUZ, sadece gizliyoruz.
            self.withdraw()
            # Ana uygulamayı aynı Tk kökü üzerinde Toplevel olarak aç
            AnaUygulama(self)
        else:
            messagebox.showerror("Hata", "Kullanıcı adı veya şifre yanlış!")


# --- ANA UYGULAMA ---
class AnaUygulama(ttk.Toplevel):
    """
    Asıl yönetim ekranı. Login penceresinin üzerinde çalışan bir Toplevel.
    """
    def __init__(self, master=None):
        super().__init__(master=master)
        self.title("Leta Aile ve Çocuk - Yönetim Sistemi v4.0 (Final)")
        self.geometry("1200x750")
        self.protocol("WM_DELETE_WINDOW", self.cikis_yap)
        
        # Menü Çubuğu
        menubar = ttk.Menu(self)
        self.config(menu=menubar)
        
        dosya_menu = ttk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Dosya İşlemleri", menu=dosya_menu)
        dosya_menu.add_command(label="Excel'e Aktar", command=self.excel_aktar)
        dosya_menu.add_command(label="Yedek Klasörünü Aç", command=self.yedek_klasoru_ac)
        dosya_menu.add_separator()
        dosya_menu.add_command(label="Çıkış", command=self.cikis_yap)
        
        yardim_menu = ttk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Yardım", menu=yardim_menu)
        yardim_menu.add_command(label="Hakkında", command=self.hakkinda_goster)

        # ANA DÜZEN
        ana_panel = ttk.Frame(self, padding=10)
        ana_panel.pack(fill=BOTH, expand=True)

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
            if kelime:
                sql += " WHERE danisan_adi LIKE ?"
                params.append(f"%{kelime}%")
            
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

    def cikis_yap(self):
        self.quit()

if __name__ == "__main__":
    sistem_kontrol()
    try:
        app = LoginPenceresi()
        app.mainloop()
    except Exception as e:
        # Program hiç açılmazsa hatayı görelim
        messagebox.showerror("Kritik Başlatma Hatası", str(e))