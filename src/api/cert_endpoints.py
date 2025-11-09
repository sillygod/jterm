"""Certificate inspection REST API endpoints.

This module provides HTTP endpoints for certcat functionality including:
- Fetching SSL certificates from remote endpoints
- Parsing local certificate files (PEM/DER)
- Validating certificate chains
- Comparing certificates
- Exporting certificate data

T024: Implementation of certificate API endpoints.
"""

import ssl
import socket
from typing import Optional, List
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, Field, validator

from src.services.cert_service import get_cert_service
from src.models.certificate import Certificate, CertificateChain

# Initialize router
router = APIRouter(prefix="/api/certificates", tags=["Certificates"])

# Get cert service instance
cert_service = get_cert_service()


# Pydantic models for request/response validation
class FetchCertRequest(BaseModel):
    """Request model for fetching remote certificate."""
    url: str = Field(..., description="URL or hostname to fetch certificate from")
    port: int = Field(443, description="Port number (default: 443)", ge=1, le=65535)
    timeout: int = Field(10, description="Connection timeout in seconds", ge=1, le=60)

    @validator('url')
    def validate_url(cls, v):
        """Extract hostname from URL or validate hostname."""
        # Remove protocol if present
        if '://' in v:
            v = v.split('://')[1]
        # Remove path if present
        if '/' in v:
            v = v.split('/')[0]
        # Remove port if present in hostname
        if ':' in v:
            v = v.split(':')[0]
        return v


class ParseCertRequest(BaseModel):
    """Request model for parsing local certificate."""
    file_path: str = Field(..., description="Absolute filesystem path to certificate file")


class CompareCertsRequest(BaseModel):
    """Request model for comparing two certificates."""
    cert1_path: Optional[str] = Field(None, description="Path to first certificate file")
    cert1_url: Optional[str] = Field(None, description="URL to fetch first certificate")
    cert2_path: Optional[str] = Field(None, description="Path to second certificate file")
    cert2_url: Optional[str] = Field(None, description="URL to fetch second certificate")


class ExportCertRequest(BaseModel):
    """Request model for certificate export."""
    source: str = Field(..., description="Certificate source (url or file path)")
    format: str = Field("pem", description="Export format: pem, der, or text")


class FetchCertResponse(BaseModel):
    """Response model for certificate fetch."""
    chain: dict
    hostname: str
    port: int
    is_trusted: bool
    expiry_warnings: List[str]


@router.post("/fetch", response_model=FetchCertResponse)
async def fetch_certificate(request: FetchCertRequest):
    """Fetch SSL certificate chain from remote HTTPS endpoint.

    Args:
        request: FetchCertRequest with hostname, port, and timeout

    Returns:
        FetchCertResponse with certificate chain and validation status

    Raises:
        HTTPException: If connection fails or certificate fetch fails
    """
    try:
        chain = await cert_service.fetch_remote_cert(
            hostname=request.url,
            port=request.port,
            timeout=request.timeout
        )

        return FetchCertResponse(
            chain=chain.to_dict(),
            hostname=request.url,
            port=request.port,
            is_trusted=chain.is_trusted,
            expiry_warnings=chain.get_expiry_warnings()
        )

    except (ssl.SSLError, socket.error) as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to connect to {request.url}:{request.port}: {str(e)}"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch certificate: {str(e)}"
        )


@router.post("/parse")
async def parse_certificate(request: ParseCertRequest):
    """Parse certificate from local file.

    Args:
        request: ParseCertRequest with file path

    Returns:
        Certificate details as JSON

    Raises:
        HTTPException: If file not found or parsing fails
    """
    try:
        cert = await cert_service.parse_local_cert(request.file_path)
        return cert.to_dict()

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse certificate: {str(e)}"
        )


@router.post("/compare")
async def compare_certificates(request: CompareCertsRequest):
    """Compare two certificates and return differences.

    At least one pair must be provided:
    - cert1_path + cert2_path
    - cert1_url + cert2_url
    - cert1_path + cert2_url
    - cert1_url + cert2_path

    Args:
        request: CompareCertsRequest with certificate sources

    Returns:
        Comparison results with differences

    Raises:
        HTTPException: If certificates cannot be loaded or compared
    """
    try:
        # Load first certificate
        if request.cert1_path:
            cert1 = await cert_service.parse_local_cert(request.cert1_path)
        elif request.cert1_url:
            chain1 = await cert_service.fetch_remote_cert(request.cert1_url)
            cert1 = chain1.leaf
        else:
            raise ValueError("Must provide either cert1_path or cert1_url")

        # Load second certificate
        if request.cert2_path:
            cert2 = await cert_service.parse_local_cert(request.cert2_path)
        elif request.cert2_url:
            chain2 = await cert_service.fetch_remote_cert(request.cert2_url)
            cert2 = chain2.leaf
        else:
            raise ValueError("Must provide either cert2_path or cert2_url")

        # Compare certificates
        comparison = cert_service.compare_certificates(cert1, cert2)

        return {
            "cert1": {
                "subject": cert1.subject,
                "serial": cert1.serial_number,
                "not_after": cert1.not_after.isoformat()
            },
            "cert2": {
                "subject": cert2.subject,
                "serial": cert2.serial_number,
                "not_after": cert2.not_after.isoformat()
            },
            "comparison": comparison
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compare certificates: {str(e)}"
        )


@router.post("/export")
async def export_certificate(request: ExportCertRequest):
    """Export certificate in specified format.

    Args:
        request: ExportCertRequest with source and format

    Returns:
        Certificate data in requested format

    Raises:
        HTTPException: If certificate cannot be loaded or exported
    """
    try:
        # Load certificate
        if request.source.startswith('http://') or request.source.startswith('https://'):
            # Remote certificate
            url = request.source.replace('https://', '').replace('http://', '')
            chain = await cert_service.fetch_remote_cert(url)
            cert = chain.leaf
        else:
            # Local file
            cert = await cert_service.parse_local_cert(request.source)

        # Export in requested format
        if request.format.lower() == "pem":
            if not cert.pem_data:
                raise ValueError("PEM data not available")
            return Response(
                content=cert.pem_data,
                media_type="application/x-pem-file",
                headers={"Content-Disposition": f"attachment; filename=certificate.pem"}
            )

        elif request.format.lower() == "der":
            if not cert.der_data:
                raise ValueError("DER data not available")
            return Response(
                content=cert.der_data,
                media_type="application/x-x509-ca-cert",
                headers={"Content-Disposition": f"attachment; filename=certificate.der"}
            )

        elif request.format.lower() == "text":
            # Format as human-readable text
            text_output = f"""Certificate Details
{'=' * 50}

Subject: {cert.subject}
Issuer: {cert.issuer}
Serial Number: {cert.serial_number}

Validity:
  Not Before: {cert.not_before.isoformat()}
  Not After: {cert.not_after.isoformat()}
  Days Until Expiry: {cert.days_until_expiry}
  Status: {"EXPIRED" if cert.is_expired else "VALID"}

Public Key:
  Algorithm: {cert.public_key.display_algorithm}
  SHA-256 Fingerprint: {cert.public_key.fingerprint_sha256}
  SHA-1 Fingerprint: {cert.public_key.fingerprint_sha1}

Subject Alternative Names:
  {chr(10).join(f"- {san}" for san in cert.san) if cert.san else "None"}

Certificate Authority: {"Yes" if cert.is_ca else "No"}
Self-Signed: {"Yes" if cert.is_self_signed else "No"}
Trust Status: {cert.trust_status.value.upper()}

Key Usage:
  {chr(10).join(f"- {ku}" for ku in cert.key_usage) if cert.key_usage else "None"}

Extended Key Usage:
  {chr(10).join(f"- {eku}" for eku in cert.extended_key_usage) if cert.extended_key_usage else "None"}
"""
            return Response(
                content=text_output,
                media_type="text/plain",
                headers={"Content-Disposition": f"attachment; filename=certificate.txt"}
            )

        else:
            raise ValueError(f"Unsupported export format: {request.format}")

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export certificate: {str(e)}"
        )
