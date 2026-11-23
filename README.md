# Apartament 3D

Un apartament de 85 m², reconstruit dintr-un releveu: plan 2D vectorial și o vizită 3D mobilată, direct în browser.

**Deschide:** https://victorrentea.github.io/apartament-3d/

- mută: drag · rotește: ⌘ + drag · zoom: rotiță · „Plimbare (WASD)” pentru mers prin casă, E deschide ușile
- ☀️/🌙 comută zi / noapte · „Produse” listează mobila cu linkuri · Shift pe o piesă arată numele și prețul, Shift + click deschide pagina produsului

## Ce e aici

- `plan.svg`, `plan.dxf`, `plan.dwg`: planul vectorial (pereți, uși, ferestre, cote), generat de `build_plan.py`
- `3d/gen3d.py` + `3d/template.html` → `3d/apartament3d.html` (Three.js, o singură pagină, fără server)
- `3d/furniture/<cameră>/`: mobila fiecărei camere (`furniture.json` = piese, poziții, produs, preț, link)

Regenerare: `.venv/bin/python 3d/gen3d.py plan.dxf 3d/apartament3d.html`

Modelele 3D de mobilier provin din paginile de produs IKEA România și rămân proprietatea IKEA; sunt folosite aici doar ca ilustrare, necomercial.
