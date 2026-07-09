"""
ensure_playwright.py

Streamlit Cloud (i inne środowiska "gołego" pip install) instaluje bibliotekę
`playwright` z requirements.txt, ale NIE pobiera binarki przeglądarki
(Chromium) — to wymaga osobnej komendy `playwright install`, która nigdy
nie jest uruchamiana automatycznie.

Efekt: BrowserType.launch: Executable doesn't exist at
.../ms-playwright/chromium-.../chrome-linux64/chrome

Ten moduł sprawdza, czy Chromium jest zainstalowane, a jeśli nie —
instaluje je (raz, przy pierwszym uruchomieniu po restarcie kontenera)
i zostawia znacznik, żeby przy kolejnych odświeżeniach nie tracić czasu
na ponowną instalację.

Użycie — dodaj na samej górze download_invoices.py oraz save_login.py
(przed `from playwright...` / `import playwright`):

    from ensure_playwright import ensure_chromium_installed
    ensure_chromium_installed()

Plik musi leżeć w tym samym katalogu co download_invoices.py / save_login.py
(czyli w katalogu głównym repo, obok data_refresh.py).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Znacznik pilnujący, żeby nie instalować Chromium przy każdym uruchomieniu
_MARKER_PATH = Path.home() / ".cache" / "ms-playwright" / ".chromium_installed"


def _chromium_binary_exists() -> bool:
    """Szybkie sprawdzenie, czy binarka chromium faktycznie istnieje na dysku."""
    cache_dir = Path.home() / ".cache" / "ms-playwright"
    if not cache_dir.exists():
        return False
    # Szukamy dowolnego katalogu chromium-* zawierającego plik wykonywalny 'chrome'
    for chromium_dir in cache_dir.glob("chromium-*"):
        for candidate in chromium_dir.rglob("chrome"):
            if candidate.is_file():
                return True
    return False


def ensure_chromium_installed(timeout: int = 300) -> None:
    """
    Upewnia się, że Chromium dla Playwrighta jest zainstalowane.
    Bezpieczne do wywołania wielokrotnie — jeśli przeglądarka już jest,
    funkcja natychmiast wraca bez żadnej dodatkowej pracy.

    Rzuca RuntimeError, jeśli instalacja się nie powiedzie (np. brak
    dostępu do sieci albo brak miejsca na dysku).
    """
    if _MARKER_PATH.exists() and _chromium_binary_exists():
        return

    if _chromium_binary_exists():
        _MARKER_PATH.parent.mkdir(parents=True, exist_ok=True)
        _MARKER_PATH.touch()
        return

    # Chromium nie znaleziony — instalujemy.
    # --with-deps próbuje też doinstalować systemowe biblioteki (apt),
    # ale na Streamlit Cloud (bez uprawnień sudo) ta część może się nie
    # udać — dlatego systemowe zależności trzymamy dodatkowo w packages.txt.
    result = subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )

    if result.returncode != 0:
        details = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            "Nie udało się zainstalować przeglądarki Chromium dla Playwrighta: "
            f"{details}"
        )

    _MARKER_PATH.parent.mkdir(parents=True, exist_ok=True)
    _MARKER_PATH.touch()


if __name__ == "__main__":
    # Pozwala też ręcznie sprawdzić / wymusić instalację:
    #   python ensure_playwright.py
    ensure_chromium_installed()
    print("OK: Chromium jest zainstalowane i gotowe do użycia.")
