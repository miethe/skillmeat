"""Legal compliance checklist for marketplace publishers.

Generates comprehensive checklists based on license type and validates
that all requirements are met before publication.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ComplianceItem:
    """A single compliance checklist item.

    Attributes:
        id: Unique identifier for the item
        question: Question or requirement text
        required: Whether this item must be completed
        category: Category of compliance (license, attribution, copyright, source)
        help_text: Additional explanation or guidance
    """

    id: str
    question: str
    required: bool
    category: str
    help_text: Optional[str] = None

    def __post_init__(self):
        """Validate compliance item."""
        valid_categories = {"license", "attribution", "copyright", "source", "legal"}
        if self.category not in valid_categories:
            raise ValueError(
                f"Invalid category '{self.category}'. "
                f"Must be one of {valid_categories}"
            )


@dataclass
class ComplianceChecklist:
    """Complete compliance checklist for a bundle.

    Attributes:
        checklist_id: Unique identifier for this checklist
        bundle_id: ID of bundle being checked
        license: License identifier for the bundle
        items: List of compliance items
        completed_items: List of completed item IDs
        consents: Dictionary of item_id -> consent (True/False)
        timestamp: When checklist was created
        publisher_signature: Optional digital signature
    """

    checklist_id: str
    bundle_id: str
    license: str
    items: List[ComplianceItem] = field(default_factory=list)
    completed_items: List[str] = field(default_factory=list)
    consents: Dict[str, bool] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    publisher_signature: Optional[str] = None

    @property
    def is_complete(self) -> bool:
        """Check if all required items are completed."""
        required_items = {item.id for item in self.items if item.required}
        completed_required = required_items & set(self.completed_items)
        return completed_required == required_items

    @property
    def completion_percentage(self) -> float:
        """Get completion percentage."""
        if not self.items:
            return 100.0
        required_count = sum(1 for item in self.items if item.required)
        if required_count == 0:
            return 100.0
        completed_count = sum(
            1 for item in self.items if item.required and item.id in self.completed_items
        )
        return (completed_count / required_count) * 100.0

    @property
    def incomplete_required_items(self) -> List[ComplianceItem]:
        """Get list of incomplete required items."""
        return [
            item
            for item in self.items
            if item.required and item.id not in self.completed_items
        ]

    def mark_complete(self, item_id: str, consented: bool = True) -> None:
        """Mark an item as complete.

        Args:
            item_id: ID of item to mark complete
            consented: Whether user consented to this item

        Raises:
            ValueError: If item_id is not found
        """
        item_ids = {item.id for item in self.items}
        if item_id not in item_ids:
            raise ValueError(f"Item ID not found: {item_id}")

        if item_id not in self.completed_items:
            self.completed_items.append(item_id)

        self.consents[item_id] = consented

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation
        """
        return {
            "checklist_id": self.checklist_id,
            "bundle_id": self.bundle_id,
            "license": self.license,
            "items": [
                {
                    "id": item.id,
                    "question": item.question,
                    "required": item.required,
                    "category": item.category,
                    "help_text": item.help_text,
                }
                for item in self.items
            ],
            "completed_items": self.completed_items,
            "consents": self.consents,
            "timestamp": self.timestamp.isoformat(),
            "publisher_signature": self.publisher_signature,
            "is_complete": self.is_complete,
            "completion_percentage": self.completion_percentage,
        }


class ComplianceChecklistGenerator:
    """Generates compliance checklists based on license type."""

    # Base items for all bundles
    BASE_ITEMS = [
        ComplianceItem(
            id="files_licensed",
            question="All files have appropriate license headers",
            required=True,
            category="license",
            help_text="Every source file should include a license header or SPDX identifier",
        ),
        ComplianceItem(
            id="license_file",
            question="LICENSE file is present and matches declared license",
            required=True,
            category="license",
            help_text="Include a LICENSE or COPYING file in the root directory",
        ),
        ComplianceItem(
            id="copyright_accurate",
            question="Copyright notices are accurate and up-to-date",
            required=True,
            category="copyright",
            help_text="Ensure all copyright years and holders are correct",
        ),
        ComplianceItem(
            id="no_proprietary",
            question="No proprietary code included without permission",
            required=True,
            category="legal",
            help_text="Verify you have rights to redistribute all included code",
        ),
        ComplianceItem(
            id="no_secrets",
            question="No secrets or credentials in code",
            required=True,
            category="legal",
            help_text="Remove API keys, passwords, tokens, and other sensitive data",
        ),
        ComplianceItem(
            id="attribution_understood",
            question="Attribution requirements understood and documented",
            required=True,
            category="attribution",
            help_text="Know what attributions are required for dependencies",
        ),
    ]

    # Additional items for GPL/copyleft licenses
    GPL_ITEMS = [
        ComplianceItem(
            id="source_included",
            question="Source code is included or accessible",
            required=True,
            category="source",
            help_text="GPL requires source code availability",
        ),
        ComplianceItem(
            id="modifications_marked",
            question="Modifications are clearly marked",
            required=True,
            category="source",
            help_text="Document any changes you made to the original code",
        ),
        ComplianceItem(
            id="same_license",
            question="Same license applied to derivative works",
            required=True,
            category="license",
            help_text="GPL requires derivatives to use the same license",
        ),
        ComplianceItem(
            id="copyright_preserved",
            question="Original copyright notices preserved",
            required=True,
            category="copyright",
            help_text="Keep all original copyright and license notices",
        ),
    ]

    # Additional items for Apache/BSD/MIT licenses
    PERMISSIVE_ITEMS = [
        ComplianceItem(
            id="license_preserved",
            question="License text preserved in distributions",
            required=True,
            category="license",
            help_text="Include original license text with distributions",
        ),
        ComplianceItem(
            id="copyright_preserved",
            question="Copyright notices preserved",
            required=True,
            category="copyright",
            help_text="Maintain original copyright notices",
        ),
    ]

    # Additional items for Apache 2.0
    APACHE_ITEMS = [
        ComplianceItem(
            id="notice_file",
            question="Attribution requirements in NOTICE file (if applicable)",
            required=False,
            category="attribution",
            help_text="If upstream has a NOTICE file, preserve it and add your attributions",
        ),
        ComplianceItem(
            id="patent_grant",
            question="Understand patent grant implications",
            required=False,
            category="legal",
            help_text="Apache 2.0 includes a patent grant; ensure this is acceptable",
        ),
    ]

    # Additional items for proprietary licenses
    PROPRIETARY_ITEMS = [
        ComplianceItem(
            id="permission_granted",
            question="Explicit permission to redistribute obtained",
            required=True,
            category="legal",
            help_text="Have written permission from copyright holder",
        ),
        ComplianceItem(
            id="terms_clear",
            question="License agreement terms are clear and documented",
            required=True,
            category="legal",
            help_text="Include license agreement or terms of use",
        ),
        ComplianceItem(
            id="commercial_allowed",
            question="Commercial use is explicitly allowed",
            required=True,
            category="legal",
            help_text="Verify that marketplace distribution is permitted",
        ),
    ]

    def __init__(self):
        """Initialize checklist generator."""
        pass

    def create_checklist(
        self, bundle_id: str, license: str, metadata: Optional[Dict] = None
    ) -> ComplianceChecklist:
        """Generate a compliance checklist for a bundle.

        Args:
            bundle_id: Unique identifier for the bundle
            license: License identifier (SPDX)
            metadata: Optional bundle metadata for additional context

        Returns:
            ComplianceChecklist with appropriate items
        """
        checklist_id = str(uuid.uuid4())
        items = list(self.BASE_ITEMS)  # Copy base items

        # Add license-specific items
        if self._is_gpl_license(license):
            items.extend(self.GPL_ITEMS)
        elif self._is_permissive_license(license):
            items.extend(self.PERMISSIVE_ITEMS)
            if license == "Apache-2.0":
                items.extend(self.APACHE_ITEMS)
        elif self._is_proprietary_license(license):
            items.extend(self.PROPRIETARY_ITEMS)

        logger.info(
            f"Generated checklist for {license}: {len(items)} items "
            f"({sum(1 for i in items if i.required)} required)"
        )

        return ComplianceChecklist(
            checklist_id=checklist_id,
            bundle_id=bundle_id,
            license=license,
            items=items,
        )

    def validate_checklist(self, checklist: ComplianceChecklist) -> List[str]:
        """Validate that checklist is properly completed.

        Args:
            checklist: Checklist to validate

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Check if all required items are completed
        if not checklist.is_complete:
            incomplete = checklist.incomplete_required_items
            errors.append(
                f"{len(incomplete)} required items not completed: "
                f"{', '.join(item.question for item in incomplete)}"
            )

        # Check consents
        required_ids = {item.id for item in checklist.items if item.required}
        for item_id in required_ids:
            if item_id not in checklist.consents:
                errors.append(f"Missing consent for required item: {item_id}")
            elif not checklist.consents[item_id]:
                item = next(i for i in checklist.items if i.id == item_id)
                errors.append(
                    f"Consent required for: {item.question}"
                )

        # Check signature for proprietary licenses
        if self._is_proprietary_license(checklist.license):
            if not checklist.publisher_signature:
                errors.append(
                    "Publisher signature required for proprietary licenses"
                )

        return errors

    def get_required_items(self, license: str) -> List[ComplianceItem]:
        """Get required checklist items for a license type.

        Args:
            license: License identifier

        Returns:
            List of required ComplianceItems
        """
        checklist = self.create_checklist("temp", license)
        return [item for item in checklist.items if item.required]

    def _is_gpl_license(self, license: str) -> bool:
        """Check if license is GPL/copyleft.

        Args:
            license: License identifier

        Returns:
            True if GPL-family license
        """
        gpl_licenses = {
            "GPL-2.0",
            "GPL-2.0-only",
            "GPL-2.0-or-later",
            "GPL-3.0",
            "GPL-3.0-only",
            "GPL-3.0-or-later",
            "AGPL-3.0",
            "AGPL-3.0-only",
            "AGPL-3.0-or-later",
            "LGPL-2.1",
            "LGPL-2.1-only",
            "LGPL-2.1-or-later",
            "LGPL-3.0",
            "LGPL-3.0-only",
            "LGPL-3.0-or-later",
        }
        return license in gpl_licenses

    def _is_permissive_license(self, license: str) -> bool:
        """Check if license is permissive.

        Args:
            license: License identifier

        Returns:
            True if permissive license
        """
        permissive = {
            "MIT",
            "Apache-2.0",
            "BSD-2-Clause",
            "BSD-3-Clause",
            "ISC",
            "0BSD",
        }
        return license in permissive

    def _is_proprietary_license(self, license: str) -> bool:
        """Check if license is proprietary.

        Args:
            license: License identifier

        Returns:
            True if proprietary
        """
        return license.lower() in {"proprietary", "commercial", "custom"}
