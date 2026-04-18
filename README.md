# MechKeys

macOS menü çubuğunda çalışan, tuş basışlarında **Cherry MX Blue** tarzı ses çalan küçük uygulama. Ses örnekleri [Mechvibes](https://github.com/hainguyents13/mechvibes) açık kaynak paketinden üretilir.

| | |
|---|---|
| **Depo** | [github.com/4hmetuyar/mechkeys](https://github.com/4hmetuyar/mechkeys) |
| **Hazır sürüm** | [Releases](https://github.com/4hmetuyar/mechkeys/releases) (`.dmg` / `.zip`) |
| **Dağıtım / CI / Gatekeeper** | [DISTRIBUTING.md](DISTRIBUTING.md) |
| **Lisans** | MIT — `LICENSE` · ses kaynağı uygulama içi footer’da |

---

## Geliştiriciler için

Bu bölüm dışarıdan klonlayıp katkı verecek veya yerelde çalıştıracak kişiler içindir.

### Gereksinimler

- **macOS** (menü çubuğu + `rumps` / `AppKit`)
- **Python 3.9+**
- Bağımlılıklar: `rumps`, `pynput`, `pygame` — sürümler `pyproject.toml` ve `requirements.txt` içinde

### Hızlı başlangıç

```bash
git clone https://github.com/4hmetuyar/mechkeys.git
cd mechkeys

python3 -m venv .venv
source .venv/bin/activate          # Windows değil; macOS/Linux: source

pip install --upgrade pip setuptools wheel
pip install -e .

# Ses WAV’ları (Mechvibes GitHub → yerel sounds/ veya Application Support)
python3 download_sounds.py

# Uygulamayı çalıştır
python3 run.py
# veya: python3 -m mechkeys
# veya (kurulum sonrası): mechkeys
```

**Uygulama içi:** Menüde kaç ses yüklendiği; **Ses seti** alt menüsünden klasör/paket seçimi (tercih kaydedilir); **Erişilebilirlik** / **Giriş izleme** için Sistem Ayarları kısayolu; **Sesleri yeniden yükle**; ses seviyesi **UserDefaults** ile hatırlanır; tuş **tekrarında debounce** (basılı tutunca makineli tık azalır); menü çubuğu ikonunda **tooltip**.

**Not:** `mechkeys-download-sounds` varsayılan olarak Blue / Brown / Red paketlerini ses kökünün **alt klasörlerine** indirir; elle de `sounds/<set_adı>/*.wav` düzeni kullanabilirsin. Kökte `sounds/*.wav` yoksa indirme dener; başarısız olursa [DISTRIBUTING.md](DISTRIBUTING.md) içindeki ağ / ffmpeg notlarına bak.

### Yerel çalıştırma seçenekleri

| Yöntem | Komut |
|--------|--------|
| Kök giriş | `python3 run.py` |
| Paket modülü | `python3 -m mechkeys` |
| `pip install -e .` sonrası | `mechkeys` |
| Ses kurulumu CLI | `mechkeys-download-sounds` veya `python3 download_sounds.py` |

### Ortam değişkeni

| Değişken | Anlamı |
|----------|--------|
| `MECHKEYS_SOUND_DIR` | WAV klasörünü zorla (mutlak yol). Yoksa: önce kök `sounds/`, PyInstaller paketinde gömülü `sounds/`, pip kurulumunda `~/Library/Application Support/MechKeys/sounds` — ayrıntı `mechkeys/paths.py`. |
| `MECHKEYS_ALLOW_SYNTH` | `1` ise `download_sounds.py` gerçek paket başarısız olunca sentetik tık üretir (varsayılan kapalı). |

### macOS izinleri (geliştirme)

Tuş dinlemek için **Erişilebilirlik** (ve bazı sürümlerde **Giriş İzleme / Input Monitoring**) içinde **Terminal**, **iTerm** veya çalıştırdığın **Python / PyInstaller `.app`** işaretlenmeli. Aksi halde ses veya dinleyici çalışmaz.

### Dağıtım özeti

| Ne | Nasıl |
|----|--------|
| `.app` + `.zip` + `.dmg` | `./scripts/build_macos_release.sh` — ayrıntı [DISTRIBUTING.md](DISTRIBUTING.md) |
| GitHub Release otomatik | `git tag v1.0.0 && git push origin v1.0.0` → Actions (depoda **Workflow permissions: Read and write** açık olmalı) |
| Depoyu güncelleme | `git pull origin main` |

PyInstaller tek satır örneği ve imzalama / notarize tam metni **DISTRIBUTING.md** içinde.

### Proje yapısı

```
mechkeys/                    # Python paketi
  __init__.py                # sürüm
  __main__.py                # python -m mechkeys
  app.py                     # rumps menü + pygame + pynput
  download_sounds.py         # Mechvibes OGG → WAV
  paths.py                   # ses klasörü çözümü (dev / pip / PyInstaller)
run.py                       # kök giriş noktası
download_sounds.py           # kök → paket içi script
scripts/build_macos_release.sh
pyproject.toml
setup.py
requirements.txt
.github/workflows/release-macos.yml
com.mechkeys.app.plist       # LaunchAgent örneği (yol: which mechkeys)
sounds/                      # geliştirmede WAV (commit’lenebilir veya .gitignore ile hariç)
LICENSE
DISTRIBUTING.md
```

### Sorun giderme (kısa)

| Sorun | Kontrol |
|-------|---------|
| Ses yok | `sounds/` içinde `.wav` var mı? `python3 download_sounds.py` · Erişilebilirlik / Giriş İzleme |
| `import mechkeys` hatası | Kökte `mechkeys.py` dosyası **yok**; paket klasörü `mechkeys/`. Her zaman repo kökünden çalış veya `pip install -e .` |
| `pip install -e .` hata | `pip install --upgrade pip setuptools` sonra `pip install .` dene |
| PyInstaller | `scripts/build_macos_release.sh` önerilir; sesler için kök `sounds/*.wav` veya gömülü data |

---

## Son kullanıcı (derlenmiş uygulama)

1. **[Releases](https://github.com/4hmetuyar/mechkeys/releases)** → **`MechKeys-macos-*.dmg`** (tercih) veya **`.zip`** indir.  
2. DMG: aç → `MechKeys.app` → **Uygulamalar**’a sürükle.  
3. İlk açılış: **Sağ tık → Aç** (Gatekeeper).  
4. **Erişilebilirlik** (ve gerekirse **Giriş İzleme**) izni ver.

**Code → Download ZIP** yalnızca kaynak koddur; çalışan paket için **Releases** gerekir. Tek indirilebilir dosya için **`.dmg`** kullanılır (Windows `.exe` eşdeğeri değildir; macOS’ta `.app` + dağıtım için `.dmg` standarttır).

**Sadece pip ile kurulum:** `pip3 install "git+https://github.com/4hmetuyar/mechkeys.git"` → `mechkeys-download-sounds` → `mechkeys`

---

## Girişte otomatik başlatma

`com.mechkeys.app.plist` içindeki `ProgramArguments` yolunu `which mechkeys` ile güncelle; sonra:

```bash
cp com.mechkeys.app.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.mechkeys.app.plist
```

---

## Mac App Store

Bu mimari (global tuş dinleme, `pynput`) **App Store sandbox** ile genelde uyumlu değildir; dağıtım **Developer ID + notarize** veya **Releases / kendi siten** ile yapılır. Kısa gerekçe: [App Sandbox](https://developer.apple.com/documentation/security/app_sandbox), [Review Guidelines](https://developer.apple.com/app-store/review/guidelines/).

---

## Lisans

MIT — `LICENSE`. Ses içeriği Mechvibes kaynaklıdır.
