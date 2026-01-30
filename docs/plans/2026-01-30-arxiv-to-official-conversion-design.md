# arXiv to Official Publication Conversion - Design Document

**Date:** 2026-01-30
**Feature:** Smart BibTeX Cleanup - arXiv → Official Publication Conversion
**Goal:** Transform CiteScan from a verification tool into an original smart bibliography management system

---

## 1. Overview

### Problem Statement
Researchers often cite arXiv preprints in their bibliographies, but academic submissions prefer official publication citations (conference/journal versions). Manually finding and updating these citations is tedious and error-prone.

### Solution
Extend CiteScan to automatically detect when an arXiv preprint has been officially published, and provide users with easy access to both versions so they can copy the official BibTeX from the venue website.

### Key Constraint
**$0 maintenance cost** - No ongoing API costs, no server infrastructure. Pure algorithmic processing using existing free academic APIs.

---

## 2. Core Architecture

### Current Flow
```
Parse BibTeX → Fetch metadata → Compare & verify → Display results
```

### Enhanced Flow
```
Parse BibTeX → Fetch metadata → Compare & verify → Detect arXiv preprints
    ↓
If arXiv detected → Search for official version → Match validation
    ↓
Display results with dual links (arXiv + Official)
```

### Components Modified
1. **Data Model** (`src/analyzers/metadata_comparator.py`)
2. **Detection Logic** (`src/analyzers/metadata_comparator.py`)
3. **Workflow** (`app.py` - `process_single_entry()`)
4. **UI Rendering** (`app.py` - `format_entry_card()`)
5. **CSS Styling** (`app.py` - `REPORT_CSS`)

---

## 3. Detection Logic

### Step 1: Identify arXiv Entries
An entry is considered an arXiv preprint if:
- Has `eprint` field with arXiv ID pattern (e.g., "2304.12345")
- `journal` or `booktitle` field contains "arXiv" or "preprint"
- URL contains "arxiv.org"

**Important:** If venue field contains known conference/journal names (ACL, NeurIPS, ICML, etc.), treat as official publication even if arXiv is mentioned in notes.

### Step 2: Search for Official Version
Use existing fetchers in priority order:
1. **Semantic Scholar** - Query by arXiv ID (best for finding publication venue)
2. **CrossRef** - Query by title (best for DOI)
3. **DBLP** - Query by title (best for CS conferences)
4. **OpenAlex** - Query by DOI or title (comprehensive coverage)

### Step 3: Validate Official Publication
A fetched result is considered an official publication if ALL criteria met:
- ✓ Has DOI (and DOI is NOT arxiv.org)
- ✓ Venue is NOT "arXiv" or "preprint"
- ✓ Venue matches known conferences/journals (NeurIPS, ICML, ICLR, ACL, EMNLP, CVPR, ICCV, ECCV, ACM, IEEE, etc.)
- ✓ Title similarity > 95%
- ✓ Author overlap > 70%
- ✓ Year is same or +1 year from arXiv (accounts for publication delay)

### Step 4: Extract Official URL
Priority order:
1. **DOI link** - `https://doi.org/{doi}` (most reliable)
2. **Venue-specific URL** - ACL Anthology, CVF, ACM Digital Library, IEEE Xplore
3. **Paper URL from database** - Fallback from Semantic Scholar/OpenAlex

---

## 4. Data Model Changes

### ComparisonResult Enhancements
Add new fields to `ComparisonResult` dataclass:

```python
@dataclass
class ComparisonResult:
    # ... existing fields ...

    # New fields for arXiv conversion
    is_arxiv_preprint: bool = False
    has_official_version: bool = False
    official_venue: Optional[str] = None  # e.g., "ACL 2025", "NeurIPS 2024"
    arxiv_url: Optional[str] = None
    official_url: Optional[str] = None
```

### New Methods
```python
class MetadataComparator:
    def detect_arxiv_entry(self, bib_entry: BibEntry) -> bool:
        """Check if entry is an arXiv preprint."""

    def is_official_publication(self, fetched_metadata, bib_entry: BibEntry) -> bool:
        """Validate if fetched metadata represents official publication."""

    def extract_venue_name(self, fetched_metadata) -> str:
        """Extract clean venue name (e.g., 'ACL 2025')."""
```

---

## 5. User Interface Design

### Current UI (Verified Entry)
```
✓ [Entry Key]  [Open paper]
Tags: ✓ Verified | Source: arxiv
```

### New UI (arXiv with Official Version Found)
```
✓ [Entry Key]  [arXiv] [Official: ACL 2025]
Tags: ✓ Verified | ⬆️ Official Version Available | Source: semantic_scholar

Reference (from semantic_scholar):
  Title: BERT: Pre-training of Deep Bidirectional Transformers
  Authors: Jacob Devlin, Ming-Wei Chang, Kenton Lee, Kristina Toutanova
  Year: 2019
  Venue: NAACL 2019
  DOI: 10.18653/v1/N19-1423
```

### UI Elements

**1. Dual Button Layout**
- `[arXiv]` button - Gray background, links to arxiv.org
- `[Official: {venue}]` button - Blue background (prominent), links to official venue
- Both buttons side-by-side in header

**2. New Tag**
- `⬆️ Official Version Available` - Orange/blue color
- Indicates user should consider using official citation

**3. Reference Section**
- Shows official metadata (venue, year, DOI)
- This is what user will find when clicking official link

### User Workflow
1. User clicks `[Official: ACL 2025]` button
2. Browser opens official venue page (e.g., https://aclanthology.org/2025.acl-long.272/)
3. User clicks "Cite" button on venue website
4. Popup/modal appears with BibTeX
5. User copies official BibTeX
6. User replaces arXiv entry in their .bib file

**Rationale:** Many academic websites (ACL Anthology, ACM, IEEE, CVF) use JavaScript modals for citations. The URL doesn't change, making automated fetching difficult without browser automation (which would break $0 cost goal). Manual copy is pragmatic and reliable.

---

## 6. Edge Cases & Handling

### Case 1: arXiv Paper Not Yet Published
- **Scenario:** Paper still under review or recently posted
- **Behavior:** Show only `[arXiv]` button (current behavior)
- **Tags:** `✓ Verified | Source: arxiv` (no official version tag)

### Case 2: Multiple Official Versions
- **Scenario:** Conference version + journal extension
- **Behavior:** Choose highest confidence match
- **Priority:** Journal > Conference > Workshop
- **Implementation:** Sort by venue prestige, pick first match

### Case 3: Publication Delay in Databases
- **Scenario:** Paper published but databases haven't indexed yet
- **Behavior:** Shows as arXiv only (no official version found)
- **Acceptable:** Databases update with 1-4 week delay, user can re-check later

### Case 4: False Positive Match
- **Scenario:** Different paper with very similar title
- **Mitigation:** High thresholds (95% title, 70% author overlap)
- **User Verification:** User clicks both links to verify it's the same paper
- **Risk:** Low due to strict matching criteria

### Case 5: Mixed Input (arXiv + Official)
- **Scenario:** User pastes BibTeX with both arXiv preprints and official publications
- **Behavior:**
  - Official publications → Normal verification (no conversion logic)
  - arXiv preprints → Trigger conversion detection
- **Detection Rule:** Check venue field first
  - If venue = "arXiv" or "preprint" → arXiv preprint
  - If venue = real conference/journal → Official publication

### Case 6: Official Entry Mentioning arXiv
- **Scenario:** BibTeX has official venue but `note = {arXiv:2304.12345}`
- **Behavior:** Treat as official publication (no conversion needed)
- **Detection:** Venue field takes precedence over notes/comments

---

## 7. Implementation Breakdown

### Phase 1: Data Model & Detection Logic
**Files:** `src/analyzers/metadata_comparator.py`

1. Add new fields to `ComparisonResult` dataclass
2. Implement `detect_arxiv_entry()` method
3. Implement `is_official_publication()` method
4. Implement `extract_venue_name()` method
5. Update all `compare_with_*()` methods to populate new fields

### Phase 2: Workflow Integration
**Files:** `app.py`

1. Modify `process_single_entry()`:
   - After finding best match, check if original entry is arXiv
   - If arXiv, validate if match is official publication
   - Store both arXiv URL and official URL
2. Update comparison result creation logic

### Phase 3: UI Rendering
**Files:** `app.py`

1. Modify `format_entry_card()`:
   - Check `has_official_version` flag
   - Render dual buttons if true
   - Add "Official Version Available" tag
   - Update reference section to show official venue
2. Update button generation logic in header

### Phase 4: CSS Styling
**Files:** `app.py` - `REPORT_CSS`

1. Add styles for dual-button layout
2. Style official button prominently (blue background)
3. Style arXiv button subtly (gray background)
4. Add styling for new tag type (orange/blue)
5. Ensure responsive layout for mobile

### Phase 5: Testing
1. Test with pure arXiv entries
2. Test with pure official entries
3. Test with mixed entries
4. Test edge cases (not published, false positives, etc.)
5. Test UI on different screen sizes

---

## 8. Known Venue Patterns

### Top-tier AI/ML/CS Conferences
- NeurIPS, ICML, ICLR, AAAI, IJCAI
- ACL, EMNLP, NAACL, EACL, COLING
- CVPR, ICCV, ECCV, SIGGRAPH
- SIGIR, KDD, WWW, WSDM
- ICSE, FSE, ASE, ISSTA

### Top-tier Journals
- JMLR, PAMI, IJCV, TACL
- CACM, TOCS, TODS, TKDE

### Venue Name Variations
- Handle abbreviations: "ICLR" vs "International Conference on Learning Representations"
- Handle year formats: "ACL 2025" vs "ACL'25" vs "Proceedings of ACL 2025"
- Normalize for comparison

---

## 9. Success Metrics

### Functional Metrics
- **Detection Accuracy:** >95% of arXiv entries correctly identified
- **Match Accuracy:** >90% of official versions correctly matched
- **False Positive Rate:** <5% incorrect matches

### User Experience Metrics
- **Conversion Rate:** % of users who click official links
- **Time Saved:** Estimated 2-5 minutes per converted citation
- **User Satisfaction:** Qualitative feedback on feature usefulness

### Technical Metrics
- **API Cost:** $0 (using existing free APIs)
- **Performance:** <500ms additional processing per entry
- **Reliability:** No new external dependencies

---

## 10. Future Enhancements (Out of Scope)

### Potential Extensions
1. **One-click BibTeX replacement** - Fetch official BibTeX directly (requires browser automation or venue-specific parsers)
2. **Batch export** - Export all official versions as a new .bib file
3. **bioRxiv support** - Extend to biology/medical preprints
4. **Preprint quality scoring** - Flag papers that should be updated to official versions
5. **Citation style conversion** - Convert between BibTeX, BibLaTeX, EndNote, etc.

### Why Not Now
- Maintain focus on core arXiv→Official conversion
- Keep $0 maintenance cost constraint
- Avoid scope creep during initial implementation

---

## 11. Risks & Mitigations

### Risk 1: API Rate Limits
- **Impact:** Semantic Scholar, CrossRef have rate limits
- **Mitigation:** Already handled in existing fetchers with delays/retries
- **Status:** Low risk (existing system already manages this)

### Risk 2: Database Coverage Gaps
- **Impact:** Some papers not indexed in any database
- **Mitigation:** Use multiple databases (Semantic Scholar, CrossRef, DBLP, OpenAlex)
- **Status:** Acceptable (user can manually verify)

### Risk 3: Venue Website Changes
- **Impact:** Official venue websites change their "Cite" button UI
- **Mitigation:** We only provide links, not scraping - user handles the rest
- **Status:** Low risk (our system is decoupled from venue UI)

### Risk 4: False Matches
- **Impact:** Suggest wrong official version
- **Mitigation:** High similarity thresholds + user verification via dual links
- **Status:** Low risk (strict matching criteria)

---

## 12. Summary

### What Changes
- **From:** BibTeX verification tool
- **To:** Smart bibliography management system with arXiv→Official conversion

### Key Innovation
- Automatic detection of arXiv preprints with official publications
- Dual-link UI for easy access to both versions
- Zero maintenance cost using existing free APIs

### User Value
- Save 2-5 minutes per citation conversion
- Reduce errors in bibliography management
- Improve citation quality for paper submissions

### Technical Approach
- Extend existing verification workflow
- Add detection logic for arXiv entries
- Enhance UI with dual buttons and tags
- Maintain $0 cost constraint

---

**Next Steps:**
1. Review and approve this design
2. Set up git worktree for isolated development
3. Create detailed implementation plan
4. Begin Phase 1 implementation
