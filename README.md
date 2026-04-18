# MechKeys

macOS menü çubuğunda çalışan Cherry MX Blue tarzı tuş sesleri. Sesler [Mechvibes](https://github.com/hainguyents13/mechvibes) açık kaynak paketinden türetilmiştir.

**GitHub’a ilk push** ve **Releases / zip / Gatekeeper**: [DISTRIBUTING.md](DISTRIBUTING.md) (bölüm 0 ve sonrası)

---

## Paylaşmak için seçenekler

### A) GitHub / zip ile kaynak

1. Bu klasörü zip’leyip veya bir Git deposuna itin.
2. Arkadaşın şu komutlarla kurar:

```bash
cd mechkeys
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
mechkeys-download-sounds
mechkeys
```

Alternatif çalıştırma (venv’siz, klasör kökündeyken):

```bash
pip install -r requirements.txt
python3 download_sounds.py
python3 run.py
```

veya:

```bash
python3 -m mechkeys
```

### B) `pip` ile kurulabilir paket (aynı makinede veya özel indeks)

Klasör kökünde:

```bash
pip install .
# veya geliştirme: pip install -e .
```

Ortaya çıkan komutlar:

| Komut | Açıklama |
|--------|----------|
| `mechkeys` | Uygulamayı başlatır |
| `mechkeys-download-sounds` | Mechvibes seslerini indirip WAV üretir |

`pip install` sonrası ses klasörü varsayılan olarak:

`~/Library/Application Support/MechKeys/sounds`

Özel klasör için: `export MECHKEYS_SOUND_DIR=/yol/istediğin/sounds`

Kaynak ağacında kök `sounds/` içinde zaten `.wav` varsa, geliştirme sırasında otomatik olarak o klasör kullanılır.

### C) Çift tıklanabilir `.app` (PyInstaller)

```bash
pip install pyinstaller
pyinstaller --windowed --name MechKeys --osx-bundle-identifier com.mechkeys.app \
  --collect-submodules pygame --hidden-import AppKit --hidden-import Foundation \
  --noconfirm run.py
```

Çıktı: `dist/MechKeys.app` — Finder’da açılabilir.

İlk seferde yine `mechkeys-download-sounds` çalıştırıp sesleri `Application Support` altına (veya `MECHKEYS_SOUND_DIR`) üretmek gerekir.

Not: PyInstaller paketi imzalamaz; başka Mac’te **Sağ tık → Aç** veya Gatekeeper ayarları gerekebilir.

**Eski `pip` ile düzenlenebilir kurulum** (`pip install -e .`) hata verirse: `pip install --upgrade pip setuptools` veya doğrudan `pip install .` kullan.

---

## Gereksinimler

- macOS
- Python 3.9+
- Bağımlılıklar: `rumps`, `pynput`, `pygame` (`pyproject.toml` veya `requirements.txt`)

---

## macOS izinleri

1. **Sistem Ayarları → Gizlilik ve Güvenlik → Erişilebilirlik**  
   Terminal, iTerm veya kullandığın Python / `MechKeys.app` için izin açık olmalı.
2. Bazı sürümlerde ayrıca **Giriş İzleme (Input Monitoring)** gerekir.

---

## Girişte otomatik başlatma (LaunchAgent)

`com.mechkeys.app.plist` içindeki `mechkeys` yolunu kendi makinede `which mechkeys` çıktısıyla değiştir; sonra:

```bash
cp com.mechkeys.app.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.mechkeys.app.plist
```

---

## Proje yapısı

```
mechkeys/                 # Python paketi
  __init__.py
  __main__.py             # python -m mechkeys
  app.py                  # Menü çubuğu uygulaması
  download_sounds.py      # Ses kurulumu
  paths.py                # Ses klasörü konumu
run.py                    # python3 run.py
download_sounds.py        # kök sarmalayıcı → paket
pyproject.toml            # pip / setuptools
setup.py                  # eski pip uyumluluğu
scripts/build_macos_release.sh  # .app + zip (ve isteğe DMG)
DISTRIBUTING.md           # GitHub Release, Gatekeeper, notarize
.github/workflows/       # Etiket itilince otomatik derleme
sounds/                   # WAV’lar (geliştirmede kökte olabilir)
LICENSE
```

---

## Sorun giderme

- **Ses yok:** `mechkeys-download-sounds` çalıştır; Erişilebilirlik / Giriş İzleme izinlerini kontrol et.
- **Import hatası:** Proje kökünden `pip install -e .` veya `PYTHONPATH=.` kullanma; mümkünse her zaman kurulum yap.

---

## Mac App Store’a koyabilir miyim?

**Kısa cevap:** Bu proje türüyle (tüm sistemde tuş dinleme + `pynput`) App Store’a girmek **fiilen çok zor ve çoğu senaryoda mümkün değil**.

**Neden:**

1. **App Sandbox zorunluluğu** — Mac App Store’a giren uygulamalar [App Sandbox](https://developer.apple.com/documentation/security/app_sandbox) ile sınırlandırılır. Tüm uygulamalarda tuş vuruşlarını dinlemek, sandbox’ın tipik izin modeliyle çakışır; “giriş izleme” benzeri yetenekler için özel entitlement gerekir ve Apple [İnceleme Kuralları](https://developer.apple.com/app-store/review/guidelines/) kapsamında bu tür uygulamaları **reddetme veya ek süreç** ile değerlendirme eğilimindedir (özellikle klavye genel dinleme / güvenlik algısı).
2. **Teknik yığın** — Python + PyInstaller/rumps ile üretilen `.app`’i Store’a vermek için yine de **Xcode arşivi**, **kod imzalama**, **App Store provisioning**, metadata ve inceleme süreci gerekir; sandbox’a uymayan davranış varsa süreç biter.

**Pratik alternatif (çoğu benzer uygulamanın yaptığı):**

- [Apple Developer Program](https://developer.apple.com/programs/) ($/yıl) ile **Developer ID** imzalama + [notarization](https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution)  
- Dağıtım: **kendi siten**, [GitHub Releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases), Setapp vb. — kullanıcı **Sağ tık → Aç** veya Güvenlik ayarlarıyla ilk açılışı onaylar.

App Store’a özellikle girmek istiyorsan: davranışı sandbox kurallarına uyacak şekilde **yeniden tasarlamak** (ör. yalnızca kendi pencerende tuş, veya Apple’ın izin verdiği resmi API’lerle sınırlı kullanım) ve büyük olasılıkla **Swift/Objective-C + AppKit** ile native uygulama gerekir; mevcut MechKeys mimarisi doğrudan “Store’a yükle” ile uyumlu değildir.

---

## Lisans

MIT — ayrıntı `LICENSE` dosyasında. Ses içeriği Mechvibes projesine dayanır; uygulama içi footer’da da belirtilir.
