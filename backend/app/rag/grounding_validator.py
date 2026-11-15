"""
ManuMind AI — Grounded Answer Validation Engine
Phase 3 Step 6: Grounded Generation Pipeline

Department of AI & Data Science — RMK Engineering College
"""

import re
from typing import Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field

from backend.app.rag.context_builder import EvidenceContext
from backend.app.rag.generation_schemas import GroundedAnswer


class ValidationResult(BaseModel):
    """Result of independent post-generation grounding audit."""
    is_valid: bool = True
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class NumericalClaim:
    """Represents an extracted engineering measurement claim or range claim."""

    def __init__(
        self,
        full_match: str,
        is_range: bool,
        num1: str,
        num2: Optional[str],
        unit: str,
    ):
        self.full_match = full_match
        self.is_range = is_range
        self.num1 = num1
        self.num2 = num2
        self.unit = unit

    def __iter__(self):
        """Allows unpacking as (full_match, num_str, unit) for backwards compatibility."""
        num_str = f"{self.num1}-{self.num2}" if self.is_range else self.num1
        return iter((self.full_match, num_str, self.unit))

    def __repr__(self) -> str:
        if self.is_range:
            return f"NumericalClaim(range='{self.full_match}', endpoints=({self.num1}, {self.num2}), unit='{self.unit}')"
        return f"NumericalClaim(single='{self.full_match}', num='{self.num1}', unit='{self.unit}')"


class GroundingValidator:
    """
    Enforces strict grounding integrity, citation existence, machine isolation,
    numerical claim support (integers, decimals, comma-formatted numbers, ranges),
    and prohibition of fabricated specifications.
    """

    CITATION_REGEX = re.compile(r"\[CIT-(\d+)\]")
    CAUSALITY_VIOLATION_PATTERNS = [
        re.compile(r"\bproven\s+physical\s+root\s+cause\b", re.IGNORECASE),
        re.compile(r"\bdefinitively\s+confirmed\s+root\s+cause\b", re.IGNORECASE),
        re.compile(r"\bsensor\s+telemetry\s+proves\s+that\b", re.IGNORECASE),
        re.compile(r"\bguaranteed\s+failure\s+source\b", re.IGNORECASE),
    ]

    NUM_PATTERN_STR = r"(?:\d{1,2}(?:,\d{2})+,\d{3}|\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
    CONNECTOR_STR = r"(?:\s*[-–]\s*|\s+to\s+)"

    ALL_UNITS_STR = (
        r"(?:"
        r"RPM|rpm|rev/min|"
        r"bar|psi|kPa|MPa|"
        r"mm/s|mm/sec|"
        r"°C|deg(?:rees?)?\s*C|degc|"
        r"%|percent|"
        r"amps?|amperes?|volts?|VAC|VDC|kW|kw|MW|A|V|W|"
        r"mm|cm|µm|microns?|um|"
        r"ms|sec|seconds?|min|minutes?|hours?|hrs?"
        r")"
    )

    RANGE_REGEX = re.compile(
        rf"(?<![\d,])(?P<num1>{NUM_PATTERN_STR}){CONNECTOR_STR}(?P<num2>{NUM_PATTERN_STR})\s*(?P<unit>{ALL_UNITS_STR})(?!\w)",
        re.IGNORECASE,
    )

    SINGLE_REGEX = re.compile(
        rf"(?<![\d,])(?P<num>{NUM_PATTERN_STR})\s*(?P<unit>{ALL_UNITS_STR})(?!\w)",
        re.IGNORECASE,
    )

    COMMA_NUM_CHUNK = r"(?<![\d,])(?P<raw>\d+[\d,]*?,[\d,]*?\d+)(?:\.\d+)?"
    ANY_COMMA_NUM_REGEX = re.compile(
        rf"{COMMA_NUM_CHUNK}(?:\s*(?:{ALL_UNITS_STR})|{CONNECTOR_STR}\s*\d+[\d,.]*\s*(?:{ALL_UNITS_STR}))(?!\w)",
        re.IGNORECASE,
    )

    KNOWN_ABBREVIATIONS = {
        "e.g.", "i.e.", "rev.", "fig.", "approx.", "no.", "ref.", "vol.", "dept.", "min.", "sec.", "vs.", "inc.", "corp.", "ltd."
    }

    def split_into_statements(self, text: str) -> List[str]:
        """
        Split text into verifiable statements / sentences.
        Preserves citation tokens attached before or after sentence delimiters (. ! ? ;).
        Avoids splitting on decimals (e.g. 0.005) or known abbreviations (e.g., Rev.).
        Handles bulleted lists, markdown headers, and multi-sentence lines.
        """
        if not text or not text.strip():
            return []

        statements: List[str] = []
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        pattern = re.compile(
            r"([.!?]|;)"                       # terminal punctuation or clause separator
            r"((?:\s*\[CIT-\d+\])*)"          # attached citation tokens (e.g. '. [CIT-1] [CIT-2]')
            r"(?=\s+[a-zA-Z0-9\[\-\*\"']|$)", # lookahead: space followed by start of new sentence/token or EOL
        )

        for line in lines:
            bullet_match = re.match(r"^(\s*[-*]\s+|\s*\d+\.\s+)", line)
            line_content = line
            if bullet_match:
                line_content = line[bullet_match.end():]

            pos = 0
            candidates = []
            for m in pattern.finditer(line_content):
                delim = m.group(1)
                end_idx = m.end()
                segment = line_content[pos:end_idx].strip()

                # Guard against splitting on decimals (e.g. 0.005, 12.5)
                dot_idx = m.start(1)
                if delim == "." and dot_idx > 0 and dot_idx < len(line_content) - 1:
                    if line_content[dot_idx - 1].isdigit() and line_content[dot_idx + 1].isdigit():
                        continue

                # Guard against splitting on known abbreviations
                words = segment.split()
                if words and words[-1].lower() in self.KNOWN_ABBREVIATIONS:
                    continue

                if segment:
                    candidates.append(segment)
                pos = end_idx

            remainder = line_content[pos:].strip()
            if remainder:
                candidates.append(remainder)

            statements.extend(candidates)

        return statements

    def detect_malformed_numerical_claims(self, text: str) -> List[str]:
        """
        Detect numerical expressions with malformed comma grouping before engineering units,
        such as '12,50 RPM' or '1,23,45 RPM'.
        """
        malformed: List[str] = []
        valid_spans: List[Tuple[int, int]] = []
        for m in self.RANGE_REGEX.finditer(text):
            valid_spans.append((m.start(), m.end()))
        for m in self.SINGLE_REGEX.finditer(text):
            valid_spans.append((m.start(), m.end()))

        for m in self.ANY_COMMA_NUM_REGEX.finditer(text):
            m_start, m_end = m.start(), m.end()
            is_covered = any(v_start <= m_start and m_end <= v_end for v_start, v_end in valid_spans)
            if not is_covered:
                malformed.append(m.group(0))

        return malformed

    def extract_numerical_claims(self, text: str) -> List[NumericalClaim]:
        """
        Extract numerical claims associated with engineering units from text.
        Extracts both single measurement claims (e.g. '6,000 RPM') and range
        expressions (e.g. '120-150 bar', '120 to 150 bar', '0.005-0.010 mm').
        Returns list of NumericalClaim objects (which unpack as 3-tuples for compatibility).
        """
        claims: List[NumericalClaim] = []
        range_spans: List[Tuple[int, int]] = []

        # 1. Extract ranges first
        for m in self.RANGE_REGEX.finditer(text):
            claims.append(
                NumericalClaim(
                    full_match=m.group(0),
                    is_range=True,
                    num1=m.group("num1"),
                    num2=m.group("num2"),
                    unit=m.group("unit"),
                )
            )
            range_spans.append((m.start(), m.end()))

        # 2. Extract single numerical claims that do not overlap with ranges
        for m in self.SINGLE_REGEX.finditer(text):
            m_start, m_end = m.start(), m.end()
            overlaps = any(r_start <= m_start and m_end <= r_end for r_start, r_end in range_spans)
            if not overlaps:
                claims.append(
                    NumericalClaim(
                        full_match=m.group(0),
                        is_range=False,
                        num1=m.group("num"),
                        num2=None,
                        unit=m.group("unit"),
                    )
                )

        return claims

    def _get_unit_regex(self, unit: str) -> str:
        """Map unit alias or symbol to canonical case-insensitive regex pattern."""
        unit_l = unit.lower().strip()
        if unit_l in ["rpm", "rev/min"]:
            return r"(?:rpm|rev/min)"
        elif unit_l == "bar":
            return r"bar"
        elif unit_l == "psi":
            return r"psi"
        elif unit_l in ["kpa", "mpa"]:
            return re.escape(unit_l)
        elif unit_l in ["mm/s", "mm/sec"]:
            return r"(?:mm/s|mm/sec)"
        elif unit_l in ["°c", "deg c", "degrees c", "degc"]:
            return r"(?:°c|deg\s*c|degrees?\s*c|degc)"
        elif unit_l in ["%", "percent"]:
            return r"(?:%|percent)"
        elif unit_l in ["amps", "amp", "amperes", "a"]:
            return r"(?:amps?|amperes?|a)"
        elif unit_l in ["volts", "volt", "v", "vac", "vdc"]:
            return r"(?:volts?|vac|vdc|v)"
        elif unit_l in ["kw", "w", "mw"]:
            return r"(?:kw|mw|w)"
        elif unit_l in ["mm", "cm", "µm", "micron", "microns", "um"]:
            return r"(?:mm|cm|µm|microns?|um)"
        elif unit_l in ["ms", "sec", "seconds?", "min", "minutes?", "hours?", "hrs?"]:
            return r"(?:ms|sec|seconds?|min|minutes?|hours?|hrs?)"
        return re.escape(unit_l)

    def _verify_single_number_in_evidence(self, num: str, unit: str, evidence_text: str) -> bool:
        """
        Verify that a specific number and compatible unit appear in the evidence text,
        either directly (e.g. '120 bar') or as part of a range (e.g. '120-150 bar' or '100 to 120 bar').
        """
        if not evidence_text:
            return False

        # Normalize number formatting (e.g. 6,000 -> 6000)
        norm_ev = re.sub(r"(\d),(\d)", r"\1\2", evidence_text.lower())
        norm_num = num.replace(",", "").strip().lower()
        unit_pat = self._get_unit_regex(unit)

        # 1. Direct match: e.g. "120 bar"
        direct_pat = rf"\b{re.escape(norm_num)}\s*(?:{unit_pat})(?!\w)"
        if re.search(direct_pat, norm_ev):
            return True

        # 2. Lower endpoint of a range in evidence: e.g. "120-150 bar" or "120 to 150 bar"
        lower_range_pat = (
            rf"\b{re.escape(norm_num)}{self.CONNECTOR_STR}{self.NUM_PATTERN_STR}\s*(?:{unit_pat})(?!\w)"
        )
        if re.search(lower_range_pat, norm_ev):
            return True

        # 3. Upper endpoint of a range in evidence: e.g. "100-120 bar" or "100 to 120 bar"
        upper_range_pat = (
            rf"\b{self.NUM_PATTERN_STR}{self.CONNECTOR_STR}{re.escape(norm_num)}\s*(?:{unit_pat})(?!\w)"
        )
        if re.search(upper_range_pat, norm_ev):
            return True

        return False

    def _verify_numerical_in_evidence(self, num: str, unit: str, evidence_text: str) -> bool:
        """
        Verify that a single numerical claim appears in the cited evidence.
        Preserves backwards compatibility for direct caller invocations.
        """
        return self._verify_single_number_in_evidence(num, unit, evidence_text)

    def _verify_claim_in_evidence(self, claim: NumericalClaim, evidence_text: str) -> bool:
        """
        Verify an extracted NumericalClaim against evidence text.
        For ranges, verifies that BOTH endpoints are supported by the cited evidence.
        """
        if not claim.is_range:
            return self._verify_single_number_in_evidence(claim.num1, claim.unit, evidence_text)
        else:
            return (
                self._verify_single_number_in_evidence(claim.num1, claim.unit, evidence_text)
                and self._verify_single_number_in_evidence(claim.num2, claim.unit, evidence_text)
            )

    def validate(
        self,
        answer: GroundedAnswer,
        context: EvidenceContext,
    ) -> ValidationResult:
        """
        Audit a generated response against the supplied evidence context.
        Args:
            answer: Generated GroundedAnswer instance.
            context: EvidenceContext containing authoritative source blocks.
        Returns:
            ValidationResult model with errors and warnings.
        """
        errors: List[str] = []
        warnings: List[str] = []

        # If answer is abstained, verify justification exists
        if answer.abstained:
            if not answer.abstention_reason:
                errors.append("Answer is marked abstained=True but lacks an abstention_reason")
            return ValidationResult(is_valid=(len(errors) == 0), errors=errors, warnings=warnings)

        # 1. Non-empty answer validation
        if not answer.answer or not answer.answer.strip():
            errors.append("Answer text is empty or whitespace-only for non-abstained response")

        if not answer.citations:
            errors.append("Answer does not contain citations for non-abstained response")

        # 2. Citation Token Existence & Metadata Integrity
        cited_in_text: Set[str] = set(self.CITATION_REGEX.findall(answer.answer))
        for obs in answer.observed_evidence:
            cited_in_text.update(self.CITATION_REGEX.findall(obs))
        for exp in answer.possible_explanations:
            cited_in_text.update(self.CITATION_REGEX.findall(exp))
        for rec in answer.recommended_investigations:
            cited_in_text.update(self.CITATION_REGEX.findall(rec))

        formatted_tokens = {f"[CIT-{num}]" for num in cited_in_text}

        # Check if citations were provided
        if not answer.citations and formatted_tokens:
            errors.append("Answer text references citation tokens but answer.citations list is empty")

        for cit in answer.citations:
            # Check for missing required citation metadata fields
            if not cit.citation_id or not cit.document_id or not cit.source_path:
                errors.append(f"Malformed citation metadata: missing required fields in {cit}")
                continue

            # Check citation ID exists in context map
            if cit.citation_id not in context.citation_map:
                errors.append(f"Hallucinated citation ID {cit.citation_id} not in context citation map")
                continue

            ref = context.citation_map[cit.citation_id]

            # Verify document ID match
            if cit.document_id != ref.document_id:
                errors.append(
                    f"Citation {cit.citation_id} document_id mismatch: claimed '{cit.document_id}', actual '{ref.document_id}'"
                )

            # Verify source path match
            if cit.source_path != ref.source_path:
                errors.append(
                    f"Citation {cit.citation_id} source_path mismatch: claimed '{cit.source_path}', actual '{ref.source_path}'"
                )

        # Verify any tokens in text exist in citations
        valid_citation_ids = {c.citation_id for c in answer.citations}
        for token in formatted_tokens:
            if token not in valid_citation_ids:
                errors.append(f"Citation token {token} appears in text but was not registered in citations metadata")

        # 3. Machine Identity Consistency
        if context.target_machine_id:
            target_upper = context.target_machine_id.upper()
            for cit in answer.citations:
                if cit.machine_id and cit.machine_id not in [target_upper, "NONE"]:
                    errors.append(
                        f"Machine mismatch: query targeted {target_upper} but citation {cit.citation_id} is from asset {cit.machine_id}"
                    )

        # 4. Causality Language Verification
        full_text = f"{answer.answer} {' '.join(answer.possible_explanations)}"
        for pattern in self.CAUSALITY_VIOLATION_PATTERNS:
            if pattern.search(full_text):
                errors.append(
                    "Causality violation: response claims sensor correlation is a proven physical root cause without teardown"
                )
                break

        # 5. Specification Placeholder Verification
        if context.has_placeholders:
            lower_text = answer.answer.lower()
            if not any(kw in lower_text for kw in ["placeholder", "unspecified", "undefined", "specification required", "missing spec"]):
                warnings.append(
                    "Retrieved evidence contains [SPEC_REQUIRED:...] placeholders but response does not explicitly disclose missing specification"
                )

        # 6. Synthetic Provenance Disclosure
        if not answer.is_synthetic:
            errors.append("Synthetic disclosure failure: answer.is_synthetic must be True for demonstration corpus")

        # 7. Numerical Claim Grounding Verification with Sentence-Level Isolation
        raw_blocks = (
            [answer.answer]
            + answer.observed_evidence
            + answer.possible_explanations
            + answer.recommended_investigations
        )
        statements: List[str] = []
        for block in raw_blocks:
            statements.extend(self.split_into_statements(block))

        for stmt in statements:
            # Check for malformed comma grouping syntax first
            malformed_claims = self.detect_malformed_numerical_claims(stmt)
            for mal in malformed_claims:
                errors.append(
                    f"Malformed numerical grouping '{mal}' found in statement: invalid thousands grouping syntax"
                )

            claims = self.extract_numerical_claims(stmt)
            if not claims:
                continue

            cits_in_stmt = [f"[CIT-{c}]" for c in self.CITATION_REGEX.findall(stmt)]
            if not cits_in_stmt:
                for claim in claims:
                    errors.append(
                        f"Uncited numerical claim '{claim.full_match}' found in statement without supporting citation: '{stmt}'"
                    )
                continue

            for claim in claims:
                supported = False
                for cit_id in cits_in_stmt:
                    ev_text = context.evidence_text_map.get(cit_id)
                    if not ev_text and cit_id in context.citation_map:
                        ev_text = context.citation_map[cit_id].snippet
                    if ev_text and self._verify_claim_in_evidence(claim, ev_text):
                        supported = True
                        break

                if not supported:
                    errors.append(
                        f"Unsupported numerical claim '{claim.full_match}' cited to {cits_in_stmt} was not found in cited evidence"
                    )

        is_valid = len(errors) == 0
        return ValidationResult(is_valid=is_valid, errors=errors, warnings=warnings)


grounding_validator = GroundingValidator()
