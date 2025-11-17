"""Publisher agreement management for marketplace.

This module provides versioned publisher agreements and terms of service
that publishers must accept before publishing bundles.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AgreementVersion(BaseModel):
    """Publisher agreement version metadata.

    Attributes:
        version: Version identifier (e.g., "1.0.0")
        effective_date: Date when agreement became effective
        title: Agreement title
        description: Brief description of agreement
        content: Full agreement text (markdown)
        is_current: Whether this is the current version
    """

    version: str = Field(..., description="Version identifier")
    effective_date: datetime = Field(..., description="Effective date")
    title: str = Field(..., description="Agreement title")
    description: str = Field(..., description="Brief description")
    content: str = Field(..., description="Full agreement text")
    is_current: bool = Field(False, description="Is current version")


class PublisherAgreementManager:
    """Manager for publisher agreements and terms of service.

    Provides functionality for:
    - Retrieving agreement versions
    - Getting current agreement
    - Displaying agreement text
    - Tracking agreement changes
    """

    # Agreement v1.0.0 content
    AGREEMENT_V1_CONTENT = """# SkillMeat Marketplace Publisher Agreement

**Version**: 1.0.0
**Effective Date**: 2025-11-17

## 1. Grant of Rights

By publishing content to SkillMeat Marketplace ("Marketplace"), you ("Publisher") grant SkillMeat and its users the following rights:

1.1. **Distribution Rights**: The right to distribute your submitted content ("Content") through the Marketplace platform to end users.

1.2. **Derivative Works**: The right to create derivative works from your Content to the extent permitted by your chosen license.

1.3. **Public Display**: The right to publicly display and promote your Content within the Marketplace, including screenshots, descriptions, and metadata.

1.4. **Technical Modifications**: The right to make technical modifications necessary for distribution, such as format conversions, compression, or packaging.

## 2. Publisher Responsibilities

You represent and warrant that:

2.1. **Ownership**: You own or have obtained all necessary rights to distribute all submitted Content.

2.2. **No Infringement**: The Content does not violate any intellectual property rights, including copyrights, trademarks, patents, or trade secrets.

2.3. **Legal Compliance**: The Content complies with all applicable laws and regulations, including export controls and data privacy laws.

2.4. **Accurate Information**: All licensing information, attribution, and metadata you provide is accurate and complete.

2.5. **Quality Standards**: The Content meets minimum quality standards and is free from malware, malicious code, or security vulnerabilities.

## 3. License Compliance

You agree to:

3.1. **Honor License Terms**: Respect and honor all license terms of any third-party components included in your Content.

3.2. **Proper Attribution**: Provide proper attribution for all third-party components according to their license requirements.

3.3. **License Compatibility**: Resolve any license conflicts before publishing, ensuring all included components are compatible with your chosen license.

3.4. **License Updates**: Promptly update your Content if you discover license issues after publication.

3.5. **Accurate Declaration**: Accurately declare the license of your Content and all included components.

## 4. Content Standards

Published Content must not:

4.1. **Malware**: Contain viruses, malware, spyware, ransomware, or any other malicious code.

4.2. **Security Violations**: Compromise system security, privacy, or stability.

4.3. **Illegal Content**: Include illegal content or facilitate illegal activities.

4.4. **Harmful Content**: Contain content that is defamatory, harassing, threatening, or discriminatory.

4.5. **Deceptive Practices**: Use misleading descriptions, false claims, or deceptive marketing.

4.6. **Privacy Violations**: Collect or transmit user data without proper disclosure and consent.

## 5. Moderation and Removal

SkillMeat reserves the right to:

5.1. **Review Submissions**: Review and moderate all Content submissions before making them available in the Marketplace.

5.2. **Remove Content**: Remove Content that violates this Agreement, applicable laws, or community standards.

5.3. **Suspend Publishers**: Suspend or terminate Publisher accounts that repeatedly violate this Agreement.

5.4. **DMCA Compliance**: Respond to valid DMCA takedown requests and other intellectual property claims.

5.5. **No Liability**: Exercise these rights without liability to you for removal or suspension.

## 6. Intellectual Property

6.1. **Your IP**: You retain all intellectual property rights to your original Content, subject to the licenses granted in Section 1.

6.2. **SkillMeat Marks**: You may not use SkillMeat's trademarks, service marks, or branding except as explicitly permitted for Marketplace promotion.

6.3. **Third-Party Marks**: You must have proper rights to use any third-party trademarks included in your Content.

6.4. **Attribution**: You agree to be attributed as the publisher of your Content in the Marketplace.

## 7. Warranty Disclaimer

7.1. **AS-IS**: Content is provided "AS IS" and "AS AVAILABLE" without warranties of any kind.

7.2. **No Warranty**: Publisher makes no warranties regarding:
   - Functionality or fitness for any particular purpose
   - Accuracy or completeness
   - Absence of errors or bugs
   - Compatibility with any systems or software
   - Security or safety

7.3. **User Responsibility**: Users accept Content at their own risk.

## 8. Liability Limitation

8.1. **Limited Liability**: Publisher's liability under this Agreement is limited to the maximum extent permitted by applicable law.

8.2. **No Consequential Damages**: Publisher is not liable for any indirect, incidental, consequential, or punitive damages arising from the use of Content.

8.3. **Indemnification**: Publisher agrees to indemnify SkillMeat against claims arising from Content that violates this Agreement or applicable laws.

## 9. Payments and Revenue (Reserved)

9.1. **Future Implementation**: The Marketplace may implement paid Content and revenue sharing in the future.

9.2. **Current Status**: All Content is currently provided free of charge to users.

9.3. **Updates**: This section will be updated before any paid Content features are implemented.

## 10. Term and Termination

10.1. **Term**: This Agreement begins when you accept it and continues until terminated.

10.2. **Termination by Publisher**: You may terminate by removing your Content from the Marketplace.

10.3. **Termination by SkillMeat**: SkillMeat may terminate your publishing privileges for violations of this Agreement.

10.4. **Survival**: Sections 2, 6, 7, 8, and 11 survive termination.

## 11. General Provisions

11.1. **Entire Agreement**: This Agreement constitutes the entire agreement between you and SkillMeat regarding Marketplace publishing.

11.2. **Modifications**: SkillMeat may modify this Agreement by posting a new version with updated effective date. Continued publishing constitutes acceptance of modifications.

11.3. **Governing Law**: This Agreement is governed by the laws of [Jurisdiction], without regard to conflict of law principles.

11.4. **Severability**: If any provision is found unenforceable, the remaining provisions remain in effect.

11.5. **No Waiver**: Failure to enforce any provision does not constitute a waiver.

11.6. **Contact**: For questions about this Agreement, contact: legal@skillmeat.io

## Acceptance

By clicking "I Agree" or publishing Content to the Marketplace, you acknowledge that you have read, understood, and agree to be bound by this Publisher Agreement.
"""

    def __init__(self):
        """Initialize publisher agreement manager."""
        self._agreements: Dict[str, AgreementVersion] = {}
        self._current_version = "1.0.0"

        # Initialize agreements
        self._load_agreements()

    def _load_agreements(self) -> None:
        """Load available agreement versions."""
        # Add v1.0.0
        self._agreements["1.0.0"] = AgreementVersion(
            version="1.0.0",
            effective_date=datetime(2025, 11, 17),
            title="SkillMeat Marketplace Publisher Agreement",
            description="Initial publisher agreement for SkillMeat Marketplace",
            content=self.AGREEMENT_V1_CONTENT,
            is_current=True,
        )

    def get_agreement(self, version: Optional[str] = None) -> AgreementVersion:
        """Get publisher agreement by version.

        Args:
            version: Agreement version (uses current if None)

        Returns:
            AgreementVersion

        Raises:
            ValueError: If version not found
        """
        if version is None:
            version = self._current_version

        if version not in self._agreements:
            raise ValueError(f"Unknown agreement version: {version}")

        return self._agreements[version]

    def get_current_agreement(self) -> AgreementVersion:
        """Get current publisher agreement.

        Returns:
            Current AgreementVersion
        """
        return self.get_agreement(self._current_version)

    def get_current_version(self) -> str:
        """Get current agreement version string.

        Returns:
            Version string (e.g., "1.0.0")
        """
        return self._current_version

    def get_all_versions(self) -> list[str]:
        """Get list of all available versions.

        Returns:
            List of version strings, sorted newest first
        """
        return sorted(self._agreements.keys(), reverse=True)

    def get_agreement_summary(self, version: Optional[str] = None) -> str:
        """Get brief summary of agreement.

        Args:
            version: Agreement version (uses current if None)

        Returns:
            Summary text
        """
        agreement = self.get_agreement(version)

        lines = [
            agreement.title,
            "=" * len(agreement.title),
            "",
            f"Version: {agreement.version}",
            f"Effective Date: {agreement.effective_date.strftime('%Y-%m-%d')}",
            "",
            agreement.description,
            "",
            "Key Sections:",
            "  1. Grant of Rights - Distribution and usage permissions",
            "  2. Publisher Responsibilities - Your obligations and warranties",
            "  3. License Compliance - Requirements for license management",
            "  4. Content Standards - Prohibited content and practices",
            "  5. Moderation and Removal - SkillMeat's rights to moderate",
            "  6. Intellectual Property - IP rights and usage",
            "  7. Warranty Disclaimer - No warranties provided",
            "  8. Liability Limitation - Limited liability provisions",
            "",
            "Read the full agreement before accepting.",
        ]

        return "\n".join(lines)

    def format_for_cli(self, version: Optional[str] = None, max_width: int = 80) -> str:
        """Format agreement for CLI display.

        Args:
            version: Agreement version (uses current if None)
            max_width: Maximum line width for wrapping

        Returns:
            Formatted text for terminal display
        """
        agreement = self.get_agreement(version)

        # Get header
        lines = [
            "=" * max_width,
            agreement.title.center(max_width),
            f"Version {agreement.version} - Effective {agreement.effective_date.strftime('%Y-%m-%d')}".center(max_width),
            "=" * max_width,
            "",
        ]

        # Add content (simplified for CLI)
        lines.extend([
            "By publishing to SkillMeat Marketplace, you agree to:",
            "",
            "1. Grant distribution rights to your content",
            "2. Ensure you have legal rights to all submitted content",
            "3. Comply with all license requirements",
            "4. Meet content quality and security standards",
            "5. Provide accurate information and attribution",
            "6. Accept content \"as-is\" without warranties",
            "7. Indemnify SkillMeat against claims",
            "",
            "SkillMeat reserves the right to:",
            "- Review and moderate submissions",
            "- Remove content that violates terms",
            "- Respond to DMCA/takedown requests",
            "",
            "For full terms, see: docs/legal/publisher-agreement-v1.md",
            "=" * max_width,
        ])

        return "\n".join(lines)

    def save_agreement_to_file(
        self,
        output_dir: Path,
        version: Optional[str] = None,
    ) -> Path:
        """Save agreement to markdown file.

        Args:
            output_dir: Output directory
            version: Agreement version (uses current if None)

        Returns:
            Path to saved file
        """
        agreement = self.get_agreement(version)

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        filename = f"publisher-agreement-v{agreement.version}.md"
        output_path = output_dir / filename

        # Write agreement
        with open(output_path, "w") as f:
            f.write(agreement.content)

        logger.info(f"Saved agreement v{agreement.version} to {output_path}")

        return output_path

    def has_version(self, version: str) -> bool:
        """Check if agreement version exists.

        Args:
            version: Version string

        Returns:
            True if version exists, False otherwise
        """
        return version in self._agreements
