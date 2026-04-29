"""
LLM Inference Service — runs on GPU.

Provides OpenAI-compatible chat completions API.
- Local mode: runs vLLM or llama.cpp for local model inference
- Proxy mode: forwards to DeepSeek/OpenAI API

Environment variables:
- LLM_MODE: "api" (proxy) or "local" (local inference)
- LLM_API_KEY: API key for proxy mode
- LLM_API_BASE: API base URL for proxy mode
- LLM_LOCAL_MODEL_PATH: path to local model (local mode)
"""
import os
import json
import time
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import httpx
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

app = FastAPI(title="LLM Inference Service", version="0.1.0")

LLM_MODE = os.environ.get("LLM_MODE", "api")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_API_BASE = os.environ.get("LLM_API_BASE", "https://api.deepseek.com")
LLM_LOCAL_MODEL_PATH = os.environ.get("LLM_LOCAL_MODEL_PATH", "/models")

# In-memory model reference (for local mode)
_local_engine = None


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str = "local"
    messages: List[ChatMessage]
    temperature: float = 0.3
    max_tokens: int = 4096
    stream: bool = False


def get_local_engine():
    """Lazy-load local LLM."""
    global _local_engine
    if _local_engine is not None:
        return _local_engine

    print(f"Loading local model from {LLM_LOCAL_MODEL_PATH}...")
    t0 = time.time()

    try:
        # Try vLLM first
        from vllm import LLM, SamplingParams
        _local_engine = {
            "type": "vllm",
            "engine": LLM(model=LLM_LOCAL_MODEL_PATH, tensor_parallel_size=2),  # Use both 4090s
        }
        print(f"✅ vLLM model loaded in {time.time()-t0:.1f}s")
    except ImportError:
        try:
            # Fallback to llama.cpp
            from llama_cpp import Llama
            model_path = os.path.join(LLM_LOCAL_MODEL_PATH, "model.gguf")
            _local_engine = {
                "type": "llamacpp",
                "engine": Llama(
                    model_path=model_path,
                    n_gpu_layers=-1,  # All layers on GPU
                    n_ctx=8192,
                    verbose=False,
                ),
            }
            print(f"✅ llama.cpp model loaded in {time.time()-t0:.1f}s")
        except ImportError:
            print("⚠️ No local inference library available (vLLM/llama.cpp)")
            _local_engine = {"type": "none"}
    return _local_engine


@app.get("/health")
async def health():
    """Health check."""
    engine_info = "none"
    if _local_engine:
        engine_info = _local_engine.get("type", "loaded")
    return {
        "status": "ok",
        "mode": LLM_MODE,
        "local_engine": engine_info,
        "model_path": LLM_LOCAL_MODEL_PATH if LLM_MODE == "local" else "N/A",
        "api_base": LLM_API_BASE if LLM_MODE == "api" else "N/A",
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    """OpenAI-compatible chat completions endpoint."""
    if LLM_MODE == "api":
        return await _proxy_chat(request)
    else:
        return await _local_chat(request)


async def _proxy_chat(request: ChatRequest):
    """Forward request to external API."""
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": request.model if request.model != "local" else "deepseek-chat",
        "messages": [m.model_dump() for m in request.messages],
        "temperature": request.temperature,
        "max_tokens": request.max_tokens,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{LLM_API_BASE}/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "id": data.get("id", "proxy-response"),
                "object": "chat.completion",
                "created": int(time.time()),
                "model": data.get("model", request.model),
                "choices": data["choices"],
                "usage": data.get("usage", {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                }),
            }
    except Exception as e:
        return JSONResponse(
            status_code=502,
            content={
                "error": {
                    "message": f"Proxy request failed: {str(e)}",
                    "type": "proxy_error",
                },
                "proxy_info": {
                    "api_base": LLM_API_BASE,
                    "model": request.model,
                }
            }
        )


def _local_chat(request: ChatRequest):
    """Run inference using local model."""
    engine = get_local_engine()
    if engine["type"] == "none":
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "message": "No local inference engine available. Install vLLM or llama.cpp.",
                    "type": "engine_unavailable",
                }
            }
        )

    try:
        # Format prompt from messages
        prompt_parts = []
        for m in request.messages:
            role = m.role
            content = m.content
            if role == "system":
                prompt_parts.append(f"<|system|>\n{content}</s>")
            elif role == "user":
                prompt_parts.append(f"<|user|>\n{content}</s>")
            elif role == "assistant":
                prompt_parts.append(f"<|assistant|>\n{content}</s>")
        prompt_parts.append("<|assistant|>\n")
        prompt = "".join(prompt_parts)

        t0 = time.time()

        if engine["type"] == "vllm":
            from vllm import SamplingParams
            sampling_params = SamplingParams(
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )
            outputs = engine["engine"].generate([prompt], sampling_params)
            generated_text = outputs[0].outputs[0].text
            prompt_tokens = len(outputs[0].prompt_token_ids)
            completion_tokens = len(outputs[0].outputs[0].token_ids)

        elif engine["type"] == "llamacpp":
            output = engine["engine"](
                prompt,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                echo=False,
            )
            generated_text = output["choices"][0]["text"]
            prompt_tokens = output["usage"]["prompt_tokens"]
            completion_tokens = output["usage"]["completion_tokens"]

        elapsed = time.time() - t0

        return {
            "id": f"local-chat-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": f"local-{LLM_LOCAL_MODEL_PATH.split('/')[-1] if LLM_LOCAL_MODEL_PATH != '/models' else 'model'}",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": generated_text,
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
            "timing": {
                "inference_time_seconds": round(elapsed, 2),
                "tokens_per_second": round(completion_tokens / elapsed, 2) if elapsed > 0 else 0,
            }
        }

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "message": f"Local inference failed: {str(e)}",
                    "type": "inference_error",
                }
            }
        )


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8002))
    uvicorn.run(app, host="0.0.0.0", port=port)
