/* ═══════════════════════════════════════════════
   OpenCrawler — iOS 级动效引擎
   滚动触发 · 视差 · 磁吸 · 3D倾斜 · 涟漪 · 进度条
   ═══════════════════════════════════════════════ */
(function() {
  'use strict';

  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ── 1. 滚动进度条 ──
  function initScrollProgress() {
    if (prefersReducedMotion) return;
    const bar = document.createElement('div');
    bar.className = 'scroll-progress';
    document.body.appendChild(bar);

    let ticking = false;
    function update() {
      const h = document.documentElement;
      const scrolled = (h.scrollTop) / (h.scrollHeight - h.clientHeight) * 100;
      bar.style.width = Math.min(scrolled, 100) + '%';
      ticking = false;
    }
    window.addEventListener('scroll', function() {
      if (!ticking) {
        requestAnimationFrame(update);
        ticking = true;
      }
    }, { passive: true });
    update();
  }

  // ── 2. 滚动入场动画 (IntersectionObserver) ──
  function initScrollReveal() {
    if (prefersReducedMotion) {
      document.querySelectorAll('[data-reveal]').forEach(el => el.classList.add('revealed'));
      return;
    }
    const observer = new IntersectionObserver(function(entries) {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          // 延迟以支持 data-delay 属性
          const delay = entry.target.dataset.delay || 0;
          setTimeout(() => {
            entry.target.classList.add('revealed');
          }, parseInt(delay));
          observer.unobserve(entry.target);
        }
      });
    }, {
      threshold: 0.08,
      rootMargin: '0px 0px -40px 0px'
    });

    document.querySelectorAll('[data-reveal]').forEach(el => observer.observe(el));
  }

  // ── 3. 导航栏滚动毛玻璃增强 ──
  function initNavScroll() {
    const nav = document.querySelector('.navbar');
    if (!nav) return;
    let ticking = false;
    function update() {
      if (window.scrollY > 10) {
        nav.classList.add('scrolled');
      } else {
        nav.classList.remove('scrolled');
      }
      ticking = false;
    }
    window.addEventListener('scroll', function() {
      if (!ticking) {
        requestAnimationFrame(update);
        ticking = true;
      }
    }, { passive: true });
  }

  // ── 4. 视差滚动 ──
  function initParallax() {
    if (prefersReducedMotion) return;
    const elements = document.querySelectorAll('[data-parallax]');
    if (elements.length === 0) return;

    let ticking = false;
    function update() {
      const scrollY = window.scrollY;
      elements.forEach(el => {
        const speed = parseFloat(el.dataset.parallax) || 0.3;
        const offset = scrollY * speed;
        el.style.transform = `translate3d(0, ${offset}px, 0)`;
      });
      ticking = false;
    }
    window.addEventListener('scroll', function() {
      if (!ticking) {
        requestAnimationFrame(update);
        ticking = true;
      }
    }, { passive: true });
  }

  // ── 5. 磁吸按钮 ──
  function initMagnetic() {
    if (prefersReducedMotion) return;
    document.querySelectorAll('[data-magnetic]').forEach(btn => {
      const strength = parseFloat(btn.dataset.magnetic) || 0.3;
      btn.style.willChange = 'transform';

      btn.addEventListener('mousemove', function(e) {
        const rect = btn.getBoundingClientRect();
        const x = e.clientX - rect.left - rect.width / 2;
        const y = e.clientY - rect.top - rect.height / 2;
        btn.style.transform = `translate(${x * strength}px, ${y * strength}px)`;
      });

      btn.addEventListener('mouseleave', function() {
        btn.style.transform = '';
      });
    });
  }

  // ── 6. 3D 卡片倾斜 ──
  function initTilt() {
    if (prefersReducedMotion) return;
    document.querySelectorAll('[data-tilt]').forEach(card => {
      const maxTilt = parseFloat(card.dataset.tilt) || 8;
      card.style.willChange = 'transform';

      card.addEventListener('mousemove', function(e) {
        const rect = card.getBoundingClientRect();
        const x = (e.clientX - rect.left) / rect.width;
        const y = (e.clientY - rect.top) / rect.height;
        const tiltX = (y - 0.5) * maxTilt * 2;
        const tiltY = (x - 0.5) * maxTilt * -2;
        card.style.transform = `perspective(800px) rotateX(${tiltX}deg) rotateY(${tiltY}deg) translateY(-4px)`;
      });

      card.addEventListener('mouseleave', function() {
        card.style.transform = '';
      });
    });
  }

  // ── 7. 涟漪效果 ──
  function initRipple() {
    if (prefersReducedMotion) return;
    document.querySelectorAll('.btn, .nav-cta, .btn-primary, .btn-submit').forEach(btn => {
      btn.style.position = btn.style.position || 'relative';
      btn.style.overflow = 'hidden';

      btn.addEventListener('click', function(e) {
        const rect = btn.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = e.clientX - rect.left - size / 2;
        const y = e.clientY - rect.top - size / 2;

        const ripple = document.createElement('span');
        ripple.className = 'ripple';
        ripple.style.width = ripple.style.height = size + 'px';
        ripple.style.left = x + 'px';
        ripple.style.top = y + 'px';

        btn.appendChild(ripple);
        setTimeout(() => ripple.remove(), 600);
      });
    });
  }

  // ── 8. 数字计数动画 ──
  function initCountUp() {
    if (prefersReducedMotion) return;
    const observer = new IntersectionObserver(function(entries) {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        const el = entry.target;
        const target = parseInt(el.dataset.count) || 0;
        const duration = parseInt(el.dataset.duration) || 1200;
        const suffix = el.dataset.suffix || '';
        const startTime = performance.now();

        function tick(now) {
          const elapsed = now - startTime;
          const progress = Math.min(elapsed / duration, 1);
          // easeOutExpo
          const eased = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
          el.textContent = Math.floor(eased * target).toLocaleString() + suffix;
          if (progress < 1) requestAnimationFrame(tick);
          else el.textContent = target.toLocaleString() + suffix;
        }
        requestAnimationFrame(tick);
        observer.unobserve(el);
      });
    }, { threshold: 0.5 });

    document.querySelectorAll('[data-count]').forEach(el => observer.observe(el));
  }

  // ── 9. Hero 文字逐字入场 ──
  function initHeroText() {
    if (prefersReducedMotion) return;
    const hero = document.querySelector('.landing-hero h1, .hero h1');
    if (!hero) return;
    const text = hero.textContent;
    hero.innerHTML = '';
    const words = text.split(' ');
    words.forEach((word, i) => {
      const span = document.createElement('span');
      span.textContent = word + ' ';
      span.style.display = 'inline-block';
      span.style.opacity = '0';
      span.style.transform = 'translateY(20px)';
      span.style.transition = 'opacity 0.5s cubic-bezier(0.16,1,0.3,1), transform 0.5s cubic-bezier(0.16,1,0.3,1)';
      span.style.transitionDelay = (i * 0.06 + 0.2) + 's';
      hero.appendChild(span);
      requestAnimationFrame(() => {
        span.style.opacity = '1';
        span.style.transform = 'translateY(0)';
      });
    });
  }

  // ── 10. 列表项动态交错 (用于动态加载的内容) ──
  window.animateStaggerIn = function(container, selector) {
    if (prefersReducedMotion) return;
    const items = container.querySelectorAll(selector || ':scope > *');
    items.forEach((item, i) => {
      item.style.opacity = '0';
      item.style.transform = 'translateY(20px)';
      item.style.transition = 'opacity 0.35s cubic-bezier(0.16,1,0.3,1), transform 0.35s cubic-bezier(0.16,1,0.3,1)';
      item.style.transitionDelay = (i * 0.04) + 's';
      requestAnimationFrame(() => {
        item.style.opacity = '1';
        item.style.transform = '';
      });
    });
  };

  // ── 11. 骨架屏 → 内容淡入 ──
  window.showSkeletonThenLoad = function(container, skeletonCount, loadFn) {
    const skelHtml = Array(skeletonCount).fill(0).map(() =>
      '<div class="skeleton" style="padding:16px;margin-bottom:10px;border-radius:12px;">' +
      '<div class="skeleton skeleton-text" style="width:70%"></div>' +
      '<div class="skeleton skeleton-text" style="width:90%"></div>' +
      '<div class="skeleton skeleton-text" style="width:40%"></div>' +
      '</div>'
    ).join('');
    container.innerHTML = skelHtml;
    loadFn();
  };

  // ── 12. 触觉反馈模拟 (视觉) ──
  window.hapticFeedback = function(element) {
    if (prefersReducedMotion) return;
    element.style.transition = 'transform 0.1s ease-out';
    element.style.transform = 'scale(0.97)';
    setTimeout(() => {
      element.style.transform = '';
      setTimeout(() => { element.style.transition = ''; }, 100);
    }, 80);
  };

  // ── 初始化 ──
  function init() {
    initScrollProgress();
    initScrollReveal();
    initNavScroll();
    initParallax();
    initMagnetic();
    initTilt();
    initRipple();
    initCountUp();
    initHeroText();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
