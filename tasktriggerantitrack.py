#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Disparador
==========
Programador de tareas de escritorio. Fusiona dos ideas:

  - "Alarma": dispara a una hora ALEATORIA dentro de un rango, ejecuta un
    programa / abre un archivo o URL, con sonido y aviso.
  - "Continua terminales": a una hora, escribe un texto + Enter en todas las
    terminales abiertas que casen un filtro (reanudar Claude al reset de uso).

Cada tarea tiene:
  - Cuando : hora FIJA (HH:MM) o ALEATORIA dentro de [desde, hasta]. Repetir a diario.
  - Accion : TERMINALES (teclea texto+Enter en ventanas que casen un filtro)
             o PROGRAMA (ejecuta programa / abre archivo o URL).
  - Extras : sonido al disparar, aviso emergente.

Sin dependencias pip: solo stdlib (tkinter, ctypes en Windows; xdotool en Linux
para teclear en ventanas; aplay/paplay para sonido).
"""

import os
import sys
import json
import time
import random
import shutil
import threading
import subprocess
from datetime import datetime, timedelta

import tkinter as tk
from tkinter import messagebox, filedialog, ttk

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ALARMS_FILE = os.path.join(APP_DIR, "alarms.json")
SOUND_FILE = os.path.join(APP_DIR, "alarm_sound.wav")
ICO_FILE = os.path.join(APP_DIR, "icon.ico")
ISO = "%Y-%m-%d %H:%M:%S"

# ======================================================================
#  Teclear en terminales  (Windows via ctypes, Linux via xdotool)
# ======================================================================
if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    wintypes.ULONG_PTR = wintypes.WPARAM

    INPUT_KEYBOARD = 1
    KEYEVENTF_KEYUP = 0x0002
    KEYEVENTF_UNICODE = 0x0004
    VK_RETURN = 0x0D
    SW_RESTORE, SW_SHOW = 9, 5

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = (("dx", wintypes.LONG), ("dy", wintypes.LONG),
                    ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD), ("dwExtraInfo", wintypes.ULONG_PTR))

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = (("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                    ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                    ("dwExtraInfo", wintypes.ULONG_PTR))

    class HARDWAREINPUT(ctypes.Structure):
        _fields_ = (("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD),
                    ("wParamH", wintypes.WORD))

    class _IUNION(ctypes.Union):
        _fields_ = (("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT))

    class INPUT(ctypes.Structure):
        _fields_ = (("type", wintypes.DWORD), ("u", _IUNION))

    EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def _kb(wVk, wScan, flags):
        inp = INPUT()
        inp.type = INPUT_KEYBOARD
        inp.u.ki = KEYBDINPUT(wVk, wScan, flags, 0, 0)
        return inp

    def _send(inp):
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    def list_windows(filt):
        res = []
        filt = (filt or "").lower()

        def cb(h, _):
            if not user32.IsWindowVisible(h):
                return True
            n = user32.GetWindowTextLengthW(h)
            if n == 0:
                return True
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(h, buf, n + 1)
            t = buf.value
            if (not filt) or (filt in t.lower()):
                res.append((h, t))
            return True

        user32.EnumWindows(EnumWindowsProc(cb), 0)
        return res

    def _focus(h):
        if user32.IsIconic(h):
            user32.ShowWindow(h, SW_RESTORE)
        fg = user32.GetForegroundWindow()
        tcur = kernel32.GetCurrentThreadId()
        pid = wintypes.DWORD()
        ttg = user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
        tfg = user32.GetWindowThreadProcessId(fg, ctypes.byref(pid))
        if tcur != ttg:
            user32.AttachThreadInput(tcur, ttg, True)
        if tfg != ttg:
            user32.AttachThreadInput(tfg, ttg, True)
        user32.ShowWindow(h, SW_SHOW)
        user32.SetForegroundWindow(h)
        if tcur != ttg:
            user32.AttachThreadInput(tcur, ttg, False)
        if tfg != ttg:
            user32.AttachThreadInput(tfg, ttg, False)

    def send_to_terminals(filt, text):
        wins = list_windows(filt)
        for h, _ in wins:
            _focus(h)
            time.sleep(0.35)
            for ch in text:
                if ord(ch) > 0xFFFF:  # fuera del BMP, raro en comandos
                    continue
                _send(_kb(0, ord(ch), KEYEVENTF_UNICODE))
                _send(_kb(0, ord(ch), KEYEVENTF_UNICODE | KEYEVENTF_KEYUP))
            time.sleep(0.12)
            _send(_kb(VK_RETURN, 0, 0))
            _send(_kb(VK_RETURN, 0, KEYEVENTF_KEYUP))
            time.sleep(0.25)
        return len(wins)

else:  # Linux / otros: xdotool
    def list_windows(filt):
        if not shutil.which("xdotool"):
            return []
        try:
            out = subprocess.check_output(
                ["xdotool", "search", "--name", filt or ""],
                stderr=subprocess.DEVNULL).decode().split()
        except Exception:
            return []
        res = []
        for wid in out:
            try:
                name = subprocess.check_output(
                    ["xdotool", "getwindowname", wid],
                    stderr=subprocess.DEVNULL).decode().strip()
            except Exception:
                name = wid
            res.append((wid, name))
        return res

    def send_to_terminals(filt, text):
        wins = list_windows(filt)
        for wid, _ in wins:
            subprocess.call(["xdotool", "windowactivate", "--sync", wid])
            time.sleep(0.3)
            subprocess.call(["xdotool", "type", "--", text])
            subprocess.call(["xdotool", "key", "Return"])
            time.sleep(0.2)
        return len(wins)


def play_sound(path):
    if not os.path.exists(path):
        return
    try:
        if sys.platform == "win32":
            import winsound
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        elif sys.platform == "darwin":
            subprocess.Popen(["afplay", path])
        else:
            for p in ("paplay", "aplay"):
                if shutil.which(p):
                    subprocess.Popen([p, path], stderr=subprocess.DEVNULL)
                    break
    except Exception as e:
        print("sonido:", e)


def run_program(program, file_url):
    try:
        if program:
            args = [program] + ([file_url] if file_url else [])
            subprocess.Popen(args)
        elif file_url:
            if sys.platform == "win32":
                os.startfile(file_url)  # noqa
            elif sys.platform == "darwin":
                subprocess.Popen(["open", file_url])
            else:
                subprocess.Popen(["xdg-open", file_url])
    except Exception as e:
        print("programa:", e)


# ======================================================================
#  Programacion de la siguiente hora de disparo
# ======================================================================
def _hm(s):
    h, m = s.strip().split(":")
    return int(h), int(m)


def compute_next(alarm, now=None):
    now = now or datetime.now()
    if alarm.get("time_mode", "fixed") == "fixed":
        h, m = _hm(alarm["time"])
        t = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if t <= now:
            t += timedelta(days=1)
        return t
    # aleatoria en rango
    sh, sm = _hm(alarm["start_time"])
    eh, em = _hm(alarm["end_time"])
    start = now.replace(hour=sh, minute=sm, second=0, microsecond=0)
    end = now.replace(hour=eh, minute=em, second=0, microsecond=0)
    if end <= start:                 # ventana que cruza medianoche
        end += timedelta(days=1)
    if end <= now:                   # la ventana de hoy ya paso
        start += timedelta(days=1)
        end += timedelta(days=1)
    lo = max(start, now)
    span = max(int((end - lo).total_seconds()), 0)
    return lo + timedelta(seconds=random.randint(0, span))


# ======================================================================
#  Interfaz
# ======================================================================
BG = "#13131a"
CARD = "#1c1c26"
FG = "#e6e6f0"
MUT = "#a6a6c0"
ACC = "#7aa2ff"
OK = "#8ee6a8"
WARN = "#f2c96b"
DANGER = "#f28ba8"


class Tooltip:
    """Ayuda contextual al pasar el ratón o al enfocar con el teclado."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<FocusIn>", self._show, add="+")
        widget.bind("<FocusOut>", self._hide, add="+")

    def _show(self, _=None):
        if self.tip or not self.text:
            return
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry("+%d+%d" % (x, y))
        tk.Label(tw, text=self.text, bg="#2a2a3a", fg="#e6e6f0", bd=1, relief="solid",
                 font=("Segoe UI", 9), padx=7, pady=4, wraplength=340, justify="left").pack()

    def _hide(self, _=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


class App:
    def __init__(self, root):
        self.root = root
        root.title("TaskTriggerAntitrack")
        root.configure(bg=BG)
        root.geometry("600x740")
        root.minsize(560, 680)
        if sys.platform == "win32" and os.path.exists(ICO_FILE):
            try:
                root.iconbitmap(ICO_FILE)
            except Exception:
                pass

        self.alarms = []
        self.selected = None
        self._build_style()
        self._build_ui()
        self.load()
        self.tick()

    # ---- estilo ttk oscuro ---------------------------------------
    def _build_style(self):
        st = ttk.Style()
        try:
            st.theme_use("clam")
        except Exception:
            pass
        st.configure(".", background=BG, foreground=FG,
                     fieldbackground=CARD, bordercolor=CARD, font=("Segoe UI", 11))
        st.configure("TFrame", background=BG)
        st.configure("Card.TFrame", background=CARD)
        st.configure("TLabel", background=BG, foreground=FG)
        st.configure("Card.TLabel", background=CARD, foreground=FG)
        st.configure("Mut.TLabel", background=CARD, foreground=MUT, font=("Segoe UI", 9))
        st.configure("H.TLabel", background=BG, foreground=ACC, font=("Segoe UI Semibold", 15))
        st.configure("TEntry", fieldbackground="#262633", foreground=FG, insertcolor=FG)
        st.configure("TSpinbox", fieldbackground="#262633", foreground=FG, arrowcolor=FG)
        st.configure("TCheckbutton", background=CARD, foreground=FG)
        st.map("TCheckbutton", background=[("active", CARD)])
        st.configure("TRadiobutton", background=CARD, foreground=FG)
        st.map("TRadiobutton", background=[("active", CARD)])
        st.configure("Accent.TButton", background=ACC, foreground="#0b0b12",
                     font=("Segoe UI Semibold", 11), borderwidth=0, padding=8)
        st.map("Accent.TButton", background=[("active", "#9cb8ff")])
        st.configure("Ghost.TButton", background=CARD, foreground=FG, borderwidth=0, padding=6)
        st.map("Ghost.TButton", background=[("active", "#2a2a38")])
        st.configure("Danger.TButton", background="#3a2230", foreground=DANGER, borderwidth=0, padding=6)
        st.map("Danger.TButton", background=[("active", "#4a2a3c")])
        # indicador de foco visible (accesibilidad por teclado)
        st.map("TEntry", bordercolor=[("focus", ACC)], lightcolor=[("focus", ACC)])
        st.map("TSpinbox", bordercolor=[("focus", ACC)], lightcolor=[("focus", ACC)])
        st.map("TButton", relief=[("focus", "solid")])

    # ---- construccion de la ventana ------------------------------
    def _build_ui(self):
        ttk.Label(self.root, text="Disparador", style="H.TLabel").pack(anchor="w", padx=18, pady=(14, 0))
        ttk.Label(self.root, text="Programador de tareas · terminales y alarmas",
                  background=BG, foreground=MUT, font=("Segoe UI", 9)).pack(anchor="w", padx=18)

        card = ttk.Frame(self.root, style="Card.TFrame", padding=14)
        card.pack(fill="x", padx=14, pady=12)

        # nombre
        self.name = self._row_entry(card, "Nombre", 0, "continua")

        # modo de hora
        self.time_mode = tk.StringVar(value="fixed")
        mr = ttk.Frame(card, style="Card.TFrame")
        mr.grid(row=1, column=0, columnspan=3, sticky="w", pady=(8, 2))
        ttk.Radiobutton(mr, text="Hora fija", value="fixed", variable=self.time_mode,
                        command=self._sync_mode).pack(side="left", padx=(0, 16))
        ttk.Radiobutton(mr, text="Aleatoria en rango", value="random", variable=self.time_mode,
                        command=self._sync_mode).pack(side="left")

        # hora fija
        self.fixed_row = ttk.Frame(card, style="Card.TFrame")
        self.fixed_row.grid(row=2, column=0, columnspan=3, sticky="w", pady=2)
        ttk.Label(self.fixed_row, text="Hora (HH:MM)", style="Card.TLabel", width=14).pack(side="left")
        self.t_h, self.t_m = self._hm_spin(self.fixed_row, 5, 0)

        # rango
        self.rand_row = ttk.Frame(card, style="Card.TFrame")
        self.rand_row.grid(row=3, column=0, columnspan=3, sticky="w", pady=2)
        _rsub = ttk.Frame(self.rand_row, style="Card.TFrame")
        _rsub.pack(anchor="w")
        ttk.Label(_rsub, text="Desde", style="Card.TLabel", width=14).pack(side="left")
        self.s_h, self.s_m = self._hm_spin(_rsub, 0, 0)
        ttk.Label(_rsub, text="  hasta", style="Card.TLabel").pack(side="left")
        self.e_h, self.e_m = self._hm_spin(_rsub, 8, 0)
        ttk.Label(self.rand_row,
                  text="(i) La hora exacta es impredecible dentro del rango → antitrazabilidad.",
                  style="Mut.TLabel").pack(anchor="w", pady=(3, 0))

        self.daily = tk.BooleanVar(value=True)
        ttk.Checkbutton(card, text="Repetir cada día", variable=self.daily).grid(
            row=4, column=0, columnspan=3, sticky="w", pady=(4, 8))

        ttk.Separator(card, orient="horizontal").grid(row=5, column=0, columnspan=3, sticky="ew", pady=6)

        # tipo de accion
        self.action = tk.StringVar(value="terminal")
        ar = ttk.Frame(card, style="Card.TFrame")
        ar.grid(row=6, column=0, columnspan=3, sticky="w")
        ttk.Radiobutton(ar, text="Escribir en terminales", value="terminal", variable=self.action,
                        command=self._sync_mode).pack(side="left", padx=(0, 16))
        ttk.Radiobutton(ar, text="Ejecutar programa / abrir", value="program", variable=self.action,
                        command=self._sync_mode).pack(side="left")

        # accion terminal
        self.term_box = ttk.Frame(card, style="Card.TFrame")
        self.term_box.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(6, 0))
        self.filt = self._row_entry(self.term_box, "Filtro de título", 0, "claude")
        self.text = self._row_entry(self.term_box, "Texto a enviar", 1, "continua")
        ttk.Label(self.term_box, text="Casa ventanas cuyo título contenga el filtro; teclea el texto + Enter.",
                  style="Mut.TLabel").grid(row=2, column=0, columnspan=3, sticky="w", pady=(2, 0))

        # accion programa
        self.prog_box = ttk.Frame(card, style="Card.TFrame")
        self.prog_box.grid(row=8, column=0, columnspan=3, sticky="ew", pady=(6, 0))
        self.program = self._row_entry(self.prog_box, "Programa", 0, "",
                                       browse=lambda: self._pick(self.program))
        self.file_url = self._row_entry(self.prog_box, "Archivo / URL", 1, "",
                                        browse=lambda: self._pick(self.file_url))

        # extras
        ex = ttk.Frame(card, style="Card.TFrame")
        ex.grid(row=9, column=0, columnspan=3, sticky="w", pady=(10, 2))
        self.snd = tk.BooleanVar(value=False)
        self.pop = tk.BooleanVar(value=False)
        ttk.Checkbutton(ex, text="Sonido", variable=self.snd).pack(side="left", padx=(0, 16))
        ttk.Checkbutton(ex, text="Aviso emergente", variable=self.pop).pack(side="left")
        self.msg = self._row_entry(card, "Mensaje del aviso", 10, "")

        # botones de accion sobre el formulario
        br = ttk.Frame(card, style="Card.TFrame")
        br.grid(row=11, column=0, columnspan=3, sticky="ew", pady=(12, 0))
        ttk.Button(br, text="Guardar tarea", style="Accent.TButton", command=self.save_task).pack(side="left")
        ttk.Button(br, text="Limpiar", style="Ghost.TButton", command=self.clear).pack(side="left", padx=8)
        ttk.Button(br, text="Probar ahora", style="Ghost.TButton", command=self.test_now).pack(side="left")

        card.grid_columnconfigure(1, weight=1)

        # ayuda contextual
        Tooltip(self.filt, "Parte del título de las ventanas objetivo. Ej.: 'claude'.")
        Tooltip(self.text, "Lo que se teclea en cada ventana, seguido de Enter.")
        Tooltip(self.program, "Programa a ejecutar. El Archivo/URL se le pasa como argumento.")
        Tooltip(self.file_url, "Archivo o URL. Sin programa, se abre con la app por defecto.")

        # lista
        lf = ttk.Frame(self.root, style="TFrame")
        lf.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        ttk.Label(lf, text="Tareas programadas", background=BG, foreground=MUT).pack(anchor="w")
        inner = tk.Frame(lf, bg=CARD)
        inner.pack(fill="both", expand=True, pady=(4, 0))
        self.lb = tk.Listbox(inner, bg=CARD, fg=FG, selectbackground=ACC, selectforeground="#0b0b12",
                             borderwidth=0, highlightthickness=1, highlightcolor=ACC,
                             activestyle="none", font=("Consolas", 10))
        self.lb.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(inner, command=self.lb.yview)
        sb.pack(side="right", fill="y")
        self.lb.config(yscrollcommand=sb.set)
        self.lb.bind("<<ListboxSelect>>", self.on_select)

        row = ttk.Frame(self.root, style="TFrame")
        row.pack(fill="x", padx=14, pady=(0, 12))
        ttk.Button(row, text="Activar / pausar", style="Ghost.TButton", command=self.toggle).pack(side="left")
        ttk.Button(row, text="Eliminar", style="Danger.TButton", command=self.delete).pack(side="left", padx=8)
        self.status = ttk.Label(row, text="", background=BG, foreground=MUT)
        self.status.pack(side="right")

        # atajos de teclado (accesibilidad)
        self.root.bind_all("<Control-s>", lambda e: self.save_task())
        self.root.bind_all("<Control-Return>", lambda e: self.save_task())
        self.root.bind_all("<Control-t>", lambda e: self.test_now())
        self.root.bind_all("<Escape>", lambda e: self.clear())
        self.lb.bind("<Delete>", lambda e: self.delete())
        ttk.Label(self.root, text="Atajos:  Ctrl+S guardar · Ctrl+T probar · Esc limpiar · Supr eliminar",
                  background=BG, foreground=MUT, font=("Segoe UI", 9)).pack(anchor="w", padx=18, pady=(0, 8))

        self._sync_mode()

    # ---- helpers de widgets --------------------------------------
    def _row_entry(self, parent, label, r, default="", browse=None):
        ttk.Label(parent, text=label, style="Card.TLabel", width=16).grid(row=r, column=0, sticky="w", pady=3)
        e = ttk.Entry(parent)
        e.insert(0, default)
        e.grid(row=r, column=1, sticky="ew", pady=3)
        parent.grid_columnconfigure(1, weight=1)
        if browse:
            ttk.Button(parent, text="…", style="Ghost.TButton", width=3, command=browse).grid(
                row=r, column=2, padx=(6, 0))
        return e

    def _hm_spin(self, parent, h, m):
        sh = ttk.Spinbox(parent, from_=0, to=23, width=4, format="%02.0f", wrap=True)
        sh.set("%02d" % h)
        sh.pack(side="left", padx=2)
        ttk.Label(parent, text=":", style="Card.TLabel").pack(side="left")
        sm = ttk.Spinbox(parent, from_=0, to=59, width=4, format="%02.0f", wrap=True)
        sm.set("%02d" % m)
        sm.pack(side="left", padx=2)
        return sh, sm

    def _pick(self, entry):
        p = filedialog.askopenfilename()
        if p:
            entry.delete(0, tk.END)
            entry.insert(0, p)

    def _sync_mode(self):
        if self.time_mode.get() == "fixed":
            self.fixed_row.grid()
            self.rand_row.grid_remove()
        else:
            self.fixed_row.grid_remove()
            self.rand_row.grid()
        if self.action.get() == "terminal":
            self.term_box.grid()
            self.prog_box.grid_remove()
        else:
            self.term_box.grid_remove()
            self.prog_box.grid()

    # ---- recoger / volcar formulario -----------------------------
    def _collect(self):
        a = {
            "name": self.name.get().strip() or "tarea",
            "time_mode": self.time_mode.get(),
            "time": "%02d:%02d" % (int(self.t_h.get()), int(self.t_m.get())),
            "start_time": "%02d:%02d" % (int(self.s_h.get()), int(self.s_m.get())),
            "end_time": "%02d:%02d" % (int(self.e_h.get()), int(self.e_m.get())),
            "daily": self.daily.get(),
            "action": self.action.get(),
            "filter": self.filt.get().strip(),
            "text": self.text.get(),
            "program": self.program.get().strip(),
            "file_url": self.file_url.get().strip(),
            "sound": self.snd.get(),
            "popup": self.pop.get(),
            "message": self.msg.get(),
            "enabled": True,
        }
        if a["time_mode"] == "random":
            sh, sm = _hm(a["start_time"])
            eh, em = _hm(a["end_time"])
            if (sh, sm) == (eh, em):
                messagebox.showerror("Rango inválido", "El rango 'desde/hasta' no puede ser el mismo minuto.")
                return None
        a["next_fire"] = compute_next(a).strftime(ISO)
        return a

    def _fill(self, a):
        self.clear()
        self.name.insert(0, a.get("name", ""))
        self.time_mode.set(a.get("time_mode", "fixed"))
        th, tm = _hm(a.get("time", "05:00"))
        self.t_h.set("%02d" % th); self.t_m.set("%02d" % tm)
        sh, sm = _hm(a.get("start_time", "00:00"))
        self.s_h.set("%02d" % sh); self.s_m.set("%02d" % sm)
        eh, em = _hm(a.get("end_time", "08:00"))
        self.e_h.set("%02d" % eh); self.e_m.set("%02d" % em)
        self.daily.set(a.get("daily", True))
        self.action.set(a.get("action", "terminal"))
        self.filt.insert(0, a.get("filter", ""))
        self.text.insert(0, a.get("text", ""))
        self.program.insert(0, a.get("program", ""))
        self.file_url.insert(0, a.get("file_url", ""))
        self.snd.set(a.get("sound", False))
        self.pop.set(a.get("popup", False))
        self.msg.insert(0, a.get("message", ""))
        self._sync_mode()

    # ---- acciones de la lista ------------------------------------
    def save_task(self):
        a = self._collect()
        if not a:
            return
        if self.selected is not None:
            self.alarms[self.selected] = a
        else:
            self.alarms.append(a)
        self.selected = None
        self.refresh()
        self.save()
        self._flash("Tarea guardada.")

    def clear(self):
        for e in (self.name, self.filt, self.text, self.program, self.file_url, self.msg):
            e.delete(0, tk.END)
        self.selected = None

    def delete(self):
        if self.selected is None:
            return
        del self.alarms[self.selected]
        self.selected = None
        self.clear()
        self.refresh()
        self.save()

    def toggle(self):
        if self.selected is None:
            return
        a = self.alarms[self.selected]
        a["enabled"] = not a.get("enabled", True)
        if a["enabled"]:
            a["next_fire"] = compute_next(a).strftime(ISO)
        self.refresh()
        self.save()

    def on_select(self, _):
        sel = self.lb.curselection()
        if not sel:
            return
        self.selected = sel[0]
        self._fill(self.alarms[self.selected])

    def test_now(self):
        a = self._collect()
        if a:
            self._fire(a, test=True)

    # ---- lista / persistencia ------------------------------------
    def refresh(self):
        self.lb.delete(0, tk.END)
        for a in self.alarms:
            when = (a["time"] if a["time_mode"] == "fixed"
                    else "%s–%s rnd" % (a["start_time"], a["end_time"]))
            nf = a.get("next_fire", "")[-8:]
            tag = "✎" if a["action"] == "terminal" else "▷"
            state = "●" if a.get("enabled", True) else "⏸"
            daily = "↻" if a.get("daily") else " "
            self.lb.insert(tk.END, "%s %s %-16s %-11s next %s %s" %
                           (state, tag, a["name"][:16], when, nf, daily))

    def save(self):
        try:
            with open(ALARMS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.alarms, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print("save:", e)

    def load(self):
        if os.path.exists(ALARMS_FILE):
            try:
                with open(ALARMS_FILE, encoding="utf-8") as f:
                    self.alarms = json.load(f)
            except Exception as e:
                print("load:", e)
                self.alarms = []
        # recalcular disparos pasados al arrancar
        now = datetime.now()
        for a in self.alarms:
            nf = a.get("next_fire")
            if a.get("enabled", True) and (not nf or datetime.strptime(nf, ISO) <= now):
                a["next_fire"] = compute_next(a, now).strftime(ISO)
        self.refresh()
        self.save()

    def _flash(self, msg):
        self.status.config(text=msg)
        self.root.after(3000, lambda: self.status.config(text=""))

    # ---- disparo --------------------------------------------------
    def _fire(self, a, test=False):
        def work():
            if a.get("sound"):
                play_sound(SOUND_FILE)
            if a["action"] == "terminal":
                n = send_to_terminals(a.get("filter", ""), a.get("text", ""))
                self.root.after(0, lambda: self._flash(
                    ("PRUEBA: " if test else "") + "enviado a %d ventana(s)" % n))
            else:
                run_program(a.get("program", ""), a.get("file_url", ""))
                self.root.after(0, lambda: self._flash(
                    ("PRUEBA: " if test else "") + "programa lanzado"))
            if a.get("popup") and a.get("message"):
                self.root.after(0, lambda: messagebox.showinfo(a.get("name", "Disparador"), a["message"]))

        threading.Thread(target=work, daemon=True).start()

    def tick(self):
        now = datetime.now()
        changed = False
        for a in self.alarms:
            if not a.get("enabled", True):
                continue
            nf = a.get("next_fire")
            if nf and now >= datetime.strptime(nf, ISO):
                self._fire(a)
                if a.get("daily"):
                    a["next_fire"] = compute_next(a, now + timedelta(minutes=1)).strftime(ISO)
                else:
                    a["enabled"] = False
                changed = True
        if changed:
            self.refresh()
            self.save()
        self.root.after(1000, self.tick)


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
