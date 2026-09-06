from tools.trajectory_metrics import Pose2
from tools.loop_closure_metrics import evaluate

def test_detects_return_loop():
    pts=[]
    xy=[(0,0),(1,0),(2,0),(2,1),(2,2),(1,2),(0,2),(0,1),(0,0)]
    k=0
    for a,b in zip(xy,xy[1:]):
        for j in range(10):
            t=j/10; x=a[0]+(b[0]-a[0])*t; y=a[1]+(b[1]-a[1])*t; p=Pose2(x,y,0); pts.append((k*.1,p,p)); k+=1
    pts.append((k*.1,Pose2(0,0,0),Pose2(0,0,0)))
    m=evaluate(pts,radius=.15,min_path=4,min_gap_samples=30)
    assert m['loop_events']>=1
