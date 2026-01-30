"""Verification service for BibTeX entries.

This service extracts the core verification logic from app.py,
making it reusable for both Gradio UI and FastAPI endpoints.
"""
import tempfile
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Optional

from src.parsers import BibParser
from src.fetchers import (
    ArxivFetcher,
    ScholarFetcher,
    CrossRefFetcher,
    SemanticScholarFetcher,
    OpenAlexFetcher,
    DBLPFetcher,
)
from src.analyzers import MetadataComparator, DuplicateDetector
from src.report.generator import EntryReport
from src.config.workflow import get_default_workflow
from src.utils.normalizer import TextNormalizer
from src.core.config import settings
from src.core.logging import get_logger
from src.core.exceptions import ParserException, FetcherException

logger = get_logger(__name__)


@dataclass
class VerificationResult:
    """Result of BibTeX verification."""

    entry_reports: list[EntryReport]
    duplicate_groups: list
    verified_count: int
    warning_count: int
    error_count: int
    total_count: int

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_count == 0:
            return 0.0
        return (self.verified_count / self.total_count) * 100


class VerificationService:
    """Service for verifying BibTeX entries against academic databases."""

    def __init__(self):
        """Initialize verification service."""
        self.parser = BibParser()
        self.arxiv_fetcher = ArxivFetcher()
        self.crossref_fetcher = CrossRefFetcher()
        self.scholar_fetcher = ScholarFetcher()
        self.semantic_scholar_fetcher = SemanticScholarFetcher()
        self.openalex_fetcher = OpenAlexFetcher()
        self.dblp_fetcher = DBLPFetcher()
        self.comparator = MetadataComparator()
        self.duplicate_detector = DuplicateDetector()
        logger.info("VerificationService initialized")

    def verify_bibtex_string(
        self,
        bibtex_content: str,
        progress_callback: Optional[callable] = None,
    ) -> VerificationResult:
        """Verify BibTeX content from string.

        Args:
            bibtex_content: BibTeX content as string
            progress_callback: Optional callback for progress updates (progress, desc)

        Returns:
            VerificationResult with all verification data

        Raises:
            ParserException: If BibTeX parsing fails
            FetcherException: If fetching fails
        """
        if not bibtex_content.strip():
            raise ParserException("Empty BibTeX content provided")

        logger.info("Starting BibTeX verification")

        # Parse BibTeX
        try:
            if progress_callback:
                progress_callback(0, "Parsing BibTeX...")

            # Write to temporary file
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".bib", delete=False, encoding="utf-8"
            ) as f:
                f.write(bibtex_content)
                temp_bib_path = f.name

            entries = self.parser.parse_file(temp_bib_path)
            Path(temp_bib_path).unlink()  # Delete temp file

            if not entries:
                raise ParserException("No valid BibTeX entries found")

            logger.info(f"Parsed {len(entries)} BibTeX entries")

        except Exception as e:
            logger.error(f"BibTeX parsing failed: {e}")
            raise ParserException(f"Failed to parse BibTeX: {str(e)}")

        # Detect duplicates
        duplicate_groups = self.duplicate_detector.find_duplicates(entries)
        if duplicate_groups:
            logger.warning(f"Found {len(duplicate_groups)} duplicate groups")

        # Get workflow configuration
        workflow_config = get_default_workflow()

        # Process entries
        entry_reports = []
        progress_lock = threading.Lock()
        verified_count = 0
        warning_count = 0
        error_count = 0

        if progress_callback:
            progress_callback(0.1, "Initializing fetchers...")

        def process_single_entry(entry, idx, total):
            """Process a single BibTeX entry."""
            comparison_result = None
            all_results = []

            for step in workflow_config.get_enabled_steps():
                result = None

                try:
                    if step.name == "arxiv_id" and entry.has_arxiv and self.arxiv_fetcher:
                        arxiv_meta = self.arxiv_fetcher.fetch_by_id(entry.arxiv_id)
                        if arxiv_meta:
                            result = self.comparator.compare_with_arxiv(entry, arxiv_meta)

                    elif step.name == "crossref_doi" and entry.doi and self.crossref_fetcher:
                        crossref_result = self.crossref_fetcher.search_by_doi(entry.doi)
                        if crossref_result:
                            result = self.comparator.compare_with_crossref(entry, crossref_result)

                    elif step.name == "semantic_scholar" and entry.title and self.semantic_scholar_fetcher:
                        ss_result = (
                            self.semantic_scholar_fetcher.fetch_by_doi(entry.doi)
                            if entry.doi
                            else None
                        )
                        if not ss_result:
                            ss_result = self.semantic_scholar_fetcher.search_by_title(entry.title)
                        if ss_result:
                            result = self.comparator.compare_with_semantic_scholar(entry, ss_result)

                    elif step.name == "dblp" and entry.title and self.dblp_fetcher:
                        dblp_result = self.dblp_fetcher.search_by_title(entry.title)
                        if dblp_result:
                            result = self.comparator.compare_with_dblp(entry, dblp_result)

                    elif step.name == "openalex" and entry.title and self.openalex_fetcher:
                        oa_result = (
                            self.openalex_fetcher.fetch_by_doi(entry.doi)
                            if entry.doi
                            else None
                        )
                        if not oa_result:
                            oa_result = self.openalex_fetcher.search_by_title(entry.title)
                        if oa_result:
                            result = self.comparator.compare_with_openalex(entry, oa_result)

                    elif step.name == "arxiv_title" and entry.title and self.arxiv_fetcher:
                        results = self.arxiv_fetcher.search_by_title(entry.title, max_results=3)
                        if results:
                            best_result = None
                            best_sim = 0.0
                            norm1 = TextNormalizer.normalize_for_comparison(entry.title)
                            for r in results:
                                sim = TextNormalizer.similarity_ratio(
                                    norm1,
                                    TextNormalizer.normalize_for_comparison(r.title),
                                )
                                if sim > best_sim:
                                    best_sim, best_result = sim, r
                            if best_result and best_sim > 0.5:
                                result = self.comparator.compare_with_arxiv(entry, best_result)

                    elif step.name == "crossref_title" and entry.title and self.crossref_fetcher:
                        crossref_result = self.crossref_fetcher.search_by_title(entry.title)
                        if crossref_result:
                            result = self.comparator.compare_with_crossref(entry, crossref_result)

                    elif step.name == "google_scholar" and entry.title and self.scholar_fetcher:
                        scholar_result = self.scholar_fetcher.search_by_title(entry.title)
                        if scholar_result:
                            result = self.comparator.compare_with_scholar(entry, scholar_result)

                except Exception as e:
                    logger.warning(f"Error in step {step.name} for entry {entry.key}: {e}")
                    continue

                if result:
                    all_results.append(result)
                    if result.is_match:
                        comparison_result = result
                        break

            # Select best result if no perfect match
            if not comparison_result and all_results:
                all_results.sort(key=lambda r: r.confidence, reverse=True)
                comparison_result = all_results[0]
            elif not comparison_result:
                comparison_result = self.comparator.create_unable_result(
                    entry, "Unable to find this paper in any data source"
                )

            return EntryReport(entry=entry, comparison=comparison_result)

        # Process entries concurrently
        max_workers = min(settings.max_workers, len(entries))
        logger.info(f"Processing {len(entries)} entries with {max_workers} workers")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_entry = {
                executor.submit(process_single_entry, e, i, len(entries)): (e, i)
                for i, e in enumerate(entries)
            }

            for future in as_completed(future_to_entry):
                entry, idx = future_to_entry[future]
                try:
                    entry_report = future.result()
                    with progress_lock:
                        entry_reports.append(entry_report)

                        if entry_report.comparison and entry_report.comparison.is_match:
                            verified_count += 1
                        elif entry_report.comparison and entry_report.comparison.has_issues:
                            warning_count += 1
                        else:
                            error_count += 1

                        if progress_callback:
                            progress_callback(
                                0.1 + (0.9 * (idx + 1) / len(entries)),
                                f"Verifying entries {idx + 1}/{len(entries)}...",
                            )

                except Exception as e:
                    with progress_lock:
                        error_count += 1
                        logger.error(f"Error processing entry {entry.key}: {e}")

        logger.info(
            f"Verification complete: {verified_count} verified, "
            f"{warning_count} warnings, {error_count} errors"
        )

        return VerificationResult(
            entry_reports=entry_reports,
            duplicate_groups=duplicate_groups,
            verified_count=verified_count,
            warning_count=warning_count,
            error_count=error_count,
            total_count=len(entries),
        )
