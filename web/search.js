export const fold = s => String(s??'').normalize('NFD').replace(/\p{Diacritic}/gu,'').toLowerCase();
export const DEFAULT_EXCLUDED_ARTISTS = ['Algis Kriščiūnas'];
export function dimensions(p,pair,f={}) {
 const order=f.order==='auto'?p.size_order:f.order;
 if(f.order==='auto'&&!['wh','hw','square'].includes(order))return null;
 return order==='hw'?[pair[1],pair[0]]:pair;
}
export function matchingSizes(p,f={}) {
 const low=k=>f[k]===''||f[k]==null?-Infinity:Number(f[k]);
 const high=k=>f[k]===''||f[k]==null?Infinity:Number(f[k]);
 return (p.sizes||[]).filter(([a,b])=>{
  if(f.order==='auto'){
   const pair=dimensions(p,[a,b],f);
   return pair?pair[0]>=low('wmin')&&pair[0]<=high('wmax')&&pair[1]>=low('hmin')&&pair[1]<=high('hmax'):false;
  }
  const fits=(w,h)=>w>=low('wmin')&&w<=high('wmax')&&h>=low('hmin')&&h<=high('hmax');
  return f.order==='hw'?fits(b,a):f.order==='either'?(fits(a,b)||fits(b,a)):fits(a,b);
 });
}
export function search(products,f={}) {
 const excluded=new Set((f.excludedArtists??DEFAULT_EXCLUDED_ARTISTS).map(name=>fold(name.trim())));
 const active=['wmin','wmax','hmin','hmax'].some(k=>f[k]!==''&&f[k]!=null);
 return products.filter(p=>!excluded.has(fold((p.artist||'').trim()))&&(f.kind!=='art'||p.is_artwork!==false)&&(!f.category||p.category===f.category)&&(!f.q||fold(`${p.title} ${p.artist}`).includes(fold(f.q)))&&(!f.artist||p.artist===f.artist)&&(!active||matchingSizes(p,f).length));
}
