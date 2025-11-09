"""Certificate data models for certcat functionality.

This module provides X.509 certificate representations including:
- Certificate entity with validation and trust status
- Certificate chain representation
- Public key information
- Trust validation helpers

T021: Certificate model implementation.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Dict, Any


class KeyAlgorithm(Enum):
    """Supported public key algorithms."""
    RSA = "RSA"
    ECDSA = "ECDSA"
    DSA = "DSA"
    ED25519 = "Ed25519"
    UNKNOWN = "Unknown"


class TrustStatus(Enum):
    """Certificate trust validation status."""
    TRUSTED = "trusted"                 # Valid chain to trusted root
    UNTRUSTED = "untrusted"             # Invalid chain or self-signed
    EXPIRED = "expired"                 # Certificate expired
    NOT_YET_VALID = "not_yet_valid"     # Not valid yet
    REVOKED = "revoked"                 # Certificate revoked
    UNKNOWN = "unknown"                 # Unable to determine


@dataclass
class PublicKeyInfo:
    """Public key details from X.509 certificate."""
    algorithm: KeyAlgorithm
    size_bits: int  # Key size (e.g., 2048, 4096, 256)
    fingerprint_sha256: str
    fingerprint_sha1: str  # Legacy, still shown for compatibility

    @property
    def display_algorithm(self) -> str:
        """Human-readable algorithm description."""
        return f"{self.algorithm.value} {self.size_bits}-bit"

    @property
    def is_weak(self) -> bool:
        """Check if key is considered weak by modern standards."""
        if self.algorithm == KeyAlgorithm.RSA and self.size_bits < 2048:
            return True
        if self.algorithm == KeyAlgorithm.ECDSA and self.size_bits < 256:
            return True
        if self.algorithm == KeyAlgorithm.DSA:
            return True  # DSA is considered legacy
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "algorithm": self.algorithm.value,
            "size_bits": self.size_bits,
            "display_algorithm": self.display_algorithm,
            "fingerprint_sha256": self.fingerprint_sha256,
            "fingerprint_sha1": self.fingerprint_sha1,
            "is_weak": self.is_weak
        }


@dataclass
class Certificate:
    """X.509 certificate representation.

    Represents a single certificate with validation helpers
    for expiry checking and trust assessment.
    """
    # Basic information
    subject: str  # Common Name (CN)
    issuer: str   # Issuer CN
    serial_number: str  # Hex-encoded serial number

    # Validity period
    not_before: datetime
    not_after: datetime

    # Public key
    public_key: PublicKeyInfo

    # Subject Alternative Names
    san: List[str] = field(default_factory=list)  # DNS names, IPs

    # Chain information
    parent_cert: Optional['Certificate'] = None  # Issuer certificate
    is_self_signed: bool = False
    is_ca: bool = False  # Is Certificate Authority

    # Trust status
    trust_status: TrustStatus = TrustStatus.UNKNOWN

    # Extensions
    key_usage: List[str] = field(default_factory=list)
    extended_key_usage: List[str] = field(default_factory=list)

    # Raw data (for export)
    pem_data: Optional[str] = None
    der_data: Optional[bytes] = None

    # Additional metadata
    version: int = 3
    signature_algorithm: str = "sha256WithRSAEncryption"

    @property
    def is_expired(self) -> bool:
        """Check if certificate is currently expired."""
        now = datetime.now(timezone.utc)
        return now > self.not_after

    @property
    def is_not_yet_valid(self) -> bool:
        """Check if certificate is not yet valid."""
        now = datetime.now(timezone.utc)
        return now < self.not_before

    def is_expiring_soon(self, days_threshold: int = 30) -> bool:
        """Check if certificate expires within threshold days."""
        if self.is_expired:
            return False
        now = datetime.now(timezone.utc)
        days_remaining = (self.not_after - now).days
        return 0 < days_remaining <= days_threshold

    @property
    def days_until_expiry(self) -> int:
        """Days until expiration (negative if expired)."""
        now = datetime.now(timezone.utc)
        return (self.not_after - now).days

    @property
    def expiry_warning(self) -> Optional[str]:
        """Human-readable expiry warning message."""
        if self.is_expired:
            return f"⚠️ EXPIRED {abs(self.days_until_expiry)} days ago"
        elif self.is_expiring_soon():
            return f"⚠️ Expires in {self.days_until_expiry} days"
        return None

    @property
    def display_name(self) -> str:
        """Best display name for the certificate."""
        # Prefer CN from subject
        if "CN=" in self.subject:
            cn = self.subject.split("CN=")[1].split(",")[0]
            return cn.strip()
        # Fallback to first SAN
        if self.san:
            return self.san[0]
        # Last resort: full subject
        return self.subject

    @property
    def is_valid(self) -> bool:
        """Check if certificate is currently valid (not expired, not revoked)."""
        if self.is_expired or self.is_not_yet_valid:
            return False
        if self.trust_status in [TrustStatus.EXPIRED, TrustStatus.REVOKED]:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "subject": self.subject,
            "issuer": self.issuer,
            "serial_number": self.serial_number,
            "not_before": self.not_before.isoformat(),
            "not_after": self.not_after.isoformat(),
            "display_name": self.display_name,
            "public_key": self.public_key.to_dict(),
            "san": self.san,
            "is_self_signed": self.is_self_signed,
            "is_ca": self.is_ca,
            "trust_status": self.trust_status.value,
            "is_expired": self.is_expired,
            "is_not_yet_valid": self.is_not_yet_valid,
            "is_expiring_soon": self.is_expiring_soon(),
            "days_until_expiry": self.days_until_expiry,
            "expiry_warning": self.expiry_warning,
            "is_valid": self.is_valid,
            "key_usage": self.key_usage,
            "extended_key_usage": self.extended_key_usage,
            "version": self.version,
            "signature_algorithm": self.signature_algorithm,
            "pem_data": self.pem_data
        }


@dataclass
class CertificateChain:
    """Complete X.509 certificate chain.

    Represents a full certificate chain from leaf (end-entity)
    certificate through intermediates to the root CA.
    """
    leaf: Certificate  # End-entity certificate
    intermediates: List[Certificate] = field(default_factory=list)
    root: Optional[Certificate] = None

    # Connection metadata (for remote fetches)
    hostname: Optional[str] = None
    port: int = 443
    fetch_time: Optional[datetime] = None

    @property
    def is_complete(self) -> bool:
        """Check if chain reaches a trusted root CA."""
        return self.root is not None and self.root.is_ca

    @property
    def chain_length(self) -> int:
        """Total number of certificates in chain."""
        return 1 + len(self.intermediates) + (1 if self.root else 0)

    @property
    def is_trusted(self) -> bool:
        """Check if entire chain is trusted."""
        # All certs must be valid
        for cert in self.get_all_certificates():
            if not cert.is_valid:
                return False

        # Chain must be complete
        if not self.is_complete:
            return False

        # Root must be trusted
        if self.root and self.root.trust_status != TrustStatus.TRUSTED:
            return False

        return True

    @property
    def has_expired_certs(self) -> bool:
        """Check if any certificate in chain is expired."""
        return any(cert.is_expired for cert in self.get_all_certificates())

    @property
    def has_expiring_soon_certs(self, days_threshold: int = 30) -> bool:
        """Check if any certificate expires within threshold."""
        return any(
            cert.is_expiring_soon(days_threshold)
            for cert in self.get_all_certificates()
        )

    def get_all_certificates(self) -> List[Certificate]:
        """Get flattened list of all certificates in order (leaf -> root)."""
        certs = [self.leaf] + self.intermediates
        if self.root:
            certs.append(self.root)
        return certs

    def get_expiry_warnings(self) -> List[str]:
        """Get all expiry warnings from the chain."""
        warnings = []
        for cert in self.get_all_certificates():
            if cert.expiry_warning:
                warnings.append(f"{cert.display_name}: {cert.expiry_warning}")
        return warnings

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "leaf": self.leaf.to_dict(),
            "intermediates": [cert.to_dict() for cert in self.intermediates],
            "root": self.root.to_dict() if self.root else None,
            "hostname": self.hostname,
            "port": self.port,
            "fetch_time": self.fetch_time.isoformat() if self.fetch_time else None,
            "is_complete": self.is_complete,
            "chain_length": self.chain_length,
            "is_trusted": self.is_trusted,
            "has_expired_certs": self.has_expired_certs,
            "has_expiring_soon_certs": self.has_expiring_soon_certs,
            "expiry_warnings": self.get_expiry_warnings()
        }
