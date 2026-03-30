# JJClicker

**Verzia:** 1.0.0
**Autor:** Juraj Jajcaj
**Platforma:** macOS (alternatíva pre Windows: `JJClicker_Windows.py`)

---

## Čo je JJClicker?

JJClicker je desktopová aplikácia s grafickým rozhraním (GUI) na automatizáciu kliknutí myšou a nahrávanie makier pohybu kurzora. Navrhnutá pre macOS s tmavým Catppuccin témou.

---

## Funkcie

### Záložka Clicker
- Nastavenie cieľovej pozície (X, Y) s 3-sekundovým odpočítaním
- Výber typu kliknutia: ľavé / pravé
- Nastaviteľný interval kliknutia v milisekundách
- Opakovanie: nekonečné alebo zadaný počet
- Zastavenie klávesovou skratkou **ESC**

### Záložka Recorder
- Nahrávanie pohybu myši a kliknutí s časovaním
- Prehrávanie nahraných sekvencií
- Opakovanie prehrávania: nekonečné alebo zadaný počet cyklov
- Pauza medzi cyklami: žiadna / fixná (sekundy) / náhodná (min–max)
- Ukladanie a načítavanie pomenovaných šablón
- Notifikácia po dokončení všetkých cyklov
- Zastavenie klávesovou skratkou **ESC**

---

## Spustenie (macOS)

### Možnosť 1 — Dock ikona (bez terminálu)
1. Otvor Finder → `Dokumenty/JJClicker/`
2. Presuň `JJClicker.app` do Docku
3. Klikni na ikonu v Docku

> **Dôležité:** Pri prvom spustení cez .app môže byť potrebné udeliť oprávnenia
> **python3** v `Systémové nastavenia → Súkromie a bezpečnosť → Accessibility`

### Možnosť 2 — Terminal.app (odporúčané pri prvom nastavení)
Dvakrát klikni na `JJClicker.command` vo Finderi — otvorí sa Terminal.app a aplikácia sa spustí.

---

## Požiadavky (macOS)

```bash
brew install python-tk@3.13
pip3 install pynput
```

### Potrebné systémové oprávnenia
| Oprávnenie | Kde udeliť | Na čo |
|---|---|---|
| **Accessibility** | Systémové nastavenia → Súkromie → Accessibility | Klikanie myšou (Clicker + prehrávanie Recorder) |
| **Input Monitoring** | Systémové nastavenia → Súkromie → Input Monitoring | Nahrávanie pohybu myši (Recorder) |

---

## Spustenie ikony (vytvorenie AppIcon.icns)

```bash
cd ~/Documents/JJClicker
python3 create_icon.py
```

---

## Windows

Aplikácia **nie je priamo spustiteľná na Windows** kvôli závislosti na macOS Quartz framework.
Pre Windows je k dispozícii alternatívna verzia:

```
JJClicker_Windows.py
```

### Požiadavky (Windows)
```powershell
pip install pynput
pip install pillow        # voliteľné, len pre ikonu
pip install plyer         # voliteľné, pre notifikácie
```

```powershell
python JJClicker_Windows.py
```

> Na Windows nie sú potrebné žiadne špeciálne oprávnenia — myš je ovládaná cez Windows API (ctypes/SendInput).

---

## Klávesové skratky

| Skratka | Akcia |
|---|---|
| **ESC** | Zastaví klikanie / nahrávanie / prehrávanie |

---

## Štruktúra súborov

```
JJClicker/
├── JJClicker.py            # Hlavná aplikácia (macOS)
├── JJClicker_Windows.py    # Alternatíva pre Windows
├── JJClicker.command       # Spúšťač pre Terminal.app (macOS)
├── JJClicker.app/          # Aplikačný balíček pre Dock (macOS)
│   └── Contents/
│       ├── Info.plist
│       ├── MacOS/JJClicker
│       └── Resources/AppIcon.icns
├── create_icon.py          # Generátor ikony (spustiť raz)
└── README.md
```
