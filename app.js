(async function(){
const [V, M, G] = await Promise.all(['data/votes.json','data/members.json','data/districts.geojson'].map(u=>fetch(u).then(r=>r.json())));
const LABEL={Y:'Yes',N:'No',A:'Abstain',X:'Absent',P:'Present, not voting',R:'Recused',O:'Other','-':'Not seated'};
const VCOL={Y:'#2e7d32',N:'#c62828',A:'#f9a825',X:'#9e9e9e',P:'#b0bec5',R:'#7e57c2',O:'#b0bec5','-':'#eceff1'};
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const pct=(a,b)=>b?(100*a/b).toFixed(1)+'%':'n/a';
// 35 distinct colors: golden-angle hues, alternating lightness
const DCOL={}; for(let d=1;d<=35;d++){const h=Math.round((d*137.508)%360); const l=[46,58,38][d%3]; const s=[70,62,55][d%2]; DCOL[d]=`hsl(${h} ${s}% ${l}%)`;}
const pidIdx={}; V.voters.forEach((v,i)=>pidIdx[v.pid]=i);
const byDistrict={}; M.members.forEach(m=>{if(m.district) byDistrict[m.district]=m;});
const byPid={}; M.members.forEach(m=>byPid[m.pid]=m);
document.getElementById('asof').textContent=`Data as of ${V.asOf}. ${V.items.length.toLocaleString()} recorded roll-call items, ${V.totalVotes.toLocaleString()} individual votes, ${V.range[0]} to ${V.range[1]}.`;
V.items.forEach(it=>{let y=0,n=0,a=0;for(const c of it.v){if(c==='Y')y++;else if(c==='N')n++;else if(c==='A')a++;} it.tl={y,n,a};});

function stats(pid){const i=pidIdx[pid]; if(i===undefined) return null;
  const s={Y:0,N:0,A:0,X:0,P:0,R:0,O:0,n:0,withMaj:0,cast:0};
  for(const it of V.items){const c=it.v[i]; if(c==='-') continue; s.n++; s[c]++; if((c==='Y'||c==='N')&&it.maj){s.cast++; if(c===it.maj) s.withMaj++;}}
  return s;}
const seatName=m=>m.vm?'Vice Mayor':(m.district?`District ${m.district}`:`At-large${m.seatNo?' seat '+m.seatNo:''}`);
const colorOf=m=>m.district?DCOL[m.district]:(m.vm?'#37474f':'#8d6e63');

// ---------- map ----------
const map=L.map('map',{zoomControl:true,scrollWheelZoom:true}).setView([36.17,-86.78],10);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:18,attribution:'© OpenStreetMap contributors'}).addTo(map);
let selItem=null, selDistrict=null; const layersByD={};
function styleFor(d){
  let fill=DCOL[d], op=0.55;
  if(selItem){const m=byDistrict[d]; const i=m?pidIdx[m.pid]:undefined; fill=i===undefined?'#eceff1':VCOL[selItem.v[i]]; op=0.8;}
  return {color:d===selDistrict?'#000':'#fff',weight:d===selDistrict?4:1.5,fillColor:fill,fillOpacity:op};
}
const layer=L.geoJSON(G,{style:f=>styleFor(f.properties.DISTRICT),onEachFeature:(f,l)=>{
  const d=f.properties.DISTRICT, m=byDistrict[d]; layersByD[d]=l;
  l.bindTooltip(String(d),{permanent:true,direction:'center',className:'dlabel'});
  l.bindPopup(()=>`<b>District ${d}</b><br>${esc(m?m.name:'')}`,{autoPan:false});
  l.on('mouseover',()=>{l.setStyle({weight:4,color:'#111',fillOpacity:selItem?0.9:0.8}); l.bringToFront(); hl(d,true); const t=document.getElementById('hoverTip'); });
  l.on('mouseout',()=>{l.setStyle(styleFor(d)); hl(d,false);});
  l.on('click',()=>{selDistrict=d; restyle(); if(m) openProfile(m);});
}}).addTo(map);
map.fitBounds(layer.getBounds(),{padding:[10,10]});
function restyle(){for(const d in layersByD) layersByD[d].setStyle(styleFor(+d));}
function hl(d,on){const el=document.querySelector(`.lg[data-d="${d}"]`); if(el){el.classList.toggle('hl',on); if(on) el.scrollIntoView({block:'nearest'});}}
// legend
const legendList=document.getElementById('legendList');
function drawLegend(){const q=document.getElementById('findDistrict').value.toLowerCase();
  legendList.innerHTML=Object.keys(byDistrict).map(Number).sort((a,b)=>a-b).filter(d=>!q||(`district ${d} `+byDistrict[d].name+' '+byDistrict[d].area).toLowerCase().includes(q)).map(d=>{const m=byDistrict[d];
    return `<div class="lg" data-d="${d}" tabindex="0"><span class="sw" style="background:${DCOL[d]}"></span><span><b style="margin:0">${d}</b> ${esc(m.name)}<br><span class="muted">${esc(m.area)}</span></span></div>`;}).join('');}
drawLegend(); document.getElementById('findDistrict').addEventListener('input',drawLegend);
legendList.addEventListener('mouseover',e=>{const el=e.target.closest('.lg'); if(!el) return; const l=layersByD[el.dataset.d]; l.setStyle({weight:4,color:'#111'}); l.bringToFront();});
legendList.addEventListener('mouseout',e=>{const el=e.target.closest('.lg'); if(!el) return; layersByD[el.dataset.d].setStyle(styleFor(+el.dataset.d));});
function pickD(el){const d=+el.dataset.d; selDistrict=d; restyle(); map.fitBounds(layersByD[d].getBounds(),{maxZoom:13,padding:[20,20]}); openProfile(byDistrict[d]);}
legendList.addEventListener('click',e=>{const el=e.target.closest('.lg'); if(el) pickD(el);});
legendList.addEventListener('keydown',e=>{if(e.key==='Enter'){const el=e.target.closest('.lg'); if(el) pickD(el);}});

// ---------- member cards ----------
const order=[...M.members].sort((a,b)=>(a.vm?-2:a.district?a.district:-1)-(b.vm?-2:b.district?b.district:-1)||(a.seatNo||0)-(b.seatNo||0));
document.getElementById('cards').innerHTML=order.map(m=>`<button class="mc" data-pid="${m.pid}"><span class="bar" style="background:${colorOf(m)}"></span><img src="${esc(m.photo||'')}" alt="" loading="lazy"><span><b style="margin:0">${esc(m.name)}</b><br><span class="muted">${seatName(m)}</span></span></button>`).join('');
document.getElementById('cards').addEventListener('click',e=>{const b=e.target.closest('.mc'); if(!b) return; const m=byPid[b.dataset.pid]; selDistrict=m.district||null; restyle(); openProfile(m);});

// ---------- profile ----------
const drawer=document.getElementById('drawer');
document.getElementById('closeDrawer').onclick=closeProfile;
drawer.addEventListener('click',e=>{if(e.target===drawer) closeProfile();});
document.addEventListener('keydown',e=>{if(e.key==='Escape') closeProfile();});
function closeProfile(){drawer.hidden=true; if(location.hash) history.replaceState(null,'',location.pathname+location.search);}
function openProfile(m){
  const s=stats(m.pid), a=m.attendance, i=pidIdx[m.pid];
  const p=document.getElementById('profile');
  p.innerHTML=`<div class="ph"><img src="${esc(m.photo||'')}" alt="Official photo of ${esc(m.name)}">
  <div class="info"><h2 id="pName">${esc(m.name)}</h2><div>${seatName(m)}${m.area?' · '+esc(m.area):''}</div>
  <div class="seatbar" style="background:${colorOf(m)}"></div>
  <div>${esc(m.bio||'')}</div></div></div>
  <div class="tiles">
   ${a?`<div class="tile"><div class="muted">Meetings attended</div><div class="n">${a.attended} of ${a.total} (${pct(a.attended,a.total)})</div></div>`:''}
   ${s?`<div class="tile"><div class="muted">Recorded votes</div><div class="n">${s.n.toLocaleString()}</div></div>
   <div class="tile"><div class="muted">Yes / No / Abstain</div><div class="n">${s.Y} / ${s.N} / ${s.A}</div></div>
   <div class="tile"><div class="muted">Absent for votes</div><div class="n">${s.X}</div></div>
   <div class="tile"><div class="muted">With the majority</div><div class="n">${pct(s.withMaj,s.cast)}</div></div>`:''}
  </div>
  <h3>Contact</h3>
  <dl><dt>Email</dt><dd><a href="mailto:${esc(m.email)}">${esc(m.email)}</a></dd>
  ${m.phone?`<dt>Phone</dt><dd><a href="tel:${esc(m.phone.replace(/[^0-9]/g,''))}">${esc(m.phone)}</a></dd>`:''}
  <dt>Office</dt><dd>${esc(m.office)}</dd>
  <dt>Official page</dt><dd><a href="${esc(m.page)}" target="_blank" rel="noopener">nashville.gov profile</a></dd>
  <dt>Newsletter</dt><dd>${m.newsletter?`<a href="${esc(m.newsletter.url)}" target="_blank" rel="noopener">${esc(m.newsletter.label)}</a>`:'<span class="muted">None found</span>'}</dd></dl>
  ${m.committees&&m.committees.length?`<h3>Committees</h3><div class="muted">As listed on their nashville.gov page, which may lag current assignments.</div><ul class="plain">${m.committees.map(c=>`<li>${esc(c)}</li>`).join('')}</ul>`:''}
  ${a&&a.missed.length?`<h3 style="margin-top:12px">Meetings missed</h3><div>${a.missed.map(x=>`<a href="${esc(x.url)}" target="_blank" rel="noopener">${x.date}</a>`).join(', ')}</div>`:''}
  ${i!==undefined?`<h3 style="margin-top:16px">How ${esc(m.name.split(' ')[0])} voted</h3>
  <div class="row"><input type="search" id="mq" placeholder="Search bill number, title or keyword">
  <select id="mv"><option value="">Any vote</option><option value="Y">Yes</option><option value="N">No</option><option value="A">Abstain</option><option value="X">Absent</option><option value="P">Present, not voting</option><option value="R">Recused</option></select>
  <select id="mo"><option value="">Any outcome</option><option>Pass</option><option>Fail</option></select>
  <select id="my"><option value="">All years</option>${[...new Set(V.items.map(x=>x.d.slice(0,4)))].sort().map(y=>`<option>${y}</option>`).join('')}</select>
  <button id="mDiv">Divided votes only</button><button id="mMin">Voted against majority</button></div>
  <div class="muted" id="mcount"></div>
  <div class="scroll" style="max-height:none"><table><thead><tr><th>Date</th><th>Legislation</th><th>Their vote</th><th>Outcome</th></tr></thead><tbody id="mbody"></tbody></table></div>`:'<div class="muted" style="margin-top:12px">No recorded votes for this member in the data.</div>'}`;
  drawer.hidden=false; drawer.querySelector('.drawer-inner').scrollTop=0;
  history.replaceState(null,'',`#${m.district?'d'+m.district:'p'+m.pid}`);
  if(i===undefined) return;
  const rows=V.items.filter(it=>it.v[i]!=='-').slice().reverse();
  let div=false,min=false; const q=document.getElementById('mq'),mv=document.getElementById('mv'),mo=document.getElementById('mo'),my=document.getElementById('my'),tb=document.getElementById('mbody');
  let limit=200;
  function draw(){const t=q.value.toLowerCase();
    const r=rows.filter(it=>{const c=it.v[i]; return (!t||(it.f+' '+it.t).toLowerCase().includes(t))&&(!mv.value||c===mv.value)&&(!mo.value||it.o===mo.value)&&(!my.value||it.d.startsWith(my.value))&&(!div||it.tl.n>0)&&(!min||((c==='Y'||c==='N')&&it.maj&&c!==it.maj));});
    document.getElementById('mcount').textContent=`${r.length.toLocaleString()} items`;
    tb.innerHTML=r.slice(0,limit).map(it=>`<tr><td>${it.d}</td><td><a href="${it.url}" target="_blank" rel="noopener">${esc(it.f||'Item')}</a> ${esc(it.t.length>160?it.t.slice(0,157)+'…':it.t)}${it.a?` <span class="muted">(${esc(it.a)})</span>`:''}</td><td class="v-${it.v[i]}">${LABEL[it.v[i]]}</td><td>${esc(it.o||'')} ${it.tl.y}-${it.tl.n}</td></tr>`).join('')+(r.length>limit?`<tr><td colspan="4"><button id="more">Show more (${(r.length-limit).toLocaleString()} left)</button></td></tr>`:'');
    const mb=document.getElementById('more'); if(mb) mb.onclick=()=>{limit+=300;draw();};}
  [q,mv,mo,my].forEach(el=>el.addEventListener('input',()=>{limit=200;draw();}));
  document.getElementById('mDiv').onclick=e=>{div=!div;e.target.classList.toggle('on',div);limit=200;draw();};
  document.getElementById('mMin').onclick=e=>{min=!min;e.target.classList.toggle('on',min);limit=200;draw();};
  draw();
}

// ---------- at a glance table ----------
const glance=M.members.map(m=>{const s=stats(m.pid)||{n:0,N:0,withMaj:0,cast:0}; const a=m.attendance||{attended:0,total:0};
  return {m,name:m.name,seat:m.vm?'VM':(m.district?`D${m.district}`:'At-large'),sk:m.vm?0:(m.district||0.5),att:a.attended,tot:a.total,attp:a.total?a.attended/a.total:0,n:s.n,N:s.N,maj:s.cast?s.withMaj/s.cast:0,majTxt:pct(s.withMaj,s.cast)};});
let sortK='seat',sortDir=1;
function drawGlance(){const r=glance.slice().sort((a,b)=>{const k=sortK==='seat'?'sk':sortK; return (a[k]>b[k]?1:a[k]<b[k]?-1:0)*sortDir;});
  document.querySelector('#stats tbody').innerHTML=r.map(x=>`<tr data-pid="${x.m.pid}" style="cursor:pointer"><td>${esc(x.name)}</td><td>${x.seat}</td><td>${x.att} of ${x.tot}</td><td>${pct(x.att,x.tot)}</td><td>${x.n.toLocaleString()}</td><td>${x.N}</td><td>${x.majTxt}</td></tr>`).join('');}
document.querySelectorAll('#stats th').forEach(th=>th.onclick=()=>{const k=th.dataset.k; sortDir=sortK===k?-sortDir:(k==='name'||k==='seat'?1:-1); sortK=k; drawGlance();});
document.querySelector('#stats tbody').addEventListener('click',e=>{const tr=e.target.closest('tr'); if(tr){const m=byPid[tr.dataset.pid]; selDistrict=m.district||null; restyle(); openProfile(m);}});
document.getElementById('glanceNote').textContent=`Attendance counts full council meetings since ${V.attendance.first}. Click a column to sort, or a row to open the profile. See the method notes below.`;
drawGlance();

// ---------- items explorer (secondary) ----------
const types=[...new Set(V.items.map(i=>i.ty).filter(Boolean))].sort();
document.getElementById('type').innerHTML+=types.map(t=>`<option>${esc(t)}</option>`).join('');
document.getElementById('year').innerHTML+=[...new Set(V.items.map(i=>i.d.slice(0,4)))].sort().map(t=>`<option>${t}</option>`).join('');
let splitOnly=false;
document.getElementById('splitOnly').onclick=e=>{splitOnly=!splitOnly;e.target.classList.toggle('on',splitOnly);renderItems();};
['q','type','year'].forEach(id=>document.getElementById(id).addEventListener('input',renderItems));
const itemByKey={}; V.items.forEach(it=>itemByKey[it.k]=it);
function renderItems(){const q=document.getElementById('q').value.toLowerCase(), ty=document.getElementById('type').value, yr=document.getElementById('year').value;
  const r=V.items.filter(it=>(!q||(it.f+' '+it.t).toLowerCase().includes(q))&&(!ty||it.ty===ty)&&(!yr||it.d.startsWith(yr))&&(!splitOnly||it.tl.n>0)).slice().reverse();
  document.getElementById('count').textContent=`${r.length.toLocaleString()} items`+(r.length>400?' (newest 400 shown; search to narrow)':'');
  document.getElementById('tbody').innerHTML=r.slice(0,400).map(it=>`<tr data-k="${it.k}" class="${selItem&&selItem.k===it.k?'sel':''}"><td>${it.d}</td><td>${esc(it.f)}</td><td>${esc(it.t.length>140?it.t.slice(0,137)+'…':it.t)}</td><td>${esc(it.o)}</td><td>${it.tl.y}-${it.tl.n}${it.tl.a?'-'+it.tl.a:''}</td></tr>`).join('');}
document.getElementById('tbody').addEventListener('click',e=>{const tr=e.target.closest('tr'); if(!tr) return; selItem=itemByKey[tr.dataset.k]; renderItems(); restyle(); showItem(selItem); colorBar(); document.getElementById('map').scrollIntoView({behavior:'smooth'});});
function colorBar(){const el=document.getElementById('colorBy');
  if(!selItem){el.hidden=true;return;} el.hidden=false;
  el.innerHTML=`<b>Map colored by:</b> ${esc(selItem.f||'Item')} on ${selItem.d} (${esc(selItem.o||'no outcome listed')}, ${selItem.tl.y}-${selItem.tl.n}). <div class="row">${['Y','N','A','X','P','R'].map(c=>`<span><span class="sw" style="background:${VCOL[c]}"></span> ${LABEL[c]}</span>`).join('')}<button id="clearSel">Back to district colors</button></div>`;
  document.getElementById('clearSel').onclick=()=>{selItem=null;renderItems();restyle();colorBar();document.getElementById('itemDetail').hidden=true;};}
function showItem(it){const el=document.getElementById('itemDetail'); el.hidden=false;
  const groups={}; V.voters.forEach((v,i)=>{const c=it.v[i]; if(c==='-') return; (groups[c]=groups[c]||[]).push(v);});
  el.innerHTML=`<h3 style="margin-top:12px">${esc(it.f||'Item')} on ${it.d}${it.o?': '+esc(it.o):''}</h3><div>${esc(it.t)}</div>
  <div class="row"><a href="${it.url}" target="_blank" rel="noopener">Legistar record</a> <a href="${it.mu}" target="_blank" rel="noopener">Meeting agenda, minutes and video</a></div>
  ${['Y','N','A','R','P','X'].filter(c=>groups[c]).map(c=>`<div style="margin-top:6px"><b class="v-${c}">${LABEL[c]} (${groups[c].length})</b>: ${groups[c].map(v=>esc(v.name)+(v.seat?` (${v.seat})`:'')).join(', ')}</div>`).join('')}`;}
renderItems();
document.getElementById('sources').innerHTML=V.notesHtml;

// deep link
const h=location.hash.slice(1); if(h){const m=h[0]==='d'?byDistrict[+h.slice(1)]:byPid[h.slice(1)]; if(m){selDistrict=m.district||null; restyle(); openProfile(m);}}
})();
