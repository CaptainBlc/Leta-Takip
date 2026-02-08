from __future__ import annotations

import sys


def center_window(win, w: int, h: int) -> None:
    win.update_idletasks()
    x = (win.winfo_screenwidth() // 2) - (w // 2)
    y = (win.winfo_screenheight() // 2) - (h // 2)
    win.geometry(f"{w}x{h}+{x}+{y}")


def center_window_smart(
    win,
    w: int,
    h: int,
    max_ratio: float = 0.85,
    min_w: int = 800,
    min_h: int = 600,
    **_ignored,
) -> None:
    """
    app_ui bazı yerlerde min_w/min_h gönderiyor. Eski imzada yoktu -> crash.
    Bu sürüm:
      - ekran oranına göre maks sınır uygular
      - min_w/min_h garantiler
      - ekstra argüman gelirse kırılmaz (**_ignored)
    """
    try:
        win.update_idletasks()
        sw = int(win.winfo_screenwidth() or 0)
        sh = int(win.winfo_screenheight() or 0)

        # minimum garanti
        w = max(int(w), int(min_w))
        h = max(int(h), int(min_h))

        # ekran sınırı
        if sw > 0 and sh > 0:
            w = min(w, int(sw * max_ratio))
            h = min(h, int(sh * max_ratio))

        center_window(win, w, h)
    except Exception:
        try:
            center_window(win, max(w, min_w), max(h, min_h))
        except Exception:
            pass


def maximize_window(win) -> None:
    """
    Platforma göre en güvenli maximize:
    - Windows: state('zoomed')
    - Linux: attributes('-zoomed', True) dene
    - macOS: full-screen/zoom bazen sorunlu; en güvenlisi geometry ile büyütmek
    """
    try:
        plat = sys.platform.lower()

        if plat.startswith("win"):
            try:
                win.state("zoomed")
                return
            except Exception:
                pass

        # Linux/Tk bazen -zoomed destekler
        try:
            win.attributes("-zoomed", True)
            return
        except Exception:
            pass

        # macOS / fallback: ekran boyuna yakın büyüt
        win.update_idletasks()
        sw = int(win.winfo_screenwidth() or 0)
        sh = int(win.winfo_screenheight() or 0)
        if sw > 0 and sh > 0:
            w = int(sw * 0.92)
            h = int(sh * 0.90)
            win.geometry(f"{w}x{h}+20+20")
    except Exception:
        pass
