import {search,matchingSizes,dimensions,fold,DEFAULT_EXCLUDED_ARTISTS} from './search.js';
const $=s=>document.querySelector(s), form=$('#filters');
let products=[],limit=48;
const params=new URLSearchParams(location.search);
for(const [key,value] of params) if(key!=='exclude'&&form.elements.namedItem(key)) form.elements.namedItem(key).value=value;
const initialExcluded=params.has('exclude')?params.getAll('exclude').filter(Boolean):DEFAULT_EXCLUDED_ARTISTS;
const money=new Intl.NumberFormat('lt-LT',{style:'currency',currency:'EUR'});
const text=(tag,content,cls)=>{const e=document.createElement(tag);e.textContent=content;if(cls)e.className=cls;return e};
function render(){
 const fields=new FormData(form),f=Object.fromEntries(fields);
 f.excludedArtists=fields.getAll('exclude');
 $('#excluded-count').textContent=f.excludedArtists.length;
 $('#excluded-names').textContent=f.excludedArtists.length?f.excludedArtists.join(', '):'No authors excluded';
 for(const k of ['w','h']){
  if(f[k+'min']!==''&&f[k+'max']!==''&&+f[k+'min']>+f[k+'max']){
   $('#error').textContent='Minimum must be less than or equal to maximum.';$('#grid').replaceChildren();$('#count').textContent='Check your ranges';$('#more').hidden=true;return;
  }
 }
 $('#error').textContent='';
 const query=new URLSearchParams([...fields].filter(([,v])=>v!==''));
 if(!f.excludedArtists.length)query.set('exclude','');
 try{history.replaceState(null,'',`${location.pathname}?${query}`)}catch{}
 const matches=search(products,f);
 const metric=p=>{const sizes=matchingSizes(p,f).map(pair=>dimensions(p,pair,f)).filter(Boolean);return sizes.length?Math.min(...sizes.map(([w,h])=>f.sort==='area'?w*h:f.sort==='width'?w:h)):Infinity};
 matches.sort((a,b)=>f.sort==='title'?a.title.localeCompare(b.title,'lt'):metric(a)-metric(b)||a.title.localeCompare(b.title,'lt'));
 $('#count').textContent=`${matches.length.toLocaleString()} ${matches.length===1?'work':'works'}`;
 $('#detail').textContent=`${products.length.toLocaleString()} indexed · ${f.order==='auto'?'automatic orientation':f.order==='hw'?'H × W labels':f.order==='either'?'either order':'W × H labels'}`;
 $('#grid').replaceChildren();
 if(!matches.length) $('#grid').append(text('div','No works fit these filters. Try widening the ranges or switching size-label order.','empty'));
 for(const p of matches.slice(0,limit)){
  const a=document.createElement('a');a.className='card';a.href=p.url;a.target='_blank';a.rel='noopener';
  const art=text('div','','art');
  if(p.image&&/^https:\/\/(www\.)?luxart\.com\//.test(p.image)){
   const img=document.createElement('img');img.src=p.image;img.alt=p.title;img.loading='lazy';img.referrerPolicy='no-referrer';
   img.onerror=()=>art.replaceChildren(text('span','Image unavailable','no-image'));art.append(img);
  } else art.append(text('span','Preview on Luxart ↗','no-image'));
  a.append(art,text('p',p.artist||'Luxart collection','artist'),text('h3',p.title));
  if(p.category)a.append(text('p',p.category,'unknown'));
  const sizes=text('div','','sizes');
  const unknownOrder=f.order==='auto'&&!['wh','hw','square'].includes(p.size_order);
  for(const pair of unknownOrder?p.sizes:matchingSizes(p,f)){
   const variant=(p.variants||[]).find(v=>v.size[0]===pair[0]&&v.size[1]===pair[1]);
   const shown=dimensions(p,pair,f)||pair;
   const chip=text('span',`${shown[0]} × ${shown[1]} cm${variant?.price!=null?' · '+money.format(variant.price):''}`,'chip');
   chip.title=variant?.label||'Original Luxart size label';sizes.append(chip);
  }
  if(unknownOrder&&p.sizes.length)sizes.append(text('span','Source sizes · orientation unverified','unknown'));
  if(!p.sizes.length)sizes.append(text('span','Size not indexed','unknown'));
  a.append(sizes,text('span','View on Luxart ↗','open'));$('#grid').append(a);
 }
 $('#more').hidden=matches.length<=limit;
}
form.addEventListener('input',()=>{limit=48;render()});form.addEventListener('submit',e=>e.preventDefault());
form.addEventListener('reset',()=>setTimeout(()=>{limit=48;render()},0));
$('#more').onclick=()=>{limit+=48;render()};
$('#include-all-authors').onclick=()=>{for(const checkbox of document.querySelectorAll('[name="exclude"]'))checkbox.checked=false;limit=48;render()};
$('#author-filter').addEventListener('input',event=>{const q=fold(event.target.value);for(const label of $('#excluded-options').children)label.hidden=!fold(label.textContent).includes(q)});
form.addEventListener('reset',()=>{for(const label of $('#excluded-options').children)label.hidden=false});
$('#example').onclick=()=>{for(const [k,v] of Object.entries({wmin:50,wmax:60,hmin:100,hmax:120}))form.elements.namedItem(k).value=v;limit=48;render()};
try{
 let data=globalThis.__CATALOG__;
 if(!data){const response=await fetch('/data/catalog.json',{cache:'no-store'});if(!response.ok)throw new Error(`Catalogue request failed (${response.status})`);data=await response.json()}
 products=data.products;
 for(const category of [...new Set(products.map(p=>p.category).filter(Boolean))].sort((a,b)=>a.localeCompare(b,'lt'))){const o=text('option',category);o.value=category;$('#category').append(o)}
 if(params.has('category'))$('#category').value=params.get('category');
 for(const artist of [...new Set(products.map(p=>p.artist).filter(Boolean))].sort((a,b)=>a.localeCompare(b,'lt'))){
  const o=text('option',artist);o.value=artist;$('#artist').append(o);
  const label=document.createElement('label'),checkbox=document.createElement('input');
  checkbox.type='checkbox';checkbox.name='exclude';checkbox.value=artist;
  checkbox.defaultChecked=DEFAULT_EXCLUDED_ARTISTS.includes(artist);
  checkbox.checked=initialExcluded.includes(artist);
  label.append(checkbox,document.createTextNode(artist));$('#excluded-options').append(label);
 }
 if(params.has('artist'))$('#artist').value=params.get('artist');
 $('#status').textContent=data.sample?'Sample only — your Du drugeliai example. Run the importer to search the full collection.':`${data.complete?'Import finished':'Partial import'} · ${products.length} works / ${data.discovered} discovered · ${data.failed?.length||0} failed · updated ${new Date(data.updated_at).toLocaleString()}. Reload after importing to pick up new data.`;
 render();
}catch(e){$('#status').textContent='Could not load catalogue. Start with: uv run python app.py';$('#error').textContent=e.message}
