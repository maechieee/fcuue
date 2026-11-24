document.addEventListener('DOMContentLoaded', function () {

  /* ── Navbar: scroll shadow (nav JS is also inline in base.html
     for immediate execution, but this handles DOMContentLoaded path) */
  const nav = document.getElementById('mainNav');
  if (nav) {
    const applyNavShadow = () => {
      nav.style.boxShadow = window.scrollY > 10
        ? '0 4px 24px rgba(19,40,78,.14)'
        : '0 2px 20px rgba(19,40,78,.08)';
    };
    window.addEventListener('scroll', applyNavShadow, { passive: true });
    applyNavShadow();
  }

  /* ── Live product search (shop page) ────────────────────────── */
  const searchInput = document.getElementById('liveSearchInput');
  if (searchInput) {
    let debounceTimer;

    function submitSearch() {
      const q   = searchInput.value.trim();
      const url = new URL(window.location.href);
      if (q) {
        url.searchParams.set('q', q);
      } else {
        url.searchParams.delete('q');
      }
      url.searchParams.delete('page');
      window.location.href = url.toString();
    }

    searchInput.addEventListener('input', () => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(submitSearch, 450);
    });

    searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        clearTimeout(debounceTimer);
        submitSearch();
      }
    });
  }

  /* ── Animated number counters ───────────────────────────────── */
  const counters = document.querySelectorAll('[data-count-to]');
  if (counters.length) {
    const animateCount = (el) => {
      const target   = parseFloat(el.dataset.countTo);
      const prefix   = el.dataset.prefix  || '';
      const suffix   = el.dataset.suffix  || '';
      const duration = 1400;
      const start    = performance.now();
      const update   = (now) => {
        const progress = Math.min((now - start) / duration, 1);
        const eased    = 1 - Math.pow(1 - progress, 3);
        const current  = Math.round(target * eased);
        el.textContent = prefix + current.toLocaleString() + suffix;
        if (progress < 1) requestAnimationFrame(update);
      };
      requestAnimationFrame(update);
    };

    const io = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          animateCount(e.target);
          io.unobserve(e.target);
        }
      });
    }, { threshold: 0.5 });

    counters.forEach(c => io.observe(c));
  }

  /* ── Cart: live quantity stepper with subtotal flash ─────────── */
  window.stepQty = function (btn, delta) {
    const input = btn.closest('.qty-stepper').querySelector('.qty-field');
    const val   = parseInt(input.value) + delta;
    const min   = parseInt(input.min) ?? 0;
    const max   = parseInt(input.max) ?? 99;
    if (val >= min && val <= max) {
      input.value = val;
      input.dispatchEvent(new Event('change'));
    }
  };

  /* ── Fade-in on scroll (sections with data-fade) ─────────────── */
  const fadeEls = document.querySelectorAll('[data-fade]');
  if (fadeEls.length) {
    const fadeObserver = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          e.target.style.opacity   = '1';
          e.target.style.transform = 'translateY(0)';
          fadeObserver.unobserve(e.target);
        }
      });
    }, { threshold: 0.12 });

    fadeEls.forEach(el => {
      el.style.opacity    = '0';
      el.style.transform  = 'translateY(24px)';
      el.style.transition = 'opacity .55s ease, transform .55s ease';
      fadeObserver.observe(el);
    });
  }

  /* ── Confirm-before-submit for destructive buttons ───────────── */
  document.querySelectorAll('[data-confirm]').forEach(form => {
    form.addEventListener('submit', e => {
      const msg = form.dataset.confirm || 'Are you sure?';
      if (!confirm(msg)) e.preventDefault();
    });
  });

});
