() => {
  // Tour gerenciado no navegador; sem dependência de seletores internos Gradio,
  // além das âncoras elem_id que controlamos e dos botões [role="tab"].
  const root = document.querySelector('gradio-app')?.shadowRoot || document;
  if (root.querySelector('#af-spotlight-root')) return;
  const ptSteps = [
    {id:'source',tab:'studio',title:'Escolha a origem',desc:'Cole um link de mídia que você tem permissão para baixar OU envie um arquivo do computador. Use somente um dos dois.'},
    {id:'formats',tab:'studio',title:'Escolha os formatos',desc:'MP3 é áudio comprimido; WAV preserva áudio sem compressão; MP4 mantém o vídeo. Você pode marcar mais de um.'},
    {id:'quality',tab:'studio',title:'Ajuste a qualidade',desc:'Escolha o bitrate do MP3 e o limite de resolução do MP4. Maior qualidade pode consumir mais armazenamento e tempo.'},
    {id:'ai',tab:'studio',title:'Use IA quando quiser',desc:'Separar voz cria instrumental e vocal. Transcrever gera texto e SRT. Desmarque as duas opções para apenas baixar ou converter.'},
    {id:'enqueue',tab:'studio',title:'Adicione à fila',desc:'Clique para incluir o trabalho. Os itens serão processados automaticamente, um de cada vez, sem travar a tela.'},
    {id:'queue',tab:'studio',title:'Acompanhe a fila',desc:'Veja quais itens aguardam, estão em execução ou terminaram. Selecione um para cancelar ou carregar o resultado. Pode adicionar vários arquivos.'},
    {id:'results',tab:'studio',title:'Ouça e baixe o resultado',desc:'Depois de concluir, selecione o trabalho na fila e clique em Ver resultado. Os players e arquivos aparecerão aqui.'},
    {id:'history',tab:'history',title:'Reabra seus trabalhos',desc:'Na aba Histórico estão os trabalhos anteriores, inclusive das versões antigas. Não precisa processar novamente.'},
    {id:'karaoke',tab:'karaoke',title:'Crie um vídeo de karaokê',desc:'Na aba Karaoke Video, escolha um MP4 e um instrumental do histórico ou envie ambos os arquivos.'},
    {id:'lyrics',tab:'karaoke',title:'Prepare a letra',desc:'Cole uma frase por linha, importe um SRT ou tente a sugestão por Whisper. O canto pode ser reconhecido incorretamente.'},
    {id:'timing',tab:'karaoke',title:'Revise tempos e texto',desc:'Ajuste início, fim e texto de cada frase. A linha do tempo mostra uma prévia do posicionamento; você pode corrigir antes da renderização.'},
    {id:'export',tab:'karaoke',title:'Escolha efeito e exporte',desc:'Defina a cor, posição, tamanho e destaque progressivo. Salve o projeto antes de exportar MP4; a renderização usa FFmpeg na CPU.'},
    {id:'shutdown',tab:'studio',title:'Encerre corretamente',desc:'Fechar a aba não encerra o servidor Python. Use Encerrar AudioForge quando acabar; o aplicativo bloqueia a saída durante trabalhos ativos.'}
  ];
  const enSteps = [
    {id:'source',tab:'studio',title:'Choose a source',desc:'Paste an authorized YouTube media URL OR upload a local file. Choose only one source.'},
    {id:'formats',tab:'studio',title:'Choose output formats',desc:'MP3 compresses audio, WAV keeps uncompressed audio and MP4 preserves video. You can select more than one.'},
    {id:'quality',tab:'studio',title:'Configure quality',desc:'Choose MP3 bitrate and MP4 maximum resolution. Higher quality may cost more CPU and storage.'},
    {id:'ai',tab:'studio',title:'Enable optional AI tools',desc:'Separate vocals and instrumental or transcribe audio to TXT/SRT. Uncheck AI if you only want media conversion.'},
    {id:'enqueue',tab:'studio',title:'Add to processing queue',desc:'Queue as many jobs as needed; only one runs at a time to protect your computer.'},
    {id:'queue',tab:'studio',title:'Monitor your jobs',desc:'View pending, running and complete jobs. Cancel a selected job or open its results.'},
    {id:'results',tab:'studio',title:'Preview outputs',desc:'Select a completed job and View result to play the audio/video or download its files.'},
    {id:'history',tab:'history',title:'Reopen older jobs',desc:'History contains completed jobs from previous versions as well.'},
    {id:'karaoke',tab:'karaoke',title:'Create a karaoke video',desc:'Open Karaoke Video and choose a processed MP4 + instrumental from History, or upload both.'},
    {id:'lyrics',tab:'karaoke',title:'Add lyrics',desc:'Paste one phrase per line, import an SRT or let Whisper suggest words and timing. Singing recognition is imperfect.'},
    {id:'timing',tab:'karaoke',title:'Edit phrase timing',desc:'Review and edit start/end times and lyrics. Use the timeline to see where phrases will appear.'},
    {id:'export',tab:'karaoke',title:'Save and render',desc:'Choose colors, subtitle position and approximate word-by-word highlighting. Save the project, then export to MP4.'},
    {id:'shutdown',tab:'studio',title:'Shut down safely',desc:'Closing the browser tab does not stop Python. Use Shut down AudioForge after your jobs finish.'}
  ];
  const initialLang = '__DEFAULT_LANGUAGE__';
  function language(){
    const field=root.querySelector('#af-ui-language input');
    const value=field?.value?.toLowerCase()||'';
    if(value.includes('english'))return 'en';
    if(value.includes('portugu'))return 'pt';
    try{return localStorage.getItem('audioforge-ui-language')||initialLang;}catch(_){return initialLang;}
  }
  const localText=(pt,en)=>language()==='en'?en:pt;
  const steps = ptSteps; // mutated in focusStep based on active locale
  function activeSteps(){return language()==='en'?enSteps:ptSteps;}
  let current=-1, focusBefore=null, transitionToken=0;
  const host=document.createElement('div'); host.id='af-spotlight-root';
  host.setAttribute('aria-live','polite');
  host.innerHTML=`<div class="af-shade" data-shade="top"></div><div class="af-shade" data-shade="left"></div><div class="af-shade" data-shade="right"></div><div class="af-shade" data-shade="bottom"></div>
    <div class="af-spotlight-ring" aria-hidden="true"></div>
    <aside class="af-flyout" role="dialog" aria-modal="true" aria-labelledby="af-tour-heading" tabindex="-1">
     <header class="af-flyout-top"><span class="af-tour-label">VISITA GUIADA • AUDIOFORGE</span><button type="button" class="af-tour-x" aria-label="Fechar tutorial">×</button></header>
     <div class="af-tour-progress" aria-hidden="true"><span></span></div>
     <div class="af-tour-step"></div><h2 id="af-tour-heading"></h2><p class="af-tour-details"></p>
     <footer class="af-tour-actions"><button type="button" class="af-tour-skip">Sair</button><span class="af-tour-key-help">← → para navegar</span><button type="button" class="af-tour-back">← Voltar</button><button type="button" class="af-tour-next">Próximo →</button></footer>
    </aside>`;
  // No Gradio sem shadow DOM, insira no BODY (Document aceita somente <html>).
  (root === document ? document.body : root).appendChild(host);
  const overlays = [...host.querySelectorAll('.af-shade')];
  const ring=host.querySelector('.af-spotlight-ring'); const flyout=host.querySelector('.af-flyout');
  const prev=host.querySelector('.af-tour-back'); const next=host.querySelector('.af-tour-next');
  function rects(r) {
    const gap=7, l=Math.max(0,r.left-gap), t=Math.max(0,r.top-gap);
    const rr=Math.min(innerWidth,r.right+gap), b=Math.min(innerHeight,r.bottom+gap),
      w=innerWidth, h=innerHeight;
    const vals=[[0,0,w,t],[0,t,l,Math.max(0,b-t)],[rr,t,Math.max(0,w-rr),Math.max(0,b-t)],[0,b,w,Math.max(0,h-b)]];
    overlays.forEach((el,i)=>Object.assign(el.style,{left:vals[i][0]+'px',top:vals[i][1]+'px',width:vals[i][2]+'px',height:vals[i][3]+'px'}));
    Object.assign(ring.style,{left:l+'px',top:t+'px',width:Math.max(0,rr-l)+'px',height:Math.max(0,b-t)+'px'});
    // Preferir ao lado; se não couber, acima/abaixo. Nunca fora da viewport.
    const cw=Math.min(360,w-24), ch=flyout.offsetHeight||275;
    let x,y;
    if (w-r.right >= cw+34) {x=r.right+18; y=r.top;}
    else if (r.left>=cw+34) {x=r.left-cw-18; y=r.top;}
    else if(h-r.bottom>=ch+24) {x=Math.max(12, Math.min(w-cw-12,r.left));y=r.bottom+16;}
    else {x=Math.max(12,Math.min(w-cw-12,r.left));y=r.top-ch-16;}
    x=Math.max(12,Math.min(w-cw-12,x));
    y=Math.max(12,Math.min(h-ch-12,y));
    Object.assign(flyout.style,{width:cw+'px',left:x+'px',top:y+'px'});
  }
  function reposition(){
    if(current<0) return;
    const target=root.querySelector('#af-guide-'+activeSteps()[current].id);
    if(target&&target.getClientRects().length) rects(target.getBoundingClientRect());
  }
  async function focusStep(n){
    if(n>=activeSteps().length){close(true);return;}
    if(n<0)return;
    current=n; const token=++transitionToken;
    host.classList.add('af-open');
    const step=activeSteps()[n];
    // Alterar aba antes de procurar o item; usa o texto visível do controle tab.
    const tab=[...root.querySelectorAll('[role="tab"]')].find(el=>
      (el.textContent||'').includes(step.tab==='history'?localText('Histórico','History'):(step.tab==='karaoke'?'Karaoke':localText('Estúdio','Studio'))));
    if(tab && tab.getAttribute('aria-selected')!=='true') tab.click();
    host.querySelector('.af-tour-step').textContent=`${localText('ETAPA','STEP')} ${n+1} ${localText('DE','OF')} ${activeSteps().length}`;
    host.querySelector('#af-tour-heading').textContent=step.title;
    host.querySelector('.af-tour-details').textContent=step.desc;
    host.querySelector('.af-tour-progress span').style.width=((n+1)/activeSteps().length*100)+'%';
    prev.disabled=n===0;
    next.textContent=n===activeSteps().length-1?localText('Concluir ✓','Finish ✓'):localText('Próximo →','Next →');
    host.querySelector('.af-tour-label').textContent=localText('VISITA GUIADA • AUDIOFORGE','GUIDED TOUR • AUDIOFORGE');
    prev.textContent=localText('← Voltar','← Back');
    host.querySelector('.af-tour-skip').textContent=localText('Sair','Skip');
    host.querySelector('.af-tour-key-help').textContent=localText('← → para navegar','← → to navigate');
    // Scroll the highlighted element into view.
    await new Promise(resolve=>setTimeout(resolve,110));
    if(token!==transitionToken)return;
    const target=root.querySelector('#af-guide-'+step.id);
    if(!target){close(false);return;}
    target.scrollIntoView({behavior:'smooth',block:'nearest',inline:'nearest'});
    await new Promise(resolve=>setTimeout(resolve,330));
    if(token!==transitionToken)return;
    reposition();next.focus({preventScroll:true});
  }
  function start(){
    focusBefore=root.activeElement||document.activeElement;
    focusStep(0);
  }
  function close(complete){
    ++transitionToken;current=-1;
    host.classList.remove('af-open');
    if(complete) try{localStorage.setItem('audioforge-tour-v0.4.0','seen');}catch(_){ }
    if(focusBefore?.focus)focusBefore.focus({preventScroll:true});
  }
  next.addEventListener('click',()=>focusStep(current+1));
  prev.addEventListener('click',()=>focusStep(current-1));
  host.querySelector('.af-tour-x').addEventListener('click',()=>close(true));
  host.querySelector('.af-tour-skip').addEventListener('click',()=>close(true));
  // O botão Gradio possui elem_id em um wrapper: delegação evita incompatibilidade.
  root.addEventListener('click',e=>{
    if(e.target.closest?.('#af-tour-launch'))setTimeout(start,0);
    if(e.target.closest?.('#af-ui-language'))setTimeout(()=>{
      try{localStorage.setItem('audioforge-ui-language',language());}catch(_){}
    },150);
  });
  root.addEventListener('change',e=>{
    if(e.target.closest?.('#af-ui-language')){
      try{localStorage.setItem('audioforge-ui-language',language());}catch(_){}
      if(current>=0)focusStep(current);
    }
  });
  document.addEventListener('keydown',e=>{
    if(current<0||e.altKey||e.ctrlKey||e.metaKey)return;
    const nodes=e.composedPath?.() || [e.target];
    if(nodes.some(node => ['textarea','input','select'].includes((node.tagName||'').toLowerCase()) || node.isContentEditable))return;
    if(e.key==='ArrowRight'){e.preventDefault();focusStep(current+1);}
    else if(e.key==='ArrowLeft'){e.preventDefault();focusStep(current-1);}
    else if(e.key==='Escape'){e.preventDefault();close(true);}
  });
  window.addEventListener('resize',reposition);
  document.addEventListener('scroll',reposition,true);
  const observer=new MutationObserver(()=>{if(current>=0)requestAnimationFrame(reposition)});
  observer.observe(root,{subtree:true,childList:true});
  setTimeout(()=>{let seen=false;try{seen=localStorage.getItem('audioforge-tour-v0.4.0')==='seen'}catch(_){ }
    if(!seen)start();},700);
}
