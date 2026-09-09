'use strict';
const eligibilityStatuses={eligible:'Проверенные условия выполнены',confirmation_required:'Нужно подтверждение ЕГЭ',ineligible:'Условия не выполнены',manual_review:'Недостаточно данных / ручная проверка'};
const benefitLabels={bvi:'БВИ', '100_points':'100 баллов',other:'Другое преимущество'};
const diplomaResults={winner:'Победитель',prize_winner:'Призёр',participant:'Участник'};
const examSubjects=['математика','информатика','физика','химия','биология','русский язык','литература','история','обществознание','география','иностранный язык'];
let diplomaState={catalog:{olympiads:[]},diplomas:[],profile:{admission_year:null,exams:[]}};

function diplomaFields(d={}){
  const options=diplomaState.catalog.olympiads.map(o=>`<option value="${o.olympiad_id}" ${o.olympiad_id===d.olympiad_id?'selected':''}>${esc(o.name)} · ${esc(o.profile)} · ${esc(o.academic_year ? o.academic_year+(o.registry_status==='draft'?' · Проект перечня':'') : o.admission_year?'Правила приёма '+o.admission_year:'Архив')} · ${esc(o.category==='rsosh'?'Перечневая':o.category==='vsosh'?'ВсОШ':o.category)}</option>`).join('');
  const legacy=d.olympiad_id&&!diplomaState.catalog.olympiads.some(o=>o.olympiad_id===d.olympiad_id);
  return `<label>Найти олимпиаду или профиль<input type="search" data-find-olympiad placeholder="Название, профиль"></label><label>Олимпиада и профиль<select name="olympiad_id" required><option value="">Выберите из каталога</option>${legacy?`<option value="${d.olympiad_id}" selected>${esc(d.olympiad?.name)} · старый каталог, уточните соответствие</option>`:''}${options}</select></label><label>Профиль на дипломе<input name="profile" maxlength="300" value="${esc(d.profile)}" placeholder="Как указан в дипломе"></label><label>Год получения диплома<input name="award_year" type="number" min="2000" max="2100" value="${esc(d.award_year)}" placeholder="Например, 2026"></label><label>Учебный год олимпиады<input name="olympiad_year" value="${esc(d.olympiad_year)}" placeholder="2025/2026" pattern="20[0-9]{2}/20[0-9]{2}"></label><label>Класс, за который выполнены задания<select name="class">${formOptions(Object.fromEntries(Array.from({length:11},(_,i)=>[String(i+1),String(i+1)])),String(d.class||11))}</select></label><label>Результат диплома<select name="result">${formOptions({'':'Не указан',...diplomaResults},d.result||'')}</select></label><label>Степень диплома<select name="level">${formOptions({'1':'I','2':'II','3':'III'},String(d.level||1))}</select></label><p class="hint">Год олимпиады и год поступления задаются отдельно. Неизвестные сведения можно оставить пустыми — вывод потребует уточнения.</p>`;
}
function examRow(e={}){return `<div class="exam-row"><label>Предмет<select name="exam_subject">${formOptions(Object.fromEntries(examSubjects.map(s=>[s,s])),e.subject||'математика')}</select></label><label>Баллы<input name="exam_score" type="number" min="0" max="100" value="${esc(e.score)}" required></label><label>Год ЕГЭ<input name="exam_year" type="number" min="2000" max="2100" value="${esc(e.year)}" required></label><button type="button" class="text-button" data-remove-exam>Убрать результат</button></div>`;}
function recommendationCard(p){
  return `<article class="rule recommendation"><p class="eyebrow">${esc(p.university)}</p><h3><a href="${href('programs',p.program_key)}">${esc(p.name)}</a></h3><p class="assessment-status ${esc(p.status)}">${esc(eligibilityStatuses[p.status])}</p>${p.assessments.map(a=>{
    const source=a.source_rule?.source||{},d=diplomaState.diplomas.find(d=>d.diploma_id===a.diploma_id),v=a.source_rule?.values||{};
    return `<details><summary>${esc(benefitLabels[a.benefit]||'Преимущество из источника')} · ${esc(eligibilityStatuses[a.status])}</summary><p>${esc(d?.olympiad?.name)} · ${esc(d?.profile||'Профиль не уточнён')}</p><p>${esc(a.reason)}</p>${a.checks.length?`<ul class="condition-checks">${a.checks.map(c=>`<li><strong>${esc(c.condition)}</strong> · ${esc({pass:'выполнено',fail:'не выполнено',pending:'нужно подтверждение',unknown:'нужна проверка'}[c.state])}<br>${esc(c.detail)}</li>`).join('')}</ul>`:''}<p><strong>Условие источника:</strong> ${esc(v.benefit)}</p><p><strong>Область действия:</strong> ${esc(v.program_scope)}</p>${(a.source_rule?.conditions||[]).map(c=>`<p class="hint">${esc(c)}</p>`).join('')}<div class="rule-source">${external(source.url,source.title||'Официальный источник')}<span>Приём ${esc(a.source_rule?.admission_year)}</span></div></details>`;
  }).join('')}</article>`;
}
async function renderDiplomas(version){
  try{
    const data=await Promise.all([personalAPI('/personal/catalog'),personalAPI('/user/diplomas/'),personalAPI('/user/admission-profile')]);
    if(version!==renderVersion)return;
    diplomaState={catalog:data[0],diplomas:data[1],profile:data[2]};
    const query=new URLSearchParams({limit:'12',offset:val('offset')||'0'});
    for(const key of ['status','benefit','diploma_id','q'])if(val(key))query.set(key,val(key));
    const matches=await personalAPI('/user/recommendations?'+query);
    if(version!==renderVersion)return;
    const p=diplomaState.profile;
    document.querySelector('#personal-content').innerHTML=`<p><button class="text-button" data-personal-logout>Выйти из аккаунта</button></p><details class="rule" ${p.admission_year?'':'open'}><summary>Поступление ${esc(p.admission_year||'— укажите год')} · ${p.exams.length} результатов ЕГЭ</summary><form data-personal-form="applicant" class="personal-form"><label>Год поступления<input name="admission_year" type="number" min="2000" max="2100" value="${esc(p.admission_year)}" required></label><p class="hint">Для 2027 года правила ещё не подтверждены. Наличие графика олимпиады 2026/27 не подтверждает льготы приёма 2027.</p><div data-exams>${p.exams.map(examRow).join('')}</div><button type="button" class="button" data-add-exam>Добавить результат ЕГЭ</button><button class="button primary">Сохранить и проверить</button><p class="form-error" role="alert"></p></form></details><details class="rule"><summary>Добавить диплом</summary><form data-personal-form="diploma" class="personal-form">${diplomaFields()}<button class="button primary">Сохранить диплом</button><p class="form-error" role="alert"></p></form></details><div class="rules">${diplomaState.diplomas.map(d=>`<details class="rule"><summary>${esc(d.olympiad.name)} · ${esc(d.profile||d.olympiad.profile)} · ${esc(d.award_year||'год не указан')}</summary><form data-personal-form="diploma" data-diploma-id="${d.diploma_id}" class="personal-form">${diplomaFields(d)}<button class="button">Сохранить изменения</button><button type="button" class="text-button" data-delete-diploma="${d.diploma_id}">Удалить диплом</button><p class="form-error" role="alert"></p></form></details>`).join('')}</div><h2 class="space-top">Куда подходят мои дипломы</h2>${note(esc(matches.message))}<div class="toolbar">${select('status','Все статусы',Object.entries(eligibilityStatuses))}${select('benefit','Все преимущества',Object.entries(benefitLabels))}${select('diploma_id','Все мои дипломы',diplomaState.diplomas.map(d=>[String(d.diploma_id),d.olympiad.name+' · '+(d.profile||d.olympiad.profile)]))}<label>Программа или вуз<input type="search" data-filter="q" value="${esc(val('q'))}" placeholder="Название"></label></div><p>Найдено программ: ${num(matches.total)}</p><div class="rules">${matches.items.map(recommendationCard).join('')}</div><div class="actions">${matches.offset>0?`<button class="button" data-match-offset="${Math.max(0,matches.offset-12)}">Назад</button>`:''}${matches.offset+12<matches.total?`<button class="button" data-match-offset="${matches.offset+12}">Ещё программы</button>`:''}</div>`;
  }catch(e){if(version===renderVersion)document.querySelector('#personal-content').innerHTML=e.status===401?authForm():note(esc(e.message));}
}
document.addEventListener('input',e=>{if(!e.target.matches('[data-find-olympiad]'))return;const q=e.target.value.toLocaleLowerCase();for(const option of e.target.form.elements.olympiad_id.options)option.hidden=!!option.value&&!option.text.toLocaleLowerCase().includes(q);});
document.addEventListener('change',e=>{
  const form=e.target.form;if(form?.dataset.personalForm!=='diploma')return;
  if(e.target.name==='olympiad_id'){const o=diplomaState.catalog.olympiads.find(o=>o.olympiad_id===Number(e.target.value));if(o)form.elements.profile.value=o.profile;}
  if(e.target.name==='result'){if(e.target.value==='winner')form.elements.level.value='1';if(e.target.value==='prize_winner'&&form.elements.level.value==='1')form.elements.level.value='2';}
});
document.addEventListener('submit',async e=>{
  const form=e.target,kind=form.dataset.personalForm;if(!['applicant','diploma'].includes(kind))return;
  e.preventDefault();const button=form.querySelector('button:not([type])');button.disabled=true;
  try{
    if(kind==='applicant'){
      const exams=[...form.querySelectorAll('.exam-row')].map(row=>({subject:row.querySelector('[name=exam_subject]').value,score:Number(row.querySelector('[name=exam_score]').value),year:Number(row.querySelector('[name=exam_year]').value)}));
      await personalAPI('/user/admission-profile','PUT',{admission_year:Number(form.elements.admission_year.value),exams});
    }else{
      const f=Object.fromEntries(new FormData(form)),body={olympiad_id:Number(f.olympiad_id),class:Number(f.class),level:Number(f.level),award_year:f.award_year?Number(f.award_year):null,olympiad_year:f.olympiad_year||null,profile:f.profile||null,result:f.result||null};
      await personalAPI(form.dataset.diplomaId?'/user/diploma/'+form.dataset.diplomaId+'/details':'/user/diploma/',form.dataset.diplomaId?'PUT':'POST',body);
    }
    const url=new URL(location.href);url.searchParams.delete('offset');history.replaceState({},'',url);render();
  }catch(error){form.querySelector('.form-error').textContent=error.message;}finally{button.disabled=false;}
});
document.addEventListener('click',async e=>{
  const add=e.target.closest('[data-add-exam]'),remove=e.target.closest('[data-remove-exam]'),del=e.target.closest('[data-delete-diploma]'),page=e.target.closest('[data-match-offset]');
  if(add){add.form.querySelector('[data-exams]').insertAdjacentHTML('beforeend',examRow());return;}
  if(remove){remove.closest('.exam-row').remove();return;}
  if(page){const url=new URL(location.href);url.searchParams.set('offset',page.dataset.matchOffset);navigate(url.pathname+url.search);return;}
  if(del){del.disabled=true;try{await personalAPI('/user/diploma/'+del.dataset.deleteDiploma,'DELETE',{});render();}catch(error){toast(error.message);}finally{del.disabled=false;}}
});
