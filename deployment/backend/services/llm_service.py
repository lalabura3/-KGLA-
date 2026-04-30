"""LLM Service — communicates with LLM API (local or cloud)."""
import json
import httpx
from typing import Optional
from config import settings


SYSTEM_PROMPTS = {
    "segment": """你是一个教育内容分析专家。请分析以下视频片段的内容，做三件事：
1. 给这个片段取一个简短标题（10字以内）
2. 用2-3句话总结核心内容
3. 列出该片段中包含的关键知识点（每个知识点用一句话描述）

请以JSON格式输出：
{"title": "...", "summary": "...", "keywords": [{"name": "...", "description": "...", "type": "concept|term|formula|method|example"}]}
""",

    "graph_relations": """你是知识图谱构建专家。给定以下知识点列表，请分析它们之间的关系。
对于每对相关的知识点，请判断关系类型（prerequisite/contains/similar/contrast/causal/sequence/related）
并给出关系强度和简要说明。

知识点列表：
{nodes_json}

请以JSON格式输出关系列表：
{"relations": [{"source": "...", "target": "...", "type": "...", "strength": 0.5, "description": "..."}]}

注意：只输出有明确关系的配对，不要强行给所有节点配对。
""",

    "qa": """你是一个基于视频内容回答问题的AI助手。以下是视频的逐字稿内容：

{transcript}

请基于以上内容回答用户的问题。如果问题超出视频内容范围，请礼貌说明。请以中文回答。
""",

    "note_generation": """你是一个教育笔记生成专家。以下是一段教学视频的逐字稿，已经按语义分段。

请为这个视频生成一份结构化学习笔记，格式如下：

# {video_title}

## 课程概述
[用2-3句话概括整节课的核心内容]

## 知识点列表

### 1. [知识点名称]
- **时间戳**: [对应视频时间]
- **要点**: 
  - [核心要点1]
  - [核心要点2]
  - ...
- **关键概念**: [相关术语解释]

### 2. [知识点名称]
...

## 总结
[本节内容的总体总结]

注意：
- 笔记要条理清晰，层次分明
- 每个知识点标注对应时间戳
- 不要原文照搬逐字稿，要提炼重组
"""
}


class LLMService:
    def __init__(self):
        self.mode = settings.llm_mode
        self.api_key = settings.llm_api_key
        self.api_base = settings.llm_api_base
        self.model = settings.llm_model
        self.local_url = settings.llm_url
        self.client = httpx.AsyncClient(timeout=120.0)

    async def chat(self, messages: list, temperature: float = 0.3) -> str:
        """Send chat completion request to LLM."""
        if self.mode == "api":
            return await self._call_api(messages, temperature)
        else:
            return await self._call_local(messages, temperature)

    async def _call_api(self, messages: list, temperature: float) -> str:
        """Call external API (DeepSeek, OpenAI-compatible)."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 4096
        }
        try:
            # Try OpenAI-compatible chat completions endpoint
            resp = await self.client.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload,
                timeout=120.0
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            # Fallback for development
            return json.dumps({
                "title": "示例标题",
                "summary": f"这是开发模式的模拟响应。API调用失败: {str(e)}。请配置正确的LLM_API_KEY。",
                "keywords": [
                    {"name": "示例知识点1", "description": "这是模拟知识点，用于开发阶段测试", "type": "concept"},
                    {"name": "示例知识点2", "description": "另一个模拟知识点", "type": "term"}
                ]
            })

    async def _call_local(self, messages: list, temperature: float) -> str:
        """Call local LLM inference service."""
        try:
            resp = await self.client.post(
                f"{self.local_url}/v1/chat/completions",
                json={
                    "model": "local",
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": 4096
                },
                timeout=120.0
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            return json.dumps({
                "error": f"Local LLM call failed: {str(e)}",
                "message": "请确保本地LLM服务已启动"
            })

    def _parse_json_from_response(self, text: str) -> dict:
        """Extract JSON from LLM response (handles markdown code blocks)."""
        # Try to find JSON in code blocks first
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        return json.loads(text)


llm_service = LLMService()
