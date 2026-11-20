"""
ManuMind AI — Secure Human Approval Gate and Cryptographic Token Verification
Phase 4 Step 6: Secure Maintenance Ticket Creation Architecture

Department of AI & Data Science — RMK Engineering College
"""

import abc
import base64
import hashlib
import hmac
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("manumind-mcp-server")

# Environment variable name holding the HMAC signing key
APPROVAL_SECRET_ENV_VAR = "MANUMIND_APPROVAL_SECRET_KEY"

# Canonical token configuration
TOKEN_ALGORITHM = "HS256"
TOKEN_VERSION = 1
TOKEN_ISSUER = "manumind-human-approval-gate"
TOKEN_ACTION = "APPROVE_MAINTENANCE_TICKET"
DEFAULT_TOKEN_EXPIRY_SECONDS = 900  # 15 minutes


# ===========================================================================
# Exception Hierarchy
# ===========================================================================

class ApprovalSecurityError(Exception):
    """Base exception for all approval security violations."""
    pass


class ApprovalConfigurationError(ApprovalSecurityError):
    """Raised when the approval service is misconfigured (e.g., missing secret key)."""
    pass


class InvalidTokenError(ApprovalSecurityError):
    """Raised when an authorization token is malformed or signature fails verification."""
    pass


class TokenExpiredError(ApprovalSecurityError):
    """Raised when an authorization token has expired."""
    pass


class TokenReplayError(ApprovalSecurityError):
    """Raised when an authorization token has already been consumed (replay attack)."""
    pass


class TokenProposalMismatchError(ApprovalSecurityError):
    """Raised when a token was issued for a different proposal ID."""
    pass


class TokenPayloadMismatchError(ApprovalSecurityError):
    """Raised when proposal payload does not match the token's cryptographic binding."""
    pass


class ProposalNotPendingError(ApprovalSecurityError):
    """Raised when a proposal is not in PENDING_APPROVAL status."""
    pass


class ProposalExpiredError(ApprovalSecurityError):
    """Raised when a proposal validity window has expired."""
    pass


class UnauthorizedApproverError(ApprovalSecurityError):
    """Raised when an approver identity or credential fails authentication."""
    pass


# ===========================================================================
# Base64URL Encoding / Decoding Utilities
# ===========================================================================

def base64url_encode(data: bytes) -> str:
    """Encodes bytes to standard base64url string without trailing padding."""
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def base64url_decode(data: str) -> bytes:
    """Decodes standard base64url string with appropriate padding."""
    rem = len(data) % 4
    if rem > 0:
        data += "=" * (4 - rem)
    return base64.urlsafe_b64decode(data.encode("ascii"))


# ===========================================================================
# Canonical Proposal Payload Hashing
# ===========================================================================

def compute_canonical_payload_hash(
    machine_id: str,
    recommendation: str,
    evidence: Dict[str, Any],
    alert_id: Optional[str] = None,
    confidence: float = 0.85,
) -> str:
    """
    Computes a deterministic, tamper-evident SHA-256 hash of proposal fields.

    Guarantees:
    - Invariant to dictionary key insertion order (sorted keys).
    - Invariant to whitespace differences in container formatting.
    - Normalized string trimming and fixed float precision.
    - Any modification to machine_id, recommendation, evidence, alert_id,
      or confidence produces an entirely different hash digest.
    """
    if not isinstance(machine_id, str) or not machine_id.strip():
        raise ValueError("machine_id must be a non-empty string")
    if not isinstance(recommendation, str) or not recommendation.strip():
        raise ValueError("recommendation must be a non-empty string")
    if not isinstance(evidence, dict):
        raise ValueError("evidence must be a dictionary")

    canonical_obj = {
        "alert_id": alert_id.strip() if alert_id else None,
        "confidence": round(float(confidence), 6),
        "evidence": evidence,
        "machine_id": machine_id.strip(),
        "recommendation": recommendation.strip(),
    }

    serialized_bytes = json.dumps(
        canonical_obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")

    return hashlib.sha256(serialized_bytes).hexdigest()


# ===========================================================================
# Cryptographic Token Manager (HMAC-SHA256)
# ===========================================================================

class HMACApprovalTokenManager:
    """
    Manages issuance and constant-time verification of short-lived approval tokens.

    Security Boundaries:
    - Signs tokens using HMAC-SHA256 with key from MANUMIND_APPROVAL_SECRET_KEY.
    - Rejects tokens if secret key is missing (fails closed).
    - Verifies token signature using constant-time comparison (hmac.compare_digest).
    - Enforces expiration window (exp) and token action.
    - Binds token to exact proposal ID and proposal payload hash.
    """

    @classmethod
    def get_secret_key(cls) -> bytes:
        """
        Retrieves the secret signing key from the secure environment.
        Fails closed if the secret is missing or empty.
        """
        secret = os.environ.get(APPROVAL_SECRET_ENV_VAR)
        if not secret or not secret.strip():
            raise ApprovalConfigurationError(
                f"HMAC signing key '{APPROVAL_SECRET_ENV_VAR}' is not configured in environment. "
                "The approval gate fails closed to prevent unauthorized ticket creation."
            )
        return secret.strip().encode("utf-8")

    @classmethod
    def issue_token(
        cls,
        proposal_id: str,
        payload_hash: str,
        approver_id: str,
        approver_role: str,
        validity_seconds: int = DEFAULT_TOKEN_EXPIRY_SECONDS,
        secret_key_override: Optional[bytes] = None,
    ) -> str:
        """
        Generates and signs a cryptographically bound authorization token.
        """
        secret_key = secret_key_override or cls.get_secret_key()

        if not proposal_id or not str(proposal_id).strip():
            raise ValueError("proposal_id must be non-empty")
        if not payload_hash or len(str(payload_hash).strip()) != 64:
            raise ValueError("payload_hash must be a valid 64-character SHA-256 hex string")
        if not approver_id or not str(approver_id).strip():
            raise ValueError("approver_id must be non-empty")

        now = datetime.now(timezone.utc)
        exp = now + timedelta(seconds=validity_seconds)

        header = {
            "alg": TOKEN_ALGORITHM,
            "typ": "JWT",
        }

        claims = {
            "jti": str(uuid.uuid4()),
            "proposal_id": str(proposal_id).strip(),
            "payload_hash": str(payload_hash).strip().lower(),
            "approver_id": str(approver_id).strip(),
            "approver_role": str(approver_role).strip(),
            "action": TOKEN_ACTION,
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
            "v": TOKEN_VERSION,
            "iss": TOKEN_ISSUER,
        }

        header_b64 = base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        claims_b64 = base64url_encode(json.dumps(claims, separators=(",", ":")).encode("utf-8"))
        signing_input = f"{header_b64}.{claims_b64}".encode("utf-8")

        signature = hmac.new(secret_key, signing_input, hashlib.sha256).digest()
        sig_b64 = base64url_encode(signature)

        return f"{header_b64}.{claims_b64}.{sig_b64}"

    @classmethod
    def verify_token(
        cls,
        token: str,
        expected_proposal_id: str,
        expected_payload_hash: str,
        secret_key_override: Optional[bytes] = None,
        clock_skew_seconds: int = 5,
    ) -> Dict[str, Any]:
        """
        Validates the authorization token:
        1. Validates structure (header.claims.signature).
        2. Validates algorithm (must be HS256).
        3. Validates HMAC signature via constant-time comparison.
        4. Validates issuer, action, version, and expiry.
        5. Validates binding to expected proposal_id and payload_hash.
        """
        secret_key = secret_key_override or cls.get_secret_key()

        if not token or not isinstance(token, str):
            raise InvalidTokenError("Authorization token must be a non-empty string.")

        parts = token.strip().split(".")
        if len(parts) != 3:
            raise InvalidTokenError(
                f"Malformed token: expected 3 dot-separated segments, received {len(parts)}."
            )

        header_b64, claims_b64, sig_b64 = parts

        # 1. Parse header
        try:
            header_bytes = base64url_decode(header_b64)
            header = json.loads(header_bytes.decode("utf-8"))
        except Exception as exc:
            raise InvalidTokenError(f"Failed to decode token header: {exc}")

        if not isinstance(header, dict) or header.get("alg") != TOKEN_ALGORITHM:
            raise InvalidTokenError(
                f"Unsupported or invalid algorithm '{header.get('alg')}'; strictly '{TOKEN_ALGORITHM}' required."
            )

        # 2. Verify signature
        signing_input = f"{header_b64}.{claims_b64}".encode("utf-8")
        expected_sig = hmac.new(secret_key, signing_input, hashlib.sha256).digest()

        try:
            received_sig = base64url_decode(sig_b64)
        except Exception as exc:
            raise InvalidTokenError(f"Failed to decode token signature: {exc}")

        if not hmac.compare_digest(expected_sig, received_sig):
            raise InvalidTokenError("Cryptographic signature verification failed: signature does not match.")

        # 3. Parse claims
        try:
            claims_bytes = base64url_decode(claims_b64)
            claims = json.loads(claims_bytes.decode("utf-8"))
        except Exception as exc:
            raise InvalidTokenError(f"Failed to decode token claims: {exc}")

        if not isinstance(claims, dict):
            raise InvalidTokenError("Token claims payload must be a JSON object.")

        # 4. Mandatory claims checks
        for field in ("jti", "proposal_id", "payload_hash", "approver_id", "action", "iat", "exp", "v", "iss"):
            if field not in claims:
                raise InvalidTokenError(f"Missing mandatory token claim '{field}'.")

        if claims.get("iss") != TOKEN_ISSUER:
            raise InvalidTokenError(f"Untrusted token issuer '{claims.get('iss')}'; expected '{TOKEN_ISSUER}'.")

        if claims.get("action") != TOKEN_ACTION:
            raise InvalidTokenError(f"Invalid token action '{claims.get('action')}'; expected '{TOKEN_ACTION}'.")

        if claims.get("v") != TOKEN_VERSION:
            raise InvalidTokenError(f"Unsupported token version '{claims.get('v')}'; expected {TOKEN_VERSION}.")

        # 5. Temporal validity
        now_ts = datetime.now(timezone.utc).timestamp()
        exp_ts = float(claims["exp"])
        if now_ts > (exp_ts + clock_skew_seconds):
            raise TokenExpiredError(
                f"Authorization token expired at timestamp {exp_ts} (current time: {int(now_ts)})."
            )

        # 6. Proposal and payload binding
        token_prop_id = str(claims["proposal_id"]).strip()
        if token_prop_id != expected_proposal_id.strip():
            raise TokenProposalMismatchError(
                f"Token is bound to proposal '{token_prop_id}', but invocation target is '{expected_proposal_id}'."
            )

        token_hash = str(claims["payload_hash"]).strip().lower()
        target_hash = str(expected_payload_hash).strip().lower()
        if token_hash != target_hash:
            raise TokenPayloadMismatchError(
                "Cryptographic binding failure: Token payload hash does not match stored proposal hash. "
                "Recommendation or evidence may have been modified after human approval."
            )

        return claims


# ===========================================================================
# Human Approval Provider Interface & Development Adapter
# ===========================================================================

class HumanApprovalProvider(abc.ABC):
    """
    Abstract interface for human authentication and approval token issuance.
    """

    @abc.abstractmethod
    def authenticate_and_approve(
        self,
        engineer_id: str,
        credential: str,
        proposal_id: str,
        proposal_data: Dict[str, Any],
        validity_seconds: int = DEFAULT_TOKEN_EXPIRY_SECONDS,
    ) -> str:
        """
        Authenticates an engineer and issues an HMAC-signed approval token
        for the specified proposal.
        """
        pass


class DevelopmentHumanApprovalAdapter(HumanApprovalProvider):
    """
    Development and test fixture adapter for human approval.

    DISCLAIMER:
    This adapter is intended strictly for development and automated test verification.
    It verifies engineer identity against a mock authorization registry.
    In production environments, this component must be replaced with enterprise
    WebAuthn/FIDO2, RMK SSO, or OAuth2 hardware-token authentication.
    """

    # Mock registry of authorized engineers and their roles
    APPROVED_ENGINEERS: Dict[str, Dict[str, str]] = {
        "ENG-RAMAN-01": {
            "name": "Lead Engineer S. Raman",
            "role": "Lead Reliability Engineer",
            "credential": "RamanSecurePass2026!",
        },
        "ENG-PATEL-02": {
            "name": "Chief Engineer K. Patel",
            "role": "Chief Maintenance Engineer",
            "credential": "PatelSecurePass2026!",
        },
        "ENG-SHARMA-03": {
            "name": "Senior Plant Engineer A. Sharma",
            "role": "Senior Plant Engineer",
            "credential": "SharmaSecurePass2026!",
        },
    }

    def authenticate_and_approve(
        self,
        engineer_id: str,
        credential: str,
        proposal_id: str,
        proposal_data: Dict[str, Any],
        validity_seconds: int = DEFAULT_TOKEN_EXPIRY_SECONDS,
    ) -> str:
        """
        Authenticates the engineer against the mock registry, re-verifies the
        canonical proposal hash, and issues a signed token.
        """
        record = self.APPROVED_ENGINEERS.get(engineer_id)
        if not record or not hmac.compare_digest(record["credential"], credential):
            logger.warning(f"Authentication failed for engineer ID '{engineer_id}' in Development Adapter.")
            raise UnauthorizedApproverError(
                f"Engineer authentication failed for '{engineer_id}'. Invalid credentials or unauthorized personnel."
            )

        # Verify the proposal data contains the canonical hash
        expected_hash = compute_canonical_payload_hash(
            machine_id=proposal_data["machine_id"],
            recommendation=proposal_data["recommendation"],
            evidence=proposal_data["evidence"],
            alert_id=proposal_data.get("alert_id"),
            confidence=proposal_data.get("confidence", 0.85),
        )

        if proposal_data.get("payload_hash") and proposal_data["payload_hash"].lower() != expected_hash.lower():
            raise TokenPayloadMismatchError("Proposal data has been altered: computed hash does not match payload_hash.")

        logger.info(
            f"[DEVELOPMENT ADAPTER] Authenticated '{record['name']}' ({record['role']}) for proposal '{proposal_id}'."
        )

        return HMACApprovalTokenManager.issue_token(
            proposal_id=proposal_id,
            payload_hash=expected_hash,
            approver_id=record["name"],
            approver_role=record["role"],
            validity_seconds=validity_seconds,
        )
