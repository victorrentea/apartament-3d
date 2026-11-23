// Room 3 extras: gaming setup on the MICKE desk (drawn from code), painting above the bed, hanging plants.
// Spliced into the page by build_furniture.py (PIECES / MODELS are substituted there).
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
const PIECES = /*__PIECES__*/;
const MODELS = {
/*__MODELS__*/
};
const sleep = ms => new Promise(r => setTimeout(r, ms));
while (!window.__ready) await sleep(50);
const { THREE, W, group } = window.__app;
const draco = new DRACOLoader().setDecoderPath('https://cdn.jsdelivr.net/npm/three@0.183.0/examples/jsm/libs/draco/gltf/');
const loader = new GLTFLoader().setDRACOLoader(draco);
const buf = b64 => Uint8Array.from(atob(b64), c => c.charCodeAt(0)).buffer;
const parsed = {};
for (const [name, b64] of Object.entries(MODELS))
  parsed[name] = await new Promise((res, rej) => loader.parse(buf(b64), '', res, rej));
draco.dispose();

// the desk belongs to the bedroom3 block: wait for it, then read the height of its top
for (let t = 0; !window.__furnitureBedroom3Ready && t < 200; t++) await sleep(100);
let deskTop = 0.75;
const desk = window.__furnitureBedroom3?.getObjectByName('b3-desk');
if (desk) { group.updateMatrixWorld(true); const b = new THREE.Box3().setFromObject(desk); deskTop = group.worldToLocal(new THREE.Vector3(0, b.max.y, 0)).y; }

// ---------- materials ----------
const std = o => new THREE.MeshStandardMaterial(o);
const black = std({ color: 0x15161a, roughness: 0.55, metalness: 0.3 });
const matte = std({ color: 0x1d1e22, roughness: 0.9 });
const steel = std({ color: 0x2a2c31, roughness: 0.4, metalness: 0.7 });
const glass = new THREE.MeshPhysicalMaterial({ color: 0x9fb4c8, roughness: 0.05, metalness: 0, transparent: true, opacity: 0.16, depthWrite: false, side: THREE.DoubleSide });
const lit = [];                                       // RGB parts: colour cycles slowly through the hue wheel
const rgb = (phase, sat = 1) => { const m = new THREE.MeshBasicMaterial({ color: 0xffffff, toneMapped: false }); lit.push({ m, phase, sat }); return m; };
const canvasTex = (w, h, draw) => { const c = document.createElement('canvas'); c.width = w; c.height = h; draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t; };
const rainbow = canvasTex(256, 4, (g, w, h) => { const gr = g.createLinearGradient(0, 0, w, 0);
  for (let i = 0; i <= 12; i++) gr.addColorStop(i / 12, `hsl(${i * 30 % 360} 100% 55%)`); g.fillStyle = gr; g.fillRect(0, 0, w, h); });
rainbow.wrapS = THREE.RepeatWrapping;
const rainbowMat = new THREE.MeshBasicMaterial({ map: rainbow, toneMapped: false });
const mesh = (geo, mat, x = 0, y = 0, z = 0, shadow = true) => { const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); m.castShadow = shadow; m.receiveShadow = shadow; return m; };
const box = (w, h, d, mat, x, y, z, shadow) => mesh(new THREE.BoxGeometry(w, h, d), mat, x, y, z, shadow);

// the picture on the screen: a synthwave racing game with its HUD (text shows at once if the screen were mirrored)
const gameTex = canvasTex(1376, 576, (g, w, h) => {
  const hz = h * 0.56;
  let gr = g.createLinearGradient(0, 0, 0, hz);
  gr.addColorStop(0, '#0b0630'); gr.addColorStop(0.55, '#5b1a8f'); gr.addColorStop(0.85, '#e0457b'); gr.addColorStop(1, '#ffb347');
  g.fillStyle = gr; g.fillRect(0, 0, w, hz);
  for (let i = 0; i < 160; i++) { g.fillStyle = `rgba(255,255,255,${0.3 + Math.random() * 0.7})`; g.fillRect(Math.random() * w, Math.random() * hz * 0.6, 2, 2); }
  gr = g.createLinearGradient(0, hz - 210, 0, hz); gr.addColorStop(0, '#fff275'); gr.addColorStop(0.5, '#ff8a3d'); gr.addColorStop(1, '#ff2e88');
  g.fillStyle = gr; g.beginPath(); g.arc(w / 2, hz - 30, 150, Math.PI, 0); g.fill();
  g.fillStyle = '#5b1a8f'; for (let i = 0; i < 5; i++) g.fillRect(w / 2 - 160, hz - 110 + i * 19, 320, 3 + i * 1.6);   // sun stripes
  const ridge = (col, amp, base, seed) => { g.fillStyle = col; g.beginPath(); g.moveTo(0, hz);
    for (let x = 0; x <= w; x += 43) g.lineTo(x, hz - base - amp * Math.abs(Math.sin(x * 0.011 + seed) * Math.cos(x * 0.004 + seed * 2)) * (0.35 + Math.abs(x - w / 2) / w * 1.6));
    g.lineTo(w, hz); g.fill(); };
  ridge('#2a1065', 150, 8, 1.3); ridge('#150833', 95, 4, 4.1);
  gr = g.createLinearGradient(0, hz, 0, h); gr.addColorStop(0, '#2b0a55'); gr.addColorStop(1, '#070214');
  g.fillStyle = gr; g.fillRect(0, hz, w, h - hz);
  g.strokeStyle = '#19e6ff'; g.shadowColor = '#19e6ff'; g.shadowBlur = 8; g.lineWidth = 2;
  for (let i = -16; i <= 16; i++) { g.beginPath(); g.moveTo(w / 2 + i * 22, hz); g.lineTo(w / 2 + i * 190, h); g.stroke(); }
  for (let i = 0; i < 12; i++) { const y = hz + (h - hz) * Math.pow(i / 12, 2.1); g.beginPath(); g.moveTo(0, y); g.lineTo(w, y); g.stroke(); }
  g.shadowBlur = 0;
  // the road and the player's car
  g.fillStyle = 'rgba(10,4,30,0.85)'; g.beginPath(); g.moveTo(w / 2 - 14, hz); g.lineTo(w / 2 + 14, hz); g.lineTo(w / 2 + 300, h); g.lineTo(w / 2 - 300, h); g.fill();
  g.fillStyle = '#ffe14d'; for (let i = 1; i < 7; i++) { const t = Math.pow(i / 7, 2.1), y = hz + (h - hz) * t; g.fillRect(w / 2 - 3 - t * 6, y, 6 + t * 12, 10 + t * 26); }
  const cy = h - 78; g.shadowColor = '#ff2e88'; g.shadowBlur = 22;
  g.fillStyle = '#e8143c'; g.beginPath(); g.moveTo(w / 2 - 120, cy + 50); g.lineTo(w / 2 - 104, cy); g.lineTo(w / 2 - 60, cy - 34); g.lineTo(w / 2 + 60, cy - 34); g.lineTo(w / 2 + 104, cy); g.lineTo(w / 2 + 120, cy + 50); g.fill();
  g.shadowBlur = 0; g.fillStyle = '#12203a'; g.beginPath(); g.moveTo(w / 2 - 84, cy - 2); g.lineTo(w / 2 - 54, cy - 28); g.lineTo(w / 2 + 54, cy - 28); g.lineTo(w / 2 + 84, cy - 2); g.fill();
  g.fillStyle = '#ffec9e'; g.fillRect(w / 2 - 112, cy + 14, 44, 12); g.fillRect(w / 2 + 68, cy + 14, 44, 12);
  g.fillStyle = '#0a0a12'; g.fillRect(w / 2 - 118, cy + 44, 40, 22); g.fillRect(w / 2 + 78, cy + 44, 40, 22);
  // HUD
  g.font = 'bold 30px Menlo, monospace'; g.textBaseline = 'top';
  g.fillStyle = 'rgba(0,0,0,0.45)'; g.fillRect(24, 22, 330, 52); g.fillRect(w - 250, 22, 226, 52); g.fillRect(24, h - 92, 300, 68);
  g.fillStyle = '#3dff7a'; g.fillRect(34, 32, 230, 14); g.fillStyle = '#19e6ff'; g.fillRect(34, 52, 170, 12);
  g.fillStyle = '#fff'; g.fillText('87', 278, 30); g.fillStyle = '#3dff7a'; g.fillText('144 FPS', w - 236, 32);
  g.fillStyle = '#fff'; g.font = 'bold 44px Menlo, monospace'; g.fillText('LAP 2/3', 40, h - 82);
  g.font = 'bold 54px Menlo, monospace'; g.textAlign = 'right'; g.fillStyle = '#ffe14d'; g.fillText('217', w - 150, h - 100);
  g.font = 'bold 24px Menlo, monospace'; g.fillStyle = '#fff'; g.fillText('km/h', w - 70, h - 74); g.textAlign = 'left';
  g.strokeStyle = '#fff'; g.lineWidth = 4; g.beginPath(); g.arc(w - 150, h - 80, 96, Math.PI * 0.85, Math.PI * 2.15); g.stroke();
  g.strokeStyle = '#ff2e88'; g.lineWidth = 8; g.beginPath(); g.arc(w - 150, h - 80, 96, Math.PI * 0.85, Math.PI * 1.75); g.stroke();
  g.fillStyle = 'rgba(0,0,0,0.5)'; g.beginPath(); g.arc(w - 120, 170, 76, 0, 7); g.fill();                                     // minimap
  g.strokeStyle = '#19e6ff'; g.lineWidth = 5; g.beginPath(); g.ellipse(w - 120, 170, 50, 34, 0.5, 0, 7); g.stroke();
  g.fillStyle = '#ff2e88'; g.beginPath(); g.arc(w - 150, 142, 7, 0, 7); g.fill();
});

// bend a geometry built flat around x into a cylinder arc of radius R whose axis stands at z = +R (front = +z, concave)
function bend(geo, R) {
  const p = geo.attributes.position;
  for (let i = 0; i < p.count; i++) { const a = p.getX(i) / R, r = R - p.getZ(i); p.setX(i, r * Math.sin(a)); p.setZ(i, R - r * Math.cos(a)); }
  p.needsUpdate = true; geo.computeVertexNormals(); return geo;
}

// ---------- pieces drawn from code: local frame +z = front, x across, y up, bottom at y = 0 ----------
const DRAW = {
  monitor() {                                         // 34" 21:9, 1000R
    const g = new THREE.Group(), R = 1.0, sw = 0.797, sh = 0.334, cyS = 0.29;       // cyS = screen centre above the desk
    const body = new THREE.BoxGeometry(sw + 0.012, sh + 0.026, 0.014, 56, 1, 1); body.translate(0, -0.007, -0.007);
    g.add(mesh(bend(body, R), black, 0, cyS, 0));
    const scr = new THREE.PlaneGeometry(sw, sh, 56, 1); scr.translate(0, 0, 0.0008);
    g.add(mesh(bend(scr, R), new THREE.MeshBasicMaterial({ map: gameTex, toneMapped: false }), 0, cyS, 0, false));
    const rear = new THREE.BoxGeometry(0.50, 0.22, 0.028, 30, 1, 1); rear.translate(0, 0, -0.027);
    g.add(mesh(bend(rear, R), black, 0, cyS, 0));
    const ring = mesh(new THREE.TorusGeometry(0.06, 0.006, 8, 40), rgb(0.6), 0, cyS, -0.043, false); g.add(ring);               // rear light ring
    g.add(box(0.012, 0.003, 0.002, rgb(0.33, 0.6), sw / 2 - 0.03, cyS - sh / 2 - 0.012, 0.012 + R * (1 - Math.cos((sw / 2 - 0.03) / R)), false)); // power LED
    // stand: neck leaning forward from a foot hub behind the panel, two legs opening in a V towards the user
    const hub = new THREE.Vector3(0, 0.012, -0.11), top = new THREE.Vector3(0, cyS - 0.02, -0.05);
    const neck = box(0.055, hub.distanceTo(top), 0.022, steel, 0, 0, 0); neck.position.copy(hub).lerp(top, 0.5);
    neck.rotation.x = Math.atan2(top.z - hub.z, top.y - hub.y); g.add(neck);
    g.add(mesh(new THREE.CylinderGeometry(0.03, 0.034, 0.024, 24), steel, 0, 0.012, -0.11));
    for (const s of [-1, 1]) { const tip = new THREE.Vector3(s * 0.25, 0.007, 0.09), a = new THREE.Vector3(0, 0.007, -0.11);
      const leg = box(0.03, 0.014, a.distanceTo(tip), steel, 0, 0, 0); leg.position.copy(a).lerp(tip, 0.5); leg.rotation.y = Math.atan2(tip.x - a.x, tip.z - a.z); g.add(leg); }
    return g;
  },
  tower(p) {                                          // mid-tower, glass on the -x side and on the front
    const g = new THREE.Group(), w = p.dims_mm.w / 1000, h = p.dims_mm.h / 1000, d = p.dims_mm.d / 1000, f = 0.012, t = 0.006;
    for (const sx of [-1, 1]) for (const sz of [-1, 1]) g.add(box(0.03, f, 0.04, matte, sx * (w / 2 - 0.03), f / 2, sz * (d / 2 - 0.05)));     // feet
    const y0 = f, H = h - f, yc = y0 + H / 2;
    g.add(box(w, t, d, black, 0, y0 + t / 2, 0));                                     // floor
    g.add(box(w, t, d, black, 0, h - t / 2, 0));                                      // roof
    g.add(box(w, H, t, black, 0, yc, -d / 2 + t / 2));                                // rear
    g.add(box(t, H, d, black, w / 2 - t / 2, yc, 0));                                 // closed side (+x)
    for (const [x, z] of [[-w / 2 + 0.005, d / 2 - 0.005], [-w / 2 + 0.005, -d / 2 + 0.005], [w / 2 - 0.005, d / 2 - 0.005]]) g.add(box(0.01, H, 0.01, black, x, yc, z));   // corner posts
    g.add(box(0.004, H - 0.02, d - 0.02, glass, -w / 2 + 0.002, yc, 0, false));       // tempered-glass side
    g.add(box(w - 0.02, H - 0.02, 0.004, glass, 0, yc, d / 2 - 0.002, false));        // glass front
    const inner = std({ color: 0x1a1024, roughness: 0.7, emissive: 0x2a0a4a, emissiveIntensity: 0.55 });   // interior bathed in RGB light
    const shroudH = 0.085;
    g.add(box(w - 2 * t, shroudH, d - 0.07, inner, 0, y0 + t + shroudH / 2, -0.03, false));                 // PSU shroud
    g.add(box(0.002, 0.012, 0.16, rgb(0.85), -w / 2 + t + 0.004, y0 + t + shroudH - 0.02, -0.05, false));
    const mbx = w / 2 - t - 0.006;
    g.add(box(0.004, 0.27, 0.25, std({ color: 0x0c0c10, roughness: 0.6, emissive: 0x18062c, emissiveIntensity: 0.6 }), mbx, y0 + shroudH + 0.16, -0.05, false));  // motherboard
    const gy = y0 + shroudH + 0.075;                                                  // graphics card
    g.add(box(0.125, 0.042, 0.27, std({ color: 0x232429, roughness: 0.45, metalness: 0.5, emissive: 0x150525, emissiveIntensity: 0.5 }), mbx - 0.066, gy, -0.045, false));
    g.add(box(0.003, 0.008, 0.24, rgb(0.05), mbx - 0.13, gy + 0.012, -0.045, false));
    for (const z of [-0.11, 0.02]) { const fan = mesh(new THREE.TorusGeometry(0.036, 0.004, 6, 28), rgb(0.5 + z), mbx - 0.066, gy - 0.022, z, false); fan.rotation.x = Math.PI / 2; g.add(fan); }
    const cy = y0 + shroudH + 0.2, cz = -0.06;                                        // CPU water block + tubes to the roof radiator
    const pump = mesh(new THREE.CylinderGeometry(0.033, 0.033, 0.04, 28), black, mbx - 0.022, cy, cz, false); pump.rotation.z = Math.PI / 2; g.add(pump);
    const pr = mesh(new THREE.TorusGeometry(0.027, 0.005, 8, 32), rgb(0.72), mbx - 0.044, cy, cz, false); pr.rotation.y = Math.PI / 2; g.add(pr);
    const pd = mesh(new THREE.CircleGeometry(0.02, 24), rgb(0.15, 0.5), mbx - 0.0425, cy, cz, false); pd.rotation.y = -Math.PI / 2; g.add(pd);
    for (const dz of [-0.012, 0.012]) g.add(mesh(new THREE.CylinderGeometry(0.005, 0.005, h - 0.04 - cy, 8), matte, mbx - 0.03, (cy + h - 0.04) / 2, cz + dz + 0.03, false));
    for (let i = 0; i < 4; i++) { const z = cz + 0.062 + i * 0.011;                   // RAM
      g.add(box(0.035, 0.115, 0.006, matte, mbx - 0.02, cy, z, false)); g.add(box(0.006, 0.115, 0.0062, rgb(0.9 + i * 0.07), mbx - 0.04, cy, z, false)); }
    g.add(box(w - 0.03, 0.026, d - 0.1, matte, 0, h - t - 0.016, -0.03, false));       // radiator under the roof
    const fan = (x, y, z, axis, r, ph) => { const k = new THREE.Group(); k.position.set(x, y, z);
      k.add(mesh(new THREE.TorusGeometry(r, 0.0055, 8, 36), rgb(ph), 0, 0, 0, false));
      k.add(mesh(new THREE.CylinderGeometry(r * 0.3, r * 0.3, 0.012, 20).rotateX(Math.PI / 2), black, 0, 0, 0, false));
      k.add(mesh(new THREE.CircleGeometry(r * 0.2, 20), rgb(ph + 0.1, 0.7), 0, 0, 0.0065, false));
      for (let i = 0; i < 7; i++) { const b = box(r * 0.68, 0.017, 0.002, std({ color: 0x30323a, roughness: 0.4, emissive: 0x241040, emissiveIntensity: 0.8, transparent: true, opacity: 0.85 }), 0, 0, 0, false);
        const a = i / 7 * Math.PI * 2; b.position.set(Math.cos(a) * r * 0.62, Math.sin(a) * r * 0.62, 0); b.rotation.z = a + 0.5; b.rotation.x = 0.35; k.add(b); }
      if (axis === 'y') k.rotation.x = Math.PI / 2; if (axis === 'x') k.rotation.y = -Math.PI / 2;
      g.add(k); };
    for (let i = 0; i < 3; i++) fan(0, y0 + 0.072 + i * 0.132, d / 2 - 0.024, 'z', 0.057, i * 0.12);          // three front intakes
    fan(0, cy + 0.01, -d / 2 + 0.022, 'z', 0.052, 0.45);                                                      // rear exhaust
    for (const z of [-0.1, 0.035]) fan(0, h - t - 0.034, z, 'y', 0.055, 0.3 + z);                              // radiator fans
    g.add(box(0.05, 0.004, 0.012, std({ color: 0x08080a }), 0.03, h + 0.001, d / 2 - 0.03, false));            // top I/O
    g.add(mesh(new THREE.CylinderGeometry(0.006, 0.006, 0.003, 16), rgb(0.55, 0.4), -0.03, h + 0.0015, d / 2 - 0.03, false));
    return g;
  },
  mousepad() {
    const g = new THREE.Group(), w = 0.80, d = 0.30;
    const edge = new THREE.BoxGeometry(w + 0.008, 0.003, d + 0.008);
    g.add(mesh(edge, rainbowMat, 0, 0.0016, 0, false));                                // glowing LED rim
    const top = mesh(new RoundedBoxGeometry(w, 0.004, d, 2, 0.002), std({ color: 0x101114, roughness: 1 }), 0, 0.002, 0); top.castShadow = false; g.add(top);
    return g;
  },
  keyboard() {                                        // tenkeyless, 36 x 13 cm
    const g = new THREE.Group(), w = 0.362, d = 0.132;
    g.add(mesh(new THREE.BoxGeometry(w - 0.004, 0.003, d - 0.004), rainbowMat, 0, 0.0015, 0, false));            // underglow
    const tilt = new THREE.Group(); tilt.rotation.x = 0.07; tilt.position.y = 0.012; g.add(tilt);
    tilt.add(mesh(new RoundedBoxGeometry(w, 0.018, d, 3, 0.004), black, 0, 0, 0));
    const u = 0.019, keys = [];                       // [x, z, width in key units]
    const x0 = -w / 2 + 0.016, z0 = -d / 2 + 0.017;
    const row = (r, widths, x = x0) => { for (const k of widths) { if (k > 0) keys.push([x + k * u / 2, z0 + r * u + (r ? 0.003 : 0), k]); x += Math.abs(k) * u; } };
    row(0, [1, -1, 1, 1, 1, 1, -.5, 1, 1, 1, 1, -.5, 1, 1, 1, 1, -.25, 1, 1, 1]);
    row(1, [...Array(13).fill(1), 2, -.25, 1, 1, 1]);
    row(2, [1.5, ...Array(12).fill(1), 1.5, -.25, 1, 1, 1]);
    row(3, [1.75, ...Array(11).fill(1), 2.25]);
    row(4, [2.25, ...Array(10).fill(1), 2.75, -1.25, 1]);
    row(5, [1.25, 1.25, 1.25, 6.25, 1.25, 1.25, 1.25, 1.25, -.25, 1, 1, 1]);
    const plate = (c0, c1, r0, r1) => tilt.add(box((c1 - c0) * u - 0.003, 0.002, (r1 - r0 + 1) * u - 0.003, rainbowMat,     // lit plate, only under keys
      x0 + (c0 + c1) / 2 * u, 0.0092, z0 + (r0 + r1) / 2 * u + (r0 ? 0.003 : 0), false));
    plate(0, 15, 1, 5); plate(15.25, 18.25, 1, 2); plate(15.25, 18.25, 5, 5); plate(16.25, 17.25, 4, 4);
    const cap = new THREE.BoxGeometry(1, 1, 1), inst = new THREE.InstancedMesh(cap, std({ color: 0x24262b, roughness: 0.65 }), keys.length);
    const m4 = new THREE.Matrix4();
    keys.forEach(([x, z, k], i) => { m4.makeScale(k * u - 0.0035, 0.008, u - 0.0035); m4.setPosition(x, 0.0135, z); inst.setMatrixAt(i, m4); });
    inst.castShadow = true; tilt.add(inst);
    return g;
  },
  mouse() {
    const g = new THREE.Group();
    const dome = new THREE.SphereGeometry(1, 28, 14, 0, Math.PI * 2, 0, Math.PI / 2); dome.scale(0.032, 0.038, 0.06);
    g.add(mesh(dome, std({ color: 0x17181c, roughness: 0.5, metalness: 0.2 }), 0, 0.001, 0));
    const strip = new THREE.TorusGeometry(1, 0.035, 6, 40); strip.rotateX(Math.PI / 2); strip.scale(0.0315, 0.03, 0.0595);
    g.add(mesh(strip, rgb(0.2), 0, 0.006, 0, false));
    const wheel = mesh(new THREE.CylinderGeometry(0.008, 0.008, 0.007, 16), rgb(0.6), 0, 0.031, -0.03, false); wheel.rotation.z = Math.PI / 2; g.add(wheel);
    g.add(box(0.0012, 0.004, 0.045, std({ color: 0x050506 }), 0, 0.033, -0.035, false));
    g.add(mesh(new THREE.CircleGeometry(0.007, 16).rotateX(-Math.PI / 2), rgb(0.2, 0.8), 0, 0.0352, 0.022, false));      // logo
    const cable = mesh(new THREE.CylinderGeometry(0.0018, 0.0018, 0.14, 6).rotateX(Math.PI / 2), matte, 0.01, 0.004, -0.128); cable.rotation.y = -0.15; g.add(cable);
    return g;
  },
  headset() {                                         // standing on its ear cups, band arching over (cups' axis = z)
    const g = new THREE.Group(), r = 0.088, cy = 0.062, red = std({ color: 0xc8102e, roughness: 0.4, metalness: 0.5 });
    const dark = std({ color: 0x141416, roughness: 0.8 });
    g.add(mesh(new THREE.TorusGeometry(r, 0.006, 8, 48, Math.PI).rotateY(Math.PI / 2), red, 0, cy + 0.03, 0));                  // steel band
    g.add(mesh(new THREE.TorusGeometry(r + 0.004, 0.0125, 10, 32, Math.PI * 0.5).rotateZ(Math.PI * 0.25).rotateY(Math.PI / 2), dark, 0, cy + 0.03, 0));   // padding on top
    for (const s of [-1, 1]) {
      const cup = new THREE.Group(); cup.position.set(0, cy, s * (r - 0.012)); cup.rotation.x = s * 0.1; g.add(cup);
      const shell = new THREE.CylinderGeometry(0.036, 0.042, 0.026, 32).rotateX(s * Math.PI / 2); shell.scale(1, 1.3, 1);
      cup.add(mesh(shell, black, 0, 0, 0));
      const pad = new THREE.TorusGeometry(0.033, 0.011, 10, 32); pad.scale(1, 1.3, 1);
      cup.add(mesh(pad, std({ color: 0x0b0b0c, roughness: 1 }), 0, 0, -s * 0.017));                                              // ear cushion (inside)
      const plate = new THREE.CylinderGeometry(0.024, 0.024, 0.003, 28).rotateX(Math.PI / 2); plate.scale(1, 1.3, 1);
      cup.add(mesh(plate, red, 0, 0, s * 0.0135));
      cup.add(box(0.008, 0.07, 0.004, red, 0, 0.045, s * 0.012));                                                               // yoke up to the band
    }
    const mic = mesh(new THREE.CylinderGeometry(0.003, 0.003, 0.11, 8).rotateZ(Math.PI / 2), dark, 0.05, cy - 0.02, -(r - 0.012)); mic.rotation.z = -0.35; g.add(mic);
    g.add(mesh(new THREE.SphereGeometry(0.008, 12, 8), dark, 0.102, cy - 0.039, -(r - 0.012)));
    return g;
  },
  bracket() {                                         // wall console: origin on the wall face at arm height, +z = out of the wall
    const g = new THREE.Group(), iron = std({ color: 0x1b1b1d, roughness: 0.5, metalness: 0.6 }), L = 0.2;
    g.add(box(0.03, 0.17, 0.005, iron, 0, -0.06, 0.0025));
    g.add(box(0.012, 0.012, L, iron, 0, 0, L / 2));
    const br = box(0.008, 0.008, Math.hypot(0.13, 0.12), iron, 0, -0.06, 0.07); br.rotation.x = Math.atan2(0.12, 0.13); g.add(br);
    const hook = mesh(new THREE.TorusGeometry(0.012, 0.0028, 8, 20, Math.PI * 1.5), iron, 0, -0.016, L - 0.01); hook.rotation.y = Math.PI / 2; g.add(hook);
    g.add(mesh(new THREE.SphereGeometry(0.008, 12, 8), iron, 0, 0, L));
    return g;
  },
};

// the IKEA materials are metallic in places; without an environment map they render black
const face = hex => { const c = document.createElement('canvas'); c.width = c.height = 16; const g = c.getContext('2d'); g.fillStyle = hex; g.fillRect(0, 0, 16, 16); return c; };
const env = new THREE.CubeTexture(['#e9e6dc', '#e9e6dc', '#ffffff', '#b8916a', '#e2e0d6', '#dcdad0'].map(face));
env.colorSpace = THREE.SRGBColorSpace; env.needsUpdate = true;

const root = new THREE.Group(); root.name = 'furniture-bedroom3-extras';
for (const p of PIECES) {
  const pivot = new THREE.Group(); pivot.name = p.id;
  pivot.rotation.y = p.rot_deg * Math.PI / 180;
  if (p.kind) {
    pivot.add(DRAW[p.kind](p));
    pivot.position.copy(W(p.x, p.y, p.on_desk != null ? deskTop + p.on_desk : p.h));
  } else {
    const model = parsed[p.model].scene.clone(true);
    model.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true;
      for (const m of [].concat(o.material)) { m.envMap = env; m.envMapIntensity = 0.3; m.needsUpdate = true; } } });
    const wall = p.orient === 'wall';
    if (wall) model.rotation.x = (p.flip ?? 1) * Math.PI / 2;        // stand the flat picture up: its face (+y) turns to +z
    if (p.upside_down) model.rotation.x = Math.PI;                   // the CHILISTRÅN GLB comes pot-up, rod-down
    const b = new THREE.Box3().setFromObject(model), c = b.getCenter(new THREE.Vector3());
    if (p.hook_h != null && p.sink == null) {                        // hanging pot: top of the cords at the hook
      model.position.set(-c.x, -b.max.y, -c.z); pivot.position.copy(W(p.x, p.y, p.hook_h));
    } else if (p.sink != null) {                                     // plant standing in the hanging pot (pot model is 0.975 m tall, origin at its bottom)
      model.position.set(0, 0, 0); pivot.position.copy(W(p.x, p.y, p.hook_h - 0.975 + p.sink));
    } else {
      model.position.set(-c.x, wall ? -c.y : -b.min.y, -c.z); pivot.position.copy(W(p.x, p.y, p.h ?? 0));
    }
    pivot.add(model);
  }
  root.add(pivot);
}

// follow the page's wall-cut slider, like the walls do
const Hw = window.__app.DATA.H.wall, cutIn = document.getElementById('cut');
const cutPlane = new THREE.Plane(new THREE.Vector3(0, -1, 0), Hw + 0.01);
const syncCut = () => { if (cutIn) cutPlane.constant = +cutIn.value >= Hw ? Hw + 0.01 : +cutIn.value; };
cutIn?.addEventListener('input', syncCut); syncCut();
root.traverse(o => { if (o.isMesh) for (const m of [].concat(o.material)) m.clippingPlanes = [cutPlane]; });

// slow RGB wave
const col = new THREE.Color();
const tick = () => { const t = performance.now() / 1000;
  for (const { m, phase, sat } of lit) m.color.copy(col.setHSL((t * 0.06 + phase + 10) % 1, 1, 0.5 + (1 - sat) * 0.35));
  rainbow.offset.x = -t * 0.08; };
tick(); setInterval(tick, 100);

group.add(root);
window.__furnitureBedroom3Extras = root;
window.__b3xParsed = parsed;
window.__furnitureBedroom3ExtrasReady = true;
