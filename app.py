#!/usr/bin/env python3
from tkinter.constants import TRUE
import base64
import gradio as gr
import tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from src.parsers import BibParser
from src.fetchers import ArxivFetcher, ScholarFetcher, CrossRefFetcher, SemanticScholarFetcher, OpenAlexFetcher, DBLPFetcher
from src.analyzers import MetadataComparator, DuplicateDetector
from src.report.generator import EntryReport
from src.config.workflow import get_default_workflow


def format_entry_card(entry_report, duplicate_groups=None):
    """格式化单个文献条目为 HTML 卡片"""
    entry = entry_report.entry
    comparison = entry_report.comparison

    # 判断状态
    if comparison and comparison.is_match:
        card_class = "verified"
        status_icon = "✓"
        status_text = "Verified"
    elif comparison and comparison.has_issues:
        card_class = "warning"
        status_icon = "⚠️"
        status_text = "Issues Found"
    else:
        card_class = "error"
        status_icon = "✗"
        status_text = "Not Found"

    # 格式化 BibTeX（BibEntry 用 raw_entry 存原始字段）
    bibtex_str = f"@{entry.entry_type}{{{entry.key},\n"
    for field, value in (entry.raw_entry or {}).items():
        if field in ("ID", "ENTRYTYPE"):
            continue
        if value is not None and str(value).strip():
            bibtex_str += f"  {field}={{{value}}},\n"
    bibtex_str = bibtex_str.rstrip(",\n") + "\n}"

    # Link for header (Open paper / DOI) when we have reference
    link_url = ""
    link_label = "Open paper"
    if comparison and getattr(comparison, "source", "") != "unable":
        if getattr(comparison, "fetched_doi", None) and str(comparison.fetched_doi).strip():
            link_url = "https://doi.org/" + str(comparison.fetched_doi).strip()
            link_label = "DOI"
        elif getattr(comparison, "fetched_url", None) and str(comparison.fetched_url).strip():
            link_url = str(comparison.fetched_url).strip()

    # 收集标签
    tags = []
    if comparison:
        if comparison.is_match:
            tags.append(('<span class="tag success">✓ Verified</span>', 0))
        if comparison.source:
            tags.append((f'<span class="tag info">Source: {comparison.source}</span>', 0))

        # 问题标签（ComparisonResult 使用 *_match，用 not *_match 表示 mismatch）
        if not comparison.title_match:
            tags.append(('<span class="tag warning">⚠️ Title Mismatch</span>', 1))
        if not comparison.author_match:
            tags.append(('<span class="tag warning">⚠️ Author Mismatch</span>', 1))
        if not comparison.year_match:
            tags.append(('<span class="tag warning">⚠️ Year Mismatch</span>', 1))
        if hasattr(comparison, 'venue_match') and not comparison.venue_match:
            tags.append(('<span class="tag warning">⚠️ Venue Mismatch</span>', 1))
        if not comparison.is_match and not comparison.has_issues:
            tags.append(('<span class="tag error">✗ Not Found</span>', 2))

    # 检查是否是重复条目
    if duplicate_groups:
        for group in duplicate_groups:
            if entry.key in group.entry_keys:
                tags.append(('<span class="tag warning">⚠️ Duplicate Entry</span>', 1))
                break

    # 按优先级排序标签
    tags.sort(key=lambda x: x[1])
    tags_html = '\n'.join([tag[0] for tag in tags])

    # 详细信息
    metadata_info = ""
    if comparison:
        if comparison.is_match:
            confidence = getattr(comparison, 'confidence', 0)
            metadata_info = f"<strong>Verification Info:</strong> All fields matched successfully | Confidence: {confidence * 100:.2f}%"
        elif comparison.has_issues:
            issues = []
            if not comparison.title_match:
                issues.append("• Title mismatch detected")
            if not comparison.author_match:
                issues.append("• Author list differs from database")
            if not comparison.year_match:
                issues.append("• Publication year mismatch")
            if hasattr(comparison, 'venue_match') and not comparison.venue_match:
                issues.append("• Venue/journal name differs")
            metadata_info = f"<strong>Issue Details:</strong><br>" + "<br>".join(issues)
        else:
            metadata_info = f"""<strong>Issue Details:</strong><br>
• Entry not found in any database<br>
• Possible causes: incorrect title, author errors, or non-existent reference<br>
• Suggestion: verify the original source or use a search engine"""

    # Ground truth (reference): compact title, author, year, doi only (no Copy, no full BibTeX)
    fetched_bibtex_html = ""
    if comparison and getattr(comparison, "source", "") != "unable" and (
        getattr(comparison, "fetched_title", None) or getattr(comparison, "fetched_authors", None)
    ):
        src = getattr(comparison, "source", "reference")
        fa = getattr(comparison, "fetched_authors", None)
        authors_str = " and ".join(fa) if isinstance(fa, list) else (fa or "")
        ft = (getattr(comparison, "fetched_title", None) or "").strip()
        fy = (getattr(comparison, "fetched_year", None) or "").strip()
        fdoi = (getattr(comparison, "fetched_doi", None) or "").strip()

        def _line(label, value):
            if not value:
                return ""
            esc = (value or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            return f'<div style="margin: 0.15em 0; font-size: 0.9em;"><strong>{label}:</strong> {esc}</div>'

        rows = []
        if ft:
            rows.append(_line("Title", ft))
        if authors_str:
            rows.append(_line("Authors", authors_str))
        if fy:
            rows.append(_line("Year", fy))
        if fdoi:
            rows.append(_line("DOI", fdoi))
        fetched_bibtex_html = f"""
        <div class="metadata-info" style="margin-top: 0.5em; font-size: 0.95em;">
            <strong>Reference (from {src}):</strong>
            {"".join(rows)}
        </div>"""

    header_link_html = ""
    if link_url:
        header_link_html = (
            f'<a href="{link_url}" target="_blank" rel="noopener" '
            'style="margin-left: auto; padding: 0.35em 0.75em; background: #2563eb; color: white; border-radius: 6px; font-size: 0.9em; font-weight: 500; text-decoration: none;">'
            f'{link_label}</a>'
        )

    html = f"""
    <div class="entry-card {card_class}">
        <div class="entry-header" style="display: flex; align-items: center; gap: 0.5em; flex-wrap: wrap;">
            <span class="status-icon">{status_icon}</span>
            <span class="entry-key">{entry.key}</span>
            {header_link_html}
        </div>
        <div class="bibtex-content">{bibtex_str}</div>
        <div class="tags-container">
            {tags_html}
        </div>
        <div class="metadata-info">
            {metadata_info}
        </div>
        {fetched_bibtex_html}
    </div>
    """
    return html, card_class


def get_card_class(entry_report):
    """Return 'verified' | 'warning' | 'error' for filtering."""
    comparison = entry_report.comparison
    if comparison and comparison.is_match:
        return "verified"
    if comparison and comparison.has_issues:
        return "warning"
    return "error"


FILTER_TO_CLASS = {"Total": None, "Verified": "verified", "Issues Found": "warning", "Not Found": "error"}

# CSS 样式（供 render_results 使用）
REPORT_CSS = """
<style>
    .ci te scan-container { max-width: 1200px; margin: 0 auto; }
    .entry-card { border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px; margin-bottom: 20px; background: white; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    .entry-card.verified { border-left: 4px solid #4caf50; }
    .entry-card.warning { border-left: 4px solid #ff9800; }
    .entry-card.error { border-left: 4px solid #f44336; }
    .entry-header { display: flex; align-items: center; margin-bottom: 15px; }
    .status-icon { font-size: 24px; margin-right: 10px; }
    .entry-key { font-size: 18px; font-weight: bold; color: #333; }
    .bibtex-content { background: #f5f5f5; padding: 15px; border-radius: 4px; font-family: 'Courier New', monospace; font-size: 13px; margin: 15px 0; overflow-x: auto; white-space: pre-wrap; color: #1a1a1a; }
    .tags-container { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 15px; }
    .tag { padding: 6px 12px; border-radius: 16px; font-size: 12px; font-weight: 500; }
    .tag.success { background: #e8f5e9; color: #2e7d32; }
    .tag.warning { background: #fff3e0; color: #e65100; }
    .tag.error { background: #ffebee; color: #c62828; }
    .tag.info { background: #e3f2fd; color: #1565c0; }
    .metadata-info { margin-top: 10px; padding: 10px; background: #fafafa; border-radius: 4px; font-size: 13px; color: #666; }
    .summary-stats { background: #f5f5f5; padding: 20px; border-radius: 8px; margin-bottom: 30px; display: flex; justify-content: space-around; text-align: center; }
    .stat-item { flex: 1; }
    .stat-number { font-size: 32px; font-weight: bold; color: #333; }
    .stat-label { font-size: 14px; color: #666; margin-top: 5px; }
    @media (prefers-color-scheme: dark) {
        .citescan-container { color: #e4e4e7; }
        .entry-card { background: #27272a; border-color: #3f3f46; box-shadow: 0 2px 4px rgba(0,0,0,0.3); }
        .entry-key { color: #fafafa; }
        .bibtex-content { background: #18181b; color: #d4d4d8; }
        .tag.success { background: #166534; color: #bbf7d0; }
        .tag.warning { background: #9a3412; color: #fed7aa; }
        .tag.error { background: #991b1b; color: #fecaca; }
        .tag.info { background: #1e3a8a; color: #bfdbfe; }
        .metadata-info { background: #3f3f46; color: #a1a1aa; }
        .metadata-info strong { color: #e4e4e7; }
        .summary-stats { background: #3f3f46; color: #e4e4e7; }
        .stat-number { color: #fafafa; }
        .stat-label { color: #a1a1aa; }
    }
</style>
"""


def render_results(entry_reports, duplicate_groups, filter_choice, include_summary=True):
    """Build HTML for (optionally) summary + filtered cards. include_summary=False when bar is a separate Gradio component."""
    verified_count = warning_count = error_count = 0
    for er in entry_reports:
        c = get_card_class(er)
        if c == "verified":
            verified_count += 1
        elif c == "warning":
            warning_count += 1
        else:
            error_count += 1

    summary_html = ""
    if include_summary:
        summary_html = f"""
    <div class="summary-stats">
        <div class="stat-item"><div class="stat-number" style="color: #4caf50;">{verified_count}</div><div class="stat-label">✓ Verified</div></div>
        <div class="stat-item"><div class="stat-number" style="color: #ff9800;">{warning_count}</div><div class="stat-label">⚠️ Issues Found</div></div>
        <div class="stat-item"><div class="stat-number" style="color: #f44336;">{error_count}</div><div class="stat-label">✗ Not Found</div></div>
        <div class="stat-item"><div class="stat-number">{len(entry_reports)}</div><div class="stat-label">Total</div></div>
    </div>
    """

    want_class = FILTER_TO_CLASS.get(filter_choice)
    if want_class is None:
        filtered = entry_reports
    else:
        filtered = [er for er in entry_reports if get_card_class(er) == want_class]

    cards_html = ""
    for entry_report in filtered:
        card_html, _ = format_entry_card(entry_report, duplicate_groups)
        cards_html += card_html
    if not cards_html:
        cards_html = "<p style='color: #666; margin: 1em 0;'>No entries in this category.</p>"

    return f"{REPORT_CSS}<div class='citescan-container'>{summary_html}{cards_html}</div>"


def filter_display(state, filter_choice):
    """Re-render results with filter. state = (entry_reports, duplicate_groups) or None."""
    if state is None:
        return "<p style='color: #666;'>Please run Verify first.</p>"
    entry_reports, duplicate_groups = state
    return render_results(entry_reports, duplicate_groups, filter_choice, include_summary=False)


# Bar 单段 HTML（大数字 + 小标签），配色与图片一致
def _bar_segment_html(num, label, num_color):
    return f'<div class="bar-seg"><span class="bar-num" style="color:{num_color}">{num}</span><span class="bar-label">{label}</span></div>'


def bar_segments_html(verified_count, warning_count, error_count, total):
    """返回 4 段 (Verified, Issues Found, Not Found, Total) 的 HTML，用于图片式 bar。"""
    return (
        _bar_segment_html(verified_count, "✓ Verified", "#32CD32"),
        _bar_segment_html(warning_count, "⚠️ Issues Found", "#FFA500"),
        _bar_segment_html(error_count, "✗ Not Found", "#FF0000"),
        _bar_segment_html(total, "Total", "#ffffff"),
    )


def process_bibtex(bibtex_input, progress=gr.Progress()):
    """处理用户输入的 BibTeX 并进行检测。返回 (html, state, seg1, seg2, seg3, seg4) 供 bar 展示与筛选。"""
    zero_segs = bar_segments_html(0, 0, 0, 0)
    if not bibtex_input.strip():
        return "<p style='color: red;'>Please enter BibTeX content</p>", None, *zero_segs

    try:
        # 解析 BibTeX
        progress(0, desc="Parsing BibTeX...")
        parser = BibParser()

        # 写入临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.bib', delete=False) as f:
            f.write(bibtex_input)
            temp_bib_path = f.name

        entries = parser.parse_file(temp_bib_path)
        Path(temp_bib_path).unlink()  # 删除临时文件

        if not entries:
            return "<p style='color: red;'>No valid BibTeX entries found</p>", None, *bar_segments_html(0, 0, 0, 0)

        # 初始化检测器
        progress(0.1, desc="Initializing fetchers...")
        arxiv_fetcher = ArxivFetcher()
        crossref_fetcher = CrossRefFetcher()
        scholar_fetcher = ScholarFetcher()
        semantic_scholar_fetcher = SemanticScholarFetcher()
        openalex_fetcher = OpenAlexFetcher()
        dblp_fetcher = DBLPFetcher()
        comparator = MetadataComparator()
        duplicate_detector = DuplicateDetector()

        # 检测重复
        duplicate_groups = duplicate_detector.find_duplicates(entries)

        # 获取工作流
        workflow_config = get_default_workflow()

        # 处理每个条目
        entry_reports = []
        progress_lock = threading.Lock()
        verified_count = 0
        warning_count = 0
        error_count = 0

        def process_single_entry(entry, idx, total):
            from src.utils.normalizer import TextNormalizer

            comparison_result = None
            all_results = []

            for step in workflow_config.get_enabled_steps():
                result = None
                if step.name == "arxiv_id" and entry.has_arxiv and arxiv_fetcher:
                    arxiv_meta = arxiv_fetcher.fetch_by_id(entry.arxiv_id)
                    if arxiv_meta:
                        result = comparator.compare_with_arxiv(entry, arxiv_meta)
                elif step.name == "crossref_doi" and entry.doi and crossref_fetcher:
                    crossref_result = crossref_fetcher.search_by_doi(entry.doi)
                    if crossref_result:
                        result = comparator.compare_with_crossref(entry, crossref_result)
                elif step.name == "semantic_scholar" and entry.title and semantic_scholar_fetcher:
                    ss_result = semantic_scholar_fetcher.fetch_by_doi(entry.doi) if entry.doi else None
                    if not ss_result:
                        ss_result = semantic_scholar_fetcher.search_by_title(entry.title)
                    if ss_result:
                        result = comparator.compare_with_semantic_scholar(entry, ss_result)
                elif step.name == "dblp" and entry.title and dblp_fetcher:
                    dblp_result = dblp_fetcher.search_by_title(entry.title)
                    if dblp_result:
                        result = comparator.compare_with_dblp(entry, dblp_result)
                elif step.name == "openalex" and entry.title and openalex_fetcher:
                    oa_result = openalex_fetcher.fetch_by_doi(entry.doi) if entry.doi else None
                    if not oa_result:
                        oa_result = openalex_fetcher.search_by_title(entry.title)
                    if oa_result:
                        result = comparator.compare_with_openalex(entry, oa_result)
                elif step.name == "arxiv_title" and entry.title and arxiv_fetcher:
                    results = arxiv_fetcher.search_by_title(entry.title, max_results=3)
                    if results:
                        best_result = None
                        best_sim = 0.0
                        norm1 = TextNormalizer.normalize_for_comparison(entry.title)
                        for r in results:
                            sim = TextNormalizer.similarity_ratio(norm1, TextNormalizer.normalize_for_comparison(r.title))
                            if sim > best_sim:
                                best_sim, best_result = sim, r
                        if best_result and best_sim > 0.5:
                            result = comparator.compare_with_arxiv(entry, best_result)
                elif step.name == "crossref_title" and entry.title and crossref_fetcher:
                    crossref_result = crossref_fetcher.search_by_title(entry.title)
                    if crossref_result:
                        result = comparator.compare_with_crossref(entry, crossref_result)
                elif step.name == "google_scholar" and entry.title and scholar_fetcher:
                    scholar_result = scholar_fetcher.search_by_title(entry.title)
                    if scholar_result:
                        result = comparator.compare_with_scholar(entry, scholar_result)

                if result:
                    all_results.append(result)
                    if result.is_match:
                        comparison_result = result
                        break

            if not comparison_result and all_results:
                all_results.sort(key=lambda r: r.confidence, reverse=True)
                comparison_result = all_results[0]
            elif not comparison_result:
                comparison_result = comparator.create_unable_result(entry, "Unable to find this paper in any data source")

            return EntryReport(entry=entry, comparison=comparison_result)

        max_workers = min(10, len(entries))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_entry = {executor.submit(process_single_entry, e, i, len(entries)): (e, i) for i, e in enumerate(entries)}

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

                        progress((idx + 1) / len(entries), desc=f"Verifying entries {idx + 1}/{len(entries)}...")
                except Exception as e:
                    with progress_lock:
                        error_count += 1
                        print(f"Error processing {entry.key}: {e}")

        # 生成 HTML（默认 Total 视图，不含 bar），并保存结果供分类筛选
        progress(1.0, desc="Generating report...")
        final_html = render_results(entry_reports, duplicate_groups, "Total", include_summary=False)
        segs = bar_segments_html(verified_count, warning_count, error_count, len(entry_reports))
        return final_html, (entry_reports, duplicate_groups), *segs

    except Exception as e:
        import traceback
        error_msg = f"<p style='color: red;'>Error: {str(e)}</p><pre>{traceback.format_exc()}</pre>"
        return error_msg, None, *bar_segments_html(0, 0, 0, 0)


# 官网示例：点击即可填入输入框进行测试
BIBTEX_EXAMPLES = [
    (
        """@article{gpt2,
  title={Language models are unsupervised multitask},
  author={Radford, Alec and Child, Rewon and Luan, David and Amodei, Dario and Sutskever, Ilya and others},
  journal={OpenAI blog},
  volume={1},
  number={8},
  pages={9},
  year={2021}
}""",
        "GPT-2 (OpenAI blog)",
    ),
    (
        """@article{devlin2018bert,
  year={2018},
  journal={arXiv preprint arXiv:1810.04805},
  author={Devlin, Jacob and Chang, Ming-Wei and Lee, Kenton and Toutanova, Kristina},
  title={BERT: Pre-training of deep bidirectional transformers for language understanding}
}""",
        "BERT (arXiv)",
    ),
    (
        """@article{vaswani2017attention,
  title={Attention is all you need},
  author={Vaswani, Ashish and Shazeer, Noam and others},
  journal={Advances in neural information processing systems},
  year={2017}
}

@article{brown2020language,
  title={Language models are few-shot learners},
  author={Brown, Tom B and Mann, Benjamin and others},
  year={2020}
}""",
        "Attention + GPT-3 (multiple entries)",
    ),
]

# Bar 图片式 UI：深灰背景 #2E3035，大数字 + 小标签，绿/橙/红/白
BAR_CSS = """
.status-bar-row { background: #2E3035 !important; border-radius: 8px !important; padding: 20px !important; margin-bottom: 20px !important; display: flex !important; justify-content: space-around !important; align-items: stretch !important; gap: 12px !important; }
.bar-segment-col { flex: 1 !important; text-align: center !important; position: relative !important; min-width: 0 !important; }
.bar-segment-col .bar-seg { display: flex !important; flex-direction: column !important; align-items: center !important; justify-content: center !important; padding: 8px 4px !important; }
.bar-segment-col .bar-num { font-size: 32px !important; font-weight: bold !important; line-height: 1.2 !important; display: block !important; }
.bar-segment-col .bar-label { font-size: 13px !important; color: #ffffff !important; margin-top: 4px !important; display: block !important; }
.bar-segment-btn { position: absolute !important; top: 0 !important; left: 0 !important; right: 0 !important; bottom: 0 !important; opacity: 0 !important; cursor: pointer !important; }
"""

# 创建 Gradio 界面
with gr.Blocks(title="CiteScan - Check References, Confirm Truth.", theme=gr.themes.Soft(), css=BAR_CSS) as demo:
    gr.Markdown("""
    # CiteScan - Check References, Confirm Truth.

    1️⃣ Paste your BibTeX below, or **click an example** to load it.

    2️⃣ Click "Verify" button to have the system verify the authenticity and accuracy of each reference.
    
    **Important: We check very carefully. Sometimes the result might look different from Google Scholar or ArXiv. We think it's best to use the official version from places like ACM, ACL, or CVF to cite your sources.

    We will also add a feature soon to help change citations from pre-print versions (like arXiv or bioRxiv) into the final official ones (like from NeurIPS, ACL, or CVF).**
    """)

    with gr.Row():
        with gr.Column():
            bibtex_input = gr.Textbox(
                label="📝 Paste your BibTeX",
                placeholder="""Paste your BibTeX or click an example below. for example: 
@article{gpt2,
  title={Language models are unsupervised multitask},
  author={Radford, Alec and Child, Rewon and Luan, David and Amodei, Dario and Sutskever, Ilya and others},
  journal={OpenAI blog},
  volume={1},
  number={8},
  pages={9},
  year={2021}
}

@article{devlin2018bert,
  year={2018},
  journal={arXiv preprint arXiv:1810.04805},
  author={Devlin, Jacob and Chang, Ming-Wei and Lee, Kenton and Toutanova, Kristina},
  title={BERT: Pre-training of deep bidirectional transformers for language understanding}
}
""",
                lines=15,
                max_lines=20
            )

            submit_btn = gr.Button("🚀 Verify", variant="primary", size="lg")

            gr.Examples(
                examples=[[ex[0]] for ex in BIBTEX_EXAMPLES],
                inputs=[bibtex_input],
                label="📋 Examples (click to load)",
                examples_per_page=6,
            )

    result_state = gr.State(value=None)

    # Bar：图片式 UI（深灰 #2E3035，大数字 + 小标签），每段可点击筛选
    zero_segs = bar_segments_html(0, 0, 0, 0)
    with gr.Row(elem_classes=["status-bar-row"]):
        with gr.Column(elem_classes=["bar-segment-col"], scale=1):
            bar_seg_verified = gr.HTML(zero_segs[0])
            btn_verified = gr.Button("Verified", elem_classes=["bar-segment-btn"], visible=True)
        with gr.Column(elem_classes=["bar-segment-col"], scale=1):
            bar_seg_issues = gr.HTML(zero_segs[1])
            btn_issues = gr.Button("Issues", elem_classes=["bar-segment-btn"], visible=True)
        with gr.Column(elem_classes=["bar-segment-col"], scale=1):
            bar_seg_notfound = gr.HTML(zero_segs[2])
            btn_notfound = gr.Button("Not Found", elem_classes=["bar-segment-btn"], visible=True)
        with gr.Column(elem_classes=["bar-segment-col"], scale=1):
            bar_seg_total = gr.HTML(zero_segs[3])
            btn_total = gr.Button("Total", elem_classes=["bar-segment-btn"], visible=True)

    with gr.Row():
        output_html = gr.HTML(label="Detection Results")

    submit_btn.click(
        fn=process_bibtex,
        inputs=[bibtex_input],
        outputs=[output_html, result_state, bar_seg_verified, bar_seg_issues, bar_seg_notfound, bar_seg_total],
    )

    def filter_to_verified(state):
        return filter_display(state, "Verified")

    def filter_to_issues(state):
        return filter_display(state, "Issues Found")

    def filter_to_notfound(state):
        return filter_display(state, "Not Found")

    def filter_to_total(state):
        return filter_display(state, "Total")

    btn_verified.click(fn=filter_to_verified, inputs=[result_state], outputs=[output_html])
    btn_issues.click(fn=filter_to_issues, inputs=[result_state], outputs=[output_html])
    btn_notfound.click(fn=filter_to_notfound, inputs=[result_state], outputs=[output_html])
    btn_total.click(fn=filter_to_total, inputs=[result_state], outputs=[output_html])

    gr.Markdown("""
*False positive cases* occur for CiteScan:

1.  **Authors Mismatch**:
    - *Reason*: Different databases deal with a longer list of  authors with different strategies, like truncation.
    - *Action*: Verify if main authors match

2.  **Venues Mismatch**:
    - *Reason*: Abbreviations vs. full names, such as "ICLR" v.s. "International Conference on Learning Representations"
    - *Action*: Both are correct.

3.  **Year GAP (±1 Year)**:
    - *Reason*: Delay between preprint (arXiv) and final version publication 
    - *Action*: Verify which version you intend to cite, We recommend you to cite the version from the official press website. Lower pre-print version bib will make your submission more confidence. 

4.  **Non-academic Sources**:
    - *Reason*: Blogs, and APIs are not indexed in academic databases.
    - *Action*: Verify URL, year, and title manually.
---
**Supported Data Sources:** arXiv, CrossRef, DBLP, Semantic Scholar, ACL Anthology, ACM, theCVF,
    """)

    # Partner logos and contact (embed images as base64 so they work when served)
    _root = Path(__file__).resolve().parent
    def _logo_b64(path: Path) -> str | None:
        if path.exists():
            return base64.b64encode(path.read_bytes()).decode("utf-8")
        return None
    _nus = _logo_b64(_root / "assets" / "logo_nus.png")
    _sjtu = _logo_b64(_root / "assets" / "logo_sjtu.png")
    _logos_html = []
    if _nus:
        _logos_html.append(f'<img src="data:image/png;base64,{_nus}" alt="NUS" style="height:72px; margin-right:24px; vertical-align:middle; display:inline-block;" />')
    if _sjtu:
        _logos_html.append(f'<img src="data:image/png;base64,{_sjtu}" alt="Shanghai Jiao Tong University" style="height:72px; vertical-align:middle; display:inline-block;" />')
    gr.HTML(f"""
    <div style="margin-top:12px;">
      <p><strong>Cooperations</strong></p>
      <p style="display:flex; align-items:center; gap:24px; flex-wrap:nowrap;">{" ".join(_logos_html)}</p>
      <p><strong> Feel free to reach out me by Email</strong> <a href="mailto:e1143641@u.nus.edu">e1143641@u.nus.edu</a></p>
    </div>
    """)

if __name__ == "__main__":
    demo.launch(
        share=False, # To create a public link, set `share=True`
        server_name="0.0.0.0", 
        server_port=7860
    )
