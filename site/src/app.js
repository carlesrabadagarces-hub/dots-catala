(function(){
  var reduce=window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var $=function(id){return document.getElementById(id)};
  var css=function(v){return getComputedStyle(document.documentElement).getPropertyValue(v).trim()};
  var BASE="dots/";
  ensureSpriteStyles();
  var APP_URL="http://127.0.0.1:3000";
  [].forEach.call(document.querySelectorAll(".app-link"),function(a){a.href=APP_URL});
  function av(look,size,label){return dotSprite(look,size,label||"Dot",BASE)}

  var AG=[
    {n:"Aina",r:"Recepcionista",look:{body:"arch",tone:"pink",hat:"tophat",accessory:"bowtie"},p:[
      ["Tinc hora dijous?","Dijous tens visita a les 10:30 amb la doctora Puig. T'envio un recordatori el dimecres al vespre."],
      ["Puc canviar-la?","Tinc lliure divendres a les 9:00 o a les 12:15. Quina et va millor?"]]},
    {n:"Pau",r:"Cuiner",look:{body:"cube",tone:"yellow",hat:"chef",accessory:"mustache"},p:[
      ["Sopar ràpid amb ous","Truita de patata en 15 minuts: 4 ous, 2 patates fines i ceba opcional. Vols la recepta pas a pas?"],
      ["Sí, sense ceba","Talla les patates ben fines, fregeix-les 8 minuts, barreja-les amb els ous batuts i cuaja 3 minuts per banda."]]},
    {n:"Laia",r:"Traductora",look:{body:"blob",tone:"blue",glasses:"shades"},p:[
      ["Tradueix: bon profit","Anglès: enjoy your meal. Francès: bon appétit. Alemany: guten Appetit."],
      ["I en italià?","Buon appetito. Igual que en castellà: buen provecho."]]},
    {n:"Marc",r:"Comptable",look:{body:"cube",tone:"green",accessory:"tie"},p:[
      ["Quin IVA porta un llibre?","A Espanya els llibres porten el 4% d'IVA. Confirma-ho amb el teu gestor per a casos especials."],
      ["I un cafè al bar?","La restauració va al 10%."]]},
    {n:"Núria",r:"Tutora",look:{body:"blob",tone:"violet",hat:"graduation"},p:[
      ["Explica'm les fraccions","Una fracció és una part d'un tot. Si talles una pizza en 4 i te'n menges 1, has menjat 1/4."],
      ["Posa'm un exercici","Quant és 1/2 + 1/4? Pista: converteix-les a quarts."]]},
    {n:"Jordi",r:"Suport tècnic",look:{body:"arch",tone:"slate",hat:"hardhat",glasses:"shades"},p:[
      ["El wifi va lent","Reinicia el router 30 segons. Si continua igual, digues-me si va lent a tots els aparells o només a un."],
      ["Només al portàtil","Oblida la xarxa al portàtil i torna-la a connectar. Si no, actualitza el controlador de wifi."]]}
  ];

  /* ---------- Imatges i composició per al canvas ---------- */
  var IMG={};
  function loadImg(src){return IMG[src]||(IMG[src]=new Promise(function(res){var i=new Image();i.onload=function(){res(i)};i.onerror=function(){res(null)};i.src=BASE+src}))}
  function compose(look,F){
    var sp=spriteParts(look).parts.slice().sort(function(a,b){return a.z-b.z});
    return Promise.all(sp.map(function(p){return loadImg(p.src)})).then(function(imgs){
      var c=document.createElement("canvas");c.width=F;c.height=F;var x=c.getContext("2d");
      sp.forEach(function(p,i){if(imgs[i])x.drawImage(imgs[i],p.x*F,p.y*F,p.w*F,p.h*F)});return c});
  }
  function hiDPI(cv,w,h){var d=Math.min(window.devicePixelRatio||1,2);cv.width=w*d;cv.height=h*d;var c=cv.getContext("2d");c.setTransform(d,0,0,d,0,0);return c}

  /* ---------- Marquee ---------- */
  var USES=["Recepcionista","Cuiner","Traductor","Comptable","Tutor","Suport tècnic","Entrenador","Guia de viatges","Redactor","Bibliotecari"],
      COLS=["#ff4d7d","#ffc21a","#2f7bff","#19c3a6","#7a4cf0","#ff8a3d"],mh="";
  for(var k=0;k<2;k++)USES.forEach(function(u,i){mh+='<span style="--dc:'+COLS[i%6]+'">'+u+'</span>'});
  $("track").innerHTML=mh;

  /* ---------- Camp de Dots (hero) ---------- */
  var stage=$("stage"),cv=$("cv"),ctx=cv.getContext("2d"),hero=$("hero"),hv=$("hv"),reel=$("reel");
  var W=0,H=0,mouse={x:0,y:0,in:false},dots=[],bubbles=[],last=0,nextTalk=1400,tick=0,colors={};
  var CHAT=[
    [[0,"Algú té la reserva de dijous?"],[1,"Sí, a les 21:00 per a quatre."]],
    [[2,"Com es diu \"bon profit\" en anglès?"],[4,"Enjoy your meal. Ho practiques?"]],
    [[3,"Falta la factura del trimestre."],[0,"L'envio ara mateix."]],
    [[5,"Reinicia el router i em dius."],[1,"Fet. Ja va més ràpid."]],
    [[4,"Repassem les fraccions?"],[2,"Endavant, 1/2 + 1/4?"]]
  ];
  var SOLO=["Hola!","Què necessites?","Sóc aquí.","Escriu-me per WhatsApp.","Tinc idees."];
  function zone(r){return{x:W/2,y:H/2-6,w:Math.min(W*.5,340)+r,h:(W<560?235:215)+r}}
  function free(R,top){var x,y,n=0,z;do{x=R+Math.random()*(W-2*R);y=(top||R)+Math.random()*(H-2*R-(top||0));z=zone(R);n++}while(n<60&&Math.abs(x-z.x)<z.w&&Math.abs(y-z.y)<z.h);return[x,y]}
  function pick(a){return a[Math.floor(Math.random()*a.length)]}
  function layout(){
    var r=stage.getBoundingClientRect();W=r.width;H=r.height;cv.style.width=W+"px";cv.style.height=H+"px";ctx=hiDPI(cv,W,H);
    if(!dots.length){
      var small=W<500;
      AG.forEach(function(a,i){var R=(small?26:34)+(i%3)*4,p0=free(R,R*2.4+24);
        var d={a:a,i:i,big:true,r:R,x:p0[0],y:p0[1],vx:(Math.random()-.5)*.8,vy:(Math.random()-.5)*.8,sq:0,walk:Math.random()*6,comp:null,F:Math.round(R*3.9*2)};
        dots.push(d);compose(a.look,d.F).then(function(c){d.comp=c})});
      var CN=small?20:36;
      for(var q=0;q<CN;q++){var R2=(small?8:10)+Math.random()*(small?6:8),p1=free(R2,R2*1.7+12),lk={body:pick(BODIES),tone:pick(TONES)};
        if(Math.random()<.3)lk.hat=pick(["crown","party","flower","chef","hardhat","tophat"]);
        var d2={a:{n:""},i:100+q,big:false,r:R2,x:p1[0],y:p1[1],vx:(Math.random()-.5)*1.1,vy:(Math.random()-.5)*1.1,sq:0,walk:Math.random()*6,comp:null,F:Math.round(R2*3.9*2)};
        dots.push(d2);(function(dd,l){compose(l,dd.F).then(function(c){dd.comp=c})})(d2,lk)}
    }
    dots.forEach(function(d){d.top=d.big?d.r*2.4+24:d.r*1.7+12;d.x=Math.min(Math.max(d.x,d.r),W-d.r);d.y=Math.min(Math.max(d.y,d.top),H-d.r-14)});
    if(reduce)draw();
  }
  function say(i,text,ms){bubbles=bubbles.filter(function(b){return b.d!==i});bubbles.push({d:i,t:text,life:ms||2800});if(dots[i])dots[i].sq=.12}
  function talk(){
    var s=pick(CHAT);say(s[0][0],s[0][1],2900);setTimeout(function(){say(s[1][0],s[1][1],2900)},1500);
  }
  function step(dt){
    var k=dt/16.7;
    dots.forEach(function(d,i){
      for(var j=i+1;j<dots.length;j++){var o=dots[j],dx=o.x-d.x,dy=o.y-d.y,m=d.r+o.r+18,q=dx*dx+dy*dy;
        if(q<m*m&&q>.01){var l=Math.sqrt(q),f=(m-l)*.03*k;d.vx-=dx/l*f;d.vy-=dy/l*f;o.vx+=dx/l*f;o.vy+=dy/l*f}}
      if(mouse.in){var mx=d.x-mouse.x,my=d.y-mouse.y,md=Math.sqrt(mx*mx+my*my);
        if(md<150&&md>1){d.vx+=mx/md*.11*k;d.vy+=my/md*.11*k}}
      var z=zone(d.r),ddx=d.x-z.x,ddy=d.y-z.y;
      if(Math.abs(ddx)<z.w&&Math.abs(ddy)<z.h){if(z.h-Math.abs(ddy)<z.w-Math.abs(ddx)){d.vy+=(ddy>=0?1:-1)*.25*k;d.y+=(ddy>=0?1:-1)*2*k}else{d.vx+=(ddx>=0?1:-1)*.25*k;d.x+=(ddx>=0?1:-1)*2*k}}
      d.vx*=.994;d.vy*=.994;var sp=Math.hypot(d.vx,d.vy);if(sp<.22){d.vx+=(Math.random()-.5)*.05;d.vy+=(Math.random()-.5)*.05}if(sp>1.6){d.vx*=.95;d.vy*=.95}
      d.x+=d.vx*k;d.y+=d.vy*k;d.sq*=.9;d.walk+=Math.hypot(d.vx,d.vy)*.32*k;
      if(d.x<d.r){d.x=d.r;d.vx=Math.abs(d.vx);d.sq=.06}if(d.x>W-d.r){d.x=W-d.r;d.vx=-Math.abs(d.vx);d.sq=.06}
      if(d.y<d.top){d.y=d.top;d.vy=Math.abs(d.vy);d.sq=.06}if(d.y>H-d.r-14){d.y=H-d.r-14;d.vy=-Math.abs(d.vy);d.sq=.06}
    });
    bubbles.forEach(function(b){b.life-=dt});bubbles=bubbles.filter(function(b){return b.life>0});
  }
  function rr(x,y,w,h,r){ctx.beginPath();ctx.moveTo(x+r,y);ctx.arcTo(x+w,y,x+w,y+h,r);ctx.arcTo(x+w,y+h,x,y+h,r);ctx.arcTo(x,y+h,x,y,r);ctx.arcTo(x,y,x+w,y,r);ctx.closePath()}
  function draw(){
    if(tick%40===0){colors.fg=css("--fg");colors.bg=css("--bg");colors.line=css("--line")}
    tick++;ctx.clearRect(0,0,W,H);
    var talking=bubbles.map(function(b){return b.d});
    dots.slice().sort(function(p,q){return (p.big-q.big)||(p.y-q.y)}).forEach(function(d){
      if(!d.comp)return;
      var spd=Math.min(1,Math.hypot(d.vx,d.vy)/1.0),feet=d.y+d.r*1.05,F=d.F/2;
      var sh=ctx.createRadialGradient(d.x,feet,0,d.x,feet,d.r*1.05);sh.addColorStop(0,"rgba(0,0,0,.22)");sh.addColorStop(1,"rgba(0,0,0,0)");
      ctx.save();ctx.translate(d.x,feet);ctx.scale(1,.2);ctx.translate(-d.x,-feet);ctx.fillStyle=sh;ctx.beginPath();ctx.arc(d.x,feet,d.r*1.05,0,7);ctx.fill();ctx.restore();
      var sp=talking.indexOf(d.i)>-1,pulse=sp?Math.sin(tick/3)*.04:0,hop=Math.abs(Math.sin(d.walk))*d.r*.16*spd;
      ctx.save();ctx.translate(d.x,feet-hop);ctx.rotate(Math.sin(d.walk)*.07*spd+d.vx*.03);
      ctx.scale(1+d.sq+pulse,1-d.sq-pulse);
      ctx.drawImage(d.comp,-F/2,-F*.95,F,F);ctx.restore();
      if(d.big){
        ctx.font="500 10px "+getComputedStyle(document.body).getPropertyValue("--mono");ctx.textAlign="center";ctx.fillStyle=colors.fg;ctx.globalAlpha=.6;
        ctx.fillText(d.a.n.toUpperCase().split("").join(String.fromCharCode(8202)),d.x,feet+16);ctx.globalAlpha=1}
    });
    ctx.font="500 13px "+getComputedStyle(document.body).fontFamily;ctx.textAlign="left";
    bubbles.forEach(function(b){
      var d=dots[b.d],words=b.t.split(" "),lines=[],ln="";
      words.forEach(function(w){var t=ln?ln+" "+w:w;if(ctx.measureText(t).width>150&&ln){lines.push(ln);ln=w}else ln=t});lines.push(ln);
      var bw=Math.min(180,Math.max.apply(null,lines.map(function(l){return ctx.measureText(l).width}))+24),bh=lines.length*17+16,
          bx=Math.min(Math.max(d.x-bw/2,8),W-bw-8),by=d.y-d.r*2.7-bh;if(by<6)by=6;
      var fade=Math.min(1,b.life/300),grow=Math.min(1,(2900-b.life)/180+.4);ctx.globalAlpha=fade;
      ctx.save();ctx.translate(bx+bw/2,by+bh);ctx.scale(grow,grow);ctx.translate(-(bx+bw/2),-(by+bh));
      ctx.fillStyle=colors.fg;rr(bx,by,bw,bh,15);ctx.fill();
      ctx.fillStyle=colors.bg;lines.forEach(function(l,i){ctx.fillText(l,bx+12,by+20+i*17)});ctx.restore();ctx.globalAlpha=1;
    });
  }
  function frame(t){
    var dt=Math.min(t-last,50);last=t;
    nextTalk-=dt;if(nextTalk<=0){talk();nextTalk=4200+Math.random()*1800}
    step(dt);draw();requestAnimationFrame(frame);
  }
  layout();new ResizeObserver(layout).observe(stage);
  function pos(e){var r=stage.getBoundingClientRect();mouse.x=e.clientX-r.left;mouse.y=e.clientY-r.top}
  hero.addEventListener("pointermove",function(e){pos(e);mouse.in=true});
  hero.addEventListener("pointerleave",function(){mouse.in=false});
  hero.addEventListener("pointerdown",function(e){pos(e);
    var hit=dots.filter(function(d){return d.big&&Math.hypot(d.x-mouse.x,d.y-mouse.y)<d.r*1.6})[0];
    if(hit){say(hit.i,pick(SOLO),2400);hit.vx+=(Math.random()-.5)*3;hit.vy-=2.5;hit.sq=.16}});
  stage.addEventListener("keydown",function(e){if(e.key==="Enter"||e.key===" "){e.preventDefault();talk()}});
  if(reduce){setTimeout(function(){talk();draw()},600)}else requestAnimationFrame(frame);

  /* ---------- Vídeo ---------- */
  var showReel=function(){if(!reel.hidden)return;reel.hidden=false};
  hv.addEventListener("loadeddata",showReel);hv.addEventListener("loadedmetadata",showReel);if(hv.readyState>=1)showReel();
  new IntersectionObserver(function(es){es.forEach(function(en){if(en.isIntersecting){var p=hv.play();if(p&&p.catch)p.catch(function(){})}else hv.pause()})},{threshold:.4}).observe(hv);

  /* ---------- Demo de mòbil ---------- */
  var tabs=$("tabs"),msgs=$("msgs"),chips=$("chips"),pav=$("pav"),pname=$("pname"),cur=0,busy=false,timer=null;
  AG.forEach(function(a,i){
    var b=document.createElement("button");b.className="tab";b.type="button";b.setAttribute("role","tab");
    b.innerHTML='<span class="av">'+av(a.look,62,a.n)+'</span><span><b>'+a.n+'</b><span class="r">'+a.r+'</span></span>';
    tabs.appendChild(b);attachLife(b.firstChild);b.onclick=function(){select(i)};
  });
  var pavLife=attachLife(pav);
  function hm(){var d=new Date();return ("0"+d.getHours()).slice(-2)+":"+("0"+d.getMinutes()).slice(-2)}
  function add(t,cls){var d=document.createElement("div");d.className="m "+(cls||"");d.appendChild(document.createTextNode(t));
    if(cls!=="typing"){var tm=document.createElement("time");tm.textContent=hm();d.appendChild(tm)}
    msgs.appendChild(d);msgs.scrollTop=msgs.scrollHeight;return d}
  function select(i){
    clearTimeout(timer);busy=false;cur=i;var a=AG[i];
    [].forEach.call(tabs.children,function(t,j){t.setAttribute("aria-selected",j===i)});
    pav.innerHTML=av(a.look,46,a.n);pav.dataset.state="happy";setTimeout(function(){pav.dataset.state="idle"},600);
    pname.textContent=a.n;msgs.innerHTML="";
    add("Hola! Sóc "+a.n+", el teu agent de "+a.r.toLowerCase()+". En què et puc ajudar?");
    chips.innerHTML="";
    a.p.forEach(function(p,k){var c=document.createElement("button");c.type="button";c.className="chip";c.textContent=p[0];c.onclick=function(){ask(k,c)};chips.appendChild(c)});
  }
  function ask(k,chip){
    if(busy)return;busy=true;chip.disabled=true;var p=AG[cur].p[k];
    add(p[0],"out");var t=add("···","typing");pav.dataset.state="thinking";
    timer=setTimeout(function(){t.remove();pav.dataset.state="talking";add(p[1]);busy=false;setTimeout(function(){pav.dataset.state="idle"},1400)},reduce?0:1000);
  }
  select(0);

  /* ---------- Flux ---------- */
  var FLOW=[{body:"arch",tone:"green",hat:"antenna"},{body:"blob",tone:"blue",hat:"party"},{body:"cube",tone:"yellow",hat:"hardhat"},{body:"arch",tone:"pink",hat:"crown"},{body:"blob",tone:"violet",hat:"wizard"}];
  [].slice.call(document.querySelectorAll("#flow .node")).forEach(function(n,i){var h=n.querySelector(".nv");h.innerHTML=av(FLOW[i],110,"");attachLife(h)});
  var flow=$("flow"),pks=[1,2,3].map(function(n){return $("pk"+n)});
  function packets(t){
    if(flow.offsetParent&&getComputedStyle(pks[0]).display!=="none"){
      var w=flow.clientWidth,x0=w*.1,x1=w*.9;
      pks.forEach(function(p,i){var ph=((t/3600)+i/3)%1,fwd=ph<.5,q=fwd?ph*2:(1-ph)*2,c=fwd?css("--c-amber"):css("--c-green");
        p.style.opacity=1;p.style.left=(x0+(x1-x0)*q-6)+"px";p.style.background=c;p.style.boxShadow="0 0 16px "+c});
    }
    if(!reduce)requestAnimationFrame(packets);
  }

  /* ---------- Scroll ---------- */
  var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){e.target.classList.add("in");io.unobserve(e.target)}})},{threshold:.08});
  [].forEach.call(document.querySelectorAll(".rv"),function(el){io.observe(el)});
  var nb=$("navbar");
  window.addEventListener("scroll",function(){nb.classList.toggle("stuck",scrollY>10)},{passive:true});

  /* ---------- Final: el Dot salta, aterra i fa l'ullet ---------- */
  (function(){
    var fc=$("fcv"),c=null,FW=0,FH=0,dot=null,parts=[],running=false,started=false,tk=0,last=0,comp=null,skin="#ffc21a",bits=[];
    var FL={body:"arch",tone:"pink",hat:"crown"},FS=360;
    compose(FL,FS*2).then(function(cc){comp=cc;
      var g=spriteLayout(FL),x=cc.getContext("2d"),ex=g.fx(g.B.eyeL)*cc.width,ey=g.eyeY*cc.height,s;
      try{s=x.getImageData(Math.round(ex-cc.width*.03),Math.round(ey),1,1).data;skin="rgb("+s[0]+","+s[1]+","+s[2]+")"}catch(e){skin=TONE_COLORS.pink}
      comp.ex=ex;comp.ey=ey});
    for(var i=0;i<10;i++)(function(){var lk={body:pick(BODIES),tone:pick(TONES)};compose(lk,90).then(function(cc){bits.push(cc)})})();
    function fl(){var r=fc.getBoundingClientRect();FW=r.width;FH=r.height;c=hiDPI(fc,FW,FH);if(dot){dot.r=Math.min(72,FH*.16);dot.gy=FH-dot.r*.6}}
    function init(){dot={x:0,y:-300,vy:0,sq:0,wink:0,winkT:-1,hop:0,r:90,gy:0,settled:false,at:0};fl();dot.y=-dot.r*4}
    function burst(){for(var i=0;i<26;i++){var a=Math.random()*Math.PI*2,sp=3+Math.random()*7;
      parts.push({x:dot.x,y:dot.y-dot.r,vx:Math.cos(a)*sp,vy:Math.sin(a)*sp-6,rot:Math.random()*6,vr:(Math.random()-.5)*.3,life:1,i:i%10,s:30+Math.random()*26})}}
    function doWink(){dot.winkT=0}
    function jump(v){dot.vy=-(v||16);dot.settled=false;dot.hop=1}
    function step(dt){
      var k=dt/16.7;dot.x=FW/2;
      if(!dot.settled){dot.vy+=.95*k;dot.y+=dot.vy*k;
        if(dot.y>=dot.gy){dot.y=dot.gy;if(Math.abs(dot.vy)>3.2){dot.sq=Math.min(.3,Math.abs(dot.vy)*.02);dot.vy=-dot.vy*.5}else{dot.vy=0;dot.settled=true;dot.sq=.18;dot.at=tk;if(!dot.hop)dot.winkT=-40;dot.hop=0}}
        else dot.sq=Math.max(-.16,-Math.abs(dot.vy)*.011)}
      else dot.sq*=.86;
      if(dot.winkT>=0){dot.winkT+=k/38;if(dot.winkT>=1){dot.winkT=-1;dot.wink=0}else dot.wink=Math.sin(Math.PI*dot.winkT)}
      else if(dot.winkT<-1){dot.winkT+=k;if(dot.winkT>=-1)dot.winkT=0}
      else if(dot.settled&&tk-dot.at>260&&tk%260===0)doWink();
      parts.forEach(function(p){p.vy+=.35*k;p.x+=p.vx*k;p.y+=p.vy*k;p.rot+=p.vr*k;p.life-=.012*k});parts=parts.filter(function(p){return p.life>0&&p.y<FH+60});
    }
    function draw(){
      c.clearRect(0,0,FW,FH);
      if(!comp)return;
      var F=dot.r*5.2,feet=dot.y+dot.r*.2,sh=Math.max(.25,1-(dot.gy-dot.y)/(FH*.9));
      c.fillStyle="rgba(0,0,0,"+(.18*sh)+")";c.beginPath();c.ellipse(dot.x,dot.gy+dot.r*.22,dot.r*1.05*sh,dot.r*.17*sh,0,0,7);c.fill();
      parts.forEach(function(p){var b=bits[p.i%Math.max(1,bits.length)];if(!b)return;c.save();c.globalAlpha=Math.max(0,p.life);c.translate(p.x,p.y);c.rotate(p.rot);c.drawImage(b,-p.s/2,-p.s/2,p.s,p.s);c.restore()});
      c.save();c.translate(dot.x,feet);c.scale(1+dot.sq,1-dot.sq);
      c.drawImage(comp,-F/2,-F*.95,F,F);
      if(dot.wink>.35){var k=F/comp.width,x=-F/2+comp.ex*k,y=-F*.95+comp.ey*k;
        c.fillStyle=skin;c.beginPath();c.ellipse(x,y,F*.026,F*.04,0,0,7);c.fill();
        c.strokeStyle="#14171c";c.lineWidth=Math.max(2.5,F*.012);c.lineCap="round";c.beginPath();c.arc(x,y+F*.012,F*.024,Math.PI*1.12,Math.PI*1.88);c.stroke()}
      c.restore();
    }
    function frame(t){if(!running)return;var dt=Math.min(t-last,50);last=t;tk++;step(dt);draw();requestAnimationFrame(frame)}
    function run(){if(!running){running=true;last=performance.now();requestAnimationFrame(frame)}}
    fc.addEventListener("pointerdown",function(e){
      if(!dot||(!dot.settled&&dot.y<0))return;
      var r=fc.getBoundingClientRect(),x=e.clientX-r.left,y=e.clientY-r.top;
      if(Math.hypot(x-dot.x,y-(dot.y-dot.r*.8))<dot.r*1.7){doWink();burst();if(dot.settled)jump(14)}});
    fc.addEventListener("pointermove",function(e){var r=fc.getBoundingClientRect();fc.style.cursor=dot&&Math.hypot(e.clientX-r.left-dot.x,e.clientY-r.top-(dot.y-dot.r*.8))<dot.r*1.7?"pointer":"default"});
    new IntersectionObserver(function(es){es.forEach(function(en){
      if(en.isIntersecting){if(!started){started=true;init();if(reduce){dot.y=dot.gy;dot.settled=true;dot.wink=1;setTimeout(draw,800)}else run()}else if(!reduce)run()}else running=false})},{threshold:.35}).observe(fc);
    new ResizeObserver(function(){if(started){fl();if(reduce)draw()}}).observe(fc);
  })();

  /* ---------- Catàleg ---------- */
  (function(){
    var raw=$("catalog-data");if(!raw)return;
    var data;try{data=JSON.parse(raw.textContent)}catch(e){return}
    if(!data.agents.length){$("cataleg").hidden=true;return}
    var grid=$("cat-grid"),chipsEl=$("cat-chips"),qi=$("cat-q"),more=$("cat-more"),cnt=$("cat-count"),sec="",limit=12;
    function norm(t){return t.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g,"")}
    function chip(id,label,n){var b=document.createElement("button");b.type="button";b.className="role";b.setAttribute("aria-pressed",id===sec);
      b.textContent=label+(n?" "+n:"");b.onclick=function(){sec=id;limit=12;render();[].forEach.call(chipsEl.children,function(c){c.setAttribute("aria-pressed",c===b)})};chipsEl.appendChild(b)}
    chip("","Tots",data.agents.length);data.sectors.forEach(function(s){chip(s.id,s.name,s.count)});
    function render(){
      var q=norm(qi.value.trim()),list=data.agents.filter(function(a){return (!sec||a.sector===sec)&&(!q||norm(a.name+" "+a.role).indexOf(q)>-1)});
      cnt.textContent=list.length+" Dots";grid.innerHTML="";
      list.slice(0,limit).forEach(function(a){
        var d=document.createElement("div");d.className="cat-card";d.style.setProperty("--cc",a.color);
        var h=document.createElement("div");h.className="cat-head";
        var ic=document.createElement("span");ic.className="cat-ico";ic.innerHTML=av(a.look||{},64,a.name);
        var t=document.createElement("div"),b=document.createElement("b"),sm=document.createElement("small");b.textContent=a.name;sm.textContent=(data.sectors.filter(function(s){return s.id===a.sector})[0]||{}).name||"";t.appendChild(b);t.appendChild(sm);
        h.appendChild(ic);h.appendChild(t);
        var p=document.createElement("p");p.textContent=a.role;
        var ask=document.createElement("div");ask.className="cat-ask";ask.textContent="“"+a.starters[0]+"”";
        d.appendChild(h);d.appendChild(p);d.appendChild(ask);grid.appendChild(d)});
      more.hidden=list.length<=limit;
    }
    more.onclick=function(){limit+=12;render()};qi.oninput=function(){limit=12;render()};render();
  })();

  /* ---------- Company: un Dot que viu a la pàgina ---------- */
  (function(){
    var host=$("cdot"),bub=$("cbubble");if(!host||!bub)return;
    var looks=[{body:"blob",tone:"blue",hat:"tophat"},{body:"arch",tone:"yellow",hat:"hardhat"},{body:"cube",tone:"violet",hat:"wizard"},{body:"blob",tone:"teal",hat:"chef",accessory:"mustache"},{body:"arch",tone:"pink",hat:"crown",accessory:"bowtie"}];
    host.innerHTML=av(pick(looks),96,"Dot company");
    var talk=["Hola! Sóc un superDOTat.","Vols crear-ne un de teu?","Tinc un Dot per a cada ofici.","Fes-me un toc, que m'agrada.","Sempre al teu WhatsApp.","Mira el catàleg: en tenim 87."],hide=null,ti=0;
    function say(t){bub.textContent=t;bub.classList.add("on");clearTimeout(hide);hide=setTimeout(function(){bub.classList.remove("on")},3400)}
    attachLife(host,{onPoke:function(){say(talk[ti++%talk.length])}});
    setTimeout(function(){say(talk[0])},2600);
    var last=scrollY,lt=0;window.addEventListener("scroll",function(){var d=Math.abs(scrollY-last);last=scrollY;var n=Date.now();if(d>260&&n-lt>1800){lt=n;host.dataset.state="happy";setTimeout(function(){if(host.dataset.state==="happy")host.dataset.state="idle"},600)}},{passive:true});
    setInterval(function(){if(host.dataset.state==="sleepy"){if(!bub.classList.contains("on"))say("zzz…")}},5000);
  })();

  if(reduce)packets(0);else requestAnimationFrame(packets);
})();
