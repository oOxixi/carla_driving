import json
from pathlib import Path
root=Path.cwd(); out=root/'artifacts/runtime/new_scenarios_20261116'
def load(p):return json.loads((root/p).read_text())
def save(name,s):
 s['map']='Town03_Opt';s['runtime']['duration_s']=16.0;s['extensions']['clean_world_on_start']=False
 (out/(name+'.json')).write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding='utf8')
a=load('scenarios/acceptance_suite/advanced/ACC_A01_lead_brake.json');a['scenario_id']='NEW_RAIN_LEAD_BRAKE_20261116';a['description']='暴雨中 30 米前车 3 秒后由 4m/s 降至 0，保持安全距离';a['weather']='HardRainNoon';a['seed']=761;a['actors'][0]['spawn']['x']=30;a['actors'][0]['behavior'].update(initial_speed_mps=4.0,target_speed_mps=0.0,brake_at_s=3.0);a['commands'][0]['time_s']=1;a['commands'][0]['parameters']['target_speed_kph']=18;save('rain_brake',a)
b=load('scenarios/acceptance_suite/supplemental/advanced/SUP_A07_pedestrian_right_to_left.json');b['scenario_id']='NEW_WET_RIGHT_CROSS_20261116';b['description']='湿润阴天右侧行人 3 秒后由右向左横穿，前方 20 米';b['weather']='WetCloudyNoon';b['seed']=762;b['actors'][0]['spawn']['x']=20;b['actors'][0]['behavior'].update(target_xy_m=[20,-3],start_time_s=3.0,speed_mps=1.2);b['commands'][0]['parameters']['target_speed_kph']=15;save('wet_pedestrian',b)
c=load('scenarios/acceptance_suite/basic/ACC_B05_emergency_stop.json');c['scenario_id']='NEW_WET_SPEED_EMERGENCY_20261116';c['description']='湿润阴天先请求 15 km/h，6 秒后紧急停车';c['weather']='WetCloudyNoon';c['seed']=763;c['commands'][0]['source_text']='将速度设置为十五公里每小时';c['commands'][0]['parameters']['target_speed_kph']=15;save('wet_emergency',c)
