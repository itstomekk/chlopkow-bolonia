"""True 3D blockout of B2 (OSM way 993157706: 16.2 x 7.9 m, footprint yaw 2.6 deg CW).
Renders the barn at a chosen ground yaw with the game's fixed oblique camera: verticals stay vertical,
only the ground plane turns. Output is a geometry/structure guide for GPT Image, NOT a game sprite."""
import math,sys
import numpy as np
from PIL import Image,ImageDraw
L,W=16.2,7.9          # metres, from OSM footprint
WALL,RIDGE=2.6,4.3    # eave / ridge height, metres (low farm auxiliary, 1 level)
EL=math.radians(50)   # camera elevation: slight top-down 3/4
S=2*6                 # 2 px/m game scale, drawn x6 for a clear guide
LIGHT=np.array([-0.6,-0.5,0.62]); LIGHT/=np.linalg.norm(LIGHT)   # from west/upper-left (x east, y south, z up)

def render(yaw_deg,path):
    t=math.radians(yaw_deg); c,s=math.cos(t),math.sin(t)
    def P(x,y,z):                        # x along building length, y across, z up -> screen
        X=x*c-y*s; Y=x*s+y*c             # yaw clockwise on screen (y is south)
        return (X*S, (Y*math.sin(EL)-z*math.cos(EL))*S)
    def N(nx,ny,nz):
        X=nx*c-ny*s; Y=nx*s+ny*c; return np.array([X,Y,nz])
    hl,hw=L/2,W/2
    faces=[]   # (corners, normal, base colour)
    wall=(226,206,170); roof=(150,112,84)
    faces.append(([(-hl,hw,0),(hl,hw,0),(hl,hw,WALL),(-hl,hw,WALL)],N(0,1,0),wall))     # south long wall
    faces.append(([(-hl,-hw,0),(-hl,hw,0),(-hl,hw,WALL),(-hl,0,RIDGE),(-hl,-hw,WALL)],N(-1,0,0),wall))   # west gable
    faces.append(([(hl,hw,0),(hl,-hw,0),(hl,-hw,WALL),(hl,0,RIDGE),(hl,hw,WALL)],N(1,0,0),wall))        # east gable
    faces.append(([(-hl,hw,WALL),(hl,hw,WALL),(hl,0,RIDGE),(-hl,0,RIDGE)],N(0,0.8,0.6),roof))           # south roof plane
    faces.append(([(-hl,-hw,WALL),(hl,-hw,WALL),(hl,0,RIDGE),(-hl,0,RIDGE)],N(0,-0.8,0.6),roof))        # north roof plane
    faces.append(([(-hl,-hw,0),(hl,-hw,0),(hl,-hw,WALL),(-hl,-hw,WALL)],N(0,-1,0),wall))                # north wall (hidden)
    cam=np.array([0,math.cos(EL),math.sin(EL)])      # direction towards the camera (south, above)
    vis=[]
    for pts,n,col in faces:
        n=n/np.linalg.norm(n)
        if float(n@cam)>0.02:
            depth=np.mean([ (x*s+y*c) - z*0.0 for x,y,z in pts])
            k=0.55+0.45*max(0.0,float(n@LIGHT))
            vis.append((depth,pts,tuple(int(v*k) for v in col)))
    vis.sort(key=lambda v:-v[0])   # far first
    allp=[P(*p) for _,pts,_ in vis for p in pts]
    x0=min(p[0] for p in allp)-20; y0=min(p[1] for p in allp)-20
    x1=max(p[0] for p in allp)+20; y1=max(p[1] for p in allp)+20
    im=Image.new('RGB',(int(x1-x0),int(y1-y0)),(255,0,255)); d=ImageDraw.Draw(im)
    for _,pts,col in vis:
        d.polygon([(P(*p)[0]-x0,P(*p)[1]-y0) for p in pts],fill=col,outline=(40,28,24))
    im.save(path); return im.size

if __name__=='__main__':
    out=sys.argv[1]
    for name,yaw in [('yaw_02',2.6),('yaw_17',17.6),('yaw_32',32.6)]:
        print(name,render(yaw,f'{out}/blockout_{name}.png'))
