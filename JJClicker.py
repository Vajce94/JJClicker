#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk
import threading
import time
import json
import sys
import subprocess
from pathlib import Path

IS_MACOS   = sys.platform == 'darwin'
IS_WINDOWS = sys.platform == 'win32'

if IS_MACOS:
    import AppKit
    from Quartz.CoreGraphics import (
        CGWarpMouseCursorPosition, CGPoint,
        CGEventCreateMouseEvent, CGEventPost,
        kCGEventLeftMouseDown, kCGEventLeftMouseUp,
        kCGEventRightMouseDown, kCGEventRightMouseUp,
        kCGEventMouseMoved,
        kCGMouseButtonLeft, kCGMouseButtonRight,
        kCGHIDEventTap,
        CGMainDisplayID, CGDisplayBounds,
        CGEventSourceCreate, kCGEventSourceStateHIDSystemState,
        CGEventCreateKeyboardEvent, CGEventSetFlags,
        kCGEventFlagMaskControl,
    )

if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes

try:
    from pynput import mouse as pynput_mouse
    from pynput import keyboard as pynput_keyboard
except ImportError:
    sys.exit("Missing pynput. Run: pip3 install pynput")

TEMPLATES_DIR = Path.home() / ".jjclicker" / "templates"
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

SETTINGS_PATH = Path.home() / ".jjclicker" / "settings.json"

APP_VERSION = "1.0.0"
APP_AUTHOR  = "Juraj Jajčaj"

# ── Menu-bar helper script (runs in its own process with a real AppKit loop) ──
_MENUBAR_HELPER = r"""
import sys, os, threading, time, AppKit

# ── Watch parent process — exit when JJClicker dies (any reason) ──────────
def _watch_parent():
    ppid = os.getppid()
    while True:
        time.sleep(0.5)
        try:
            os.kill(ppid, 0)   # signal 0: just checks if process is alive
        except (ProcessLookupError, OSError):
            # Parent is gone — terminate ourselves cleanly
            AppKit.NSApplication.sharedApplication().terminate_(None)
            return
threading.Thread(target=_watch_parent, daemon=True).start()

class _D(AppKit.NSObject):
    def open_(self, _):   sys.stdout.write('open\n');   sys.stdout.flush()
    def record_(self, _): sys.stdout.write('record\n'); sys.stdout.flush()
    def play_(self, _):   sys.stdout.write('play\n');   sys.stdout.flush()
    def about_(self, _):  sys.stdout.write('about\n');  sys.stdout.flush()
    def quit_(self, _):   sys.stdout.write('quit\n');   sys.stdout.flush()

def _mi(menu, title, sel):
    item = AppKit.NSMenuItem.alloc().init()
    item.setTitle_(title)
    item.setTarget_(d)
    item.setAction_(getattr(_D, sel).selector)
    menu.addItem_(item)

nsapp = AppKit.NSApplication.sharedApplication()
nsapp.setActivationPolicy_(1)   # Accessory: no Dock icon for helper

d = _D.alloc().init()
sb  = AppKit.NSStatusBar.systemStatusBar()
si  = sb.statusItemWithLength_(AppKit.NSVariableStatusItemLength)
si.setVisible_(True)
btn = si.button()
try:
    img = AppKit.NSImage.imageWithSystemSymbolName_accessibilityDescription_(
        'cursorarrow.click.2', 'JJClicker')
    if img: btn.setImage_(img)
    else:   btn.setTitle_('JJ')
except Exception:
    btn.setTitle_('JJ')

titles = sys.argv[1:]
lbl = dict(zip(['about','open','record','play','quit'], titles)) if len(titles)==5 else {}

menu = AppKit.NSMenu.alloc().init()
_mi(menu, lbl.get('about', 'About JJClicker'),   'about_')
menu.addItem_(AppKit.NSMenuItem.separatorItem())
_mi(menu, lbl.get('open',  'Open JJClicker'),    'open_')
menu.addItem_(AppKit.NSMenuItem.separatorItem())
_mi(menu, lbl.get('record','⏺  Record'),          'record_')
_mi(menu, lbl.get('play',  '▶  Play / Stop'),     'play_')
menu.addItem_(AppKit.NSMenuItem.separatorItem())
_mi(menu, lbl.get('quit',  'Quit JJClicker'),     'quit_')
si.setMenu_(menu)

sys.stderr.write('[menubar] ready\n'); sys.stderr.flush()
nsapp.run()
"""

# ── Windows system-tray helper (runs in its own process with pystray) ──────
_MENUBAR_HELPER_WINDOWS = r"""
import sys, os, threading, time

try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError as e:
    sys.stderr.write(f'[tray] missing dependency: {e}\n')
    sys.exit(1)

_icon_ref = [None]

def _watch_parent():
    ppid = os.getppid()
    while True:
        time.sleep(0.5)
        try:
            os.kill(ppid, 0)
        except (ProcessLookupError, OSError):
            if _icon_ref[0]:
                _icon_ref[0].stop()
            return
threading.Thread(target=_watch_parent, daemon=True).start()

def _send(cmd):
    sys.stdout.write(cmd + '\n')
    sys.stdout.flush()

titles = sys.argv[1:]
lbl = dict(zip(['about','open','record','play','quit'], titles)) if len(titles)==5 else {}

def _make_icon():
    size = 64
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([2, 2, size-2, size-2], fill=(137, 180, 250, 255))
    d.rectangle([16, 24, 20, 40], fill=(30, 30, 46, 255))
    d.rectangle([28, 24, 32, 40], fill=(30, 30, 46, 255))
    d.rectangle([40, 24, 44, 40], fill=(30, 30, 46, 255))
    d.rectangle([52, 24, 56, 40], fill=(30, 30, 46, 255))
    return img

menu = pystray.Menu(
    pystray.MenuItem(lbl.get('about', 'About JJClicker'), lambda icon, item: _send('about')),
    pystray.Menu.SEPARATOR,
    pystray.MenuItem(lbl.get('open',  'Open JJClicker'),  lambda icon, item: _send('open')),
    pystray.Menu.SEPARATOR,
    pystray.MenuItem(lbl.get('record','Record'),           lambda icon, item: _send('record')),
    pystray.MenuItem(lbl.get('play',  'Play / Stop'),      lambda icon, item: _send('play')),
    pystray.Menu.SEPARATOR,
    pystray.MenuItem(lbl.get('quit',  'Quit JJClicker'),   lambda icon, item: _send('quit')),
)

_icon = pystray.Icon('JJClicker', _make_icon(), 'JJClicker', menu)
_icon_ref[0] = _icon
sys.stderr.write('[tray] ready\n'); sys.stderr.flush()
_icon.run()
"""

DEFAULT_SHORTCUTS = {
    "start_recording": {"cmd": True,  "shift": False, "alt": False, "key": "r"},
    "toggle_playing":  {"cmd": True,  "shift": False, "alt": False, "key": "d"},
    "stop":            {"cmd": False, "shift": False, "alt": False, "key": "escape"},
}

# ── Translations ────────────────────────────────────────────────────────────

TRANSLATIONS = {
    'en': {
        # Tabs
        'tab_clicker':   '  Clicker  ',
        'tab_recorder':  '  Recorder  ',
        'tab_planner':   '  Planner  ',
        'tab_settings':  '  Settings  ',
        # Clicker tab — labels
        'pos_xy':        'Position (X, Y)',
        'click_type':    'Click type',
        'click_left':    'Left',
        'click_right':   'Right',
        'interval_ms':   'Interval (ms)',
        'repeat':        'Repeat',
        'infinite':      'Infinite',
        'count_lbl':     'Count:',
        # Clicker tab — buttons
        'btn_start':     '▶   Start',
        'btn_stop':      '⏹   Stop',
        'btn_capture':   'Capture',
        # Clicker status
        'status_ready':         'Ready',
        'status_move_mouse':    'Move mouse to target...',
        'status_capturing':     'Capturing in {n}s...',
        'status_set_pos':       'Set: {x}, {y}',
        'status_check_values':  'Check values!',
        'status_clicking':      'Clicking...',
        'status_stopped_clk':   'Stopped',
        'status_clicks':        'Clicks: {c}',
        'status_clicks_of':     'Clicks: {c} / {t}',
        'status_error':         'Error: {e}',
        # Recorder tab — buttons
        'btn_record':      '⏺   Record',
        'btn_stop_rec':    '⏹   Stop',
        'btn_play':        '▶   Play',
        'btn_stop_play':   '⏹   Stop',
        # Recorder tab — shortcut labels
        'sc_record_lbl':   'Record',
        'sc_play_stop':    'Play/Stop',
        'sc_stop_lbl':     'Stop',
        'sc_settings_lbl': 'edit',
        # Recorder tab — other labels
        'repeat_label':        'Repeat:',
        'pause_between':       'Pause between cycles:',
        'pause_none':          'None',
        'pause_fixed':         'Fixed',
        'pause_random':        'Random',
        # Recorder status
        'rec_status_ready':    'Ready',
        'status_starting':     'Starting...',
        'status_recording':    'Recording...',
        'status_stopping':     'Stopping...',
        'status_events':       'Events captured: {n}',
        'status_recorded':     'Recorded — {n} events, {d}s',
        'status_no_events':    '0 events — check System Settings → Privacy → Input Monitoring',
        'status_playing':      'Playing...',
        'status_cycle_pause':  'Cycle {n} done — pause {s}s',
        'status_cycle':        'Cycle: {n}',
        'status_error_msg':    'Error: {msg}',
        'status_all_done':     'All cycles done!',
        'notify_done':         '✓  All cycles done!',
        'status_stopped_rec':  'Stopped',
        # Recorder — template section
        'template_name':       'Template name',
        'btn_save':            'Save',
        'saved_templates':     'Saved templates',
        'btn_load':            'Load',
        'btn_delete':          'Delete',
        'status_select_tmpl':  'Select a template from the list',
        'status_loading':      'Loading...',
        'status_loaded':       'Loaded: {name} — {n} events, {d}s',
        'status_saving':       'Saving...',
        'status_saved':        'Saved: {name}',
        'status_enter_name':   'Enter template name',
        'status_nothing_rec':  'Nothing recorded',
        'status_deleted':      'Deleted: {name}',
        # Planner tab
        'planner_tmpl':        'Template:',
        'btn_add':             '+ Add',
        'task_order':          'Task order:',
        'btn_remove':          '✕ Remove',
        'pause_between_tasks': 'Pause between tasks:',
        'loop_label':          'Loop',
        'phases_label':        'Phases:',
        'phase_pause':         'Pause between phases:',
        'start_label':         'Start:',
        'start_now':           'Immediately',
        'start_at':            'At time:',
        'btn_start_plan':      '▶   Start plan',
        'btn_stop_plan':       '⏹   Stop',
        # Planner status
        'sched_ready':         'Ready',
        'sched_no_tasks':      'No tasks in plan',
        'sched_select_tmpl':   'Select template',
        'sched_starting':      'Starting...',
        'sched_stopped':       'Stopped',
        'sched_waiting':       'Waiting until {t} — remaining {r}',
        'sched_time_error':    'Time error: {e}',
        'sched_task':          'Task {i}/{total}: {name}  ×{r}{pt}',
        'sched_load_error':    'Load error: {e}',
        'sched_task_cycle':    'Task {i}/{total}: {name} — cycle {c}/{r}{pt}',
        'sched_pause_tasks':   'Pause between tasks — remaining {r:.1f}s',
        'sched_pause_phases':  'Pause between phases (phase {p}/{pl}) — remaining {t}',
        'sched_done':          'Plan complete!',
        'phase_tag_inf':       ' [phase {p}/∞]',
        'phase_tag_cnt':       ' [phase {p}/{c}]',
        # Settings tab
        'settings_shortcuts':  'Keyboard shortcuts',
        'sc_start_rec_lbl':    'Start recording',
        'sc_toggle_play_lbl':  'Play / Stop',
        'sc_stop_lbl2':        'Stop  (ESC)',
        'sc_hint':             'Click Change and then press a new keyboard shortcut.',
        'btn_reset_sc':        'Reset default shortcuts',
        'btn_change':          'Change',
        'btn_cancel':          'Cancel',
        'sc_press_keys':       'Press keys...',
        'settings_language':   'Language',
        'lang_english':        'English',
        'lang_slovak':         'Slovak',
        'lang_french':         'French',
        'lang_german':         'German',
        'lang_spanish':        'Spanish',
        # Planner — pause gap
        'btn_add_pause':       '+ Add Pause',
        'pause_gap_lbl':       'Pause:',
        'sched_pause_item':    '  ⏱  {d}s',
        'sched_running_pause': 'Pause gap — remaining {r:.1f}s',
        # Menu bar
        'menu_about':          'About JJClicker',
        'menu_open':           'Open JJClicker',
        'menu_record':         '⏺   Record  (⌘R)',
        'menu_play':           '▶   Play / Stop  (⌘D)',
        'menu_quit':           'Quit JJClicker',
    },
    'sk': {
        # Tabs
        'tab_clicker':   '  Klikač  ',
        'tab_recorder':  '  Nahrávač  ',
        'tab_planner':   '  Plánovač  ',
        'tab_settings':  '  Nastavenia  ',
        # Clicker tab — labels
        'pos_xy':        'Pozícia (X, Y)',
        'click_type':    'Typ kliku',
        'click_left':    'Ľavý',
        'click_right':   'Pravý',
        'interval_ms':   'Interval (ms)',
        'repeat':        'Opakovanie',
        'infinite':      'Nekonečné',
        'count_lbl':     'Počet:',
        # Clicker tab — buttons
        'btn_start':     '▶   Spustiť',
        'btn_stop':      '⏹   Zastaviť',
        'btn_capture':   'Zachytiť',
        # Clicker status
        'status_ready':         'Pripravený',
        'status_move_mouse':    'Presuň myš na cieľ...',
        'status_capturing':     'Zachytávam za {n}s...',
        'status_set_pos':       'Nastavené: {x}, {y}',
        'status_check_values':  'Skontroluj hodnoty!',
        'status_clicking':      'Klika...',
        'status_stopped_clk':   'Zastavený',
        'status_clicks':        'Klikov: {c}',
        'status_clicks_of':     'Klikov: {c} / {t}',
        'status_error':         'Chyba: {e}',
        # Recorder tab — buttons
        'btn_record':      '⏺   Nahrávať',
        'btn_stop_rec':    '⏹   Zastaviť',
        'btn_play':        '▶   Prehrať',
        'btn_stop_play':   '⏹   Zastaviť',
        # Recorder tab — shortcut labels
        'sc_record_lbl':   'Nahrávať',
        'sc_play_stop':    'Prehrať/Stop',
        'sc_stop_lbl':     'Zastaviť',
        'sc_settings_lbl': 'upraviť',
        # Recorder tab — other labels
        'repeat_label':        'Opakovanie:',
        'pause_between':       'Pauza medzi cyklami:',
        'pause_none':          'Žiadna',
        'pause_fixed':         'Fixná',
        'pause_random':        'Random',
        # Recorder status
        'rec_status_ready':    'Pripravený',
        'status_starting':     'Spúšťam...',
        'status_recording':    'Nahrávam...',
        'status_stopping':     'Zastavujem...',
        'status_events':       'Zachytených udalostí: {n}',
        'status_recorded':     'Nahrané — {n} udalostí, {d}s',
        'status_no_events':    '0 udalostí — skontroluj System Settings → Privacy → Input Monitoring',
        'status_playing':      'Prehráva...',
        'status_cycle_pause':  'Cyklus {n} hotový — pauza {s}s',
        'status_cycle':        'Cyklus: {n}',
        'status_error_msg':    'Chyba: {msg}',
        'status_all_done':     'Všetky cykly dokončené!',
        'notify_done':         '✓  Všetky cykly dokončené!',
        'status_stopped_rec':  'Zastavené',
        # Recorder — template section
        'template_name':       'Názov šablóny',
        'btn_save':            'Uložiť',
        'saved_templates':     'Uložené šablóny',
        'btn_load':            'Načítať',
        'btn_delete':          'Vymazať',
        'status_select_tmpl':  'Vyber šablónu zo zoznamu',
        'status_loading':      'Načítavam...',
        'status_loaded':       'Načítané: {name} — {n} udalostí, {d}s',
        'status_saving':       'Ukladám...',
        'status_saved':        'Uložené: {name}',
        'status_enter_name':   'Zadaj názov šablóny',
        'status_nothing_rec':  'Nič nie je nahrané',
        'status_deleted':      'Vymazané: {name}',
        # Planner tab
        'planner_tmpl':        'Šablóna:',
        'btn_add':             '+ Pridať',
        'task_order':          'Poradie úloh:',
        'btn_remove':          '✕ Odstrániť',
        'pause_between_tasks': 'Pauza medzi úlohami:',
        'loop_label':          'Zacykliť',
        'phases_label':        'Fáz:',
        'phase_pause':         'Pauza medzi fázami:',
        'start_label':         'Spustiť:',
        'start_now':           'Ihneď',
        'start_at':            'O čase:',
        'btn_start_plan':      '▶   Spustiť plán',
        'btn_stop_plan':       '⏹   Zastaviť',
        # Planner status
        'sched_ready':         'Pripravený',
        'sched_no_tasks':      'Žiadne úlohy v pláne',
        'sched_select_tmpl':   'Vyber šablónu',
        'sched_starting':      'Spúšťam...',
        'sched_stopped':       'Zastavené',
        'sched_waiting':       'Čakám do {t} — zostáva {r}',
        'sched_time_error':    'Chyba času: {e}',
        'sched_task':          'Úloha {i}/{total}: {name}  ×{r}{pt}',
        'sched_load_error':    'Chyba načítania: {e}',
        'sched_task_cycle':    'Úloha {i}/{total}: {name} — cyklus {c}/{r}{pt}',
        'sched_pause_tasks':   'Pauza medzi úlohami — zostáva {r:.1f}s',
        'sched_pause_phases':  'Pauza medzi fázami (fáza {p}/{pl}) — zostáva {t}',
        'sched_done':          'Plán dokončený!',
        'phase_tag_inf':       ' [fáza {p}/∞]',
        'phase_tag_cnt':       ' [fáza {p}/{c}]',
        # Settings tab
        'settings_shortcuts':  'Klávesové skratky',
        'sc_start_rec_lbl':    'Spustiť nahrávanie',
        'sc_toggle_play_lbl':  'Prehrať / Zastaviť',
        'sc_stop_lbl2':        'Zastaviť  (ESC)',
        'sc_hint':             'Klikni Zmeniť a potom stlač novú klávesovú skratku.',
        'btn_reset_sc':        'Obnoviť predvolené skratky',
        'btn_change':          'Zmeniť',
        'btn_cancel':          'Zrušiť',
        'sc_press_keys':       'Stlač klávesy...',
        'settings_language':   'Jazyk',
        'lang_english':        'Angličtina',
        'lang_slovak':         'Slovenčina',
        'lang_french':         'Francúzština',
        'lang_german':         'Nemčina',
        'lang_spanish':        'Španielčina',
        # Planner — pause gap
        'btn_add_pause':       '+ Pridať pauzu',
        'pause_gap_lbl':       'Pauza:',
        'sched_pause_item':    '  ⏱  {d}s',
        'sched_running_pause': 'Pauza — zostáva {r:.1f}s',
        # Menu bar
        'menu_about':          'O aplikácii JJClicker',
        'menu_open':           'Otvoriť JJClicker',
        'menu_record':         '⏺   Nahrávať  (⌘R)',
        'menu_play':           '▶   Prehrať / Stop  (⌘D)',
        'menu_quit':           'Ukončiť JJClicker',
    },

    'fr': {
        'tab_clicker': '  Clicker  ', 'tab_recorder': '  Enregistreur  ',
        'tab_planner': '  Planificateur  ', 'tab_settings': '  Paramètres  ',
        'pos_xy': 'Position (X, Y)', 'click_type': 'Type de clic',
        'click_left': 'Gauche', 'click_right': 'Droite',
        'interval_ms': 'Intervalle (ms)', 'repeat': 'Répétition',
        'infinite': 'Infini', 'count_lbl': 'Nombre:',
        'btn_start': '▶   Démarrer', 'btn_stop': '⏹   Arrêter', 'btn_capture': 'Capturer',
        'status_ready': 'Prêt', 'status_move_mouse': 'Déplacer la souris vers la cible...',
        'status_capturing': 'Capture dans {n}s...', 'status_set_pos': 'Défini: {x}, {y}',
        'status_check_values': 'Vérifier les valeurs!', 'status_clicking': 'En cours...',
        'status_stopped_clk': 'Arrêté', 'status_clicks': 'Clics: {c}',
        'status_clicks_of': 'Clics: {c} / {t}', 'status_error': 'Erreur: {e}',
        'btn_record': '⏺   Enregistrer', 'btn_stop_rec': '⏹   Arrêter',
        'btn_play': '▶   Lire', 'btn_stop_play': '⏹   Arrêter',
        'sc_record_lbl': 'Enregistrer', 'sc_play_stop': 'Lire/Stop',
        'sc_stop_lbl': 'Arrêter', 'sc_settings_lbl': 'modifier',
        'repeat_label': 'Répétition:', 'pause_between': 'Pause entre cycles:',
        'pause_none': 'Aucune', 'pause_fixed': 'Fixe', 'pause_random': 'Aléatoire',
        'rec_status_ready': 'Prêt', 'status_starting': 'Démarrage...',
        'status_recording': 'Enregistrement...', 'status_stopping': 'Arrêt...',
        'status_events': 'Événements capturés: {n}',
        'status_recorded': 'Enregistré — {n} événements, {d}s',
        'status_no_events': '0 événements — vérifier Préférences Système → Sécurité → Surveillance des entrées',
        'status_playing': 'Lecture...', 'status_cycle_pause': 'Cycle {n} terminé — pause {s}s',
        'status_cycle': 'Cycle: {n}', 'status_error_msg': 'Erreur: {msg}',
        'status_all_done': 'Tous les cycles terminés!',
        'notify_done': '✓  Tous les cycles terminés!', 'status_stopped_rec': 'Arrêté',
        'template_name': 'Nom du modèle', 'btn_save': 'Enregistrer',
        'saved_templates': 'Modèles enregistrés', 'btn_load': 'Charger', 'btn_delete': 'Supprimer',
        'status_select_tmpl': 'Sélectionner un modèle dans la liste',
        'status_loading': 'Chargement...',
        'status_loaded': 'Chargé: {name} — {n} événements, {d}s',
        'status_saving': 'Enregistrement...', 'status_saved': 'Enregistré: {name}',
        'status_enter_name': 'Entrer le nom du modèle',
        'status_nothing_rec': "Rien d'enregistré", 'status_deleted': 'Supprimé: {name}',
        'planner_tmpl': 'Modèle:', 'btn_add': '+ Ajouter',
        'task_order': 'Ordre des tâches:', 'btn_remove': '✕ Supprimer',
        'pause_between_tasks': 'Pause entre tâches:',
        'loop_label': 'Boucle', 'phases_label': 'Phases:', 'phase_pause': 'Pause entre phases:',
        'start_label': 'Démarrer:', 'start_now': 'Maintenant', 'start_at': "À l'heure:",
        'btn_start_plan': '▶   Démarrer le plan', 'btn_stop_plan': '⏹   Arrêter',
        'sched_ready': 'Prêt', 'sched_no_tasks': 'Aucune tâche dans le plan',
        'sched_select_tmpl': 'Sélectionner un modèle', 'sched_starting': 'Démarrage...',
        'sched_stopped': 'Arrêté',
        'sched_waiting': "Attente jusqu'à {t} — reste {r}",
        'sched_time_error': 'Erreur de temps: {e}',
        'sched_task': 'Tâche {i}/{total}: {name}  ×{r}{pt}',
        'sched_load_error': 'Erreur de chargement: {e}',
        'sched_task_cycle': 'Tâche {i}/{total}: {name} — cycle {c}/{r}{pt}',
        'sched_pause_tasks': 'Pause entre tâches — reste {r:.1f}s',
        'sched_pause_phases': 'Pause entre phases (phase {p}/{pl}) — reste {t}',
        'sched_done': 'Plan terminé!',
        'phase_tag_inf': ' [phase {p}/∞]', 'phase_tag_cnt': ' [phase {p}/{c}]',
        'settings_shortcuts': 'Raccourcis clavier',
        'sc_start_rec_lbl': "Démarrer l'enregistrement",
        'sc_toggle_play_lbl': 'Lire / Arrêter', 'sc_stop_lbl2': 'Arrêter  (ESC)',
        'sc_hint': 'Cliquez sur Modifier et appuyez sur le nouveau raccourci.',
        'btn_reset_sc': 'Réinitialiser les raccourcis',
        'btn_change': 'Modifier', 'btn_cancel': 'Annuler', 'sc_press_keys': 'Appuyer sur les touches...',
        'settings_language': 'Langue', 'lang_english': 'Anglais', 'lang_slovak': 'Slovaque',
        'lang_french': 'Français', 'lang_german': 'Allemand', 'lang_spanish': 'Espagnol',
        'btn_add_pause': '+ Ajouter pause', 'pause_gap_lbl': 'Pause:',
        'sched_pause_item': '  ⏱  {d}s', 'sched_running_pause': 'Pause — reste {r:.1f}s',
        'menu_about': 'À propos de JJClicker',
        'menu_open': 'Ouvrir JJClicker', 'menu_record': '⏺   Enregistrer  (⌘R)',
        'menu_play': '▶   Lire / Stop  (⌘D)', 'menu_quit': 'Quitter JJClicker',
    },
    'de': {
        'tab_clicker': '  Klicker  ', 'tab_recorder': '  Recorder  ',
        'tab_planner': '  Planer  ', 'tab_settings': '  Einstellungen  ',
        'pos_xy': 'Position (X, Y)', 'click_type': 'Klicktyp',
        'click_left': 'Links', 'click_right': 'Rechts',
        'interval_ms': 'Intervall (ms)', 'repeat': 'Wiederholung',
        'infinite': 'Unbegrenzt', 'count_lbl': 'Anzahl:',
        'btn_start': '▶   Starten', 'btn_stop': '⏹   Stoppen', 'btn_capture': 'Erfassen',
        'status_ready': 'Bereit', 'status_move_mouse': 'Maus zum Ziel bewegen...',
        'status_capturing': 'Erfasse in {n}s...', 'status_set_pos': 'Gesetzt: {x}, {y}',
        'status_check_values': 'Werte prüfen!', 'status_clicking': 'Klickt...',
        'status_stopped_clk': 'Gestoppt', 'status_clicks': 'Klicks: {c}',
        'status_clicks_of': 'Klicks: {c} / {t}', 'status_error': 'Fehler: {e}',
        'btn_record': '⏺   Aufnehmen', 'btn_stop_rec': '⏹   Stoppen',
        'btn_play': '▶   Abspielen', 'btn_stop_play': '⏹   Stoppen',
        'sc_record_lbl': 'Aufnehmen', 'sc_play_stop': 'Abspielen/Stop',
        'sc_stop_lbl': 'Stoppen', 'sc_settings_lbl': 'bearbeiten',
        'repeat_label': 'Wiederholung:', 'pause_between': 'Pause zwischen Zyklen:',
        'pause_none': 'Keine', 'pause_fixed': 'Fix', 'pause_random': 'Zufällig',
        'rec_status_ready': 'Bereit', 'status_starting': 'Starte...',
        'status_recording': 'Aufnahme...', 'status_stopping': 'Stoppe...',
        'status_events': 'Erfasste Ereignisse: {n}',
        'status_recorded': 'Aufgenommen — {n} Ereignisse, {d}s',
        'status_no_events': '0 Ereignisse — Systemeinstellungen → Datenschutz → Eingabeüberwachung prüfen',
        'status_playing': 'Wird abgespielt...', 'status_cycle_pause': 'Zyklus {n} fertig — Pause {s}s',
        'status_cycle': 'Zyklus: {n}', 'status_error_msg': 'Fehler: {msg}',
        'status_all_done': 'Alle Zyklen abgeschlossen!',
        'notify_done': '✓  Alle Zyklen abgeschlossen!', 'status_stopped_rec': 'Gestoppt',
        'template_name': 'Vorlagenname', 'btn_save': 'Speichern',
        'saved_templates': 'Gespeicherte Vorlagen', 'btn_load': 'Laden', 'btn_delete': 'Löschen',
        'status_select_tmpl': 'Vorlage aus Liste auswählen',
        'status_loading': 'Lade...',
        'status_loaded': 'Geladen: {name} — {n} Ereignisse, {d}s',
        'status_saving': 'Speichere...', 'status_saved': 'Gespeichert: {name}',
        'status_enter_name': 'Vorlagenname eingeben',
        'status_nothing_rec': 'Nichts aufgenommen', 'status_deleted': 'Gelöscht: {name}',
        'planner_tmpl': 'Vorlage:', 'btn_add': '+ Hinzufügen',
        'task_order': 'Aufgabenreihenfolge:', 'btn_remove': '✕ Entfernen',
        'pause_between_tasks': 'Pause zwischen Aufgaben:',
        'loop_label': 'Schleife', 'phases_label': 'Phasen:', 'phase_pause': 'Pause zwischen Phasen:',
        'start_label': 'Starten:', 'start_now': 'Sofort', 'start_at': 'Zur Zeit:',
        'btn_start_plan': '▶   Plan starten', 'btn_stop_plan': '⏹   Stoppen',
        'sched_ready': 'Bereit', 'sched_no_tasks': 'Keine Aufgaben im Plan',
        'sched_select_tmpl': 'Vorlage auswählen', 'sched_starting': 'Starte...',
        'sched_stopped': 'Gestoppt',
        'sched_waiting': 'Warte bis {t} — verbleibend {r}',
        'sched_time_error': 'Zeitfehler: {e}',
        'sched_task': 'Aufgabe {i}/{total}: {name}  ×{r}{pt}',
        'sched_load_error': 'Ladefehler: {e}',
        'sched_task_cycle': 'Aufgabe {i}/{total}: {name} — Zyklus {c}/{r}{pt}',
        'sched_pause_tasks': 'Pause zwischen Aufgaben — verbleibend {r:.1f}s',
        'sched_pause_phases': 'Pause zwischen Phasen (Phase {p}/{pl}) — verbleibend {t}',
        'sched_done': 'Plan abgeschlossen!',
        'phase_tag_inf': ' [Phase {p}/∞]', 'phase_tag_cnt': ' [Phase {p}/{c}]',
        'settings_shortcuts': 'Tastenkürzel',
        'sc_start_rec_lbl': 'Aufnahme starten',
        'sc_toggle_play_lbl': 'Abspielen / Stoppen', 'sc_stop_lbl2': 'Stoppen  (ESC)',
        'sc_hint': 'Klicke Ändern und drücke dann das neue Tastenkürzel.',
        'btn_reset_sc': 'Standardkürzel wiederherstellen',
        'btn_change': 'Ändern', 'btn_cancel': 'Abbrechen', 'sc_press_keys': 'Tasten drücken...',
        'settings_language': 'Sprache', 'lang_english': 'Englisch', 'lang_slovak': 'Slowakisch',
        'lang_french': 'Französisch', 'lang_german': 'Deutsch', 'lang_spanish': 'Spanisch',
        'btn_add_pause': '+ Pause hinzufügen', 'pause_gap_lbl': 'Pause:',
        'sched_pause_item': '  ⏱  {d}s', 'sched_running_pause': 'Pause — verbleibend {r:.1f}s',
        'menu_about': 'Über JJClicker',
        'menu_open': 'JJClicker öffnen', 'menu_record': '⏺   Aufnehmen  (⌘R)',
        'menu_play': '▶   Abspielen / Stop  (⌘D)', 'menu_quit': 'JJClicker beenden',
    },
    'es': {
        'tab_clicker': '  Clicker  ', 'tab_recorder': '  Grabador  ',
        'tab_planner': '  Planificador  ', 'tab_settings': '  Ajustes  ',
        'pos_xy': 'Posición (X, Y)', 'click_type': 'Tipo de clic',
        'click_left': 'Izquierdo', 'click_right': 'Derecho',
        'interval_ms': 'Intervalo (ms)', 'repeat': 'Repetición',
        'infinite': 'Infinito', 'count_lbl': 'Cantidad:',
        'btn_start': '▶   Iniciar', 'btn_stop': '⏹   Detener', 'btn_capture': 'Capturar',
        'status_ready': 'Listo', 'status_move_mouse': 'Mover el ratón al objetivo...',
        'status_capturing': 'Capturando en {n}s...', 'status_set_pos': 'Establecido: {x}, {y}',
        'status_check_values': '¡Verificar valores!', 'status_clicking': 'Haciendo clic...',
        'status_stopped_clk': 'Detenido', 'status_clicks': 'Clics: {c}',
        'status_clicks_of': 'Clics: {c} / {t}', 'status_error': 'Error: {e}',
        'btn_record': '⏺   Grabar', 'btn_stop_rec': '⏹   Detener',
        'btn_play': '▶   Reproducir', 'btn_stop_play': '⏹   Detener',
        'sc_record_lbl': 'Grabar', 'sc_play_stop': 'Reproducir/Stop',
        'sc_stop_lbl': 'Detener', 'sc_settings_lbl': 'editar',
        'repeat_label': 'Repetición:', 'pause_between': 'Pausa entre ciclos:',
        'pause_none': 'Ninguna', 'pause_fixed': 'Fija', 'pause_random': 'Aleatoria',
        'rec_status_ready': 'Listo', 'status_starting': 'Iniciando...',
        'status_recording': 'Grabando...', 'status_stopping': 'Deteniendo...',
        'status_events': 'Eventos capturados: {n}',
        'status_recorded': 'Grabado — {n} eventos, {d}s',
        'status_no_events': '0 eventos — verificar Ajustes del Sistema → Privacidad → Monitoreo de Entrada',
        'status_playing': 'Reproduciendo...', 'status_cycle_pause': 'Ciclo {n} completado — pausa {s}s',
        'status_cycle': 'Ciclo: {n}', 'status_error_msg': 'Error: {msg}',
        'status_all_done': '¡Todos los ciclos completados!',
        'notify_done': '✓  ¡Todos los ciclos completados!', 'status_stopped_rec': 'Detenido',
        'template_name': 'Nombre de plantilla', 'btn_save': 'Guardar',
        'saved_templates': 'Plantillas guardadas', 'btn_load': 'Cargar', 'btn_delete': 'Eliminar',
        'status_select_tmpl': 'Seleccionar una plantilla de la lista',
        'status_loading': 'Cargando...',
        'status_loaded': 'Cargado: {name} — {n} eventos, {d}s',
        'status_saving': 'Guardando...', 'status_saved': 'Guardado: {name}',
        'status_enter_name': 'Ingresar nombre de plantilla',
        'status_nothing_rec': 'Nada grabado', 'status_deleted': 'Eliminado: {name}',
        'planner_tmpl': 'Plantilla:', 'btn_add': '+ Agregar',
        'task_order': 'Orden de tareas:', 'btn_remove': '✕ Quitar',
        'pause_between_tasks': 'Pausa entre tareas:',
        'loop_label': 'Bucle', 'phases_label': 'Fases:', 'phase_pause': 'Pausa entre fases:',
        'start_label': 'Iniciar:', 'start_now': 'Ahora', 'start_at': 'A las:',
        'btn_start_plan': '▶   Iniciar plan', 'btn_stop_plan': '⏹   Detener',
        'sched_ready': 'Listo', 'sched_no_tasks': 'No hay tareas en el plan',
        'sched_select_tmpl': 'Seleccionar plantilla', 'sched_starting': 'Iniciando...',
        'sched_stopped': 'Detenido',
        'sched_waiting': 'Esperando hasta {t} — quedan {r}',
        'sched_time_error': 'Error de tiempo: {e}',
        'sched_task': 'Tarea {i}/{total}: {name}  ×{r}{pt}',
        'sched_load_error': 'Error de carga: {e}',
        'sched_task_cycle': 'Tarea {i}/{total}: {name} — ciclo {c}/{r}{pt}',
        'sched_pause_tasks': 'Pausa entre tareas — quedan {r:.1f}s',
        'sched_pause_phases': 'Pausa entre fases (fase {p}/{pl}) — quedan {t}',
        'sched_done': '¡Plan completado!',
        'phase_tag_inf': ' [fase {p}/∞]', 'phase_tag_cnt': ' [fase {p}/{c}]',
        'settings_shortcuts': 'Atajos de teclado',
        'sc_start_rec_lbl': 'Iniciar grabación',
        'sc_toggle_play_lbl': 'Reproducir / Detener', 'sc_stop_lbl2': 'Detener  (ESC)',
        'sc_hint': 'Haz clic en Cambiar y luego presiona el nuevo atajo.',
        'btn_reset_sc': 'Restablecer atajos predeterminados',
        'btn_change': 'Cambiar', 'btn_cancel': 'Cancelar', 'sc_press_keys': 'Presionar teclas...',
        'settings_language': 'Idioma', 'lang_english': 'Inglés', 'lang_slovak': 'Eslovaco',
        'lang_french': 'Francés', 'lang_german': 'Alemán', 'lang_spanish': 'Español',
        'btn_add_pause': '+ Agregar pausa', 'pause_gap_lbl': 'Pausa:',
        'sched_pause_item': '  ⏱  {d}s', 'sched_running_pause': 'Pausa — quedan {r:.1f}s',
        'menu_about': 'Acerca de JJClicker',
        'menu_open': 'Abrir JJClicker', 'menu_record': '⏺   Grabar  (⌘R)',
        'menu_play': '▶   Reproducir / Stop  (⌘D)', 'menu_quit': 'Salir de JJClicker',
    },
}

# ─────────────────────────────────────────────────────────────────────────────

_SCREEN_SIZE_CACHE = None

if IS_MACOS:
    _HID_SOURCE = CGEventSourceCreate(kCGEventSourceStateHIDSystemState)

    # macOS virtual key codes for arrow keys + left Control
    _VK_CTRL  = 59
    _VK_UP    = 126
    _VK_DOWN  = 125
    _VK_LEFT  = 123
    _VK_RIGHT = 124

    _GESTURE_VKEYS = {
        'up':    _VK_UP,
        'down':  _VK_DOWN,
        'left':  _VK_RIGHT,   # swipe left → next space = Ctrl+Right
        'right': _VK_LEFT,    # swipe right → prev space = Ctrl+Left
    }


def _play_gesture(direction):
    if not IS_MACOS:
        return  # no virtual desktop gestures on Windows
    vk = _GESTURE_VKEYS.get(direction)
    if vk is None:
        return
    for key, down, flags in [
        (_VK_CTRL, True,  0),
        (vk,       True,  kCGEventFlagMaskControl),
        (vk,       False, kCGEventFlagMaskControl),
        (_VK_CTRL, False, 0),
    ]:
        ev = CGEventCreateKeyboardEvent(_HID_SOURCE, key, down)
        CGEventSetFlags(ev, flags)
        CGEventPost(kCGHIDEventTap, ev)
    time.sleep(0.7)


def _get_screen_size():
    global _SCREEN_SIZE_CACHE
    if _SCREEN_SIZE_CACHE is not None:
        return _SCREEN_SIZE_CACHE
    if IS_MACOS:
        bounds = CGDisplayBounds(CGMainDisplayID())
        _SCREEN_SIZE_CACHE = (int(bounds.size.width), int(bounds.size.height))
    else:
        _SCREEN_SIZE_CACHE = (
            ctypes.windll.user32.GetSystemMetrics(0),
            ctypes.windll.user32.GetSystemMetrics(1),
        )
    return _SCREEN_SIZE_CACHE


def _dock_show():
    if not IS_MACOS:
        return
    subprocess.run(
        ["osascript", "-e",
         'tell application "System Events" to set autohide of dock preferences to false'],
        capture_output=True
    )
    time.sleep(0.45)


def _dock_hide():
    if not IS_MACOS:
        return
    subprocess.run(
        ["osascript", "-e",
         'tell application "System Events" to set autohide of dock preferences to true'],
        capture_output=True
    )


def _mouse_move(x, y):
    if IS_MACOS:
        CGWarpMouseCursorPosition(CGPoint(x, y))
        ev = CGEventCreateMouseEvent(_HID_SOURCE, kCGEventMouseMoved, CGPoint(x, y), kCGMouseButtonLeft)
        CGEventPost(kCGHIDEventTap, ev)
    else:
        ctypes.windll.user32.SetCursorPos(int(x), int(y))


def _mouse_release_all():
    if IS_MACOS:
        from Quartz.CoreGraphics import CGEventGetLocation, CGEventCreate
        loc = CGEventGetLocation(CGEventCreate(None))
        for ev_type, btn in [(kCGEventLeftMouseUp,  kCGMouseButtonLeft),
                             (kCGEventRightMouseUp, kCGMouseButtonRight)]:
            ev = CGEventCreateMouseEvent(_HID_SOURCE, ev_type, loc, btn)
            CGEventPost(kCGHIDEventTap, ev)
    else:
        ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)  # LEFTUP
        ctypes.windll.user32.mouse_event(0x0010, 0, 0, 0, 0)  # RIGHTUP


def _mouse_click(x, y, button, pressed):
    if IS_MACOS:
        _, sh = _get_screen_size()
        if button == 'left' and y >= sh - 80:
            if pressed:
                CGWarpMouseCursorPosition(CGPoint(x, y))
                subprocess.run(
                    ["osascript", "-e",
                     f'tell application "System Events" to click at {{{int(x)}, {int(y)}}}'],
                    capture_output=True
                )
            return
        CGWarpMouseCursorPosition(CGPoint(x, y))
        if button == 'left':
            ev_type = kCGEventLeftMouseDown if pressed else kCGEventLeftMouseUp
            btn_id  = kCGMouseButtonLeft
        else:
            ev_type = kCGEventRightMouseDown if pressed else kCGEventRightMouseUp
            btn_id  = kCGMouseButtonRight
        ev = CGEventCreateMouseEvent(_HID_SOURCE, ev_type, CGPoint(x, y), btn_id)
        CGEventPost(kCGHIDEventTap, ev)
    else:
        ctypes.windll.user32.SetCursorPos(int(x), int(y))
        if button == 'left':
            flag = 0x0002 if pressed else 0x0004   # LEFTDOWN / LEFTUP
        else:
            flag = 0x0008 if pressed else 0x0010   # RIGHTDOWN / RIGHTUP
        ctypes.windll.user32.mouse_event(flag, 0, 0, 0, 0)


# Keep old names as aliases so MacroRecorder.play() calls still work
_quartz_move        = _mouse_move
_quartz_click       = _mouse_click
_quartz_release_all = _mouse_release_all

BG     = "#1e1e2e"
FG     = "#cdd6f4"
ACC    = "#89b4fa"
GREEN  = "#a6e3a1"
RED    = "#f38ba8"
YELLOW = "#f9e2af"
PANEL  = "#313244"
MUTED  = "#6c7086"


class MacroRecorder:
    MOVE_THRESHOLD = 4

    def __init__(self):
        self.events = []
        self._recording = False
        self._start_time = None
        self._listener = None
        self._last_pos = None

    def start(self):
        self.events = []
        self._recording = True
        self._start_time = time.perf_counter()
        self._last_pos = None
        self._listener = pynput_mouse.Listener(
            on_move=self._on_move,
            on_click=self._on_click
        )
        self._listener.start()

    def stop(self):
        self._recording = False
        if self._listener:
            self._listener.stop()
            self._listener = None

    def _t(self):
        return time.perf_counter() - self._start_time

    def _on_move(self, x, y):
        if not self._recording:
            return
        if self._last_pos:
            lx, ly = self._last_pos
            if abs(x - lx) < self.MOVE_THRESHOLD and abs(y - ly) < self.MOVE_THRESHOLD:
                return
        self._last_pos = (x, y)
        self.events.append({'type': 'move', 'x': x, 'y': y, 't': self._t()})

    def _on_click(self, x, y, button, pressed):
        if not self._recording:
            return
        self.events.append({
            'type': 'click',
            'x': x, 'y': y,
            'button': button.name,
            'pressed': pressed,
            't': self._t()
        })

    def play(self, stop_event, repeat=1, on_count=None, on_error=None):
        if not self.events:
            return
        _, sh = _get_screen_size()
        dock_zone_y = sh - 80
        needs_dock = any(ev['type'] == 'move' and ev['y'] >= dock_zone_y
                         for ev in self.events)
        if needs_dock:
            _dock_show()
        try:
            for r in range(repeat):
                if stop_event.is_set():
                    break
                ref = time.perf_counter()
                for ev in self.events:
                    if stop_event.is_set():
                        return
                    wait = ev['t'] - (time.perf_counter() - ref)
                    if wait > 0:
                        deadline = time.perf_counter() + wait
                        while time.perf_counter() < deadline:
                            if stop_event.is_set():
                                return
                            time.sleep(min(0.05, deadline - time.perf_counter()))
                    try:
                        if ev['type'] == 'move':
                            _quartz_move(ev['x'], ev['y'])
                        elif ev['type'] == 'click':
                            _quartz_click(ev['x'], ev['y'], ev['button'], ev['pressed'])
                        elif ev['type'] == 'gesture':
                            _play_gesture(ev['direction'])
                    except Exception as e:
                        if on_error:
                            on_error(str(e))
                        return
                if on_count:
                    on_count(r + 1)
        finally:
            if needs_dock:
                _dock_hide()

    def save(self, name):
        path = TEMPLATES_DIR / f"{name}.json"
        data = {'name': name, 'events': self.events, 'duration': self.duration()}
        with open(path, 'w') as f:
            json.dump(data, f)

    def load(self, name):
        path = TEMPLATES_DIR / f"{name}.json"
        with open(path) as f:
            self.events = json.load(f)['events']

    def duration(self):
        return self.events[-1]['t'] if self.events else 0

    @staticmethod
    def list_templates():
        return sorted(p.stem for p in TEMPLATES_DIR.glob("*.json"))

    @staticmethod
    def delete(name):
        (TEMPLATES_DIR / f"{name}.json").unlink(missing_ok=True)




class JJClicker:
    def __init__(self, root):
        self.root = root
        self.root.title("JJClicker")
        self.root.resizable(True, True)
        self.root.configure(bg=BG)

        self._clicking = False
        self._click_thread = None
        self._recorder = MacroRecorder()
        self._recording = False
        self._playing = False
        self._play_stop = threading.Event()
        self._play_thread = None

        self._sched_tasks = []
        self._sched_running = False
        self._sched_stop = threading.Event()
        self._sched_recorder = MacroRecorder()

        self._gesture_monitor = None

        # Translatable-widget registry: list of (widget, key, attr)
        # attr is 'text' for most widgets, 'values' for combobox, etc.
        self._tw = []

        # Settings & shortcut capture
        self._settings = dict(DEFAULT_SHORTCUTS)
        self._load_settings()
        self._capturing_action = None
        self._capturing_label  = None
        self._capturing_btn    = None

        self._setup_styles()
        self._build_ui()
        self._track_mouse()
        self._start_kb_listener()
        if IS_MACOS:
            self._pump_appkit_events()
        # Delay tray/menu-bar setup until mainloop is running
        self.root.after(300, self._setup_status_bar)

        # Close button (⨯) hides the window instead of quitting
        self.root.protocol("WM_DELETE_WINDOW", self._on_window_close)

        # Dock → Quit (SIGTERM): kill helper directly then exit — do NOT call
        # tkinter methods from a signal handler (unsafe); just murder the process.
        import signal as _sig, atexit
        def _on_sigterm(*_):
            self._kill_helper_now()
            sys.exit(0)
        _sig.signal(_sig.SIGTERM, _on_sigterm)
        atexit.register(self._kill_helper_now)

    def _on_window_close(self):
        """Red ⨯ button — minimize to Dock instead of quitting."""
        self.root.iconify()

    def _kill_helper_now(self):
        """Kill the helper immediately — safe to call from signal handlers or atexit."""
        import os, signal as _sig
        proc = getattr(self, '_mb_proc', None)
        if proc and proc.poll() is None:
            try: proc.kill()
            except Exception: pass
        self._mb_proc = None
        try:
            pid = int(self._MB_PID_FILE.read_text().strip())
            try:
                if IS_WINDOWS:
                    os.kill(pid, _sig.SIGTERM)
                else:
                    os.kill(pid, _sig.SIGKILL)
            except (ProcessLookupError, OSError): pass
        except Exception: pass
        try: self._MB_PID_FILE.unlink(missing_ok=True)
        except Exception: pass

    def _quit_app(self):
        self._kill_helper_now()
        self.root.quit()

    # ── Language helpers ────────────────────────────────────────

    def _t(self, key):
        """Return translated string for key in current language."""
        lang = self._settings.get('language', 'en')
        d = TRANSLATIONS.get(lang, TRANSLATIONS['en'])
        return d.get(key, TRANSLATIONS['en'].get(key, key))

    def _r(self, widget, key, attr='text'):
        """Register widget for language updates; return widget."""
        self._tw.append((widget, key, attr))
        return widget

    def _apply_language(self):
        """Update all registered widgets to the current language."""
        for widget, key, attr in self._tw:
            try:
                widget.config(**{attr: self._t(key)})
            except Exception:
                pass
        # Update notebook tab names
        try:
            self._nb.tab(0, text=self._t('tab_clicker'))
            self._nb.tab(1, text=self._t('tab_recorder'))
            self._nb.tab(2, text=self._t('tab_planner'))
            self._nb.tab(3, text=self._t('tab_settings'))
        except Exception:
            pass
        # Reset status labels to their "ready" defaults if currently idle
        try:
            if not self._clicking:
                self.click_status_var.set(self._t('status_ready'))
        except Exception:
            pass
        try:
            if not self._recording and not self._playing:
                self.rec_status_var.set(self._t('rec_status_ready'))
        except Exception:
            pass
        try:
            if not self._sched_running:
                self.sched_status_var.set(self._t('sched_ready'))
        except Exception:
            pass
        # Rebuild menu bar with new language
        try:
            self._setup_status_bar()
        except Exception:
            pass

    # ── AppKit pump (macOS only) ─────────────────────────────────

    def _pump_appkit_events(self):
        if not IS_MACOS:
            return
        try:
            AppKit.NSRunLoop.currentRunLoop().runMode_beforeDate_(
                "NSDefaultRunLoopMode",
                AppKit.NSDate.dateWithTimeIntervalSinceNow_(0.0)
            )
        except Exception:
            pass
        self.root.after(50, self._pump_appkit_events)

    def _on_gesture(self, event):
        if not self._recording:
            return
        try:
            dx = event.deltaX()
            dy = event.deltaY()
            if abs(dy) >= abs(dx):
                direction = 'up' if dy < 0 else 'down'
            else:
                direction = 'left' if dx < 0 else 'right'
            self._recorder.events.append({
                'type': 'gesture', 'direction': direction, 't': self._recorder._t()
            })
        except Exception:
            pass

    def _setup_styles(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure(".", background=BG, foreground=FG, fieldbackground=PANEL,
                    bordercolor=PANEL, darkcolor=PANEL, lightcolor=PANEL,
                    troughcolor=PANEL, font=("Helvetica", 15))
        s.configure("TFrame", background=BG)
        s.configure("TNotebook", background=BG, borderwidth=0, tabmargins=0)
        s.configure("TNotebook.Tab", background=PANEL, foreground=MUTED, padding=(16, 8))
        s.map("TNotebook.Tab",
              background=[("selected", BG)],
              foreground=[("selected", ACC)])
        s.configure("TRadiobutton", background=BG, foreground=FG, focuscolor=BG)
        s.map("TRadiobutton", indicatorcolor=[("selected", ACC)])
        s.configure("TCheckbutton", background=BG, foreground=FG, focuscolor=BG)
        s.map("TCheckbutton", indicatorcolor=[("selected", ACC)])

        for name, bg, fg, abg in [
            ("Start",  ACC,       BG,  "#7aa2f7"),
            ("Stop",   RED,       BG,  "#e06c75"),
            ("Record", RED,       BG,  "#e06c75"),
            ("Play",   GREEN,     BG,  "#7dc88a"),
            ("Pick",   PANEL,     ACC, "#45475a"),
            ("Save",   ACC,       BG,  "#7aa2f7"),
            ("Del",    "#45475a", RED, "#313244"),
            ("Load",   PANEL,     ACC, "#45475a"),
            ("Sched",  ACC,       BG,  "#7aa2f7"),
            ("Up",     PANEL,     FG,  "#45475a"),
            ("Down",   PANEL,     FG,  "#45475a"),
        ]:
            s.configure(f"{name}.TButton", background=bg, foreground=fg,
                        font=("Helvetica", 15, "bold"), borderwidth=0,
                        relief="flat", padding=(10, 7))
            s.map(f"{name}.TButton", background=[("active", abg)])

    def _entry(self, parent, var, width=10, numeric=True):
        e = tk.Entry(parent, textvariable=var, width=width, bg=PANEL, fg=YELLOW,
                     insertbackground=YELLOW, relief="flat", font=("Helvetica", 15),
                     highlightthickness=1, highlightbackground="#45475a")
        if numeric:
            vcmd = (self.root.register(lambda P: P == '' or P.replace('.', '', 1).isdigit()), '%P')
            e.config(validate='key', validatecommand=vcmd)
        return e

    def _lbl(self, parent, key_or_text, fg=None, size=12, translate=True):
        text = self._t(key_or_text) if translate else key_or_text
        w = tk.Label(parent, text=text, bg=BG, fg=fg or FG,
                     font=("Helvetica", size + 3))
        if translate:
            self._tw.append((w, key_or_text, 'text'))
        return w

    def _sep(self, parent, row):
        tk.Frame(parent, bg="#45475a", height=1).grid(
            row=row, column=0, columnspan=3, sticky="ew", pady=12)

    def _build_logo(self):
        W, H = 300, 82
        c = tk.Canvas(self.root, width=W, height=H, bg=BG, highlightthickness=0)
        c.grid(row=0, column=0, pady=(18, 2))

        # ── Badge ─────────────────────────────────────────────────
        # Outer subtle glow ring
        self._rounded_rect(c, 1, 3, 97, 67, 16, fill="#252537", outline="")
        # Main badge body
        self._rounded_rect(c, 3, 5, 95, 65, 14, fill="#1c1c2e", outline="")
        # Top half highlight for depth
        self._rounded_rect(c, 3, 5, 95, 36, 14, fill="#23233a", outline="")

        # Colored bracket ornaments  [ JJ ]
        c.create_line(15, 17, 10, 17, 10, 53, 15, 53, fill=ACC, width=2, joinstyle="miter")
        c.create_line(83, 17, 88, 17, 88, 53, 83, 53, fill=RED, width=2, joinstyle="miter")

        # "JJ" — clean Helvetica Bold
        c.create_text(34, 37, text="J", font=("Helvetica", 38, "bold"), fill=ACC, anchor="center")
        c.create_text(64, 37, text="J", font=("Helvetica", 38, "bold"), fill=RED, anchor="center")

        # Small dot between letters
        c.create_oval(46, 33, 51, 38, fill="#45475a", outline="")

        # ── Right section ─────────────────────────────────────────
        # Vertical divider
        c.create_line(108, 14, 108, 62, fill="#3a3a54", width=1)

        # "clicker" — bold, full brightness
        c.create_text(118, 28, text="clicker", font=("Helvetica", 22, "bold"), fill=FG, anchor="w")

        # Subtitle — muted, small
        c.create_text(118, 52, text="macro automation", font=("Helvetica", 11), fill=MUTED, anchor="w")

        # ── Bottom gradient accent line ───────────────────────────
        steps = 40
        x1, x2, y = 3, W - 3, H - 8
        for i in range(steps):
            t  = i / steps
            r  = int(0x89 + t * (0xf3 - 0x89))
            g  = int(0xb4 + t * (0x8b - 0xb4))
            b  = int(0xfa + t * (0xa8 - 0xfa))
            sx = int(x1 + t * (x2 - x1))
            ex = int(x1 + (i + 1) / steps * (x2 - x1))
            c.create_line(sx, y, ex, y, fill=f"#{r:02x}{g:02x}{b:02x}", width=2)

    @staticmethod
    def _rounded_rect(canvas, x1, y1, x2, y2, r, **kw):
        pts = [
            x1+r, y1,   x2-r, y1,
            x2,   y1,   x2,   y1+r,
            x2,   y2-r, x2,   y2,
            x2-r, y2,   x1+r, y2,
            x1,   y2,   x1,   y2-r,
            x1,   y1+r, x1,   y1,
        ]
        canvas.create_polygon(pts, smooth=True, **kw)

    def _build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)

        self._build_logo()

        self.mouse_var = tk.StringVar(value="x: 0   y: 0")
        tk.Label(self.root, textvariable=self.mouse_var, bg=PANEL, fg=MUTED,
                 font=("Helvetica", 14), padx=10, pady=4).grid(
            row=1, column=0, sticky="ew", padx=24, pady=(0, 10))

        self._nb = ttk.Notebook(self.root)
        self._nb.grid(row=2, column=0, sticky="nsew", padx=24, pady=(0, 20))

        t1 = ttk.Frame(self._nb, padding=(16, 14))
        t2 = ttk.Frame(self._nb, padding=(16, 14))
        t3 = ttk.Frame(self._nb, padding=(16, 14))
        t4 = ttk.Frame(self._nb, padding=(16, 14))
        self._nb.add(t1, text=self._t('tab_clicker'))
        self._nb.add(t2, text=self._t('tab_recorder'))
        self._nb.add(t3, text=self._t('tab_planner'))
        self._nb.add(t4, text=self._t('tab_settings'))

        for tab in (t1, t2, t3, t4):
            tab.columnconfigure(0, weight=1)

        self._build_clicker_tab(t1)
        self._build_recorder_tab(t2)
        self._build_scheduler_tab(t3)
        self._build_settings_tab(t4)

    # ── Clicker tab ────────────────────────────────────────────

    def _build_clicker_tab(self, p):
        pad = dict(padx=4, pady=5)

        self._lbl(p, 'pos_xy').grid(row=0, column=0, sticky="w", **pad)
        cf = ttk.Frame(p)
        cf.grid(row=0, column=1, sticky="w", **pad)
        self.x_var = tk.StringVar(value="0")
        self.y_var = tk.StringVar(value="0")
        self._entry(cf, self.x_var, 6).pack(side="left")
        tk.Label(cf, text="  ,  ", bg=BG, fg=MUTED, font=("Helvetica", 15)).pack(side="left")
        self._entry(cf, self.y_var, 6).pack(side="left")
        self._r(ttk.Button(p, text=self._t('btn_capture'), style="Pick.TButton",
                           command=self._pick_location), 'btn_capture').grid(
            row=0, column=2, padx=(8, 0), pady=5)

        self._lbl(p, 'click_type').grid(row=1, column=0, sticky="w", **pad)
        self.click_type = tk.StringVar(value="left")
        ctf = ttk.Frame(p)
        ctf.grid(row=1, column=1, columnspan=2, sticky="w", **pad)
        self._r(ttk.Radiobutton(ctf, text=self._t('click_left'), variable=self.click_type,
                                value="left"), 'click_left').pack(side="left", padx=(0, 12))
        self._r(ttk.Radiobutton(ctf, text=self._t('click_right'), variable=self.click_type,
                                value="right"), 'click_right').pack(side="left")

        self._lbl(p, 'interval_ms').grid(row=2, column=0, sticky="w", **pad)
        ivf = ttk.Frame(p)
        ivf.grid(row=2, column=1, columnspan=2, sticky="w", **pad)
        self.interval_var = tk.StringVar(value="1000")
        self._entry(ivf, self.interval_var, 8).pack(side="left")
        tk.Label(ivf, text="  ms", bg=BG, fg=MUTED, font=("Helvetica", 14)).pack(side="left")

        self._lbl(p, 'repeat').grid(row=3, column=0, sticky="w", **pad)
        rpf = ttk.Frame(p)
        rpf.grid(row=3, column=1, columnspan=2, sticky="w", **pad)
        self.repeat_type = tk.StringVar(value="infinite")
        self._r(ttk.Radiobutton(rpf, text=self._t('infinite'), variable=self.repeat_type,
                                value="infinite", command=self._toggle_repeat), 'infinite').pack(
            side="left", padx=(0, 12))
        self._r(ttk.Radiobutton(rpf, text=self._t('count_lbl'), variable=self.repeat_type,
                                value="count", command=self._toggle_repeat), 'count_lbl').pack(
            side="left")
        self.repeat_count = tk.StringVar(value="10")
        self.repeat_entry = self._entry(rpf, self.repeat_count, 5)
        self.repeat_entry.config(state="disabled", fg=MUTED)
        self.repeat_entry.pack(side="left", padx=(6, 0))

        self._sep(p, 4)

        self.click_btn = self._r(ttk.Button(p, text=self._t('btn_start'), style="Start.TButton",
                                            command=self._toggle_clicking, width=20), 'btn_start')
        self.click_btn.grid(row=5, column=0, columnspan=3, pady=(0, 8))

        self.click_status_var = tk.StringVar(value=self._t('status_ready'))
        self.click_status_lbl = tk.Label(p, textvariable=self.click_status_var,
                                         bg=BG, fg=MUTED, font=("Helvetica", 14))
        self.click_status_lbl.grid(row=6, column=0, columnspan=3)

        self.click_counter_var = tk.StringVar(value="")
        tk.Label(p, textvariable=self.click_counter_var, bg=BG, fg=GREEN,
                 font=("Helvetica", 14, "bold")).grid(row=7, column=0, columnspan=3, pady=(2, 0))

    def _toggle_repeat(self):
        if self.repeat_type.get() == "count":
            self.repeat_entry.config(state="normal", fg=YELLOW)
        else:
            self.repeat_entry.config(state="disabled", fg=MUTED)

    def _pick_location(self):
        self._set_click_status(self._t('status_move_mouse'), YELLOW)
        self.root.after(100, self._countdown, 3)

    def _countdown(self, n):
        if n > 0:
            self._set_click_status(self._t('status_capturing').format(n=n), YELLOW)
            self.root.after(1000, self._countdown, n - 1)
        else:
            from Quartz.CoreGraphics import CGEventCreate, CGEventGetLocation
            loc = CGEventGetLocation(CGEventCreate(None))
            x, y = int(loc.x), int(loc.y)
            self.x_var.set(str(x))
            self.y_var.set(str(y))
            self._set_click_status(self._t('status_set_pos').format(x=x, y=y), GREEN)

    def _set_click_status(self, text, color=MUTED):
        self.click_status_var.set(text)
        self.click_status_lbl.config(fg=color)

    def _toggle_clicking(self):
        if self._clicking:
            self._stop_clicking()
        else:
            self._start_clicking()

    def _start_clicking(self):
        try:
            x = int(self.x_var.get())
            y = int(self.y_var.get())
            interval = int(self.interval_var.get()) / 1000.0
        except ValueError:
            self._set_click_status(self._t('status_check_values'), RED)
            return
        self._clicking = True
        self.click_btn.config(text=self._t('btn_stop'), style="Stop.TButton")
        self._set_click_status(self._t('status_clicking'), GREEN)
        self._click_thread = threading.Thread(
            target=self._click_loop, args=(x, y, interval), daemon=True)
        self._click_thread.start()

    def _stop_clicking(self):
        self._clicking = False
        self.click_btn.config(text=self._t('btn_start'), style="Start.TButton")
        self._set_click_status(self._t('status_stopped_clk'))
        self.click_counter_var.set("")

    def _click_loop(self, x, y, interval):
        btn = self.click_type.get()
        infinite = self.repeat_type.get() == "infinite"
        total = int(self.repeat_count.get()) if not infinite else None
        count = 0
        while self._clicking:
            try:
                _quartz_click(x, y, btn, True)
                time.sleep(0.05)
                _quartz_click(x, y, btn, False)
            except Exception as e:
                self.root.after(0, self._set_click_status,
                                self._t('status_error').format(e=e), RED)
                self.root.after(0, self._stop_clicking)
                return
            count += 1
            if count % 5 == 0 or count == 1:
                if infinite:
                    self.root.after(0, lambda c=count:
                                    self.click_counter_var.set(self._t('status_clicks').format(c=c)))
                else:
                    self.root.after(0, lambda c=count, t=total:
                                    self.click_counter_var.set(
                                        self._t('status_clicks_of').format(c=c, t=t)))
            if not infinite and count >= total:
                self.root.after(0, lambda c=count, t=total:
                                self.click_counter_var.set(
                                    self._t('status_clicks_of').format(c=c, t=t)))
                self.root.after(0, self._stop_clicking)
                return
            time.sleep(interval)

    # ── Recorder tab ───────────────────────────────────────────

    def _build_recorder_tab(self, p):
        p.rowconfigure(10, weight=1)
        p.columnconfigure(0, weight=1)
        p.columnconfigure(1, weight=1)
        p.columnconfigure(2, weight=1)
        pad = dict(padx=4, pady=5)

        btn_f = ttk.Frame(p)
        btn_f.grid(row=0, column=0, columnspan=3, pady=(0, 4))
        self.rec_btn = self._r(
            ttk.Button(btn_f, text=self._t('btn_record'), style="Record.TButton",
                       command=self._toggle_recording, width=14), 'btn_record')
        self.rec_btn.pack(side="left", padx=(0, 8))
        self.play_btn = self._r(
            ttk.Button(btn_f, text=self._t('btn_play'), style="Play.TButton",
                       command=self._toggle_playing, width=14, state="disabled"), 'btn_play')
        self.play_btn.pack(side="left")

        # keyboard shortcuts legend
        sc_f = ttk.Frame(p)
        sc_f.grid(row=3, column=0, columnspan=3, sticky="w", pady=(2, 0))
        sc_pairs = [
            ("⌘R", 'sc_record_lbl'),
            ("⌘D", 'sc_play_stop'),
            ("ESC", 'sc_stop_lbl'),
            ("→ Settings", 'sc_settings_lbl'),
        ]
        self._sc_legend_labels = []
        for key_text, desc_key in sc_pairs:
            tk.Label(sc_f, text=key_text, bg=PANEL, fg=ACC,
                     font=("Helvetica", 11, "bold"), padx=5, pady=1).pack(side="left", padx=(6, 1))
            desc_lbl = tk.Label(sc_f, text=self._t(desc_key), bg=BG, fg=MUTED,
                                font=("Helvetica", 11))
            desc_lbl.pack(side="left", padx=(0, 4))
            self._tw.append((desc_lbl, desc_key, 'text'))

        rp_f = ttk.Frame(p)
        rp_f.grid(row=1, column=0, columnspan=3, sticky="w", **pad)
        self._lbl(rp_f, 'repeat_label').pack(side="left", padx=(0, 8))
        self.play_repeat_type = tk.StringVar(value="count")
        self._r(ttk.Radiobutton(rp_f, text=self._t('infinite'), variable=self.play_repeat_type,
                                value="infinite", command=self._toggle_play_repeat),
                'infinite').pack(side="left", padx=(0, 8))
        self._r(ttk.Radiobutton(rp_f, text=self._t('count_lbl'), variable=self.play_repeat_type,
                                value="count", command=self._toggle_play_repeat),
                'count_lbl').pack(side="left")
        self.play_repeat_count = tk.StringVar(value="3")
        self.play_repeat_entry = self._entry(rp_f, self.play_repeat_count, 4)
        self.play_repeat_entry.config(state="normal", fg=YELLOW)
        self.play_repeat_entry.pack(side="left", padx=(6, 0))

        pz_f = ttk.Frame(p)
        pz_f.grid(row=2, column=0, columnspan=3, sticky="w", **pad)
        self._lbl(pz_f, 'pause_between').pack(side="left", padx=(0, 8))
        self.pause_type = tk.StringVar(value="none")
        self._r(ttk.Radiobutton(pz_f, text=self._t('pause_none'), variable=self.pause_type,
                                value="none", command=self._toggle_pause),
                'pause_none').pack(side="left", padx=(0, 8))
        self._r(ttk.Radiobutton(pz_f, text=self._t('pause_fixed'), variable=self.pause_type,
                                value="fixed", command=self._toggle_pause),
                'pause_fixed').pack(side="left")
        self.pause_fixed_var = tk.StringVar(value="5")
        self.pause_fixed_entry = self._entry(pz_f, self.pause_fixed_var, 4)
        self.pause_fixed_entry.config(state="disabled", fg=MUTED)
        self.pause_fixed_entry.pack(side="left", padx=(4, 2))
        self._lbl(pz_f, "s", translate=False).pack(side="left", padx=(0, 12))
        self._r(ttk.Radiobutton(pz_f, text=self._t('pause_random'), variable=self.pause_type,
                                value="random", command=self._toggle_pause),
                'pause_random').pack(side="left")
        self.pause_min_var = tk.StringVar(value="5")
        self.pause_max_var = tk.StringVar(value="30")
        self.pause_min_entry = self._entry(pz_f, self.pause_min_var, 4)
        self.pause_min_entry.config(state="disabled", fg=MUTED)
        self.pause_min_entry.pack(side="left", padx=(4, 2))
        self._lbl(pz_f, "–", translate=False).pack(side="left")
        self.pause_max_entry = self._entry(pz_f, self.pause_max_var, 4)
        self.pause_max_entry.config(state="disabled", fg=MUTED)
        self.pause_max_entry.pack(side="left", padx=(2, 2))
        self._lbl(pz_f, "s", translate=False).pack(side="left")

        self.rec_status_var = tk.StringVar(value=self._t('rec_status_ready'))
        self.rec_status_lbl = tk.Label(p, textvariable=self.rec_status_var,
                                       bg=BG, fg=MUTED, font=("Helvetica", 14))
        self.rec_status_lbl.grid(row=4, column=0, columnspan=3, pady=(4, 0))

        self.rec_counter_var = tk.StringVar(value="")
        tk.Label(p, textvariable=self.rec_counter_var, bg=BG, fg=GREEN,
                 font=("Helvetica", 14, "bold")).grid(row=5, column=0, columnspan=3)

        self._sep(p, 6)

        self._lbl(p, 'template_name').grid(row=7, column=0, sticky="w", **pad)
        sf = ttk.Frame(p)
        sf.grid(row=7, column=1, columnspan=2, sticky="w", **pad)
        self.template_name_var = tk.StringVar(value="")
        self._entry(sf, self.template_name_var, 16, numeric=False).pack(side="left")
        self._r(ttk.Button(sf, text=self._t('btn_save'), style="Save.TButton",
                           command=self._save_template), 'btn_save').pack(side="left", padx=(8, 0))

        tk.Frame(p, bg="#45475a", height=1).grid(row=8, column=0, columnspan=3,
                                                  sticky="ew", pady=(10, 4))
        self._lbl(p, 'saved_templates', fg=MUTED, size=11).grid(row=9, column=0,
                                                                  columnspan=3, sticky="w")

        lf = tk.Frame(p, bg=PANEL)
        lf.grid(row=10, column=0, columnspan=3, sticky="ew", pady=(4, 6))
        self.template_list = tk.Listbox(lf, bg=PANEL, fg=FG, selectbackground=ACC,
                                        selectforeground=BG, font=("Helvetica", 16),
                                        relief="flat", bd=0, height=10,
                                        activestyle="none", highlightthickness=0)
        self.template_list.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        self.template_list.bind("<Double-Button-1>", self._load_and_play_template)
        sb = tk.Scrollbar(lf, orient="vertical", command=self.template_list.yview,
                          bg=PANEL, troughcolor=PANEL, bd=0, width=8)
        sb.pack(side="right", fill="y")
        self.template_list.config(yscrollcommand=sb.set)

        af = ttk.Frame(p)
        af.grid(row=11, column=0, columnspan=3, sticky="w", pady=(0, 4))
        self._r(ttk.Button(af, text=self._t('btn_load'), style="Load.TButton",
                           command=self._load_template), 'btn_load').pack(side="left", padx=(0, 8))
        self._r(ttk.Button(af, text=self._t('btn_delete'), style="Del.TButton",
                           command=self._delete_template), 'btn_delete').pack(side="left")

        self._refresh_templates()

    def _toggle_play_repeat(self):
        if self.play_repeat_type.get() == "count":
            self.play_repeat_entry.config(state="normal", fg=YELLOW)
        else:
            self.play_repeat_entry.config(state="disabled", fg=MUTED)

    def _toggle_pause(self):
        pt = self.pause_type.get()
        self.pause_fixed_entry.config(state="normal" if pt == "fixed"  else "disabled",
                                      fg=YELLOW     if pt == "fixed"  else MUTED)
        self.pause_min_entry.config(state="normal"  if pt == "random" else "disabled",
                                    fg=YELLOW       if pt == "random" else MUTED)
        self.pause_max_entry.config(state="normal"  if pt == "random" else "disabled",
                                    fg=YELLOW       if pt == "random" else MUTED)

    def _get_pause_fn(self):
        import random
        pt = self.pause_type.get()
        if pt == "fixed":
            secs = float(self.pause_fixed_var.get())
            return lambda: secs
        elif pt == "random":
            lo = float(self.pause_min_var.get())
            hi = float(self.pause_max_var.get())
            return lambda: random.uniform(lo, hi)
        return None

    def _set_rec_status(self, text, color=MUTED):
        self.rec_status_var.set(text)
        self.rec_status_lbl.config(fg=color)

    def _toggle_recording(self):
        if self._recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        self._recording = True
        self.rec_btn.config(text=self._t('btn_stop_rec'), style="Stop.TButton")
        self.play_btn.config(state="disabled")
        self._set_rec_status(self._t('status_starting'), YELLOW)
        if IS_MACOS:
            if self._gesture_monitor:
                AppKit.NSEvent.removeMonitor_(self._gesture_monitor)
            mask = (1 << 31) | (1 << 29)
            self._gesture_monitor = AppKit.NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
                mask, self._on_gesture
            )
        threading.Thread(target=self._start_listener, daemon=True).start()

    def _start_listener(self):
        self._recorder.start()
        self.root.after(0, lambda: self._set_rec_status(self._t('status_recording'), RED))
        self.root.after(0, self._update_event_count)

    def _update_event_count(self):
        if self._recording:
            self.rec_counter_var.set(
                self._t('status_events').format(n=len(self._recorder.events)))
            self.root.after(200, self._update_event_count)

    def _stop_recording(self):
        self._recording = False
        if IS_MACOS and self._gesture_monitor:
            AppKit.NSEvent.removeMonitor_(self._gesture_monitor)
            self._gesture_monitor = None
        if self.root.state() == 'iconic':
            self.root.deiconify()
            self.root.lift()
        self.rec_btn.config(text=self._t('btn_record'), style="Record.TButton")
        self.rec_counter_var.set("")
        self._set_rec_status(self._t('status_stopping'), YELLOW)
        def _stop_bg():
            self._recorder.stop()
            n   = len(self._recorder.events)
            dur = self._recorder.duration()
            self.root.after(0, lambda: self._set_rec_status(
                self._t('status_recorded').format(n=n, d=f"{dur:.1f}"), GREEN))
            if n > 0:
                self.root.after(0, lambda: self.play_btn.config(state="normal"))
        threading.Thread(target=_stop_bg, daemon=True).start()

    def _toggle_playing(self):
        if self._playing:
            self._stop_playing()
        else:
            self._start_playing()

    def _start_playing(self):
        if not self._recorder.events:
            self._set_rec_status(self._t('status_no_events'), YELLOW)
            return
        self._playing = True
        self._play_stop.clear()
        self.play_btn.config(text=self._t('btn_stop_play'), style="Stop.TButton")
        self.rec_btn.config(state="disabled")
        self._set_rec_status(self._t('status_playing'), GREEN)
        infinite = self.play_repeat_type.get() == "infinite"
        repeat = 999999 if infinite else int(self.play_repeat_count.get())
        pause_fn = self._get_pause_fn()
        self.root.iconify()
        self._play_thread = threading.Thread(
            target=self._play_loop, args=(repeat, pause_fn), daemon=True)
        self._play_thread.start()

    def _play_loop(self, repeat, pause_fn):
        def on_count(n):
            if pause_fn and not self._play_stop.is_set():
                secs = pause_fn()
                self.root.after(0, lambda s=secs: self.rec_counter_var.set(
                    self._t('status_cycle_pause').format(n=n, s=f"{s:.1f}")))
                deadline = time.perf_counter() + secs
                while time.perf_counter() < deadline:
                    if self._play_stop.is_set():
                        return
                    time.sleep(0.05)
            self.root.after(0, lambda: self.rec_counter_var.set(
                self._t('status_cycle').format(n=n)))
        def on_error(msg):
            self.root.after(0, lambda: self._set_rec_status(
                self._t('status_error_msg').format(msg=msg), RED))
            self.root.after(0, self._stop_playing)
        self._recorder.play(self._play_stop, repeat=repeat, on_count=on_count, on_error=on_error)
        if not self._play_stop.is_set():
            self.root.after(0, self._notify_done)
        self.root.after(0, self._stop_playing)

    def _notify_done(self):
        self.root.deiconify()
        self.root.lift()
        self._set_rec_status(self._t('status_all_done'), GREEN)
        popup = tk.Toplevel(self.root)
        popup.overrideredirect(True)
        popup.attributes('-topmost', True)
        popup.configure(bg=GREEN)
        sw = self.root.winfo_screenwidth()
        w, h = 340, 64
        popup.geometry(f"{w}x{h}+{sw - w - 20}+20")
        tk.Label(popup, text=self._t('notify_done'),
                 bg=GREEN, fg=BG,
                 font=("Helvetica", 15, "bold"),
                 padx=16).pack(fill="both", expand=True)
        popup.after(4000, popup.destroy)

    def _stop_playing(self):
        self._play_stop.set()
        self._playing = False
        _quartz_release_all()
        self.root.deiconify()
        self.play_btn.config(text=self._t('btn_play'), style="Play.TButton")
        self.rec_btn.config(state="normal")
        self._set_rec_status(self._t('status_stopped_rec'))
        self.rec_counter_var.set("")

    # ── Scheduler / Planner tab ────────────────────────────────

    def _build_scheduler_tab(self, p):
        p.rowconfigure(3, weight=1)
        p.columnconfigure(0, weight=1)
        pad = dict(padx=4, pady=4)

        # ── Add task row
        add_f = ttk.Frame(p)
        add_f.grid(row=0, column=0, sticky="ew", **pad)
        add_f.columnconfigure(1, weight=1)
        self._lbl(add_f, 'planner_tmpl').grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.sched_template_var = tk.StringVar()
        self.sched_template_cb = ttk.Combobox(
            add_f, textvariable=self.sched_template_var, state="readonly",
            font=("Helvetica", 14), width=18)
        self.sched_template_cb.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        tk.Label(add_f, text="×", bg=BG, fg=FG, font=("Helvetica", 15)).grid(row=0, column=2)
        self.sched_repeat_var = tk.StringVar(value="3")
        self._entry(add_f, self.sched_repeat_var, 4).grid(row=0, column=3, padx=(4, 8))
        self._r(ttk.Button(add_f, text=self._t('btn_add'), style="Load.TButton",
                           command=self._sched_add_task), 'btn_add').grid(row=0, column=4)

        # ── Add pause gap row
        self._lbl(add_f, 'pause_gap_lbl').grid(row=1, column=0, sticky="w", padx=(0, 6), pady=(4, 0))
        self.sched_pause_gap_var = tk.StringVar(value="5")
        self._entry(add_f, self.sched_pause_gap_var, 5).grid(row=1, column=1, sticky="w", padx=(0, 4), pady=(4, 0))
        tk.Label(add_f, text="s", bg=BG, fg=FG, font=("Helvetica", 14)).grid(row=1, column=2, pady=(4, 0))
        self._r(ttk.Button(add_f, text=self._t('btn_add_pause'), style="Load.TButton",
                           command=self._sched_add_pause), 'btn_add_pause').grid(
            row=1, column=3, columnspan=2, sticky="w", padx=(8, 0), pady=(4, 0))

        # ── Task queue
        tk.Frame(p, bg="#45475a", height=1).grid(row=1, column=0, sticky="ew", pady=(6, 4))
        ctrl_f = ttk.Frame(p)
        ctrl_f.grid(row=2, column=0, sticky="w", padx=4, pady=(0, 2))
        self._lbl(ctrl_f, 'task_order', size=10, fg=MUTED).pack(side="left", padx=(0, 10))
        ttk.Button(ctrl_f, text="↑", style="Up.TButton", width=3,
                   command=self._sched_move_up).pack(side="left", padx=(0, 4))
        ttk.Button(ctrl_f, text="↓", style="Down.TButton", width=3,
                   command=self._sched_move_down).pack(side="left", padx=(0, 4))
        self._r(ttk.Button(ctrl_f, text=self._t('btn_remove'), style="Del.TButton",
                           command=self._sched_remove_task), 'btn_remove').pack(
            side="left", padx=(0, 4))

        lf = tk.Frame(p, bg=PANEL)
        lf.grid(row=3, column=0, sticky="nsew", pady=(2, 4))
        lf.rowconfigure(0, weight=1)
        lf.columnconfigure(0, weight=1)
        self.sched_list = tk.Listbox(lf, bg=PANEL, fg=FG, selectbackground=ACC,
                                     selectforeground=BG, font=("Helvetica", 15),
                                     relief="flat", bd=0, height=5,
                                     activestyle="none", highlightthickness=0)
        self.sched_list.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        sb2 = tk.Scrollbar(lf, orient="vertical", command=self.sched_list.yview,
                           bg=PANEL, troughcolor=PANEL, bd=0, width=8)
        sb2.grid(row=0, column=1, sticky="ns")
        self.sched_list.config(yscrollcommand=sb2.set)

        # ── Pause between tasks
        tk.Frame(p, bg="#45475a", height=1).grid(row=4, column=0, sticky="ew", pady=(4, 4))
        pz_f = ttk.Frame(p)
        pz_f.grid(row=5, column=0, sticky="w", padx=4, pady=2)
        self._lbl(pz_f, 'pause_between_tasks').pack(side="left", padx=(0, 8))
        self.sched_pause_type = tk.StringVar(value="none")
        self._r(ttk.Radiobutton(pz_f, text=self._t('pause_none'), variable=self.sched_pause_type,
                                value="none", command=self._sched_toggle_pause),
                'pause_none').pack(side="left", padx=(0, 8))
        self._r(ttk.Radiobutton(pz_f, text=self._t('pause_fixed'), variable=self.sched_pause_type,
                                value="fixed", command=self._sched_toggle_pause),
                'pause_fixed').pack(side="left")
        self.sched_pause_var = tk.StringVar(value="5")
        self.sched_pause_entry = self._entry(pz_f, self.sched_pause_var, 4)
        self.sched_pause_entry.config(state="disabled", fg=MUTED)
        self.sched_pause_entry.pack(side="left", padx=(4, 4))
        self._lbl(pz_f, "s", translate=False).pack(side="left")

        # ── Loop / cycle section
        tk.Frame(p, bg="#45475a", height=1).grid(row=6, column=0, sticky="ew", pady=(4, 4))
        lp_f = ttk.Frame(p)
        lp_f.grid(row=7, column=0, sticky="w", padx=4, pady=2)
        self.sched_loop_var = tk.BooleanVar(value=False)
        self._r(ttk.Checkbutton(lp_f, text=self._t('loop_label'), variable=self.sched_loop_var,
                                command=self._sched_toggle_loop), 'loop_label').pack(
            side="left", padx=(0, 14))
        self.sched_loop_count_type = tk.StringVar(value="infinite")
        self.sched_loop_rb_inf = self._r(
            ttk.Radiobutton(lp_f, text=self._t('infinite'), variable=self.sched_loop_count_type,
                            value="infinite", state="disabled"), 'infinite')
        self.sched_loop_rb_inf.pack(side="left", padx=(0, 8))
        self.sched_loop_rb_cnt = self._r(
            ttk.Radiobutton(lp_f, text=self._t('phases_label'), variable=self.sched_loop_count_type,
                            value="count", state="disabled"), 'phases_label')
        self.sched_loop_rb_cnt.pack(side="left")
        self.sched_loop_count_var = tk.StringVar(value="3")
        self.sched_loop_count_entry = self._entry(lp_f, self.sched_loop_count_var, 4)
        self.sched_loop_count_entry.config(state="disabled", fg=MUTED)
        self.sched_loop_count_entry.pack(side="left", padx=(4, 16))
        self._lbl(lp_f, 'phase_pause').pack(side="left", padx=(0, 4))
        self.sched_loop_pause_var = tk.StringVar(value="60")
        self.sched_loop_pause_entry = self._entry(lp_f, self.sched_loop_pause_var, 5)
        self.sched_loop_pause_entry.config(state="disabled", fg=MUTED)
        self.sched_loop_pause_entry.pack(side="left", padx=(4, 4))
        self._lbl(lp_f, "s", translate=False).pack(side="left")

        # ── Start time
        tk.Frame(p, bg="#45475a", height=1).grid(row=8, column=0, sticky="ew", pady=(4, 4))
        st_f = ttk.Frame(p)
        st_f.grid(row=9, column=0, sticky="w", padx=4, pady=2)
        self._lbl(st_f, 'start_label').pack(side="left", padx=(0, 8))
        self.sched_start_type = tk.StringVar(value="now")
        self._r(ttk.Radiobutton(st_f, text=self._t('start_now'), variable=self.sched_start_type,
                                value="now", command=self._sched_toggle_time),
                'start_now').pack(side="left", padx=(0, 8))
        self._r(ttk.Radiobutton(st_f, text=self._t('start_at'), variable=self.sched_start_type,
                                value="at", command=self._sched_toggle_time),
                'start_at').pack(side="left")
        self.sched_time_var = tk.StringVar(value="23:00")
        self.sched_time_entry = self._entry(st_f, self.sched_time_var, 6, numeric=False)
        self.sched_time_entry.config(state="disabled", fg=MUTED)
        self.sched_time_entry.pack(side="left", padx=(6, 0))

        # ── Run controls
        tk.Frame(p, bg="#45475a", height=1).grid(row=10, column=0, sticky="ew", pady=(4, 4))
        run_f = ttk.Frame(p)
        run_f.grid(row=11, column=0, sticky="w", padx=4, pady=(0, 4))
        self.sched_run_btn = self._r(
            ttk.Button(run_f, text=self._t('btn_start_plan'), style="Sched.TButton",
                       width=16, command=self._sched_toggle), 'btn_start_plan')
        self.sched_run_btn.pack(side="left", padx=(0, 8))

        self.sched_status_var = tk.StringVar(value=self._t('sched_ready'))
        self.sched_status_lbl = tk.Label(p, textvariable=self.sched_status_var,
                                         bg=BG, fg=MUTED, font=("Helvetica", 13))
        self.sched_status_lbl.grid(row=12, column=0, sticky="w", padx=4)

        self._sched_refresh_templates()

    def _sched_refresh_templates(self):
        def _bg():
            names = MacroRecorder.list_templates()
            self.root.after(0, lambda: self.sched_template_cb.config(values=names))
            if names and not self.sched_template_var.get():
                self.root.after(0, lambda: self.sched_template_var.set(names[0]))
        threading.Thread(target=_bg, daemon=True).start()

    def _sched_toggle_pause(self):
        on = self.sched_pause_type.get() == "fixed"
        self.sched_pause_entry.config(state="normal" if on else "disabled",
                                      fg=YELLOW if on else MUTED)

    def _sched_toggle_time(self):
        on = self.sched_start_type.get() == "at"
        self.sched_time_entry.config(state="normal" if on else "disabled",
                                     fg=YELLOW if on else MUTED)

    def _sched_toggle_loop(self):
        on = self.sched_loop_var.get()
        self.sched_loop_rb_inf.config(state="normal" if on else "disabled")
        self.sched_loop_rb_cnt.config(state="normal" if on else "disabled")
        self.sched_loop_count_entry.config(state="normal" if on else "disabled",
                                           fg=YELLOW if on else MUTED)
        self.sched_loop_pause_entry.config(state="normal" if on else "disabled",
                                           fg=YELLOW if on else MUTED)

    def _sched_add_task(self):
        name = self.sched_template_var.get().strip()
        if not name:
            self._sched_set_status(self._t('sched_select_tmpl'), YELLOW)
            return
        try:
            repeat = max(1, int(self.sched_repeat_var.get() or "1"))
        except ValueError:
            repeat = 1
        self._sched_tasks.append({'type': 'task', 'name': name, 'repeat': repeat})
        self._sched_refresh_list()

    def _sched_add_pause(self):
        try:
            dur = max(0.1, float(self.sched_pause_gap_var.get() or "5"))
        except ValueError:
            dur = 5.0
        self._sched_tasks.append({'type': 'pause', 'duration': dur})
        self._sched_refresh_list()

    def _sched_remove_task(self):
        sel = self.sched_list.curselection()
        if not sel:
            return
        del self._sched_tasks[sel[0]]
        self._sched_refresh_list()

    def _sched_move_up(self):
        sel = self.sched_list.curselection()
        if not sel or sel[0] == 0:
            return
        i = sel[0]
        self._sched_tasks[i - 1], self._sched_tasks[i] = (
            self._sched_tasks[i], self._sched_tasks[i - 1])
        self._sched_refresh_list()
        self.sched_list.selection_set(i - 1)

    def _sched_move_down(self):
        sel = self.sched_list.curselection()
        if not sel or sel[0] >= len(self._sched_tasks) - 1:
            return
        i = sel[0]
        self._sched_tasks[i], self._sched_tasks[i + 1] = (
            self._sched_tasks[i + 1], self._sched_tasks[i])
        self._sched_refresh_list()
        self.sched_list.selection_set(i + 1)

    def _sched_refresh_list(self):
        self.sched_list.delete(0, tk.END)
        task_i = 0
        for item in self._sched_tasks:
            if item.get('type') == 'pause':
                self.sched_list.insert(tk.END, self._t('sched_pause_item').format(d=item['duration']))
            else:
                task_i += 1
                self.sched_list.insert(tk.END, f"  {task_i}.  {item['name']}  ×{item['repeat']}")

    def _sched_set_status(self, text, color=MUTED):
        self.sched_status_var.set(text)
        self.sched_status_lbl.config(fg=color)

    def _sched_toggle(self):
        if self._sched_running:
            self._sched_stop_plan()
        else:
            self._sched_start_plan()

    def _sched_start_plan(self):
        if not self._sched_tasks:
            self._sched_set_status(self._t('sched_no_tasks'), YELLOW)
            return
        self._sched_running = True
        self._sched_stop.clear()
        self.sched_run_btn.config(text=self._t('btn_stop_plan'), style="Stop.TButton")
        self._sched_set_status(self._t('sched_starting'), YELLOW)
        start_type = self.sched_start_type.get()
        start_time = self.sched_time_var.get().strip() if start_type == "at" else None
        pause_fixed = (float(self.sched_pause_var.get() or "0")
                       if self.sched_pause_type.get() == "fixed" else 0)
        if self.sched_loop_var.get():
            loop_infinite = self.sched_loop_count_type.get() == "infinite"
            loop_count = 999999 if loop_infinite else max(1, int(self.sched_loop_count_var.get() or "1"))
            loop_pause = float(self.sched_loop_pause_var.get() or "0")
        else:
            loop_count = 1
            loop_pause = 0
        threading.Thread(
            target=self._sched_loop,
            args=(list(self._sched_tasks), start_time, pause_fixed, loop_count, loop_pause),
            daemon=True
        ).start()

    def _sched_stop_plan(self):
        self._sched_stop.set()
        self._sched_running = False
        _quartz_release_all()
        self.root.deiconify()
        self.sched_run_btn.config(text=self._t('btn_start_plan'), style="Sched.TButton")
        self._sched_set_status(self._t('sched_stopped'))

    def _sched_loop(self, tasks, start_time, pause_between, loop_count, loop_pause):
        import datetime

        def _wait_countdown(secs, label_fn):
            deadline = time.perf_counter() + secs
            while time.perf_counter() < deadline:
                if self._sched_stop.is_set():
                    return False
                rem = deadline - time.perf_counter()
                self.root.after(0, lambda t=f"{int(rem//3600):02d}:{int((rem%3600)//60):02d}:{int(rem%60):02d}":
                                label_fn(t))
                time.sleep(0.5)
            return True

        if start_time:
            try:
                h, m = map(int, start_time.split(':'))
                now = datetime.datetime.now()
                target = now.replace(hour=h, minute=m, second=0, microsecond=0)
                if target <= now:
                    target += datetime.timedelta(days=1)
                secs_left = (target - datetime.datetime.now()).total_seconds()
                ok = _wait_countdown(secs_left,
                    lambda t: self._sched_set_status(
                        self._t('sched_waiting').format(t=start_time, r=t), YELLOW))
                if not ok:
                    self.root.after(0, self._sched_stop_plan)
                    return
            except Exception as e:
                self.root.after(0, lambda: self._sched_set_status(
                    self._t('sched_time_error').format(e=e), RED))
                self.root.after(0, self._sched_stop_plan)
                return

        self.root.iconify()
        task_items = [t for t in tasks if t.get('type') != 'pause']
        total = len(task_items)
        infinite = (loop_count == 999999)

        for phase in range(loop_count):
            if self._sched_stop.is_set():
                break

            if phase > 0 and loop_pause > 0:
                ph_label = "∞" if infinite else str(loop_count)
                ok = _wait_countdown(loop_pause,
                    lambda t, ph=phase, pl=ph_label: self._sched_set_status(
                        self._t('sched_pause_phases').format(p=ph, pl=pl, t=t), YELLOW))
                if not ok:
                    break

            if loop_count == 1:
                phase_tag = ""
            elif infinite:
                phase_tag = self._t('phase_tag_inf').format(p=phase + 1)
            else:
                phase_tag = self._t('phase_tag_cnt').format(p=phase + 1, c=loop_count)

            task_idx = 0
            for list_idx, item in enumerate(tasks):
                if self._sched_stop.is_set():
                    break

                if item.get('type') == 'pause':
                    dur = item['duration']
                    deadline = time.perf_counter() + dur
                    while time.perf_counter() < deadline:
                        if self._sched_stop.is_set():
                            break
                        rem = deadline - time.perf_counter()
                        self.root.after(0, lambda r=rem: self._sched_set_status(
                            self._t('sched_running_pause').format(r=r), YELLOW))
                        time.sleep(0.2)
                    continue

                task_idx += 1
                task = item
                self.root.after(0, lambda i=task_idx, n=task['name'], r=task['repeat'], pt=phase_tag:
                                self._sched_set_status(
                                    self._t('sched_task').format(
                                        i=i, total=total, name=n, r=r, pt=pt), GREEN))
                try:
                    self._sched_recorder.load(task['name'])
                except Exception as e:
                    self.root.after(0, lambda e=e: self._sched_set_status(
                        self._t('sched_load_error').format(e=e), RED))
                    self._sched_stop.set()
                    break

                play_stop = threading.Event()

                def _run_task(stop_ev=play_stop, tk_=task, i=task_idx, pt=phase_tag):
                    self._sched_recorder.play(
                        stop_ev, repeat=tk_['repeat'],
                        on_count=lambda n, i=i, tk_=tk_, pt=pt: self.root.after(
                            0, lambda: self._sched_set_status(
                                self._t('sched_task_cycle').format(
                                    i=i, total=total, name=tk_['name'],
                                    c=n, r=tk_['repeat'], pt=pt), GREEN))
                    )

                t = threading.Thread(target=_run_task, daemon=True)
                t.start()
                while t.is_alive():
                    if self._sched_stop.is_set():
                        play_stop.set()
                        t.join(timeout=2)
                        break
                    time.sleep(0.1)

                if self._sched_stop.is_set():
                    break

                # Apply global pause_between only if the next item is not a pause gap
                # and this is not the last item in the list
                next_item = tasks[list_idx + 1] if list_idx + 1 < len(tasks) else None
                next_is_pause = next_item is not None and next_item.get('type') == 'pause'
                is_last = (list_idx == len(tasks) - 1)
                if pause_between > 0 and not is_last and not next_is_pause:
                    deadline = time.perf_counter() + pause_between
                    while time.perf_counter() < deadline:
                        if self._sched_stop.is_set():
                            break
                        rem = deadline - time.perf_counter()
                        self.root.after(0, lambda r=rem: self._sched_set_status(
                            self._t('sched_pause_tasks').format(r=r), YELLOW))
                        time.sleep(0.2)

        if not self._sched_stop.is_set():
            self.root.after(0, lambda: self._sched_set_status(self._t('sched_done'), GREEN))
            self.root.after(0, self.root.deiconify)
            self.root.after(0, self.root.lift)
        self.root.after(0, lambda: self.sched_run_btn.config(
            text=self._t('btn_start_plan'), style="Sched.TButton"))
        self._sched_running = False

    # ── Settings: load / save ───────────────────────────────────

    def _load_settings(self):
        try:
            with open(SETTINGS_PATH) as f:
                stored = json.load(f)
            for k, v in stored.items():
                self._settings[k] = v
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        # Default language is English
        if 'language' not in self._settings:
            self._settings['language'] = 'en'

    def _save_settings(self):
        try:
            with open(SETTINGS_PATH, 'w') as f:
                json.dump(self._settings, f, indent=2)
        except Exception:
            pass

    def _sc_display(self, action):
        s = self._settings.get(action, DEFAULT_SHORTCUTS.get(action, {}))
        parts = []
        if s.get('cmd'):   parts.append("Ctrl" if IS_WINDOWS else "⌘")
        if s.get('shift'): parts.append("Shift" if IS_WINDOWS else "⇧")
        if s.get('alt'):   parts.append("Alt" if IS_WINDOWS else "⌥")
        key = s.get('key', '')
        if key == 'escape': parts.append("ESC")
        elif key == 'space': parts.append("Space" if IS_WINDOWS else "⎵")
        elif key: parts.append(key.upper())
        return "  ".join(parts) if parts else "—"

    def _start_sc_capture(self, action, lbl, btn):
        if self._capturing_action:
            self._cancel_sc_capture()
        self._capturing_action = action
        self._capturing_label  = lbl
        self._capturing_btn    = btn
        lbl.config(text=self._t('sc_press_keys'), fg=RED)
        btn.config(text=self._t('btn_cancel'), style="Stop.TButton",
                   command=self._cancel_sc_capture)

    def _cancel_sc_capture(self):
        if self._capturing_label and self._capturing_action:
            self._capturing_label.config(
                text=self._sc_display(self._capturing_action), fg=YELLOW)
        if self._capturing_btn and self._capturing_action:
            a, l, b = self._capturing_action, self._capturing_label, self._capturing_btn
            b.config(text=self._t('btn_change'), style="Load.TButton",
                     command=lambda aa=a, ll=l, bb=b: self._start_sc_capture(aa, ll, bb))
        self._capturing_action = None
        self._capturing_label  = None
        self._capturing_btn    = None

    def _finish_sc_capture(self, action, cmd, shift, alt, key):
        self._settings[action] = {'cmd': cmd, 'shift': shift, 'alt': alt, 'key': key}
        self._save_settings()
        lbl, btn = self._capturing_label, self._capturing_btn
        self._capturing_action = None
        self._capturing_label  = None
        self._capturing_btn    = None
        if lbl:
            lbl.config(text=self._sc_display(action), fg=YELLOW)
        if btn:
            btn.config(text=self._t('btn_change'), style="Load.TButton",
                       command=lambda a=action, l=lbl, b=btn: self._start_sc_capture(a, l, b))

    # ── Settings tab UI ─────────────────────────────────────────

    def _build_settings_tab(self, outer):
        outer.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)

        canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
        canvas.grid(row=0, column=0, sticky="nsew")
        sb = tk.Scrollbar(outer, orient="vertical", command=canvas.yview,
                          bg=PANEL, troughcolor=PANEL, bd=0, width=8)
        sb.grid(row=0, column=1, sticky="ns")
        canvas.configure(yscrollcommand=sb.set)

        p = tk.Frame(canvas, bg=BG)
        p.columnconfigure(0, weight=1)
        cw = canvas.create_window((0, 0), window=p, anchor="nw")
        p.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(cw, width=e.width))
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(-(e.delta // 120), "units"))

        # ── Keyboard shortcuts section
        self._r(tk.Label(p, text=self._t('settings_shortcuts'), bg=BG, fg=ACC,
                         font=("Helvetica", 15)), 'settings_shortcuts').grid(
            row=0, column=0, sticky="w", padx=8, pady=(10, 4))
        tk.Frame(p, bg=ACC, height=1).grid(
            row=1, column=0, sticky="ew", padx=8, pady=(0, 10))

        sc_f = tk.Frame(p, bg=BG)
        sc_f.grid(row=2, column=0, sticky="ew", padx=8)
        sc_f.columnconfigure(1, weight=1)

        sc_defs = [
            ("start_recording", 'sc_start_rec_lbl'),
            ("toggle_playing",  'sc_toggle_play_lbl'),
            ("stop",            'sc_stop_lbl2'),
        ]
        self._sc_rows = {}
        self._sc_action_labels = {}   # action → label widget (for lang updates)
        for row_i, (action, label_key) in enumerate(sc_defs):
            stripe = tk.Frame(sc_f, bg=PANEL if row_i % 2 == 0 else BG,
                              padx=10, pady=8)
            stripe.grid(row=row_i, column=0, columnspan=3, sticky="ew", pady=2)
            stripe.columnconfigure(1, weight=1)

            action_lbl = tk.Label(stripe, text=self._t(label_key),
                                  bg=stripe["bg"], fg=FG, font=("Helvetica", 15))
            action_lbl.pack(side="left", padx=(4, 20))
            self._tw.append((action_lbl, label_key, 'text'))
            self._sc_action_labels[action] = action_lbl

            badge = tk.Label(stripe, text=self._sc_display(action),
                             bg="#1e1e2e", fg=YELLOW,
                             font=("Helvetica", 14, "bold"),
                             padx=12, pady=4, relief="flat",
                             highlightthickness=1, highlightbackground="#45475a")
            badge.pack(side="left", padx=(0, 16))

            btn = ttk.Button(stripe, text=self._t('btn_change'), style="Load.TButton",
                             command=lambda a=action, bl=badge, bt=None: None)
            btn.pack(side="right", padx=4)
            btn.config(command=lambda a=action, bl=badge, bt=btn:
                       self._start_sc_capture(a, bl, bt))
            self._tw.append((btn, 'btn_change', 'text'))
            self._sc_rows[action] = (badge, btn)

        # ── Hint
        tk.Frame(p, bg="#45475a", height=1).grid(
            row=3, column=0, sticky="ew", padx=8, pady=(18, 8))
        self._r(tk.Label(p, text=self._t('sc_hint'), bg=BG, fg=MUTED,
                         font=("Helvetica", 13)), 'sc_hint').grid(
            row=4, column=0, sticky="w", padx=8)

        # ── Reset button
        self._r(ttk.Button(p, text=self._t('btn_reset_sc'), style="Load.TButton",
                           command=self._reset_shortcuts), 'btn_reset_sc').grid(
            row=5, column=0, sticky="w", padx=8, pady=(14, 0))

        # ── Language section
        tk.Frame(p, bg=ACC, height=1).grid(
            row=6, column=0, sticky="ew", padx=8, pady=(24, 10))
        self._r(tk.Label(p, text=self._t('settings_language'), bg=BG, fg=ACC,
                         font=("Helvetica", 15)), 'settings_language').grid(
            row=7, column=0, sticky="w", padx=8, pady=(0, 8))

        lang_f = tk.Frame(p, bg=BG)
        lang_f.grid(row=8, column=0, sticky="w", padx=8)

        _lang_native = [
            ('en', 'English'),
            ('sk', 'Slovenčina'),
            ('fr', 'Français'),
            ('de', 'Deutsch'),
            ('es', 'Español'),
        ]
        _all_names = [n for _, n in _lang_native]
        current_lang = self._settings.get('language', 'en')
        current_name = next((n for c, n in _lang_native if c == current_lang), 'English')

        self._lang_cb_var = tk.StringVar(value=current_name)
        self._lang_cb = ttk.Combobox(
            lang_f, textvariable=self._lang_cb_var,
            values=_all_names, font=("Helvetica", 14), width=16)
        self._lang_cb.pack(side="left")

        def _lang_key(_event, opts=_lang_native, all_n=_all_names):
            typed = self._lang_cb_var.get()
            filtered = [n for _, n in opts if n.lower().startswith(typed.lower())]
            self._lang_cb['values'] = filtered or all_n
            if filtered:
                try:
                    self._lang_cb.event_generate('<Down>')
                except Exception:
                    pass

        def _lang_pick(event=None, opts=_lang_native, all_n=_all_names):
            selected = self._lang_cb_var.get()
            self._lang_cb['values'] = all_n
            for code, name in opts:
                if name == selected:
                    self._change_language(code)
                    return
            # If typed text doesn't exactly match, reset to current
            c = self._settings.get('language', 'en')
            self._lang_cb_var.set(next((n for cd, n in opts if cd == c), 'English'))

        def _lang_focus_in(_event):
            # Select all text so the first keystroke replaces it (no need to delete first)
            self._lang_cb.after(1, lambda: self._lang_cb.select_range(0, tk.END))

        self._lang_cb.bind('<FocusIn>', _lang_focus_in)
        self._lang_cb.bind('<KeyRelease>', _lang_key)
        self._lang_cb.bind('<<ComboboxSelected>>', _lang_pick)
        self._lang_cb.bind('<Return>', _lang_pick)
        self._lang_cb.bind('<FocusOut>', _lang_pick)

        # ── About section
        tk.Frame(p, bg="#45475a", height=1).grid(
            row=9, column=0, sticky="ew", padx=8, pady=(28, 12))

        about_f = tk.Frame(p, bg=BG)
        about_f.grid(row=10, column=0, sticky="w", padx=16, pady=(0, 16))

        tk.Label(about_f, text=f"JJClicker  v{APP_VERSION}",
                 bg=BG, fg=FG, font=("Helvetica", 16, "bold")).pack(anchor="w")
        tk.Label(about_f, text=f"Autor:  {APP_AUTHOR}",
                 bg=BG, fg=MUTED, font=("Helvetica", 13)).pack(anchor="w", pady=(4, 0))
        tk.Label(about_f, text="Open-source — voľne použiteľná a upraviteľná",
                 bg=BG, fg=MUTED, font=("Helvetica", 13)).pack(anchor="w", pady=(2, 0))

    def _show_about_dialog(self):
        from tkinter import messagebox
        self.root.deiconify()
        self.root.lift()
        messagebox.showinfo(
            "JJClicker",
            f"JJClicker  v{APP_VERSION}\n\n"
            f"Autor:  {APP_AUTHOR}\n\n"
            "Open-source — voľne použiteľná a upraviteľná.\n"
            "Free & open-source macro automation for macOS."
        )

    def _change_language(self, lang):
        self._settings['language'] = lang
        self._save_settings()
        self._apply_language()

    def _reset_shortcuts(self):
        self._settings.update(DEFAULT_SHORTCUTS)
        self._save_settings()
        for action, (lbl, btn) in self._sc_rows.items():
            lbl.config(text=self._sc_display(action), fg=YELLOW)

    # ── macOS menu-bar status item (subprocess with own AppKit loop) ────────

    # PID file so helpers from previous sessions are killed on next launch
    _MB_PID_FILE = Path.home() / ".jjclicker" / "menubar.pid"

    def _setup_status_bar(self):
        """Spawn a helper subprocess for the system tray / menu-bar icon.
        On macOS uses AppKit; on Windows uses pystray.
        Uses a PID file to kill any leftover helper from a previous session."""
        self._stop_menubar_helper()   # kills current + any previous-session helper

        import tempfile
        helper_src  = _MENUBAR_HELPER_WINDOWS if IS_WINDOWS else _MENUBAR_HELPER
        helper_path = Path(tempfile.gettempdir()) / "jjclicker_menubar.py"
        helper_path.write_text(helper_src, encoding="utf-8")

        titles = [
            self._t('menu_about'),
            self._t('menu_open'),
            self._t('menu_record'),
            self._t('menu_play'),
            self._t('menu_quit'),
        ]

        python = sys.executable
        try:
            self._mb_proc = subprocess.Popen(
                [python, str(helper_path)] + titles,
                stdout=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                stderr=sys.stderr,
            )
        except Exception as e:
            print(f"[JJClicker] menubar helper launch error: {e}", file=sys.stderr)
            return

        # Persist PID so a future session can kill this helper
        try:
            self._MB_PID_FILE.write_text(str(self._mb_proc.pid))
        except Exception:
            pass

        # Background thread: read events from helper and dispatch to tkinter
        def _reader():
            for raw in self._mb_proc.stdout:
                cmd = raw.decode().strip()
                if cmd == 'open':
                    self.root.after(0, lambda: (self.root.deiconify(), self.root.lift()))
                elif cmd == 'record':
                    if self._recording:
                        self.root.after(0, self._stop_recording)
                    else:
                        self.root.after(0, self._hotkey_start_recording)
                elif cmd == 'play':
                    self.root.after(0, self._hotkey_toggle_playing)
                elif cmd == 'about':
                    self.root.after(0, self._show_about_dialog)
                elif cmd == 'quit':
                    self.root.after(0, self._quit_app)
        threading.Thread(target=_reader, daemon=True).start()

    def _stop_menubar_helper(self):
        self._kill_helper_now()

    def _refresh_templates(self):
        def _bg():
            names = MacroRecorder.list_templates()
            def _ui():
                self.template_list.delete(0, tk.END)
                for name in names:
                    self.template_list.insert(tk.END, f"  {name}")
                self.sched_template_cb.config(values=names)
                if names and not self.sched_template_var.get():
                    self.sched_template_var.set(names[0])
            self.root.after(0, _ui)
        threading.Thread(target=_bg, daemon=True).start()

    def _selected_template(self):
        sel = self.template_list.curselection()
        if not sel:
            return None
        return self.template_list.get(sel[0]).strip()

    def _save_template(self):
        name = self.template_name_var.get().strip()
        if not name:
            self._set_rec_status(self._t('status_enter_name'), YELLOW)
            return
        if not self._recorder.events:
            self._set_rec_status(self._t('status_nothing_rec'), YELLOW)
            return
        self._set_rec_status(self._t('status_saving'), YELLOW)
        def _bg():
            self._recorder.save(name)
            self.root.after(0, self._refresh_templates)
            self.root.after(0, lambda: self._set_rec_status(
                self._t('status_saved').format(name=name), GREEN))
        threading.Thread(target=_bg, daemon=True).start()

    def _load_template(self):
        name = self._selected_template()
        if not name:
            self._set_rec_status(self._t('status_select_tmpl'), YELLOW)
            return
        self._set_rec_status(self._t('status_loading'), YELLOW)
        def _bg():
            self._recorder.load(name)
            n   = len(self._recorder.events)
            dur = self._recorder.duration()
            self.root.after(0, lambda: self._set_rec_status(
                self._t('status_loaded').format(name=name, n=n, d=f"{dur:.1f}"), GREEN))
            self.root.after(0, lambda: self.play_btn.config(state="normal"))
        threading.Thread(target=_bg, daemon=True).start()

    def _load_and_play_template(self, event=None):
        name = self._selected_template()
        if not name:
            return
        self._set_rec_status(self._t('status_loading'), YELLOW)
        def _bg():
            self._recorder.load(name)
            n   = len(self._recorder.events)
            dur = self._recorder.duration()
            self.root.after(0, lambda: self._set_rec_status(
                self._t('status_loaded').format(name=name, n=n, d=f"{dur:.1f}"), GREEN))
            self.root.after(0, lambda: self.play_btn.config(state="normal"))
            self.root.after(150, self._start_playing)
        threading.Thread(target=_bg, daemon=True).start()

    def _delete_template(self):
        name = self._selected_template()
        if not name:
            return
        MacroRecorder.delete(name)
        self._refresh_templates()
        self._set_rec_status(self._t('status_deleted').format(name=name), MUTED)

    def _track_mouse(self):
        try:
            if IS_MACOS:
                from Quartz.CoreGraphics import CGEventCreate, CGEventGetLocation
                loc = CGEventGetLocation(CGEventCreate(None))
                self.mouse_var.set(f"x: {int(loc.x)}   y: {int(loc.y)}")
            else:
                pt = wintypes.POINT()
                ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
                self.mouse_var.set(f"x: {pt.x}   y: {pt.y}")
        except Exception:
            pass
        self.root.after(200, self._track_mouse)

    def _sc_matches(self, key, cmd, shift, alt, action):
        s = self._settings.get(action, DEFAULT_SHORTCUTS.get(action, {}))
        if bool(s.get('cmd'))   != cmd:   return False
        if bool(s.get('shift')) != shift: return False
        if bool(s.get('alt'))   != alt:   return False
        k = s.get('key', '')
        if k == 'escape': return key == pynput_keyboard.Key.esc
        if k == 'space':  return key == pynput_keyboard.Key.space
        try:
            return bool(getattr(key, 'char', None)) and key.char.lower() == k
        except Exception:
            return False

    def _start_kb_listener(self):
        _mods = {
            'cmd':   set(),
            'shift': set(),
            'alt':   set(),
        }
        # On Windows ⌘ = Ctrl; on macOS ⌘ = Cmd
        if IS_WINDOWS:
            _CMD_KEYS = (pynput_keyboard.Key.ctrl,
                         pynput_keyboard.Key.ctrl_l,  pynput_keyboard.Key.ctrl_r)
        else:
            _CMD_KEYS = (pynput_keyboard.Key.cmd,
                         pynput_keyboard.Key.cmd_l,   pynput_keyboard.Key.cmd_r)
        _SHIFT_KEYS = (pynput_keyboard.Key.shift,
                       pynput_keyboard.Key.shift_l, pynput_keyboard.Key.shift_r)
        _ALT_KEYS   = (pynput_keyboard.Key.alt,
                       pynput_keyboard.Key.alt_l,   pynput_keyboard.Key.alt_r)

        def _on_press(key):
            if key in _CMD_KEYS:   _mods['cmd'].add(key);   return
            if key in _SHIFT_KEYS: _mods['shift'].add(key); return
            if key in _ALT_KEYS:   _mods['alt'].add(key);   return

            cmd   = bool(_mods['cmd'])
            shift = bool(_mods['shift'])
            alt   = bool(_mods['alt'])

            if self._capturing_action:
                if key == pynput_keyboard.Key.esc:
                    self.root.after(0, self._cancel_sc_capture)
                    return
                if key == pynput_keyboard.Key.space:
                    key_str = 'space'
                elif key == pynput_keyboard.Key.esc:
                    key_str = 'escape'
                else:
                    try:
                        key_str = key.char.lower() if key.char else str(key).replace('Key.', '')
                    except AttributeError:
                        key_str = str(key).replace('Key.', '')
                action = self._capturing_action
                self.root.after(0, lambda a=action, c=cmd, sh=shift, al=alt, k=key_str:
                                self._finish_sc_capture(a, c, sh, al, k))
                return

            if self._sc_matches(key, cmd, shift, alt, 'stop'):
                if self._playing:
                    self.root.after(0, self._stop_playing)
                elif self._recording:
                    self.root.after(0, self._stop_recording)
            elif self._sc_matches(key, cmd, shift, alt, 'start_recording'):
                self.root.after(0, self._hotkey_start_recording)
            elif self._sc_matches(key, cmd, shift, alt, 'toggle_playing'):
                self.root.after(0, self._hotkey_toggle_playing)

        def _on_release(key):
            _mods['cmd'].discard(key)
            _mods['shift'].discard(key)
            _mods['alt'].discard(key)

        self._kb_listener = pynput_keyboard.Listener(
            on_press=_on_press, on_release=_on_release)
        self._kb_listener.daemon = True
        threading.Thread(target=self._kb_listener.start, daemon=True).start()

    def _hotkey_start_recording(self):
        if self._recording or self._playing:
            return
        self.root.iconify()
        self.root.after(350, self._start_recording)

    def _hotkey_toggle_playing(self):
        if self._recording:
            return
        if self._playing:
            self._stop_playing()
        elif self._recorder.events:
            self._start_playing()


def main():
    root = tk.Tk()
    JJClicker(root)
    root.update_idletasks()
    w = root.winfo_reqwidth()
    h = root.winfo_reqheight()
    root.geometry(f"{int(w * 1.15)}x{int(h * 1.15)}")
    root.mainloop()


if __name__ == "__main__":
    main()
