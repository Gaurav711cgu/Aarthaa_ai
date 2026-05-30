# Security Policy

## Supported Versions
| Version | Supported |
|---------|-----------|
| 2.x (main) | ✅ Active |
| 1.x | ❌ No longer maintained |

## Reporting a Vulnerability
Please do NOT open a public GitHub issue for security vulnerabilities.

Email: gauravkumarnayak@gmail.com  
Subject: [SECURITY] Artha AI — <brief description>

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (optional)

We will respond within 48 hours and aim to patch within 7 days for critical issues.

## Known Security Scope
- JWT signing key rotation endpoint (admin only)
- SQL injection prevention in FinLens query engine
- Model integrity via SHA-256 hash verification
- Input size limits on all upload endpoints
