"""Cleanup only our explicitly named actors in isolated port 22190 after a client crash."""
import carla
c=carla.Client('127.0.0.1',22190);c.set_timeout(10);w=c.get_world();assert w.get_map().name.endswith('Town05_Opt');a=list(w.get_actors());own={x.id for x in a if x.attributes.get('role_name','').startswith('visibility_audit:')};targets=[x for x in a if x.id in own or (x.parent and x.parent.id in own)]
for z in sorted(targets,key=lambda x:not x.type_id.startswith('sensor.')):
 try:z.destroy()
 except RuntimeError as e:print('cleanup:',repr(e))
s=w.get_settings();s.synchronous_mode=False;s.fixed_delta_seconds=None;w.apply_settings(s);print('cleaned',len(targets),'owned actors')
