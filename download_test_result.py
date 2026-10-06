"""Save the video from an exported RunPod status JSON. No API credentials needed."""
import argparse
import base64
import json
from pathlib import Path
p = argparse.ArgumentParser()
p.add_argument('result_json', type=Path)
p.add_argument('--output', type=Path, default=Path('djb-video-test.mp4'))
a = p.parse_args()
data = json.loads(a.result_json.read_text(encoding='utf-8-sig'))
output = data.get('output', data)
if not isinstance(output, dict) or output.get('success') is not True:
    p.error('Job did not return a successful video output')
raw = base64.b64decode(output['video_base64'], validate=True)
if len(raw) != output.get('bytes'):
    p.error('Video byte count mismatch')
a.output.write_bytes(raw)
print(f'Video saved: {a.output}')
print(f"Measured worker time: {output.get('worker_seconds')} seconds (not full billed time)")
