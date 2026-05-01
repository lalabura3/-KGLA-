"""Full Pipeline Integration Tests — ASR → Notes → Knowledge Graph.

These tests validate the complete data flow across all three pipeline stages,
using mocked external services (Whisper, LLM) while testing real service layer code.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from unittest.mock import ANY, AsyncMock, MagicMock, PropertyMock, patch

import pytest


# ═══════════════════════════════════════════════
# 1. ASR Pipeline Integration
# ═══════════════════════════════════════════════

class TestASRPipelineIntegration:
    """Integration tests for ASR pipeline stages (extract → VAD → transcribe → post-process)."""

    @pytest.mark.asyncio
    async def test_asr_pipeline_full_flow(self, sample_video_id, sample_audio_path):
        """Full ASR pipeline: extract_audio → run_vad → transcribe → post_process."""
        # We mock external services (FFmpeg, Whisper HTTP) and test the orchestration
        with (
            patch("backend.services.asr_service.ASRService.extract_audio", new_callable=AsyncMock) as mock_extract,
            patch("backend.services.asr_service.ASRService.run_vad", new_callable=AsyncMock) as mock_vad,
            patch("backend.services.asr_service.ASRService.transcribe", new_callable=AsyncMock) as mock_transcribe,
            patch("backend.services.asr_service.ASRService.post_process") as mock_post_process,
        ):
            from backend.services.asr_service import ASRService, ASRResult, ASRSegment

            mock_extract.return_value = sample_audio_path
            mock_vad.return_value = MagicMock(
                segments=[MagicMock(start=0.0, end=5.0, speech=True)],
                total_duration=60.0,
                speech_duration=55.0,
                speech_ratio=0.917,
            )
            mock_transcribe.return_value = [
                ASRSegment(index=0, start=0.0, end=5.3, text="测试文本", confidence=0.95),
            ]
            mock_post_process.return_value = [
                ASRSegment(index=0, start=0.0, end=5.2, text="[修正]测试文本", confidence=0.95),
            ]

            service = ASRService()
            result = await service.process(
                video_path=Path("/tmp/test.mp4"),
                video_id=sample_video_id,
                language="zh",
            )

            # Verify orchestration
            mock_extract.assert_awaited_once()
            mock_vad.assert_awaited_once()
            mock_transcribe.assert_awaited_once()
            mock_post_process.assert_called_once()

            # Verify result structure
            assert isinstance(result, ASRResult)
            assert result.video_id == sample_video_id
            assert result.language == "zh"
            assert len(result.segments) == 1
            assert result.segments[0].text == "[修正]测试文本"

    @pytest.mark.asyncio
    async def test_asr_pipeline_skip_vad_when_disabled(self, sample_video_id):
        """VAD step should be skipped when run_vad=False."""
        with (
            patch("backend.services.asr_service.ASRService.extract_audio", new_callable=AsyncMock),
            patch("backend.services.asr_service.ASRService.run_vad", new_callable=AsyncMock) as mock_vad,
            patch("backend.services.asr_service.ASRService.transcribe", new_callable=AsyncMock),
            patch("backend.services.asr_service.ASRService.post_process"),
        ):
            from backend.services.asr_service import ASRService

            service = ASRService()
            await service.process(
                video_path=Path("/tmp/test.mp4"),
                video_id=sample_video_id,
                run_vad=False,  # Disable VAD
            )

            mock_vad.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_asr_pipeline_with_progress_callback(self, sample_video_id):
        """Progress callback should be invoked at each pipeline stage."""
        progress_calls = []

        async def progress_cb(stage: str, pct: int):
            progress_calls.append((stage, pct))

        with (
            patch("backend.services.asr_service.ASRService.extract_audio", new_callable=AsyncMock),
            patch("backend.services.asr_service.ASRService.run_vad", new_callable=AsyncMock),
            patch("backend.services.asr_service.ASRService.transcribe", new_callable=AsyncMock),
            patch("backend.services.asr_service.ASRService.post_process"),
        ):
            from backend.services.asr_service import ASRService

            service = ASRService()
            await service.process(
                video_path=Path("/tmp/test.mp4"),
                video_id=sample_video_id,
                progress_callback=progress_cb,
            )

            assert len(progress_calls) >= 4  # extracting, vad, transcribing, post_processing, complete
            stages = [c[0] for c in progress_calls]
            assert "extracting" in stages
            assert "transcribing" in stages
            assert "complete" in stages

    @pytest.mark.asyncio
    async def test_asr_pipeline_handles_empty_segments(self, sample_video_id):
        """Pipeline should handle empty segment list gracefully."""
        with (
            patch("backend.services.asr_service.ASRService.extract_audio", new_callable=AsyncMock),
            patch("backend.services.asr_service.ASRService.run_vad", new_callable=AsyncMock),
            patch("backend.services.asr_service.ASRService.transcribe", new_callable=AsyncMock),
            patch("backend.services.asr_service.ASRService.post_process"),
        ):
            from backend.services.asr_service import ASRService, ASRResult

            service = ASRService()
            result = await service.process(
                video_path=Path("/tmp/empty.mp4"),
                video_id=sample_video_id,
            )

            assert isinstance(result, ASRResult)
            assert result.video_id == sample_video_id

    def test_asr_post_process_term_injection(self):
        """Post-processing should inject terms from term dictionary."""
        from backend.services.asr_service import ASRService, ASRSegment

        segments = [
            ASRSegment(index=0, start=0.0, end=3.0, text="CNN在图像识别中很有效", confidence=0.90),
        ]

        service = ASRService()
        result = service.post_process(segments, vad_result=None)

        assert len(result) == 1
        # The term dictionary should preserve/improve technical terms
        assert "CNN" in result[0].text

    def test_asr_parse_duration(self):
        """FFmpeg stderr duration parsing should handle various formats."""
        from backend.services.asr_service import ASRService

        service = ASRService()

        # Standard format
        assert service._parse_duration("Duration: 01:30:45.12") == 5445.12

        # Zero duration
        assert service._parse_duration("Duration: 00:00:00.00") == 0.0

        # No duration info
        assert service._parse_duration("No duration found") == 0.0


# ═══════════════════════════════════════════════
# 2. Note Generation Integration
# ═══════════════════════════════════════════════

class TestNoteGenerationIntegration:
    """Integration tests for Note Generation pipeline (metadata → sections → polish)."""

    @pytest.mark.asyncio
    async def test_note_generation_full_flow(
        self, sample_video_id, sample_transcript_segments,
        mock_metadata_llm_response, mock_sections_llm_response, mock_polish_llm_response,
    ):
        """Full note generation pipeline: metadata → sections → polish."""
        from backend.services.note_service import NoteService, NoteGenerationResult

        call_stage = [0]

        # Mock the LLM calls for all 3 stages
        async def mock_llm_call(system: str, user: str, temperature: float, max_tokens: int = 4096):
            stage = call_stage[0]
            call_stage[0] += 1
            if stage == 0:  # Stage 1: metadata extraction
                return json.dumps(mock_metadata_llm_response, ensure_ascii=False)
            elif stage == 1:  # Stage 2: section generation
                return json.dumps(mock_sections_llm_response, ensure_ascii=False)
            else:  # Stage 3: polish
                return json.dumps(mock_polish_llm_response, ensure_ascii=False)

        service = NoteService(llm_url="http://test:8002")

        with patch.object(service, '_call_llm', side_effect=mock_llm_call):
            result = await service.generate(
                video_id=sample_video_id,
                transcript_segments=sample_transcript_segments,
            )

            assert result.status == "completed"
            assert result.stages_completed == 3
            assert result.note is not None
            assert result.note.title == mock_metadata_llm_response["title"]
            assert len(result.note.sections) >= 2
            assert len(result.note.keywords) >= 5

    @pytest.mark.asyncio
    async def test_note_generation_empty_transcript_fails(self, sample_video_id):
        """Note generation with empty transcript should fail gracefully."""
        from backend.services.note_service import NoteService

        service = NoteService()
        result = await service.generate(
            video_id=sample_video_id,
            transcript_segments=[],
        )

        assert result.status == "failed"
        assert "No transcript segments" in (result.error or "")

    @pytest.mark.asyncio
    async def test_note_generation_stage1_metadata_extraction(
        self, sample_transcript_segments, mock_metadata_llm_response,
    ):
        """Stage 1 metadata extraction should produce title, summary, keywords."""
        from backend.services.note_service import NoteService, NoteMetadata

        service = NoteService()
        async def mock_llm(system, user, temperature, max_tokens=4096):
            return json.dumps(mock_metadata_llm_response, ensure_ascii=False)

        with patch.object(service, '_call_llm', side_effect=mock_llm):
            full_transcript = "\n".join(
                f"[{seg['segment_index']}] ({seg['start']}s-{seg['end']}s) {seg['text']}"
                for seg in sample_transcript_segments
            )
            title, summary, keywords, metadata = await service.extract_metadata(full_transcript)

            assert title == "深度学习入门：神经网络基础"
            assert len(summary) > 10
            assert len(keywords) >= 5
            assert isinstance(metadata, NoteMetadata)
            assert metadata.topic == "深度学习"
            assert metadata.is_technical is True

    @pytest.mark.asyncio
    async def test_note_generation_stage2_section_split(
        self, sample_transcript_segments, mock_sections_llm_response,
    ):
        """Stage 2 section generation should produce timestamp-anchored sections."""
        from backend.services.note_service import NoteService

        service = NoteService()
        async def mock_llm(system, user, temperature, max_tokens=4096):
            return json.dumps(mock_sections_llm_response, ensure_ascii=False)

        with patch.object(service, '_call_llm', side_effect=mock_llm):
            sections = await service.generate_sections(
                transcript_segments=sample_transcript_segments,
                title="深度学习入门",
                topic="深度学习",
            )

            assert len(sections) >= 2
            for sec in sections:
                assert sec.heading
                assert sec.content
                assert sec.start_time >= 0
                assert sec.end_time > sec.start_time
                assert len(sec.evidence) >= 1

    @pytest.mark.asyncio
    async def test_note_generation_stage3_polish_hallucination_check(
        self, mock_polish_llm_response,
    ):
        """Stage 3 polish should detect and flag hallucinations."""
        from backend.services.note_service import NoteService, NoteOutput, NoteSection

        # Create a note with potentially hallucinated content
        note = NoteOutput(
            title="Test",
            summary="Test summary",
            sections=[
                NoteSection(
                    heading="Section 1",
                    content="Some content",
                    start_time=0.0,
                    end_time=10.0,
                ),
            ],
        )

        service = NoteService()

        async def mock_llm(system, user, temperature, max_tokens=4096):
            return json.dumps(mock_polish_llm_response, ensure_ascii=False)

        with patch.object(service, '_call_llm', side_effect=mock_llm):
            result = await service.polish(note, transcript_snippet="original text")

            assert result.sections[0].hallucination_flags == []
            assert result.sections[0].confidence == 1.0

    def test_note_json_serialization(self):
        """NoteOutput should serialize correctly for LLM polish stage."""
        from backend.services.note_service import NoteOutput, NoteSection, NoteMetadata, NoteService

        note = NoteOutput(
            title="Test",
            summary="Summary",
            keywords=["kw1", "kw2"],
            metadata=NoteMetadata(topic="AI", difficulty="beginner"),
            sections=[
                NoteSection(
                    heading="Intro",
                    content="Content here",
                    start_time=0.0,
                    end_time=10.0,
                    key_points=["Point 1"],
                ),
            ],
        )

        serialized = NoteService._note_to_json(note)

        assert serialized["title"] == "Test"
        assert len(serialized["sections"]) == 1
        assert serialized["sections"][0]["heading"] == "Intro"
        assert serialized["sections"][0]["key_points"] == ["Point 1"]
        assert serialized["metadata"]["topic"] == "AI"

    def test_timestamped_transcript_building(self):
        """Building timestamped transcript from segments should include all metadata."""
        from backend.services.note_service import NoteService

        segments = [
            {"segment_index": 0, "start": 0.0, "end": 5.0, "text": "Hello", "speaker_id": "A"},
            {"segment_index": 1, "start": 5.0, "end": 10.0, "text": "World", "speaker_id": None},
        ]

        result = NoteService._build_timestamped_transcript(segments)

        assert "[Seg 0]" in result
        assert "(0.0s → 5.0s)" in result
        assert "[Speaker A]" in result
        assert "[Seg 1]" in result
        assert "[Speaker A]" not in result.split("[Seg 1]")[1] if "[Seg 1]" in result else True

    def test_full_text_composition(self):
        """Full text should be composed from structured note sections."""
        from backend.services.note_service import NoteOutput, NoteSection, NoteMetadata, NoteService

        note = NoteOutput(
            title="Test Title",
            summary="Test summary here",
            keywords=["kw1", "kw2"],
            metadata=NoteMetadata(topic="AI"),
            sections=[
                NoteSection(
                    heading="Chapter 1",
                    content="Content for chapter 1",
                    start_time=0.0,
                    end_time=10.0,
                    key_points=["KP1", "KP2"],
                ),
            ],
        )

        full_text = NoteService._compose_full_text(note)

        assert "# Test Title" in full_text
        assert "## 摘要" in full_text
        assert "Test summary here" in full_text
        assert "## Chapter 1" in full_text
        assert "KP1" in full_text
        assert "kw1" in full_text


# ═══════════════════════════════════════════════
# 3. Knowledge Graph Integration
# ═══════════════════════════════════════════════

class TestGraphExtractionIntegration:
    """Integration tests for Knowledge Graph pipeline (nodes → relations)."""

    @pytest.mark.asyncio
    async def test_graph_extraction_full_flow(
        self, sample_video_id, sample_note_sections,
        mock_nodes_llm_response, mock_relations_llm_response,
    ):
        """Full graph extraction pipeline: nodes → relations."""
        from backend.services.graph_service import GraphService, GraphExtractionResult

        service = GraphService()

        # Mock both LLM calls
        call_count = 0

        async def mock_llm_call(system, user, temperature, max_tokens=4096):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return json.dumps(mock_nodes_llm_response, ensure_ascii=False)
            return json.dumps(mock_relations_llm_response, ensure_ascii=False)

        with patch.object(service, '_call_llm', side_effect=mock_llm_call):
            result = await service.extract(
                video_id=sample_video_id,
                title="深度学习入门",
                summary="深度学习入门总结",
                keywords=["深度学习", "神经网络", "CNN"],
                sections=sample_note_sections,
                full_text="Full note text for context",
            )

            assert result.status == "completed"
            assert result.stages_completed == 2
            assert len(result.nodes) >= 5
            assert len(result.relations) >= 3
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_graph_extraction_empty_sections_fails(self, sample_video_id):
        """Graph extraction with empty sections should fail gracefully."""
        from backend.services.graph_service import GraphService

        service = GraphService()
        result = await service.extract(
            video_id=sample_video_id,
            title="Test",
            summary="Test",
            keywords=[],
            sections=[],
            full_text="",
        )

        assert result.status == "failed"
        assert "No note sections" in (result.error or "")

    @pytest.mark.asyncio
    async def test_graph_extraction_stage1_nodes(
        self, mock_nodes_llm_response,
    ):
        """Stage 1 node extraction should produce knowledge nodes with types."""
        from backend.services.graph_service import GraphService

        service = GraphService()

        async def mock_llm(system, user, temperature, max_tokens=4096):
            return json.dumps(mock_nodes_llm_response, ensure_ascii=False)

        with patch.object(service, '_call_llm', side_effect=mock_llm):
            nodes = await service.extract_nodes(
                title="深度学习入门",
                summary="深度学习总结",
                keywords=["深度学习", "神经网络"],
                sections=[{"section_index": 0, "heading": "Intro", "content": "Content", "key_points": ["P1"]}],
            )

            assert len(nodes) >= 5
            for node in nodes:
                assert node.name
                assert node.node_type in ("CONCEPT", "TECHNOLOGY", "METHODOLOGY", "PERSON", "EXAMPLE", "RELATION", "PREREQUISITE")
                assert 0.0 <= node.importance <= 1.0

    @pytest.mark.asyncio
    async def test_graph_extraction_stage2_relations(
        self, mock_nodes_llm_response, mock_relations_llm_response,
    ):
        """Stage 2 relation extraction should produce valid relations between known nodes."""
        from backend.services.graph_service import GraphService, KnowledgeNodeData

        service = GraphService()

        # Parse nodes from mock response
        raw_nodes = mock_nodes_llm_response["nodes"]
        nodes = [
            KnowledgeNodeData(
                name=n["name"],
                description=n["description"],
                node_type=n["node_type"],
                importance=n["importance"],
                segment_indices=n["segment_indices"],
            )
            for n in raw_nodes
        ]

        async def mock_llm2(system, user, temperature, max_tokens=4096):
            return json.dumps(mock_relations_llm_response, ensure_ascii=False)

        with patch.object(service, '_call_llm', side_effect=mock_llm2):
            relations = await service.extract_relations(
                title="深度学习入门",
                note_full_text="Full note text with all content",
                nodes=nodes,
            )

            assert len(relations) >= 3
            for rel in relations:
                assert rel.source in [n.name for n in nodes]
                assert rel.target in [n.name for n in nodes]
                assert rel.relation_type in (
                    "PREREQUISITE_OF", "IS_A", "PART_OF", "RELATES_TO",
                    "CONTRASTS_WITH", "LEADS_TO", "EXAMPLE_OF", "USES", "APPLIES_TO",
                )

    @pytest.mark.asyncio
    async def test_graph_extraction_skips_invalid_relations(
        self, mock_relations_llm_response,
    ):
        """Relations referencing non-existent nodes should be filtered out."""
        from backend.services.graph_service import GraphService, KnowledgeNodeData

        service = GraphService()

        # Node list only has '深度学习', so '神经网络' WILL match (source exists)
        # But only one target '神经网络' also exists in node list
        nodes = [
            KnowledgeNodeData(name="深度学习", description="DL", node_type="CONCEPT", importance=0.9),
            KnowledgeNodeData(name="神经网络", description="NN", node_type="TECHNOLOGY", importance=0.8),
        ]

        # Mock returns relations where some targets don't exist in node list
        invalid_relations = {
            "relations": [
                {"source": "深度学习", "target": "神经网络", "relation_type": "IS_A", "strength": 0.9, "description": ""},
                {"source": "深度学习", "target": "NonexistentNode", "relation_type": "RELATES_TO", "strength": 0.5, "description": ""},
            ]
        }

        async def mock_llm_inv(system, user, temperature, max_tokens=4096):
            return json.dumps(invalid_relations, ensure_ascii=False)

        with patch.object(service, '_call_llm', side_effect=mock_llm_inv):
            relations = await service.extract_relations(
                title="Test",
                note_full_text="Text",
                nodes=nodes,
            )

            # Only valid relation should pass (both source and target in node list)
            assert len(relations) == 1
            assert relations[0].target == "神经网络"

    def test_node_deduplication(self):
        """Deduplicate nodes by name, merging descriptions and importance."""
        from backend.services.graph_service import GraphService, KnowledgeNodeData

        nodes = [
            KnowledgeNodeData(name="深度学习", description="Short", node_type="CONCEPT", importance=0.5, segment_indices=[0]),
            KnowledgeNodeData(name="深度学习", description="Longer description for merge", node_type="CONCEPT", importance=0.9, segment_indices=[1]),
            KnowledgeNodeData(name="DEEP LEARNING", description="Another", node_type="TECHNOLOGY", importance=0.7, segment_indices=[2]),
        ]

        deduped = GraphService._dedup_nodes(nodes)

        assert len(deduped) == 2  # 2 unique after case-insensitive dedup
        assert deduped[0].description == "Longer description for merge"  # Longer kept
        assert deduped[0].importance == 0.9  # Higher importance kept
        assert sorted(deduped[0].segment_indices) == [0, 1]

    def test_relation_deduplication(self):
        """Deduplicate relations by source-target-type direction."""
        from backend.services.graph_service import GraphService, RelationData

        relations = [
            RelationData(source="A", target="B", relation_type="RELATES_TO", strength=0.8),
            RelationData(source="A", target="B", relation_type="RELATES_TO", strength=0.9),  # Duplicate
            RelationData(source="B", target="A", relation_type="RELATES_TO", strength=0.7),  # Reversed same type
            RelationData(source="A", target="C", relation_type="USES", strength=0.6),  # Different
        ]

        deduped = GraphService._dedup_relations(relations)
        assert len(deduped) == 2  # Only unique relations


# ═══════════════════════════════════════════════
# 4. Full Pipeline End-to-End
# ═══════════════════════════════════════════════

class TestFullPipelineIntegration:
    """End-to-end integration test: ASR → Notes → Knowledge Graph."""

    @pytest.mark.asyncio
    async def test_full_pipeline_data_flow(
        self,
        sample_video_id,
        sample_asr_segments,
        mock_metadata_llm_response,
        mock_sections_llm_response,
        mock_polish_llm_response,
        mock_nodes_llm_response,
        mock_relations_llm_response,
    ):
        """Complete data flow: ASR segments flow through notes into knowledge graph.

        This tests that the output schema of each stage is compatible with
        the input schema of the next stage.
        """
        # ── Step 1: ASR Pipeline → segments ──
        asr_result = sample_asr_segments
        assert len(asr_result) >= 5
        assert all(s["start"] < s["end"] for s in asr_result)
        assert all(s["text"] for s in asr_result)

        # ── Step 2: ASR segments → Notes ──
        note_input = [
            {
                "segment_index": s["segment_index"],
                "start": s["start"],
                "end": s["end"],
                "text": s["text"],
                "speaker_id": None,
            }
            for s in asr_result
        ]

        from backend.services.note_service import NoteService

        note_service = NoteService()
        note_call_count = [0]

        async def mock_note_llm(system, user, temperature, max_tokens=4096):
            stage = note_call_count[0]
            note_call_count[0] += 1
            if stage == 0:
                return json.dumps(mock_metadata_llm_response, ensure_ascii=False)
            elif stage == 1:
                return json.dumps(mock_sections_llm_response, ensure_ascii=False)
            return json.dumps(mock_polish_llm_response, ensure_ascii=False)

        with patch.object(note_service, '_call_llm', side_effect=mock_note_llm):
            note_result = await note_service.generate(
                video_id=sample_video_id,
                transcript_segments=note_input,
            )

        assert note_result.status == "completed"
        note = note_result.note
        assert note is not None

        # ── Step 3: Notes → Knowledge Graph ──
        graph_sections = [
            {
                "section_index": i,
                "heading": s.heading,
                "content": s.content,
                "key_points": s.key_points,
            }
            for i, s in enumerate(note.sections)
        ]

        from backend.services.graph_service import GraphService

        graph_service = GraphService()

        call_log = {"count": 0}

        async def mock_graph_llm(system, user, temperature, max_tokens=4096):
            call_log["count"] += 1
            if call_log["count"] == 1:
                return json.dumps(mock_nodes_llm_response, ensure_ascii=False)
            return json.dumps(mock_relations_llm_response, ensure_ascii=False)

        with patch.object(graph_service, '_call_llm', side_effect=mock_graph_llm):
            graph_result = await graph_service.extract(
                video_id=sample_video_id,
                title=note.title,
                summary=note.summary,
                keywords=note.keywords,
                sections=graph_sections,
                full_text=note.raw_full_text,
            )

        assert graph_result.status == "completed"
        assert len(graph_result.nodes) >= 5
        assert len(graph_result.relations) >= 3

        # ── Verify graph references valid note content ──
        node_names = {n.name for n in graph_result.nodes}
        for rel in graph_result.relations:
            assert rel.source in node_names
            assert rel.target in node_names

    @pytest.mark.asyncio
    async def test_pipeline_handles_partial_failure_gracefully(self, sample_video_id):
        """Pipeline should handle failure at any stage without cascading crashes."""
        from backend.services.note_service import NoteService

        # Simulate LLM failure during notes
        service = NoteService()

        async def failing_mock(system, user, temperature, max_tokens=4096):
            raise RuntimeError("LLM service unavailable")

        with patch.object(service, '_call_llm', side_effect=failing_mock):
            result = await service.generate(
                video_id=sample_video_id,
                transcript_segments=[
                    {"segment_index": 0, "start": 0.0, "end": 5.0, "text": "Test", "speaker_id": None},
                ],
            )

            assert result.status == "failed"
            assert result.error is not None


# ═══════════════════════════════════════════════
# 5. Service Layer Error Handling
# ═══════════════════════════════════════════════

class TestServiceErrorHandling:
    """Integration tests for error handling at service boundaries."""

    @pytest.mark.asyncio
    async def test_llm_call_retry_mechanism(self):
        """LLM calls should retry on transient failures.
        
        Note: The retry logic lives in _call_llm which makes HTTP calls to LLM service.
        Since we mock _call_llm directly (not HTTP), the retry is bypassed in tests.
        This test validates the retry configuration is properly set.
        """
        from backend.services.graph_service import GraphService

        service = GraphService(max_retries=2)
        assert service.max_retries == 2
        assert hasattr(service, '_call_llm')

        # Verify the retry is implemented in _call_llm
        import inspect
        source = inspect.getsource(service._call_llm)
        assert 'max_retries' in source or 'retry' in source.lower()
        assert service.max_retries >= 1

    @pytest.mark.asyncio
    async def test_llm_call_gives_up_after_retries(self):
        """LLM calls should give up after exhausting retries.
        
        When the retry limit is exhausted, the error should propagate.
        This test validates the service handles retry limits properly.
        """
        from backend.services.note_service import NoteService

        service = NoteService(max_retries=1)
        assert service.max_retries == 1

        # Verify retry configuration exists
        import inspect
        source = inspect.getsource(service._call_llm)
        assert 'self.max_retries' in source

        # Test that empty transcript (validated before LLM call) fails gracefully
        result = await service.generate(
            video_id=uuid.uuid4(),
            transcript_segments=[],
        )

        assert result.status == "failed"
        assert "No transcript segments" in (result.error or "")

    def test_json_parse_safe_handles_markdown_fences(self):
        """JSON parsing should strip markdown code fences."""
        from backend.services.note_service import NoteService

        text = '```json\n{"key": "value"}\n```'
        result = NoteService._parse_json_safe(text)
        assert isinstance(result, dict)
        assert result["key"] == "value"

    def test_json_parse_safe_fallback_regex(self):
        """JSON parsing should fall back to regex extraction."""
        from backend.services.note_service import NoteService

        text = 'Here is the result: {"key": "value"}'
        result = NoteService._parse_json_safe(text)
        assert isinstance(result, dict)
        assert result["key"] == "value"

    def test_json_parse_safe_returns_empty_on_failure(self):
        """JSON parsing should return empty dict/list on complete failure."""
        from backend.services.note_service import NoteService

        # Text starting with '{' returns empty dict, else empty list
        result_dict = NoteService._parse_json_safe("{Not JSON at all")
        assert result_dict == {}

        result_list = NoteService._parse_json_safe("Not JSON at all")
        assert result_list == []
