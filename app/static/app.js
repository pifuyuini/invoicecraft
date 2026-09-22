/* InvoiceCraft: a small, deliberately framework-free workspace. */
(() => {
  'use strict';
  let strings = JSON.parse(document.getElementById('ui-strings')?.textContent || '{}');
  let language = document.documentElement.lang;
  const t = (key) => strings[key] || key;
  function translateDOM(root = document) {
    root.querySelectorAll('[data-ui-language]').forEach((el) => { el.hidden = el.dataset.uiLanguage !== language; });
    root.querySelectorAll('[data-i18n]').forEach((el) => { el.textContent = t(el.dataset.i18n); });
    root.querySelectorAll('[data-i18n-placeholder]').forEach((el) => { el.placeholder = t(el.dataset.i18nPlaceholder); });
    root.querySelectorAll('[data-i18n-aria]').forEach((el) => { el.setAttribute('aria-label', t(el.dataset.i18nAria)); });
  }
  window.toast = function toast(message, kind = 'success') {
    const el = document.createElement('div');
    el.className = `toast toast-${kind}`;
    el.setAttribute('role', 'status');
    el.textContent = message;
    const close = document.createElement('button');
    close.type = 'button'; close.textContent = '×'; close.setAttribute('aria-label', t('Close'));
    close.onclick = () => el.remove(); el.append(close);
    document.getElementById('toasts').append(el);
    setTimeout(() => el.remove(), 6500);
  };
  document.querySelectorAll('#toasts .toast').forEach((el) => setTimeout(() => el.remove(), 6500));
  const dirtyForms = new Map();
  function snapshot(form) { return new URLSearchParams(new FormData(form)).toString(); }
  function refreshDirty(form) {
    const record = dirtyForms.get(form);
    record.dirty = snapshot(form) !== record.initial;
    const label = form.querySelector('[data-save-state]');
    if (label) {
      const key = record.dirty ? 'Unsaved changes' : 'No unsaved changes';
      label.dataset.i18n = key; label.textContent = t(key); label.classList.toggle('dirty', record.dirty);
    }
  }
  document.querySelectorAll('[data-dirty-form]').forEach((form) => {
    dirtyForms.set(form, {initial: snapshot(form), dirty: false});
    form.addEventListener('input', () => refreshDirty(form));
    form.addEventListener('change', () => refreshDirty(form));
  });
  window.addEventListener('beforeunload', (event) => {
    if ([...dirtyForms.values()].some((record) => record.dirty)) { event.preventDefault(); event.returnValue = ''; }
  });
  document.querySelectorAll('[data-language-select]').forEach((select) => select.addEventListener('change', async () => {
    const requested = select.value; select.disabled = true;
    try {
      const response = await fetch('/language', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({language:requested})});
      if (!response.ok) throw new Error('language');
      const oldTitle = document.title.split(' — ')[0];
      const titleKey = Object.keys(strings).find((key) => strings[key] === oldTitle) || oldTitle;
      const result = await response.json(); strings = result.strings; language = result.language;
      document.title = `${t(titleKey)} — InvoiceCraft`;
      document.documentElement.lang = language; translateDOM();
      document.querySelectorAll('[data-language-select]').forEach((el) => { el.value = language; });
      const preference = document.querySelector('.settings-form [name=language]');
      if (preference) { preference.value = language; refreshDirty(preference.form); }
    } catch { select.value = language; window.toast(t('Could not change language. Please try again.'), 'error'); }
    finally { select.disabled = false; }
  }));
  let navFocus = null;
  const navViewport = window.matchMedia('(max-width: 760px)');
  const syncNavFocus = () => {
    const sidebar = document.getElementById('sidebar');
    if (sidebar) sidebar.inert = navViewport.matches && !document.body.classList.contains('nav-open');
  };
  navViewport.addEventListener('change', syncNavFocus);
  syncNavFocus();
  const closeNav = () => {
    document.body.classList.remove('nav-open');
    document.querySelector('[data-nav-toggle]')?.setAttribute('aria-expanded','false');
    const backdrop = document.querySelector('[data-close-nav]'); if (backdrop) backdrop.hidden = true;
    syncNavFocus();
    navFocus?.focus();
  };
  document.querySelector('[data-nav-toggle]')?.addEventListener('click', (event) => {
    navFocus = event.currentTarget;
    const open = document.body.classList.toggle('nav-open');
    navFocus.setAttribute('aria-expanded',String(open)); document.querySelector('[data-close-nav]').hidden = !open;
    syncNavFocus();
    if (open) document.querySelector('.workspace-nav a')?.focus();
  });
  document.querySelector('[data-close-nav]')?.addEventListener('click', closeNav);
  document.addEventListener('keydown',(event) => { if (event.key === 'Escape' && document.body.classList.contains('nav-open')) closeNav(); });
  let dialogTrigger = null;
  document.addEventListener('click', async (event) => {
    const open = event.target.closest('[data-open-dialog]');
    if (open) { dialogTrigger = open; document.getElementById(open.dataset.openDialog).showModal(); }
    const close = event.target.closest('[data-close-dialog]'); if (close) close.closest('dialog').close();
    const copy = event.target.closest('[data-copy]');
    if (copy) {
      try {
        if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(copy.dataset.copy);
        else {
          const field = document.createElement('textarea'); field.value = copy.dataset.copy; field.style.position='fixed'; field.style.opacity='0'; document.body.append(field); field.select();
          const copied = document.execCommand('copy'); field.remove(); if (!copied) throw new Error('copy');
        }
        window.toast(t('Link copied'));
      } catch { window.prompt(t('Copy this link:'),copy.dataset.copy); }
    }
    const password = event.target.closest('[data-pw-toggle]');
    if (password) { const input = password.parentElement.querySelector('input'); input.type = input.type === 'password' ? 'text' : 'password'; const key = input.type === 'password' ? 'Show' : 'Hide'; password.dataset.i18n=key; password.textContent=t(key); }
  });
  document.querySelectorAll('dialog').forEach((dialog) => {
    dialog.addEventListener('close',() => dialogTrigger?.focus());
    dialog.addEventListener('click',(event) => { if (event.target === dialog) { const rect=dialog.getBoundingClientRect(); if (event.clientX<rect.left || event.clientX>rect.right || event.clientY<rect.top || event.clientY>rect.bottom) dialog.close(); } });
  });
  document.querySelectorAll('form').forEach((form) => form.addEventListener('submit',(event) => {
    if (form.id === 'inline-client-form') return;
    if (form.dataset.confirm && !window.confirm(`${t('Delete')} “${form.dataset.confirm}”? ${t('This cannot be undone.')}`)) {event.preventDefault();return;}
    if (event.defaultPrevented || !form.checkValidity()) return;
    if (dirtyForms.has(form)) dirtyForms.get(form).dirty=false;
    if (form.method.toLowerCase()==='post') {
      form.querySelectorAll('button[type=submit]').forEach((button) => {button.disabled=true;button.setAttribute('aria-busy','true');});
    }
  }));
  document.querySelectorAll('[data-remember-list]').forEach((link) => link.addEventListener('click',() => {
    sessionStorage.setItem('invoicecraft-list-position',JSON.stringify({path:location.pathname+location.search,y:window.scrollY}));
  }));
  try { const saved=JSON.parse(sessionStorage.getItem('invoicecraft-list-position')||'null'); if(saved?.path===location.pathname+location.search){window.scrollTo(0,saved.y);sessionStorage.removeItem('invoicecraft-list-position');} } catch { /* Position is optional. */ }
  document.querySelectorAll('.field-error').forEach((error) => {
    if(error.textContent.trim()) {const control=error.parentElement.querySelector('input,select,textarea');control?.setAttribute('aria-invalid','true');}
  });
  document.querySelector('[aria-invalid=true]')?.focus();
  const invoiceForm=document.getElementById('invoice-form');
  if(!invoiceForm) return;
  const items=document.getElementById('items-body');
  const preview=document.getElementById('invoice-preview');
  const previewState=document.getElementById('preview-state');
  let previewTimer=null, previewController=null;
  function state(key){previewState.dataset.i18n=key;previewState.textContent=t(key);}
  async function updatePreview(){
    previewController?.abort();previewController=new AbortController();
    preview.parentElement.setAttribute('aria-busy','true');state('Updating…');
    const payload=new FormData(invoiceForm);
    const descriptions=payload.getAll('description');payload.delete('description');
    descriptions.forEach((value)=>payload.append('description',value.trim() || t('Description')));
    try{
      const response=await fetch('/invoices/preview',{method:'POST',body:payload,signal:previewController.signal,headers:{Accept:'application/json'}});
      const result=await response.json();
      if(!response.ok){
        if(result.errors){Object.entries(result.errors).forEach(([key,message])=>{const el=invoiceForm.querySelector(`[data-error-for="${key}"]`);if(el){el.dataset.i18n=message;el.textContent=t(message);el.parentElement.querySelector('input,select,textarea')?.setAttribute('aria-invalid','true');}});}
        state('Check your details');return;
      }
      preview.innerHTML=result.html;
      invoiceForm.querySelectorAll('[data-error-for]').forEach((el)=>{el.textContent='';delete el.dataset.i18n;});
      invoiceForm.querySelectorAll('[aria-invalid=true]').forEach((el)=>el.removeAttribute('aria-invalid'));
      const amounts=preview.querySelectorAll('.document-items tbody tr td:last-child');
      items.querySelectorAll('.row-amount').forEach((el,index)=>{el.textContent=amounts[index]?.textContent || '—';});
      state('Up to date');
    }catch(error){if(error.name!=='AbortError')state('Preview unavailable');}
    finally{preview.parentElement.removeAttribute('aria-busy');}
  }
  function queuePreview(){clearTimeout(previewTimer);previewTimer=setTimeout(updatePreview,280);}
  function renumber(){
    items.querySelectorAll('[data-item-row]').forEach((row,index)=>{
      row.querySelector('.item-number').textContent=String(index+1).padStart(2,'0');
      row.querySelectorAll('[name]').forEach((field)=>{
        const key=`${field.name}_${index}`; field.setAttribute('aria-describedby',`error-${key}`);
        const error=field.parentElement.querySelector('.field-error');if(error){error.id=`error-${key}`;error.dataset.errorFor=key;}
      });
    });
    refreshDirty(invoiceForm);queuePreview();
  }
  invoiceForm.addEventListener('input',queuePreview);invoiceForm.addEventListener('change',queuePreview);
  document.getElementById('add-item').addEventListener('click',()=>{
    const row=items.firstElementChild.cloneNode(true);
    row.querySelectorAll('input,textarea').forEach((input)=>{input.value=input.name==='quantity'?'1':input.name==='unit_price'?'0':'';input.removeAttribute('aria-invalid');});
    row.querySelectorAll('.field-error').forEach((el)=>{el.textContent='';delete el.dataset.i18n;});row.querySelector('.row-amount').textContent='—';items.append(row);renumber();row.querySelector('textarea').focus();
  });
  items.addEventListener('click',(event)=>{
    const button=event.target.closest('.remove-row');if(!button)return;
    const row=button.closest('[data-item-row]');
    if(items.children.length>1)row.remove();
    else row.querySelectorAll('input,textarea').forEach((input)=>{input.value=input.name==='quantity'?'1':input.name==='unit_price'?'0':'';});
    renumber();document.getElementById('add-item').focus();
  });
  document.querySelectorAll('[data-due-days]').forEach((button)=>button.addEventListener('click',()=>{
    const issue=invoiceForm.elements.issue_date.value;if(!issue)return;
    const date=new Date(`${issue}T12:00:00`);date.setDate(date.getDate()+Number(button.dataset.dueDays));
    invoiceForm.elements.due_date.value=`${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;
    refreshDirty(invoiceForm);queuePreview();
  }));
  document.querySelectorAll('[data-editor-tab]').forEach((button)=>button.addEventListener('click',()=>{
    document.querySelector('[data-editor-view]').dataset.editorView=button.dataset.editorTab;
    document.querySelectorAll('[data-editor-tab]').forEach((el)=>{const active=el===button;el.classList.toggle('active',active);el.setAttribute('aria-pressed',String(active));});
  }));
  document.getElementById('inline-client-form').addEventListener('submit',async(event)=>{
    event.preventDefault();const form=event.currentTarget;const button=form.querySelector('[type=submit]');const error=form.querySelector('[data-dialog-error]');button.disabled=true;error.hidden=true;
    try{
      const response=await fetch('/clients',{method:'POST',body:new FormData(form),headers:{Accept:'application/json'}});const result=await response.json();
      if(!response.ok){error.textContent=t(result.error||Object.values(result.errors||{})[0]||'Please check your details.');error.hidden=false;form.querySelector('input').focus();return;}
      const client=result.client;const option=new Option(client.name,client.id,true,true);document.getElementById('invoice-client').append(option);
      form.closest('dialog').close();form.reset();refreshDirty(invoiceForm);queuePreview();window.toast(t('Client added'));
    }catch{error.textContent=t('Could not save. Please try again.');error.hidden=false;}
    finally{button.disabled=false;}
  });
  updatePreview();
})();
