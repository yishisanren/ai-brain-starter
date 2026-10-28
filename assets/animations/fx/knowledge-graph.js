(function(){
  window.HPX = window.HPX || {};
  window.HPX['knowledge-graph'] = function(el){
    const U = window.HPX._u;
    const k = U.canvas(el), ctx = k.ctx;
    const pal = U.palette(el);
    const tx = U.text(el, '#e7e7ef');
    // deck copy: labels are what lives in the brain
    const labels = ['项目','决定','假设','经验','偏好','更正','下一步','阻塞','STATUS','inbox',
      'Claude Code','Codex','Hermes','日结','汇总','周总结','开工','简报','确认','验收',
      '原话','根因','来源','交付物','技能','裁定','口径','边界'];
    const L = Math.max(90, k.w/5.6), R = Math.max(7, k.w/150), FS = Math.max(12, Math.round(k.w/48));
    const N = 28;
    // never settle: each node wanders slowly, so the graph keeps drifting for as long as the slide is open
    const WANDER = Math.max(0.15, k.w*0.0004);
    const nodes = Array.from({length:N}, (_,i) => ({
      x: U.rand(k.w*.2, k.w*.8), y: U.rand(k.h*.2, k.h*.8),
      vx: 0, vy: 0, label: labels[i%labels.length],
      p: U.rand(0, 6.28), q: U.rand(0, 6.28), s: U.rand(0.35, 0.75),
      c: pal[i%pal.length]
    }));
    const edges = [];
    const made = new Set();
    while (edges.length < 50){
      const a = (Math.random()*N)|0, b = (Math.random()*N)|0;
      if (a===b) continue;
      const key = a<b ? a+'-'+b : b+'-'+a;
      if (made.has(key)) continue;
      made.add(key); edges.push([a,b]);
    }
    const stop = U.loop((t) => {
      // physics
      for (let i=0;i<N;i++){
        for (let j=i+1;j<N;j++){
          const a=nodes[i], b=nodes[j];
          const dx=b.x-a.x, dy=b.y-a.y;
          let d2=dx*dx+dy*dy; if (d2<1) d2=1;
          const d=Math.sqrt(d2);
          const f=1600*(L/90)*(L/90)/d2;
          const fx=(dx/d)*f, fy=(dy/d)*f;
          a.vx-=fx; a.vy-=fy; b.vx+=fx; b.vy+=fy;
        }
      }
      for (const [i,j] of edges){
        const a=nodes[i], b=nodes[j];
        const dx=b.x-a.x, dy=b.y-a.y, d=Math.hypot(dx,dy)||1;
        const f=(d-L)*0.008;
        const fx=(dx/d)*f, fy=(dy/d)*f;
        a.vx+=fx; a.vy+=fy; b.vx-=fx; b.vy-=fy;
      }
      const cx=k.w/2, cy=k.h/2;
      for (const n of nodes){
        n.vx += (cx-n.x)*0.002;
        n.vy += (cy-n.y)*0.002;
        n.vx += Math.cos(t*n.s + n.p)*WANDER;
        n.vy += Math.sin(t*n.s*0.8 + n.q)*WANDER;
        // soft walls keep wandering nodes (and their labels) on the canvas
        const mx=k.w*0.06, my=k.h*0.06+FS*1.5;
        if (n.x<mx) n.vx+=(mx-n.x)*0.05; else if (n.x>k.w-mx) n.vx-=(n.x-(k.w-mx))*0.05;
        if (n.y<my) n.vy+=(my-n.y)*0.05; else if (n.y>k.h-my*0.6) n.vy-=(n.y-(k.h-my*0.6))*0.05;
        n.vx *= 0.85; n.vy *= 0.85;
        n.x += n.vx; n.y += n.vy;
      }
      ctx.clearRect(0,0,k.w,k.h);
      ctx.strokeStyle = U.css(el,'--kg-edge','rgba(200,190,230,0.22)'); ctx.lineWidth=1.2;
      for (const [i,j] of edges){
        const a=nodes[i], b=nodes[j];
        ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke();
      }
      ctx.font='500 '+FS+'px '+U.css(el,'--font-plain','system-ui,sans-serif'); ctx.textAlign='center'; ctx.textBaseline='middle';
      for (const n of nodes){
        ctx.fillStyle = n.c;
        ctx.shadowColor=n.c; ctx.shadowBlur=R*2.5; ctx.beginPath(); ctx.arc(n.x,n.y,R,0,Math.PI*2); ctx.fill(); ctx.shadowBlur=0;
        ctx.fillStyle = tx;
        ctx.fillText(n.label, n.x, n.y-R-FS*0.8);
      }
    });
    return { stop(){ stop(); k.destroy(); } };
  };
})();
