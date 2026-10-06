FROM pytorch/pytorch:2.7.1-cuda12.8-cudnn9-devel
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 TOKENIZERS_PARALLELISM=false HF_HOME=/runpod-volume/hf-cache
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends git ffmpeg ca-certificates && rm -rf /var/lib/apt/lists/*
ARG WAN_COMMIT=1ea34ff48f87168174e12956e200b1d908b1c5ff
RUN git clone https://github.com/Wan-Video/Wan2.2.git /app/Wan2.2 && cd /app/Wan2.2 && git checkout "${WAN_COMMIT}"
# Keep the CUDA 12.8 PyTorch build. Use native SDPA instead of FlashAttention 2
# to avoid relying on unsupported Blackwell kernels in third-party extensions.
RUN python -m pip install --no-cache-dir 'runpod>=1.7,<2' 'huggingface-hub>=0.30,<1' 'Pillow>=11,<12' 'numpy>=1.26,<2' 'opencv-python-headless>=4.9,<4.12' 'diffusers>=0.31,<0.36' 'transformers==4.51.3' 'accelerate>=1.1,<2' 'imageio[ffmpeg]>=2.34,<3' 'easydict==1.13' 'ftfy>=6.2,<7' 'dashscope>=1.20,<2' 'imageio-ffmpeg>=0.5,<0.7' 'requests>=2.32,<3' 'einops>=0.8,<1' 'torchvision==0.22.1'
COPY patch_attention.py /app/patch_attention.py
RUN python /app/patch_attention.py
COPY handler.py /app/handler.py
ENV WAN_MODEL_DIR=/runpod-volume/models/Wan2.2-I2V-A14B WAN_MODEL_REVISION=206a9ee1b7bfaaf8f7e4d81335650533490646a3
CMD ["python", "-u", "/app/handler.py"]
