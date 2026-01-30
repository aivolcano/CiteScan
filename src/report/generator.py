from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from pathlib import Path

from ..parsers.bib_parser import BibEntry
from ..analyzers.metadata_comparator import ComparisonResult
from ..analyzers.duplicate_detector import DuplicateGroup


@dataclass
class EntryReport:
    """Report for a single bib entry (bib-only: entry + comparison)."""
    entry: BibEntry
    comparison: Optional[ComparisonResult]


class ReportGenerator:
    """Generates bibliography-only markdown reports."""

    def __init__(
        self,
        minimal_verified: bool = False,
        check_preprint_ratio: bool = True,
        preprint_warning_threshold: float = 0.50,
    ):
        self.entries: List[EntryReport] = []
        self.duplicate_groups: Optional[List[DuplicateGroup]] = None
        self.bib_files: List[str] = []
        self.minimal_verified = minimal_verified
        self.check_preprint_ratio = check_preprint_ratio
        self.preprint_warning_threshold = preprint_warning_threshold

    def add_entry_report(self, report: EntryReport):
        self.entries.append(report)

    def set_metadata(self, bib_files: str | List[str], tex_files: str | List[str] = None):
        if isinstance(bib_files, str):
            self.bib_files = [bib_files]
        else:
            self.bib_files = list(bib_files) if bib_files else []

    def set_duplicate_groups(self, groups: List[DuplicateGroup]):
        self.duplicate_groups = groups

    def _is_verified(self, entry: EntryReport) -> bool:
        return not self._has_issues(entry)

    def _has_issues(self, entry: EntryReport) -> bool:
        return bool(entry.comparison and entry.comparison.has_issues)

    def _is_preprint(self, entry: BibEntry) -> bool:
        preprint_keywords = [
            "arxiv", "biorxiv", "medrxiv", "ssrn", "preprint",
            "openreview", "techreport", "technical report", "working paper",
        ]
        if entry.entry_type.lower() in ["techreport", "unpublished", "misc"]:
            text = " ".join([
                entry.journal.lower(), entry.booktitle.lower(),
                entry.publisher.lower(), entry.entry_type.lower(),
            ])
            if any(k in text for k in preprint_keywords):
                return True
        if entry.has_arxiv:
            return True
        venue = " ".join([entry.journal.lower(), entry.booktitle.lower(), entry.publisher.lower()])
        return any(k in venue for k in preprint_keywords)

    def get_summary_stats(self) -> dict:
        """Return bibliography issue counts only (no LaTeX)."""
        total = len(self.entries)
        title_mismatches = author_mismatches = year_mismatches = unable_to_verify = 0
        for e in self.entries:
            if not e.comparison:
                continue
            if e.comparison.has_issues:
                for issue in e.comparison.issues:
                    if "Title mismatch" in issue:
                        title_mismatches += 1
                    elif "Author mismatch" in issue:
                        author_mismatches += 1
                    elif "Year mismatch" in issue:
                        year_mismatches += 1
                    elif "Unable to find" in issue:
                        unable_to_verify += 1

        stats = {}
        if title_mismatches > 0:
            stats["Title Mismatches"] = title_mismatches
        if author_mismatches > 0:
            stats["Author Mismatches"] = author_mismatches
        if year_mismatches > 0:
            stats["Year Mismatches"] = year_mismatches
        if unable_to_verify > 0:
            stats["Unable to Verify"] = unable_to_verify
        if self.duplicate_groups:
            stats["Duplicate Groups"] = len(self.duplicate_groups)
        return stats

    def _generate_issues_section(self) -> List[str]:
        lines = ["## ⚠️ Critical Issues Detected", ""]
        has_any = False

        if self.duplicate_groups:
            has_any = True
            lines.append("### 🔄 Duplicate Entries")
            for i, group in enumerate(self.duplicate_groups, 1):
                lines.append(f"#### Group {i} (Similarity: {group.similarity_score:.0%})")
                lines.append(f"**Reason:** {group.reason}")
                lines.append("")
                lines.append("| Key | Title | Year |")
                lines.append("|-----|-------|------|")
                for entry in group.entries:
                    lines.append(f"| `{entry.key}` | {entry.title} | {entry.year} |")
                lines.append("")

        issue_entries = [e for e in self.entries if self._has_issues(e)]
        if issue_entries:
            has_any = True
            lines.append("### ⚠️ Metadata Issues")
            for report in issue_entries:
                lines.extend(self._format_entry_detail(report, is_verified=False))

        if not has_any:
            lines.append("🎉 **No critical issues found!**")
        return lines

    def _generate_verified_section(self) -> List[str]:
        lines = ["## ✅ Verified Entries", ""]
        verified = [e for e in self.entries if self._is_verified(e)]
        if not verified:
            lines.append("_No verified entries found._")
            return lines
        lines.append(f"Found **{len(verified)}** entries with correct metadata.")
        lines.append("")
        lines.append("<details>")
        lines.append("<summary>Click to view verified entries</summary>")
        lines.append("")
        for report in verified:
            lines.extend(self._format_entry_detail(report, minimal=self.minimal_verified, is_verified=True))
        lines.append("</details>")
        return lines

    def _format_entry_detail(self, report: EntryReport, minimal: bool = False, is_verified: bool = False) -> List[str]:
        entry = report.entry
        comp = report.comparison
        lines = []
        icon = "✅" if is_verified else "⚠️"
        lines.append(f"#### {icon} `{entry.key}`")
        lines.append(f"**Title:** {entry.title}")
        lines.append("")
        if comp:
            status_icon = "✅" if comp.is_match else "❌"
            lines.append(f"- **Metadata Status:** {status_icon} {comp.source.upper()} (Confidence: {comp.confidence:.1%})")
            if comp.has_issues and not minimal:
                lines.append("  - **Discrepancies:**")
                for issue in comp.issues:
                    if "Mismatch" in issue or "mismatch" in issue:
                        lines.append(f"    - 🔴 {issue}")
                        if "Title" in issue:
                            lines.append(f"      - **Bib:** `{comp.bib_title}`")
                            lines.append(f"      - **Fetched:** `{comp.fetched_title}`")
                        elif "Author" in issue:
                            lines.append(f"      - **Bib:** `{', '.join(comp.bib_authors)}`")
                            lines.append(f"      - **Fetched:** `{', '.join(comp.fetched_authors)}`")
                    else:
                        lines.append(f"    - 🔸 {issue}")
        lines.append("")
        lines.append("---")
        lines.append("")
        return lines

    def save_bibliography_report(self, filepath: str):
        """Generate and save bibliography-only report."""
        total = len(self.entries)
        verified = sum(1 for e in self.entries if self._is_verified(e))
        issues = sum(1 for e in self.entries if self._has_issues(e))
        dup_str = str(len(self.duplicate_groups)) if self.duplicate_groups else "N/A"

        preprint_str = "N/A"
        preprint_warning = []
        if self.check_preprint_ratio and self.entries:
            preprint_count = sum(1 for e in self.entries if self._is_preprint(e.entry))
            preprint_ratio = preprint_count / len(self.entries)
            preprint_str = f"{preprint_count} ({preprint_ratio:.1%})"
            if preprint_ratio > self.preprint_warning_threshold:
                preprint_warning = [
                    "",
                    f"> ⚠️ **High Preprint Ratio:** {preprint_ratio:.1%} of entries are preprints.",
                ]

        bib_names = ", ".join([f"`{Path(f).name}`" for f in self.bib_files]) if self.bib_files else "N/A"
        lines = [
            "# Bibliography Validation Report",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "| File Type | Filename |",
            "|-----------|----------|",
            f"| **Bib File(s)** | {bib_names} |",
            "",
            "> **⚠️ Disclaimer:** This report is generated by an automated tool. Please verify reported issues manually.",
            "",
            "## 📊 Summary",
            "",
            "| Metric | Count |",
            "|--------|-------|",
            f"| **Total Entries** | {total} |",
            f"| ✅ **Verified (Clean)** | {verified} |",
            f"| ⚠️ **With Issues** | {issues} |",
            f"| 🔄 **Duplicate Groups** | {dup_str} |",
            f"| 📄 **Preprints** | {preprint_str} |",
            "",
        ]
        if preprint_warning:
            lines.extend(preprint_warning)
            lines.append("")
        lines.extend(self._generate_issues_section())
        lines.append("")
        lines.extend(self._generate_verified_section())
        lines.append("")
        lines.append("---")
        lines.append(f"Report generated by **CiteScan** on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
