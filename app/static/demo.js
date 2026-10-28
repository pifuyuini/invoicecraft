/* Static demo: only display preferences persist; all business data stays in this page. */
(() => {
  'use strict';
  const data = JSON.parse(document.getElementById('demo-data').textContent);
  let language = document.documentElement.lang;
  const t = (key, lang = language) => data.catalogs[lang]?.[key] || key;
  const fullApp = () => language === 'en'
    ? 'Available in the full app. This static demo does not save changes.'
    : '此功能需运行完整应用。静态演示不会保存更改。';
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function toast(message) {
    const el = document.createElement('div');
    el.className = 'toast toast-success'; el.setAttribute('role','status'); el.textContent = message;
    document.getElementById('toasts').append(el); setTimeout(() => el.remove(), 6500);
  }
  const invoiceForm = document.getElementById('invoice-form');
  function translateDOM() {
    document.querySelectorAll('[data-i18n]').forEach((el) => { el.textContent = t(el.dataset.i18n); });
    document.querySelectorAll('[data-i18n-placeholder]').forEach((el) => { el.placeholder = t(el.dataset.i18nPlaceholder); });
    document.querySelectorAll('[data-i18n-aria]').forEach((el) => { el.setAttribute('aria-label',t(el.dataset.i18nAria)); });
    document.querySelectorAll('[data-ui-language]').forEach((el) => { el.hidden = el.dataset.uiLanguage !== language; });
  }
  document.querySelectorAll('[data-language-select]').forEach((select) => select.addEventListener('change', () => {
    language = select.value; document.documentElement.lang = language; translateDOM();
    document.querySelectorAll('[data-language-select]').forEach((el) => { el.value = language; });
    if (invoiceForm) updatePreview();
  }));
  const viewport = matchMedia('(max-width: 760px)');
  let navFocus;
  function syncNav() {
    const open = document.body.classList.contains('nav-open');
    const sidebar = document.getElementById('sidebar'); if (sidebar) sidebar.inert = viewport.matches && !open;
    document.querySelector('[data-nav-toggle]')?.setAttribute('aria-expanded',String(open));
    const backdrop = document.querySelector('[data-close-nav]'); if (backdrop) backdrop.hidden = !open;
  }
  viewport.addEventListener('change',syncNav); syncNav();
  document.querySelector('[data-nav-toggle]')?.addEventListener('click',(event) => {
    navFocus = event.currentTarget; document.body.classList.toggle('nav-open'); syncNav();
    if (document.body.classList.contains('nav-open')) document.querySelector('.workspace-nav a')?.focus();
  });
  const closeNav = () => { document.body.classList.remove('nav-open'); syncNav(); navFocus?.focus(); };
  document.querySelector('[data-close-nav]')?.addEventListener('click',closeNav);
  document.addEventListener('keydown',(event) => { if (event.key === 'Escape') closeNav(); });
  document.addEventListener('click',async (event) => {
    const blocked = event.target.closest('[data-demo-disabled]');
    if (blocked) { event.preventDefault(); toast(fullApp()); return; }
    const copy = event.target.closest('[data-demo-copy]');
    if (copy) {
      const url = new URL(copy.dataset.copy, location.origin).href;
      try { await navigator.clipboard.writeText(url); toast(language === 'en' ? 'Static demo link copied' : '已复制静态演示链接'); }
      catch { window.prompt(t('Copy this link:'),url); }
    }
  });
  // method=dialog + disabled submit controls already make writes inert without JS.
  document.querySelectorAll('form').forEach((form) => form.addEventListener('submit',(event) => {
    event.preventDefault();
    if (form.classList.contains('filter-bar')) filterList();
    else toast(fullApp());
  }));
  // Integer decimal arithmetic matches Python Decimal ROUND_HALF_UP per line, then tax.
  function decimal(value, places = 6, maximum = 1000000000000n) {
    const match = /^(\d*)(?:\.(\d*))?(?:e([+-]?\d+))?$/i.exec(String(value).trim());
    if (!match || !(match[1] || match[2])) throw new Error(t('Enter a valid non-negative number.'));
    const exponent = Number(match[3] || 0);
    if (!Number.isSafeInteger(exponent) || Math.abs(exponent) > 30) throw new Error(t('Enter a valid non-negative number.'));
    let n = BigInt(match[1] + (match[2] || ''));
    let scale = (match[2] || '').length - exponent;
    if (scale < 0) { n *= 10n ** BigInt(-scale); scale = 0; }
    if (scale > places) throw new Error(t(places === 4 ? 'Use at most four decimal places.' : 'Use at most six decimal places.'));
    const d = 10n ** BigInt(scale);
    if (n > maximum * d) throw new Error(t('Enter a valid non-negative number.'));
    return {n,d};
  }
  const roundHalfUp = (n,d) => (2n*n+d)/(2n*d);
  const factor = (currency) => currency === 'JPY' ? 1n : 100n;
  function money(minor,currency) {
    const digits = currency === 'JPY' ? 0 : 2;
    let text = minor.toString().padStart(digits+1,'0');
    const head = (digits ? text.slice(0,-digits) : text).replace(/\B(?=(\d{3})+(?!\d))/g,',');
    const tail = digits ? '.'+text.slice(-digits) : '';
    return ({USD:'$',EUR:'€',GBP:'£',CNY:'¥',JPY:'¥'}[currency] || currency+' ')+head+tail;
  }
  function amount(quantity,price,currency) {
    const q = decimal(quantity), p = decimal(price);
    return roundHalfUp(q.n*p.n*factor(currency),q.d*p.d);
  }
  // Exposed only for deterministic arithmetic validation; it never stores business data.
  window.invoicecraftDemoMath = {decimal,amount,money,roundHalfUp};
  function filterList() {
    const form = document.querySelector('.filter-bar'); if (!form) return;
    const fields = new FormData(form), query = String(fields.get('q') || '').toLocaleLowerCase();
    const table = document.querySelector('.invoice-table,.client-table'); if (!table) return;
    const invoiceList = table.classList.contains('invoice-table');
    const params = new URLSearchParams(location.search);
    const status = fields.get('status') || params.get('status') || 'all';
    const rows = [...table.tBodies[0].rows];
    const records = new Map(data.invoices.map((row) => [String(row.id),row]));
    const meta = (row) => records.get(row.querySelector('a')?.pathname.match(/\/invoices\/(\d+)/)?.[1]);
    let visible = 0;
    rows.forEach((row) => {
      const record = invoiceList ? meta(row) : null;
      const matches = row.textContent.toLocaleLowerCase().includes(query)
        && (!invoiceList || status === 'all' || record?.status === status)
        && (!fields.get('currency') || record?.currency === fields.get('currency'))
        && (!fields.get('client_id') || String(record?.clientId) === fields.get('client_id'));
      row.hidden = !matches; if (matches) visible++;
    });
    const sort = fields.get('sort') || 'newest';
    rows.sort((a,b) => {
      if (!invoiceList) return sort === 'name-desc'
        ? b.textContent.localeCompare(a.textContent) : a.textContent.localeCompare(b.textContent);
      const aMeta = meta(a), bMeta = meta(b);
      const key = sort === 'due' ? 'dueDate' : 'issueDate';
      return aMeta[key].localeCompare(bMeta[key])*(sort === 'newest' ? -1 : 1);
    }).forEach((row) => table.tBodies[0].append(row));
    let empty = document.querySelector('.demo-empty');
    if (!empty) { empty = document.createElement('p'); empty.className='demo-empty'; table.parentElement.append(empty); }
    empty.textContent=t('No matches just yet.'); empty.hidden=visible>0;
    const count=document.querySelector('.pagination .muted b'); if(count)count.textContent=String(visible);
    for (const [key,value] of fields) { if (value && value!=='all') params.set(key,value); else params.delete(key); }
    params.delete('page'); history.replaceState(null,'',location.pathname+(params.size?'?'+params:''));
    document.querySelectorAll('.tabs .tab').forEach((tab) => {
      const current=new URL(tab.href).searchParams.get('status')||'all';
      tab.classList.toggle('active',current===status);
    });
  }
  const filterForm = document.querySelector('.filter-bar');
  if (filterForm) {
    const query = new URLSearchParams(location.search);
    if (document.querySelector('.client-table')) {
      const label=document.createElement('label'); const select=document.createElement('select');
      select.name='sort'; select.setAttribute('aria-label',t('Sort'));
      [['name-asc','Name A–Z'],['name-desc','Name Z–A']].forEach(([value,text]) => select.add(new Option(text,value)));
      label.append(select); filterForm.insertBefore(label,filterForm.querySelector('button'));
    }
    query.forEach((value,key) => { const control=filterForm.elements.namedItem(key); if(control)control.value=value; });
    filterForm.addEventListener('input',filterList); filterForm.addEventListener('change',filterList);
    document.querySelectorAll('.tabs .tab').forEach((tab) => tab.addEventListener('click',(event) => {
      event.preventDefault(); filterForm.elements.status.value=new URL(tab.href).searchParams.get('status')||'all'; filterList();
    }));
    filterList();
  }
  if (!invoiceForm) return;
  const items = document.getElementById('items-body');
  const preview = document.getElementById('invoice-preview');
  const previewState = document.getElementById('preview-state');
  const initial = new URLSearchParams(new FormData(invoiceForm)).toString();
  const requestedClient = new URLSearchParams(location.search).get('client_id');
  if (requestedClient && !invoiceForm.elements.invoice_id) invoiceForm.elements.client_id.value=requestedClient;
  const number = invoiceForm.elements.invoice_id
    ? document.querySelector('.editor-heading .eyebrow').textContent : 'DEMO-DRAFT';
  const tr = (key,lang) => esc(t(key,lang));
  function party(p,lang,title) {
    return '<div><h3>'+tr(title,lang)+'</h3><strong>'+esc(p?.name||'—')+'</strong>'
      +(p?.company?'<p>'+esc(p.company)+'</p>':'')+(p?.email?'<p>'+esc(p.email)+'</p>':'')
      +(p?.address?'<p class="preserve-lines">'+esc(p.address)+'</p>':'')+'</div>';
  }
  function updatePreview() {
    const fields = new FormData(invoiceForm), currency=String(fields.get('currency'));
    const lang=String(fields.get('document_language'));
    const descriptions=fields.getAll('description'), quantities=fields.getAll('quantity'), prices=fields.getAll('unit_price');
    const statusKey = new URLSearchParams(fields).toString()===initial ? 'No unsaved changes' : 'Unsaved changes';
    const saveState=invoiceForm.querySelector('[data-save-state]');
    saveState.dataset.i18n=statusKey; saveState.textContent=t(statusKey)+' · '+(language==='en'?'Refresh resets':'刷新还原');
    try {
      if (!fields.get('issue_date')) throw new Error(t('Issue date is required.'));
      if (fields.get('due_date') && fields.get('due_date')<fields.get('issue_date')) throw new Error(t('Due date cannot be before issue date.'));
      const amounts=quantities.map((q,index) => amount(q,prices[index],currency));
      const subtotal=amounts.reduce((sum,value) => sum+value,0n);
      const rate=decimal(fields.get('tax_rate'),4,100n);
      const tax=roundHalfUp(subtotal*rate.n,rate.d*100n);
      const client=data.clients.find((c) => String(c.id)===String(fields.get('client_id')));
      const unit=(value) => {const n=decimal(value);return money(roundHalfUp(n.n*factor(currency),n.d),currency);};
      const rows=descriptions.map((description,index) => '<tr><td class="preserve-lines">'+esc(description||t('Description',lang))+'</td><td>'+esc(quantities[index])+'</td><td>'+esc(unit(prices[index]))+'</td><td>'+esc(money(amounts[index],currency))+'</td></tr>').join('');
      const note=(title,value) => value?'<section class="document-notes"><h3>'+tr(title,lang)+'</h3><p class="preserve-lines">'+esc(value)+'</p></section>':'';
      preview.innerHTML='<article class="invoice-document" lang="'+esc(lang)+'"><header class="document-heading"><div><span class="document-kicker">'+tr('Invoice',lang)+'</span><h2>'+esc(number)+'</h2></div><span class="document-brand">O.</span></header><div class="document-parties">'+party(data.issuer,lang,'From')+party(client,lang,'Bill to')+'</div><div class="document-meta">'
        +[['Issue date',fields.get('issue_date')],['Due date',fields.get('due_date')||'—'],['Currency',currency]].map(([label,value])=>'<div><span>'+tr(label,lang)+'</span><strong>'+esc(value)+'</strong></div>').join('')
        +'</div><table class="document-items"><thead><tr>'+['Description','Qty','Unit price','Amount'].map((key)=>'<th>'+tr(key,lang)+'</th>').join('')+'</tr></thead><tbody>'+rows+'</tbody></table><div class="document-totals"><div><span>'+tr('Subtotal',lang)+'</span><span>'+esc(money(subtotal,currency))+'</span></div><div><span>'+tr('Tax',lang)+' ('+esc(fields.get('tax_rate'))+'%)</span><span>'+esc(money(tax,currency))+'</span></div><div class="document-total"><strong>'+tr('Total',lang)+'</strong><strong>'+esc(money(subtotal+tax,currency))+'<small>'+esc(currency)+'</small></strong></div></div>'+note('Notes',fields.get('notes'))+note('Payment instructions',data.paymentInstructions)+'<footer class="document-footer">'+tr('Thank you for your business.',lang)+'</footer></article>';
      items.querySelectorAll('.row-amount').forEach((el,index) => {el.textContent=money(amounts[index],currency);});
      previewState.textContent=t('Up to date');
    } catch(error) { previewState.textContent=t('Check your details'); preview.innerHTML='<p class="demo-empty" role="status">'+esc(error.message)+'</p>'; }
  }
  function renumber() {
    items.querySelectorAll('[data-item-row]').forEach((row,index) => {
      row.querySelector('.item-number').textContent=String(index+1).padStart(2,'0');
      row.querySelectorAll('[name]').forEach((field) => {
        const key=field.name+'_'+index; field.setAttribute('aria-describedby','error-'+key);
        const error=field.parentElement.querySelector('.field-error'); if(error){error.id='error-'+key;error.dataset.errorFor=key;}
      });
    }); updatePreview();
  }
  invoiceForm.addEventListener('input',updatePreview); invoiceForm.addEventListener('change',updatePreview);
  document.getElementById('add-item').addEventListener('click',() => {
    const row=items.firstElementChild.cloneNode(true);
    row.querySelectorAll('input,textarea').forEach((field) => {field.value=field.name==='quantity'?'1':field.name==='unit_price'?'0':'';});
    row.querySelectorAll('.field-error').forEach((el) => {el.textContent='';});
    items.append(row); renumber(); row.querySelector('textarea').focus();
  });
  items.addEventListener('click',(event) => {
    const button=event.target.closest('.remove-row'); if(!button)return;
    const row=button.closest('[data-item-row]');
    if(items.children.length>1)row.remove();
    else row.querySelectorAll('input,textarea').forEach((field) => {field.value=field.name==='quantity'?'1':field.name==='unit_price'?'0':'';});
    renumber();
  });
  document.querySelectorAll('[data-due-days]').forEach((button) => button.addEventListener('click',() => {
    const issued=invoiceForm.elements.issue_date.value; if(!issued)return;
    const due=new Date(issued+'T12:00:00Z'); due.setUTCDate(due.getUTCDate()+Number(button.dataset.dueDays));
    invoiceForm.elements.due_date.value=due.toISOString().slice(0,10); updatePreview();
  }));
  document.querySelectorAll('[data-editor-tab]').forEach((button) => button.addEventListener('click',() => {
    document.querySelector('[data-editor-view]').dataset.editorView=button.dataset.editorTab;
    document.querySelectorAll('[data-editor-tab]').forEach((el) => {el.classList.toggle('active',el===button);el.setAttribute('aria-pressed',String(el===button));});
  }));
  updatePreview();
})();
