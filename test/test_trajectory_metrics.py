import math
from tools.trajectory_metrics import Pose2, align_se2, evaluate

def test_alignment_removes_global_offset():
    gt=[Pose2(0,0,0),Pose2(1,0,0),Pose2(1,1,math.pi/2)]
    est=[Pose2(2,3,.4),Pose2(2+math.cos(.4),3+math.sin(.4),.4),Pose2(2+math.cos(.4)-math.sin(.4),3+math.sin(.4)+math.cos(.4),.4+math.pi/2)]
    aligned,_=align_se2(gt,est)
    assert max(math.hypot(a.x-b.x,a.y-b.y) for a,b in zip(gt,aligned))<1e-9

def test_metrics_zero_for_identical():
    rows=[(i*.1,Pose2(i*.1,0,0),Pose2(i*.1,0,0)) for i in range(30)]
    m=evaluate(rows,5)
    assert m['ate_rmse_m']<1e-12 and m['rpe_translation_rmse_m']<1e-12
