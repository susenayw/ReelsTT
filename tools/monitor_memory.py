"""Read-only process sampling for a manual playback verification session."""
import argparse
import json
from pathlib import Path
import time
import psutil

parser = argparse.ArgumentParser()
parser.add_argument('--seconds', type=int, default=45)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
state_file = root / 'data' / 'runtime.json'
state = json.loads(state_file.read_text())
process = psutil.Process(state['pid'])
records = []
end = time.monotonic()+args.seconds
while time.monotonic() < end:
    try:
        info = process.memory_info()
        state = json.loads(state_file.read_text())
        records.append({'rss_mb': round(info.rss/1e6, 2), 'private_mb': round(getattr(info, 'private', info.rss)/1e6, 2),
                        'players': state.get('players'), 'index': state.get('index'), 'feed': state.get('feed'),
                        'hwdec': state.get('hwdec'), 'path': state.get('path')})
    except (OSError, ValueError, psutil.NoSuchProcess):
        break
    time.sleep(.2)
report = {'samples': len(records), 'interval_seconds': .2,
          'peak_rss_mb': max((s['rss_mb'] for s in records), default=0),
          'peak_private_mb': max((s['private_mb'] for s in records), default=0),
          'records': records}
(root / 'data' / 'memory-verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='records'}))
