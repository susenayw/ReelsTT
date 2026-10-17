"""Generate a tiny, reproducible local demo library. Original clip is CC0 (MDN)."""
from pathlib import Path
import subprocess
import urllib.request
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
target = ROOT / 'Demo videos'
target.mkdir(exist_ok=True)
source = target / '01 - A moment in bloom.mp4'
if not source.exists():
    urllib.request.urlretrieve('https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4', source)
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
jobs = [
    ('02 - A closer look - vertical.mp4', ['-vf', 'crop=ih*9/16:ih,scale=720:1280', '-c:v', 'libx264', '-preset', 'fast', '-crf', '24']),
    ('03 - Slow days - HEVC 10bit.mkv', ['-vf', 'scale=1920:1080', '-c:v', 'libx265', '-pix_fmt', 'yuv420p10le', '-preset', 'ultrafast', '-crf', '28', '-x265-params', 'pools=2:frame-threads=2:log-level=error']),
    ('04 - A different perspective.webm', ['-vf', 'hflip,scale=1280:720', '-c:v', 'libvpx-vp9', '-deadline', 'realtime', '-cpu-used', '8', '-crf', '36', '-b:v', '0']),
    ('05 - Bloom in detail - 4K HEVC.mkv', ['-t', '2', '-vf', 'scale=3840:2160', '-c:v', 'libx265', '-pix_fmt', 'yuv420p10le', '-preset', 'ultrafast', '-crf', '30', '-x265-params', 'pools=2:frame-threads=2:log-level=error']),
]
for name, encoding in jobs:
    output = target / name
    if output.exists():
        continue
    subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-threads', '2', '-filter_threads', '1', '-i', str(source),
                    '-an', *encoding, '-threads', '2', '-y', str(output)], check=True)
print(target)
