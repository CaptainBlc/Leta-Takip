# Seans Ücreti Otomatik Mantığı ve Modül Eşleşme Rehberi

Bu dosya, seans ücretlerinin otomatik belirlenmesi, hangi modüllerin (tabloların) nasıl eşleştiği ve veri aktarımında boşluk/tekrar kaynaklı sorunların nasıl önlendiğini açıklar.

---

## 1. Seans Ücreti Otomatik Mantığı (Hangi Sırayla Nereden Alınır?)

### 1.1 Yeni seans kaydında (sıfır ücret girilmişse)

1. **`seans_kayit()`** içinde `hizmet_bedeli == 0` ise otomatik ücret aranır.
2. **`get_ogrenci_personel_ucreti(ogrenci_id, personel_adi, conn)`** çağrılır; sıra:
   - **Önce:** `ogrenci_personel_fiyatlandirma` tablosu  
     `(ogrenci_id, personel_adi, aktif=1, bitis_tarihi uygun)` → `seans_ucreti`
   - **Sonra:** `cocuk_personel_atama` tablosu  
     `(cocuk_id, personel_adi, aktif=1)` → `seans_ucreti`
3. Bulunan ücret `hizmet_bedeli` olarak kullanılır; yoksa 0 kalır.

### 1.2 Akıllı varsayılanlar (Smart Defaults – form otomatik doldurma)

Kullanıcı danışan + terapist seçtiğinde **`get_smart_defaults(danisan_adi, terapist, tarih, saat)`** çağrılır:

- **Fiyat:** `get_price_for_danisan_terapist(danisan_adi, terapist)`:
  1. **Önce:** `pricing_policy`  
     `(student_id = danışan id, teacher_name = terapist)` → `price`
  2. **Sonra:** `get_ogrenci_personel_ucreti()` (yukarıdaki gibi `ogrenci_personel_fiyatlandirma` → `cocuk_personel_atama`)
- **Oda:** `get_oda_for_terapist_saat(terapist, tarih, saat)`:
  1. **Önce:** `haftalik_seans_programi` (personel + hafta + gün + saat) → `oda_adi`
  2. **Sonra:** `seans_takvimi` (son seansın odası)

### 1.3 Personel ücreti (hoca payı)

**`hesapla_personel_ucreti(personel_adi, seans_ucreti)`** sabit kurallara göre:

- **Pervin Hoca:** %100 (seans ücreti = personel ücreti)
- **Arif Hoca:** Sabit 2500 TL
- **Diğerleri:** %40

Bu kurallar `PERSONEL_UCRET_KURALLARI` sözlüğünden okunur; personel adı **tam eşleşme** (boşluksuz/normalize) ile aranır.

---

## 2. Modüller Arası Eşleşme (Hangi Alanlar Birbirine Bağlı?)

| Kaynak / Amaç        | Alan(lar)        | Eşleşme kuralı |
|----------------------|------------------|-----------------|
| Danışan → ID         | `danisanlar.ad_soyad` ↔ `records.danisan_adi`, `seans_takvimi.danisan_adi` | **UPPER + TRIM** ile karşılaştırma; kayıtta **danisan_adi** tutarlılık için **strip + UPPER** saklanır |
| Terapist / personel   | `personel_adi`, `terapist`, `teacher_name` (farklı tablolarda) | **TRIM** (baş/son boşluk yok); aynı yazım (örn. "Pervin Hoca") |
| Öğrenci–personel ücret| `ogrenci_personel_fiyatlandirma.ogrenci_id` + `personel_adi` | `danisanlar.id` = `ogrenci_id`; personel **strip** ile |
| Fiyat (pricing)      | `pricing_policy.student_id` + `teacher_name` | `danisanlar.id` = `student_id`; **teacher_name TRIM** ile eşleşir |

### 2.1 Sık görülen eşleşme problemleri

- **Danışan adı:** Biri "AHMET YILMAZ", diğeri "Ahmet Yilmaz" yazılırsa JOIN’ler `UPPER()` ile çalışır ama listede “aynı kişi iki kez” gibi görünebilir. Çözüm: danışan adını **kaydederken hep aynı formatta** (örn. UPPER) yazmak.
- **Terapist / personel adı:** "Pervin Hoca" ile "Pervin Hoca " (sonda boşluk) farklı sayılır; fiyat/oda eşleşmez. Çözüm: tüm okuma/yazmalarda **strip** ve mümkünse sorgularda **TRIM(alan)** kullanmak.
- **Haftalık program:** `haftalik_seans_programi.personel_adi` ile `seans_takvimi.terapist` aynı kişiyi göstermeli; yine **strip** ve tutarlı yazım gerekir.

---

## 3. Veri Aktarımında Boşluk ve Tekrar Sorunları

### 3.1 Boşluk (whitespace)

- **İçe aktarmada (Excel vb.):** Tüm metin alanları **strip()** ile okunur; danışan adı **UPPER** (danisanlar ile uyum için), terapist/personel **strip** (eşleşme için).
- **Kayıt yazarken:** `seans_kayit` ve ilgili yerlerde **danisan_adi** ve **terapist** kayda geçmeden önce normalize edilir (strip, danisan_adi için UPPER).

### 3.2 Tekrar (duplicate)

- **Seans Ücret Takip import:** Aynı (tarih, danisan_adi, terapist) için zaten kayıt varsa **atlanır** (tekrar eklenmez).
- **Danışanlar import:** `UPPER(ad_soyad)` ile var mı diye bakılır; varsa tekrar eklenmez.

Bu kurallar, “modüllerin seans ücretlerinin otomatik mantıkları” ve “bazı modüllerin eşleşme problemleri” ile “verilerdeki boşluklardan kaynaklanan aktarım problemleri”ni azaltmak için uygulanır.
