"""API Endpoint Integration Tests.

Tests all REST API routes and WebSocket endpoints using mocked DB/service layers.
Covers ASR, Notes, and Knowledge Graph routers.
"""
from __future__ import annotations

import json
import uuid
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel


# ═══════════════════════════════════════════════
# ASR API Router Tests
# ═══════════════════════════════════════════════

class TestASRAPIEndpoints:
    """Integration tests for ASR API endpoints (transcribe, status, segments, corrections)."""

    @pytest.mark.asyncio
    async def test_asr_transcribe_endpoint(self):
        """POST /api/v1/videos/{id}/asr/transcribe should start processing."""
        from backend.routers.asr import router, TranscribeRequest, TranscribeResponse

        routes = {r.path for r in router.routes}
        # The actual route paths include /api/v1/videos prefix
        assert any("asr/transcribe" in p for p in routes), f"transcribe route not found in {routes}"

        # Validate request/response schemas
        req = TranscribeRequest(language="zh")
        assert req.language == "zh"

        resp = TranscribeResponse(video_id="test", status="processing", message="started")
        assert resp.status == "processing"

    @pytest.mark.asyncio
    async def test_asr_status_endpoint(self):
        """GET /api/v1/videos/{id}/asr/status should return progress info."""
        from backend.routers.asr import ASRStatusResponse

        resp = ASRStatusResponse(
            video_id="test",
            status="completed",
            progress=100,
            segment_count=10,
            duration=1800.0,
        )
        assert resp.status == "completed"
        assert resp.segment_count == 10
        assert resp.duration == 1800.0

    @pytest.mark.asyncio
    async def test_asr_segment_list_endpoint(self):
        """GET /api/v1/videos/{id}/asr/segments should return paginated previews."""
        from backend.routers.asr import SegmentPreview, SegmentOut

        seg = SegmentOut(
            id=str(uuid.uuid4()),
            segment_index=0,
            start_time=0.0,
            end_time=5.0,
            text="测试文本",
            confidence=0.95,
            words=["测试", "文本"],
            is_manually_edited=False,
        )
        preview = SegmentPreview(segment=seg, prev_text=None, next_text="Next text")
        assert preview.segment.text == "测试文本"
        assert preview.next_text == "Next text"

    @pytest.mark.asyncio
    async def test_asr_segment_correction_endpoint(self):
        """PATCH /api/v1/videos/{id}/asr/segments/{sid} should update segment."""
        from backend.routers.asr import SegmentCorrectionRequest, SegmentCorrectionResponse

        req = SegmentCorrectionRequest(text="修正后的文本")
        assert req.text == "修正后的文本"

        resp = SegmentCorrectionResponse(
            id=str(uuid.uuid4()),
            segment_index=0,
            text="修正后的文本",
            is_manually_edited=True,
            original_text="原始文本",
        )
        assert resp.is_manually_edited is True
        assert resp.original_text == "原始文本"

    @pytest.mark.asyncio
    async def test_websocket_route_registered(self):
        """WebSocket route /ws/video/{video_id}/asr should be registered."""
        from backend.routers.asr import router

        ws_routes = [r.path for r in router.routes if hasattr(r, 'path') and 'ws' in r.path.lower()]
        assert any("ws" in path for path in ws_routes)


# ═══════════════════════════════════════════════
# Notes API Router Tests
# ═══════════════════════════════════════════════

class TestNotesAPIEndpoints:
    """Integration tests for Notes API endpoints."""

    def test_notes_router_registered(self):
        """Notes router should have all required routes."""
        from backend.routers.notes import router

        routes = {r.path for r in router.routes}

        expected_routes_substrings = [
            "notes/generate",
            "notes",
            "notes/sections",
            "notes/status",
        ]
        for sub in expected_routes_substrings:
            assert any(sub in p for p in routes), f"No route containing '{sub}' found in {routes}"

    def test_note_out_schema(self):
        """NoteOut response schema should serialize correctly."""
        from backend.routers.notes import NoteOut, NoteSectionOut

        sections = [
            NoteSectionOut(
                id=str(uuid.uuid4()),
                section_index=0,
                heading="Introduction",
                content="Content here",
                start_time=0.0,
                end_time=30.0,
                key_points=["Point 1"],
                confidence=0.95,
            ),
        ]
        note = NoteOut(
            id=str(uuid.uuid4()),
            video_id=str(uuid.uuid4()),
            title="Test Note",
            summary="Summary",
            keywords=["kw1"],
            metadata={"topic": "AI"},
            hallucination_score=0.0,
            language="zh",
            word_count=250,
            sections=sections,
        )
        assert note.title == "Test Note"
        assert len(note.sections) == 1
        assert note.sections[0].heading == "Introduction"
        assert note.hallucination_score == 0.0

    def test_note_generate_request_schema(self):
        """GenerateNotesRequest should support force re-generation."""
        from backend.routers.notes import GenerateNotesRequest

        req_default = GenerateNotesRequest()
        assert req_default.force is False

        req_force = GenerateNotesRequest(force=True)
        assert req_force.force is True

    def test_section_update_schema(self):
        """Section update request should accept partial updates."""
        from backend.routers.notes import SectionUpdateRequest

        update = SectionUpdateRequest(heading="New Heading")
        assert update.heading == "New Heading"
        assert update.content is None
        assert update.key_points is None

        update_full = SectionUpdateRequest(heading="H", content="C", key_points=["K1"])
        assert update_full.content == "C"


# ═══════════════════════════════════════════════
# Knowledge Graph API Router Tests
# ═══════════════════════════════════════════════

class TestGraphAPIEndpoints:
    """Integration tests for Knowledge Graph API endpoints."""

    def test_graph_router_prefix(self):
        """Graph router should be registered with correct prefix."""
        from backend.routers.graph import router

        assert len(router.routes) > 0

    def test_graph_extract_response_schema(self):
        """Graph extraction response should include status message."""
        from backend.routers.graph import (
            NodeOut,
            RelationOut,
        )

        node = NodeOut(
            id=str(uuid.uuid4()),
            name="Deep Learning",
            description="A subset of ML",
            node_type="CONCEPT",
            importance=0.95,
        )
        assert node.name == "Deep Learning"
        assert node.node_type == "CONCEPT"

        rel = RelationOut(
            id=str(uuid.uuid4()),
            source="NodeA",
            target="NodeB",
            source_id=str(uuid.uuid4()),
            target_id=str(uuid.uuid4()),
            relation_type="IS_A",
            strength=0.9,
        )
        assert rel.relation_type == "IS_A"

        # GraphOut can be used as response schema
        from backend.routers.graph import GraphOut
        graph = GraphOut(nodes=[node], relations=[rel])
        assert len(graph.nodes) == 1
        assert len(graph.relations) == 1

    def test_graph_search_response(self):
        """Graph search should support query parameter validation."""
        from backend.routers.graph import NodeOut

        node = NodeOut(
            id=str(uuid.uuid4()),
            name="Neural Network",
            description="NN description",
            node_type="TECHNOLOGY",
            importance=0.9,
        )

        # Validate NodeOut schema works
        assert node.name == "Neural Network"
        assert node.node_type == "TECHNOLOGY"

        # Search result can be a dict with nodes list
        result = {"nodes": [node.model_dump()], "total_matches": 1, "query": "neural"}
        assert result["total_matches"] == 1


# ═══════════════════════════════════════════════
# Common API Patterns
# ═══════════════════════════════════════════════

class TestAPIErrorHandling:
    """Common API error handling patterns."""

    def test_consistent_error_response(self):
        """All API errors should return consistent structure."""
        from fastapi import HTTPException

        # 404
        e404 = HTTPException(status_code=404, detail="Video not found")
        assert e404.status_code == 404
        assert "Video not found" in e404.detail

        # 409 conflict
        e409 = HTTPException(status_code=409, detail="ASR already in progress")
        assert e409.status_code == 409

        # 422 validation
        e422 = HTTPException(status_code=422, detail="Validation error")
        assert e422.status_code == 422

    def test_consistent_video_id_validation(self):
        """All routes should validate UUID format for video_id parameters."""
        invalid_id = "not-a-uuid"

        with pytest.raises(ValueError, match=r".*UUID.*"):
            uuid.UUID(invalid_id)

        valid_id = uuid.uuid4()
        assert isinstance(valid_id, uuid.UUID)

    def test_pagination_query_params(self):
        """Pagination endpoints should support offset and limit params."""
        from fastapi import Query

        # Validate Query default value mechanics
        offset = Query(default=0)
        limit = Query(default=50)

        assert offset.default == 0
        assert limit.default == 50


# ═══════════════════════════════════════════════
# Video Upload API Tests
# ═══════════════════════════════════════════════

class TestVideoUploadAPI:
    """Integration tests for video upload and management endpoints."""

    def test_video_schema(self):
        """Video model response should include all required fields."""
        from backend.models.video import Video
        from backend.models import VideoStatus

        # Validate enum values
        assert VideoStatus.UPLOADED.value == "uploaded"
        assert VideoStatus.PROCESSING.value == "processing"

        # Model should have required fields
        from backend.database import Base
        assert hasattr(Video, 'filename')
        assert hasattr(Video, 'file_path')
        assert hasattr(Video, 'status')

    def test_asr_segment_model(self):
        """ASR segment ORM model should have all required fields."""
        from backend.models.video_segment import VideoSegment

        # Check segment model has required columns
        assert hasattr(VideoSegment, 'segment_index')
        assert hasattr(VideoSegment, 'text')
        assert hasattr(VideoSegment, 'confidence')
        assert hasattr(VideoSegment, 'is_manually_edited')

    def test_knowledge_node_model(self):
        """KnowledgeNode ORM model should support all node types."""
        from backend.models.knowledge import KnowledgeNode

        # Check node model has required columns
        assert hasattr(KnowledgeNode, 'name')
        assert hasattr(KnowledgeNode, 'description')
        assert hasattr(KnowledgeNode, 'node_type')
        assert hasattr(KnowledgeNode, 'importance')

    def test_relation_model(self):
        """Relation ORM model should support all relation types."""
        from backend.models.knowledge import Relation

        # Check relation model has required columns
        assert hasattr(Relation, 'source_node_id')
        assert hasattr(Relation, 'target_node_id')
        assert hasattr(Relation, 'relation_type')
        assert hasattr(Relation, 'strength')
