// Living room (room 1) furniture: page code template for build_living.py (it fills in the pieces, models and Draco path).
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
const PIECES = __PIECES__;
const MODELS = __MODELS__;
while (!window.__ready) await new Promise(r => setTimeout(r, 50));
const { THREE, W, group } = window.__app;
const draco = new DRACOLoader().setDecoderPath('__DRACO__');
const loader = new GLTFLoader().setDRACOLoader(draco);
const buf = b64 => Uint8Array.from(atob(b64), c => c.charCodeAt(0)).buffer;
const parsed = {};
for (const [name, b64] of Object.entries(MODELS))
  parsed[name] = await new Promise((res, rej) => loader.parse(buf(b64), '', res, rej));

const mesh = (geo, mat, x = 0, y = 0, z = 0) => { const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); return m; };
const std = (color, roughness = 0.5, metalness = 0) => new THREE.MeshStandardMaterial({ color, roughness, metalness });

// pieces drawn from code: local +z = front, origin = footprint centre (TV: panel centre)
const DRAW = {
  tv(d) {                                    // wall-mounted flat TV
    const w = d.w / 1000, h = d.h / 1000, D = d.d / 1000, g = new THREE.Group();
    const black = std(0x121212, 0.45, 0.2), metal = std(0x3a3c40, 0.35, 0.8);
    const glass = new THREE.MeshPhysicalMaterial({ color: 0x05070a, roughness: 0.06, metalness: 0.1, clearcoat: 1, clearcoatRoughness: 0.03, reflectivity: 0.6 });
    g.add(mesh(new THREE.BoxGeometry(w, h, D * 0.5), black, 0, 0, D * 0.25));                    // panel + thin bezel
    g.add(mesh(new THREE.BoxGeometry(w * 0.8, h * 0.78, D * 0.375), black, 0, 0, -D * 0.1875));  // rear housing
    g.add(mesh(new THREE.BoxGeometry(0.40, 0.30, D * 0.125), metal, 0, 0, -D * 0.4375));         // VESA wall bracket
    g.add(mesh(new THREE.PlaneGeometry(w - 0.016, h - 0.016), glass, 0, 0, D * 0.5 + 0.0005));  // glossy screen
    return g;
  },
  bike(d) {                                  // upright magnetic exercise bike, ~97 x 52 x 128 cm, flywheel at the front
    const g = new THREE.Group(), L = d.d / 1000, Wd = d.w / 1000;
    const silver = std(0xc3c7cc, 0.3, 0.75), black = std(0x1b1c1e, 0.45, 0.1), gloss = std(0x101113, 0.18, 0.2);
    const foam = std(0x222222, 0.9), accent = std(0xd6452f, 0.4, 0.1);
    const tube = (pts, r, mat) => g.add(new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts.map(p => new THREE.Vector3(...p))), 40, r, 12), mat));
    const cyl = (r, len, mat, x, y, z, axis = 'x') => {      // cylinder along the given axis
      const m = mesh(new THREE.CylinderGeometry(r, r, len, 28), mat, x, y, z);
      if (axis === 'x') m.rotation.z = Math.PI / 2; else if (axis === 'z') m.rotation.x = Math.PI / 2;
      g.add(m); return m;
    };
    const zf = L / 2 - 0.06, zr = -L / 2 + 0.06;               // front / rear base bars
    for (const z of [zf, zr]) {                                 // base bars with rubber end caps
      cyl(0.03, Wd - 0.06, silver, 0, 0.035, z);
      for (const s of [-1, 1]) cyl(0.034, 0.05, black, s * (Wd / 2 - 0.025), 0.035, z);
    }
    tube([[0, 0.05, zr], [0, 0.16, zr + 0.18], [0, 0.32, -0.08], [0, 0.40, 0.08]], 0.032, silver);   // rear frame up to the crank
    tube([[0, 0.05, zf], [0, 0.22, zf - 0.08], [0, 0.40, 0.12]], 0.032, silver);                       // front leg
    // flywheel housing (black disc, flat sides) with a red accent ring
    cyl(0.23, 0.11, gloss, 0, 0.42, 0.16);
    const ring = mesh(new THREE.TorusGeometry(0.205, 0.008, 8, 48), accent, 0.056, 0.42, 0.16); ring.rotation.y = Math.PI / 2; g.add(ring);
    const ring2 = ring.clone(); ring2.position.x = -0.056; g.add(ring2);
    // crank, cranks and pedals (opposite phase)
    cyl(0.035, 0.15, silver, 0, 0.38, -0.02);
    for (const s of [-1, 1]) {
      const a = s > 0 ? 0.6 : 0.6 + Math.PI, cx = 0, cy = 0.38 + Math.sin(a) * 0.17, cz = -0.02 + Math.cos(a) * 0.17;
      const crank = mesh(new THREE.BoxGeometry(0.022, 0.035, 0.19), silver, s * 0.09, (0.38 + cy) / 2, (-0.02 + cz) / 2);
      crank.rotation.x = -a; g.add(crank);
      const pedal = mesh(new THREE.BoxGeometry(0.11, 0.025, 0.07), black, s * 0.15, cy, cz); g.add(pedal);
      const strap = mesh(new THREE.BoxGeometry(0.09, 0.03, 0.012), accent, s * 0.15, cy + 0.025, cz); g.add(strap);
      void cx;
    }
    // seat post + saddle
    tube([[0, 0.40, -0.06], [0, 0.62, -0.15], [0, 0.86, -0.22]], 0.03, silver);
    cyl(0.036, 0.10, black, 0, 0.66, -0.165, 'y').rotation.x = -0.38;              // adjustment collar
    const saddle = new THREE.Group(); saddle.position.set(0, 0.90, -0.24);
    const s1 = mesh(new THREE.SphereGeometry(0.5, 24, 16), black); s1.scale.set(0.27, 0.11, 0.30); saddle.add(s1);
    const s2 = mesh(new THREE.SphereGeometry(0.5, 24, 16), black); s2.scale.set(0.09, 0.08, 0.20); s2.position.set(0, 0.005, 0.13); saddle.add(s2);
    g.add(saddle);
    // handlebar post, bar with foam grips, display
    tube([[0, 0.48, 0.10], [0, 0.80, 0.20], [0, 1.10, 0.26]], 0.03, silver);
    cyl(0.026, 0.30, silver, 0, 1.12, 0.26);
    for (const s of [-1, 1]) {
      tube([[s * 0.15, 1.12, 0.26], [s * 0.22, 1.15, 0.20], [s * 0.25, 1.20, 0.08], [s * 0.24, 1.23, -0.02]], 0.022, foam);
      cyl(0.024, 0.02, silver, s * 0.24, 1.23, -0.03, 'z');                         // grip end cap
    }
    const disp = new THREE.Group(); disp.position.set(0, 1.21, 0.29); disp.rotation.x = -0.6;
    disp.add(mesh(new THREE.BoxGeometry(0.19, 0.12, 0.04), black));
    const lcd = mesh(new THREE.PlaneGeometry(0.15, 0.075), new THREE.MeshStandardMaterial({ color: 0x9fd4c2, emissive: 0x2f8f74, emissiveIntensity: 0.9, roughness: 0.3 }), 0, 0.005, -0.0205);
    lcd.rotation.y = Math.PI; disp.add(lcd);                                          // screen faces the rider (towards -z)
    g.add(disp);
    return g;
  },
};

// a natural mix of books on each shelf: upright rows, a few leaning, now and then a small flat stack
function books(cfg, idPrefix) {
  const g = new THREE.Group(); g.name = idPrefix + '-books';
  let seed = cfg.seed || 7;
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  const COLORS = [0x8c2f2a, 0x2f4f6f, 0x3d6b4f, 0xc9a227, 0x5b3a6e, 0xd8d2c4, 0x1f2a36, 0xb5653a, 0x6f8fa6, 0x9a8f7a, 0x2c2c2c, 0xa33b55, 0xe7e1d2, 0x46705f];
  const mats = COLORS.map(c => std(c, 0.75));
  const W2 = cfg.inner_w / 2, depth = cfg.depth;
  for (const [ri, row] of cfg.rows.entries()) {
    const maxH = Math.min(row.clear - 0.025, 0.32), end = -W2 + (cfg.inner_w - 0.01) * row.fill;
    let x = -W2 + 0.01;
    while (x < end) {
      if (rnd() < 0.07 && end - x > 0.26) {                        // a small flat stack
        const n = 2 + Math.floor(rnd() * 3); let y = row.y;
        const sw = 0.17 + rnd() * 0.06;
        for (let k = 0; k < n; k++) {
          const t = 0.025 + rnd() * 0.02, b = mesh(new THREE.BoxGeometry(sw - k * 0.01, t, Math.min(depth - 0.03, 0.15 + rnd() * 0.06)), mats[Math.floor(rnd() * mats.length)], x + sw / 2, y + t / 2, cfg.z);
          b.rotation.y = (rnd() - 0.5) * 0.15; g.add(b); y += t;
        }
        x += sw + 0.01; continue;
      }
      const t = 0.016 + rnd() * 0.034, h = Math.max(0.15, maxH - rnd() * 0.12), dd = Math.min(depth - 0.02, 0.13 + rnd() * 0.08);
      const b = mesh(new THREE.BoxGeometry(t, h, dd), mats[Math.floor(rnd() * mats.length)]);
      if (rnd() < 0.05 && ri % 2 === 0) {                           // leaning on the previous book
        const a = 0.3; b.rotation.z = -a;
        b.position.set(x + Math.sin(a) * h / 2 + Math.cos(a) * t / 2, row.y + Math.cos(a) * h / 2 + Math.sin(a) * t / 2 - 0.004, cfg.z);
        x += Math.sin(a) * h + t + 0.01; g.add(b); x = end; continue;  // a leaning book ends the row
      }
      b.position.set(x + t / 2, row.y + h / 2, cfg.z + (rnd() - 0.5) * 0.01);
      g.add(b); x += t + 0.0015;
    }
  }
  return g;
}

const living = new THREE.Group(); living.name = 'furniture-living';
for (const p of PIECES) {
  const pivot = new THREE.Group(); pivot.name = p.id;
  if (p.kind) {
    pivot.add(DRAW[p.kind](p.dims_mm));
    pivot.position.copy(W(p.x, p.y, p.h || 0));
  } else {
    const model = parsed[p.model].scene.clone(true);
    model.scale.setScalar(p.scale);
    if (p.wall) model.rotation.x = p.flip * Math.PI / 2;           // stand the flat picture up: its face (+y) turns to +z
    const box = new THREE.Box3().setFromObject(model);
    const c = box.getCenter(new THREE.Vector3());
    model.position.set(-c.x, p.wall ? -c.y : -box.min.y, -c.z);     // footprint centre at the pivot, bottom on the floor
    pivot.add(model);
    if (p.books) pivot.add(books(p.books, p.id));
    pivot.position.copy(W(p.x, p.y, p.wall ? p.h : 0));              // wall pieces: h = centre height
  }
  pivot.rotation.y = p.rot_deg * Math.PI / 180;                      // world rotation.y = plan angle (CCW); front (+z) faces rot - 90
  living.add(pivot);
}
living.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
// follow the page's wall-cut slider ("Tăietură pereți"), so tall pieces don't stick out of a dollhouse cut
const Hw = window.__app.DATA.H.wall, cutIn = document.getElementById('cut');
const cutPlane = new THREE.Plane(new THREE.Vector3(0, -1, 0), Hw + 0.01);
const syncCut = () => { if (cutIn) cutPlane.constant = +cutIn.value >= Hw ? Hw + 0.01 : +cutIn.value; };
cutIn?.addEventListener('input', syncCut); syncCut();
living.traverse(o => { if (o.isMesh) for (const m of [].concat(o.material)) { m.clippingPlanes = [cutPlane]; m.clipShadows = true; } });
group.add(living);
draco.dispose();
window.__furnitureLiving = living;
window.__furnitureLivingReady = true;
