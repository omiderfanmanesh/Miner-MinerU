"""
Heading Corrector Agent - Uses LLM to determine correct heading levels.

This agent takes unmatched headings and asks the LLM to determine the correct
heading level based on context and document structure.
"""

import json
from typing import List, Optional


def build_heading_correction_prompt(
    heading_text: str,
    context_headings: List[str],
    toc_entries: List[dict],
) -> str:
    """
    Build a prompt for the LLM to determine correct heading level.

    Args:
        heading_text: The unmatched heading text
        context_headings: Recent headings for context (with their levels)
        toc_entries: Available TOC entries for reference

    Returns:
        Prompt for the LLM
    """
    toc_section = ""
    if toc_entries:
        toc_section = "\n## Available TOC Structure:\n"
        for entry in toc_entries[:10]:  # Show first 10 entries
            kind = entry.get("kind", "unknown")
            title = entry.get("title", "")
            toc_section += f"- {kind}: {title}\n"

    context_section = ""
    if context_headings:
        context_section = "\n## Document Context (recent headings):\n"
        for i, (level, text) in enumerate(context_headings[-5:]):  # Last 5
            heading_marker = "#" * level
            context_section += f"{i + 1}. {heading_marker} {text}\n"

    prompt = f"""You are a document structure expert. Analyze the heading and determine its correct level in the document hierarchy.

## Heading to Analyze:
{heading_text}

## Heading Level Mapping:
- Level 1 (#): Major sections, main categories (SECTION, PART, CHAPTER, ANNEX)
- Level 2 (##): Main divisions, articles (ARTICLE, ART., TITLE within section)
- Level 3 (###): Subsections, subarticles (PARA, SUBSECTION, ART. X(Y))
- Level 4 (####): Details, items, points (ITEM, CLAUSE, SUB-PARA)
{toc_section}{context_section}

## Your Task:
Determine the correct heading level (1, 2, 3, or 4) for the heading "{heading_text}".

Consider:
1. What is the semantic meaning of this heading?
2. How does it relate to the document structure?
3. What level is most appropriate in the hierarchy?

Respond ONLY with a JSON object in this format:
{{
    "heading": "{heading_text}",
    "level": <1, 2, 3, or 4>,
    "reasoning": "Brief explanation of why this level is correct",
    "confidence": <0.0 to 1.0>
}}

Do not include any text outside the JSON object."""

    return prompt


def correct_heading_with_llm(
    client,
    heading_text: str,
    context_headings: List[tuple],
    toc_entries: List[dict],
) -> Optional[int]:
    """
    Use LLM to determine correct heading level for an unmatched heading.

    Args:
        client: LLM client (Anthropic or Azure)
        heading_text: The heading text to analyze
        context_headings: List of (level, text) tuples for context
        toc_entries: List of TOC entry dicts for reference

    Returns:
        Correct heading level (1-4) or None if agent cannot decide
    """
    prompt = build_heading_correction_prompt(heading_text, context_headings, toc_entries)

    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = response.content[0].text.strip()

        # Parse JSON response
        result = json.loads(response_text)

        level = result.get("level")
        confidence = result.get("confidence", 0.5)

        # Only return level if confidence is reasonable
        if confidence >= 0.6 and level in [1, 2, 3, 4]:
            return level

        return None

    except json.JSONDecodeError:
        print(f"Warning: Could not parse LLM response for heading: {heading_text}")
        return None
    except Exception as e:
        print(f"Error calling LLM for heading correction: {e}")
        return None
