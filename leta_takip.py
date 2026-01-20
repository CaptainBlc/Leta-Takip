import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import datetime

# --- VERİTABANI BAĞLANTISI VE KURULUMU ---
def veritabani_kur():
    conn = sqlite3.connect("leta_veritabani.db")
    cursor = conn.cursor()
    # Eğer tablo yoksa oluşturuyoruz
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS kayitlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT,
            danisan_adi TEXT,
            terapist TEXT,
            hizmet_bedeli REAL,
            alinan_ucret REAL,
            kalan_borc REAL,
            notlar TEXT
        )
    """)
    conn.commit()
    conn.close()

# --- İŞLEM FONKSİYONLARI ---
def kayit_ekle():
    tarih = entry_tarih.get()
    danisan = entry_danisan.get()
    terapist = combo_terapist.get()
    
    try:
        bedel = float(entry_bedel.get())
        alinan = float(entry_alinan.get())
    except ValueError:
        messagebox.showerror("Hata", "Lütfen ücret kısımlarına sadece sayı giriniz.")
        return

    kalan = bedel - alinan
    notlar = entry_not.get()

    if danisan == "":
        messagebox.showwarning("Uyarı", "Danışan adı boş olamaz.")
        return

    conn = sqlite3.connect("leta_veritabani.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO kayitlar (tarih, danisan_adi, terapist, hizmet_bedeli, alinan_ucret, kalan_borc, notlar) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (tarih, danisan, terapist, bedel, alinan, kalan, notlar))
    conn.commit()
    conn.close()
    
    messagebox.showinfo("Başarılı", "Kayıt başarıyla eklendi.")
    listeyi_yenile()
    # Giriş alanlarını temizle
    entry_danisan.delete(0, tk.END)
    entry_bedel.delete(0, tk.END)
    entry_alinan.delete(0, tk.END)

def listeyi_yenile():
    # Tabloyu temizle
    for i in tree.get_children():
        tree.delete(i)
    
    conn = sqlite3.connect("leta_veritabani.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM kayitlar ORDER BY id DESC") # En son eklenen en üstte
    rows = cursor.fetchall()
    conn.close()

    for row in rows:
        # Eğer borç varsa satırı kırmızımsı yapalım (tag kullanımı)
        borc_durumu = row[6]
        tag = 'normal'
        if borc_durumu > 0:
            tag = 'borclu'
        
        tree.insert("", "end", values=row, tags=(tag,))

def borc_sorgula():
    isim = entry_arama.get()
    if isim == "":
        listeyi_yenile()
        return

    for i in tree.get_children():
        tree.delete(i)
    
    conn = sqlite3.connect("leta_veritabani.db")
    cursor = conn.cursor()
    # SQL ile filtreleme (Benzer isimleri bulur)
    cursor.execute("SELECT * FROM kayitlar WHERE danisan_adi LIKE ?", ('%' + isim + '%',))
    rows = cursor.fetchall()
    
    toplam_borc = 0
    for row in rows:
        toplam_borc += row[6]
        tag = 'borclu' if row[6] > 0 else 'normal'
        tree.insert("", "end", values=row, tags=(tag,))
    
    conn.close()
    lbl_toplam_sonuc.config(text=f"{isim} için Toplam Borç: {toplam_borc} TL", fg="red")

# --- ARAYÜZ (GUI) TASARIMI ---
root = tk.Tk()
root.title("Leta Aile ve Çocuk - Borç Takip Sistemi v1.0")
root.geometry("1000x600")

# Veritabanını başlat
veritabani_kur()

# 1. BÖLÜM: KAYIT GİRİŞ PANELİ
frame_giris = tk.LabelFrame(root, text="Yeni Seans Girişi", padx=10, pady=10)
frame_giris.pack(fill="x", padx=10, pady=5)

tk.Label(frame_giris, text="Tarih (GG.AA.YYYY):").grid(row=0, column=0)
entry_tarih = tk.Entry(frame_giris)
entry_tarih.insert(0, datetime.datetime.now().strftime("%d.%m.%Y")) # Bugünün tarihi
entry_tarih.grid(row=0, column=1)

tk.Label(frame_giris, text="Danışan Adı:").grid(row=0, column=2)
entry_danisan = tk.Entry(frame_giris)
entry_danisan.grid(row=0, column=3)

tk.Label(frame_giris, text="Terapist:").grid(row=0, column=4)
combo_terapist = ttk.Combobox(frame_giris, values=["Pervin Hoca", "Çağlar Hoca", "Elif Hoca", "Arif Hoca", "Sena Hoca", "Name Hoca"])
combo_terapist.current(0)
combo_terapist.grid(row=0, column=5)

tk.Label(frame_giris, text="Seans Ücreti:").grid(row=1, column=0)
entry_bedel = tk.Entry(frame_giris)
entry_bedel.grid(row=1, column=1)

tk.Label(frame_giris, text="Tahsil Edilen:").grid(row=1, column=2)
entry_alinan = tk.Entry(frame_giris)
entry_alinan.grid(row=1, column=3)

tk.Label(frame_giris, text="Notlar:").grid(row=1, column=4)
entry_not = tk.Entry(frame_giris)
entry_not.grid(row=1, column=5)

btn_ekle = tk.Button(frame_giris, text="KAYDET", bg="green", fg="white", command=kayit_ekle)
btn_ekle.grid(row=2, column=0, columnspan=6, sticky="we", pady=10)

# 2. BÖLÜM: ARAMA PANELİ
frame_arama = tk.Frame(root, pady=10)
frame_arama.pack()

tk.Label(frame_arama, text="Danışan Ara:").pack(side="left")
entry_arama = tk.Entry(frame_arama)
entry_arama.pack(side="left", padx=5)
btn_ara = tk.Button(frame_arama, text="SORGULA", command=borc_sorgula)
btn_ara.pack(side="left")
lbl_toplam_sonuc = tk.Label(frame_arama, text="", font=("Arial", 12, "bold"))
btn_refresh = tk.Button(frame_arama, text="Tüm Listeyi Gör", command=listeyi_yenile)
btn_refresh.pack(side="left", padx=10)
lbl_toplam_sonuc.pack(side="left", padx=20)

# 3. BÖLÜM: LİSTE (TREEVIEW)
columns = ("ID", "Tarih", "Danışan", "Terapist", "Bedel", "Alınan", "Kalan Borç", "Notlar")
tree = ttk.Treeview(root, columns=columns, show="headings")

for col in columns:
    tree.heading(col, text=col)
    tree.column(col, width=100)

tree.column("ID", width=30)
tree.column("Danışan", width=150)

# Renklendirme tag'i
tree.tag_configure('borclu', background='#ffcccc') # Borcu olanlar açık kırmızı

tree.pack(fill="both", expand=True, padx=10, pady=10)

# İlk açılışta listeyi doldur
listeyi_yenile()

root.mainloop()