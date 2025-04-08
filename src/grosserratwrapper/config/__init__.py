from pathlib import Path

# ab Python3.11 steht toml in der Standard-Bibliothek zur Verfügung,
# hier muss noch tomli importiert werden.
import tomli

path = Path(__file__).parent / "config.toml"
# Lade die Konfigurationsdatei und erstelle dicts für die Teilmodule von KlimametrikPy
with path.open(mode="rb") as fp:
    conf = tomli.load(fp)
    geschaeftstypen = conf["geschaeftstypen"]

__all__ = ["geschaeftstypen"]
