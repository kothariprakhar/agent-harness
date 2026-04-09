// Types matching backend Pydantic models

export interface ResearchFinding {
  claim: string;
  source_url: string;
  source_title: string;
  supporting_quote: string;
  confidence: number;
  search_query: string;
}

export interface Citation {
  index: number;
  source_url: string;
  source_title: string;
  claim_text: string;
}

export interface ArticleDraft {
  markdown: string;
  citations: Citation[];
  word_count: number;
  sections: string[];
}

export interface CriticIssue {
  severity: string;
  location: string;
  description: string;
  suggestion: string;
}

export interface CriticReport {
  passed: boolean;
  citation_accuracy: number;
  claim_grounding_score: number;
  internal_consistency: number;
  audience_alignment: number;
  completeness: number;
  overall_score: number;
  style_match: number;
  issues: CriticIssue[];
  suggestions: string[];
  revision_required: boolean;
}

export interface ChartSpec {
  chart_id: string;
  title: string;
  chart_type: string;
  plotly_json: { data: any[]; layout: any };
  data_sources: string[];
  caption: string;
  placement_hint: string;
}

export interface ConceptArtifact {
  artifact_id: string;
  title: string;
  html_content: string;
  concept_explained: string;
  interactivity_description: string;
  placement_hint: string;
}

export interface TokenUsage {
  agent: string;
  input_tokens: number;
  output_tokens: number;
}

export interface PipelineResult {
  article: ArticleDraft;
  research: {
    findings: ResearchFinding[];
    queries_used: string[];
    total_sources_consulted: number;
  };
  charts: ChartSpec[];
  artifacts: ConceptArtifact[];
  evaluation: CriticReport;
  token_usage: TokenUsage[];
  revision_count: number;
  total_time_seconds: number;
}

export interface PipelineEvent {
  type: string;
  data: {
    message?: string;
    [key: string]: any;
  };
}

// ── Knowledge Base Types ──────────────────────────────────────────────────

export interface StyleProfile {
  tone_descriptors: string[];
  sentence_style: string;
  vocabulary_level: string;
  formatting_patterns: string[];
  structural_template: string[];
  exemplary_passages: string[];
  avg_sentence_length: number;
  avg_section_count: number;
  uses_citations: boolean;
  uses_subheadings: boolean;
}

export interface KBArticle {
  id: string;
  filename: string;
  title: string;
  upload_date: string;
  tags: string[];
  word_count: number;
  format: string;
  style_profile: StyleProfile | null;
}

export interface CompositeStyleGuide {
  article_count: number;
  avg_tone: string[];
  avg_vocabulary_level: string;
  structural_template: string[];
  formatting_rules: string[];
  exemplary_passages: string[];
  full_style_prompt: string;
}

export type AgentName = "orchestrator" | "researcher" | "writer" | "critic" | "data_analyst";

export interface AgentNodeData {
  name: AgentName;
  label: string;
  status: "idle" | "working" | "completed" | "failed";
  message: string;
}
