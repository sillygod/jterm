"""DNS lookup service for querying DNS records and WHOIS information.

This service provides functionality for:
- Resolving DNS records (A, AAAA, MX, NS, TXT, CNAME, SOA, PTR)
- Querying WHOIS information for domains
- Reverse DNS lookups for IP addresses
"""

import asyncio
import logging
import re
import socket
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

import dns.resolver
import dns.reversename
import dns.exception
import whois

logger = logging.getLogger(__name__)

# DNS record types to query
DNS_RECORD_TYPES = ['A', 'AAAA', 'MX', 'NS', 'TXT', 'CNAME', 'SOA']


@dataclass
class DNSRecord:
    """Represents a single DNS record."""
    record_type: str
    value: str
    ttl: int
    priority: Optional[int] = None  # For MX records


@dataclass
class DNSResult:
    """DNS query result for a domain."""
    domain: str
    records: Dict[str, List[DNSRecord]]
    query_time: str
    nameservers_used: List[str]
    error: Optional[str] = None


@dataclass
class WhoisResult:
    """WHOIS query result for a domain."""
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


class DNSService:
    """Service for DNS and WHOIS lookups."""

    def __init__(self):
        """Initialize DNS service."""
        self.resolver = dns.resolver.Resolver()
        self.resolver.timeout = 5
        self.resolver.lifetime = 10

    def _is_valid_domain(self, domain: str) -> bool:
        """Validate domain name format."""
        pattern = r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
        return bool(re.match(pattern, domain))

    def _is_ip_address(self, value: str) -> bool:
        """Check if value is an IP address."""
        try:
            socket.inet_pton(socket.AF_INET, value)
            return True
        except socket.error:
            try:
                socket.inet_pton(socket.AF_INET6, value)
                return True
            except socket.error:
                return False

    def _format_datetime(self, dt: Any) -> Optional[str]:
        """Format datetime to ISO string."""
        if dt is None:
            return None
        if isinstance(dt, list):
            dt = dt[0] if dt else None
        if isinstance(dt, datetime):
            return dt.isoformat()
        return str(dt) if dt else None

    async def resolve_dns(
        self,
        domain: str,
        record_types: Optional[List[str]] = None
    ) -> DNSResult:
        """Resolve DNS records for a domain.

        Args:
            domain: Domain name to query
            record_types: List of record types to query (default: all common types)

        Returns:
            DNSResult with all resolved records
        """
        if record_types is None:
            record_types = DNS_RECORD_TYPES

        domain = domain.strip().lower()

        # Handle IP address input (do reverse DNS)
        if self._is_ip_address(domain):
            return await self._reverse_dns_lookup(domain)

        if not self._is_valid_domain(domain):
            return DNSResult(
                domain=domain,
                records={},
                query_time=datetime.now().isoformat(),
                nameservers_used=list(self.resolver.nameservers),
                error=f"Invalid domain format: {domain}"
            )

        records: Dict[str, List[DNSRecord]] = {}

        # Run queries in parallel using asyncio
        async def query_record_type(rtype: str) -> tuple:
            try:
                loop = asyncio.get_event_loop()
                answers = await loop.run_in_executor(
                    None,
                    lambda: self.resolver.resolve(domain, rtype)
                )
                result = []
                for rdata in answers:
                    record = self._parse_record(rtype, rdata, answers.ttl)
                    if record:
                        result.append(record)
                return (rtype, result)
            except dns.resolver.NXDOMAIN:
                logger.debug(f"NXDOMAIN for {domain} {rtype}")
                return (rtype, [])
            except dns.resolver.NoAnswer:
                logger.debug(f"No answer for {domain} {rtype}")
                return (rtype, [])
            except dns.resolver.NoNameservers:
                logger.debug(f"No nameservers for {domain} {rtype}")
                return (rtype, [])
            except dns.exception.Timeout:
                logger.warning(f"Timeout querying {domain} {rtype}")
                return (rtype, [])
            except Exception as e:
                logger.error(f"Error querying {domain} {rtype}: {e}")
                return (rtype, [])

        tasks = [query_record_type(rtype) for rtype in record_types]
        results = await asyncio.gather(*tasks)

        for rtype, record_list in results:
            if record_list:
                records[rtype] = record_list

        return DNSResult(
            domain=domain,
            records=records,
            query_time=datetime.now().isoformat(),
            nameservers_used=list(self.resolver.nameservers)
        )

    def _parse_record(
        self,
        record_type: str,
        rdata: Any,
        ttl: int
    ) -> Optional[DNSRecord]:
        """Parse DNS record data into DNSRecord object."""
        try:
            if record_type == 'A':
                return DNSRecord(
                    record_type='A',
                    value=str(rdata),
                    ttl=ttl
                )
            elif record_type == 'AAAA':
                return DNSRecord(
                    record_type='AAAA',
                    value=str(rdata),
                    ttl=ttl
                )
            elif record_type == 'MX':
                return DNSRecord(
                    record_type='MX',
                    value=str(rdata.exchange).rstrip('.'),
                    ttl=ttl,
                    priority=rdata.preference
                )
            elif record_type == 'NS':
                return DNSRecord(
                    record_type='NS',
                    value=str(rdata).rstrip('.'),
                    ttl=ttl
                )
            elif record_type == 'TXT':
                # Join multiple strings in TXT record
                txt_data = rdata.strings
                value = b''.join(txt_data).decode('utf-8', errors='replace')
                return DNSRecord(
                    record_type='TXT',
                    value=value,
                    ttl=ttl
                )
            elif record_type == 'CNAME':
                return DNSRecord(
                    record_type='CNAME',
                    value=str(rdata.target).rstrip('.'),
                    ttl=ttl
                )
            elif record_type == 'SOA':
                value = f"Primary NS: {str(rdata.mname).rstrip('.')}, " \
                        f"Email: {str(rdata.rname).rstrip('.')}, " \
                        f"Serial: {rdata.serial}"
                return DNSRecord(
                    record_type='SOA',
                    value=value,
                    ttl=ttl
                )
            elif record_type == 'PTR':
                return DNSRecord(
                    record_type='PTR',
                    value=str(rdata).rstrip('.'),
                    ttl=ttl
                )
            else:
                return DNSRecord(
                    record_type=record_type,
                    value=str(rdata),
                    ttl=ttl
                )
        except Exception as e:
            logger.error(f"Error parsing {record_type} record: {e}")
            return None

    async def _reverse_dns_lookup(self, ip_address: str) -> DNSResult:
        """Perform reverse DNS lookup for an IP address."""
        try:
            rev_name = dns.reversename.from_address(ip_address)
            loop = asyncio.get_event_loop()
            answers = await loop.run_in_executor(
                None,
                lambda: self.resolver.resolve(rev_name, 'PTR')
            )

            records = {'PTR': []}
            for rdata in answers:
                records['PTR'].append(DNSRecord(
                    record_type='PTR',
                    value=str(rdata).rstrip('.'),
                    ttl=answers.ttl
                ))

            return DNSResult(
                domain=ip_address,
                records=records,
                query_time=datetime.now().isoformat(),
                nameservers_used=list(self.resolver.nameservers)
            )
        except Exception as e:
            logger.error(f"Reverse DNS lookup failed for {ip_address}: {e}")
            return DNSResult(
                domain=ip_address,
                records={},
                query_time=datetime.now().isoformat(),
                nameservers_used=list(self.resolver.nameservers),
                error=f"Reverse DNS lookup failed: {str(e)}"
            )

    async def query_whois(self, domain: str) -> WhoisResult:
        """Query WHOIS information for a domain.

        Args:
            domain: Domain name to query

        Returns:
            WhoisResult with WHOIS information
        """
        domain = domain.strip().lower()

        # Remove www. prefix if present
        if domain.startswith('www.'):
            domain = domain[4:]

        try:
            loop = asyncio.get_event_loop()
            w = await loop.run_in_executor(None, lambda: whois.whois(domain))

            # Handle name_servers which could be string or list
            name_servers = w.name_servers
            if isinstance(name_servers, str):
                name_servers = [name_servers]
            elif name_servers:
                name_servers = [ns.lower() for ns in name_servers if ns]

            # Handle status which could be string or list
            status = w.status
            if isinstance(status, str):
                status = [status]

            # Handle emails
            emails = w.emails
            if isinstance(emails, str):
                emails = [emails]

            return WhoisResult(
                domain=domain,
                registrar=w.registrar,
                creation_date=self._format_datetime(w.creation_date),
                expiration_date=self._format_datetime(w.expiration_date),
                updated_date=self._format_datetime(w.updated_date),
                name_servers=name_servers,
                status=status,
                registrant=getattr(w, 'registrant', None) or getattr(w, 'org', None),
                registrant_country=getattr(w, 'country', None),
                dnssec=getattr(w, 'dnssec', None),
                emails=emails,
                raw_text=w.text if hasattr(w, 'text') else None
            )
        except Exception as e:
            logger.error(f"WHOIS query failed for {domain}: {e}")
            return WhoisResult(
                domain=domain,
                error=f"WHOIS query failed: {str(e)}"
            )

    async def full_lookup(self, domain: str) -> Dict[str, Any]:
        """Perform full DNS and WHOIS lookup.

        Args:
            domain: Domain name to query

        Returns:
            Dictionary with both DNS and WHOIS results
        """
        # Run DNS and WHOIS queries in parallel
        dns_result, whois_result = await asyncio.gather(
            self.resolve_dns(domain),
            self.query_whois(domain)
        )

        return {
            'domain': domain,
            'dns': asdict(dns_result),
            'whois': asdict(whois_result)
        }


# Singleton instance
dns_service = DNSService()
