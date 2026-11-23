// Decor pieces outside the living (bedroom 3 LED wall light): page code template for build_decor.py.
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

// soft glow painted on the wall around a ring lamp: bright annulus at the ring, fading outwards and inwards
function haloTexture(ringFrac, a) {
  const S = 512, c = document.createElement('canvas'); c.width = c.height = S;
  const g = c.getContext('2d'), r0 = S / 2, f = x => Math.min(1, Math.max(0, x));
  const grad = g.createRadialGradient(r0, r0, 0, r0, r0, r0);
  grad.addColorStop(0, `rgba(255,176,92,${0.18 * a})`);
  grad.addColorStop(f(ringFrac - 0.18), `rgba(255,176,92,${0.30 * a})`);
  grad.addColorStop(f(ringFrac - 0.02), `rgba(255,190,110,${0.85 * a})`);
  grad.addColorStop(f(ringFrac + 0.04), `rgba(255,170,85,${0.65 * a})`);
  grad.addColorStop(f(ringFrac + 0.22), `rgba(255,160,80,${0.22 * a})`);
  grad.addColorStop(f(ringFrac + 0.45), `rgba(255,160,80,${0.06 * a})`);
  grad.addColorStop(1, 'rgba(255,160,80,0)');
  g.fillStyle = grad; g.fillRect(0, 0, S, S);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}

const decor = new THREE.Group(); decor.name = 'furniture-decor';
for (const p of PIECES) {
  const pivot = new THREE.Group(); pivot.name = p.id;
  const model = parsed[p.model].scene.clone(true);
  model.scale.setScalar(p.scale);
  if (p.wall) model.rotation.x = Math.PI / 2;                     // modelled lying flat: face (+y) turns to +z
  const box = new THREE.Box3().setFromObject(model), c = box.getCenter(new THREE.Vector3()), size = box.getSize(new THREE.Vector3());
  const ring = p.led ? p.led.ring_center : null;                    // centre of the lit ring inside the model bbox (x, y offsets)
  model.position.set(-c.x - (ring ? ring[0] : 0), -c.y - (ring ? ring[1] : 0), -c.z);
  pivot.add(model);
  if (p.led) {                                                      // make it glow: emissive body + halo on the wall + a real light
    const L = p.led;
    model.traverse(o => {
      if (!o.isMesh) return;
      o.material = o.material.clone();                              // the LED body: lit warm white, not dimmed by tone mapping
      o.material.color = new THREE.Color(0xffffff);
      o.material.emissive = new THREE.Color(L.color); o.material.emissiveIntensity = L.emissive; o.material.toneMapped = false;
      o.castShadow = false;
    });
    if (L.halo_m > L.diameter_m) {
      const halo = new THREE.Mesh(new THREE.PlaneGeometry(L.halo_m, L.halo_m),
        new THREE.MeshBasicMaterial({ map: haloTexture(L.diameter_m / L.halo_m, L.halo_alpha), transparent: true, depthWrite: false, toneMapped: false }));   // warm tint on the wall (additive would vanish on a light wall)
      halo.position.z = -size.z / 2 + 0.002;                        // just in front of the wall face
      halo.name = p.id + '-halo';
      pivot.add(halo);
    }
    if (L.intensity > 0) {
      const light = new THREE.PointLight(L.color, L.intensity, L.distance, 1.6);
      light.position.z = L.light_z;                                 // out in the room, so the wall does not burn out
      pivot.add(light);
    }
  }
  pivot.position.copy(W(p.x, p.y, p.h));
  pivot.rotation.y = p.rot_deg * Math.PI / 180;                     // front (+z) faces plan angle rot - 90
  decor.add(pivot);
}
const Hw = window.__app.DATA.H.wall, cutIn = document.getElementById('cut');
const cutPlane = new THREE.Plane(new THREE.Vector3(0, -1, 0), Hw + 0.01);
const syncCut = () => { if (cutIn) cutPlane.constant = +cutIn.value >= Hw ? Hw + 0.01 : +cutIn.value; };
cutIn?.addEventListener('input', syncCut); syncCut();
decor.traverse(o => { if (o.isMesh) for (const m of [].concat(o.material)) m.clippingPlanes = [cutPlane]; });
group.add(decor);
draco.dispose();
window.__furnitureDecor = decor;
window.__furnitureDecorReady = true;
