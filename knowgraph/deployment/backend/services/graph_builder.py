"""Knowledge graph building service."""
import json
from typing import List
from services.llm_service import llm_service, SYSTEM_PROMPTS


async def extract_knowledge_nodes(segments: List[dict]) -> List[dict]:
    """Extract knowledge nodes from analyzed segments.
    
    Args:
        segments: List of dicts with keys: title, summary, keywords
    
    Returns:
        List of knowledge node dicts
    """
    nodes = []
    for seg in segments:
        for kw in seg.get("keywords", []):
            node = {
                "name": kw["name"],
                "description": kw["description"],
                "node_type": kw.get("type", "concept"),
                "timestamp": seg.get("start_time", 0),
                "segment_index": seg.get("segment_index", 0),
                "importance": 0.5
            }
            nodes.append(node)
    return nodes


async def infer_relations(nodes: List[dict]) -> List[dict]:
    """Use LLM to infer relations between knowledge nodes."""
    node_names = [n["name"] for n in nodes]

    if len(node_names) < 2:
        return []

    nodes_json = json.dumps(node_names, ensure_ascii=False)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPTS["graph_relations"].format(nodes_json=nodes_json)},
        {"role": "user", "content": f"请分析以下知识点之间的关系：\n{json.dumps(node_names, ensure_ascii=False, indent=2)}"}
    ]

    response = await llm_service.chat(messages)
    try:
        result = llm_service._parse_json_from_response(response)
        relations = result.get("relations", [])

        # Map node names back to IDs
        name_to_index = {n["name"]: i for i, n in enumerate(nodes)}
        mapped_relations = []
        for rel in relations:
            src_idx = name_to_index.get(rel.get("source"))
            tgt_idx = name_to_index.get(rel.get("target"))
            if src_idx is not None and tgt_idx is not None and src_idx != tgt_idx:
                mapped_relations.append({
                    "source_node_index": src_idx,
                    "target_node_index": tgt_idx,
                    "relation_type": rel.get("type", "related"),
                    "strength": rel.get("strength", 0.5),
                    "description": rel.get("description", "")
                })
        return mapped_relations
    except (json.JSONDecodeError, KeyError, IndexError):
        return []


async def build_video_graph(segments: List[dict]) -> dict:
    """Full pipeline: extract nodes + infer relations for a single video."""
    # Step 1: Extract knowledge nodes
    nodes = await extract_knowledge_nodes(segments)

    # Step 2: Infer relations between nodes
    relations = await infer_relations(nodes)

    return {
        "nodes": nodes,
        "relations": relations
    }
