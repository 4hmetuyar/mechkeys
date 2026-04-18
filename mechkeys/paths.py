"""Ses dosyaları klasörü: geliştirme, PyInstaller, pip kurulumu."""

import os
import sys


def _darwin_app_support_sounds():
    p = os.path.join(
        os.path.expanduser("~"),
        "Library",
        "Application Support",
        "MechKeys",
        "sounds",
    )
    os.makedirs(p, exist_ok=True)
    return p


def get_sound_dir():
    """
    Öncelik:
    1. MECHKEYS_SOUND_DIR ortam değişkeni
    2. PyInstaller (.app): paket içi sounds/ (varsa)
    3. Repo kökündeki sounds/ (mevcut WAV varsa; geliştirme)
    4. site-packages kurulumu: Application Support (macOS)
    5. Paket yanında mechkeys/sounds/

    Birden fazla ses seti: bu kökün altına alt klasör koyup her birine .wav
    ekleyebilirsin; kökte doğrudan duran .wav'lar «Ana klasör» seti olur.
    """
    override = os.environ.get("MECHKEYS_SOUND_DIR")
    if override:
        os.makedirs(override, exist_ok=True)
        return override

    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        bundled = os.path.join(sys._MEIPASS, "sounds")
        try:
            if os.path.isdir(bundled) and any(
                n.lower().endswith(".wav") for n in os.listdir(bundled)
            ):
                return bundled
        except OSError:
            pass
        if sys.platform == "darwin":
            return _darwin_app_support_sounds()
        fb = os.path.join(sys._MEIPASS, "sounds")
        os.makedirs(fb, exist_ok=True)
        return fb

    here = os.path.dirname(os.path.abspath(__file__))
    installed = "site-packages" in here or "dist-packages" in here

    if not installed:
        parent = os.path.dirname(here)
        legacy = os.path.join(parent, "sounds")
        try:
            if os.path.isdir(legacy) and any(
                n.lower().endswith(".wav") for n in os.listdir(legacy)
            ):
                return legacy
        except OSError:
            pass

    if installed:
        if sys.platform == "darwin":
            return _darwin_app_support_sounds()
        p = os.path.join(here, "sounds")
        os.makedirs(p, exist_ok=True)
        return p

    p = os.path.join(here, "sounds")
    os.makedirs(p, exist_ok=True)
    return p
