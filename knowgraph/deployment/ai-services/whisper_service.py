"""
Whisper ASR Service — runs on GPU via faster-whisper.

Dedicated service for audio transcription with GPU acceleration.
Designed to run on the 2×4090 machine alongside the LLM service.
"""
import os
import time
import json
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, Form, Query
from fastapi.responses import JSONResponse
import tempfile

app = FastAPI(title="Whisper ASR Service", version="0.1.0")

# Global model cache
_model = None
_model_size = os.environ.get("WHISPER_MODEL", "large-v3")


def get_model():
    """Lazy-load Whisper model (loaded once, kept in memory)."""
    global _model
    if _model is None:
        print(f"Loading Whisper model: {_model_size}...")
        t0 = time.time()
        from faster_whisper import WhisperModel
        # Use float16 on GPU; fall back to CPU if CUDA unavailable
        try:
            _model = WhisperModel(_model_size, device="cuda", compute_type="float16")
            print(f"✅ Whisper loaded on GPU in {time.time()-t0:.1f}s")
        except Exception:
            print("⚠️ GPU unavailable, falling back to CPU...")
            _model = WhisperModel(_model_size, device="cpu", compute_type="int8")
            print(f"✅ Whisper loaded on CPU in {time.time()-t0:.1f}s")
    return _model


@app.get("/health")
async def health():
    """Health check."""
    try:
        model = get_model()
        return {
            "status": "ok",
            "model": _model_size,
            "device": "cuda" if str(model.device) == "cuda" else "cpu"
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "message": str(e)}
        )


@app.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    language: str = Query("zh", description="Language code (zh, en, etc.)"),
    response_format: str = Query("verbose_json", description="Response format")
):
    """
    Transcribe audio file using Whisper.

    Returns segments with start/end timestamps and text.
    """
    try:
        model = get_model()

        # Save uploaded file to temp location
        suffix = Path(file.filename).suffix or ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        # Transcribe
        t0 = time.time()
        segments, info = model.transcribe(
            tmp_path,
            language=language,
            beam_size=5,
            vad_filter=True,  # Filter out non-speech
            vad_parameters=dict(
                min_silence_duration_ms=500,
                threshold=0.5
            )
        )

        # Collect results
        result_segments = []
        full_text_parts = []
        for seg in segments:
            seg_dict = {
                "start": round(seg.start, 2),
                "end": round(seg.end, 2),
                "text": seg.text.strip(),
            }
            result_segments.append(seg_dict)
            full_text_parts.append(seg.text.strip())

        # Clean up temp file
        os.unlink(tmp_path)

        elapsed = time.time() - t0
        duration = info.duration if info else 0

        return {
            "full_text": " ".join(full_text_parts),
            "segments": result_segments,
            "language": info.language if info else language,
            "duration": round(duration, 2),
            "processing_time": round(elapsed, 2),
            "model": _model_size,
        }

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "message": "Transcription failed"}
        )


@app.post("/transcribe_file")
async def transcribe_file_path(
    file_path: str = Form(...),
    language: str = Form("zh")
):
    """
    Transcribe audio by file path (for local files).
    Useful when the audio file is already on the filesystem.
    """
    if not os.path.exists(file_path):
        return JSONResponse(
            status_code=400,
            content={"error": f"File not found: {file_path}"}
        )

    try:
        model = get_model()

        t0 = time.time()
        segments, info = model.transcribe(
            file_path,
            language=language,
            beam_size=5,
            vad_filter=True,
        )

        result_segments = []
        full_text_parts = []
        for seg in segments:
            seg_dict = {
                "start": round(seg.start, 2),
                "end": round(seg.end, 2),
                "text": seg.text.strip(),
            }
            result_segments.append(seg_dict)
            full_text_parts.append(seg.text.strip())

        elapsed = time.time() - t0
        duration = info.duration if info else 0

        return {
            "full_text": " ".join(full_text_parts),
            "segments": result_segments,
            "language": info.language if info else language,
            "duration": round(duration, 2),
            "processing_time": round(elapsed, 2),
            "model": _model_size,
        }

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
