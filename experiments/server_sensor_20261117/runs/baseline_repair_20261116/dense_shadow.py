"""Isolated dense-LiDAR experiment; all fusion remains evaluation-only."""
from dataclasses import replace
from types import MappingProxyType
import runpy
import integration.carla_perception as cp
specs=list(cp.DEFAULT_SENSOR_SPECS)
for i,s in enumerate(specs):
 if s.blueprint_id=='sensor.lidar.ray_cast':
  attrs=dict(s.attributes);attrs.update(channels='64',points_per_second='2240000');specs[i]=replace(s,attributes=MappingProxyType(attrs))
profiles=dict(cp.SENSOR_PROFILES);profiles['default']=tuple(specs);cp.SENSOR_PROFILES=MappingProxyType(profiles)
print('EXPERIMENT: 64-channel 2240000 points/s LiDAR; unchanged RGB and safety gates; shadow output not used for control',flush=True)
runpy.run_module('tools.target_demo.evaluate_shadow_sensor_fusion',run_name='__main__')
