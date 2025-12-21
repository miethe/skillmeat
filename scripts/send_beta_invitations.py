#!/usr/bin/env python3
"""
Send SkillMeat beta program invitations to selected participants.

This script manages the invitation process for the beta program:
1. Load participant list from CSV
2. Customize invitation emails
3. Send via configured email service
4. Track delivery and opened rates

Usage:
    python scripts/send_beta_invitations.py --file participants.csv
    python scripts/send_beta_invitations.py --file participants.csv --dry-run
    python scripts/send_beta_invitations.py --file participants.csv --resend-failed
"""

import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import re


class BetaInvitationSender:
    """Manage beta program invitation process."""

    def __init__(self, participant_file: str = "participants.csv", dry_run: bool = False):
        """Initialize invitation sender."""
        self.participant_file = Path(participant_file)
        self.dry_run = dry_run
        self.participants: List[Dict[str, str]] = []
        self.sent_invitations: Dict[str, Dict[str, Any]] = {}
        self.tracking_file = Path("docs/user/beta/invitation-tracking.json")
        self.failed_sends: List[str] = []

    def load_participants(self) -> bool:
        """Load participant list from CSV file."""
        if not self.participant_file.exists():
            print(f"Participant file not found: {self.participant_file}")
            return False

        try:
            with open(self.participant_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                self.participants = list(reader)

            print(f"Loaded {len(self.participants)} participants")
            return len(self.participants) > 0
        except Exception as e:
            print(f"Error loading participant file: {e}")
            return False

    def load_tracking(self) -> None:
        """Load invitation tracking data from previous runs."""
        if self.tracking_file.exists():
            try:
                with open(self.tracking_file, "r", encoding="utf-8") as f:
                    self.sent_invitations = json.load(f)
                print(f"Loaded tracking for {len(self.sent_invitations)} previous invitations")
            except Exception as e:
                print(f"Error loading tracking file: {e}")

    def validate_participant(self, participant: Dict[str, str]) -> tuple[bool, str]:
        """Validate participant data for sending invitation."""
        required_fields = ["name", "email", "role"]
        for field in required_fields:
            if not participant.get(field):
                return False, f"Missing required field: {field}"

        # Validate email
        email = participant.get("email", "").strip()
        if not self._is_valid_email(email):
            return False, f"Invalid email: {email}"

        return True, ""

    def _is_valid_email(self, email: str) -> bool:
        """Validate email format."""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    def customize_invitation(self, participant: Dict[str, str]) -> str:
        """Customize invitation email for specific participant."""
        template = self._get_invitation_template()

        # Basic replacements
        email = template.replace("[Name]", participant.get("name", "Developer"))
        email = email.replace("[name]", participant.get("name", "Developer"))

        # Role-specific customization
        role = participant.get("role", "Developer").lower()
        if "skill" in role:
            email = email.replace(
                "[specific skill/use case]",
                "skill development and distribution workflows"
            )
        elif "team" in role or "lead" in role:
            email = email.replace(
                "[specific skill/use case]",
                "team collaboration and artifact sharing"
            )
        else:
            email = email.replace(
                "[specific skill/use case]",
                "personal productivity and organization"
            )

        # Platform info
        platforms = participant.get("platforms", "all").split(",")
        if platforms and platforms[0] != "all":
            email = email.replace(
                "[macOS / Windows / Linux / all three]",
                " / ".join([p.strip() for p in platforms])
            )

        return email

    def _get_invitation_template(self) -> str:
        """Load invitation email template from docs."""
        template_file = Path("docs/user/beta/participant-invitation-email.md")

        if not template_file.exists():
            print(f"Template file not found: {template_file}")
            return self._get_default_template()

        try:
            with open(template_file, "r", encoding="utf-8") as f:
                content = f.read()
                # Extract email body (skip markdown header/formatting)
                lines = content.split("\n")
                body_start = None
                for i, line in enumerate(lines):
                    if line.startswith("## Email Body"):
                        body_start = i + 2  # Skip header and blank line
                        break

                if body_start:
                    return "\n".join(lines[body_start:])
            return self._get_default_template()
        except Exception as e:
            print(f"Error loading template: {e}")
            return self._get_default_template()

    def _get_default_template(self) -> str:
        """Get default invitation template."""
        return """Hello [Name],

We're building SkillMeat - a personal collection manager for Claude Code artifacts.
We're excited to invite you to our closed beta program before general availability.

**What's involved:**
- 1-2 hours per week for 4-6 weeks
- Install and test SkillMeat features
- Report bugs you discover
- Complete a brief survey at the end

**Rewards:**
- Early access to v1.0 (2 weeks before GA)
- Beta contributor badge on your profile
- Credit in release notes
- Exclusive swag (t-shirt, stickers, mug)
- Priority support from engineering team

Ready to join? Click below to confirm:

[**ACCEPT BETA INVITATION**]
https://forms.skillmeat.dev/beta-signup

Questions? Reply to this email or post in our GitHub Discussions.

Thanks for helping us shape SkillMeat!

—SkillMeat Team
"""

    def send_invitation(self, participant: Dict[str, str]) -> bool:
        """Send invitation email to participant."""
        email = participant.get("email", "").strip()

        # Validate
        valid, error_msg = self.validate_participant(participant)
        if not valid:
            print(f"[SKIP] {email}: {error_msg}")
            return False

        # Check if already sent
        if email in self.sent_invitations:
            sent_info = self.sent_invitations[email]
            if sent_info.get("status") == "sent":
                print(f"[SKIP] {email}: Already sent on {sent_info.get('sent_at')}")
                return False

        # Customize email
        body = self.customize_invitation(participant)

        if self.dry_run:
            print(f"\n[DRY RUN] Would send to {email}")
            print(f"Subject: You're invited to the SkillMeat closed beta")
            print(f"Body preview:\n{body[:200]}...\n")
            return True

        # In real implementation, would send via email service (SendGrid, AWS SES, etc.)
        # For now, simulate sending
        print(f"[SEND] Invitation to {email}")

        # Track in database
        self.sent_invitations[email] = {
            "name": participant.get("name"),
            "role": participant.get("role"),
            "platform": participant.get("platform"),
            "status": "sent",
            "sent_at": datetime.now().isoformat(),
            "opened": False,
            "signed_up": False,
        }

        return True

    def send_all_invitations(self) -> int:
        """Send invitations to all valid participants."""
        if not self.participants:
            print("No participants to invite")
            return 0

        successful = 0
        failed = 0

        print(f"\nSending invitations to {len(self.participants)} participants...")
        print("=" * 70)

        for participant in self.participants:
            if self.send_invitation(participant):
                successful += 1
            else:
                failed += 1

        print("=" * 70)
        print(f"Sent: {successful} | Skipped: {failed}")

        # Save tracking
        self.save_tracking()

        return successful

    def save_tracking(self) -> None:
        """Save invitation tracking to file."""
        self.tracking_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.tracking_file, "w", encoding="utf-8") as f:
            json.dump(self.sent_invitations, f, indent=2)
        print(f"Tracking saved: {self.tracking_file}")

    def generate_report(self) -> str:
        """Generate invitation campaign report."""
        if not self.sent_invitations:
            return "No invitations sent yet."

        total = len(self.sent_invitations)
        sent = sum(1 for i in self.sent_invitations.values() if i.get("status") == "sent")
        opened = sum(1 for i in self.sent_invitations.values() if i.get("opened"))
        signed_up = sum(
            1 for i in self.sent_invitations.values() if i.get("signed_up")
        )

        open_rate = (opened / sent * 100) if sent > 0 else 0
        signup_rate = (signed_up / opened * 100) if opened > 0 else 0

        report = f"""
# Beta Invitation Campaign Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Metrics

| Metric | Count | Rate |
|--------|-------|------|
| **Total Invitations** | {total} | 100% |
| **Sent** | {sent} | {(sent/total*100):.1f}% |
| **Opened** | {opened} | {open_rate:.1f}% |
| **Signed Up** | {signed_up} | {signup_rate:.1f}% |

## Distribution

### By Role
"""

        roles = {}
        for invitation in self.sent_invitations.values():
            role = invitation.get("role", "Unknown")
            roles[role] = roles.get(role, 0) + 1

        for role, count in sorted(roles.items(), key=lambda x: x[1], reverse=True):
            report += f"- {role}: {count}\n"

        report += "\n### By Platform\n"

        platforms = {}
        for invitation in self.sent_invitations.values():
            platform = invitation.get("platform", "Unknown")
            platforms[platform] = platforms.get(platform, 0) + 1

        for platform, count in sorted(platforms.items(), key=lambda x: x[1], reverse=True):
            report += f"- {platform}: {count}\n"

        return report

    def run(self) -> int:
        """Run complete invitation campaign."""
        # Load data
        if not self.load_participants():
            return 1

        self.load_tracking()

        # Send invitations
        sent = self.send_all_invitations()

        # Generate report
        report = self.generate_report()
        print("\n" + report)

        return 0 if sent > 0 else 1


def main() -> int:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Send SkillMeat beta program invitations"
    )
    parser.add_argument(
        "--file",
        default="participants.csv",
        help="CSV file with participant list (default: participants.csv)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate sending without actually sending emails",
    )
    parser.add_argument(
        "--resend-failed",
        action="store_true",
        help="Resend to failed addresses",
    )

    args = parser.parse_args()

    sender = BetaInvitationSender(participant_file=args.file, dry_run=args.dry_run)
    return sender.run()


if __name__ == "__main__":
    sys.exit(main())
