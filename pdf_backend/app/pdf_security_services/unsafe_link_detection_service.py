import logging
import fitz
import urllib.parse
import re
import ipaddress
import uuid
import datetime
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class UnsafeLinkDetectionService:
    def __init__(self):
        self.SAFE_SCHEMES = ['http', 'https', 'ftp', 'mailto']
        self.DANGEROUS_SCHEMES = ['javascript', 'data', 'file', 'vbscript', 'ms-msdt', 'ws', 'wss']
        self.SUSPICIOUS_KEYWORDS = [
            'login', 'signin', 'verify', 'account', 'update', 'secure', 
            'banking', 'billing', 'confirm', 'password', 'auth', 'payment'
        ]

    def _analyze_url(self, url: str) -> Dict[str, Any]:
        findings = []
        score = 0
        risk_level = "INFO"
        
        try:
            parsed = urllib.parse.urlparse(url)
            scheme = parsed.scheme.lower() if parsed.scheme else ""
            hostname = parsed.hostname.lower() if parsed.hostname else ""
            path = parsed.path.lower()
            query = parsed.query
        except Exception as e:
            return {
                "risk_score": 100,
                "risk_level": "CRITICAL",
                "findings": [{
                    "rule_id": "MALFORMED_URL",
                    "category": "URL_VALIDATION",
                    "severity": "CRITICAL",
                    "description": "URL could not be parsed.",
                    "evidence": str(e),
                    "score": 100
                }]
            }

        if not scheme:
            findings.append({"rule_id": "MISSING_SCHEME", "category": "URL_VALIDATION", "severity": "LOW", "description": "URL lacks a valid protocol scheme.", "evidence": url, "score": 10})
            score += 10
        elif scheme in self.DANGEROUS_SCHEMES:
            findings.append({"rule_id": "DANGEROUS_SCHEME", "category": "DANGEROUS_SCHEME", "severity": "CRITICAL", "description": f"Executable or dangerous scheme '{scheme}' detected.", "evidence": scheme, "score": 100})
            score += 100
        elif scheme not in self.SAFE_SCHEMES:
            findings.append({"rule_id": "UNKNOWN_SCHEME", "category": "URL_VALIDATION", "severity": "MEDIUM", "description": f"Uncommon protocol scheme '{scheme}'.", "evidence": scheme, "score": 30})
            score += 30
        elif scheme == 'http':
            findings.append({"rule_id": "INSECURE_TRANSPORT", "category": "TRANSPORT", "severity": "LOW", "description": "Insecure HTTP scheme used instead of HTTPS.", "evidence": "http://", "score": 15})
            score += 15

        if hostname:
            if hostname.startswith("xn--") or ".xn--" in hostname:
                findings.append({"rule_id": "PUNYCODE_DOMAIN", "category": "PUNYCODE", "severity": "HIGH", "description": "Punycode (IDN) detected. Often used for homograph phishing.", "evidence": hostname, "score": 60})
                score += 60
            try:
                ip = ipaddress.ip_address(hostname.strip("[]"))
                if ip.is_private or ip.is_loopback or ip.is_reserved:
                    findings.append({"rule_id": "PRIVATE_IP_HOST", "category": "IP_ADDRESS", "severity": "HIGH", "description": "Private, loopback, or reserved IP address used as hostname.", "evidence": str(ip), "score": 75})
                    score += 75
                else:
                    findings.append({"rule_id": "PUBLIC_IP_HOST", "category": "IP_ADDRESS", "severity": "MEDIUM", "description": "Public IP address used instead of domain name.", "evidence": str(ip), "score": 40})
                    score += 40
            except ValueError:
                pass
            parts = hostname.split('.')
            if len(parts) > 4:
                findings.append({"rule_id": "EXCESSIVE_SUBDOMAINS", "category": "DOMAIN_ANALYSIS", "severity": "MEDIUM", "description": "Host contains an unusually high number of subdomains.", "evidence": hostname, "score": 30})
                score += 30
            if len(hostname) > 60:
                findings.append({"rule_id": "LONG_HOSTNAME", "category": "DOMAIN_ANALYSIS", "severity": "MEDIUM", "description": "Hostname is suspiciously long.", "evidence": f"Length: {len(hostname)}", "score": 25})
                score += 25
        elif scheme in ['http', 'https']:
            findings.append({"rule_id": "MISSING_HOSTNAME", "category": "URL_VALIDATION", "severity": "HIGH", "description": "Web scheme provided but hostname is missing.", "evidence": url, "score": 50})
            score += 50

        if parsed.username or parsed.password:
            findings.append({"rule_id": "CREDENTIALS_IN_URL", "category": "CREDENTIAL_ABUSE", "severity": "HIGH", "description": "Username or password embedded directly in URL.", "evidence": f"Username: {parsed.username}", "score": 70})
            score += 70
        if parsed.netloc and '@' in parsed.netloc and not (parsed.username or parsed.password):
            findings.append({"rule_id": "MISLEADING_AUTHORITY", "category": "CREDENTIAL_ABUSE", "severity": "CRITICAL", "description": "Misleading userinfo structure often used to mask actual domain.", "evidence": parsed.netloc, "score": 85})
            score += 85

        if len(url) > 200:
            findings.append({"rule_id": "EXCESSIVE_URL_LENGTH", "category": "URL_STRUCTURE", "severity": "LOW", "description": "URL exceeds normal length.", "evidence": f"Length: {len(url)}", "score": 10})
            score += 10

        percent_encodings = len(re.findall(r'%[0-9a-fA-F]{2}', url))
        if percent_encodings > 10:
            findings.append({"rule_id": "EXCESSIVE_ENCODING", "category": "OBFUSCATION", "severity": "MEDIUM", "description": "High number of URL encodings detected, which may attempt to obfuscate the destination.", "evidence": f"Count: {percent_encodings}", "score": 30})
            score += 30

        found_keywords = [kw for kw in self.SUSPICIOUS_KEYWORDS if kw in path or kw in hostname]
        if found_keywords:
            findings.append({"rule_id": "SUSPICIOUS_KEYWORDS", "category": "PHISHING_HEURISTICS", "severity": "MEDIUM", "description": "URL contains keywords commonly associated with credential harvesting.", "evidence": ", ".join(found_keywords), "score": sum([15 for _ in found_keywords])})
            score += sum([15 for _ in found_keywords])

        if score >= 80:
            risk_level = "CRITICAL"
        elif score >= 60:
            risk_level = "HIGH"
        elif score >= 30:
            risk_level = "MEDIUM"
        elif score >= 10:
            risk_level = "LOW"
        else:
            risk_level = "INFO"

        return {
            "risk_score": min(score, 100),
            "risk_level": risk_level,
            "findings": findings
        }

    def scan_pdf_links(self, filepath: Path) -> Dict[str, Any]:
        if not filepath.exists():
            raise FileNotFoundError("PDF file not found")

        doc = fitz.open(filepath)
        total_links = 0
        extracted_links = {}
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            for link in page.get_links():
                if link['kind'] == fitz.LINK_URI:
                    uri = link['uri']
                    if not uri:
                        continue
                    total_links += 1
                    if uri not in extracted_links:
                        extracted_links[uri] = {
                            "original_url": uri,
                            "normalized_url": uri.strip(),
                            "page_numbers": [page_num + 1],
                            "occurrence_count": 1
                        }
                    else:
                        extracted_links[uri]["occurrence_count"] += 1
                        if (page_num + 1) not in extracted_links[uri]["page_numbers"]:
                            extracted_links[uri]["page_numbers"].append(page_num + 1)
        doc.close()

        analyzed_links = []
        stats = {
            "safe": 0, "suspicious": 0, "high_risk": 0, "dangerous_scheme": 0, "invalid": 0
        }

        for uri, data in extracted_links.items():
            analysis = self._analyze_url(data["normalized_url"])
            link_record = {**data, **analysis}
            try:
                parsed = urllib.parse.urlparse(data["normalized_url"])
                link_record["protocol"] = parsed.scheme
                link_record["hostname"] = parsed.hostname
                try:
                    link_record["port"] = parsed.port
                except ValueError:
                    link_record["port"] = None
                link_record["path"] = parsed.path
                link_record["has_query"] = bool(parsed.query)
                link_record["has_fragment"] = bool(parsed.fragment)
            except Exception:
                link_record["protocol"] = ""
                link_record["hostname"] = ""
                link_record["port"] = None
                link_record["path"] = ""
                link_record["has_query"] = False
                link_record["has_fragment"] = False

            analyzed_links.append(link_record)

            risk = analysis["risk_level"]
            if risk == "CRITICAL" and any(f["rule_id"] == "MALFORMED_URL" for f in analysis["findings"]):
                stats["invalid"] += 1
            elif risk == "CRITICAL" and any(f["rule_id"] == "DANGEROUS_SCHEME" for f in analysis["findings"]):
                stats["dangerous_scheme"] += 1
            elif risk in ["HIGH", "CRITICAL"]:
                stats["high_risk"] += 1
            elif risk in ["LOW", "MEDIUM"]:
                stats["suspicious"] += 1
            else:
                stats["safe"] += 1

        return {
            "scan_id": uuid.uuid4().hex[:16],
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "total_links": total_links,
            "unique_links": len(extracted_links),
            "stats": stats,
            "links": analyzed_links
        }

unsafe_link_detection_service = UnsafeLinkDetectionService()
