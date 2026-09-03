// Mirrors backend/app/schemas/*.py — kept intentionally close to the
// Pydantic models so a response can be typed as-is with no translation
// layer. Field names match the JSON the API actually returns.

export type RequirementImportance = "must_have" | "preferred";
export type RequirementCategory =
  | "technical_skill"
  | "soft_skill"
  | "education"
  | "certification"
  | "domain_experience";

export interface JobRequirement {
  id: string | null;
  name: string;
  category: RequirementCategory;
  importance: RequirementImportance;
  description: string;
  normalized_terms: string[];
  evidence_required: boolean;
  weight: number;
}

export interface JobOut {
  id: string;
  org_id: string;
  title: string;
  department: string;
  location: string;
  employment_type: string;
  description: string;
  experience_requirement: string;
  requirements: JobRequirement[];
  requirements_analyzed: boolean;
  experience_years_min: number | null;
  created_at: string;
}

export interface JobSummary {
  id: string;
  title: string;
  candidate_count: number;
  last_analysis_at: string | null;
  top_candidate_score: number | null;
  review_required_count: number;
}

export type CandidateStatus =
  | "strong_match"
  | "potential_match"
  | "review_required"
  | "low_match";

export type ResumeStatus =
  | "uploaded"
  | "parsing"
  | "analyzing"
  | "completed"
  | "failed"
  | "review_required";

export interface CandidateRow {
  application_id: string;
  display_label: string;
  match_score: number;
  evidence_confidence: number;
  document_integrity: number;
  integrity_category?: "normal" | "suspicious" | "high_risk";
  status: CandidateStatus;
  top_strengths?: string[];
  major_gaps?: string[];
  resume_status: ResumeStatus;
}

export type CandidateSummary = CandidateRow;

// Spec update "ranking, not shortlisting" — a descriptive ranking tier,
// never a hiring decision. Deliberately distinct from CandidateStatus
// above, which is the recruiter's own decision/override classification.
export type RankingStatus =
  | "top_match"
  | "strong_match"
  | "potential_match"
  | "lower_match"
  | "human_review_required";

// A recruiter's own pick for the next hiring stage — stored entirely
// separately from RankingStatus and from CandidateStatus. Any rank can be
// selected regardless of position; this is intentional human oversight.
export type SelectionStatus = "selected" | "not_selected" | "under_review";

export interface RankedCandidate {
  rank: number;
  application_id: string;
  display_label: string;
  match_score: number;
  evidence_confidence: number;
  document_integrity: number;
  must_have_coverage: number;
  preferred_coverage: number;
  transferability: number;
  ranking_status: RankingStatus;
  top_strengths: string[];
  major_gaps: string[];
  human_review_required: boolean;
  selection_status: SelectionStatus | null;
}

export interface RankingSummary {
  candidates_analyzed: number;
  top_match_label: string | null;
  average_match: number | null;
  highest_evidence_confidence: number | null;
  candidates_requiring_review: number;
}

export interface JobRankingResponse {
  job_id: string;
  job_title: string;
  ranking_version: number;
  summary: RankingSummary;
  ranking: RankedCandidate[];
}

export interface SelectionIn {
  selection_status: SelectionStatus;
  selection_reason?: string | null;
}

export interface SelectionOut {
  application_id: string;
  recruiter_id: string;
  selection_status: SelectionStatus;
  selection_reason: string | null;
  selected_at: string;
}

export type MatchStatus =
  | "exact_match"
  | "equivalent_match"
  | "partial_match"
  | "transferable"
  | "not_evidenced"
  | "conflicting"
  | "potential_gaming"
  | "human_review";

export interface EvidenceItem {
  text: string;
  source: string;
  page: number;
  chunk_id: string | null;
}

export interface RequirementAssessment {
  requirement: string;
  status: MatchStatus;
  evidence: EvidenceItem[];
  evidence_strength: number;
  skill_depth: number;
  transferability: number | null;
  relationship: string | null;
  confidence: number;
  uncertainty: string;
  verification_needed: boolean;
  verification_question: string | null;
  explanation: string;
  why_not: string | null;
}

export type ConsistencyStatus = "supported" | "unsupported" | "conflicting";

export interface ClaimEvidenceConsistency {
  claim: string;
  status: ConsistencyStatus;
  explanation: string;
}

export interface TrajectoryPoint {
  period_label: string;
  role: string;
  technologies: string[];
  responsibility_note: string;
}

export interface CareerTrajectory {
  points: TrajectoryPoint[];
  summary: string;
}

export interface AdaptabilityIndicator {
  level: "low" | "moderate" | "high";
  technology_transitions: number;
  role_transitions: number;
  explanation: string;
}

export interface GraphNode {
  id: string;
  label: string;
  kind: string; // candidate | job | requirement | skill | experience | project | achievement | certification | evidence
  status: string | null; // direct_evidence | equivalent | transferable | missing | requires_verification
}

export interface GraphEdge {
  source: string;
  target: string;
  relationship: string;
}

export interface CapabilityGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export type IntegrityCategory = "normal" | "suspicious" | "high_risk";
export type IntegritySeverity = "low" | "medium" | "high";

export interface IntegrityFlag {
  type: string;
  severity: IntegritySeverity;
  description: string;
  page: number;
  evidence_text: string;
  confidence: number;
}

export interface IntegrityReport {
  category: IntegrityCategory;
  score: number;
  flags: IntegrityFlag[];
  suppressed_terms: string[];
}

export interface InterviewQuestion {
  requirement: string;
  question: string;
  why_this_question: string;
  type?: string;
  expected_signal?: string;
}

export interface ScoreBreakdown {
  must_have_points: number;
  must_have_max: number;
  preferred_points: number;
  preferred_max: number;
  evidence_points: number;
  evidence_max: number;
  experience_points: number;
  experience_max: number;
  transferability_points: number;
  transferability_max: number;
  adaptability_points: number;
  adaptability_max: number;
  integrity_points: number;
  integrity_max: number;
}

export interface CandidateScores {
  match_score: number;
  evidence_confidence: number;
  document_integrity: number;
  breakdown: ScoreBreakdown;
  low_confidence: boolean;
}

export interface CandidateAnalysis {
  application_id: string;
  display_label: string;
  blind_mode: boolean;
  scores: CandidateScores;
  status: CandidateStatus;
  executive_summary: string;
  requirement_analysis: RequirementAssessment[];
  claim_consistency: ClaimEvidenceConsistency[];
  career_trajectory: CareerTrajectory;
  adaptability: AdaptabilityIndicator;
  capability_graph: CapabilityGraph;
  integrity: IntegrityReport;
  interview_questions: InterviewQuestion[];
  human_review_required: boolean;
  human_review_reasons: string[];
  analysis_mode: "mock" | "real";
  analysis_incomplete: boolean;
  incomplete_reason: string | null;
  created_at: string;
}

export interface RecruiterDecisionOut {
  id: string;
  application_id: string;
  original_status: CandidateStatus;
  decision: "agree" | "override" | "needs_further_review";
  final_status: CandidateStatus;
  reason: string | null;
  recruiter_id: string;
  created_at: string;
}

export interface AuthOut {
  token: string;
  user_id: string;
  email: string;
  organization_id: string;
  organization_name: string;
}

export interface AdversarialAttackReport {
  attack_type: string;
  label: string;
  injected_keywords: string[];
  detected: boolean;
  matching_impact: string;
  integrity_impact: string;
  flags_triggered: string[];
}

export interface AdversarialSuiteResult {
  source: string;
  attacks: AdversarialAttackReport[];
  summary: {
    total_attacks: number;
    detected: number;
    excluded_from_matching: number;
  };
}

export type VerificationCategory =
  | "ownership"
  | "experience"
  | "depth"
  | "scale"
  | "decision_making"
  | "troubleshooting"
  | "architecture"
  | "impact";

export type QuestionStatus =
  | "generated"
  | "reviewed"
  | "asked"
  | "verified"
  | "not_verified"
  | "skipped";

export type VerificationRecordStatus =
  | "verified"
  | "partially_verified"
  | "not_verified"
  | "inconclusive";

export interface CandidateClaim {
  id: string;
  claim: string;
  skill: string;
  claimed_level: string;
  claim_source: string;
  evidence_strength: number;
  evidence_level: "VERY_STRONG" | "STRONG" | "MODERATE" | "WEAK" | "INSUFFICIENT" | "NONE";
  evidence_gaps: string[];
  verification_required: boolean;
  consistency_note: string;
}

export interface VerificationQuestionRecord {
  id: string;
  organization_id: string;
  application_id: string;
  claim_id: string | null;
  requirement_id: string | null;
  question: string;
  purpose: string;
  evidence_gap: string;
  verification_category: VerificationCategory;
  expected_evidence: string;
  priority: number;
  status: QuestionStatus;
  recruiter_notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface VerificationRecord {
  id: string;
  organization_id: string;
  application_id: string;
  claim_id: string | null;
  question_id: string;
  recruiter_id: string;
  verification_status: VerificationRecordStatus;
  verification_notes: string;
  verified_at: string;
  created_at: string;
}

export interface VerificationSummaryPayload {
  application_id: string;
  claims: CandidateClaim[];
  questions: VerificationQuestionRecord[];
  verifications: VerificationRecord[];
}
