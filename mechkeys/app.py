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

UD_VOLUME_PERCENT = "MechKeysVolumePercent"
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
        self.listener = None
        self._last_key_time = {}
        self._debounce_lock = threading.Lock()

        self.brand_item = rumps.MenuItem("MechKeys", callback=None)
        self.tagline_item = rumps.MenuItem("Cherry MX Blue · kayıtlı sesler", callback=None)
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

        self.menu = [
            self.brand_item,
            self.tagline_item,
            None,
            self.toggle_item,
            self.status_item,
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
            btn.setToolTip_("MechKeys — Ses %d%% — %s — %d örnek" % (pct, state, n))
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
                    "Cherry MX Blue · kayıtlı sesler",
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

    def _load_sounds(self):
        """Load all .wav files from sounds directory."""
        self.sounds = []
        if not os.path.exists(SOUND_DIR):
            os.makedirs(SOUND_DIR)
            print(f"[MechKeys] Ses klasörü oluşturuldu: {SOUND_DIR}")
            print("[MechKeys] Lütfen Cherry MX Blue .wav dosyalarını bu klasöre ekleyin.")
            self._update_status_item()
            self._update_status_tooltip()
            return

        paths = []
        for root, _dirs, files in os.walk(SOUND_DIR):
            for f in files:
                if f.lower().endswith(".wav"):
                    paths.append(os.path.join(root, f))
        paths.sort()

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
