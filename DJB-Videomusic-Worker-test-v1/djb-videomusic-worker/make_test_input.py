"""Create a bounded RunPod input JSON from a local reference image."""
import argparse
import base64
import json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('image', type=Path)
p.add_argument('--output', type=Path, default=Path('test-input.json'))
p.add_argument('--resolution', choices=['480p', '720p'], default='480p')
a = p.parse_args()
raw = a.image.read_bytes()
if len(raw) > 4 * 1024 * 1024:
    p.error('Image must be smaller than 4 MB')
prompt = ('A cinematic medium shot of the same woman shown in the reference image. '
          'She slowly turns her head toward the camera with a calm expression. '
          'Keep her facial features, hairstyle and clothing consistent. '
          'Subtle natural movement, dark gothic atmosphere, soft dramatic light, '
          'static camera, no text, no logos, no rapid scene changes.')
payload = {'input': {'action': 'generate_scene', 'image_base64': base64.b64encode(raw).decode(),
                     'prompt': prompt, 'resolution': a.resolution, 'frames': 81,
                     'steps': 40, 'seed': 42}}
a.output.write_text(json.dumps(payload), encoding='utf-8')
print(f'Input created: {a.output} (no RunPod call was made)')
