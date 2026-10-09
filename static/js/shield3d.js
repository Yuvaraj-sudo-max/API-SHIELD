/**
 * shield3d.js - Quantum 3D Holographic Defense Matrix
 * Renders real-time multi-layered 3D barrier using Three.js with Canvas fallback.
 * Visualizes packet photon streams, energy deflection shockwaves, and barrier alerts.
 */

class Shield3DVisualizer {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    if (!this.container) return;

    this.scene = null;
    this.camera = null;
    this.renderer = null;

    // 3D Objects
    this.coreMesh = null;
    this.coreWireframe = null;
    this.shieldGeodesic = null;
    this.orbitalRing1 = null;
    this.orbitalRing2 = null;
    this.satellites = [];
    this.particleSystem = null;
    this.activeShockwaves = [];
    this.incomingPackets = [];

    // Lighting
    this.coreLight = null;
    this.ambientLight = null;

    // View & Interaction State
    this.mode = 'hologram'; // 'hologram' | 'wireframe' | 'quantum'
    this.isDragging = false;
    this.mousePrev = { x: 0, y: 0 };
    this.targetRotation = { x: 0.2, y: 0.3 };
    this.currentRotation = { x: 0.2, y: 0.3 };
    this.cameraDistance = 8.5;
    this.alarmActive = false;
    this.alarmTimer = null;

    this.init();
  }

  init() {
    if (typeof THREE !== 'undefined') {
      try {
        this.initThree();
        this.setupEventListeners();
        this.animate();
        return;
      } catch (err) {
        console.warn("Three.js initialization failed, falling back to 2D Canvas:", err);
      }
    }
    this.initCanvasFallback();
  }

  /* -------------------------------------------------------------
     THREE.JS QUANTUM MATRIX IMPLEMENTATION
     ------------------------------------------------------------- */
  initThree() {
    const width = this.container.clientWidth || 600;
    const height = this.container.clientHeight || 380;

    // 1. Scene & Camera
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    this.camera.position.set(0, 0, this.cameraDistance);

    // 2. WebGL Renderer
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setSize(width, height);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.domElement.id = 'shield-webgl-canvas';
    this.container.appendChild(this.renderer.domElement);

    // 3. Dynamic Lighting System
    this.ambientLight = new THREE.AmbientLight(0x0a1026, 2.5);
    this.scene.add(this.ambientLight);

    const dirLight1 = new THREE.DirectionalLight(0x00f2fe, 2.2);
    dirLight1.position.set(6, 8, 6);
    this.scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0x8b5cf6, 1.8);
    dirLight2.position.set(-6, -6, 4);
    this.scene.add(dirLight2);

    this.coreLight = new THREE.PointLight(0x00f2fe, 3, 20);
    this.coreLight.position.set(0, 0, 0);
    this.scene.add(this.coreLight);

    // 4. Central Crystalline Core
    const coreGeo = new THREE.IcosahedronGeometry(1.5, 1);
    this.coreMat = new THREE.MeshPhongMaterial({
      color: 0x00f2fe,
      emissive: 0x061e38,
      specular: 0xffffff,
      shininess: 100,
      transparent: true,
      opacity: 0.65,
      flatShading: true,
    });
    this.coreMesh = new THREE.Mesh(coreGeo, this.coreMat);
    this.scene.add(this.coreMesh);

    // Core Wireframe Layer
    const wireMat = new THREE.MeshBasicMaterial({
      color: 0x38bdf8,
      wireframe: true,
      transparent: true,
      opacity: 0.5,
    });
    this.coreWireframe = new THREE.Mesh(coreGeo, wireMat);
    this.coreWireframe.scale.set(1.02, 1.02, 1.02);
    this.scene.add(this.coreWireframe);

    // 5. Outer Geodesic Defense Shield Sphere
    const shieldGeo = new THREE.IcosahedronGeometry(2.35, 2);
    this.shieldMat = new THREE.MeshBasicMaterial({
      color: 0x00f2fe,
      wireframe: true,
      transparent: true,
      opacity: 0.25,
    });
    this.shieldGeodesic = new THREE.Mesh(shieldGeo, this.shieldMat);
    this.scene.add(this.shieldGeodesic);

    // 6. Dual Gyroscopic Orbital Rings
    const ringGeo1 = new THREE.TorusGeometry(3.0, 0.025, 16, 100);
    const ringMat1 = new THREE.MeshBasicMaterial({ color: 0x6366f1, transparent: true, opacity: 0.6 });
    this.orbitalRing1 = new THREE.Mesh(ringGeo1, ringMat1);
    this.orbitalRing1.rotation.x = Math.PI / 3;
    this.scene.add(this.orbitalRing1);

    const ringGeo2 = new THREE.TorusGeometry(3.4, 0.025, 16, 100);
    const ringMat2 = new THREE.MeshBasicMaterial({ color: 0x00f2fe, transparent: true, opacity: 0.5 });
    this.orbitalRing2 = new THREE.Mesh(ringGeo2, ringMat2);
    this.orbitalRing2.rotation.y = Math.PI / 4;
    this.scene.add(this.orbitalRing2);

    // Orbital Satellites
    const satGeo = new THREE.SphereGeometry(0.09, 12, 12);
    const satMat = new THREE.MeshBasicMaterial({ color: 0x00f5a0 });
    for (let i = 0; i < 3; i++) {
      const sat = new THREE.Mesh(satGeo, satMat);
      sat.userData = { angle: (i * Math.PI * 2) / 3, radius: 3.4, speed: 0.015 + i * 0.005 };
      this.scene.add(sat);
      this.satellites.push(sat);
    }

    // 7. Ambient Floating Quantum Particles
    const particleCount = 200;
    const particleGeo = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCount * 3);
    for (let i = 0; i < particleCount * 3; i += 3) {
      positions[i] = (Math.random() - 0.5) * 14;
      positions[i + 1] = (Math.random() - 0.5) * 14;
      positions[i + 2] = (Math.random() - 0.5) * 14;
    }
    particleGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    const particleMat = new THREE.PointsMaterial({
      color: 0x38bdf8,
      size: 0.08,
      transparent: true,
      opacity: 0.55,
    });
    this.particleSystem = new THREE.Points(particleGeo, particleMat);
    this.scene.add(this.particleSystem);

    // Resize Observer
    window.addEventListener('resize', () => this.onResize());
  }

  onResize() {
    if (!this.renderer || !this.container) return;
    const width = this.container.clientWidth;
    const height = this.container.clientHeight;
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height);
  }

  setupEventListeners() {
    const el = this.renderer.domElement;

    el.addEventListener('mousedown', (e) => {
      this.isDragging = true;
      this.mousePrev = { x: e.clientX, y: e.clientY };
    });

    window.addEventListener('mousemove', (e) => {
      if (!this.isDragging) return;
      const dx = e.clientX - this.mousePrev.x;
      const dy = e.clientY - this.mousePrev.y;
      this.targetRotation.y += dx * 0.007;
      this.targetRotation.x += dy * 0.007;
      this.targetRotation.x = Math.max(-Math.PI / 2.5, Math.min(Math.PI / 2.5, this.targetRotation.x));
      this.mousePrev = { x: e.clientX, y: e.clientY };
    });

    window.addEventListener('mouseup', () => {
      this.isDragging = false;
    });

    // Touch support for mobile/tablets
    el.addEventListener('touchstart', (e) => {
      if (e.touches.length === 1) {
        this.isDragging = true;
        this.mousePrev = { x: e.touches[0].clientX, y: e.touches[0].clientY };
      }
    }, { passive: true });

    window.addEventListener('touchmove', (e) => {
      if (!this.isDragging || e.touches.length !== 1) return;
      const dx = e.touches[0].clientX - this.mousePrev.x;
      const dy = e.touches[0].clientY - this.mousePrev.y;
      this.targetRotation.y += dx * 0.007;
      this.targetRotation.x += dy * 0.007;
      this.mousePrev = { x: e.touches[0].clientX, y: e.touches[0].clientY };
    }, { passive: true });

    window.addEventListener('touchend', () => {
      this.isDragging = false;
    });

    // Zoom on wheel
    el.addEventListener('wheel', (e) => {
      e.preventDefault();
      this.cameraDistance += e.deltaY * 0.005;
      this.cameraDistance = Math.max(5.0, Math.min(14.0, this.cameraDistance));
      this.camera.position.z = this.cameraDistance;
    }, { passive: false });
  }

  setMode(mode) {
    this.mode = mode;
    if (mode === 'hologram') {
      this.coreMat.wireframe = false;
      this.coreMat.opacity = 0.65;
      this.shieldMat.opacity = 0.25;
      this.orbitalRing1.visible = true;
      this.orbitalRing2.visible = true;
      this.particleSystem.visible = true;
    } else if (mode === 'wireframe') {
      this.coreMat.wireframe = true;
      this.coreMat.opacity = 0.9;
      this.shieldMat.opacity = 0.55;
      this.orbitalRing1.visible = true;
      this.orbitalRing2.visible = true;
      this.particleSystem.visible = false;
    } else if (mode === 'quantum') {
      this.coreMat.wireframe = false;
      this.coreMat.opacity = 0.35;
      this.shieldMat.opacity = 0.15;
      this.orbitalRing1.visible = true;
      this.orbitalRing2.visible = true;
      this.particleSystem.visible = true;
    }
  }

  resetCamera() {
    this.targetRotation = { x: 0.2, y: 0.3 };
    this.cameraDistance = 8.5;
    if (this.camera) {
      this.camera.position.set(0, 0, this.cameraDistance);
    }
  }

  /* -------------------------------------------------------------
     LIVE REQUEST PHOTON PACKET & DEFENSE REACTIONS
     ------------------------------------------------------------- */
  fireRequestPulse(decisionType = 'ALLOWED', details = {}) {
    if (!this.scene) return;

    // Origin: Left side client quadrant
    const origin = new THREE.Vector3(-6, (Math.random() - 0.5) * 2, (Math.random() - 0.5) * 2);
    const target = new THREE.Vector3(0, 0, 0);

    let photonColor = 0x00f5a0; // Allowed: Emerald
    if (decisionType === 'LIMITED') photonColor = 0xffb300; // Limited: Amber
    if (decisionType === 'BLOCKED') photonColor = 0xff0055; // Blocked: Crimson

    const packetGeo = new THREE.SphereGeometry(0.12, 8, 8);
    const packetMat = new THREE.MeshBasicMaterial({ color: photonColor });
    const packetMesh = new THREE.Mesh(packetGeo, packetMat);
    packetMesh.position.copy(origin);
    this.scene.add(packetMesh);

    this.incomingPackets.push({
      mesh: packetMesh,
      origin: origin.clone(),
      target: target.clone(),
      progress: 0,
      speed: 0.06,
      decisionType: decisionType,
    });
  }

  triggerBarrierShockwave(colorHex = 0x00f2fe, scaleMax = 4.2) {
    if (!this.scene) return;

    const ringGeo = new THREE.RingGeometry(2.35, 2.45, 48);
    const ringMat = new THREE.MeshBasicMaterial({
      color: colorHex,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.9,
    });
    const wave = new THREE.Mesh(ringGeo, ringMat);
    wave.rotation.x = Math.PI / 2;
    this.scene.add(wave);

    this.activeShockwaves.push({
      mesh: wave,
      scale: 1,
      maxScale: scaleMax,
      opacity: 0.9,
    });
  }

  triggerAlarmLockdown() {
    this.alarmActive = true;
    if (this.coreMat) {
      this.coreMat.color.setHex(0xff0055);
      this.coreMat.emissive.setHex(0x550011);
    }
    if (this.shieldMat) {
      this.shieldMat.color.setHex(0xff0055);
      this.shieldMat.opacity = 0.7;
    }
    if (this.coreLight) {
      this.coreLight.color.setHex(0xff0055);
    }

    clearTimeout(this.alarmTimer);
    this.alarmTimer = setTimeout(() => {
      this.alarmActive = false;
      if (this.coreMat) {
        this.coreMat.color.setHex(0x00f2fe);
        this.coreMat.emissive.setHex(0x061e38);
      }
      if (this.shieldMat) {
        this.shieldMat.color.setHex(0x00f2fe);
        this.shieldMat.opacity = 0.25;
      }
      if (this.coreLight) {
        this.coreLight.color.setHex(0x00f2fe);
      }
    }, 2800);
  }

  animate() {
    requestAnimationFrame(() => this.animate());

    // 1. Smooth Inertia Camera Drag Rotation
    this.currentRotation.x += (this.targetRotation.x - this.currentRotation.x) * 0.1;
    this.currentRotation.y += (this.targetRotation.y - this.currentRotation.y) * 0.1;

    if (!this.isDragging) {
      // Idle Auto-Rotation
      this.targetRotation.y += 0.0025;
    }

    // 2. Rotate 3D Core and Rings
    if (this.coreMesh) {
      this.coreMesh.rotation.x = this.currentRotation.x;
      this.coreMesh.rotation.y = this.currentRotation.y;
      this.coreWireframe.rotation.x = this.currentRotation.x;
      this.coreWireframe.rotation.y = this.currentRotation.y;

      // Gentle pulsating breath
      const pulse = 1 + Math.sin(Date.now() * 0.003) * 0.04;
      this.coreMesh.scale.set(pulse, pulse, pulse);
    }

    if (this.shieldGeodesic) {
      this.shieldGeodesic.rotation.y -= 0.0015;
      this.shieldGeodesic.rotation.x += 0.001;
    }

    if (this.orbitalRing1) {
      this.orbitalRing1.rotation.z += 0.004;
    }
    if (this.orbitalRing2) {
      this.orbitalRing2.rotation.z -= 0.005;
    }

    // 3. Update Satellites along Orbit
    this.satellites.forEach((sat) => {
      sat.userData.angle += sat.userData.speed;
      sat.position.x = Math.cos(sat.userData.angle) * sat.userData.radius;
      sat.position.y = Math.sin(sat.userData.angle) * sat.userData.radius * 0.5;
      sat.position.z = Math.sin(sat.userData.angle) * sat.userData.radius;
    });

    // 4. Update Ambient Particle Field
    if (this.particleSystem) {
      this.particleSystem.rotation.y += 0.0006;
    }

    // 5. Update In-Flight Photon Packets
    for (let i = this.incomingPackets.length - 1; i >= 0; i--) {
      const p = this.incomingPackets[i];
      p.progress += p.speed;
      p.mesh.position.lerpVectors(p.origin, p.target, p.progress);

      if (p.progress >= 1.0) {
        // Impact barrier center!
        if (p.decisionType === 'ALLOWED') {
          this.triggerBarrierShockwave(0x00f5a0, 3.2);
        } else if (p.decisionType === 'LIMITED') {
          this.triggerBarrierShockwave(0xffb300, 4.0);
        } else if (p.decisionType === 'BLOCKED') {
          this.triggerBarrierShockwave(0xff0055, 4.8);
          this.triggerAlarmLockdown();
        }

        this.scene.remove(p.mesh);
        this.incomingPackets.splice(i, 1);
      }
    }

    // 6. Update Expanding Shockwaves
    for (let i = this.activeShockwaves.length - 1; i >= 0; i--) {
      const s = this.activeShockwaves[i];
      s.scale += 0.08;
      s.opacity -= 0.025;
      s.mesh.scale.set(s.scale, s.scale, s.scale);
      s.mesh.material.opacity = Math.max(0, s.opacity);

      if (s.opacity <= 0 || s.scale >= s.maxScale) {
        this.scene.remove(s.mesh);
        this.activeShockwaves.splice(i, 1);
      }
    }

    if (this.renderer && this.scene && this.camera) {
      this.renderer.render(this.scene, this.camera);
    }
  }

  /* -------------------------------------------------------------
     2D CANVAS FALLBACK (FOR NON-WEBGL / HEADLESS SYSTEMS)
     ------------------------------------------------------------- */
  initCanvasFallback() {
    this.container.innerHTML = '<canvas id="fallback-radar-canvas" style="width:100%; height:100%; display:block;"></canvas>';
    const canvas = document.getElementById('fallback-radar-canvas');
    const ctx = canvas.getContext('2d');

    const resize = () => {
      canvas.width = this.container.clientWidth;
      canvas.height = this.container.clientHeight;
    };
    resize();
    window.addEventListener('resize', resize);

    let angle = 0;
    const drawRadar = () => {
      requestAnimationFrame(drawRadar);
      const w = canvas.width;
      const h = canvas.height;
      const cx = w / 2;
      const cy = h / 2;
      const maxR = Math.min(w, h) * 0.42;

      ctx.fillStyle = '#070a13';
      ctx.fillRect(0, 0, w, h);

      // Cyber Grid
      ctx.strokeStyle = 'rgba(0, 242, 254, 0.08)';
      ctx.lineWidth = 1;
      for (let r = maxR * 0.25; r <= maxR; r += maxR * 0.25) {
        ctx.beginPath();
        ctx.arc(cx, cy, r, 0, Math.PI * 2);
        ctx.stroke();
      }

      // Rotating Radar Line
      angle += 0.025;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(cx + Math.cos(angle) * maxR, cy + Math.sin(angle) * maxR);
      ctx.strokeStyle = 'rgba(0, 242, 254, 0.6)';
      ctx.lineWidth = 2;
      ctx.stroke();

      // Central Shield Core
      ctx.beginPath();
      ctx.arc(cx, cy, 24, 0, Math.PI * 2);
      ctx.fillStyle = this.alarmActive ? '#ff0055' : '#00f2fe';
      ctx.shadowColor = this.alarmActive ? '#ff0055' : '#00f2fe';
      ctx.shadowBlur = 20;
      ctx.fill();
      ctx.shadowBlur = 0;
    };
    drawRadar();
  }
}
