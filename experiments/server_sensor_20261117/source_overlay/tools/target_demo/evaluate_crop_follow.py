"""Record evaluation-only simulator truth beside the real sensor runner."""
import dataclasses,json,os
from pathlib import Path
import numpy as np
from PIL import Image
from integration import carla_runner
from integration.carla_perception import CarlaPerceptionBridge
from integration.second_group_runtime import CanonicalRuntimeBridge
from tools.target_demo.capture_command_diagnostics import matrix,actor_truth

records=[]; command=[]; errors=[]; state={}; orig_acquire=CarlaPerceptionBridge.acquire; orig_submit=CanonicalRuntimeBridge.submit

def acquire(self,*args,**kwargs):
    sample=orig_acquire(self,*args,**kwargs)
    try:
        rgb=sample.rgb
        row={'frame':sample.frame.frame,'world_frame':self._world.get_snapshot().frame,
             'scene':dataclasses.asdict(sample.frame),'sources':dict(sample.source_by_field),
             'evaluation_only_actors':actor_truth(self),'ego_world_matrix':matrix(self._ego.get_transform()),
             'camera_world_matrix':matrix(rgb.transform),'camera_width':rgb.width,'camera_height':rgb.height,
             'fov':float(self._sensors.actors['rgb_front'].attributes.get('fov',100)),
             'detector_stats':getattr(self._detector,'last_stats',None)}
        records.append(row); state['sample']=sample; state['row']=row
    except Exception as exc: errors.append(f'{type(exc).__name__}: {exc}')
    return sample

def submit(self,envelope,scene,vehicle,**kwargs):
    try:
        sample=state['sample']; row=state['row']
        if scene.frame==row['frame']:
            rgb=sample.rgb
            command.append({'frame':scene.frame,'text':envelope.get('source_text'),'rgb':bytes(rgb.raw_data),'width':rgb.width,'height':rgb.height})
    except Exception as exc: errors.append(f'submit {type(exc).__name__}: {exc}')
    return orig_submit(self,envelope,scene,vehicle,**kwargs)

if __name__=='__main__':
    CarlaPerceptionBridge.acquire=acquire; CanonicalRuntimeBridge.submit=submit
    try: carla_runner.main()
    finally:
        out=Path(os.environ['FOLLOW_EVAL_DIR']);out.mkdir(parents=True,exist_ok=True)
        with (out/'truth_for_evaluation.jsonl').open('w') as f:
            for row in records: f.write(json.dumps(row,ensure_ascii=False)+'\n')
        if command:
            c=command[0];pixels=np.frombuffer(c['rgb'],dtype=np.uint8).reshape(c['height'],c['width'],4)
            Image.fromarray(pixels[:,:,[2,1,0]],mode='RGB').save(out/'command_rgb.png')
        (out/'observer_status.json').write_text(json.dumps({'frames':len(records),'commands':[{'frame':c['frame'],'text':c['text']} for c in command],'errors':errors},ensure_ascii=False,indent=2))
        print('EVALUATION_OBSERVER',len(records),'frames,',len(command),'commands,',len(errors),'errors',flush=True)
