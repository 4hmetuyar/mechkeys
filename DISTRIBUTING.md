# Dağıtım rehberi (GitHub Releases, zip/DMG, Gatekeeper)

Bu belge, MechKeys’i **App Store olmadan** paylaşmak için pratik adımları özetler: derleme, arşiv, GitHub Release ve kullanıcıların Gatekeeper ile ilk açılışı.

---

## 0. Projeyi GitHub’a ilk kez gönderme

Bu klasörde `git init` ve ilk commit hazır olabilir. Kalan adımlar:

### A) GitHub web arayüzü

1. [github.com/new](https://github.com/new) → Repository adı (ör. `mechkeys`) → **Public** → README / .gitignore **ekleme** (boş depo).
2. Aşağıdaki komutlarda `KULLANICI` ve `REPO` değerlerini kendi hesabınla değiştir:

```bash
cd /path/to/mechkeys
git remote add origin https://github.com/KULLANICI/REPO.git
git branch -M main
git push -u origin main
```

SSH kullanıyorsan: `git@github.com:KULLANICI/REPO.git`

### B) GitHub CLI (`gh`)

```bash
gh auth login
cd /path/to/mechkeys
gh repo create mechkeys --public --source=. --remote=origin --push
```

İsim çakışırsa `--public` yanına farklı bir depo adı ver.

---

## 1. Ne üreteceksin?

| Çıktı | Açıklama |
|--------|-----------|
| `dist/MechKeys.app` | macOS uygulama paketi |
| `dist/MechKeys-macos-*.dmg` | **Tek indirilebilir dosya** (diğer Mac uygulamalarındaki gibi) |
| `dist/MechKeys-macos-*.zip` | Aynı `.app`’in sıkıştırılmış hâli (alternatif) |

Ses dosyaları: Derleme sırasında kökte `sounds/*.wav` varsa PyInstaller bunları `.app` içine gömer. Yoksa kullanıcı ilk açılışta terminalden `mechkeys-download-sounds` çalıştıramaz (paket dışında); bu durumda uygulama sesleri `~/Library/Application Support/MechKeys/sounds` altına indirmek için **kaynak kurulum** veya elle kopyalama gerekir. **Release öncesi** `python3 download_sounds.py` çalıştırıp tekrar derlemen önerilir.

---

## 2. Yerelde derleme

```bash
cd /path/to/mechkeys
chmod +x scripts/build_macos_release.sh
./scripts/build_macos_release.sh
```

DMG üretmek istemezsen:

```bash
SKIP_DMG=1 ./scripts/build_macos_release.sh
```

Çıktı: `dist/` altında `MechKeys.app`, `MechKeys-macos-*.zip` ve (varsayılan) **`MechKeys-macos-*.dmg`**. `SKIP_DMG=1` ise yalnızca zip üretilir.

---

## 3. GitHub Releases (otomatik)

1. Depoyu GitHub’a gönder.
2. Sürüm numarasını `mechkeys/__init__.py` ve `pyproject.toml` / `setup.py` ile hizala (isteğe bağlı ama iyi pratik).
3. Etiket oluştur ve it:

```bash
git tag v1.0.0
git push origin v1.0.0
```

4. `.github/workflows/release-macos.yml` tetiklenir; işlem bitince **Releases** sayfasında `v1.0.0` altında **`.zip`** ve **`.dmg`** dosyaları görünür.

**Not:** İlk kez kullanıyorsan `Settings → Actions → General` altında iş akışı yazma izninin açık olduğundan emin ol.

---

## 4. GitHub’da elle Release

1. **Releases → Draft a new release**
2. **Choose a tag** ile `v1.0.0` oluştur
3. Yerelde ürettiğin `MechKeys-macos-*.dmg` ve/veya `*.zip` dosyalarını **Attach binaries** ile yükle
4. Kısa sürüm notu yaz (ör. “İlk sürüm, macOS 13+”)

---

## 5. Son kullanıcı: Gatekeeper (imzasız veya “bilinmeyen geliştirici”)

Apple, internetten indirilen uygulamaları varsayılan olarak kısıtlar. **İmzasız** veya senin Developer ID’n dışındaki bir zip için kullanıcıya şunu yaz:

1. Zip’i aç, `MechKeys.app`’i **Uygulamalar** klasörüne sürükle (veya istediği yere).
2. **İlk çalıştırma:** `MechKeys.app`’e **Sağ tık (veya Control+tık) → Aç** → iletişim kutusunda yine **Aç**.
3. **Sistem Ayarları → Gizlilik ve Güvenlik → Erişilebilirlik** (ve gerekirse **Giriş İzleme**) içinde MechKeys’i etkinleştir.

“Çift tıklayınca açılmıyor” şikayetlerinde neredeyse her zaman **Sağ tık → Aç** çözümüdür.

---

## 6. Developer ID + notarization (isteğe bağlı, daha az uyarı)

Kendi sitende veya GitHub’da **daha az kırmızı uyarı** için:

1. [Apple Developer Program](https://developer.apple.com/programs/) üyeliği
2. Xcode veya `codesign` ile **Developer ID Application** sertifikasıyla `.app` imzalama
3. `xcrun notarytool` ile [notarization](https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution)
4. `xcrun stapler staple` ile staple

Bu adımlar Apple hesabına ve sertifika yönetimine bağlıdır; depoda gizli anahtar saklanmamalıdır. CI’da notarize etmek için GitHub Secrets ile `.p12` veya özel anahtar akışı kurulur (ayrı bir rehber konusu).

---

## 7. Kendi sitende barındırma

- Zip veya DMG’yi CDN / statik hosting / S3 benzeri bir yere koy.
- İndirme linki + aynı Gatekeeper + Erişilebilirlik maddelerini sayfada kısa tekrar et.
- İstersen SHA256 özeti ver: `shasum -a 256 dist/MechKeys-macos-arm64.zip`

---

## Özet

| Yol | Zorluk | Kullanıcı deneyimi |
|-----|--------|---------------------|
| Zip + GitHub Release | Düşük | Sağ tık → Aç gerekir |
| Developer ID + notarize | Orta | Daha az uyarı |
| Mac App Store | Bu proje için uygun değil | README “Mac App Store” bölümü |

Sorularını issue olarak açabilirsin; derleme betiği `scripts/build_macos_release.sh` içinde.
