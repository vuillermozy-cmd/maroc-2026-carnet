"""Recalcule les tracés routiers du carnet (objet GEO de index.html) avec le routeur public OSRM.

Usage : python3 tools/routes.py > geo.json
Puis remplacer l'objet `const GEO = {...};` dans index.html par le contenu de geo.json,
et reporter les km / minutes affichés sur la sortie d'erreur dans DAYS[].drive.

Chaque jour est une liste de points [lon, lat] par lesquels la route doit passer.
On appelle curl plutôt que urllib : le Python système de macOS échoue sur le TLS d'OSRM.
"""
import json
import subprocess
import sys
import time

OSRM = "https://router.project-osrm.org/route/v1/driving/"
EPS = 0.0007  # tolérance de simplification, en degrés (~70 m)

DAYS = {
    # 21 : Marrakech -> col du Tichka -> Télouet (vallée de l'Ounila) -> Aït-Ben-Haddou
    "d21": [(-7.99, 31.63), (-7.381, 31.291), (-7.237, 31.287), (-7.129, 31.047)],
    # 22 : Aït-Ben-Haddou -> Ouarzazate -> Kelâat M'Gouna -> Boumalne Dadès
    "d22": [(-7.129, 31.047), (-6.89, 30.92), (-6.13, 31.24), (-5.988, 31.369)],
    # 23 : Boumalne -> lacets des gorges du Dadès -> Boumalne (on ne garde que l'aller)
    "d23": [(-5.988, 31.369), (-5.925, 31.53), (-5.988, 31.369)],
    # 24 : Boumalne -> Kelâat M'Gouna -> Skoura
    "d24": [(-5.988, 31.369), (-6.13, 31.24), (-6.56, 31.06)],
    # 26 : Skoura -> Ouarzazate -> col du Tichka -> Marrakech
    "d26": [(-6.56, 31.06), (-6.89, 30.92), (-7.381, 31.291), (-7.99, 31.63)],
}
OUTBOUND_ONLY = {"d23"}


def rdp(pts, eps):
    """Ramer-Douglas-Peucker."""
    if len(pts) < 3:
        return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    dx, dy = x2 - x1, y2 - y1
    length = (dx * dx + dy * dy) ** 0.5 or 1e-12
    dmax, idx = 0.0, 0
    for i in range(1, len(pts) - 1):
        x0, y0 = pts[i]
        d = abs(dy * x0 - dx * y0 + x2 * y1 - y2 * x1) / length
        if d > dmax:
            dmax, idx = d, i
    if dmax > eps:
        return rdp(pts[: idx + 1], eps)[:-1] + rdp(pts[idx:], eps)
    return [pts[0], pts[-1]]


def route(points):
    coords = ";".join(f"{lon},{lat}" for lon, lat in points)
    url = f"{OSRM}{coords}?overview=full&geometries=geojson"
    raw = subprocess.run(["curl", "-s", "-m", "30", url], capture_output=True, check=True).stdout
    return json.loads(raw)["routes"][0]


def main():
    geo = {}
    for key, points in DAYS.items():
        r = route(points)
        line = r["geometry"]["coordinates"]
        if key in OUTBOUND_ONLY:
            line = line[: len(line) // 2 + 1]
        geo[key] = [[round(x, 3), round(y, 3)] for x, y in rdp(line, EPS)]
        print(f"{key}: {r['distance'] / 1000:.0f} km, {r['duration'] / 60:.0f} min, {len(geo[key])} points", file=sys.stderr)
        time.sleep(1)  # serveur public : rester poli
    print(json.dumps(geo, separators=(",", ":")))


if __name__ == "__main__":
    main()
