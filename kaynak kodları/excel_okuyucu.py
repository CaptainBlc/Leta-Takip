import pandas as pd
import sys

dosyalar = [
    'SEANS ÜCRET TAKİP.xlsx',
    'LETA SEANS.xlsx',
    'PERVİN HOCA HAFTALIK.xlsx',
    'Yapılacaklar Listesi.xlsx'
]

for dosya in dosyalar:
    try:
        print(f"\n{'='*80}")
        print(f"DOSYA: {dosya}")
        print('='*80)
        
        df = pd.read_excel(dosya)
        
        print(f"\nSütunlar: {df.columns.tolist()}")
        print(f"Satır sayısı: {len(df)}")
        print(f"\nİlk 15 satır:")
        print(df.head(15).to_string())
        
        # Her sütunun veri tiplerini göster
        print(f"\nVeri tipleri:")
        print(df.dtypes)
        
        # Boş değerleri kontrol et
        print(f"\nBoş değerler:")
        print(df.isnull().sum())
        
    except Exception as e:
        print(f"\nHATA: {dosya} okunamadı - {e}")

print("\n" + "="*80)
print("ANALİZ TAMAMLANDI")
print("="*80)

