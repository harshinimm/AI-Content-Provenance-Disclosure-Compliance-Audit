# Backend only (server.py + audit/) — the web/ frontend deploys separately
# to Vercel as a static build, not from this image.
FROM python:3.11-slim

WORKDIR /app

# System deps: git (to clone the SynthID detector at build time), curl+tar
# (to fetch c2patool's release tarball).
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# c2patool (Linux x86_64 release) — the archived contentauth/c2patool repo
# moved into contentauth/c2pa-rs's cli/ crate, see README for context.
ARG C2PATOOL_VERSION=v0.26.70
RUN curl -sSL -o /tmp/c2patool.tar.gz \
    "https://github.com/contentauth/c2pa-rs/releases/download/c2patool-${C2PATOOL_VERSION}/c2patool-${C2PATOOL_VERSION}-x86_64-unknown-linux-gnu.tar.gz" \
    && tar -xzf /tmp/c2patool.tar.gz -C /usr/local/bin c2patool \
    && rm /tmp/c2patool.tar.gz \
    && chmod +x /usr/local/bin/c2patool
ENV C2PATOOL_PATH=/usr/local/bin/c2patool

# CPU-only torch/torchvision, installed *before* anything else pulls them
# in transitively. PyPI's default "torch" package bundles full CUDA
# support (multi-GB) that we don't need — everything here runs CPU-only —
# and was almost certainly the actual cause of build failures/timeouts on
# a hosted builder. Installing the CPU wheel first means the later
# `pip install -r requirements.txt` calls (which just say torch>=X) see
# the constraint already satisfied and never touch the CUDA build.
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# SynthID community detector (see audit/synthid.py) — cloned at build time,
# same as the local dev setup, so its own requirements.txt (torch/
# torchvision/opencv) get baked into the image rather than downloaded on
# every cold start.
RUN git clone --depth 1 https://github.com/newideas99/gpt-image-synthid-detector /opt/gpt-image-synthid-detector \
    && pip install --no-cache-dir -r /opt/gpt-image-synthid-detector/requirements.txt
ENV SYNTHID_DETECTOR_REPO=/opt/gpt-image-synthid-detector

# App dependencies (this also pulls in the DIRE ensemble's transformers/
# torch — HuggingFace weights download on first request, not at build
# time, so the image itself stays smaller at the cost of a slower first
# request per model).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY audit/ ./audit/
COPY server.py .

# Railway (and most PaaS hosts) inject $PORT at runtime rather than using
# a fixed port — bind to it instead of hardcoding 8000.
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}"]
