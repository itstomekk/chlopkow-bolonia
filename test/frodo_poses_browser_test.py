"""Exercise every Frodo pose via actual renderer, preserving walk and a constant lick draw size.
Run ONLY through test/isolated_browser_runner.py (no public test arrivals).
"""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'gen/frodo/out'
BASE=os.environ.get('ARK_URL','http://127.0.0.1:8793/index.html')
meta=json.loads((ROOT/'docs/img/frodo_poses.json').read_text())
with sync_playwright() as p:
    browser=p.chromium.launch()
    page=browser.new_page(viewport={'width':1280,'height':720})
    errors=[]; missing=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('response',lambda r:missing.append((r.status,r.url)) if r.status>=400 else None)
    page.add_init_script("""window.__poseDraw=[];
    const original=CanvasRenderingContext2D.prototype.drawImage;
    CanvasRenderingContext2D.prototype.drawImage=function(img,...a){
      if(img.src && img.src.endsWith('/img/frodo_poses.png')){
        const m=this.getTransform();
        window.__poseDraw.push({frame:a[0]/32,size:a[6],at:[m.a*a[4]+m.e,m.d*a[5]+m.f],s:m.a});
        if(window.__poseDraw.length>100)window.__poseDraw.shift();
      }
      return original.call(this,img,...a);
    };""")
    page.goto(BASE+'?dog=frodo')
    page.wait_for_function('window.__game && window.ARK')
    page.keyboard.press('KeyN')
    page.locator('#player-name-input').fill('Test');page.keyboard.press('Enter')
    page.wait_for_function("__game.scene==='play'")
    page.wait_for_function('window.__poseDraw.length>0',timeout=20000)
    # Open ground and camera settling, not arbitrary random forest/house spawn.
    spot=page.evaluate("""() => {
      const A=ARK;
      for(let y=300;y<A.MAP.h-300;y+=70)for(let x=300;x<A.MAP.w-300;x+=70){
        if(A.terrainAt(x,y)!=='grass')continue;
        if([[-45,0],[45,0],[0,-60],[0,60]].every(([dx,dy])=>!A.blocked(x+dx,y+dy))&&!A.blocked(x,y)){
          A.teleport(x,y);return [x,y];
        }
      }
      throw Error('No clear grass spot');
    }""")
    page.wait_for_timeout(1500)
    checks=[]
    for action,seq in page.evaluate('Object.entries(CHLOPKOW_DOG.anims)'):
        for frame in dict.fromkeys(seq):
            index=meta['poses'].index(frame)
            t=seq.index(frame)/(page.evaluate('(CHLOPKOW_DOG.rates||{})["'+action+'"]||3'))+0.01
            page.evaluate("""({action,t})=>{const g=__game,F=g.FRODO;g.scene='end';F.x=g.P.x;F.y=g.P.y+42;
              F.dir='right';F.moving=false;F.action=action;F.idleAnim=t;window.__poseDraw=[];}""",{'action':action,'t':t})
            page.wait_for_function('(i)=>window.__poseDraw.some(d=>d.frame===i)',arg=index)
            drawn=page.evaluate('window.__poseDraw.at(-1)')
            assert drawn['frame']==index,(action,frame,drawn)
            checks.append((action,frame,drawn['size']))
    assert max(s for _,_,s in checks)-min(s for _,_,s in checks)<1e-9,'pose-dependent zoom'
    page.evaluate("""()=>{__game.scene='play';const F=__game.FRODO;F.routine='lick';F.routineT=99;F.action='lick';F.idleAnim=1;
      F.wander=0;F.wanderWait=99;F.chase=null;__game.P.dir='up';F.x=__game.P.x;F.y=__game.P.y+42;}""")
    page.wait_for_timeout(150)
    page.screenshot(path=str(OUT/'frodo_ingame.png'))
    assert not errors,errors
    assert not missing,missing
    print('FRODO runtime PASS:',len(checks),'action/frame combinations, all constant draw size; no page errors or HTTP errors')
    browser.close()
