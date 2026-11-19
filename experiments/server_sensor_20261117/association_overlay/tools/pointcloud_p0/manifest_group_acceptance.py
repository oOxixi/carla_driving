import hashlib,json,pathlib,subprocess
B=pathlib.Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime');W=pathlib.Path('/home/tiaozhansai/carla-lane-association-20261117');O=B/'pointcloud_p0_diagnosis_20261117/group_acceptance';code=['integration/duplicate_detection_grouper.py','integration/target_group_localization.py','integration/target_pointcloud_localization.py','integration/tests/test_duplicate_detection_grouper.py','tools/pointcloud_p0/regress_groups.py','tools/pointcloud_p0/collect_overlap20.py','tools/pointcloud_p0/collect_overlap_sweep.py','tools/pointcloud_p0/collect_overlap_focus.py','tools/pointcloud_p0/collect_overlap_holdout.py','tools/pointcloud_p0/adversarial_overlap_check.py','tools/pointcloud_p0/holdout_adversarial_check.py']
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for v in iter(lambda:f.read(1024*1024),b''):h.update(v)
 return h.hexdigest()
sets=['pointcloud_group_regression55_20261117','pointcloud_group_regression20_20261117','pointcloud_group_sweep_20261117','pointcloud_group_focus_20261117','pointcloud_group_holdout_20261117'];records=[]
for name in sets:
 for f in sorted((B/name).glob('*/*/result.json')):
  r=json.loads(f.read_text());src=pathlib.Path(r['point_data_source']);files=[src/'result.json',src/'camera.png',src/'lidar.bin',src/'semantic_lidar.bin',src/'radar.bin',f,f.parent/'point_status.u8',f.parent/'point_owner.i32',f.parent/'point_reason.u8'];assert all(p.is_file() for p in files);records.append({'set':name,'case':r['case'],'repeat':r['repeat'],'sha256':{str(p):sha(p) for p in files}})
assert len(records)==109
manifest={'git_head':subprocess.check_output(['git','-C',str(W),'rev-parse','HEAD'],text=True).strip(),'note':'Files in isolated worktree are uncommitted. Historical source hash describes current retained recorder; timestamps absent in old 55. Grouping inference excludes ground truth.','code_sha256':{p:sha(W/p) for p in code},'records':records,'report_sha256':{f:sha(O/f) for f in ['report.json','integrity.json','index.html']}}
(O/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');print('Integrity manifest created for',len(records),'runs')
