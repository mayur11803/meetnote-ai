"""
Meeting Analyzer
Uses NVIDIA NIM LLMs to extract structured insights from a transcript.
"""

import json
import re
from typing import Any
from nvidia_client import NVIDIAClient

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are an expert meeting analyst and note-taker.
Your role is to analyze meeting transcripts and extract structured, actionable information.
Always respond with valid JSON only. No markdown fences, no extra text.
Be specific, concise, and use the exact words from the transcript where possible.
"""

# ── Analysis prompts ──────────────────────────────────────────────────────────
SUMMARY_PROMPT = """Analyze this meeting transcript and return a JSON object with the following structure:

{
  "executive_summary": "2-3 sentence high-level summary of the entire meeting",
  "meeting_type": "e.g. standup / planning / review / brainstorm / client call / interview",
  "main_topics": ["topic 1", "topic 2", "topic 3"],
  "key_discussion_points": [
    {"point": "concise description", "context": "why it matters", "speaker": "speaker name if identifiable"}
  ],
  "decisions": [
    {"decision": "what was decided", "rationale": "why", "decided_by": "person or group"}
  ],
  "action_items": [
    {"task": "specific task description", "owner": "person responsible", "deadline": "date or timeframe or null", "priority": "high/medium/low"}
  ],
  "open_questions": ["question 1", "question 2"],
  "risks_concerns": ["risk or concern 1"],
  "sentiment": "positive/neutral/negative/mixed",
  "meeting_effectiveness": "high/medium/low",
  "follow_up_meeting_needed": true,
  "tags": ["tag1", "tag2"]
}

TRANSCRIPT:
{transcript}
"""

SPEAKER_PROMPT = """Analyze speaker contributions from this meeting transcript and return a JSON object:

{
  "speakers": [
    {
      "name": "Speaker name or Speaker 1/2/etc",
      "estimated_talk_percentage": 35,
      "key_contributions": ["contribution 1", "contribution 2"],
      "role_in_meeting": "facilitator/participant/decision-maker/observer",
      "questions_asked": ["question 1"],
      "commitments_made": ["commitment 1"]
    }
  ],
  "meeting_dynamics": "description of interaction patterns",
  "dominant_speaker": "name",
  "collaboration_level": "high/medium/low"
}

TRANSCRIPT:
{transcript}
"""

TIMELINE_PROMPT = """Extract a chronological timeline of key moments from this transcript:

Return JSON:
{
  "timeline": [
    {"timestamp_hint": "beginning/middle/end or time if visible", "event": "what happened", "significance": "why it matters"}
  ],
  "duration_phases": [
    {"phase": "phase name", "description": "what happened in this phase"}
  ]
}

TRANSCRIPT:
{transcript}
"""

INSIGHTS_PROMPT = """Provide strategic insights and recommendations from this meeting:

Return JSON:
{
  "key_insights": ["insight 1", "insight 2"],
  "recommendations": ["recommendation 1", "recommendation 2"],
  "blockers_identified": ["blocker 1"],
  "success_factors": ["factor 1"],
  "next_steps_summary": "narrative summary of what needs to happen next"
}

TRANSCRIPT:
{transcript}
"""


# ── Analyzer class ────────────────────────────────────────────────────────────
class MeetingAnalyzer:

    def __init__(self, nvidia_client: NVIDIAClient):
        self.client = nvidia_client

    async def analyze(self, transcript: str, session: dict) -> dict:
        """Run all analysis passes and merge results."""
        # Use faster model for shorter transcripts, smarter model for long ones
        model = (
            "meta/llama-3.1-70b-instruct"
            if len(transcript) > 2000
            else "meta/llama-3.1-8b-instruct"
        )

        # Truncate very long transcripts to fit context window
        max_chars = 12000
        transcript_excerpt = transcript[:max_chars]
        if len(transcript) > max_chars:
            transcript_excerpt += "\n[Transcript truncated for analysis]"

        results = await self._run_analyses(transcript_excerpt, model)
        return self._merge(results, session, transcript)

    async def _run_analyses(self, transcript: str, model: str) -> dict:
        """Run all four analysis prompts in parallel."""
        import asyncio

        async def call(prompt_template: str) -> dict:
            prompt = prompt_template.format(transcript=transcript)
            raw = await self.client.chat_complete(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                model=model,
                temperature=0.2,
                max_tokens=3000,
            )
            return self._parse_json(raw)

        summary_task  = asyncio.create_task(call(SUMMARY_PROMPT))
        speaker_task  = asyncio.create_task(call(SPEAKER_PROMPT))
        timeline_task = asyncio.create_task(call(TIMELINE_PROMPT))
        insights_task = asyncio.create_task(call(INSIGHTS_PROMPT))

        summary, speakers, timeline, insights = await asyncio.gather(
            summary_task, speaker_task, timeline_task, insights_task,
            return_exceptions=True,
        )

        return {
            "summary": summary if not isinstance(summary, Exception) else {},
            "speakers": speakers if not isinstance(speakers, Exception) else {},
            "timeline": timeline if not isinstance(timeline, Exception) else {},
            "insights": insights if not isinstance(insights, Exception) else {},
        }

    def _merge(self, results: dict, session: dict, full_transcript: str) -> dict:
        """Merge all analysis results into one coherent structure."""
        summary = results.get("summary", {})
        speakers = results.get("speakers", {})
        timeline = results.get("timeline", {})
        insights = results.get("insights", {})

        return {
            # Core summary
            "executive_summary": summary.get("executive_summary", ""),
            "meeting_type": summary.get("meeting_type", "General meeting"),
            "main_topics": summary.get("main_topics", []),
            "sentiment": summary.get("sentiment", "neutral"),
            "meeting_effectiveness": summary.get("meeting_effectiveness", "medium"),
            "follow_up_meeting_needed": summary.get("follow_up_meeting_needed", False),
            "tags": summary.get("tags", []),

            # Discussion details
            "key_discussion_points": summary.get("key_discussion_points", []),
            "decisions": summary.get("decisions", []),
            "action_items": summary.get("action_items", []),
            "open_questions": summary.get("open_questions", []),
            "risks_concerns": summary.get("risks_concerns", []),

            # Speaker analysis
            "speakers": speakers.get("speakers", []),
            "meeting_dynamics": speakers.get("meeting_dynamics", ""),
            "dominant_speaker": speakers.get("dominant_speaker", ""),
            "collaboration_level": speakers.get("collaboration_level", "medium"),

            # Timeline
            "timeline": timeline.get("timeline", []),
            "duration_phases": timeline.get("duration_phases", []),

            # Insights
            "key_insights": insights.get("key_insights", []),
            "recommendations": insights.get("recommendations", []),
            "blockers_identified": insights.get("blockers_identified", []),
            "success_factors": insights.get("success_factors", []),
            "next_steps_summary": insights.get("next_steps_summary", ""),

            # Meta
            "word_count": len(full_transcript.split()),
            "analyzed_at": __import__("datetime").datetime.utcnow().isoformat(),
        }

    @staticmethod
    def _parse_json(text: str) -> dict:
        """Safely parse JSON from LLM output, stripping markdown fences if present."""
        text = text.strip()
        # Strip ```json ... ``` fences
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find the first JSON object in the response
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except Exception:
                    pass
        return {}
