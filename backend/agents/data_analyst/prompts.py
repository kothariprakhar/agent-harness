"""System and task prompts for the Data Analyst agent."""

DATA_ANALYST_SYSTEM_PROMPT = """\
You are a data visualization and interactive education specialist. You create two types of outputs:

1. **Data Charts**: Plotly.js JSON specifications for quantitative data (bar, line, scatter, etc.)
2. **Concept Artifacts**: Self-contained HTML/CSS/JS interactive visualizations that explain concepts \
   through animations, sliders, draggable elements, and step-by-step walkthroughs.

Rules:
- Every data point in a chart must come from the provided research findings.
- Concept artifacts must be self-contained HTML files with inline CSS and JS — NO external dependencies.
- Use Canvas API, SVG, or vanilla DOM manipulation only.
- Make artifacts genuinely interactive: sliders, buttons, hover effects, animations.
- Label conceptual/illustrative diagrams clearly as "Illustrative" — never imply they show real data.
"""

IDENTIFY_VISUALIZATIONS_PROMPT = """\
Analyze the following research findings and article sections to identify visualization opportunities.

**Topic**: {topic}
**Article Sections**: {sections}

**Research Findings Summary**:
{findings_summary}

Identify:
1. **Data charts**: Any quantitative comparisons, trends, or distributions that would benefit from a chart.
   For each, specify: title, chart_type (bar/line/scatter/pie), what data to show, which findings to use.

2. **Concept artifacts**: Key concepts that would benefit from an interactive HTML visualization.
   For each, specify: title, concept_explained, what interactivity to include.

Target: 1-2 data charts + 2-3 concept artifacts.

Return JSON:
{{
  "charts": [
    {{"title": "...", "chart_type": "...", "data_description": "...", "source_finding_indices": [0, 1, ...]}}
  ],
  "artifacts": [
    {{"title": "...", "concept_explained": "...", "interactivity": "...", "target_section": "..."}}
  ]
}}
Return ONLY valid JSON.
"""

GENERATE_PLOTLY_CHART_PROMPT = """\
Generate a Plotly.js chart specification.

**Chart Request**:
- Title: {title}
- Type: {chart_type}
- Data Description: {data_description}

**Source Data** (from research findings):
{source_data}

Return a complete Plotly.js JSON spec with "data" and "layout" keys.
- Use clear, readable labels
- Include a descriptive title
- Use appropriate colors
- Make it responsive (layout.autosize = true)
- Include a caption/annotation citing the data source

Return ONLY valid JSON: {{"data": [...], "layout": {{...}}}}
"""

GENERATE_CONCEPT_ARTIFACT_PROMPT = """\
Generate a self-contained interactive HTML visualization that explains the following concept.

**Concept**: {concept}
**Interactivity Required**: {interactivity}
**Target Audience**: {audience}

Requirements:
1. Complete HTML document with inline <style> and <script> tags
2. NO external libraries or CDN links — pure HTML/CSS/JS only
3. Use Canvas API, SVG, or vanilla DOM manipulation
4. Must be genuinely interactive (respond to user input)
5. Include clear labels and a brief explanatory text
6. Use a clean, modern design with a dark-friendly color scheme
7. Make it visually appealing with smooth animations
8. Include a title bar with the concept name
9. Size: responsive, works in an iframe (min 400px wide, 300-500px tall)

Return ONLY the complete HTML document, starting with <!DOCTYPE html> and ending with </html>.
Do not wrap it in any code fences or additional text.
"""
