/* Display hardware. Presentation preferences never change invoice data. */
(() => {
  'use strict';
  const root = document.documentElement;
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const storageKey = 'invoicecraft-console-display';
  let saved = {};
  try { saved = JSON.parse(localStorage.getItem(storageKey) || '{}'); } catch { /* Use the physical defaults. */ }
  let state = {
    brightness: Math.min(100, Math.max(45, Number(saved.brightness) || 100)),
    effects: saved.effects !== false,
    phosphor: saved.phosphor === 'amber' ? 'amber' : 'green',
  };
  const persist = () => { try { localStorage.setItem(storageKey, JSON.stringify(state)); } catch { /* The display still works without storage. */ } };
  function apply() {
    root.dataset.consolePhosphor = state.phosphor;
    root.dataset.consoleEffects = state.effects && !reducedMotion.matches ? 'on' : 'off';
    root.style.setProperty('--display-brightness', String(state.brightness / 100));
    root.style.setProperty('--knob-angle', `${-135 + ((state.brightness - 45) / 55) * 270}deg`);
    document.querySelectorAll('[data-console-brightness]').forEach((el) => { el.value = String(state.brightness); });
    document.querySelectorAll('[data-console-brightness-value]').forEach((el) => { el.textContent = String(state.brightness); });
    document.querySelectorAll('input[data-console-effects]').forEach((el) => { el.checked = state.effects && !reducedMotion.matches; });
    document.querySelectorAll('button[data-console-phosphor]').forEach((el) => { el.setAttribute('aria-pressed', String(el.dataset.consolePhosphor === state.phosphor)); });
  }
  apply();
  const rack = document.querySelector('[data-console-rack]');
  const rackSize = window.matchMedia('(min-width: 1101px)');
  if (rack) { rack.open = rackSize.matches; rackSize.addEventListener('change', () => { rack.open = rackSize.matches; }); }
  reducedMotion.addEventListener('change', apply);
  document.querySelectorAll('[data-console-brightness]').forEach((el) => el.addEventListener('input', () => {
    state.brightness = Number(el.value); apply(); persist();
  }));
  document.querySelectorAll('input[data-console-effects]').forEach((el) => el.addEventListener('change', () => {
    state.effects = el.checked; apply(); persist();
  }));
  let changeTimer;
  document.querySelectorAll('button[data-console-phosphor]').forEach((el) => el.addEventListener('click', () => {
    if (state.phosphor === el.dataset.consolePhosphor) return;
    state.phosphor = el.dataset.consolePhosphor; apply(); persist();
    if (state.effects && !reducedMotion.matches) {
      root.classList.remove('channel-changing');
      void root.offsetWidth;
      root.classList.add('channel-changing');
      clearTimeout(changeTimer);
      changeTimer = setTimeout(() => root.classList.remove('channel-changing'), 330);
    }
  }));
  const clock = () => {
    const now = new Date();
    const time = [now.getHours(), now.getMinutes(), now.getSeconds()].map((value) => String(value).padStart(2, '0')).join(':');
    const date = [now.getFullYear(), String(now.getMonth() + 1).padStart(2, '0'), String(now.getDate()).padStart(2, '0')].join('-');
    const weekday = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'][now.getDay()];
    document.querySelectorAll('[data-console-date]').forEach((el) => { el.textContent = `${date} ${weekday}`; });
    document.querySelectorAll('[data-console-clock]').forEach((el) => { el.textContent = time; });
  };
  clock();
  setInterval(clock, 1000);
  const boot = document.querySelector('[data-console-boot]');
  if (boot && state.effects && !reducedMotion.matches) {
    const text = boot.dataset.consoleText;
    let index = 0;
    boot.textContent = '';
    root.classList.add('console-booting');
    const timer = setInterval(() => {
      if (!state.effects || reducedMotion.matches) { boot.textContent = text; clearInterval(timer); root.classList.remove('console-booting'); return; }
      index = Math.min(text.length, index + 1);
      boot.textContent = text.slice(0, index);
      if (index === text.length) { clearInterval(timer); root.classList.remove('console-booting'); }
    }, 1000 / 12);
  }
})();
