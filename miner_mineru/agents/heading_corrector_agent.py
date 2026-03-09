"""
Heading Corrector Agent - Uses LLM to determine correct heading levels.

This agent takes unmatched headings and asks the LLM to determine the correct
heading level based on context and document structure.

Supports both single-heading and batch inference modes for cost efficiency.
"""

import json
from typing import List, Optional, Dict


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

RESPOND WITH ONLY A JSON OBJECT - NO OTHER TEXT:
{{
    "heading": "{heading_text}",
    "level": 1,
    "reasoning": "Brief explanation",
    "confidence": 0.8
}}

Replace the example values with the actual analysis. The level must be 1, 2, 3, or 4."""

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

        # Try to extract JSON from response (handle cases where model adds extra text)
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            # Try to find JSON object in the response
            import re
            json_match = re.search(r'\{[^{}]*"level"[^{}]*\}', response_text)
            if json_match:
                result = json.loads(json_match.group())
            else:
                return None

        level = result.get("level")
        confidence = result.get("confidence", 0.5)

        # Only return level if confidence is reasonable
        if confidence >= 0.6 and level in [1, 2, 3, 4]:
            return level

        return None

    except json.JSONDecodeError:
        return None
    except Exception as e:
        return None


def build_batch_heading_correction_prompt(
    headings: List[str],
    context_headings: List[tuple],
    toc_entries: List[dict],
) -> str:
    """
    Build a prompt for batch LLM inference on multiple headings at once.

    Args:
        headings: List of heading texts to analyze
        context_headings: Recent headings for context (with their levels)
        toc_entries: Available TOC entries for reference

    Returns:
        Prompt for batch LLM inference
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

    headings_list = "\n".join(f"{i + 1}. {heading}" for i, heading in enumerate(headings))

    prompt = f"""You are a document structure expert. Analyze multiple headings and determine their correct levels in the document hierarchy.

## Headings to Analyze:
{headings_list}

## Heading Level Mapping:
- Level 1 (#): Major sections, main categories (SECTION, PART, CHAPTER, ANNEX)
- Level 2 (##): Main divisions, articles (ARTICLE, ART., TITLE within section)
- Level 3 (###): Subsections, subarticles (PARA, SUBSECTION, ART. X(Y))
- Level 4 (####): Details, items, points (ITEM, CLAUSE, SUB-PARA)
{toc_section}{context_section}

## Your Task:
For EACH heading above, determine the correct heading level (1, 2, 3, or 4) based on:
1. Semantic meaning of the heading
2. How it relates to the document structure
3. Appropriate level in the hierarchy

RESPOND WITH ONLY A JSON ARRAY - NO OTHER TEXT:
[
  {{"heading": "{headings[0] if headings else 'example'}", "level": 1, "confidence": 0.8}},
  {{"heading": "next heading", "level": 2, "confidence": 0.9}}
]

Each object must have "heading", "level" (1-4), and "confidence" (0-1) fields.
Order must match the input headings list."""

    return prompt


def correct_headings_batch(
    client,
    headings: List[str],
    context_headings: List[tuple],
    toc_entries: List[dict],
) -> Dict[str, Optional[int]]:
    """
    Use LLM to determine correct heading levels for multiple headings in ONE API call.

    Args:
        client: LLM client (Anthropic or Azure)
        headings: List of heading texts to analyze
        context_headings: List of (level, text) tuples for context
        toc_entries: List of TOC entry dicts for reference

    Returns:
        Dict mapping heading text -> level (1-4) or None if cannot decide
    """
    if not headings:
        return {}

    prompt = build_batch_heading_correction_prompt(headings, context_headings, toc_entries)

    result_dict = {}

    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = response.content[0].text.strip()

        # Try to extract JSON array from response
        try:
            results = json.loads(response_text)
        except json.JSONDecodeError:
            # Try to find JSON array in the response
            import re
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                try:
                    results = json.loads(json_match.group())
                except json.JSONDecodeError:
                    return {h: None for h in headings}
            else:
                return {h: None for h in headings}

        # Process results
        if not isinstance(results, list):
            return {h: None for h in headings}

        for item in results:
            if isinstance(item, dict):
                heading = item.get("heading", "")
                level = item.get("level")
                confidence = item.get("confidence", 0.5)

                # Only use level if confidence is reasonable and level is valid
                if heading and confidence >= 0.6 and level in [1, 2, 3, 4]:
                    result_dict[heading] = level
                elif heading:
                    result_dict[heading] = None

        # Ensure all input headings are in result_dict (set to None if missing)
        for heading in headings:
            if heading not in result_dict:
                result_dict[heading] = None

        return result_dict

    except json.JSONDecodeError:
        return {h: None for h in headings}
    except Exception as e:
        return {h: None for h in headings}
