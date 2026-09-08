'use strict';
const eventKinds={registration_open:'Начало регистрации',registration_close:'Окончание регистрации',qualifying:'Отборочный этап',final:'Заключительный этап',results:'Результаты',appeal:'Апелляция',documents_open:'Начало подачи документов',documents_close:'Окончание подачи документов',admission:'Приёмная кампания',custom:'Своё событие'};
const participation={planned:'В планах',registered:'Зарегистрирован',participating:'Участвую',completed:'Завершено',skipped:'Пропускаю'};
let personalState={events:[],plan:[],loggedIn:false};
async function personalAPI(path,method='GET',body) {
  const r=await fetch('/backend'+path,{method,headers:{'Content-Type':'application/json'},credentials:'same-origin',body:body===undefined?undefined:JSON.stringify(body),cache:'no-store'});
  const data=await r.json().catch(()=>({}));
  if(!r.ok){const error=new Error(data.message||'Не удалось выполнить запрос');error.status=r.status;throw error;}
  return data;
}
function localEventDate(e) {
  if(e.start_date)return e.start_date;
  if(!e.starts_at)return '';
  const parts=new Intl.DateTimeFormat('en-CA',{timeZone:e.timezone,year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date(e.starts_at));
  const get=t=>parts.find(p=>p.type===t).value;return `${get('year')}-${get('month')}-${get('day')}`;
}
function eventIncludesDate(e,date) {
  if(!date)return true;if(e.time_kind==='undated')return false;
  if(e.time_kind==='all_day')return e.start_date===date;
  if(e.time_kind==='date_range')return e.start_date<=date&&date<=e.end_date;
  const end=e.ends_at?localEventDate({...e,starts_at:new Date(new Date(e.ends_at).getTime()-1).toISOString()}):localEventDate(e);
  return localEventDate(e)<=date&&date<=end;
}
function eventDateText(e) {
  if(e.time_kind==='undated')return 'Срок ещё не подтверждён';
  if(e.time_kind==='all_day')return e.start_date+' · время не указано';
  if(e.time_kind==='date_range')return `${e.start_date} — ${e.end_date} включительно`;
  const f=new Intl.DateTimeFormat('ru-RU',{timeZone:e.timezone,dateStyle:'medium',timeStyle:'short'});
  return f.format(new Date(e.starts_at))+(e.ends_at?' — '+f.format(new Date(e.ends_at)):'');
}
function authForm(){return `<section class="rule"><h2>Войдите в свой аккаунт ОлимпГида</h2><form data-personal-form="login" class="personal-form"><label>Электронная почта<input name="email" type="email" autocomplete="username" required></label><label>Пароль<input name="password" type="password" autocomplete="current-password" required></label><button class="button primary">Войти</button><p class="form-error" role="alert"></p></form></section>`;}
function personalPage(type){return intro(type==='calendar'?'Мой календарь':'Мои дипломы',type==='calendar'?'Олимпиады и поступление по твоему плану. Личные отметки сохраняются в аккаунте.':'Проверь условия льгот с учётом года диплома и поступления.','book')+'<div id="personal-content" aria-live="polite">Загружаем…</div>';}
function formOptions(map,value){return Object.entries(map).map(([v,t])=>`<option value="${esc(v)}" ${v===value?'selected':''}>${esc(t)}</option>`).join('');}
function calendarLocalInput(instant,zone){
  if(!instant)return '';
  const parts=new Intl.DateTimeFormat('en-CA',{timeZone:zone,year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'}).formatToParts(new Date(instant));
  const get=t=>parts.find(p=>p.type===t).value;return `${get('year')}-${get('month')}-${get('day')}T${get('hour')}:${get('minute')}:${get('second')}`;
}
function calendarInstant(wall,zone){
  if(!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?$/.test(wall))throw new Error('Укажите дату и время');
  const full=wall.length===16?wall+':00':wall,anchor=Date.parse(full+'Z');
  if(!Number.isFinite(anchor)||new Date(anchor).toISOString().slice(0,19)!==full)throw new Error('Некорректная дата');
  const matches=[];
  for(let minutes=-14*60;minutes<=14*60;minutes+=15){const instant=new Date(anchor-minutes*60000).toISOString();if(calendarLocalInput(instant,zone)===full)matches.push({instant,minutes});}
  if(matches.length!==1)throw new Error(matches.length?'Время повторяется при переводе часов. Укажите событие в часовом поясе UTC.':'Такого времени нет в выбранном часовом поясе. Проверьте дату и перевод часов.');
  const offset=matches[0].minutes,abs=Math.abs(offset);return full+(offset<0?'-':'+')+String(Math.floor(abs/60)).padStart(2,'0')+':'+String(abs%60).padStart(2,'0');
}
function calendarEventForm(e={}) {
  return `<label>Название<input name="title" maxlength="240" value="${esc(e.title)}" required></label><label>Вид<select name="kind">${formOptions(eventKinds,e.kind||'custom')}</select></label><label>Точность даты<select name="time_kind">${formOptions({all_day:'Весь день',timed:'Точное время',date_range:'Диапазон дат',undated:'Дата не объявлена'},e.time_kind||'all_day')}</select></label><label>Часовой пояс<input name="timezone" value="${esc(e.timezone||Intl.DateTimeFormat().resolvedOptions().timeZone||'Europe/Moscow')}" required></label><div data-date-fields="day"><label>Дата начала<input name="start_date" type="date" value="${esc(e.start_date)}"></label><label data-range-field>Дата окончания (включительно)<input name="end_date" type="date" value="${esc(e.end_date)}"></label></div><div data-date-fields="timed"><label>Начало в выбранном часовом поясе<input name="starts_at" type="datetime-local" step="1" value="${esc(calendarLocalInput(e.starts_at,e.timezone))}"></label><label>Окончание — необязательно<input name="ends_at" type="datetime-local" step="1" value="${esc(calendarLocalInput(e.ends_at,e.timezone))}"></label></div><label>Описание<textarea name="description" maxlength="8000">${esc(e.description)}</textarea></label><label>Учебный год олимпиады (необязательно)<input name="season" placeholder="2026/2027" value="${esc(e.season)}"></label><label>Год поступления (необязательно)<input name="admission_year" type="number" min="2000" max="2100" value="${esc(e.admission_year)}"></label>`;
}
function toggleDateFields(form){const kind=form.elements.time_kind?.value;if(!kind)return;form.querySelector('[data-date-fields="day"]').hidden=!['all_day','date_range'].includes(kind);form.querySelector('[data-range-field]').hidden=kind!=='date_range';form.querySelector('[data-date-fields="timed"]').hidden=kind!=='timed';}
function eventFromForm(form){const f=Object.fromEntries(new FormData(form));const e={title:f.title,kind:f.kind,time_kind:f.time_kind,timezone:f.timezone,description:f.description,season:f.season,admission_year:f.admission_year?Number(f.admission_year):null};if(['all_day','date_range'].includes(e.time_kind))e.start_date=f.start_date;if(e.time_kind==='date_range')e.end_date=f.end_date;if(e.time_kind==='timed'){e.starts_at=calendarInstant(f.starts_at,e.timezone);if(f.ends_at)e.ends_at=calendarInstant(f.ends_at,e.timezone);}return e;}
function eventLinks(e){return [...(e.web_olympiad_ids||[]).filter(id=>olymp[id]).map(id=>`<a href="${href('olympiads',id)}">К олимпиаде</a>`),...(e.program_keys||[]).filter(id=>programs[id]).map(id=>`<a href="${href('programs',id)}">${esc(programs[id].name)}</a>`),...(e.university_key&&uni[e.university_key]?[`<a href="${href('universities',e.university_key)}">Программы ${esc(uni[e.university_key].short_name)}</a>`]:[]),...(val('program')&&programs[val('program')]?[`<a href="${href('programs',val('program'))}">К выбранной программе</a>`]:[])].join('');}
function eventCard(row,planned){const e=row.event;const saved=personalState.plan.find(p=>p.event_id===row.id);return `<article class="rule"><div class="rule-header"><h3>${esc(e.title)}</h3><span class="tag">${esc(eventKinds[e.kind])}</span></div><p class="payment-amount">${esc(eventDateText(e))}</p><p class="hint">${esc(e.timezone)}${e.season?' · Сезон '+esc(e.season):''}${e.admission_year?' · Приём '+esc(e.admission_year):''}${!row.event_id&&planned?' · Своё событие':''}</p><p>${esc(e.description)}</p>${row.dates_changed?note('Данные источника обновились. Ваш статус и заметка сохранены.'):''}${row.source_active===false?note('Событие снято с опубликованного графика. Оно сохранено в вашем плане для проверки.'):''}<div class="rule-source">${eventLinks(e)}${e.source_url?external(e.source_url,'Источник'):''}${e.checked_on?`<span>Проверено ${esc(e.checked_on)}</span>`:''}</div>${planned?`<form data-personal-form="plan" data-plan-id="${row.plan_id}" class="personal-form"><label>Участие<select name="status">${formOptions(participation,row.status)}</select></label><label>Моя заметка<textarea name="note" maxlength="4000">${esc(row.note)}</textarea></label>${!row.event_id?`<details><summary>Изменить своё событие</summary>${calendarEventForm(e)}</details>`:''}${row.dates_changed?'<label class="check"><input type="checkbox" name="acknowledge">Я проверил обновление источника</label>':''}<div class="actions"><button class="button">Сохранить отметки</button><button type="button" class="text-button" data-delete-plan="${row.plan_id}">Удалить из плана</button></div><p class="form-error" role="alert"></p></form>`:`<button class="button" data-add-event="${esc(row.id)}" ${saved||!personalState.loggedIn?'disabled':''}>${saved?'В моём плане':'Добавить в план'}</button>`}</article>`;}
async function renderPersonal(type,version){
  if(type==='diplomas'&&typeof renderDiplomas==='function')return renderDiplomas(version);
  try {
    const [events,plan]=await Promise.all([personalAPI('/calendar/events'),personalAPI('/user/calendar').catch(e=>{if(e.status===401)return null;throw e;})]);
    if(version!==renderVersion)return;
    personalState={events,plan:plan||[],loggedIn:plan!==null};
    const mine=val('scope')!=='catalog',byDate=val('view')==='dates';
    let rows=(mine?personalState.plan:events).filter(r=>(!val('kind')||r.event.kind===val('kind'))&&(!val('status')||r.status===val('status'))&&(!val('season')||r.event.season===val('season'))&&(!val('olympiad')||(r.event.web_olympiad_ids||[]).includes(val('olympiad')))&&(!val('program')||(r.event.program_keys||[]).includes(val('program'))||r.event.university_key===programs[val('program')]?.university_id)&&(!byDate||eventIncludesDate(r.event,val('date'))));
    rows.sort((a,b)=>(localEventDate(a.event)||'9999').localeCompare(localEventDate(b.event)||'9999')||a.event.title.localeCompare(b.event.title));
    const controls=`<div class="toolbar">${select('scope','Мой план',[['catalog','Каталог событий']])}${select('view','Список',[['dates','По датам']])}${select('kind','Все события',Object.entries(eventKinds))}${select('status','Любой статус',Object.entries(participation))}${select('season','Все сезоны',[...new Set(events.map(r=>r.event.season).filter(Boolean))])}${byDate?`<label class="calendar-date-filter">Дата<input type="date" data-filter="date" value="${esc(val('date'))}"></label>`:''}</div>`;
    let previous=null;const cards=rows.map(r=>{const day=val('date')||localEventDate(r.event)||'Без даты';const title=byDate&&day!==previous?`<h2 class="space-top">${esc(day)}</h2>`:'';previous=day;return title+eventCard(r,mine);}).join('');
    document.querySelector('#personal-content').innerHTML=(plan===null?authForm():`<p><button class="text-button" data-personal-logout>Выйти из аккаунта</button></p><details class="rule"><summary>Добавить своё событие</summary><form data-personal-form="custom" class="personal-form">${calendarEventForm()}<button class="button primary">Добавить событие</button><p class="form-error" role="alert"></p></form></details>`)+controls+(rows.length?`<div class="rules">${cards}</div>`:empty(mine?'В плане пока нет событий':'По этим фильтрам нет событий','Откройте каталог событий или добавьте своё.'))+note('Подтверждён общий график «Высшей пробы» 2026/27 и срок подачи документов ИТМО 2026. События других олимпиад добавляются по мере проверки источников.');
    document.querySelectorAll('[data-personal-form]').forEach(toggleDateFields);
  }catch(e){if(version===renderVersion)document.querySelector('#personal-content').innerHTML=note(esc(e.message));}
}
document.addEventListener('change',e=>{if(e.target.name==='time_kind')toggleDateFields(e.target.form);});
document.addEventListener('submit',async e=>{
  const form=e.target,kind=form.dataset.personalForm;if(!kind)return;
  if(!['login','custom','plan'].includes(kind))return;
  e.preventDefault();const button=form.querySelector('button[type="submit"],button:not([type])');if(button)button.disabled=true;
  try{
    if(kind==='login')await personalAPI('/auth/login','POST',Object.fromEntries(new FormData(form)));
    if(kind==='custom'){form.dataset.clientKey ||= crypto.randomUUID();await personalAPI('/user/calendar/custom','POST',{client_key:form.dataset.clientKey,event:eventFromForm(form)});}
    if(kind==='plan'){const body={status:form.elements.status.value,note:form.elements.note.value,acknowledge:!!form.elements.acknowledge?.checked};if(form.elements.title)body.event=eventFromForm(form);await personalAPI('/user/calendar/'+form.dataset.planId,'PUT',body);}
    render();
  }catch(error){form.querySelector('.form-error').textContent=error.message;}finally{if(button)button.disabled=false;}
});
document.addEventListener('click',async e=>{
  const add=e.target.closest('[data-add-event]'),del=e.target.closest('[data-delete-plan]'),logout=e.target.closest('[data-personal-logout]');if(!add&&!del&&!logout)return;
  const button=add||del||logout;button.disabled=true;
  try{if(add)await personalAPI('/user/calendar','POST',{event_id:add.dataset.addEvent});if(del)await personalAPI('/user/calendar/'+del.dataset.deletePlan,'DELETE',{});if(logout){await personalAPI('/auth/logout','POST',{});personalState={events:[],plan:[],loggedIn:false};}render();}catch(error){toast(error.message);}finally{button.disabled=false;}
});
