#!/usr/bin/env python3
"""
Cherry MX Blue ses dosyalarını Mechvibes açık kaynak paketinden indirir.

Gerçek mekanik sesler: GitHub’daki Mechvibes ``sound.ogg`` + ``config.json``
tanımlarından pygame ile PCM dilimleri üretilir (ffmpeg gerekmez).
"""

import urllib.request
import os
import json
import shutil
import subprocess
import zipfile
import tempfile
import math
import random
import struct
import wave

from mechkeys.paths import get_sound_dir

SOUND_DIR = get_sound_dir()

PACK_URL = "https://github.com/hainguyents13/mechvibes/raw/master/public/audio/cherry-mx-blue.zip"

# Mechvibes: CherryMX Blue ABS (kayıtlı gerçek tuş sesleri, tek OGG içinde)
MECHVIBES_BLUE_ABS_BASE = (
    "https://raw.githubusercontent.com/hainguyents13/mechvibes/main/src/audio/cherrymx-blue-abs"
)
ASK_SYNTH = os.environ.get("MECHKEYS_ALLOW_SYNTH", "").lower() in ("1", "true", "yes")


def _write_click_wav(path, freq, duration, sample_rate=44100, seed=None):
    """Pygame/numpy olmadan kısa mekanik tık benzeri mono WAV yazar."""
    rng = random.Random(seed)
    n = max(1, int(sample_rate * duration))
    frames = bytearray()
    amp = 0.42
    for i in range(n):
        t = i / sample_rate
        click = math.sin(2 * math.pi * freq * t)
        noise = rng.uniform(-1.0, 1.0) * 0.12
        env = math.exp(-t * 55.0)
        s = (click * 0.72 + noise) * env * amp
        s = max(-1.0, min(1.0, s))
        frames.extend(struct.pack("<h", int(s * 32767)))
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(frames))


def generate_fallback_wav_pack(sound_dir, count=8):
    """İnternet/sox yokken kullanılacak küçük tık sesleri (click_1.wav …)."""
    os.makedirs(sound_dir, exist_ok=True)
    rng = random.Random(42)
    base = [
        (780, 0.052),
        (800, 0.048),
        (820, 0.05),
        (760, 0.055),
        (840, 0.045),
        (795, 0.05),
        (815, 0.047),
        (770, 0.053),
    ]
    made = 0
    for idx in range(min(count, len(base))):
        freq, dur = base[idx]
        freq += rng.randint(-12, 12)
        dur *= rng.uniform(0.94, 1.06)
        path = os.path.join(sound_dir, f"click_{idx + 1}.wav")
        _write_click_wav(path, freq, dur, seed=1000 + idx)
        print(f"  ✅ {os.path.basename(path)} oluşturuldu")
        made += 1
    return made


def generate_sounds_with_sox(sound_dir):
    """macOS'ta mevcut sox ile ses üretir."""
    import subprocess
    
    os.makedirs(sound_dir, exist_ok=True)
    
    # 5 farklı varyasyon (pitch farklılıkları ile daha doğal hissettirmek için)
    variants = [
        (800, 0.05, "click_1.wav"),
        (850, 0.045, "click_2.wav"),
        (780, 0.055, "click_3.wav"),
        (820, 0.048, "click_4.wav"),
        (760, 0.052, "click_5.wav"),
    ]
    
    generated = 0
    for freq, dur, name in variants:
        out_path = os.path.join(sound_dir, name)
        try:
            # sox ile kısa tık sesi oluştur
            cmd = [
                "sox", "-n", "-r", "44100", "-c", "2", out_path,
                "synth", str(dur), "sine", str(freq),
                "fade", "l", "0", str(dur), str(dur * 0.8),
                "vol", "0.9"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"  ✅ {name} oluşturuldu")
                generated += 1
            else:
                print(f"  ⚠️  {name} oluşturulamadı: {result.stderr.strip()}")
        except FileNotFoundError:
            print("  ⚠️  sox bulunamadı.")
            return 0
    
    return generated


def _slice_ogg_with_ffmpeg(ogg_path, sound_dir, segments, sample_rate=44100):
    """Pygame OGG yükleyemezse ffmpeg ile WAV dilimleri üretir."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return 0
    os.makedirs(sound_dir, exist_ok=True)
    made = 0
    for idx, (off_ms, dur_ms) in enumerate(segments, start=1):
        out = os.path.join(sound_dir, f"mxblue_{idx:03d}.wav")
        off_s = off_ms / 1000.0
        dur_s = dur_ms / 1000.0
        cmd = [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            ogg_path,
            "-ss",
            f"{off_s:.6f}",
            "-t",
            f"{dur_s:.6f}",
            "-acodec",
            "pcm_s16le",
            "-ar",
            str(sample_rate),
            "-ac",
            "2",
            out,
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"  ⚠️  ffmpeg dilim {idx}: {r.stderr.strip() or r.stdout.strip()}")
            continue
        print(f"  ✅ {os.path.basename(out)}")
        made += 1
    return made


def _clear_old_synthetic_clicks(sound_dir):
    """Önceki sentetik click_*.wav dosyalarını siler (gerçek paketle karışmasın)."""
    try:
        for name in os.listdir(sound_dir):
            if name.startswith("click_") and name.endswith(".wav"):
                os.remove(os.path.join(sound_dir, name))
    except OSError:
        pass


def download_mechvibes_cherrymx_blue_slices(sound_dir):
    """Mechvibes cherrymx-blue-abs: sound.ogg içinden gerçek tuş seslerini WAV yapar."""
    cfg_url = f"{MECHVIBES_BLUE_ABS_BASE}/config.json"
    ogg_url = f"{MECHVIBES_BLUE_ABS_BASE}/sound.ogg"

    print("📥 Mechvibes Cherry MX Blue (ABS) gerçek ses paketi indiriliyor…")
    tmp = tempfile.mkdtemp(prefix="mechkeys_dl_")
    ogg_path = os.path.join(tmp, "sound.ogg")
    cfg_path = os.path.join(tmp, "config.json")
    try:
        urllib.request.urlretrieve(cfg_url, cfg_path)
        urllib.request.urlretrieve(ogg_url, ogg_path)
    except Exception as e:
        print(f"  ⚠️  İndirme başarısız: {e}")
        shutil.rmtree(tmp, ignore_errors=True)
        return False

    try:
        with open(cfg_path, encoding="utf-8") as f:
            cfg = json.load(f)
        defines = cfg.get("defines") or {}
    except Exception as e:
        print(f"  ⚠️  config.json okunamadı: {e}")
        shutil.rmtree(tmp, ignore_errors=True)
        return False

    seen = set()
    segments = []
    for v in defines.values():
        if isinstance(v, (list, tuple)) and len(v) >= 2:
            off, dur = int(v[0]), int(v[1])
            if dur <= 0:
                continue
            key = (off, dur)
            if key not in seen:
                seen.add(key)
                segments.append(key)
    segments.sort()

    if not segments:
        print("  ⚠️  config içinde geçerli ses dilimi yok.")
        shutil.rmtree(tmp, ignore_errors=True)
        return False

    sr = 44100
    channels = 2
    sample_width = 2
    frame_bytes = channels * sample_width

    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    import pygame

    raw = None
    pygame.mixer.quit()
    pygame.mixer.pre_init(sr, -16, channels, 512)
    try:
        pygame.mixer.init()
        snd = pygame.mixer.Sound(ogg_path)
        raw = pygame.mixer.Sound.get_raw(snd)
    except Exception as e:
        print(f"  ⚠️  pygame ile OGG okunamadı: {e}")
    finally:
        pygame.mixer.quit()

    os.makedirs(sound_dir, exist_ok=True)
    made = 0

    if raw is not None:
        for idx, (off_ms, dur_ms) in enumerate(segments, start=1):
            start_frame = int(off_ms / 1000.0 * sr)
            n_frames = int(dur_ms / 1000.0 * sr)
            start_byte = start_frame * frame_bytes
            n_bytes = n_frames * frame_bytes
            chunk = raw[start_byte : start_byte + n_bytes]
            if len(chunk) < n_bytes:
                chunk = chunk + b"\x00" * (n_bytes - len(chunk))
            out_path = os.path.join(sound_dir, f"mxblue_{idx:03d}.wav")
            with wave.open(out_path, "w") as wf:
                wf.setnchannels(channels)
                wf.setsampwidth(sample_width)
                wf.setframerate(sr)
                wf.writeframes(chunk)
            print(f"  ✅ {os.path.basename(out_path)}")
            made += 1
    else:
        made = _slice_ogg_with_ffmpeg(ogg_path, sound_dir, segments, sr)

    shutil.rmtree(tmp, ignore_errors=True)

    if made <= 0:
        print("  ⚠️  Hiç WAV üretilemedi (pygame/ffmpeg).")
        return False

    _clear_old_synthetic_clicks(sound_dir)
    print(f"  ℹ️  {made} benzersiz gerçek tuş vuruşu WAV olarak kaydedildi.")
    return True


def download_mechvibes_pack(sound_dir):
    """Mechvibes ses paketini indirir."""
    zip_path = "/tmp/cherry-mx-blue.zip"
    
    print("📥 Cherry MX Blue ses paketi indiriliyor...")
    try:
        urllib.request.urlretrieve(PACK_URL, zip_path)
        
        with zipfile.ZipFile(zip_path, 'r') as zf:
            os.makedirs(sound_dir, exist_ok=True)
            for name in zf.namelist():
                if name.endswith(".wav") or name.endswith(".ogg"):
                    zf.extract(name, sound_dir)
                    print(f"  ✅ {os.path.basename(name)} çıkartıldı")
        
        os.remove(zip_path)
        return True
    except Exception as e:
        print(f"  ⚠️  İndirme başarısız: {e}")
        return False


def main():
    os.makedirs(SOUND_DIR, exist_ok=True)
    
    print("🎵 MechKeys - Ses Dosyası Kurulumu")
    print("=" * 40)
    
    # 1. Gerçek Mechvibes Cherry MX Blue (GitHub OGG + config dilimleri)
    if download_mechvibes_cherrymx_blue_slices(SOUND_DIR):
        print(f"\n✅ Gerçek mekanik klavye sesleri hazır: {SOUND_DIR}")
        return

    # 2. Eski zip (çoğu ortamda 404)
    if download_mechvibes_pack(SOUND_DIR):
        print("\n✅ Ses paketi başarıyla indirildi!")
        return

    # 3. Sentetik tıklar yalnızca istenirse (gerçek ses değil)
    if ASK_SYNTH:
        print("\n🔧 MECHKEYS_ALLOW_SYNTH=1 → yerleşik sentetik tıklar üretiliyor…")
        n = generate_fallback_wav_pack(SOUND_DIR)
        if n > 0:
            print(f"\n✅ {n} ses dosyası oluşturuldu: {SOUND_DIR}")
            return

    print("\n📋 Gerçek sesler için:")
    print("   • İnternet bağlantısı ve pygame kurulu olmalı (requirements.txt).")
    print("   • pygame OGG okuyamazsa: brew install ffmpeg sonra bu script’i tekrar çalıştır.")
    print(f"   • WAV’ları elle eklemek için klasör: {SOUND_DIR}")
    print("   • https://mechvibes.com — Cherry MX Blue paketleri")


if __name__ == "__main__":
    main()
