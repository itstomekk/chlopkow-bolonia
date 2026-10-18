"""Frodo complete behaviour assets: palette consistency, frame bounds, lick colour and registry references."""
import json
from pathlib import Path
import subprocess
import unittest
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]

class FrodoPoses(unittest.TestCase):
    def test_manifest_and_all_behaviours(self):
        meta=json.loads((ROOT/'docs/img/frodo_poses.json').read_text())
        im=Image.open(ROOT/'docs/img/frodo_poses.png').convert('RGBA')
        self.assertEqual(len(meta['poses']),49)
        self.assertEqual(im.size,(49*32,32))
        expected={'sit','pant','scratch','sniff','lie','lick','yawn','tilt','shake','bark','howl','dig','belly','run','jump','beg','wag','sleep','stretch','lickpaw','playbow'}
        self.assertTrue(expected <= set(meta['anims']))
        data=np.asarray(im).astype(np.int32)
        self.assertTrue(set(np.unique(data[...,3])) <= {0,255})
        rgb=data[data[...,3]>0,:3]
        self.assertLessEqual(len(np.unique(rgb,axis=0)),27)
        self.assertFalse(((rgb[:,0]>160)&(rgb[:,2]>160)&(rgb[:,1]<100)).any())
        frames={n:data[:,i*32:(i+1)*32] for i,n in enumerate(meta['poses'])}
        for n,a in frames.items():
            with self.subTest(pose=n):
                self.assertTrue(a[...,3].any())
                self.assertFalse(a[0,:,3].any())
                self.assertFalse(a[-1,:,3].any())
                if n.startswith(('lick','pant','yawn','tilt')):
                    c=a[a[...,3]>0,:3]
                    tan=(c[:,0]>c[:,2]+35)&(c[:,0]>130)&(c[:,1]>70)
                    self.assertGreaterEqual(int(tan.sum()),12, 'tan markings vanished')
        for action,seq in meta['anims'].items():
            self.assertTrue(set(seq)<=frames.keys(),action)
            unique=list(dict.fromkeys(seq))
            for left,right in zip(unique,unique[1:]):
                self.assertGreater(int(np.any(frames[left]!=frames[right],axis=2).sum()),3,action)

    def test_original_walk_unchanged(self):
        current=(ROOT/'docs/img/frodo.png').read_bytes()
        before=subprocess.check_output(['git','show','HEAD:docs/img/frodo.png'],cwd=ROOT)
        self.assertEqual(current,before)

    def test_runtime_uses_complete_poses(self):
        script="""const fs=require('fs'),vm=require('vm'); const window={};
        const localStorage={getItem(){return null},setItem(){}};
        vm.runInNewContext(fs.readFileSync('docs/js/dogs.js','utf8'),{window,localStorage,location:{search:''},URLSearchParams});
        const d=window.CHLOPKOW_DOGS.frodo;
        if(d.poses!=='img/frodo_poses.png') throw Error('old dark pose strip still active');
        const m=JSON.parse(fs.readFileSync('docs/'+d.poses.replace('.png','.json'),'utf8'));
        for(const a of d.routine) for(const n of d.anims[a]) if(!m.poses.includes(n))throw Error(n);
        for(const a of ['yawn','tilt','shake','wag','dig','sleep','belly','stretch']) if(!d.routine.includes(a))throw Error(a);
        console.log('Frodo registry complete');"""
        out=subprocess.check_output(['node','-e',script],cwd=ROOT,text=True)
        self.assertIn('registry complete',out)

if __name__=='__main__': unittest.main()
