/* Eu Edito — Browser Declarative Scene Player (Canvas 2D + Three.js WebGL 3D) */
(function () {
  function rgbStr(arr, a) {
    if (!Array.isArray(arr) || arr.length < 3) return `rgba(34,197,94,${a})`;
    return `rgba(${arr[0]},${arr[1]},${arr[2]},${a})`;
  }

  function ease(t, mode) {
    const u = Math.max(0, Math.min(1, t));
    if (mode === 'spring') {
      if (u < 0.68) {
        const s = u / 0.68;
        return 1.07 * (1 - Math.pow(1 - s, 3));
      }
      const s = (u - 0.68) / 0.32;
      return 1.07 - 0.07 * (s * s * (3 - 2 * s));
    }
    if (mode === 'smooth') return u * u * (3 - 2 * u);
    return 1 - Math.pow(1 - u, 3);
  }

  // Lazy offscreen Three.js WebGL renderer for true 3D metallic coins, monoliths, and octahedron cores
  let glRenderer = null;
  let glFailed = false;
  function renderThreeOffscreen(kind, w, h, palette, prog, tSec, vals) {
    if (glFailed || typeof window.THREE === 'undefined') return null;
    try {
      const THREE = window.THREE;
      if (!glRenderer) {
        const off = document.createElement('canvas');
        off.width = 360; off.height = 180;
        glRenderer = new THREE.WebGLRenderer({ canvas: off, alpha: true, antialias: true });
        glRenderer.setClearColor(0x000000, 0);
      }
      if (glRenderer.domElement.width !== w || glRenderer.domElement.height !== h) {
        glRenderer.setSize(w, h, false);
      }
      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(36, w / Math.max(1, h), 0.1, 100);
      camera.position.set(0, 0.85, 5.2);
      camera.lookAt(0, 0, 0);

      const amb = new THREE.AmbientLight(0xffffff, 0.65);
      const key = new THREE.DirectionalLight(0xffffff, 1.15);
      key.position.set(3, 5, 4);
      const rim = new THREE.DirectionalLight(new THREE.Color(palette.primary_hex || '#22C55E'), 0.9);
      rim.position.set(-4, -1, -2);
      scene.add(amb, key, rim);

      const group = new THREE.Group();
      const anim = ease(Math.min(1, prog / 0.72), 'spring');
      const primCol = new THREE.Color(rgbStr(palette.primary || [34, 197, 94], 1).replace(/rgba\(|\)/g, '').split(',').slice(0, 3).map((x) => Number(x) / 255));
      const secCol = new THREE.Color(rgbStr(palette.secondary || [250, 204, 21], 1).replace(/rgba\(|\)/g, '').split(',').slice(0, 3).map((x) => Number(x) / 255));

      if (kind === '3d_coins_growth') {
        const mat = new THREE.MeshStandardMaterial({ color: secCol, metalness: 0.75, roughness: 0.25 });
        [2, 4, 7].forEach((cnt, col) => {
          const shown = Math.max(1, Math.round(cnt * anim));
          for (let k = 0; k < shown; k++) {
            const coin = new THREE.Mesh(new THREE.CylinderGeometry(0.36, 0.36, 0.14, 20), mat);
            coin.position.set(-1.15 + col * 1.15, -0.75 + k * 0.22, 0);
            group.add(coin);
          }
        });
        group.rotation.y = tSec * 0.6;
      } else if (kind === '3d_pillars_scale') {
        const arr = (Array.isArray(vals) && vals.length ? vals : [28, 56, 84, 100]).slice(0, 4);
        const vmax = Math.max(...arr, 1);
        arr.forEach((v, i) => {
          const hh = Math.max(0.25, 1.75 * (v / vmax) * anim);
          const mat = new THREE.MeshStandardMaterial({
            color: i === arr.length - 1 ? primCol : secCol,
            metalness: i === arr.length - 1 ? 0.55 : 0.25,
            roughness: 0.35,
          });
          const box = new THREE.Mesh(new THREE.BoxGeometry(0.46, hh, 0.46), mat);
          box.position.set(-1.2 + i * 0.80, -0.85 + hh / 2, 0);
          group.add(box);
        });
        group.rotation.y = -0.35 + Math.sin(tSec * 0.7) * 0.15;
      } else {
        const mat = new THREE.MeshStandardMaterial({ color: primCol, metalness: 0.65, roughness: 0.20, wireframe: false });
        const oct = new THREE.Mesh(new THREE.OctahedronGeometry(0.95, 0), mat);
        group.add(oct);
        group.rotation.y = tSec * 1.1;
        group.rotation.x = 0.25;
      }
      scene.add(group);
      glRenderer.render(scene, camera);
      return glRenderer.domElement;
    } catch {
      glFailed = true;
      return null;
    }
  }

  function drawSceneBackdrop(ctx, w, h, plan, alphaEnv, enterP) {
    const pal = plan.palette || {};
    const prim = pal.primary || [34, 197, 94];
    const bg = pal.bg || [10, 14, 22];
    const smode = plan.surface_mode || 'pure_halo';
    const dy = (1 - enterP) * 14;
    const x0 = w * 0.03, y0 = h * 0.03 + dy, x1 = w * 0.97, y1 = h * 0.97 + dy;

    // Frameless feathered radial scrim strictly inside canvas bounds (never opaque PowerPoint box!)
    const rg = ctx.createRadialGradient(w / 2, h / 2 + dy, w * 0.05, w / 2, h / 2 + dy, w * 0.44);
    rg.addColorStop(0, rgbStr(bg, 0.78 * alphaEnv));
    rg.addColorStop(0.70, rgbStr(bg, 0.34 * alphaEnv));
    rg.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = rg;
    ctx.fillRect(0, 0, w, h);

    ctx.save();
    if (smode === 'scrim_brackets') {
      ctx.strokeStyle = rgbStr(prim, 0.85 * alphaEnv); ctx.lineWidth = 1.8;
      const L = 12;
      [[x0 + 8, y0 + 8, 1, 1], [x1 - 8, y0 + 8, -1, 1], [x0 + 8, y1 - 8, 1, -1], [x1 - 8, y1 - 8, -1, -1]].forEach(([cx, cy, dx, dy2]) => {
        ctx.beginPath(); ctx.moveTo(cx + dx * L, cy); ctx.lineTo(cx, cy); ctx.lineTo(cx, cy + dy2 * L); ctx.stroke();
      });
    } else if (smode === 'swiss_pillar') {
      ctx.fillStyle = rgbStr(prim, 0.92 * alphaEnv); ctx.fillRect(x0 + 10, y0 + 10, 4, y1 - y0 - 20);
    } else if (smode === 'hairline_floating' || smode === 'chronicle_rule') {
      ctx.fillStyle = rgbStr(prim, 0.75 * alphaEnv); ctx.fillRect(x0 + 14, y0 + 8, x1 - x0 - 28, 1.8);
    }
    ctx.restore();
    return dy;
  }

  function renderPlanFrame(canvas, item, prog, tSec) {
    if (!canvas || !item) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width, h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    const plan = item.scene_plan || (item.params && item.params.scene_plan);
    if (!plan || !Array.isArray(plan.layers)) return;

    const enterP = ease(Math.min(1, prog / 0.18), 'cubic-out');
    const exitP = ease(Math.min(1, (1 - prog) / 0.14), 'smooth');
    const alphaEnv = Math.max(0, Math.min(1, Math.min(enterP, exitP)));
    if (alphaEnv <= 0.01) return;

    ctx.save();
    ctx.globalAlpha = alphaEnv;
    const dy = drawSceneBackdrop(ctx, w, h, plan, alphaEnv, enterP);
    const pal = plan.palette || {};
    const prim = pal.primary || [34, 197, 94];
    const sec = pal.secondary || [255, 255, 255];
    const textCol = pal.text || [248, 250, 252];
    const mutedCol = pal.muted || [160, 175, 195];
    const sc = w / 400;

    plan.layers.forEach((lyr) => {
      const box = lyr.box || [0.05, 0.05, 0.95, 0.95];
      const bx0 = box[0] * w, by0 = box[1] * h + dy, bx1 = box[2] * w, by1 = box[3] * h + dy;
      const bw = bx1 - bx0, bh = by1 - by0;
      const comp = lyr.component;
      const pr = lyr.props || {};
      const anim = ease(Math.min(1, prog / 0.72), 'spring');

      if (comp === 'kinetic_headline') {
        const fMain = `800 ${Math.max(10, Math.round(17 * sc))}px 'CreatoDisplay', sans-serif`;
        const fItal = `italic 700 ${Math.max(10, Math.round(17 * sc))}px 'AppleGaramond', Georgia, serif`;
        ctx.font = fMain;
        ctx.fillStyle = rgbStr(textCol, 0.98);
        const tStr = String(pr.title || '').slice(0, 26);
        ctx.fillText(tStr, bx0, by0 + 18 * sc);
        if (pr.accent) {
          const tw = ctx.measureText(tStr).width;
          ctx.font = fItal;
          ctx.fillStyle = rgbStr(prim, 0.98);
          if (bx0 + tw + 8 * sc < w * 0.78) {
            ctx.fillText(String(pr.accent).slice(0, 20), bx0 + tw + 8 * sc, by0 + 18 * sc);
          } else {
            ctx.fillText(String(pr.accent).slice(0, 24), bx0, by0 + 34 * sc);
          }
        }
        if (pr.subtitle) {
          ctx.font = `500 ${Math.max(8, Math.round(9.5 * sc))}px sans-serif`;
          ctx.fillStyle = rgbStr(mutedCol, 0.92);
          ctx.fillText(String(pr.subtitle).slice(0, 46), bx0, by0 + (pr.accent && tStr.length > 14 ? 46 : 33) * sc);
        }
      } else if (comp === '3d_coins_growth' || comp === '3d_pillars_scale' || comp === 'ai_neural_architecture') {
        const glCanv = renderThreeOffscreen(comp, Math.max(120, Math.round(bw)), Math.max(80, Math.round(bh)), pal, prog, tSec, pr.values);
        if (glCanv) {
          ctx.drawImage(glCanv, bx0, by0, bw, bh);
        }
        if (pr.threshold_label) {
          ctx.fillStyle = rgbStr(prim, 0.95);
          ctx.font = `800 ${Math.max(8, Math.round(10 * sc))}px sans-serif`;
          ctx.fillText(String(pr.threshold_label).slice(0, 18), bx0 + 4, by0 + 14 * sc);
        }
      } else if (comp === 'tactical_radar') {
        const cx = (bx0 + bx1) / 2, cy = (by0 + by1) / 2, rad = Math.min(bw, bh) * 0.44;
        [0.4, 0.72, 1.0].forEach((f) => {
          ctx.beginPath(); ctx.arc(cx, cy, rad * f, 0, Math.PI * 2);
          ctx.strokeStyle = rgbStr(prim, 0.6); ctx.lineWidth = 1.3; ctx.stroke();
        });
        const ang = (tSec * 2) % (Math.PI * 2);
        ctx.beginPath(); ctx.moveTo(cx, cy); ctx.arc(cx, cy, rad, ang - 0.6, ang); ctx.closePath();
        ctx.fillStyle = rgbStr(prim, 0.25); ctx.fill();
        [-2.4, -0.6, 0.8, 2.4].forEach((a) => {
          const d = rad * (1.05 - 0.6 * anim);
          ctx.beginPath(); ctx.arc(cx + Math.cos(a) * d, cy + Math.sin(a) * d, 3.5 * sc, 0, Math.PI * 2);
          ctx.fillStyle = rgbStr(sec, 0.95); ctx.fill();
        });
      } else if (comp === 'geo_route_map') {
        const lbls = pr.labels || ['Origem', 'Destino'];
        const pts = lbls.slice(0, 3).map((_, i) => [bx0 + bw * (0.16 + 0.34 * i), by0 + bh * (i % 2 === 0 ? 0.65 : 0.28)]);
        ctx.strokeStyle = rgbStr(prim, 0.95); ctx.lineWidth = 2.2 * sc;
        for (let i = 0; i < pts.length - 1; i++) {
          const [p0, p1] = [pts[i], pts[i + 1]];
          ctx.beginPath(); ctx.moveTo(p0[0], p0[1]);
          ctx.quadraticCurveTo((p0[0] + p1[0]) / 2, Math.min(p0[1], p1[1]) - 18 * sc, p0[0] + (p1[0] - p0[0]) * anim, p0[1] + (p1[1] - p0[1]) * anim);
          ctx.stroke();
        }
        pts.forEach(([px, py], i) => {
          ctx.beginPath(); ctx.arc(px, py, 4 * sc, 0, Math.PI * 2); ctx.fillStyle = rgbStr(prim, 1); ctx.fill();
          ctx.fillStyle = rgbStr(textCol, 0.95); ctx.font = `700 ${Math.round(8.5 * sc)}px sans-serif`; ctx.textAlign = 'center';
          ctx.fillText(String(lbls[i]).slice(0, 12), px, py + 12 * sc);
        });
        ctx.textAlign = 'left';
      } else if (comp === 'machine_cutaway') {
        const cy = (by0 + by1) / 2, g1x = bx0 + bw * 0.28, g2x = bx0 + bw * 0.56;
        const drawCog = (gx, gy, r, rot, col) => {
          ctx.save(); ctx.translate(gx, gy); ctx.rotate(rot);
          ctx.beginPath();
          for (let k = 0; k < 16; k++) {
            const a = (k * Math.PI) / 8, rr = k % 2 === 0 ? r : r * 0.78;
            k === 0 ? ctx.moveTo(Math.cos(a) * rr, Math.sin(a) * rr) : ctx.lineTo(Math.cos(a) * rr, Math.sin(a) * rr);
          }
          ctx.closePath(); ctx.strokeStyle = rgbStr(col, 0.95); ctx.lineWidth = 1.6; ctx.stroke(); ctx.restore();
        };
        drawCog(g1x, cy, bh * 0.36, tSec * 1.4, prim);
        drawCog(g2x, cy - 8 * sc, bh * 0.26, -tSec * 2.0, sec);
        const px = g2x + bw * 0.22 + Math.sin(tSec * 3.8) * 10 * sc;
        ctx.strokeStyle = rgbStr(prim, 0.85); ctx.strokeRect(g2x + bw * 0.16, cy - 16 * sc, bw * 0.22, 32 * sc);
        ctx.fillStyle = rgbStr(sec, 0.9); ctx.fillRect(px, cy - 12 * sc, 10 * sc, 24 * sc);
      } else if (comp === 'science_orbital') {
        const cx = bx0 + bw * 0.30, cy = (by0 + by1) / 2, rad = Math.min(bw * 0.24, bh * 0.40);
        [0.2, 1.25, 2.3].forEach((tilt, oi) => {
          ctx.save(); ctx.translate(cx, cy); ctx.rotate(tilt);
          ctx.beginPath(); ctx.ellipse(0, 0, rad, rad * 0.42, 0, 0, Math.PI * 2);
          ctx.strokeStyle = rgbStr(prim, 0.65); ctx.lineWidth = 1.4; ctx.stroke();
          const a = tSec * (2 + oi * 0.6) + oi * 2;
          ctx.beginPath(); ctx.arc(Math.cos(a) * rad, Math.sin(a) * rad * 0.42, 3.2 * sc, 0, Math.PI * 2);
          ctx.fillStyle = rgbStr(sec, 1); ctx.fill(); ctx.restore();
        });
        ctx.beginPath();
        for (let i = 0; i < 24; i++) {
          const u = i / 23, wx = bx0 + bw * (0.56 + 0.40 * u), wy = cy + Math.sin(u * Math.PI * 4 - tSec * 5) * Math.sin(u * Math.PI) * 18 * sc;
          i === 0 ? ctx.moveTo(wx, wy) : ctx.lineTo(wx, wy);
        }
        ctx.strokeStyle = rgbStr(sec, 0.95); ctx.lineWidth = 2; ctx.stroke();
      } else if (comp === 'chronology_archive') {
        const cy = (by0 + by1) / 2, items = pr.labels || ['Início', 'Virada', 'Hoje'];
        ctx.strokeStyle = rgbStr(prim, 0.95); ctx.lineWidth = 2;
        ctx.beginPath(); ctx.moveTo(bx0 + 18, cy); ctx.lineTo(bx0 + 18 + (bw - 36) * anim, cy); ctx.stroke();
        items.slice(0, 3).forEach((it, i) => {
          const ix = bx0 + 28 + ((bw - 56) * i) / Math.max(1, items.slice(0, 3).length - 1);
          ctx.beginPath(); ctx.arc(ix, cy, 4 * sc, 0, Math.PI * 2); ctx.fillStyle = rgbStr(prim, 1); ctx.fill();
          ctx.fillStyle = rgbStr(textCol, 0.95); ctx.font = `700 ${Math.round(9 * sc)}px sans-serif`; ctx.textAlign = 'center';
          ctx.fillText(String(it).slice(0, 14), ix, cy + (i % 2 === 0 ? -12 : 18) * sc);
        });
        ctx.textAlign = 'left';
      } else if (comp === 'editorial_comparison') {
        const vals = pr.values || [35, 92], lbls = pr.labels || ['A', 'B'], vmax = Math.max(...vals.slice(0, 2), 1);
        [0, 1].forEach((i) => {
          const ry = by0 + 12 * sc + i * (bh / 2);
          ctx.fillStyle = rgbStr(textCol, 0.95); ctx.font = `700 ${Math.round(9.5 * sc)}px sans-serif`;
          ctx.fillText(String(lbls[i] || `Valor ${i + 1}`).slice(0, 20), bx0 + 6, ry + 10 * sc);
          ctx.fillStyle = rgbStr(i === 0 ? sec : prim, 0.92);
          ctx.fillRect(bx0 + 6, ry + 15 * sc, Math.max(16, (bw - 48) * (vals[i] / vmax) * anim), 14 * sc);
        });
      } else if (comp === 'calligraphy_sheet') {
        ctx.fillStyle = 'rgba(252,249,242,0.95)'; ctx.fillRect(bx0 + 8, by0 + 4, bw - 16, bh - 8);
        ctx.beginPath();
        for (let i = 0; i < Math.max(2, Math.floor(28 * anim)); i++) {
          const u = i / 27, px = bx0 + 20 + (bw - 40) * u, py = by0 + bh * 0.55 - Math.sin(u * Math.PI * 3) * bh * 0.25;
          i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
        }
        ctx.strokeStyle = rgbStr(prim, 1); ctx.lineWidth = 2.6 * sc; ctx.stroke();
      } else {
        // process_transformation
        const cy = (by0 + by1) / 2, lx = bx0 + bw * 0.22, rx = bx0 + bw * 0.78;
        ctx.strokeStyle = rgbStr(sec, 0.9); ctx.lineWidth = 2; ctx.strokeRect(lx - 18 * sc, cy - 16 * sc, 36 * sc, 32 * sc);
        ctx.beginPath(); ctx.arc(rx, cy, 18 * sc, 0, Math.PI * 2); ctx.fillStyle = rgbStr(prim, 0.35); ctx.fill(); ctx.strokeStyle = rgbStr(prim, 1); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(lx + 24 * sc, cy); ctx.lineTo(lx + 24 * sc + (rx - lx - 48 * sc) * anim, cy); ctx.stroke();
      }
    });
    ctx.restore();
  }

  window.EuEditoScenePlayer = { renderFrame: renderPlanFrame };
})();
