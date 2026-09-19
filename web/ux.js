/* Shared, testable UI state; opening and closing never removes conversation DOM. */
(function(root){
  function transition(state,event){
    if(event==='close'||event==='minimize')return 'closed';
    if(event==='open')return 'panel';
    if(event==='expand')return 'expanded';
    if(event==='restore'||event==='escape')return state==='expanded'?'panel':state;
    return state;
  }
  function preferred(storage,system){const v=storage.getItem('payflow-theme');return v==='dark'||v==='light'?v:(system?'dark':'light')}
  function storeTheme(storage,value){if(!['dark','light'].includes(value))throw Error('Invalid theme');storage.setItem('payflow-theme',value);return value}
  const api={transition,preferred,storeTheme};
  if(typeof module!=='undefined')module.exports=api;
  if(typeof document==='undefined')return;
  root.IncidentUX=api;
  try{document.documentElement.dataset.theme=preferred(localStorage,matchMedia('(prefers-color-scheme: dark)').matches)}catch{document.documentElement.dataset.theme='dark'}
  document.addEventListener('DOMContentLoaded',()=>{
    let mode='closed';const panel=document.querySelector('.assistant-panel');const launcher=document.querySelector('[data-assistant-open]');
    function setMode(event){mode=transition(mode,event);if(!panel)return;
      panel.dataset.mode=mode;panel.hidden=mode==='closed';panel.classList.remove('mobile-open');
      launcher.hidden=mode!=='closed';launcher.setAttribute('aria-expanded',String(mode!=='closed'));
      document.body.classList.toggle('copilot-expanded',mode==='expanded');
      const expand=panel.querySelector('[data-copilot-expand]');expand.textContent=mode==='expanded'?'▣':'□';expand.setAttribute('aria-label',mode==='expanded'?'Restore copilot':'Expand copilot');expand.title=expand.getAttribute('aria-label');
      if(mode==='closed')launcher.focus({preventScroll:true});else if(event==='open')panel.querySelector('[data-assistant-close]').focus({preventScroll:true});
    }
    function labels(){document.querySelectorAll('[data-theme-toggle]').forEach(b=>{const dark=document.documentElement.dataset.theme==='dark';b.textContent=dark?'☀ Light':'☾ Dark';b.setAttribute('aria-label',dark?'Switch to light theme':'Switch to dark theme')})}
    if(panel)setMode('close');labels();
    document.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;
      if(b.hasAttribute('data-assistant-open'))setMode('open');
      if(b.hasAttribute('data-assistant-close'))setMode('close');
      if(b.hasAttribute('data-copilot-minimize'))setMode('minimize');
      if(b.hasAttribute('data-copilot-expand'))setMode(mode==='expanded'?'restore':'expand');
      if(b.hasAttribute('data-theme-toggle')){const theme=document.documentElement.dataset.theme==='dark'?'light':'dark';try{storeTheme(localStorage,theme)}catch{}document.documentElement.dataset.theme=theme;labels()}
    });
    document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!document.querySelector('dialog[open]'))setMode('escape');
      if(e.key==='Tab'&&mode==='expanded'){const f=[...panel.querySelectorAll('button,input,a[href]')].filter(n=>!n.disabled&&n.getClientRects().length);if(e.shiftKey&&document.activeElement===f[0]){e.preventDefault();f.at(-1).focus()}else if(!e.shiftKey&&document.activeElement===f.at(-1)){e.preventDefault();f[0].focus()}}
    });
  });
})(typeof window!=='undefined'?window:globalThis);
