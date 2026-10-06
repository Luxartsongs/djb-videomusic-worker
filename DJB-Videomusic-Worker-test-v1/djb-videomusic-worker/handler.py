"""DJB isolated Wan image-to-video test worker. No audio endpoint/billing changes."""
import base64
import binascii
import io
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time

LOG = logging.getLogger('djb-video')
logging.basicConfig(level=logging.INFO, format='[DJB VIDEO] %(message)s')
MODEL = 'Wan-AI/Wan2.2-I2V-A14B'
MODEL_REVISION = os.getenv('WAN_MODEL_REVISION', '206a9ee1b7bfaaf8f7e4d81335650533490646a3')
MODEL_DIR = Path(os.getenv('WAN_MODEL_DIR', '/runpod-volume/models/Wan2.2-I2V-A14B'))
WAN_DIR = Path(os.getenv('WAN_CODE_DIR', '/app/Wan2.2'))
LOCK = threading.Lock()
MAX_IMAGE_BYTES = 4 * 1024 * 1024
MAX_VIDEO_BYTES = 5 * 1024 * 1024


def validate(payload):
    if not isinstance(payload, dict):
        raise ValueError('input must be an object')
    action = payload.get('action', 'generate_scene')
    if action == 'health':
        return {'action': action}
    if action != 'generate_scene':
        raise ValueError('Only generate_scene and health are supported')
    prompt = payload.get('prompt')
    if not isinstance(prompt, str) or not 10 <= len(prompt.strip()) <= 3000:
        raise ValueError('prompt must contain 10 to 3000 characters')
    image = payload.get('image_base64')
    if not isinstance(image, str) or len(image) > (MAX_IMAGE_BYTES * 4 // 3 + 200):
        raise ValueError('image_base64 is required; maximum image size is 4 MB')
    if image.startswith('data:'):
        prefix, sep, image = image.partition(',')
        if not sep or not prefix.endswith(';base64'):
            raise ValueError('Invalid image data URI')
    try:
        raw = base64.b64decode(image, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError('Invalid image base64') from exc
    if not raw or len(raw) > MAX_IMAGE_BYTES:
        raise ValueError('Invalid image size')
    size = payload.get('resolution', '480p')
    if size not in ('480p', '720p'):
        raise ValueError('resolution must be 480p or 720p')
    frames = payload.get('frames', 81)
    if isinstance(frames, bool) or not isinstance(frames, int) or frames not in (49, 81):
        raise ValueError('Test worker supports 49 or 81 frames only')
    steps = payload.get('steps', 40)
    if isinstance(steps, bool) or not isinstance(steps, int) or not 20 <= steps <= 40:
        raise ValueError('steps must be an integer between 20 and 40')
    seed = payload.get('seed', 42)
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 2147483647:
        raise ValueError('seed must be a nonnegative 32-bit integer')
    return dict(action=action, prompt=prompt.strip(), raw=raw, resolution=size,
                frames=frames, steps=steps, seed=seed)


def ensure_model():
    # Refuse ephemeral fallback: the first download must survive worker shutdown.
    if not Path('/runpod-volume').is_mount():
        raise RuntimeError('Attach a RunPod Network Volume mounted at /runpod-volume')
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    marker = MODEL_DIR / '.djb-model-complete'
    if marker.exists() and marker.read_text().strip() == MODEL_REVISION:
        return
    from huggingface_hub import snapshot_download
    LOG.info('Downloading model to the persistent network volume (first job only)')
    snapshot_download(repo_id=MODEL, revision=MODEL_REVISION, local_dir=str(MODEL_DIR),
                      max_workers=4, ignore_patterns=['*.md', '*.png', '*.jpg', '*.mp4'])
    for name in ['low_noise_model', 'high_noise_model', 'Wan2.1_VAE.pth',
                 'models_t5_umt5-xxl-enc-bf16.pth']:
        if not (MODEL_DIR / name).exists():
            raise RuntimeError('Incomplete model download')
    marker.write_text(MODEL_REVISION)


def command(params, image, output):
    return [sys.executable, str(WAN_DIR / 'generate.py'), '--task', 'i2v-A14B',
            '--size', '832*480' if params['resolution'] == '480p' else '1280*720',
            '--ckpt_dir', str(MODEL_DIR), '--image', str(image),
            '--prompt', params['prompt'], '--frame_num', str(params['frames']),
            '--sample_steps', str(params['steps']), '--base_seed', str(params['seed']),
            '--offload_model', 'True', '--convert_model_dtype', '--t5_cpu',
            '--save_file', str(output)]


def handler(job):
    params = validate(job.get('input'))
    if params['action'] == 'health':
        import torch
        gpu = torch.cuda.is_available()
        return {'success': True, 'worker': 'djb-video-wan-test', 'cuda_available': gpu,
                'gpu': torch.cuda.get_device_name(0) if gpu else None,
                'network_volume_mounted': Path('/runpod-volume').is_mount(),
                'model_downloaded': (MODEL_DIR / '.djb-model-complete').exists(),
                'model': MODEL, 'model_revision': MODEL_REVISION}
    # One inference per worker; the endpoint itself is also capped at one worker.
    with LOCK:
        from PIL import Image, ImageOps
        import torch
        if not torch.cuda.is_available():
            raise RuntimeError('CUDA GPU unavailable')
        total = torch.cuda.get_device_properties(0).total_memory
        if total < 80 * 1024 ** 3:
            raise RuntimeError('This test configuration requires at least 80 GB VRAM')
        # Validate/decode the image before spending time downloading model weights.
        Image.MAX_IMAGE_PIXELS = 25_000_000
        with Image.open(io.BytesIO(params['raw'])) as im:
            if im.format not in ('JPEG', 'PNG', 'WEBP'):
                raise ValueError('Use a JPG, PNG or WebP image')
            im = ImageOps.exif_transpose(im).convert('RGB')
            im.thumbnail((1920, 1920))
            prepared = im.copy()
        started = time.monotonic()
        ensure_model()
        with tempfile.TemporaryDirectory(prefix='djb-video-') as directory:
            folder = Path(directory)
            image, output = folder / 'reference.png', folder / 'scene.mp4'
            prepared.save(image)
            LOG.info('Generating %s frames, %s, %s steps',
                     params['frames'], params['resolution'], params['steps'])
            # Argument array: no shell interpolation of prompts or filenames.
            subprocess.run(command(params, image, output), cwd=str(WAN_DIR),
                           check=True, timeout=2400)
            if not output.is_file() or output.stat().st_size == 0:
                raise RuntimeError('No video generated')
            if output.stat().st_size > MAX_VIDEO_BYTES:
                smaller = folder / 'scene-small.mp4'
                subprocess.run(['ffmpeg', '-y', '-i', str(output), '-an', '-c:v',
                                'libx264', '-crf', '26', '-preset', 'medium',
                                '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
                                str(smaller)], check=True, timeout=120,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                output = smaller
            if output.stat().st_size > MAX_VIDEO_BYTES:
                raise RuntimeError('Test output exceeds 5 MB; production storage is required')
            probe = subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
                                    'format=duration:stream=width,height,avg_frame_rate',
                                    '-of', 'json', str(output)], check=True,
                                   capture_output=True, text=True, timeout=30)
            metadata = json.loads(probe.stdout)
            raw = output.read_bytes()
            return {'success': True, 'model': MODEL, 'video_base64': base64.b64encode(raw).decode(),
                    'mime_type': 'video/mp4', 'file_name': 'djb-video-test.mp4',
                    'bytes': len(raw), 'seed': params['seed'], 'steps': params['steps'],
                    'frames': params['frames'], 'video_metadata': metadata,
                    'worker_seconds': round(time.monotonic() - started, 2),
                    'note': 'Silent test scene; music, montage and billing are not connected'}


if __name__ == '__main__':
    import runpod
    runpod.serverless.start({'handler': handler})
