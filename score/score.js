(async function(){
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const [config, scores]=await Promise.all([
  fetch('../data/score_config.json').then(r=>r.json()),
  fetch('../data/scores.json').then(r=>r.json()),
]);
const P=config.parameters;
const pop={}; (scores.population||[]).forEach(p=>pop[p.id]=p);
const example=scores.members.find(m=>m.pid===281)||scores.members[0];
document.getElementById('asof').textContent=`Version ${config.version}. Scores computed ${scores.computedAt} UTC. Lookback windows end ${scores.windowEnds}. Vote file: ${scores.inputsAsOf&&scores.inputsAsOf.votes||'unknown'}. Handles checked ${config.checked}.`;

function compSection(c){
  const p=pop[c.id]||{scoredMembers:0,missingMembers:0};
  const state=p.scoredMembers?`Scored for ${p.scoredMembers} of ${p.scoredMembers+p.missingMembers} people on this site.`:`Not scored for anyone yet: ${p.missingMembers} people are missing this input.`;
  const sources=(c.sources||[]).filter(s=>s.url).map(s=>`<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title||s.url)}</a>`).join('; ');
  return `<section class="card"><h2>${esc(c.name)} <span class="muted">${c.weight} of 100 · ${esc(c.group)}</span></h2>
    <p>${esc(c.plain)}</p>
    <p class="formula">${esc(c.formula)}</p>
    <p><b>When it is left out.</b> ${esc(c.missingWhen)}</p>
    <p class="muted">${state}${sources?' Sources: '+sources+'.':''}</p></section>`;
}
function exampleTable(m){
  return `<table><thead><tr><th>Component</th><th>Weight</th><th>Input</th><th>Points</th><th></th></tr></thead><tbody>${m.components.map(c=>{
    const used=c.status==='ok'&&c.points!=null;
    return `<tr class="${used?'':'miss'}"><td>${esc(c.name)}</td><td>${c.weight}</td><td>${esc(c.input||'')}</td><td>${used?Number(c.points).toFixed(1):'—'}</td><td>${used?'In the score':'Left out'}</td></tr>`;
  }).join('')}</tbody></table>`;
}
const barHtml=example.components.map(c=>{
  const on=c.status==='ok';
  return `<span style="width:${c.weight}%;background:${on?'#a16207':'#e6e0d4'}" title="${esc(c.name)}, weight ${c.weight}${on?'':', no data'}"></span>`;
}).join('');
const rows=[...scores.members].sort((a,b)=>(b.score??-1)-(a.score??-1)||a.name.localeCompare(b.name));
const table=rows.map(m=>{
  const have=m.components.filter(c=>c.status==='ok').map(c=>c.name).join(', ');
  const miss=m.components.filter(c=>c.status!=='ok').map(c=>c.name).join(', ');
  return `<tr><td><a href="../index.html?score=open#p${m.pid}">${esc(m.name)}</a></td><td>${esc(m.seat)}</td><td>${m.score==null?'Insufficient data':m.score}</td><td>${Math.round(m.coverage*100)}%</td><td>${esc(have)}</td><td class="muted">${esc(miss)}</td></tr>`;
}).join('');
const changes=(config.changelog||[]).map(c=>`<li><b>${esc(c.version)}</b> (${esc(c.date)}). ${esc(c.notes)}</li>`).join('');
const terms=(config.civilityTerms||[]).map(esc).join(', ');

document.getElementById('page').innerHTML=`
<section class="card">
<h2>The idea</h2>
<p>The score asks two questions. Are they <b>decent</b> in what they post: tone and civility, screened by a fixed word list? And are they <b>serving</b>: at council meetings, on recorded votes, updating constituents, posting in public, at community meetings, and answering questions?</p>
<p>"With the majority" stays a separate stat on the member card. This score does not go up for voting yes, and it does not go up for voting with the room.</p>
<p>${esc(config.missingData)}</p>
<p>${esc(config.rounding)}</p>
</section>

<section class="card">
<h2>What is in the number today</h2>
<p>Every person is scored from the same files. A component counts only for the people who have data for it.</p>
<table><thead><tr><th>Component</th><th>Weight</th><th>People scored</th><th>People left out</th></tr></thead><tbody>
${config.components.map(c=>{const p=pop[c.id]; return `<tr><td>${esc(c.name)}</td><td>${c.weight}</td><td>${p.scoredMembers}</td><td>${p.missingMembers}</td></tr>`;}).join('')}
</tbody></table>
<p class="muted">Council attendance, vote presence, and whether a member newsletter is on file come from the files this site already publishes. Online engagement is scored only when a post file is a complete lookback (<code>fetchStatus</code> of ok). Decency needs that same file and at least ${P.decencyMinPosts} of the member's own posts. Community meetings and constituent replies have no data files yet, so they are defined here and left out of every score.</p>
</section>

${config.components.map(compSection).join('')}

<section class="card">
<h2>The numbers in the formulas</h2>
<ul class="plain">
<li>Online posts and tone use the last <b>${P.onlineLookbackDays}</b> days. <b>${P.onlineFullCreditPosts}</b> posts is full credit for engagement.</li>
<li>Tone needs at least <b>${P.decencyMinPosts}</b> of the member's own posts. A post is "shouting" when it has at least <b>${P.shoutingMinLetters}</b> letters and at least <b>${Math.round(P.shoutingCapsRatio*100)}%</b> of those letters are uppercase.</li>
<li>A filed newsletter issue list uses the last <b>${P.newsletterLookbackDays}</b> days. <b>${P.newsletterFullCredit}</b> issues is full credit. Until that file exists, the score is 100 for a member-specific newsletter link and 0 when the hand check found none, or when the only link is the county-wide GovDelivery form.</li>
<li>Community meetings use the last <b>${P.communityLookbackDays}</b> days. <b>${P.communityFullCredit}</b> meetings marked attended is full credit.</li>
<li>Constituent replies use the last <b>${P.repliesLookbackDays}</b> days. <b>${P.repliesFullCredit}</b> replies is full credit.</li>
</ul>
<p>Full credit is the top of that component. Extra posts, issues, or meetings do not push it past 100, and they do not push the whole score past 100.</p>
<details><summary>Civility word list (${(config.civilityTerms||[]).length} terms)</summary>
<p class="muted">Matched as whole tokens, after lowercasing, with URLs stripped. The list is intentionally narrow. Criticism of a bill, a mayor, or a party is not on it.</p>
<p>${terms}</p></details>
</section>

<section class="card">
<h2>Worked example: ${esc(example.name)}</h2>
<p>${esc(example.seat)}. Gold segments in the bar have data. Gray segments are in the formula and were left out for this member.</p>
<div class="wbar" aria-hidden="true">${barHtml}</div>
<p class="formula">${esc(example.arithmetic)}</p>
<div class="scroll">${exampleTable(example)}</div>
<p><a href="../index.html?score=open#p${example.pid}">Open ${esc(example.name.split(' ')[0])}'s card with this breakdown</a></p>
</section>

<section class="card">
<h2>Every member</h2>
<p class="muted">Forty council members, plus the Vice Mayor, who presides and is on the map page. Click a name for the card.</p>
<div class="scroll"><table><thead><tr><th>Member</th><th>Seat</th><th>Score</th><th>Coverage</th><th>In the score</th><th>Left out</th></tr></thead><tbody>${table}</tbody></table></div>
</section>

<section class="card">
<h2>Where the data comes from</h2>
<ul class="plain">
<li>Meetings and votes: Metro's public Legistar records, the same files as the <a href="../">map page</a>. See that page for the coverage limit: before September 2026, Legistar often recorded only the divided votes.</li>
<li>Newsletters: the hand-checked links in <code>scripts/members_seed.py</code>. A later <code>data/newsletters/&lt;slug&gt;.json</code> with an <code>issues</code> list replaces the yes/no score for that member.</li>
<li>X handles and posts: <code>data/tweets/&lt;slug&gt;.json</code>. Handles were taken from a campaign site, a newsletter archive, Ballotpedia, or a profile whose bio names the seat, and then the profile was opened. Official nashville.gov member pages link the Council Office account (@NashvilleMCO), not personal accounts. Posts are scored only when <code>fetchStatus</code> is <code>ok</code>.</li>
<li>Community meetings and constituent replies: not collected. The optional file shapes are in the README.</li>
</ul>
</section>

<section class="card">
<h2>How often it updates</h2>
<p>${esc(config.updateCadence)}</p>
<p>Run it by hand with <code>python3 scripts/compute_score.py</code>. The window is the last N days ending on the UTC date of that run, so the same files can produce a new score after time passes.</p>
</section>

<section class="card">
<h2>Version ${esc(config.version)}</h2>
<ul class="plain">${changes}</ul>
</section>`;
})();
