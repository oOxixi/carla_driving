from pathlib import Path
import time, urllib.request
root=Path(__file__).resolve().parents[2]/'artifacts/runtime/target_live/replay'
root.mkdir(parents=True,exist_ok=True)
count=0;last=0.;start=time.monotonic();buffer=b''
with urllib.request.urlopen('http://127.0.0.1:18081/stream.mjpg',timeout=120) as response:
    while time.monotonic()-start<120:
        block=response.read(4096)
        if not block:break
        buffer+=block
        while True:
            begin=buffer.find(b'\xff\xd8');end=buffer.find(b'\xff\xd9',begin+2) if begin>=0 else -1
            if end<0:break
            data=buffer[begin:end+2];buffer=buffer[end+2:]
            now=time.monotonic()
            if now-last>=.5:
                tmp=root/f'{count:04d}.tmp';target=root/f'{count:04d}.jpg'
                tmp.write_bytes(data);tmp.replace(target);count+=1;last=now
        if len(buffer)>2_000_000:buffer=buffer[-200_000:]
print('recorded frames',count,flush=True)
