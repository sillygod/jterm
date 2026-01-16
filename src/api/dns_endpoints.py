"""DNS lookup REST API endpoints.

This module provides HTTP endpoints for dnscat functionality including:
- DNS record resolution (A, AAAA, MX, NS, TXT, CNAME, SOA, PTR)
- WHOIS information queries
- Full domain lookup (DNS + WHOIS)
"""

from typing import Optional, List, Dict, Any
from dataclasses import asdict
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from src.services.dns_service import dns_service

# Initialize router
router = APIRouter(prefix="/api/dns", tags=["DNS"])


class DNSQueryRequest(BaseModel):
    """Request model for DNS query."""
    domain: str = Field(..., description="Domain name or IP address to query")
    record_types: Optional[List[str]] = Field(
        None,
        description="List of record types to query (default: A, AAAA, MX, NS, TXT, CNAME, SOA)"
    )

    @field_validator('domain')
    @classmethod
    def validate_domain(cls, v: str) -> str:
        """Clean up domain input."""
        v = v.strip().lower()
        # Remove protocol if present
        if '://' in v:
            v = v.split('://')[1]
        # Remove path if present
        if '/' in v:
            v = v.split('/')[0]
        # Remove port if present
        if ':' in v:
            v = v.split(':')[0]
        return v


class WhoisQueryRequest(BaseModel):
    """Request model for WHOIS query."""
    domain: str = Field(..., description="Domain name to query")

    @field_validator('domain')
    @classmethod
    def validate_domain(cls, v: str) -> str:
        """Clean up domain input."""
        v = v.strip().lower()
        if '://' in v:
            v = v.split('://')[1]
        if '/' in v:
            v = v.split('/')[0]
        if ':' in v:
            v = v.split(':')[0]
        # Remove www. prefix
        if v.startswith('www.'):
            v = v[4:]
        return v


class FullLookupRequest(BaseModel):
    """Request model for full DNS + WHOIS lookup."""
    domain: str = Field(..., description="Domain name to query")

    @field_validator('domain')
    @classmethod
    def validate_domain(cls, v: str) -> str:
        """Clean up domain input."""
        v = v.strip().lower()
        if '://' in v:
            v = v.split('://')[1]
        if '/' in v:
            v = v.split('/')[0]
        if ':' in v:
            v = v.split(':')[0]
        return v


class DNSRecordResponse(BaseModel):
    """Response model for a DNS record."""
    record_type: str
    value: str
    ttl: int
    priority: Optional[int] = None


class DNSQueryResponse(BaseModel):
    """Response model for DNS query."""
    domain: str
    records: Dict[str, List[DNSRecordResponse]]
    query_time: str
    nameservers_used: List[str]
    error: Optional[str] = None


class WhoisQueryResponse(BaseModel):
    """Response model for WHOIS query."""
    domain: str
    registrar: Optional[str] = None
    creation_date: Optional[str] = None
    expiration_date: Optional[str] = None
    updated_date: Optional[str] = None
    name_servers: Optional[List[str]] = None
    status: Optional[List[str]] = None
    registrant: Optional[str] = None
    registrant_country: Optional[str] = None
    dnssec: Optional[str] = None
    emails: Optional[List[str]] = None
    raw_text: Optional[str] = None
    error: Optional[str] = None


class FullLookupResponse(BaseModel):
    """Response model for full lookup."""
    domain: str
    dns: DNSQueryResponse
    whois: WhoisQueryResponse


@router.post("/query", response_model=DNSQueryResponse)
async def query_dns(request: DNSQueryRequest) -> DNSQueryResponse:
    """Query DNS records for a domain.

    Args:
        request: DNS query request with domain and optional record types

    Returns:
        DNS query response with resolved records
    """
    try:
        result = await dns_service.resolve_dns(
            request.domain,
            request.record_types
        )
        return DNSQueryResponse(
            domain=result.domain,
            records={
                rtype: [DNSRecordResponse(**asdict(rec)) for rec in records]
                for rtype, records in result.records.items()
            },
            query_time=result.query_time,
            nameservers_used=result.nameservers_used,
            error=result.error
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DNS query failed: {str(e)}"
        )


@router.post("/whois", response_model=WhoisQueryResponse)
async def query_whois(request: WhoisQueryRequest) -> WhoisQueryResponse:
    """Query WHOIS information for a domain.

    Args:
        request: WHOIS query request with domain

    Returns:
        WHOIS query response with domain registration info
    """
    try:
        result = await dns_service.query_whois(request.domain)
        return WhoisQueryResponse(**asdict(result))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"WHOIS query failed: {str(e)}"
        )


@router.post("/lookup", response_model=FullLookupResponse)
async def full_lookup(request: FullLookupRequest) -> FullLookupResponse:
    """Perform full DNS and WHOIS lookup for a domain.

    Args:
        request: Full lookup request with domain

    Returns:
        Full lookup response with both DNS records and WHOIS info
    """
    try:
        result = await dns_service.full_lookup(request.domain)

        dns_data = result['dns']
        whois_data = result['whois']

        return FullLookupResponse(
            domain=result['domain'],
            dns=DNSQueryResponse(
                domain=dns_data['domain'],
                records={
                    rtype: [DNSRecordResponse(**rec) for rec in records]
                    for rtype, records in dns_data['records'].items()
                },
                query_time=dns_data['query_time'],
                nameservers_used=dns_data['nameservers_used'],
                error=dns_data.get('error')
            ),
            whois=WhoisQueryResponse(**whois_data)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Full lookup failed: {str(e)}"
        )
