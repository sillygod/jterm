"""Certificate service for fetching and validating SSL/TLS certificates.

This service provides functionality for:
- Fetching certificates from remote HTTPS endpoints
- Parsing local certificate files (PEM/DER format)
- Validating certificate chains and trust status
- Comparing certificates for changes

T023: CertService implementation.
"""

import ssl
import socket
import certifi
import httpx
from datetime import datetime, timezone
from typing import Optional, List, Tuple, Dict, Any
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, dsa, ec, ed25519
from cryptography.x509.oid import ExtensionOID, NameOID, AuthorityInformationAccessOID

from src.models.certificate import (
    Certificate,
    CertificateChain,
    PublicKeyInfo,
    KeyAlgorithm,
    TrustStatus
)


class CertService:
    """Service for certificate operations."""

    def __init__(self):
        """Initialize certificate service with system trust store."""
        self.trust_store_path = certifi.where()

    async def fetch_remote_cert(
        self,
        hostname: str,
        port: int = 443,
        timeout: int = 10
    ) -> CertificateChain:
        """Fetch certificate chain from remote HTTPS endpoint.

        Args:
            hostname: Remote hostname to connect to
            port: Port number (default: 443)
            timeout: Connection timeout in seconds

        Returns:
            CertificateChain with all certificates from the remote endpoint

        Raises:
            ssl.SSLError: If SSL/TLS connection fails
            socket.error: If network connection fails
            ValueError: If hostname is invalid
        """
        context = ssl.create_default_context(cafile=self.trust_store_path)
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED

        # Connect and fetch certificates
        with socket.create_connection((hostname, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as secure_sock:
                # Get peer certificate in DER format (binary)
                der_cert_bytes = secure_sock.getpeercert(binary_form=True)

                if not der_cert_bytes:
                    raise ValueError("No certificate received from server")

                # Parse the leaf certificate
                cert = x509.load_der_x509_certificate(der_cert_bytes, default_backend())
                leaf = self._parse_x509_certificate(cert)

                # Fetch intermediate certificates from AIA extension
                intermediates = await self._fetch_intermediate_certs(cert)

                # Try to identify the root certificate
                root = None
                if intermediates:
                    # The last intermediate might be the root or issued by root
                    last_intermediate_cert = intermediates[-1]
                    if last_intermediate_cert.is_self_signed:
                        # Last intermediate is actually the root
                        root = intermediates.pop()

                # Build chain structure
                chain = CertificateChain(
                    leaf=leaf,
                    intermediates=intermediates,
                    root=root,
                    hostname=hostname,
                    port=port,
                    fetch_time=datetime.now(timezone.utc)
                )

                # Update trust status
                self._validate_chain_trust(chain)

                return chain

    async def parse_local_cert(self, file_path: str) -> Certificate:
        """Parse certificate from local file.

        Supports PEM and DER formats. For PEM files with multiple certificates,
        only the first one is returned.

        Args:
            file_path: Path to certificate file

        Returns:
            Parsed Certificate object

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file cannot be parsed as certificate
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Certificate file not found: {file_path}")

        cert_data = path.read_bytes()

        # Try PEM first
        try:
            cert = x509.load_pem_x509_certificate(cert_data, default_backend())
            return self._parse_x509_certificate(cert)
        except ValueError:
            pass

        # Try DER
        try:
            cert = x509.load_der_x509_certificate(cert_data, default_backend())
            return self._parse_x509_certificate(cert)
        except ValueError as e:
            raise ValueError(f"Invalid certificate format: {e}")

    def validate_chain(self, chain: CertificateChain) -> bool:
        """Validate certificate chain integrity and trust.

        Args:
            chain: Certificate chain to validate

        Returns:
            True if chain is valid and trusted, False otherwise
        """
        self._validate_chain_trust(chain)
        return chain.is_trusted

    def compare_certificates(
        self,
        cert1: Certificate,
        cert2: Certificate
    ) -> Dict[str, any]:
        """Compare two certificates and return differences.

        Args:
            cert1: First certificate
            cert2: Second certificate

        Returns:
            Dictionary with comparison results
        """
        differences = []

        # Compare subjects
        if cert1.subject != cert2.subject:
            differences.append({
                "field": "subject",
                "cert1": cert1.subject,
                "cert2": cert2.subject
            })

        # Compare issuers
        if cert1.issuer != cert2.issuer:
            differences.append({
                "field": "issuer",
                "cert1": cert1.issuer,
                "cert2": cert2.issuer
            })

        # Compare validity dates
        if cert1.not_before != cert2.not_before:
            differences.append({
                "field": "not_before",
                "cert1": cert1.not_before.isoformat(),
                "cert2": cert2.not_before.isoformat()
            })

        if cert1.not_after != cert2.not_after:
            differences.append({
                "field": "not_after",
                "cert1": cert1.not_after.isoformat(),
                "cert2": cert2.not_after.isoformat()
            })

        # Compare public keys
        if cert1.public_key.fingerprint_sha256 != cert2.public_key.fingerprint_sha256:
            differences.append({
                "field": "public_key",
                "cert1": cert1.public_key.display_algorithm,
                "cert2": cert2.public_key.display_algorithm
            })

        # Compare SANs
        san1_set = set(cert1.san)
        san2_set = set(cert2.san)
        if san1_set != san2_set:
            differences.append({
                "field": "san",
                "added": list(san2_set - san1_set),
                "removed": list(san1_set - san2_set)
            })

        return {
            "identical": len(differences) == 0,
            "difference_count": len(differences),
            "differences": differences,
            "serial_match": cert1.serial_number == cert2.serial_number
        }

    def _parse_x509_certificate(self, cert: x509.Certificate) -> Certificate:
        """Parse cryptography x509.Certificate to our Certificate model.

        Args:
            cert: cryptography Certificate object

        Returns:
            Our Certificate dataclass
        """
        # Extract subject CN
        try:
            subject_cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
        except (IndexError, AttributeError):
            subject_cn = str(cert.subject)

        # Extract issuer CN
        try:
            issuer_cn = cert.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
        except (IndexError, AttributeError):
            issuer_cn = str(cert.issuer)

        # Parse public key
        public_key = cert.public_key()
        key_info = self._parse_public_key(public_key, cert)

        # Extract SANs
        san_list = []
        try:
            san_ext = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
            san_list = [str(name) for name in san_ext.value]
        except x509.ExtensionNotFound:
            pass

        # Check if self-signed
        is_self_signed = cert.issuer == cert.subject

        # Check if CA
        is_ca = False
        try:
            basic_constraints = cert.extensions.get_extension_for_oid(
                ExtensionOID.BASIC_CONSTRAINTS
            )
            is_ca = basic_constraints.value.ca
        except x509.ExtensionNotFound:
            pass

        # Extract key usage
        key_usage_list = []
        try:
            ku_ext = cert.extensions.get_extension_for_oid(ExtensionOID.KEY_USAGE)
            ku = ku_ext.value
            if ku.digital_signature:
                key_usage_list.append("Digital Signature")
            if ku.key_encipherment:
                key_usage_list.append("Key Encipherment")
            if ku.key_cert_sign:
                key_usage_list.append("Certificate Sign")
        except x509.ExtensionNotFound:
            pass

        # Extract extended key usage
        extended_key_usage_list = []
        try:
            eku_ext = cert.extensions.get_extension_for_oid(ExtensionOID.EXTENDED_KEY_USAGE)
            extended_key_usage_list = [str(oid) for oid in eku_ext.value]
        except x509.ExtensionNotFound:
            pass

        # Get PEM data
        pem_data = cert.public_bytes(serialization.Encoding.PEM).decode('utf-8')

        # Get DER data
        der_data = cert.public_bytes(serialization.Encoding.DER)

        # Determine initial trust status based on validity
        trust_status = TrustStatus.UNKNOWN
        now = datetime.now(timezone.utc)
        if now > cert.not_valid_after_utc:
            trust_status = TrustStatus.EXPIRED
        elif now < cert.not_valid_before_utc:
            trust_status = TrustStatus.NOT_YET_VALID

        return Certificate(
            subject=str(cert.subject),
            issuer=str(cert.issuer),
            serial_number=hex(cert.serial_number)[2:].upper(),
            not_before=cert.not_valid_before_utc,
            not_after=cert.not_valid_after_utc,
            public_key=key_info,
            san=san_list,
            is_self_signed=is_self_signed,
            is_ca=is_ca,
            trust_status=trust_status,
            key_usage=key_usage_list,
            extended_key_usage=extended_key_usage_list,
            pem_data=pem_data,
            der_data=der_data,
            version=cert.version.value,
            signature_algorithm=cert.signature_algorithm_oid._name
        )

    def _parse_public_key(
        self,
        public_key,
        cert: x509.Certificate
    ) -> PublicKeyInfo:
        """Parse public key information from certificate.

        Args:
            public_key: Public key object from certificate
            cert: Full certificate for fingerprinting

        Returns:
            PublicKeyInfo with algorithm and fingerprints
        """
        # Determine algorithm and key size
        if isinstance(public_key, rsa.RSAPublicKey):
            algorithm = KeyAlgorithm.RSA
            size_bits = public_key.key_size
        elif isinstance(public_key, ec.EllipticCurvePublicKey):
            algorithm = KeyAlgorithm.ECDSA
            size_bits = public_key.curve.key_size
        elif isinstance(public_key, dsa.DSAPublicKey):
            algorithm = KeyAlgorithm.DSA
            size_bits = public_key.key_size
        elif isinstance(public_key, ed25519.Ed25519PublicKey):
            algorithm = KeyAlgorithm.ED25519
            size_bits = 256  # Ed25519 is always 256 bits
        else:
            algorithm = KeyAlgorithm.UNKNOWN
            size_bits = 0

        # Calculate fingerprints
        sha256_fingerprint = cert.fingerprint(hashes.SHA256()).hex().upper()
        sha1_fingerprint = cert.fingerprint(hashes.SHA1()).hex().upper()

        # Format fingerprints with colons
        sha256_formatted = ":".join(sha256_fingerprint[i:i+2] for i in range(0, len(sha256_fingerprint), 2))
        sha1_formatted = ":".join(sha1_fingerprint[i:i+2] for i in range(0, len(sha1_fingerprint), 2))

        return PublicKeyInfo(
            algorithm=algorithm,
            size_bits=size_bits,
            fingerprint_sha256=sha256_formatted,
            fingerprint_sha1=sha1_formatted
        )

    async def _fetch_intermediate_certs(self, leaf_cert: x509.Certificate) -> List[Certificate]:
        """Fetch intermediate certificates from AIA extension.

        Args:
            leaf_cert: The leaf certificate to extract AIA from

        Returns:
            List of intermediate Certificate objects
        """
        intermediates = []
        current_cert = leaf_cert
        max_depth = 10  # Prevent infinite loops
        depth = 0

        while depth < max_depth:
            try:
                # Get Authority Information Access extension
                aia_ext = current_cert.extensions.get_extension_for_oid(
                    ExtensionOID.AUTHORITY_INFORMATION_ACCESS
                )

                # Find CA Issuers URL
                ca_issuer_url = None
                for access_description in aia_ext.value:
                    if access_description.access_method == AuthorityInformationAccessOID.CA_ISSUERS:
                        ca_issuer_url = access_description.access_location.value
                        break

                if not ca_issuer_url:
                    # No more issuers to fetch
                    break

                # Fetch the intermediate certificate
                async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                    response = await client.get(ca_issuer_url)
                    response.raise_for_status()

                    # Parse the certificate (usually in DER format)
                    try:
                        intermediate_cert = x509.load_der_x509_certificate(
                            response.content,
                            default_backend()
                        )
                    except ValueError:
                        # Try PEM format
                        intermediate_cert = x509.load_pem_x509_certificate(
                            response.content,
                            default_backend()
                        )

                    # Parse and add to chain
                    parsed_intermediate = self._parse_x509_certificate(intermediate_cert)
                    intermediates.append(parsed_intermediate)

                    # Check if this is self-signed (root)
                    if intermediate_cert.issuer == intermediate_cert.subject:
                        # Found the root, stop here
                        break

                    # Continue with the next level
                    current_cert = intermediate_cert
                    depth += 1

            except (x509.ExtensionNotFound, httpx.RequestError, ValueError) as e:
                # No AIA extension or fetch failed, stop here
                break

        return intermediates

    def _validate_chain_trust(self, chain: CertificateChain) -> None:
        """Validate trust status of certificate chain.

        Updates trust_status on all certificates in the chain.

        Args:
            chain: Certificate chain to validate
        """
        # Simple validation based on expiry and self-signed status
        # More sophisticated validation would use OpenSSL verify

        # Check leaf certificate
        if chain.leaf.is_expired:
            chain.leaf.trust_status = TrustStatus.EXPIRED
        elif chain.leaf.is_not_yet_valid:
            chain.leaf.trust_status = TrustStatus.NOT_YET_VALID
        elif chain.leaf.is_self_signed and not chain.is_complete:
            chain.leaf.trust_status = TrustStatus.UNTRUSTED
        elif chain.is_complete:
            chain.leaf.trust_status = TrustStatus.TRUSTED
        else:
            chain.leaf.trust_status = TrustStatus.UNTRUSTED

        # Update intermediates
        for intermediate in chain.intermediates:
            if intermediate.is_expired:
                intermediate.trust_status = TrustStatus.EXPIRED
            elif intermediate.is_not_yet_valid:
                intermediate.trust_status = TrustStatus.NOT_YET_VALID
            else:
                intermediate.trust_status = TrustStatus.TRUSTED

        # Update root
        if chain.root:
            if chain.root.is_expired:
                chain.root.trust_status = TrustStatus.EXPIRED
            elif chain.root.is_not_yet_valid:
                chain.root.trust_status = TrustStatus.NOT_YET_VALID
            elif chain.root.is_ca:
                chain.root.trust_status = TrustStatus.TRUSTED
            else:
                chain.root.trust_status = TrustStatus.UNTRUSTED


# Singleton instance
_cert_service_instance: Optional[CertService] = None


def get_cert_service() -> CertService:
    """Get singleton CertService instance."""
    global _cert_service_instance
    if _cert_service_instance is None:
        _cert_service_instance = CertService()
    return _cert_service_instance
