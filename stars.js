/* ── Shared Stars & Magic Particles ── */
(function () {
  const canvas = document.getElementById('stars-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let W, H;

  const stars = Array.from({ length: 200 }, () => ({
    x: Math.random() * 9999,
    y: Math.random() * 9999,
    r: Math.random() * 1.2 + 0.2,
    twinkle: Math.random() * Math.PI * 2,
    speed: Math.random() * 0.006 + 0.002,
  }));

  const sparks = Array.from({ length: 20 }, () => ({
    x: Math.random() * 9999,
    y: Math.random() * 9999,
    vx: (Math.random() - 0.5) * 0.45,
    vy: (Math.random() - 0.5) * 0.45,
    r: Math.random() * 2 + 0.8,
    color: Math.random() > 0.5 ? '#c9a84c' : '#9b59b6',
  }));

  function resize() {
    W = canvas.width  = window.innerWidth;
    H = canvas.height = window.innerHeight;
    sparks.forEach(s => {
      if (s.x > W) s.x = Math.random() * W;
      if (s.y > H) s.y = Math.random() * H;
    });
  }
  resize();
  window.addEventListener('resize', resize);

  function draw(t) {
    ctx.clearRect(0, 0, W, H);

    stars.forEach(s => {
      s.twinkle += s.speed;
      const a = 0.15 + 0.55 * (0.5 + 0.5 * Math.sin(s.twinkle));
      ctx.beginPath();
      ctx.arc(s.x % W, s.y % H, s.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(232,220,200,${a})`;
      ctx.fill();
    });

    sparks.forEach(sp => {
      sp.x += sp.vx; sp.y += sp.vy;
      if (sp.x < 0) sp.x = W; if (sp.x > W) sp.x = 0;
      if (sp.y < 0) sp.y = H; if (sp.y > H) sp.y = 0;
      const a = 0.25 + 0.5 * Math.abs(Math.sin(t * 0.001 + sp.x * 0.01));
      const hex = Math.floor(a * 255).toString(16).padStart(2, '0');
      ctx.beginPath();
      ctx.arc(sp.x, sp.y, sp.r, 0, Math.PI * 2);
      ctx.fillStyle = sp.color + hex;
      ctx.fill();
      ctx.beginPath();
      ctx.arc(sp.x, sp.y, sp.r * 3.5, 0, Math.PI * 2);
      ctx.fillStyle = sp.color + '14';
      ctx.fill();
    });

    requestAnimationFrame(draw);
  }
  requestAnimationFrame(draw);

  /* Fade-in on scroll */
  const obs = new IntersectionObserver(
    entries => entries.forEach(e => {
      if (e.isIntersecting) { e.target.classList.add('visible'); obs.unobserve(e.target); }
    }),
    { threshold: 0.08 }
  );
  document.querySelectorAll('.fade-up').forEach(el => obs.observe(el));

  /* ── Hamburger Menu ── */
  const hamburger = document.getElementById('nav-hamburger');
  const navEl     = document.querySelector('nav');
  const desktopUl = document.querySelector('.nav-links');

  if (hamburger && navEl && desktopUl) {
    // Build mobile nav by cloning desktop links
    const mobileNav = document.createElement('div');
    mobileNav.id = 'mobile-nav';
    mobileNav.className = 'mobile-nav';
    mobileNav.innerHTML = `<ul>${desktopUl.innerHTML}</ul>`;
    navEl.insertAdjacentElement('afterend', mobileNav);

    const toggle = (force) => {
      const isOpen = typeof force === 'boolean' ? force : !mobileNav.classList.contains('open');
      mobileNav.classList.toggle('open', isOpen);
      hamburger.classList.toggle('open', isOpen);
      hamburger.setAttribute('aria-expanded', isOpen);
    };

    hamburger.addEventListener('click', e => { e.stopPropagation(); toggle(); });

    mobileNav.querySelectorAll('a').forEach(a =>
      a.addEventListener('click', () => toggle(false))
    );

    document.addEventListener('click', e => {
      if (!hamburger.contains(e.target) && !mobileNav.contains(e.target)) toggle(false);
    });
  }
})();
