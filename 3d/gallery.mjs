// Takes the gallery photos: one from every room corner listed in DATA.views (see gen3d.py), daylight, eye level.
// Needs playwright (npm i playwright) next to this file; run: node gallery.mjs <project dir>
import { chromium } from 'playwright';
import fs from 'fs';
const proj = process.argv[2], out = proj + '/3d/gallery';
fs.mkdirSync(out, { recursive: true });
for (const f of fs.readdirSync(out)) fs.unlinkSync(out + '/' + f);
const b = await chromium.launch({ channel: 'chrome', headless: true, args: ['--use-angle=metal', '--enable-gpu', '--ignore-gpu-blocklist'] });
const p = await b.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1 });
await p.goto('file://' + proj + '/3d/apartament3d.html'); await p.waitForTimeout(15000);
await p.addStyleTag({ content: '#ui,#prodwrap,#cam,#ptip,#gal,#lightbox{display:none!important}' });
const views = await p.evaluate(() => __app.DATA.views);
const index = []; const count = {};
for (const [k, x, y, tx, ty] of views) {
  const r = await p.evaluate(([x, y, tx, ty]) => {
    const { THREE, camera, orbit, W, scene } = __app;
    camera.fov = 78; camera.updateProjectionMatrix();
    const ray = new THREE.Raycaster(); const tgt = W(tx, ty, 1.0);
    const solid = []; scene.traverse(o => { if (o.isMesh && o.visible && o.name !== 'shadow-shell' && o.name !== 'mirror' && !(o.material.transparent && o.material.opacity < 0.5)) solid.push(o); });
    const clear = pos => { let min = 99; for (const a of [-0.5, -0.25, 0, 0.25, 0.5]) { const d = tgt.clone().sub(pos).normalize().applyAxisAngle(new THREE.Vector3(0, 1, 0), a); ray.set(pos, d); const h = ray.intersectObjects(solid, false)[0]; if (h) min = Math.min(min, h.distance); } return min; };
    let best = null;
    for (let s = 0; s <= 1.4; s += 0.2) {                      // step out of a wardrobe / bookcase standing in the corner
      const L = Math.hypot(tx - x, ty - y), px = x + (tx - x) / L * s, py = y + (ty - y) / L * s;
      for (const h of [1.6, 1.75]) { const pos = W(px, py, h), c = clear(pos); if (!best || c > best.c + 0.3) best = { c, px, py, h }; }
      if (best.c > 0.9) break;
    }
    if (best.c < 0.5) return null;
    camera.position.copy(W(best.px, best.py, best.h)); orbit.target.copy(tgt); orbit.update();
    return [best.px, best.py, best.h, tx, ty, 1.0].map(v => +v.toFixed(2));
  }, [x, y, tx, ty]);
  if (!r) { console.log('room', k, 'corner', x, y, 'blocked, skipped'); continue; }
  await p.evaluate(() => { __app.orbit.update(); }); await p.waitForTimeout(1500);
  count[k] = (count[k] || 0) + 1; const file = `r${k}-${count[k]}.jpg`;
  await p.screenshot({ path: `${out}/${file}`, type: 'jpeg', quality: 82 });
  index.push({ file, room: k, cam: `${r[0]},${r[1]},${r[2]};${r[3]},${r[4]},${r[5]}` });
}
fs.writeFileSync(out + '/index.json', JSON.stringify(index, null, 1));
console.log('photos', index.length);
await b.close();
