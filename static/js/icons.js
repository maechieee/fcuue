(function () {
  const paths = {
    check: '<path d="M20 6 9 17l-5-5"/>',
    x: '<path d="M18 6 6 18M6 6l12 12"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    dash: '<path d="M5 12h14"/>',
    arrowLeft: '<path d="M19 12H5M12 19l-7-7 7-7"/>',
    arrowRight: '<path d="M5 12h14M12 5l7 7-7 7"/>',
    chevronDown: '<path d="m6 9 6 6 6-6"/>',
    chevronLeft: '<path d="m15 18-6-6 6-6"/>',
    chevronRight: '<path d="m9 18 6-6-6-6"/>',
    search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
    grid: '<path d="M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z"/>',
    bag: '<path d="M6 8h12l-1 12H7L6 8Z"/><path d="M9 8a3 3 0 0 1 6 0"/>',
    box: '<path d="m3 7 9-4 9 4-9 4-9-4Z"/><path d="M3 7v10l9 4 9-4V7M12 11v10"/>',
    receipt: '<path d="M7 3h10v18l-2-1.5-2 1.5-2-1.5-2 1.5-2-1.5V3Z"/><path d="M9 8h6M9 12h6M9 16h4"/>',
    person: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    people: '<path d="M16 21a6 6 0 0 0-12 0"/><circle cx="10" cy="8" r="4"/><path d="M22 21a5 5 0 0 0-5-5M17 4a3 3 0 0 1 0 6"/>',
    calendar: '<path d="M7 3v4M17 3v4M4 9h16"/><rect x="4" y="5" width="16" height="16" rx="2"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v6l4 2"/>',
    alert: '<path d="M12 3 2 21h20L12 3Z"/><path d="M12 9v5M12 18h.01"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/>',
    image: '<rect x="3" y="5" width="18" height="14" rx="2"/><circle cx="8" cy="10" r="2"/><path d="m21 16-5-5L5 19"/>',
    trash: '<path d="M3 6h18M8 6V4h8v2M6 6l1 15h10l1-15M10 10v7M14 10v7"/>',
    edit: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5Z"/>',
    eye: '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
    eyeOff: '<path d="M3 3l18 18"/><path d="M10.6 10.6a3 3 0 0 0 4 4"/><path d="M9.5 5.5A10.8 10.8 0 0 1 12 5c6 0 10 7 10 7a17 17 0 0 1-2.2 3.1M6.6 6.6C3.8 8.5 2 12 2 12s4 7 10 7c1.3 0 2.5-.3 3.6-.8"/>',
    lock: '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
    location: '<path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="3"/>',
    mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>',
    graph: '<path d="M4 19V5M4 19h16"/><path d="m7 15 4-4 3 3 5-7"/>',
    bars: '<path d="M5 20V10M12 20V4M19 20v-7"/>',
    download: '<path d="M12 3v12M7 10l5 5 5-5"/><path d="M5 21h14"/>',
    tag: '<path d="M20 13 13 20 4 11V4h7l9 9Z"/><circle cx="8.5" cy="8.5" r="1.5"/>',
    star: '<path d="m12 3 2.7 5.5 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.8 1-6.1-4.4-4.3 6.1-.9L12 3Z"/>',
    shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/>',
    school: '<path d="m3 8 9-4 9 4-9 4-9-4Z"/><path d="M7 10v5c0 2 10 2 10 0v-5"/><path d="M21 8v7"/>',
    mortarboard: '<path d="m3 8 9-4 9 4-9 4-9-4Z"/><path d="M7 10v5c0 2 10 2 10 0v-5"/><path d="M21 8v6"/>',
    book: '<path d="M5 4h7a4 4 0 0 1 4 4v12H9a4 4 0 0 0-4 4V4Z"/><path d="M16 8h3v12h-3"/>',
    journal: '<path d="M6 4h12v16H6z"/><path d="M9 4v16M12 8h3M12 12h3"/><path d="M4 8h2M4 12h2M4 16h2"/>',
    pencil: '<path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-5 1 1-5 12.5-10.5Z"/><path d="m14 6 4 4"/>',
    balloon: '<path d="M12 13c3.3 0 6-2.7 6-6s-2.7-5-6-5-6 1.7-6 5 2.7 6 6 6Z"/><path d="M12 13c0 2-2 2-2 4s4 2 4 5"/><path d="m9 14 3-1 3 1"/>',
    layers: '<path d="m12 2 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5M3 17l9 5 9-5"/>',
    ruler: '<path d="M4 17 17 4l3 3L7 20l-3-3Z"/><path d="m14 7 3 3M11 10l2 2M8 13l3 3"/>',
    store: '<path d="M4 10h16l-1-5H5l-1 5Z"/><path d="M6 10v10h12V10M9 20v-6h6v6"/>',
  };

  function keyFor(name) {
    if (!name) return 'info';
    if (name.includes('chevron-left')) return 'chevronLeft';
    if (name.includes('chevron-right')) return 'chevronRight';
    if (name.includes('chevron-down')) return 'chevronDown';
    if (name.includes('arrow-left')) return 'arrowLeft';
    if (name.includes('arrow-right')) return 'arrowRight';
    if (name === 'x' || name.startsWith('x-')) return name.includes('circle') ? 'alert' : 'x';
    if (name.includes('check')) return 'check';
    if (name.includes('plus')) return 'plus';
    if (name.includes('dash')) return 'dash';
    if (name.includes('search')) return 'search';
    if (name.includes('list') || name.includes('sliders')) return 'menu';
    if (name.includes('grid')) return 'grid';
    if (name.includes('bag')) return 'bag';
    if (name.includes('box')) return 'box';
    if (name.includes('receipt')) return 'receipt';
    if (name.includes('people')) return 'people';
    if (name.includes('person')) return 'person';
    if (name.includes('calendar')) return 'calendar';
    if (name.includes('clock') || name.includes('hourglass')) return 'clock';
    if (name.includes('exclamation')) return 'alert';
    if (name.includes('info') || name.includes('bell')) return 'info';
    if (name.includes('image')) return 'image';
    if (name.includes('trash')) return 'trash';
    if (name.includes('mortarboard')) return 'mortarboard';
    if (name.includes('balloon')) return 'balloon';
    if (name.includes('journal')) return 'journal';
    if (name.includes('book')) return 'book';
    if (name.includes('pencil')) return 'pencil';
    if (name.includes('eye-slash')) return 'eyeOff';
    if (name.includes('eye')) return 'eye';
    if (name.includes('lock')) return 'lock';
    if (name.includes('geo')) return 'location';
    if (name.includes('envelope')) return 'mail';
    if (name.includes('graph')) return 'graph';
    if (name.includes('speedometer')) return 'graph';
    if (name.includes('bar-chart')) return 'bars';
    if (name.includes('download')) return 'download';
    if (name.includes('tag')) return 'tag';
    if (name.includes('star')) return 'star';
    if (name.includes('shield') || name.includes('patch')) return 'shield';
    if (name.includes('school')) return 'school';
    if (name.includes('diagram') || name.includes('layers')) return 'layers';
    if (name.includes('ruler')) return 'ruler';
    if (name.includes('shop')) return 'store';
    return 'info';
  }

  function iconName(el) {
    if (el.dataset.icon) return el.dataset.icon;
    const cls = Array.from(el.classList).find((name) => name.startsWith('bi-') && name !== 'bi');
    return cls ? cls.slice(3) : '';
  }

  function render(el) {
    const name = iconName(el);
    const key = keyFor(name);
    // Guard: skip attribute writes that haven't changed to break potential observer loops
    if (el.dataset.icon !== name) el.dataset.icon = name;
    if (!el.classList.contains('ui-icon')) el.classList.add('ui-icon');
    el.setAttribute('aria-hidden', 'true');
    el.innerHTML = '<svg viewBox="0 0 24 24" focusable="false">' + paths[key] + '</svg>';
  }

  function renderAll(root) {
    if (root.matches?.('[data-icon], .bi')) render(root);
    root.querySelectorAll?.('[data-icon], .bi').forEach(render);
  }

  window.renderLocalIcon = render;
  window.renderLocalIcons = renderAll;

  document.addEventListener('DOMContentLoaded', function () {
    renderAll(document);
    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        if (mutation.type === 'attributes' && (mutation.attributeName === 'class' || mutation.attributeName === 'data-icon')) {
          const el = mutation.target;
          if (el.matches('[data-icon], .bi')) render(el);
        }
      }
    });
    document.querySelectorAll('[data-icon], .bi').forEach((el) => {
      observer.observe(el, { attributes: true });
    });
  });
})();
