/* Aurora Awards background scene.
   Two-pass WebGL render every frame:
     Pass 1: aurora curtains (full-screen quad with fragment shader,
             ported from aurora-gracewood.com — Bayer-noise stars and the
             fake-mirror reflection both removed).
     Pass 2: NASA Blue Marble Night sphere, slowly rotating, positioned to
             create a curved horizon at the bottom of the viewport.
   Canvas is position:fixed in CSS so the scene stays locked to the viewport
   while page content scrolls above it. */

(function () {
  const canvas = document.getElementById('aurora-canvas');
  if (!canvas) {
    console.warn('[bg.js] no #aurora-canvas element found');
    return;
  }
  if (typeof THREE === 'undefined') {
    console.warn('[bg.js] THREE.js not loaded');
    return;
  }

  const W = () => window.innerWidth;
  const H = () => window.innerHeight;

  /* WebGLRenderer creation can fail when the browser has accumulated too
     many WebGL contexts (typically after rapid hard-refreshes during dev).
     Browsers cap at ~16 contexts per tab. Wrap in try-catch so a failed
     context init doesn't crash the entire page — the rest of the site
     still works, just without the aurora animation. */
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: false,
      alpha: true
    });
  } catch (e) {
    console.warn('[bg.js] WebGL context failed to initialize. Aurora background disabled. Cause:', e);
    canvas.style.display = 'none';
    return;
  }
  if (!renderer || !renderer.getContext()) {
    console.warn('[bg.js] WebGL renderer created but context is null. Aurora background disabled.');
    canvas.style.display = 'none';
    return;
  }
  renderer.setPixelRatio(1); /* no devicePixelRatio scaling — softer aurora is fine */
  renderer.setSize(W(), H());
  renderer.setClearColor(0x000000, 0); /* fully transparent — body gradient shows through */
  renderer.autoClear = false;

  /* Release the WebGL context cleanly when the page unloads so we don't
     stack up dead contexts across refreshes. */
  window.addEventListener('beforeunload', () => {
    try { renderer.forceContextLoss(); } catch (_) {}
    try { renderer.dispose(); } catch (_) {}
  });
  /* Detect which Three.js color-space API is available.
     - r152+ uses `SRGBColorSpace` constant + `colorSpace` property.
     - r128 uses `sRGBEncoding` constant + `encoding` property.
     We're loading r128 from cdnjs so the `else` branch is the active one,
     but the detection lets the code work if the Three.js version is bumped. */
  const USE_NEW_COLOR_API = (typeof THREE.SRGBColorSpace !== 'undefined');
  try {
    if (USE_NEW_COLOR_API) {
      renderer.outputColorSpace = THREE.SRGBColorSpace;
    } else {
      renderer.outputEncoding = THREE.sRGBEncoding;
    }
  } catch (e) {
    console.warn('[bg.js] could not set output color space:', e);
  }
  /* Tone mapping with high exposure: brightens the Earth texture so faint
     city lights are visible despite the oblique viewing geometry. Filmic
     curve clamps highlights gracefully so already-bright lights don't blow
     out. Aurora is already alpha-keyed and rendered in linear space, so it's
     unaffected by tone mapping. */
  /* ACES Filmic tone mapping with moderate exposure boost for the night
     texture: brightens dim city lights so they pop against dark ocean
     without saturating the brightest already-lit areas. */
  if (THREE.ACESFilmicToneMapping !== undefined) {
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 2.0;
  }

  /* ===================================================================== */
  /* AURORA SCENE — orthographic full-screen quad with the curtain shader. */
  /* ===================================================================== */
  const auroraScene = new THREE.Scene();
  const auroraCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);

  const vertexShader = `
    void main() {
      gl_Position = vec4(position, 1.0);
    }
  `;

  /* Fragment shader — ported from aurora-gracewood.com mainImage().
     Modifications:
       - Bayer-noise starfield (Fetch + Blur) removed; v=0.
       - if(mirror) fake reflection block replaced with a dark navy
         gradient — the Earth sphere will render on top of it.
       - Ray-march steps capped at 80 (was 200) for performance.
       - GLSL-ES-1.0 syntax (texture2D) for WebGL 1 compatibility, but we
         don't use textures in this pass anyway.
  */
  const fragmentShader = `
    uniform vec3 iResolution;
    uniform float iTime;

    float hash(float p) { p = fract(p * 0.011); p *= p + 7.5; p *= p + p; return fract(p); }
    float hash(vec2 p) { vec3 p3 = fract(vec3(p.xyx) * 0.13); p3 += dot(p3, p3.yzx + 3.333); return fract((p3.x + p3.y) * p3.z); }

    float noise(vec2 x) {
      vec2 i = floor(x); vec2 f = fract(x); vec2 u = f * f * (3.0 - 2.0 * f);
      return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x),
                 mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y) - 0.5;
    }

    float noise(vec3 x) {
      const vec3 step = vec3(110, 241, 171);
      vec3 i = floor(x); vec3 f = fract(x); float n = dot(i, step); vec3 u = f * f * (3.0 - 2.0 * f);
      return mix(mix(mix(hash(n + dot(step, vec3(0, 0, 0))), hash(n + dot(step, vec3(1, 0, 0))), u.x),
                     mix(hash(n + dot(step, vec3(0, 1, 0))), hash(n + dot(step, vec3(1, 1, 0))), u.x), u.y),
                 mix(mix(hash(n + dot(step, vec3(0, 0, 1))), hash(n + dot(step, vec3(1, 0, 1))), u.x),
                     mix(hash(n + dot(step, vec3(0, 1, 1))), hash(n + dot(step, vec3(1, 1, 1))), u.x), u.y), u.z) - 0.5;
    }

    float noiseOctaves(vec3 x) {
      return noise(x) +
        noise(x * 2.0 + x) * 0.5 +
        noise(x * 4.0 + x * 2.0) * 0.25 +
        noise(x * 8.0 + x * 4.0) * 0.125;
    }

    #define DEG2RAD 0.0174533
    void main() {
      vec2 uv = (gl_FragCoord.xy / iResolution.xy) * 2.0 - 1.0;

      float yaw = 0.0;
      /* Portrait-only pitch reduction: 20° → 15° base. Lower pitch =
         camera looks more horizontally = horizon moves UP in viewport =
         aurora content shifts up. Single-change-only this round. */
      float pitch = ((iResolution.y / iResolution.x > 1.0) ? 15.0 : 20.0) * DEG2RAD;
      pitch += abs(pow(uv.x, 2.0) * 3.0 * DEG2RAD);
      /* Yaw: landscape uses squared (pow(uv.x, 2.0)) — symmetric around
         center, gives the panoramic curl. On portrait, the symmetry shows
         as a visible "mirror" in the middle of viewport because both
         halves sample the same content. Switch to LINEAR uv.x on portrait
         so left and right halves see DIFFERENT aurora content — no mirror. */
      yaw = (iResolution.y / iResolution.x > 1.0) ? uv.x : pow(uv.x, 2.0);
      /* Portrait-only leftward shift (positive yaw → content shifts LEFT). */
      yaw += (iResolution.y / iResolution.x > 1.0) ? 1.5 : 0.0;

      vec2 look = vec2(yaw, pitch);
      /* Orientation-aware FOV. Landscape: fov_x = 75° + fov.y proportional
         to aspect (original). Portrait: fov_x = 22° (much narrower
         horizontal FOV → curtains look way wider on the narrow viewport)
         + fov.y = 33° (taller aurora coverage, horizon at ~78% of viewport). */
      float aspect = iResolution.y / iResolution.x;
      float fov_x = (aspect > 1.0) ? (3.0 * DEG2RAD) : (150.0 * 0.5 * DEG2RAD);
      float fov_y = (aspect > 1.0) ? (33.0 * DEG2RAD) : (fov_x * aspect);
      vec2 fov = vec2(fov_x, fov_y);
      vec2 tan_uv = uv * tan(fov);
      vec2 ray_a = atan(tan_uv) + look;
      vec3 ray = vec3(
        cos(ray_a.x) * cos(ray_a.y),
        sin(ray_a.y),
        sin(ray_a.x) * cos(ray_a.y)
      );

      bool below_horizon = ray.y < 0.0;
      ray.y = abs(ray.y);

      float start = 10000.0;
      float end = 80000.0;
      float brightness = 25.0;
      float fade_start = 100000.0;
      float fade_end = 200000.0;

      float slope = clamp(length(ray.xz) / ray.y, 0.0, 1.0);
      /* Compromise step ceiling at 100 — half of the original 200 (which
         was too laggy on mobile) but well above 60 (where visible ring
         banding appeared). 100 should produce smooth gradients without
         the perf hit of 200. */
      float steps = clamp(25.0 / (1.0 - slope), 25.0, 100.0);

      vec3 outc = vec3(0.0);
      float outv = 0.0;
      vec3 prevpoint = vec3(0.0);
      float prevvalue = 0.0;

      /* Per-pixel jitter that ALSO animates per-frame. Magnitude 0.7 is
         enough to fully break up the band boundaries (no rings). The
         time-varying input means each frame has DIFFERENT random
         positions for each pixel — so any per-pixel noise the eye would
         see as "dots" instead becomes film grain that averages out
         temporally (the eye blends ~6 frames into a smooth percept).
         Best of both worlds: rings hidden by spatial dithering, dots
         hidden by temporal averaging. */
      float jitter = hash(gl_FragCoord.xy + iTime * vec2(1.137, 0.913)) * 0.7;

      for (float i = 0.0; i <= 100.0; i++) {
        if (i > steps) break;
        float fi = (i + jitter) / steps;
        float elevation = mix(start, end, fi);

        vec2 intersection = vec2(elevation * ray.x / ray.y, elevation * ray.z / ray.y);
        vec3 curpoint = vec3(intersection.x, elevation, intersection.y);

        float h_distance = length(intersection);
        float coef = 1.0;

        if (h_distance > fade_end) continue;
        if (h_distance > fade_start) {
          coef = 1.0 - (h_distance - fade_start) / (fade_end - fade_start);
        }

        vec3 timeOffset = iTime * vec3(0.025, 0.0, -0.25);
        vec2 xzOffset = intersection * 0.000005 + timeOffset.xz;
        float yOffset = fi * 0.01 + noiseOctaves(vec3(xzOffset, 0.0)) * 1.35 + timeOffset.y;
        vec3 posOffset = vec3(xzOffset, yOffset);

        float hue = noiseOctaves(timeOffset + posOffset + vec3(3.13, 2.35, 0.0));
        float value = abs(hue);
        hue = hue * 15.0 - fi;
        value = clamp(2.5 - value * 50.0, 0.0, 1.0);
        value = coef * (brightness / steps) * min(i, 1.0) * (1.0 - pow(fi, 0.15)) * value;

        float curvalue = value;

        if (i > 0.0) {
          float base = length(curpoint - prevpoint) * 0.0007;
          float mn = min(value, prevvalue);
          float mx = max(value, prevvalue);
          float area = base * (mx + mn) * 0.5;
          value = area;

          vec3 color = hue >= 0.0
            ? mix(vec3(0.0, 1.0, 0.0), vec3(0.0, 0.0, 1.0), hue)
            : mix(vec3(0.0, 1.0, 0.0), vec3(1.0, 0.0, 1.0), -hue);
          outc += value * color;
          outv += value;
        }
        prevvalue = curvalue;
        prevpoint = curpoint;
      }

      /* Without the Bayer starfield mix, just scale the aurora intensity. */
      outc = outc * 0.6;

      /* Aurora alpha = brightness. Bright curtains are opaque; dark sky
         is transparent so the body's gradient background shows through.
         Below horizon we go fully transparent; the Earth sphere paints
         on top during pass 2 wherever the planet is visible. */
      float aurora_alpha = clamp(length(outc) * 1.8, 0.0, 1.0);
      if (below_horizon) {
        outc = vec3(0.0);
        aurora_alpha = 0.0;
      }

      gl_FragColor = vec4(outc, aurora_alpha);
    }
  `;

  const auroraMaterial = new THREE.ShaderMaterial({
    uniforms: {
      iTime: { value: 0 },
      iResolution: { value: new THREE.Vector3(W(), H(), 1) }
    },
    vertexShader,
    fragmentShader
  });

  auroraScene.add(new THREE.Mesh(new THREE.PlaneGeometry(2, 2), auroraMaterial));

  /* ===================================================================== */
  /* EARTH SCENE — perspective camera, NASA Blue Marble Night sphere.       */
  /* The sphere is positioned below and slightly behind the camera so its   */
  /* upper edge curves across the bottom portion of the viewport, matching  */
  /* the curve the original shader's mirror reflection used to produce.     */
  /* ===================================================================== */
  const earthScene = new THREE.Scene();
  /* Mobile-style detection via VIEWPORT WIDTH. Catches both real mobile
     devices AND narrow desktop windows. */
  const earthCamera = new THREE.PerspectiveCamera(130, W() / H(), 0.1, 20000);
  earthCamera.position.set(0, 0, 0);
  /* Mobile-only: more downward tilt → sphere appears higher in viewport. */
  earthCamera.lookAt(new THREE.Vector3(0, (window.innerWidth < 600 && window.innerHeight > window.innerWidth) ? -0.65 : -0.5, -1));

  /* Northern HALF-sphere with reduced segment count: 96×24 (was 128×32).
     ~44% fewer triangles than the previous setting, ~72% fewer than the
     original full-sphere 128×64. At our viewing distance only a small
     cap of the sphere is visible, the curve is gentle, and 96 segments
     around the equator gives 3.75° per polygon — sub-pixel error vs the
     mathematically smooth circle at our render scale. */
  const earthGeometry = new THREE.SphereGeometry(
    8000, 96, 24,
    0, Math.PI * 2,
    0, Math.PI / 2
  );

  /* Composite of two textures for "Earth at night with visible continents":
     - Day map (2048×1024): heavily darkened for moonlit continent outlines.
     - Night map (8192×4096): downsized from NASA Black Marble's 13500×6750
       to Solar System Scope's 8K version. ~60% smaller file (3.1MB vs
       8.1MB), faster initial load. Detail at our oblique viewing scale is
       still well above what individual screen pixels can resolve — 8K
       texels are still ~22 per km of Earth circumference, plenty for
       distinct city light pinpoints. */
  const dayTexUrl = './earth-day-2k.jpg';
  const nightTexUrl = './earth-night-8k.jpg';
  const loader = new THREE.TextureLoader();
  /* No crossOrigin attribute — same-origin load. Setting `crossOrigin =
     'anonymous'` would force the browser to demand CORS headers from the
     local Python http.server which doesn't send them, causing the texture
     load to fail silently. */

  /* Custom Earth material:
       - Samples the night-map texture
       - Applies an exposure-style brightness boost so faint city lights pop
         without saturating the brightest already-bright lights
       - Slightly increases blue tint so dim coastlines read as ocean
     A standard MeshBasicMaterial just samples and outputs the texture color,
     which at this oblique viewing geometry ends up averaging too many dim
     ocean texels per pixel — city lights blur into invisibility. The custom
     shader gives us control over the post-sample brightening curve. */
  /* Pre-texture-load color: `0x010103` (almost black, faintest blue).
     User preferred this over `0x000510` (which read as aquamarine-green
     on their display). Display panel rendering of low-intensity hues is
     unpredictable — keeping the value the user accepted. */
  const earthMaterial = new THREE.MeshBasicMaterial({
    color: 0x010103,
    map: null,
    toneMapped: false
  });

  const earth = new THREE.Mesh(earthGeometry, earthMaterial);
  earth.position.set(0, -17000, 0);
  earth.rotation.x = -Math.PI * 60.5 / 180;
  /* Portrait branch FIRST (unchanged from round 132). Then very-narrow-
     height check catches mobile landscape (height < 400 AND wider than
     tall) without affecting desktop (typically height > 500). */
  if (window.innerWidth < 600 && window.innerHeight > window.innerWidth) {
    earth.scale.set(3.0, 0.5, 3.0);
  } else {
    earth.scale.set(12.0, 0.5, 12.0);
  }
  earthScene.add(earth);

  /* Aurora is held off until the Earth's texture composite is ready. Globe
     loads first (exclusive GPU time for canvas processing + texture upload),
     THEN aurora kicks in. Without this, both compete during page load and
     the heavy GPU lifting takes longer. */
  let auroraReady = false;

  /* Load via fetch + createImageBitmap with `imageOrientation: 'none'`.
     This forces the browser to IGNORE any EXIF orientation tag in the
     JPEG, so the image is always loaded in its stored orientation. Last
     time, the day texture's EXIF orientation tag (set to "upper-right" /
     rotate 90° CW by Photoshop) was making Three.js's TextureLoader
     auto-rotate it during decode, mismatching the night map. With this
     safer load path, EXIF rotation can't bite us again. */
  function loadOrientedBitmap(url) {
    return fetch(url)
      .then((r) => {
        if (!r.ok) throw new Error('HTTP ' + r.status + ' for ' + url);
        return r.blob();
      })
      .then((blob) => createImageBitmap(blob, { imageOrientation: 'none' }));
  }

  let dayBitmap = null, nightBitmap = null;

  function tryComposite() {
    if (!dayBitmap || !nightBitmap) return;
    const w = nightBitmap.width;
    const fullH = nightBitmap.height;

    /* Half-height canvas: top half of source textures only (latitudes
       0°–90°N, the northern hemisphere). The half-sphere geometry
       naturally maps to this with NO UV remap — Three.js's UVs span 0..1
       across the partial sphere, and the half-height canvas spans equator
       (canvas v=0) to north pole (canvas v=1). Saves 50% of texture memory.
       Source-image top half = pixels y=0 to y=fullH/2. */
    const cropFracY = 0.0;        /* start at top of source image */
    const cropFracHeight = 0.5;   /* take top half */
    const bandHeight = Math.round(fullH * cropFracHeight);

    console.log('[bg.js] Compositing northern half Earth:', w, 'x', bandHeight,
      '(saves 50% of texture memory)');

    /* CHUNKED canvas processing. The drawImage-with-filter operations on
       8K-13K source bitmaps each take 30-100ms — that's a frame budget
       blown, and the requestAnimationFrame loop can't fire during the
       blocking work. So instead of running all three layers sequentially,
       we split them across animation frames using requestAnimationFrame.
       Aurora has time to render between layer steps. */
    const cv = document.createElement('canvas');
    cv.width = w;
    cv.height = bandHeight;
    const ctx = cv.getContext('2d');

    /* Step 1 (sync): just fill the navy base — fast operation, no need
       to defer. */
    ctx.fillStyle = '#040818';
    ctx.fillRect(0, 0, w, bandHeight);

    /* Step 2 (next frame): darkened day map. */
    requestAnimationFrame(() => {
      try {
        ctx.globalAlpha = 0.55;
        ctx.filter = 'brightness(0.18) saturate(0.6)';
        ctx.drawImage(
          dayBitmap,
          0, dayBitmap.height * cropFracY,
          dayBitmap.width, dayBitmap.height * cropFracHeight,
          0, 0,
          w, bandHeight
        );
        ctx.filter = 'none';
        ctx.globalAlpha = 1.0;
      } catch (e) {
        console.warn('[bg.js] day-map composite failed', e);
      }

      /* Step 3 (frame after): night-side city lights. */
      requestAnimationFrame(() => {
        try {
          ctx.globalCompositeOperation = 'lighter';
          ctx.filter = 'blur(0.5px) contrast(1.6) brightness(1.4)';
          ctx.drawImage(
            nightBitmap,
            0, nightBitmap.height * cropFracY,
            nightBitmap.width, nightBitmap.height * cropFracHeight,
            0, 0,
            w, bandHeight
          );
          ctx.filter = 'none';
          ctx.globalCompositeOperation = 'source-over';
        } catch (e) {
          console.warn('[bg.js] night-map composite failed', e);
        }

        /* Step 4 (frame after that): finalize texture and assign to material. */
        requestAnimationFrame(() => {
          const processed = new THREE.CanvasTexture(cv);
          /* No UV remap needed: half-sphere geometry has UV v=0..1 spanning
             from equator to north pole, and the half-height canvas spans
             the same latitudes (top half of original = equator to north
             pole). Default repeat=(1,1) and offset=(0,0) work correctly. */
          processed.wrapT = THREE.ClampToEdgeWrapping;
          if (USE_NEW_COLOR_API) {
            processed.colorSpace = THREE.SRGBColorSpace;
          } else {
            processed.encoding = THREE.sRGBEncoding;
          }
          processed.anisotropy = renderer.capabilities.getMaxAnisotropy();
          processed.minFilter = THREE.LinearMipmapLinearFilter;
          processed.magFilter = THREE.LinearFilter;
          processed.generateMipmaps = true;
          processed.needsUpdate = true;
          earthMaterial.map = processed;
          earthMaterial.color.setHex(0xffffff);
          earthMaterial.toneMapped = true;
          earthMaterial.needsUpdate = true;
          /* Earth texture is now live. Allow aurora to start rendering. */
          auroraReady = true;
        });
      });
    });
  }

  loadOrientedBitmap(dayTexUrl).then(
    (bmp) => { dayBitmap = bmp; console.log('[bg.js] day bitmap loaded:', bmp.width, 'x', bmp.height); tryComposite(); },
    (err) => { console.warn('[bg.js] day bitmap failed', err); }
  );
  loadOrientedBitmap(nightTexUrl).then(
    (bmp) => { nightBitmap = bmp; console.log('[bg.js] night bitmap loaded:', bmp.width, 'x', bmp.height); tryComposite(); },
    (err) => { console.warn('[bg.js] night bitmap failed', err); }
  );

  /* ===================================================================== */
  /* RENDER LOOP                                                            */
  /* ===================================================================== */
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function frame(t) {
    if (document.hidden) {
      requestAnimationFrame(frame);
      return;
    }
    /* Aurora time scaled to half-speed (was t/1000 = 1× real time) for a
       slower, smoother curtain flow. */
    auroraMaterial.uniforms.iTime.value = t / 2000;
    /* Slow rotation: full revolution every 90 seconds. Same on mobile and
       desktop. */
    earth.rotation.y = (t / 90000) * Math.PI * 2;

    renderer.clear();
    /* Skip aurora rendering until the Earth texture composite is finished.
       Globe loads first; aurora kicks in once `auroraReady` flips to true
       (set in the final tryComposite step after the texture is assigned). */
    if (auroraReady) {
      renderer.render(auroraScene, auroraCamera);
      renderer.clearDepth();
    }
    renderer.render(earthScene, earthCamera);

    if (!reducedMotion) requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);

  /* ===================================================================== */
  /* RESIZE                                                                 */
  /* ===================================================================== */
  function applyOrientationLayout() {
    const isPortraitMobile = window.innerWidth < 600 && window.innerHeight > window.innerWidth;
    if (isPortraitMobile) {
      earth.scale.set(3.0, 0.5, 3.0);
    } else {
      earth.scale.set(12.0, 0.5, 12.0);
    }
    earthCamera.lookAt(new THREE.Vector3(0, isPortraitMobile ? -0.65 : -0.5, -1));
  }

  window.addEventListener('resize', () => {
    renderer.setSize(W(), H());
    auroraMaterial.uniforms.iResolution.value.set(W(), H(), 1);
    earthCamera.aspect = W() / H();
    earthCamera.updateProjectionMatrix();
    applyOrientationLayout();
  });
})();
