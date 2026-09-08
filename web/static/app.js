'use strict';

const icons = {
  cap: '<path d="m2 9 10-5 10 5-10 5zM6 11v6q6 4 12 0v-6M22 9v7"/>',
  trophy: '<path d="M8 3h8v6a4 4 0 0 1-8 0zM8 5H4v2a4 4 0 0 0 4 4m8-6h4v2a4 4 0 0 1-4 4M12 13v6m-4 2h8m-7-2h6"/>',
  book: '<path d="M12 5c-3-2-7-2-10-1v15c3-1 7-1 10 1 3-2 7-2 10-1V4c-3-1-7-1-10 1zm0 0v15"/>',
  bookmark: '<path d="M6 3h12v18l-6-4-6 4z"/>',
  search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
  pin: '<path d="M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 0 1 14 0z"/><circle cx="12" cy="10" r="2.3"/>',
  arrow: '<path d="M4 12h16m-6-6 6 6-6 6"/>',
  chevron: '<path d="m9 5 7 7-7 7"/>',
  external: '<path d="M14 3h7v7m0-7L11 13m-1-9H4v16h16v-6"/>',
  shield: '<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6zM8 12l3 3 5-6"/>',
  file: '<path d="M14 2H5v20h14V7zm0 0v6h5M8 12h8m-8 4h8"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10h.01"/>',
  spark: '<path d="m12 2 2.5 7.5L22 12l-7.5 2.5L12 22l-2.5-7.5L2 12l7.5-2.5z"/>',
};
const icon = name => `<svg viewBox="0 0 24 24" aria-hidden="true">${icons[name] || icons.book}</svg>`;
const esc = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const normalize = value => String(value ?? '').toLocaleLowerCase('ru').replaceAll('ё', 'е');
const num = value => Number(value).toLocaleString('ru-RU');
const category = {rsosh:'РСОШ', vsosh:'ВсОШ', international:'Международная'};
const abbr = {hse:'ВШЭ', itmo:'ITMO', bmstu:'МГТУ', mipt:'МФТИ', mephi:'МИФИ', mai:'МАИ', msal:'МГЮА'};
const labels = {olympiad_name:'Олимпиада в документе', olympiad_profile:'Профиль олимпиады', olympiad_subject:'Предмет олимпиады', olympiad_level:'Уровень олимпиады', registry_number:'Номер в перечне', document_number:'Номер в документе', confirmation_subjects:'Предметы подтверждения', confirmation_score:'Баллы подтверждения', full_score_subjects:'Предметы для 100 баллов', diplomas:'Диплом', grades:'Классы', benefit:'Формулировка льготы', program_scope:'Область действия', field_codes:'Код направления', olympiad_year:'Учебный год олимпиады', winner:'Победитель', prize_winner:'Призёр'};
let catalog, uni, olymp, fields, programs, units, renderVersion = 0, inputTimer, toastTimer;
let saved;
try { saved = new Set(JSON.parse(localStorage.getItem('olympguide:favorites:v1') || '[]')); } catch { saved = new Set(); }
const params = () => new URLSearchParams(location.search);
const val = key => params().get(key) || '';
const route = () => location.pathname.split('/').filter(Boolean);
const href = (type, id) => `/${type}/${encodeURIComponent(id)}`;
const uniMark = id => `<div class="uni-mark ${esc(id)}" aria-hidden="true">${esc(abbr[id] || id)}</div>`;
const benefits = values => (values || []).map(b => b === 'bvi' ? `<span class="tag bvi">${icon('spark')}БВИ</span>` : '<span class="tag points">100 баллов</span>').join('');
const bookmark = (type, id, name) => `<button class="favorite ${saved.has(`${type}:${id}`) ? 'selected' : ''}" data-favorite="${esc(type+':'+id)}" aria-label="В избранное: ${esc(name)}" aria-pressed="${saved.has(`${type}:${id}`)}" title="Сохранить в избранное">${icon('bookmark')}</button>`;
const note = text => `<div class="note">${icon('info')}<div>${text}</div></div>`;
const safeUrl = url => { try { const parsed = new URL(url, location.origin); return ['https:', 'http:'].includes(parsed.protocol) ? esc(parsed.href) : '#'; } catch { return '#'; } };
const external = (url, text) => `<a href="${safeUrl(url)}" target="_blank" rel="noopener noreferrer">${esc(text)} ${icon('external')}</a>`;
const empty = (title='Ничего не найдено', text='Попробуйте изменить запрос или сбросить фильтры.') => `<div class="empty">${icon('search')}<h3>${esc(title)}</h3><p>${esc(text)}</p><button class="button" data-reset>Сбросить фильтры</button></div>`;
const search = (placeholder='Поиск по названию', key='q') => `<label class="searchbox">${icon('search')}<input type="search" data-query="${key}" value="${esc(val(key))}" placeholder="${esc(placeholder)}" aria-label="${esc(placeholder)}" autocomplete="off"></label>`;
function select(key, title, options) {
  return `<select data-filter="${esc(key)}" aria-label="${esc(title)}"><option value="">${esc(title)}</option>${options.map(o => { const [value, label] = Array.isArray(o) ? o : [o, o]; return `<option value="${esc(value)}" ${val(key) === String(value) ? 'selected' : ''}>${esc(label)}</option>`; }).join('')}</select>`;
}
const benefitSelect = () => select('benefit', 'Все льготы', [['bvi','Без вступительных испытаний'],['100_points','100 баллов за предмет']]);
const universitySelect = ids => select('university', 'Все вузы', catalog.universities.filter(u => !ids || ids.includes(u.id)).map(u => [u.id,u.short_name]));
const categorySelect = () => select('category','Все категории',Object.entries(category));
function matches(text) { return normalize(val('q')).split(/\s+/).filter(Boolean).every(word => normalize(text).includes(word)); }
function entityMatches(entity, type) {
  const allowed = val('university') ? entity.university_benefits[val('university')] || [] : entity.benefit_types;
  return (!val('benefit') || allowed.includes(val('benefit'))) && (!val('university') || entity.university_ids.includes(val('university'))) && (!val('saved') || saved.has(`${type}:${entity.id}`));
}
const favToggle = () => `<button class="toggle ${val('saved') ? 'selected' : ''}" data-toggle-saved aria-pressed="${!!val('saved')}">${icon('bookmark')}Избранное</button>`;
function paginate(items, renderer, className='grid') {
  const page = Math.min(Math.max(1, Number(val('page')) || 1), Math.max(1, Math.ceil(items.length / 24)));
  return items.length ? `<div class="${className}">${items.slice((page-1)*24,page*24).map(renderer).join('')}</div>${pagination(items.length, page)}` : empty();
}
function pagination(total, page, size=24) {
  const pages = Math.ceil(total / size);
  return pages > 1 ? `<div class="pagination"><button class="button" data-page="${page-1}" ${page <= 1 ? 'disabled' : ''}>← Назад</button><span>${page} / ${pages} · ${num(total)} записей</span><button class="button" data-page="${page+1}" ${page >= pages ? 'disabled' : ''}>Далее →</button></div>` : '';
}
function heading(title, count, right='') { return `<div class="results-heading"><strong>${title}<span class="count">${num(count)}</span></strong>${right}</div>`; }
function intro(title, subtitle, graphic='cap') { return `<div class="intro"><div class="intro-copy"><div class="eyebrow">${icon('spark')}Твой путь в университет</div><h1>${esc(title)}</h1><p class="subtitle">${esc(subtitle)}</p></div><div class="intro-icon">${icon(graphic)}</div></div>`; }
function crumbs(parts) { return `<nav class="breadcrumbs" aria-label="Хлебные крошки">${parts.map(([title,url]) => url ? `<a href="${url}">${esc(title)}</a>` : `<span>${esc(title)}</span>`).join(icon('chevron'))}</nav>`; }
function tabs(options, current) { return `<nav class="tabs">${options.map(([id,title,count]) => { const p=params();p.set('tab',id);['page','q','benefit','category','profile','level'].forEach(k=>p.delete(k));return `<a class="tab ${current===id?'active':''}" href="${location.pathname}?${esc(p.toString())}">${title}${count===undefined?'':`<span>${num(count)}</span>`}</a>`; }).join('')}</nav>`; }
function shell() {
  document.querySelector('#app').innerHTML = `<aside class="sidebar"><a href="/universities" class="brand"><img src="/favicon.svg" alt=""><span>ОлимпГид<span class="brand-dot">.</span></span></a><div class="brand-sub">Поступление через олимпиады</div><div class="nav-title">НАВИГАЦИЯ</div><nav class="nav" aria-label="Основная навигация">${[['universities','cap','Вузы'],['olympiads','trophy','Олимпиады'],['fields','book','Направления'],['favorites','bookmark','Избранное']].map(([path,ico,title])=>`<a href="/${path}" data-nav="${path}">${icon(ico)}<span>${title}</span>${path==='favorites'?`<span class="nav-count" id="favorite-count">${saved.size}</span>`:''}</a>`).join('')}</nav><div class="side-bottom"><div class="side-note"><strong>${icon('shield')} Приёмная кампания ${catalog.admission_year}</strong>Условия льгот из официальных документов вузов.</div><div class="side-foot"><span class="status-dot"></span>Данные от ${new Date(catalog.collected_on+'T00:00:00').toLocaleDateString('ru-RU')}</div></div></aside><div class="workspace"><header class="topbar"><span class="topbar-label">Возможности для олимпиадников</span><div class="top-actions"><span class="year-label">Приём ${catalog.admission_year}</span><span class="avatar" title="Локальный просмотр">ОГ</span></div></header><main id="main" class="main" tabindex="-1"></main></div>`;
}
function stats() { return `<div class="stats">${[['cap',catalog.universities.length,'вузов в каталоге'],['trophy',catalog.olympiads.length,'названий олимпиад'],['shield',catalog.rule_count,'записей об условиях льгот'],['file',catalog.source_count,'официальных источника']].map(([i,n,t])=>`<div class="stat"><div class="stat-icon">${icon(i)}</div><div><div class="stat-value">${num(n)}</div><div class="stat-label">${t}</div></div></div>`).join('')}</div>`; }
function universityCard(u) { return `<article class="card"><div class="card-top">${uniMark(u.id)}${bookmark('universities',u.id,u.short_name)}</div><h3 class="card-name"><a href="${href('universities',u.id)}">${esc(u.short_name)}</a></h3><p class="card-description">${esc(u.name)}</p><div class="location">${icon('pin')}${esc(u.city)}</div><div class="tags">${benefits(u.benefit_types)}</div><div class="card-footer"><span><strong>${num(u.rule_count)}</strong> условий льгот</span><a class="arrow-link" href="${href('universities',u.id)}">Подробнее ${icon('arrow')}</a></div></article>`; }
function olympiadCard(o) { return `<article class="card"><div class="card-top"><div class="olymp-mark">${icon('trophy')}</div>${bookmark('olympiads',o.id,o.name)}</div><h3><a href="${href('olympiads',o.id)}">${esc(o.name)}</a></h3><p class="card-description">${esc(o.profiles.slice(0,3).join(' · '))}${o.profiles.length>3 ? ` · ещё ${o.profiles.length-3}` : ''}</p><div class="tags"><span class="tag">${category[o.category]}</span>${benefits(o.benefit_types)}</div><div class="card-footer"><span>Вузов с условиями: <strong>${o.university_ids.length}</strong></span><a class="arrow-link" href="${href('olympiads',o.id)}">Льготы ${icon('arrow')}</a></div></article>`; }
function fieldCard(f) { return `<article class="card field-card"><span class="code">${esc(f.code)}</span><h3><a href="${href('fields',f.id)}">${esc(f.name)}</a></h3><div class="field-group">${esc(f.degree)} · ${esc(f.group)}</div><div class="card-footer"><span>Вузов в данных: <strong>${f.university_ids.length}</strong></span><a href="${href('fields',f.id)}" class="arrow-link">Смотреть ${icon('arrow')}</a></div></article>`; }
function programRow(p) {
  const u=uni[p.university_id],context=route()[0]==='units'?route()[1]:val('unit');
  const url=href('programs',p.id)+(context&&[...p.unit_ids,...p.department_ids].includes(context)?'?unit='+encodeURIComponent(context):'');
  return `<article class="program-row">${p.field_id?`<span class="code">${esc(p.field_id)}</span>`:`<div class="olymp-mark">${icon('book')}</div>`}<div class="program-copy"><h3><a href="${url}">${esc(p.name)}</a></h3><div class="program-meta"><a href="${href('universities',u.id)}">${esc(u.short_name)}</a><span>·</span><span>${p.kind==='group'?'Группа / общие условия':p.directory_kind==='field'?'Направление подготовки':'Образовательная программа'}</span><span>·</span><span>${num(p.rule_count)} условий${p.school?' школы':''}</span></div>${p.unit_ids.length?`<div class="program-units">${p.unit_ids.map(id=>`<a href="${href('units',id)}">${esc(units[id].code||units[id].name)}</a>`).join('')}</div>`:''}${p.competition_group?`<div class="hint">Конкурсная группа: ${esc(p.competition_group)}</div>`:''}</div><div class="tags">${p.school?'<span class="tag">Условия школы</span>':benefits(p.benefit_types)}</div>${bookmark('programs',p.id,p.name)}<a href="${url}" class="arrow-link" aria-label="Открыть ${esc(p.name)}">${icon('arrow')}</a></article>`;
}
function directory(type) {
  if (type==='universities') {
    const list=catalog.universities.filter(u=>matches(u.name+' '+u.short_name+' '+u.city)&&entityMatches(u,type)&&(!val('city')||val('city')===u.city));
    return intro('Вузы, где ценят твои победы','Найди университет и узнай, какие олимпиады дают БВИ или 100 баллов за вступительное испытание.')+stats()+`<div class="toolbar">${search('Название вуза или город')}${select('city','Все города',[...new Set(catalog.universities.map(u=>u.city))])}${benefitSelect()}${favToggle()}</div>`+heading('Университеты',list.length,`<span>Условия приёма ${catalog.admission_year}</span>`)+paginate(list,universityCard)+note('БВИ — поступление без вступительных испытаний. 100 баллов — максимальный результат за указанный предмет. Подтверждение и ограничения смотрите в условиях конкретной льготы.');
  }
  if (type==='olympiads') {
    let list=catalog.olympiads.filter(o=>matches([o.name,...o.profiles,...o.aliases].join(' '))&&entityMatches(o,type)&&(!val('category')||o.category===val('category')));
    if(val('sort')==='universities')list.sort((a,b)=>b.university_ids.length-a.university_ids.length);
    return intro('Олимпиады открывают двери','Найди свою олимпиаду, выбери профиль и посмотри условия льгот в университетах.','trophy')+`<div class="toolbar">${search('Олимпиада или профиль, например «математика»')}${universitySelect()}${benefitSelect()}${categorySelect()}${favToggle()}${select('sort','По названию',[['universities','По числу вузов']])}</div>`+heading('Олимпиады',list.length)+paginate(list,olympiadCard,'grid directory-olymp')+note('Названия и профили взяты из документов вузов. Разные формулировки названия могут отображаться отдельно; точное написание сохранено в каждой записи.');
  }
  const list=catalog.fields.filter(f=>matches(f.name+' '+f.code+' '+f.group)&&entityMatches(f,type)&&(!val('degree')||f.degree===val('degree')));
  return intro('Выбери своё направление','Сравни направления подготовки и открой программы с условиями приёма по олимпиадам.','book')+`<div class="toolbar">${search('Название или код направления')}${universitySelect()}${select('degree','Любой уровень',[...new Set(catalog.fields.map(f=>f.degree))])}${benefitSelect()}</div>`+heading('Направления в каталоге',list.length)+paginate(list,fieldCard)+note('Здесь собраны направления из официальных каталогов программ и условий льгот. Распределение по факультетам, институтам и школам доступно на страницах вузов.');
}
function hero({title, subtitle, uid, type, id, meta='', graphic='book'}) { return `<section class="detail-hero">${uid?uniMark(uid):`<div class="uni-mark">${icon(graphic)}</div>`}<div class="hero-copy"><h1>${esc(title)}</h1><p class="subtitle">${esc(subtitle)}</p><div class="hero-meta">${meta}</div></div>${type?bookmark(type,id,title):''}</section>`; }
function programSection(list, groupNote=true) {
  const filtered=list.filter(p=>!p.aggregate&&matches([p.name,p.field_id,p.school,p.competition_group,...(p.unit_ids||[]).map(id=>units[id]?.name)].join(' '))&&entityMatches(p,'programs')&&(!val('unit')||[...p.unit_ids,...p.department_ids].includes(val('unit'))));
  const concrete=filtered.filter(p=>p.kind!=='group'), groups=filtered.filter(p=>p.kind==='group');
  return `<div class="toolbar">${search('Найти направление или программу')}${benefitSelect()}${favToggle()}</div>`+heading('Направления и программы',concrete.length)+(concrete.length?paginate(concrete,programRow,'program-list'):!groups.length?empty():'')+(groups.length?`<h2 class="group-title">Группы направлений и общие условия <span class="count">${groups.length}</span></h2>${groupNote?note('Эти правила заданы для группы программ, физтех-школы или содержат исключения. Откройте группу, чтобы увидеть полную область действия.'):''}<div class="program-list space-top">${groups.map(programRow).join('')}</div>`:'');
}
function universityPage(u) {
  const tab=val('tab')||(u.unit_count?'units':'programs');
  const list=catalog.programs.filter(p=>p.university_id===u.id);
  let content=crumbs([['Вузы','/universities'],[u.short_name]])+hero({title:u.short_name,subtitle:u.name,uid:u.id,type:'universities',id:u.id,meta:`<span class="location">${icon('pin')}${esc(u.city)}</span>${external(u.site,'Сайт вуза')}<span>${num(u.rule_count)} условий льгот</span><span>${u.unit_count} подразделений · ${u.field_count} направлений</span><div class="tags">${benefits(u.benefit_types)}</div>`})+tabs([['units','Подразделения',u.unit_count],['programs','Все программы',u.program_count],['rules','Льготы',u.rule_count],['about','О данных']],tab);
  if(tab==='rules')content+=ruleSection({university:u.id});
  else if(tab==='about')content+=`<section class="rule source-summary"><h2>Что есть в каталоге</h2><p><strong>Охват:</strong> ${esc(u.scope)}</p><p><strong>Год приёма:</strong> ${catalog.admission_year}<br><strong>Дата сбора:</strong> ${esc(catalog.collected_on)}<br><strong>Условий льгот:</strong> ${num(u.rule_count)}<br><strong>Названий олимпиад:</strong> ${u.olympiad_ids.length}</p><p>У каждой записи есть ссылка на документ вуза и сохранённую копию с номером страницы. Стоимость обучения и число мест в этот набор данных не входят.</p><a class="button primary" href="${href('universities',u.id)}?tab=rules">Смотреть условия ${icon('arrow')}</a></section>`;
  else if(tab==='units')content+=unitDirectory(u,list);
  else content+=programSection(list);
  return content;
}

function unitSummary(t) {
  const onlyFields=t.program_ids.every(id=>programs[id].directory_kind==='field');
  return `Направлений: ${t.field_ids.length}${onlyFields?'':` · Программ / профилей: ${t.program_count}`}`;
}
function unitCard(t) {
  return `<article class="card unit-card"><div class="unit-kicker">${esc(t.type)}${t.code?` · ${esc(t.code)}`:''}</div><h3><a href="${href('units',t.id)}">${esc(t.name)}</a></h3><p class="hint">${t.field_ids.map(id=>esc(id)).slice(0,6).join(' · ')}${t.field_ids.length>6?' · …':''}</p><div class="card-footer"><span>${unitSummary(t)}</span><a class="arrow-link" href="${href('units',t.id)}">${icon('arrow')}</a></div></article>`;
}
function unitDirectory(u,list) {
  const visible=catalog.units.filter(t=>t.university_id===u.id&&!t.parent_id&&matches([t.name,t.code,...t.program_ids.map(id=>`${programs[id].name} ${programs[id].field_id}`)].join(' '))&&entityMatches(t,'units'));
  const unassigned=list.filter(p=>p.kind!=='group'&&!p.aggregate&&!p.unit_ids.length);
  return `<div class="toolbar">${search('Факультет, институт, школа или направление')}${benefitSelect()}</div>`+heading('Факультеты, институты и школы',visible.length)+paginate(visible,unitCard,'grid unit-grid')+
    (unassigned.length?note(`Для ${unassigned.length} записей из условий льгот подразделение не указано в собранном каталоге. Они доступны во вкладке «Все программы».`):'')+
    note('Открой подразделение, чтобы увидеть его направления и программы. Совместные программы доступны в каждом указанном вузом подразделении.');
}
function unitPage(t) {
  const u=uni[t.university_id],parent=units[t.parent_id],tab=val('tab')||'programs';
  const list=t.program_ids.map(id=>programs[id]);
  let content=crumbs([['Вузы','/universities'],[u.short_name,href('universities',u.id)],...(parent?[[parent.code||parent.name,href('units',parent.id)]]:[]),[t.code||t.name]])+
    hero({title:t.name,subtitle:u.name,uid:u.id,meta:`${t.code?`<span class="code">${esc(t.code)}</span>`:''}<span>${unitSummary(t)}</span>${external(t.url,'Официальный источник')}`})+
    tabs([['programs','Направления',t.field_ids.length],['rules','Льготы',t.rule_count],...(t.child_ids.length?[['departments','Кафедры',t.child_ids.length]]:[])],tab);
  if(tab==='rules')return content+ruleSection({university:u.id,unit:t.id});
  if(tab==='departments')return content+`<div class="grid unit-grid">${t.child_ids.map(id=>unitCard(units[id])).join('')}</div>`;
  const filtered=list.filter(p=>matches(`${p.name} ${p.field_id} ${fields[p.field_id]?.name}`)&&entityMatches(p,'programs'));
  const codes=[...new Set(filtered.map(p=>p.field_id))].sort();
  content+=`<div class="toolbar">${search('Название направления или программы')}${benefitSelect()}</div>`+heading('Направления подготовки',codes.length);
  content+=codes.length?`<div class="field-tree">${codes.map(code=>{
    const f=fields[code],ps=filtered.filter(p=>p.field_id===code);
    return `<section class="field-branch"><div class="field-branch-heading"><span class="code">${esc(code)}</span><div><h2><a href="${href('fields',code)}?unit=${encodeURIComponent(t.id)}">${esc(f.name)}</a></h2><p>${esc(f.degree)}${ps.every(p=>p.directory_kind==='field')?'':` · Программ / профилей: ${ps.length}`}</p></div><a class="arrow-link" aria-label="Открыть направление ${esc(code)}" href="${href('fields',code)}?unit=${encodeURIComponent(t.id)}">${icon('arrow')}</a></div><div class="program-list">${ps.map(programRow).join('')}</div></section>`;
  }).join('')}</div>`:empty();
  return content+`<div class="rule-source space-top">${t.source_ids.map(id=>`<a href="/sources/${esc(id)}" target="_blank" rel="noopener">${icon('file')}Сохранённый источник структуры</a>`).join('')}</div>`;
}

function affiliationSection(p) {
  if(p.affiliation_status==='not_in_directory')return note('Направление упомянуто в условиях льгот, но отсутствует в собранном каталоге программ 2026. Подразделение не подтверждено; наличие этой записи не подтверждает набор на направление.');
  if(!p.unit_ids.length)return '';
  return `<section class="rule affiliation-section"><h2>Где проходит обучение</h2><div class="affiliation-links">${p.unit_ids.map(id=>`<a class="button" href="${href('units',id)}">${esc(units[id].name)} ${icon('arrow')}</a>`).join('')}</div>${p.department_ids.length?`<p class="hint">Кафедры</p><div class="rule-links">${p.department_ids.map(id=>`<a href="${href('units',id)}">${esc(units[id].code)} · ${esc(units[id].name)}</a>`).join('')}</div>`:p.department_label?`<p class="hint">${esc(p.department_label)}</p>`:''}${p.tracks?.length?`<h3 class="space-top">Образовательные траектории</h3><ul class="track-list">${p.tracks.map(name=>`<li>${esc(name)}</li>`).join('')}</ul>`:''}<div class="rule-source">${external(p.program_url||p.source_url,p.program_url?'Программа на сайте вуза':'Официальный перечень программ')}${[...new Set((p.affiliations||[]).map(a=>a.source_id))].map(id=>`<a href="/sources/${esc(id)}" target="_blank" rel="noopener">${icon('file')}Источник распределения</a>`).join('')}</div></section>`;
}
function olympiadPage(o) {
  return crumbs([['Олимпиады','/olympiads'],[o.name]])+hero({title:o.name,subtitle:`${category[o.category]} · ${o.profiles.length} профилей в документах вузов`,type:'olympiads',id:o.id,graphic:'trophy',meta:`<span>Вузов с условиями: ${o.university_ids.length}</span><span>${num(o.rule_count)} записей</span><div class="tags">${benefits(o.benefit_types)}</div>`})+`<h2>Где пригодится твой диплом</h2>`+ruleSection({olympiad:o.id},o);
}
function fieldPage(f) {
  const t=units[val('unit')],u=t?uni[t.university_id]:null;
  const list=catalog.programs.filter(p=>p.field_id===f.id&&!p.aggregate&&(!t||[...p.unit_ids,...p.department_ids].includes(t.id))),tab=val('tab')||'programs';
  return crumbs(t?[['Вузы','/universities'],[u.short_name,href('universities',u.id)],[t.code||t.name,href('units',t.id)],[f.code]]:[['Направления','/fields'],[f.code]])+hero({title:f.name,subtitle:t?t.name:f.group,meta:`<span class="code">${esc(f.code)}</span><span>${esc(f.degree)}</span><span>${f.university_ids.length} вузов в данных</span>`})+tabs([['programs','Программы и вузы',list.length],['rules','Условия льгот',t?t.field_rule_counts[f.id]||0:f.rule_count]],tab)+(tab==='rules'?ruleSection({field:f.id,...(t?{unit:t.id,university:u.id}:{})}):programSection(list))+note('Программы связаны с явно указанными направлениями. Для МФТИ показаны условия соответствующей физтех-школы: применимость к конкурсной группе уточняется в формулировке льготы. Общие правила с исключениями доступны на страницах вузов.');
}
function programPage(p) {
  const u=uni[p.university_id],f=fields[p.field_id];
  const context=units[val('unit')]&&[...p.unit_ids,...p.department_ids].includes(val('unit'))?units[val('unit')]:units[p.unit_ids[0]];
  const trail=context?[[context.code||context.name,href('units',context.id)],[p.field_id,href('fields',p.field_id)+'?unit='+encodeURIComponent(context.id)]]:[];
  if(p.rule_relation==='school_conditions') {
    const general=catalog.programs.find(x=>x.university_id===u.id&&x.kind==='group'&&x.name==='Конкурсные группы МФТИ; см. условия');
    return crumbs([['Вузы','/universities'],[u.short_name,href('universities',u.id)],...trail,[p.name]])+hero({title:p.name,subtitle:u.name,uid:u.id,type:'programs',id:p.id,meta:`<a href="${href('universities',u.id)}">${esc(u.short_name)}</a><a class="code" href="${href('fields',f.id)}">${esc(f.code)}</a><span>${esc(p.education_level)}</span><span>${esc(p.school)}</span>`})+affiliationSection(p)+`<section class="rule"><dl class="rule-facts"><div><dt>Направление</dt><dd>${esc(p.field_name)}</dd></div><div><dt>Физтех-школа</dt><dd>${esc(p.school)}</dd></div><div><dt>Конкурсная группа</dt><dd>${esc(p.competition_group)}</dd></div></dl><div class="rule-source">${external(p.source_url,'Официальный перечень программ')}<a href="/sources/${esc(p.source_id)}" target="_blank" rel="noopener">Сохранённая копия перечня</a></div></section>`+note(`Ниже — условия физтех-школы ${esc(p.school)}. Если в формулировке перечислены отдельные конкурсные группы, сверьте их с группой этой программы. ${general?`<a href="${href('programs',general.id)}">Общие условия МФТИ для 100 баллов</a>.`:''}`)+`<h2 class="space-top">Условия физтех-школы</h2>`+ruleSection({program:p.id});
  }
  return crumbs([['Вузы','/universities'],[u.short_name,href('universities',u.id)],...trail,[p.kind==='group'?'Группа направлений':p.name]])+hero({title:p.name,subtitle:u.name,uid:u.id,type:'programs',id:p.id,meta:`<a href="${href('universities',u.id)}">${esc(u.short_name)}</a>${f?`<a class="code" href="${href('fields',f.id)}">${esc(f.code)} · ${esc(p.education_level||f.degree)}</a>`:'<span>Группа / общие условия</span>'}<span>${num(p.rule_count)} записей</span>`})+affiliationSection(p)+(p.kind==='group'?note('Область действия этой группы сохранена в формулировке вуза. У отдельных льгот могут быть дополнительные ограничения.'):note('Здесь показаны условия для этой программы или явного перечня направлений. Дополнительные общие правила доступны на странице вуза.'))+`<h2 class="space-top">Олимпиады и льготы</h2>`+ruleSection({program:p.id});
}
let pendingRuleParams=null;
function ruleSection(base, o=null) {
  pendingRuleParams=base;
  return `<div class="toolbar rule-filter">${search('Поиск по профилю, диплому или условиям')}${!base.university&&!base.program?universitySelect(o?.university_ids):''}${benefitSelect()}${o?select('profile','Все профили',o.profiles):categorySelect()}${o?.levels.length?select('level','Любой уровень олимпиады',o.levels):''}</div><div id="rule-results" aria-live="polite" aria-busy="true"><div class="loading">Загружаем условия…</div></div>`;
}
function ruleCard(r) {
  const v=r.values,u=uni[r.university_id];
  const facts=['olympiad_profile','diplomas','grades','confirmation_subjects','confirmation_score','full_score_subjects','olympiad_level','olympiad_year','winner','prize_winner'].filter(k=>v[k]);
  const where=Object.entries(r.location).map(([k,value])=>`${({page:'стр.',table:'таблица',row:'строка',column:'столбец',section:'раздел',paragraph:'пункт'})[k]||k} ${value}`).join(' · ');
  const plinks=r.program_ids.slice(0,4).map(id=>{const p=programs[id];return `<a href="${href('programs',id)}">${esc(p.kind==='group'?'Открыть группу':p.field_id+' · '+p.name)}</a>`;}).join('');
  const related=(r.related_program_ids||[]).slice(0,4).map(id=>`<a href="${href('programs',id)}">${esc(programs[id].field_id+' · '+programs[id].name)}</a>`).join('');
  return `<article class="rule"><div class="rule-header"><h3><a href="${href('olympiads',r.olympiad_id)}">${esc(v.olympiad_name)}</a></h3><div class="tags">${benefits(r.benefit_types)}</div></div><p class="rule-subtitle"><a href="${href('universities',u.id)}">${esc(u.short_name)}</a> · ${esc(category[r.category])} · Приём ${r.admission_year}</p><div class="rule-scope"><strong>Где действует условие</strong>${esc(v.program_scope)}<div class="rule-links">${plinks}${r.program_ids.length>4?`<a href="${href('universities',u.id)}">Ещё направлений: ${r.program_ids.length-4}</a>`:''}</div>${related?`<strong class="space-top">${u.id==='mipt'?'Программы этой физтех-школы':'Программы указанных направлений'}</strong><div class="rule-links">${related}</div>`:""}</div>${u.id==="mipt"?`<p class="school-benefit">${esc(v.benefit)}</p>`:""}<dl class="rule-facts">${facts.map(k=>`<div><dt>${esc(labels[k])}</dt><dd>${esc(v[k])}</dd></div>`).join('')}</dl><details><summary>Полная формулировка и дополнительные условия</summary>${Object.entries(v).map(([k,value])=>`<p><strong>${esc(labels[k]||k)}:</strong> ${esc(value)}</p>`).join('')}${r.conditions.length?`<ul>${r.conditions.map(c=>`<li>${esc(c)}</li>`).join('')}</ul>`:''}</details><div class="rule-source">${external(r.source_url,'Документ вуза')}<a href="${esc(r.source.local_url)}" target="_blank" rel="noopener">${icon('file')}Сохранённая копия</a><span>${esc(where)}</span></div></article>`;
}
async function renderRules(base, version) {
  const p=params();['tab','saved','page'].forEach(k=>p.delete(k));Object.entries(base).forEach(([k,v])=>p.set(k,v));
  const page=Math.max(1,Number(val('page'))||1);p.set('offset',(page-1)*24);p.set('limit',24);
  try {
    const response=await fetch('/api/rules?'+p);if(!response.ok)throw new Error('Не удалось загрузить условия');const data=await response.json();
    if(version!==renderVersion)return;
    const area=document.querySelector('#rule-results');
    area.setAttribute('aria-busy','false');
    area.innerHTML=heading('Условия льгот',data.total,`<button class="text-button" data-reset>Сбросить фильтры</button>`)+(data.items.length?`<div class="rules">${data.items.map(ruleCard).join('')}</div>${pagination(data.total,page)}`:empty())+note('Запись описывает условие из документа, а не гарантированное поступление. Проверьте профиль, диплом, класс, подтверждающий предмет и дополнительные условия.');
  } catch(error) {if(version===renderVersion){const area=document.querySelector('#rule-results');area.setAttribute('aria-busy','false');area.innerHTML=empty('Не удалось загрузить условия','Проверьте, что локальный сервер запущен, и обновите страницу.');}}
}
function favoritesPage() {
  const us=catalog.universities.filter(u=>saved.has('universities:'+u.id)),os=catalog.olympiads.filter(o=>saved.has('olympiads:'+o.id)),ps=catalog.programs.filter(p=>saved.has('programs:'+p.id));
  return intro('Твои ориентиры','Сохраняй вузы, олимпиады и программы, чтобы быстро вернуться к ним. Избранное хранится в этом браузере.','bookmark')+(us.length+os.length+ps.length ? (us.length?heading('Вузы',us.length)+`<div class="grid">${us.map(universityCard).join('')}</div>`:'')+(os.length?heading('Олимпиады',os.length)+`<div class="grid directory-olymp">${os.map(olympiadCard).join('')}</div>`:'')+(ps.length?heading('Направления и программы',ps.length)+`<div class="program-list">${ps.map(programRow).join('')}</div>`:''):`<div class="empty">${icon('bookmark')}<h3>Здесь будет твой список</h3><p>Нажми на закладку рядом с вузом, олимпиадой или программой.</p><a class="button primary" href="/universities">Выбрать вуз ${icon('arrow')}</a></div>`);
}
function render() {
  const version=++renderVersion;pendingRuleParams=null;
  const focus=document.activeElement?.dataset.query;const start=document.activeElement?.selectionStart;
  const [type='universities',id]=route();let content,title;
  document.querySelectorAll('[data-nav]').forEach(a=>{const active=a.dataset.nav===(type==='programs'?'fields':type==='units'?'universities':type);a.classList.toggle('active',active);active?a.setAttribute('aria-current','page'):a.removeAttribute('aria-current');});
  if(!id&&['universities','olympiads','fields'].includes(type)){content=directory(type);title={universities:'Вузы',olympiads:'Олимпиады',fields:'Направления'}[type];}
  else if(type==='universities'&&uni[id]){content=universityPage(uni[id]);title=uni[id].short_name;}
  else if(type==='units'&&units[id]){content=unitPage(units[id]);title=units[id].name;}
  else if(type==='olympiads'&&olymp[id]){content=olympiadPage(olymp[id]);title=olymp[id].name;}
  else if(type==='fields'&&fields[id]){content=fieldPage(fields[id]);title=fields[id].name;}
  else if(type==='programs'&&programs[id]){content=programPage(programs[id]);title=programs[id].name;}
  else if(type==='favorites'&&!id){content=favoritesPage();title='Избранное';}
  else {content=`<div class="empty"><h1>Страница не найдена</h1><p>Возможно, ссылка относится к другому набору данных.</p><a href="/universities" class="button primary">К вузам</a></div>`;title='Страница не найдена';}
  document.title=title+' — ОлимпГид';
  document.querySelector('#main').innerHTML=content+`<footer class="footer"><span>ОлимпГид · Возможности для олимпиадников</span><span>Приём ${catalog.admission_year} · Данные собраны ${new Date(catalog.collected_on+'T00:00:00').toLocaleDateString('ru-RU')}</span></footer>`;
  if(focus){const input=document.querySelector(`[data-query="${focus}"]`);if(input){input.focus({preventScroll:true});try{input.setSelectionRange(start,start);}catch{}}}
  if(pendingRuleParams)renderRules(pendingRuleParams,version);
}
function navigate(url,replace=false,scroll=true) {clearTimeout(inputTimer);history[replace?'replaceState':'pushState']({},'',url);render();if(scroll)window.scrollTo({top:0,behavior:'instant'});}
function setFilter(key,value,replace=false) {const p=params();value?p.set(key,value):p.delete(key);if(key!=='page')p.delete('page');navigate(location.pathname+(p.size?'?'+p:''),replace,key==='page');}
function toast(message){const el=document.querySelector('#toast');el.textContent=message;el.classList.add('visible');clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.classList.remove('visible'),2300);}
document.addEventListener('click',e=>{
  const favorite=e.target.closest('[data-favorite]');if(favorite){const key=favorite.dataset.favorite;saved.has(key)?saved.delete(key):saved.add(key);try{localStorage.setItem('olympguide:favorites:v1',JSON.stringify([...saved]));toast(saved.has(key)?'Сохранено в избранном':'Удалено из избранного');}catch{toast('Сохранено на время просмотра: хранилище браузера недоступно');}document.querySelector('#favorite-count').textContent=saved.size;if(route()[0]==='favorites'||val('saved'))render();else document.querySelectorAll('[data-favorite]').forEach(b=>{b.classList.toggle('selected',saved.has(b.dataset.favorite));b.setAttribute('aria-pressed',saved.has(b.dataset.favorite));});return;}
  const toggle=e.target.closest('[data-toggle-saved]');if(toggle){setFilter('saved',val('saved')?'':'1');return;}
  const page=e.target.closest('[data-page]');if(page&&!page.disabled){setFilter('page',page.dataset.page);return;}
  if(e.target.closest('[data-reset]')){const p=new URLSearchParams();if(val('tab'))p.set('tab',val('tab'));if(val('unit')&&['fields','programs'].includes(route()[0]))p.set('unit',val('unit'));navigate(location.pathname+(p.size?'?'+p:''),false,false);return;}
  const a=e.target.closest('a');if(a&&!e.defaultPrevented&&e.button===0&&!e.metaKey&&!e.ctrlKey&&!e.shiftKey&&!e.altKey&&!a.target&&!a.hasAttribute('download')){const url=new URL(a.href);if(url.origin===location.origin&&!url.pathname.startsWith('/sources/')&&!a.classList.contains('skip')){e.preventDefault();navigate(url.pathname+url.search);}}
});
document.addEventListener('change',e=>{if(e.target.dataset.filter)setFilter(e.target.dataset.filter,e.target.value);});
document.addEventListener('input',e=>{if(e.target.dataset.query){clearTimeout(inputTimer);const key=e.target.dataset.query,value=e.target.value;inputTimer=setTimeout(()=>setFilter(key,value,true),230);}});
window.addEventListener('popstate',()=>{clearTimeout(inputTimer);render();});
window.addEventListener('storage',e=>{if(e.key==='olympguide:favorites:v1'){try{saved=new Set(JSON.parse(e.newValue||'[]'));document.querySelector('#favorite-count').textContent=saved.size;render();}catch{}}});
(async()=>{try{const response=await fetch('/api/catalog');if(!response.ok)throw new Error('Catalog unavailable');catalog=await response.json();uni=Object.fromEntries(catalog.universities.map(u=>[u.id,u]));olymp=Object.fromEntries(catalog.olympiads.map(o=>[o.id,o]));fields=Object.fromEntries(catalog.fields.map(f=>[f.id,f]));programs=Object.fromEntries(catalog.programs.map(p=>[p.id,p]));units=Object.fromEntries((catalog.units||[]).map(t=>[t.id,t]));shell();render();}catch(error){document.querySelector('#app').innerHTML='<div class="initial error"><h1>Не удалось открыть каталог</h1><p>Убедитесь, что сервер запущен командой python web/server.py, и обновите страницу.</p></div>';}})();
