#!/usr/bin/env python3
"""
MechKeys - Cherry MX Blue mechanical keyboard sound simulator
macOS Menubar App
"""

import hashlib
import os
import subprocess
import threading
import time

import pygame
import rumps
from pynput import keyboard
from pynput.keyboard import Key, KeyCode

from mechkeys.paths import get_sound_dir

SOUND_DIR = get_sound_dir()

ROOT_PACK_ID = "__root__"
UD_VOLUME_PERCENT = "MechKeysVolumePercent"
UD_SELECTED_PACK = "MechKeysSelectedPack"
KEY_DEBOUNCE_SEC = 0.042

# NSControlStateValue — menüdeki tik işareti
try:
    from AppKit import NSControlStateValueOn, NSControlStateValueOff
except ImportError:
    NSControlStateValueOn = 1
    NSControlStateValueOff = 0


class MechKeysApp(rumps.App):
    def __init__(self):
        super().__init__("MechKeys", title="⌨️", quit_button=None, template=None)

        self.enabled = True
        self.volume = self._load_saved_volume()
        self.sounds = []
        self.pack_defs = self._discover_pack_defs()
        self.selected_pack_id = self._resolve_selected_pack_id(self.pack_defs)
        self.listener = None
        self._last_key_time = {}
        self._debounce_lock = threading.Lock()

        self.brand_item = rumps.MenuItem("MechKeys", callback=None)
        self.tagline_item = rumps.MenuItem("Kayıtlı tuş sesleri · Mechvibes", callback=None)
        self.toggle_item = rumps.MenuItem("Tuş sesleri", callback=self.toggle)
        self.toggle_item.state = NSControlStateValueOn

        self.status_item = rumps.MenuItem(self._status_menu_title(0), callback=None)

        self.vol_readout = rumps.MenuItem(self._volume_readout_title(), callback=None)
        self.vol_slider = rumps.SliderMenuItem(
            value=self.volume * 100.0,
            min_value=0.0,
            max_value=100.0,
            dimensions=(260, 28),
            callback=self._on_volume_slider,
        )
        self._polish_slider()

        self.open_access_item = rumps.MenuItem("Erişilebilirlik ayarları…", callback=self._open_accessibility_settings)
        self.open_listen_item = rumps.MenuItem("Giriş izleme ayarları…", callback=self._open_input_monitoring_settings)
        self.reload_sounds_item = rumps.MenuItem("Sesleri yeniden yükle", callback=self._reload_sounds_menu)

        self.footer_item = rumps.MenuItem("Kaynak: Mechvibes · MIT", callback=None)

        self.pack_submenu_item = rumps.MenuItem("Ses seti")
        self._pack_choice_rows = []

        self.menu = [
            self.brand_item,
            self.tagline_item,
            None,
            self.toggle_item,
            self.status_item,
            self.pack_submenu_item,
            None,
            self.vol_readout,
            self.vol_slider,
            None,
            self.open_access_item,
            self.open_listen_item,
            self.reload_sounds_item,
            None,
            self.footer_item,
            None,
            rumps.MenuItem("Çıkış", callback=self.quit_app, key="q"),
        ]

        self._apply_menu_typography()

        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=256)
        pygame.mixer.init()

        self._populate_pack_submenu()
        self._load_sounds()
        self._start_listener()

    @staticmethod
    def _load_saved_volume():
        try:
            from Foundation import NSUserDefaults

            d = NSUserDefaults.standardUserDefaults()
            if d.objectForKey_(UD_VOLUME_PERCENT) is None:
                return 0.8
            v = float(d.doubleForKey_(UD_VOLUME_PERCENT)) / 100.0
            v = max(0.0, min(1.0, v))
            # Slider kaydetmiş 0.0 → sessiz; çoğu kullanıcıda yanlışlıkla 0 kalmış olur
            if v < 0.001:
                return 0.8
            return v
        except Exception:
            return 0.8

    def _save_volume_prefs(self):
        try:
            from Foundation import NSUserDefaults

            d = NSUserDefaults.standardUserDefaults()
            d.setDouble_forKey_(self.volume * 100.0, UD_VOLUME_PERCENT)
            d.synchronize()
        except Exception:
            pass

    @staticmethod
    def _count_wavs_in_tree(dirpath):
        n = 0
        try:
            for root, _dirs, files in os.walk(dirpath):
                for f in files:
                    if f.lower().endswith(".wav"):
                        n += 1
        except OSError:
            pass
        return n

    def _discover_pack_defs(self):
        """Ses setleri: kökte doğrudan .wav dosyaları + her alt klasördeki .wav ağacı."""
        base = SOUND_DIR
        packs = []
        try:
            os.makedirs(base, exist_ok=True)
        except OSError:
            pass

        root_n = 0
        try:
            for name in os.listdir(base):
                p = os.path.join(base, name)
                if name.startswith(".") or not os.path.isfile(p):
                    continue
                if name.lower().endswith(".wav"):
                    root_n += 1
        except OSError:
            pass

        if root_n > 0:
            packs.append(
                {
                    "id": ROOT_PACK_ID,
                    "title": "Ana klasör",
                    "path": base,
                    "count": root_n,
                }
            )

        try:
            sub_names = sorted(
                n
                for n in os.listdir(base)
                if not n.startswith(".") and os.path.isdir(os.path.join(base, n))
            )
        except OSError:
            sub_names = []

        for name in sub_names:
            p = os.path.join(base, name)
            n = self._count_wavs_in_tree(p)
            if n <= 0:
                continue
            packs.append({"id": name, "title": name, "path": p, "count": n})

        return packs

    def _load_saved_pack_id_string(self):
        try:
            from Foundation import NSUserDefaults

            d = NSUserDefaults.standardUserDefaults()
            if d.objectForKey_(UD_SELECTED_PACK) is None:
                return None
            s = d.stringForKey_(UD_SELECTED_PACK)
            if s is None:
                return None
            return str(s)
        except Exception:
            return None

    def _save_pack_prefs(self, pack_id):
        try:
            from Foundation import NSUserDefaults

            d = NSUserDefaults.standardUserDefaults()
            d.setObject_forKey_(pack_id, UD_SELECTED_PACK)
            d.synchronize()
        except Exception:
            pass

    @staticmethod
    def _default_pack_id_from_defs(packs):
        if not packs:
            return ROOT_PACK_ID
        return max(packs, key=lambda p: (p["count"], p["title"].lower()))["id"]

    def _resolve_selected_pack_id(self, packs):
        if not packs:
            return ROOT_PACK_ID
        valid = {p["id"] for p in packs}
        saved = self._load_saved_pack_id_string()
        if saved in valid:
            return saved
        return self._default_pack_id_from_defs(packs)

    def _active_pack_dir(self):
        for p in self.pack_defs:
            if p["id"] == self.selected_pack_id:
                return p["path"]
        if self.pack_defs:
            return self.pack_defs[0]["path"]
        return SOUND_DIR

    def _pack_choice_title(self, p):
        return "%s  (%d)" % (p["title"], p["count"])

    def _populate_pack_submenu(self):
        """rumps: MenuItem alt menüsü .add() ile doldurulur (tuple çifti değil)."""
        top = self.pack_submenu_item
        if getattr(top, "_menu", None) is not None:
            top.clear()
        self._pack_choice_rows = []
        if not self.pack_defs:
            top.add(rumps.MenuItem("(Klasörde .wav yok)", callback=None))
            return
        for p in self.pack_defs:
            mi = rumps.MenuItem(
                self._pack_choice_title(p),
                callback=self._make_pack_select_callback(p["id"]),
            )
            mi.state = (
                NSControlStateValueOn if p["id"] == self.selected_pack_id else NSControlStateValueOff
            )
            top.add(mi)
            self._pack_choice_rows.append((p["id"], mi))

    def _make_pack_select_callback(self, pack_id):
        def _cb(_):
            self._select_sound_pack(pack_id)

        return _cb

    def _select_sound_pack(self, pack_id):
        if pack_id == self.selected_pack_id:
            return
        ids = {p["id"] for p in self.pack_defs}
        if pack_id not in ids:
            return
        self.selected_pack_id = pack_id
        self._save_pack_prefs(pack_id)
        self._sync_pack_submenu_states()
        self._load_sounds()
        self._update_status_tooltip()

    def _sync_pack_submenu_states(self):
        for pid, mi in getattr(self, "_pack_choice_rows", []):
            try:
                mi.state = (
                    NSControlStateValueOn if pid == self.selected_pack_id else NSControlStateValueOff
                )
            except Exception:
                pass

    def _active_pack_label(self):
        for p in self.pack_defs:
            if p["id"] == self.selected_pack_id:
                return p["title"]
        return ""

    def _status_menu_title(self, n_sounds):
        if n_sounds <= 0:
            return "⚠️  Ses yok — Terminal: mechkeys-download-sounds"
        return "✓  %d ses örneği yüklü" % n_sounds

    def _update_status_item(self):
        self.status_item.title = self._status_menu_title(len(self.sounds))

    @rumps.timer(0.4)
    def _post_launch_tooltip(self, timer):
        """Menü çubuğu ikonuna kısa açıklama (status bar button tooltip)."""
        try:
            self._update_status_tooltip()
        finally:
            try:
                timer.stop()
            except Exception:
                pass

    def _update_status_tooltip(self):
        try:
            from AppKit import NSApplication

            delegate = NSApplication.sharedApplication().delegate()
            if delegate is None or not hasattr(delegate, "nsstatusitem"):
                return
            item = delegate.nsstatusitem
            btn = item.button()
            if btn is None:
                return
            pct = int(round(max(0.0, min(1.0, self.volume)) * 100.0))
            state = "Açık" if self.enabled else "Kapalı"
            n = len(self.sounds)
            pack = self._active_pack_label() or "—"
            btn.setToolTip_("MechKeys — %s — Ses %d%% — %s — %d örnek" % (pack, pct, state, n))
        except Exception:
            pass

    def _open_accessibility_settings(self, _):
        urls = (
            "x-apple.systemsettings:com.apple.preference.security?Privacy_Accessibility",
            "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
        )
        for u in urls:
            try:
                if subprocess.run(["open", u], capture_output=True, timeout=5).returncode == 0:
                    return
            except Exception:
                continue

    def _open_input_monitoring_settings(self, _):
        urls = (
            "x-apple.systemsettings:com.apple.preference.security?Privacy_ListenEvent",
            "x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent",
        )
        for u in urls:
            try:
                if subprocess.run(["open", u], capture_output=True, timeout=5).returncode == 0:
                    return
            except Exception:
                continue

    def _reload_sounds_menu(self, _):
        self.pack_defs = self._discover_pack_defs()
        valid = {p["id"] for p in self.pack_defs}
        if self.selected_pack_id not in valid:
            self.selected_pack_id = self._resolve_selected_pack_id(self.pack_defs)
            self._save_pack_prefs(self.selected_pack_id)
        self._populate_pack_submenu()
        self._load_sounds()
        try:
            rumps.notification("MechKeys", "Sesler", "%d örnek yüklendi." % len(self.sounds))
        except Exception:
            pass

    def _polish_slider(self):
        try:
            s = self.vol_slider._slider
            s.setContinuous_(True)
            from AppKit import NSControlSizeLarge

            s.setControlSize_(NSControlSizeLarge)
        except Exception:
            pass

    def _apply_menu_typography(self):
        """Sabit menü satırlarında sistem fontu ve ikincil renk (Açık/Koyu uyumlu)."""
        try:
            from AppKit import (
                NSAttributedString,
                NSColor,
                NSFont,
                NSFontAttributeName,
                NSForegroundColorAttributeName,
                NSFontWeightMedium,
                NSFontWeightRegular,
            )

            def attr(text, *, size=13.0, weight=NSFontWeightRegular, color=None):
                if color is None:
                    color = NSColor.labelColor()
                font = NSFont.systemFontOfSize_weight_(size, weight)
                return NSAttributedString.alloc().initWithString_attributes_(
                    text,
                    {
                        NSFontAttributeName: font,
                        NSForegroundColorAttributeName: color,
                    },
                )

            self.brand_item._menuitem.setAttributedTitle_(
                attr("MechKeys", size=14.0, weight=NSFontWeightMedium)
            )
            self.tagline_item._menuitem.setAttributedTitle_(
                attr(
                    "Kayıtlı tuş sesleri · Mechvibes",
                    size=11.0,
                    weight=NSFontWeightRegular,
                    color=NSColor.secondaryLabelColor(),
                )
            )
            self.footer_item._menuitem.setAttributedTitle_(
                attr(
                    "Kaynak: Mechvibes · MIT",
                    size=10.0,
                    weight=NSFontWeightRegular,
                    color=NSColor.tertiaryLabelColor(),
                )
            )
        except Exception:
            pass

    def _wav_paths_for_pack(self, pack_id, pack_dir):
        """Ana klasör: yalnızca doğrudan .wav; alt klasör paketleri: tüm ağaç."""
        paths = []
        if pack_id == ROOT_PACK_ID:
            try:
                for name in os.listdir(pack_dir):
                    fp = os.path.join(pack_dir, name)
                    if os.path.isfile(fp) and name.lower().endswith(".wav"):
                        paths.append(fp)
            except OSError:
                pass
        else:
            for root, _dirs, files in os.walk(pack_dir):
                for f in files:
                    if f.lower().endswith(".wav"):
                        paths.append(os.path.join(root, f))
        paths.sort()
        return paths

    def _load_sounds(self):
        """Seçili ses setindeki .wav dosyalarını yükler."""
        self.sounds = []
        if not os.path.exists(SOUND_DIR):
            os.makedirs(SOUND_DIR)
            print(f"[MechKeys] Ses klasörü oluşturuldu: {SOUND_DIR}")
            print("[MechKeys] Lütfen .wav dosyalarını bu klasöre veya alt klasörlere ekleyin.")
            self._update_status_item()
            self._update_status_tooltip()
            return

        pdir = self._active_pack_dir()
        paths = self._wav_paths_for_pack(self.selected_pack_id, pdir)

        for path in paths:
            rel = os.path.relpath(path, SOUND_DIR)
            try:
                snd = pygame.mixer.Sound(path)
                snd.set_volume(self.volume)
                self.sounds.append(snd)
                print(f"[MechKeys] Yüklendi: {rel}")
            except Exception as e:
                print(f"[MechKeys] Hata ({rel}): {e}")

        print(f"[MechKeys] {len(self.sounds)} ses dosyası yüklendi.")
        self._update_status_item()
        self._update_status_tooltip()

    @staticmethod
    def _key_fingerprint(key):
        """Aynı fiziksel tuş her zaman aynı dizeyi üretsin (süreçler arası da sabit)."""
        if isinstance(key, Key):
            return f"K:{key.name}"
        if isinstance(key, KeyCode):
            if key.vk is not None:
                return f"V:{key.vk}"
            if key.char is not None:
                return f"C:{key.char}"
        return f"R:{repr(key)}"

    def _sound_index_for_key(self, key):
        n = len(self.sounds)
        if n == 0:
            return 0
        fp = self._key_fingerprint(key)
        digest = hashlib.md5(fp.encode("utf-8")).digest()
        return int.from_bytes(digest[:4], "big") % n

    def _play_sound_on_main_thread(self, key):
        """pygame mixer ana iş parçacığında güvenilir çalışır (macOS)."""
        if not self.sounds or not self.enabled:
            return
        idx = self._sound_index_for_key(key)
        try:
            self.sounds[idx].play()
        except Exception:
            pass

    def _on_press(self, key):
        """Keyboard event handler — debounce; ses çalma ana kuyrukta."""
        if not self.enabled:
            return
        fp = self._key_fingerprint(key)
        now = time.monotonic()
        with self._debounce_lock:
            last = self._last_key_time.get(fp, 0.0)
            if now - last < KEY_DEBOUNCE_SEC:
                return
            self._last_key_time[fp] = now

        try:
            from Foundation import NSOperationQueue

            NSOperationQueue.mainQueue().addOperationWithBlock_(
                lambda k=key: self._play_sound_on_main_thread(k)
            )
        except Exception:
            threading.Thread(
                target=lambda: self._play_sound_on_main_thread(key),
                daemon=True,
            ).start()

    def _start_listener(self):
        """Start global keyboard listener."""
        self.listener = keyboard.Listener(on_press=self._on_press)
        self.listener.daemon = True
        self.listener.start()
        print("[MechKeys] Klavye dinleyici başlatıldı.")

    def toggle(self, sender):
        self.enabled = not self.enabled
        self.toggle_item.state = NSControlStateValueOn if self.enabled else NSControlStateValueOff
        self.title = "⌨️" if self.enabled else "⌨️ ⏸"
        self._update_status_tooltip()

    def _volume_readout_title(self):
        v = max(0.0, min(1.0, self.volume))
        pct = int(round(v * 100.0))
        steps = 12
        filled = int(round(v * steps))
        filled = max(0, min(steps, filled))
        bar = "█" * filled + "░" * (steps - filled)
        return "Ses  {:>3}%   {}".format(pct, bar)

    def _on_volume_slider(self, sender):
        """Menüdeki NSSlider (rumps.SliderMenuItem)."""
        v = max(0.0, min(1.0, float(sender.value) / 100.0))
        self._set_volume(v, sync_slider=False)
        self.vol_readout.title = self._volume_readout_title()

    def _set_volume(self, vol, sync_slider=True):
        self.volume = max(0.0, min(1.0, float(vol)))
        for snd in self.sounds:
            snd.set_volume(self.volume)
        if sync_slider and hasattr(self, "vol_slider"):
            self.vol_slider.value = self.volume * 100.0
        if hasattr(self, "vol_readout"):
            self.vol_readout.title = self._volume_readout_title()
        self._save_volume_prefs()
        self._update_status_tooltip()

    def quit_app(self, _):
        if self.listener:
            self.listener.stop()
        pygame.mixer.quit()
        rumps.quit_application()


def main():
    MechKeysApp().run()
