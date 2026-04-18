#!/usr/bin/env python3
"""
MechKeys - Cherry MX Blue mechanical keyboard sound simulator
macOS Menubar App
"""

import rumps
import pygame
import threading
import os
import hashlib
from pynput import keyboard
from pynput.keyboard import Key, KeyCode

from mechkeys.paths import get_sound_dir

SOUND_DIR = get_sound_dir()

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
        self.volume = 0.8
        self.sounds = []
        self.listener = None

        self.brand_item = rumps.MenuItem("MechKeys", callback=None)
        self.tagline_item = rumps.MenuItem("Cherry MX Blue · kayıtlı sesler", callback=None)
        self.toggle_item = rumps.MenuItem("Tuş sesleri", callback=self.toggle)
        self.toggle_item.state = NSControlStateValueOn

        self.vol_readout = rumps.MenuItem(self._volume_readout_title(), callback=None)
        self.vol_slider = rumps.SliderMenuItem(
            value=self.volume * 100.0,
            min_value=0.0,
            max_value=100.0,
            dimensions=(260, 28),
            callback=self._on_volume_slider,
        )
        self._polish_slider()

        self.footer_item = rumps.MenuItem("Kaynak: Mechvibes · MIT", callback=None)

        self.menu = [
            self.brand_item,
            self.tagline_item,
            None,
            self.toggle_item,
            None,
            self.vol_readout,
            self.vol_slider,
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

    def _play_sound(self, key):
        """Tuş başına sabit bir WAV; farklı tuşlar havuza dağıtılır."""
        if not self.sounds or not self.enabled:
            return
        idx = self._sound_index_for_key(key)
        self.sounds[idx].play()

    def _on_press(self, key):
        """Keyboard event handler."""
        if self.enabled:
            threading.Thread(target=self._play_sound, args=(key,), daemon=True).start()

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

    def quit_app(self, _):
        if self.listener:
            self.listener.stop()
        pygame.mixer.quit()
        rumps.quit_application()


def main():
    MechKeysApp().run()
