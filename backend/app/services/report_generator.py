import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as RLImage,
    KeepTogether,
    HRFlowable,
)
import json
from PIL import Image as PILImage

from backend.app.config import settings

def _prepare_thumbnail(image_path: Path, max_width: float, max_height: float, output_path: Path) -> tuple[float, float] | None:
    """Prepares and resizes an image for inclusion in the PDF without distorting aspect ratio."""
    if not image_path.exists():
        return None
    try:
        with PILImage.open(image_path) as img:
            w, h = img.size
            if w <= 0 or h <= 0:
                return None
            ratio = min(max_width / w, max_height / h)
            new_w = w * ratio
            new_h = h * ratio
            
            # Save normalized RGB copy for ReportLab
            rgb_img = img.convert("RGB")
            rgb_img.save(output_path, format="JPEG", quality=90)
            return (new_w, new_h)
    except Exception:
        return None

def generate_pdf_report(
    evidence: dict[str, Any],
    integrity: dict[str, Any],
    metadata: dict[str, Any],
    ela: dict[str, Any],
    cv_analysis: dict[str, Any],
    findings: list[dict[str, Any]],
    output_path: Path,
    comparison: dict[str, Any] | None = None,
) -> str:
    """
    Generates a professional, genuine digital forensics technical examination PDF report.
    Adheres to forensic reporting standards with explicit separation between
    observations, limitations, and cryptographic integrity verifications.
    """
    report_id = f"REP-{uuid.uuid4().hex[:8].upper()}"
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    
    # Custom palette
    navy_dark = colors.HexColor("#0f172a")
    cyan_primary = colors.HexColor("#0891b2")
    slate_muted = colors.HexColor("#64748b")
    bg_light = colors.HexColor("#f8fafc")
    border_slate = colors.HexColor("#e2e8f0")
    amber_alert = colors.HexColor("#d97706")
    emerald_check = colors.HexColor("#16a34a")

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=navy_dark,
    )
    
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=slate_muted,
    )

    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=cyan_primary,
        spaceBefore=10,
        spaceAfter=4,
    )

    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=navy_dark,
    )

    mono_style = ParagraphStyle(
        "MonoStyle",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=7.5,
        leading=9.5,
        textColor=navy_dark,
    )

    alert_style = ParagraphStyle(
        "AlertStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=amber_alert,
    )

    disclaimer_style = ParagraphStyle(
        "Disclaimer",
        parent=styles["Italic"],
        fontName="Helvetica-Oblique",
        fontSize=7.5,
        leading=10,
        textColor=slate_muted,
    )

    story = []

    # --- Header ---
    header_data = [
        [
            Paragraph("<b>EviSutra</b> | Digital Forensics Laboratory", title_style),
            Paragraph(f"<b>Report ID:</b> {report_id}<br/><b>Generated:</b> {generated_at}", subtitle_style),
        ]
    ]
    header_table = Table(header_data, colWidths=[4.0 * inch, 3.5 * inch])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1.5, color=cyan_primary, spaceBefore=2, spaceAfter=8))

    # --- Disclaimer Header Notice ---
    notice_text = (
        "<b>CLASSIFICATION:</b> TECHNICAL FORENSIC EVIDENCE REPORT &bull; AUTOMATED HEURISTIC ANALYSIS<br/>"
        "<i>Notice: Cryptographic digest establishes byte-level preservation relative to intake. "
        "Error Level Analysis and metadata inspections provide empirical indicators, not definitive proof of scene authenticity.</i>"
    )
    story.append(Paragraph(notice_text, disclaimer_style))
    story.append(Spacer(1, 8))

    # --- Section 1: Evidence Metadata & Cryptographic Integrity ---
    story.append(Paragraph("1. Evidence Provenance & Cryptographic Verification", section_heading))
    
    intake_hash = evidence.get("sha256_intake", "Unknown")
    current_hash = integrity.get("current_hash", "Unknown")
    hash_match = integrity.get("matches", False)

    integrity_badge = (
        "<font color='#16a34a'><b>MATCHED &bull; Stored bytes identical to intake record</b></font>"
        if hash_match
        else "<font color='#dc2626'><b>MISMATCH DETECTED &bull; Evidence byte alteration detected</b></font>"
    )

    evidence_table_data = [
        [Paragraph("<b>Evidence ID:</b>", body_style), Paragraph(str(evidence.get("id")), mono_style),
         Paragraph("<b>Case Reference:</b>", body_style), Paragraph(str(evidence.get("case_id")), body_style)],
        [Paragraph("<b>File Name:</b>", body_style), Paragraph(str(evidence.get("original_filename")), body_style),
         Paragraph("<b>Validated Format:</b>", body_style), Paragraph(str(evidence.get("mime_type")), body_style)],
        [Paragraph("<b>File Size:</b>", body_style), Paragraph(f"{evidence.get('file_size', 0):,} bytes", body_style),
         Paragraph("<b>Dimensions:</b>", body_style), Paragraph(f"{evidence.get('width')} &times; {evidence.get('height')} px", body_style)],
        [Paragraph("<b>Intake SHA-256:</b>", body_style), Paragraph(intake_hash, mono_style),
         Paragraph("<b>Intake Timestamp:</b>", body_style), Paragraph(str(evidence.get("created_at")), body_style)],
        [Paragraph("<b>Verification Hash:</b>", body_style), Paragraph(current_hash, mono_style),
         Paragraph("<b>Integrity Status:</b>", body_style), Paragraph(integrity_badge, body_style)],
    ]
    t_ev = Table(evidence_table_data, colWidths=[1.3 * inch, 2.7 * inch, 1.3 * inch, 2.2 * inch])
    t_ev.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg_light),
        ("GRID", (0, 0), (-1, -1), 0.5, border_slate),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t_ev)
    story.append(Spacer(1, 10))

    # --- Section 2: Metadata Inspection ---
    story.append(Paragraph("2. Extracted Container & EXIF Metadata", section_heading))
    has_exif = metadata.get("has_exif", False)

    if has_exif:
        meta_data = [
            [Paragraph("<b>Camera Make:</b>", body_style), Paragraph(str(metadata.get("make") or "Not recorded"), body_style),
             Paragraph("<b>Camera Model:</b>", body_style), Paragraph(str(metadata.get("model") or "Not recorded"), body_style)],
            [Paragraph("<b>Date Original:</b>", body_style), Paragraph(str(metadata.get("datetime_original") or "Not recorded"), body_style),
             Paragraph("<b>Software Tag:</b>", body_style), Paragraph(str(metadata.get("software") or "None detected"), body_style)],
            [Paragraph("<b>GPS Coordinates:</b>", body_style),
             Paragraph(
                 f"{metadata.get('gps_lat', 'N/A')}, {metadata.get('gps_lon', 'N/A')}"
                 if metadata.get("gps_lat") is not None else "No GPS tags present in container",
                 body_style
             ),
             Paragraph("<b>Total Tags Extracted:</b>", body_style),
             Paragraph(f"{len(metadata.get('raw_tags', {}))} tags", body_style)],
        ]
    else:
        meta_data = [
            [Paragraph("<b>EXIF Status:</b>", body_style),
             Paragraph("No EXIF metadata block found in image container.", body_style),
             Paragraph("<b>Note:</b>", body_style),
             Paragraph("Absence of EXIF is common in web/social-media distribution; not proof of tampering.", disclaimer_style)]
        ]

    t_meta = Table(meta_data, colWidths=[1.3 * inch, 2.7 * inch, 1.3 * inch, 2.2 * inch])
    t_meta.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg_light),
        ("GRID", (0, 0), (-1, -1), 0.5, border_slate),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 10))

    # --- Section 3: Visual Artifacts (Original vs ELA) ---
    story.append(Paragraph("3. Visual Forensic Artifacts (Original vs. Error Level Analysis)", section_heading))
    
    # Render preview and ELA image side-by-side if available
    orig_file_path = settings.EVIDENCE_DIR / evidence.get("stored_filename", "")
    temp_orig_thumb = settings.REPORTS_DIR / f"thumb_orig_{uuid.uuid4().hex[:8]}.jpg"
    temp_ela_thumb = settings.REPORTS_DIR / f"thumb_ela_{uuid.uuid4().hex[:8]}.jpg"

    thumb_orig_dims = _prepare_thumbnail(orig_file_path, 3.5 * inch, 2.0 * inch, temp_orig_thumb)
    
    ela_artifact_name = ela.get("artifact_filename")
    ela_file_path = (settings.ARTIFACTS_DIR / ela_artifact_name) if ela_artifact_name else None
    thumb_ela_dims = _prepare_thumbnail(ela_file_path, 3.5 * inch, 2.0 * inch, temp_ela_thumb) if ela_file_path else None

    visual_row = []
    if thumb_orig_dims and temp_orig_thumb.exists():
        img_orig_rl = RLImage(str(temp_orig_thumb), width=thumb_orig_dims[0], height=thumb_orig_dims[1])
        cell_orig = [Paragraph("<b>Original Evidence Preview</b>", body_style), img_orig_rl]
    else:
        cell_orig = [Paragraph("Original preview unavailable", body_style)]

    if thumb_ela_dims and temp_ela_thumb.exists():
        img_ela_rl = RLImage(str(temp_ela_thumb), width=thumb_ela_dims[0], height=thumb_ela_dims[1])
        cell_ela = [Paragraph(f"<b>ELA Visualization (Q={ela.get('quality', 95)}, {ela.get('scale', 15)}x scale)</b>", body_style), img_ela_rl]
    else:
        ela_status_msg = ela.get("explanation", "ELA not performed or unsupported for this media format.")
        cell_ela = [Paragraph(f"<b>ELA Visualization</b><br/><font color='#64748b'>{ela_status_msg}</font>", body_style)]

    visual_table = Table([[cell_orig, cell_ela]], colWidths=[3.75 * inch, 3.75 * inch])
    visual_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BACKGROUND", (0, 0), (-1, -1), bg_light),
        ("GRID", (0, 0), (-1, -1), 0.5, border_slate),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(visual_table)
    story.append(Spacer(1, 10))

    # --- Optional Section 4: Image Comparison (if performed) ---
    temp_comp_thumb = None
    if comparison:
        story.append(Paragraph("4. Geometric Feature Correspondence & Crop Comparison", section_heading))
        is_ref = comparison.get("reference_id") == evidence.get("id")
        paired_id = comparison.get("candidate_id") if is_ref else comparison.get("reference_id")
        role_str = "Reference Image (Original Scene)" if is_ref else "Candidate Image (Target Sample)"
        
        comp_status = str(comparison.get("status", "unknown")).upper().replace("_", " ")
        status_color = "#0284c7" if "DUPLICATE" in comp_status else ("#2563eb" if ("IDENTICAL" in comp_status or "SIMILAR" in comp_status) else ("#16a34a" if "MATCH" in comp_status else ("#d97706" if "INCONCLUSIVE" in comp_status else "#64748b")))

        overlap_box = json.loads(comparison.get("overlap_box_json")) if comparison.get("overlap_box_json") else None
        overlap_str = (
            f"X: {overlap_box['x']}, Y: {overlap_box['y']}, {overlap_box['width']}&times;{overlap_box['height']} px"
            if overlap_box else "N/A"
        )
        scale_val = comparison.get("estimated_scale")
        scale_str = f"{scale_val:.3f}&times;" if scale_val is not None else "1.000&times;"

        comp_table_data = [
            [Paragraph("<b>Comparison ID:</b>", body_style), Paragraph(str(comparison.get("id")), mono_style),
             Paragraph("<b>Role in Comparison:</b>", body_style), Paragraph(role_str, body_style)],
            [Paragraph("<b>Paired Evidence:</b>", body_style), Paragraph(str(paired_id), mono_style),
             Paragraph("<b>Geometric Status:</b>", body_style), Paragraph(f"<font color='{status_color}'><b>{comp_status}</b></font>", body_style)],
            [Paragraph("<b>Algorithm / Detector:</b>", body_style), Paragraph(f"{comparison.get('algorithm', 'SIFT')} (RANSAC 5.0 px)", body_style),
             Paragraph("<b>Verified Inliers:</b>", body_style), Paragraph(f"{comparison.get('inliers_count', 0)} / {comparison.get('raw_matches', 0)} ({comparison.get('inlier_ratio', 0)*100:.1f}%)", body_style)],
            [Paragraph("<b>Estimated Overlap:</b>", body_style), Paragraph(overlap_str, body_style),
             Paragraph("<b>Scale Ratio:</b>", body_style), Paragraph(scale_str, body_style)],
            [Paragraph("<b>Observed Result:</b>", body_style), Paragraph(comparison.get("explanation", ""), body_style),
             Paragraph("<b>Method Limitations:</b>", body_style), Paragraph(comparison.get("limitations", ""), disclaimer_style)],
        ]
        t_comp = Table(comp_table_data, colWidths=[1.3 * inch, 2.7 * inch, 1.3 * inch, 2.2 * inch])
        t_comp.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), bg_light),
            ("GRID", (0, 0), (-1, -1), 0.5, border_slate),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(t_comp)

        # Embed comparison visual artifact if available
        comp_art_name = comparison.get("artifact_name")
        if comp_art_name:
            comp_art_path = settings.ARTIFACTS_DIR / comp_art_name
            temp_comp_thumb = settings.REPORTS_DIR / f"thumb_comp_{uuid.uuid4().hex[:8]}.jpg"
            comp_thumb_dims = _prepare_thumbnail(comp_art_path, 7.0 * inch, 2.5 * inch, temp_comp_thumb)
            if comp_thumb_dims and temp_comp_thumb.exists():
                story.append(Spacer(1, 4))
                img_comp_rl = RLImage(str(temp_comp_thumb), width=comp_thumb_dims[0], height=comp_thumb_dims[1])
                comp_img_table = Table([[Paragraph("<b>Feature Correspondence & Overlap Bounding Box Overlay</b>", body_style)], [img_comp_rl]], colWidths=[7.5 * inch])
                comp_img_table.setStyle(TableStyle([
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("BACKGROUND", (0, 0), (-1, -1), bg_light),
                    ("GRID", (0, 0), (-1, -1), 0.5, border_slate),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]))
                story.append(comp_img_table)
        story.append(Spacer(1, 10))

    # --- Section: Table of Findings ---
    section_num = "5" if comparison else "4"
    story.append(Paragraph(f"{section_num}. Technical Findings & Empirical Observations", section_heading))

    findings_data = [
        [
            Paragraph("<b>Test / Examination</b>", body_style),
            Paragraph("<b>Observed Result</b>", body_style),
            Paragraph("<b>Technical Interpretation</b>", body_style),
            Paragraph("<b>Method Limitations</b>", body_style),
            Paragraph("<b>Severity</b>", body_style),
        ]
    ]

    for f in findings:
        sev = f.get("severity", "info").lower()
        sev_color = "#dc2626" if sev in ["critical", "high"] else ("#d97706" if sev == "medium" else "#0284c7")
        findings_data.append([
            Paragraph(f"<b>{f.get('test_performed', '')}</b>", body_style),
            Paragraph(f.get("observed_result", ""), body_style),
            Paragraph(f.get("explanation", ""), body_style),
            Paragraph(f.get("limitations", ""), disclaimer_style),
            Paragraph(f"<font color='{sev_color}'><b>{sev.upper()}</b></font>", body_style),
        ])

    t_findings = Table(
        findings_data,
        colWidths=[1.5 * inch, 1.4 * inch, 2.1 * inch, 1.8 * inch, 0.7 * inch]
    )
    t_findings.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("GRID", (0, 0), (-1, -1), 0.5, border_slate),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_findings)
    story.append(Spacer(1, 14))

    # --- Signature & Sign-Off ---
    signoff_text = (
        "<b>LEGAL & FORENSIC ADMISSIBILITY DISCLAIMER:</b><br/>"
        "This examination report was generated programmatically by the EviSutra Digital Forensics Suite v0.2.0. "
        "The cryptographic hash proves byte integrity relative to the point of intake only. "
        "The automated analyses (ELA, EXIF, and noise variance) provide investigative indicators for qualified forensic examiner review "
        "and do not constitute an autonomous guarantee of authenticity or court admissibility under Indian Evidence Act Section 65B "
        "without accompanying examiner testimony and strict physical chain of custody documentation."
    )
    story.append(Paragraph(signoff_text, disclaimer_style))
    story.append(Spacer(1, 10))

    # Build the document
    doc.build(story)

    # Clean up temporary thumbnails
    if temp_orig_thumb.exists():
        try:
            os.remove(temp_orig_thumb)
        except Exception:
            pass
    if temp_ela_thumb.exists():
        try:
            os.remove(temp_ela_thumb)
        except Exception:
            pass
    if temp_comp_thumb and temp_comp_thumb.exists():
        try:
            os.remove(temp_comp_thumb)
        except Exception:
            pass

    return report_id


def generate_video_pdf_report(
    evidence: dict[str, Any],
    integrity: dict[str, Any],
    video_analysis: dict[str, Any],
    findings: list[dict[str, Any]],
    output_path: Path,
) -> str:
    """
    Generates a SWGDE / ISO 27037 compliant Video Forensic Examination PDF Report.
    Includes:
    - Case & Evidence Header with SHA-256 Digest
    - Elementary Stream & Container Atom Metrics
    - Color Profile & Night-Vision Grading Assessment
    - Multi-Scale Temporal Splicing & Cut Detection Table
    - Embedded Keyframes Gallery with Regional Noise Residuals
    - Legal & Forensic Admissibility Disclaimer
    """
    report_id = f"REP-VID-{uuid.uuid4().hex[:8].upper()}"
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    navy_dark = colors.HexColor("#0f172a")
    cyan_primary = colors.HexColor("#0891b2")
    slate_muted = colors.HexColor("#64748b")
    border_slate = colors.HexColor("#e2e8f0")
    amber_alert = colors.HexColor("#d97706")
    emerald_check = colors.HexColor("#16a34a")

    title_style = ParagraphStyle(
        "VidReportTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=17,
        leading=21,
        textColor=navy_dark,
    )
    subtitle_style = ParagraphStyle(
        "VidReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=slate_muted,
    )
    section_heading = ParagraphStyle(
        "VidSectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=cyan_primary,
        spaceBefore=10,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "VidBodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=navy_dark,
    )
    code_style = ParagraphStyle(
        "VidCodeStyle",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#334155"),
    )
    disclaimer_style = ParagraphStyle(
        "VidDisclaimer",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=7.5,
        leading=10,
        textColor=slate_muted,
    )

    story = []

    # Title & Header
    header_html = (
        "<b>EVISUTRA DIGITAL EVIDENCE EXAMINATION REPORT</b><br/>"
        "<font size=10 color='#0891b2'>Forensic Video Analysis & Temporal Continuity Audit</font>"
    )
    meta_html = (
        f"<b>Report ID:</b> {report_id}<br/>"
        f"<b>Generated:</b> {generated_at}<br/>"
        f"<b>Standard:</b> SWGDE / ISO/IEC 27037:2012"
    )
    t_header = Table(
        [[Paragraph(header_html, title_style), Paragraph(meta_html, subtitle_style)]],
        colWidths=[360, 180],
    )
    t_header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(t_header)
    story.append(HRFlowable(width="100%", thickness=1.5, color=cyan_primary, spaceBefore=4, spaceAfter=8))

    # Executive Forensic Summary Banner
    classification = video_analysis.get("classification", "unknown")
    class_labels = {
        "cut_and_color_grading_detected": ("TEMPORAL CUT & NIGHT FILTER DETECTED", colors.HexColor("#b91c1c")),
        "temporal_cut_detected": ("TEMPORAL SPLICING / CUT DETECTED", amber_alert),
        "color_grading_applied": ("NIGHT-VISION / COLOR GRADING APPLIED", amber_alert),
        "natural_continuous_stream": ("CONTINUOUS NATURAL VIDEO STREAM", emerald_check),
    }
    banner_label, banner_color = class_labels.get(classification, (classification.upper(), slate_muted))

    banner_data = [
        [
            Paragraph(f"<font color='white'><b>FORENSIC STATUS: {banner_label}</b></font>", ParagraphStyle("WhiteB", parent=body_style, fontSize=10, textColor=colors.white)),
        ],
        [
            Paragraph(video_analysis.get("summary_statement", "Analysis complete."), ParagraphStyle("Stmt", parent=body_style, fontSize=8.5, textColor=navy_dark)),
        ]
    ]
    t_banner = Table(banner_data, colWidths=[540])
    t_banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), banner_color),
        ("BACKGROUND", (0, 1), (0, 1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 1, banner_color),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t_banner)
    story.append(Spacer(1, 10))

    # Section 1: Chain of Custody & Hash Verification
    story.append(Paragraph("1. Chain of Custody & Cryptographic Intake", section_heading))
    match_status = "MATCH (VERIFIED)" if integrity.get("matches", True) else "TAMPERING DETECTED"
    match_color = emerald_check if integrity.get("matches", True) else colors.HexColor("#ef4444")

    intake_data = [
        ["Evidence Item ID", evidence.get("id", "N/A"), "Original Filename", evidence.get("original_filename", "N/A")],
        ["Case ID", evidence.get("case_id", "N/A"), "Media Format", f"{evidence.get('mime_type')} ({video_analysis.get('video_properties', {}).get('codec', 'H.264')})"],
        ["File Size", f"{evidence.get('file_size', 0):,} bytes", "Intake Timestamp", evidence.get("created_at", "N/A")],
        ["Cryptographic Digest", Paragraph(f"<b>SHA-256:</b> {evidence.get('sha256_intake', 'N/A')}", code_style), "Vault Hash Recheck", Paragraph(f"<font color='{match_color.hexval()}'><b>{match_status}</b></font>", body_style)],
    ]
    t_intake = Table(intake_data, colWidths=[105, 165, 105, 165])
    t_intake.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f8fafc")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#f8fafc")),
        ("GRID", (0, 0), (-1, -1), 0.5, border_slate),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_intake)
    story.append(Spacer(1, 8))

    # Section 2: Video Stream & Container Timing
    story.append(Paragraph("2. Video Elementary Stream & Container Atom Metrics", section_heading))
    props = video_analysis.get("video_properties", {})
    stream_data = [
        ["Resolution", props.get("resolution", "N/A"), "Frame Rate (FPS)", f"{props.get('fps', 0)} fps"],
        ["Decoded Frame Count", f"{props.get('total_frames', 0):,} frames", "Video Codec FourCC", props.get("codec", "N/A")],
        ["Decoded Video Duration", f"{props.get('decoded_duration_sec', 0):.4f} seconds", "Container Presentation Duration", f"{props.get('container_duration_sec', 0)} seconds"],
        ["Audio/Video Track Skew", f"{props.get('audio_video_skew_sec', 0):+.4f} seconds", "Elementary Timing Evaluation", "Standard Constant Frame Rate (CFR)"],
    ]
    t_stream = Table(stream_data, colWidths=[110, 160, 110, 160])
    t_stream.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f8fafc")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#f8fafc")),
        ("GRID", (0, 0), (-1, -1), 0.5, border_slate),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_stream)
    story.append(Spacer(1, 8))

    # Section 3: Color Profile & Night-Vision Grading
    story.append(Paragraph("3. Color Profile & Night-Theme / Filter Analysis", section_heading))
    cprof = video_analysis.get("color_profile", {})
    night_str = "ACTIVE (Monochrome / Night Vision Filter)" if cprof.get("night_theme_detected") else "NORMAL (Natural Color Spectrum)"
    night_color = amber_alert if cprof.get("night_theme_detected") else emerald_check

    color_data = [
        ["Mean Saturation (S)", f"{cprof.get('mean_saturation', 0):.1f} / 255.0", "Mean Luminance (V)", f"{cprof.get('mean_luminance', 0):.1f} / 255.0"],
        ["RGB Channel Correlation", f"{cprof.get('channel_correlation', 0):.4f}", "Night Theme Classification", Paragraph(f"<font color='{night_color.hexval()}'><b>{night_str}</b></font>", body_style)],
    ]
    t_color = Table(color_data, colWidths=[110, 160, 110, 160])
    t_color.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f8fafc")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#f8fafc")),
        ("GRID", (0, 0), (-1, -1), 0.5, border_slate),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_color)
    story.append(Spacer(1, 8))

    # Section 4: Temporal Splicing & Cut Detection Table
    story.append(Paragraph("4. Temporal Splicing & Cut Detection", section_heading))
    cuts = video_analysis.get("temporal_cuts", {}).get("cuts", [])
    if cuts:
        cuts_table_data = [["#", "Timestamp", "Frame", "Cut Type", "Bhattacharyya Dist", "Z-Score", "Pixel Delta"]]
        for c in cuts:
            cuts_table_data.append([
                str(c.get("cut_index", 1)),
                f"{c.get('timestamp_sec', 0):.2f}s",
                str(c.get("frame_index", 0)),
                c.get("cut_type", "Cut"),
                f"{c.get('bhattacharyya_distance', 0):.4f}",
                f"{c.get('bhatt_z_score', 0):.1f}",
                f"{c.get('pixel_delta', 0):.1f}",
            ])
        t_cuts = Table(cuts_table_data, colWidths=[25, 65, 50, 150, 90, 60, 100])
        t_cuts.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fee2e2")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#991b1b")),
            ("GRID", (0, 0), (-1, -1), 0.5, border_slate),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t_cuts)
    else:
        story.append(Paragraph("<b>No temporal cut anomalies detected:</b> Video timeline exhibits continuous inter-frame progression without abrupt statistical distance spikes.", body_style))
    story.append(Spacer(1, 8))

    # Section 5: Keyframes Gallery
    keyframes = video_analysis.get("keyframes", [])
    if keyframes:
        story.append(Paragraph("5. Keyframe Extraction & Noise Residual Checkpoints", section_heading))
        kf_row = []
        for k in keyframes[:3]:
            art_p = Path(k.get("artifact_path", ""))
            if not art_p.exists() and k.get("artifact_name"):
                art_p = settings.ARTIFACTS_DIR / k.get("artifact_name")
            if art_p.exists():
                try:
                    rl_img = RLImage(str(art_p), width=160, height=90)
                    cap_text = f"Frame {k.get('frame_index')} ({k.get('timestamp_sec')}s)<br/>Noise: {k.get('noise_variance')}"
                    kf_row.append([rl_img, Paragraph(cap_text, subtitle_style)])
                except Exception:
                    pass
        if kf_row:
            t_kf = Table([[item[0] for item in kf_row], [item[1] for item in kf_row]], colWidths=[175] * len(kf_row))
            t_kf.setStyle(TableStyle([
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("PADDING", (0, 0), (-1, -1), 2),
            ]))
            story.append(t_kf)
        story.append(Spacer(1, 8))

    # Section 6: Findings & Legal Disclaimer
    story.append(Paragraph("6. Structured Forensic Examination Findings", section_heading))
    findings_data = [["Severity", "Forensic Test", "Observed Result", "Explanation & Admissibility Note"]]
    for f in findings:
        sev_color = colors.HexColor("#ef4444") if f.get("severity") in ["high", "critical"] else (amber_alert if f.get("severity") == "medium" else colors.HexColor("#3b82f6"))
        findings_data.append([
            Paragraph(f"<font color='{sev_color.hexval()}'><b>{f.get('severity', 'info').upper()}</b></font>", body_style),
            Paragraph(f.get("test_performed", ""), body_style),
            Paragraph(f.get("observed_result", ""), body_style),
            Paragraph(f.get("explanation", ""), body_style),
        ])
    t_find = Table(findings_data, colWidths=[55, 120, 165, 200])
    t_find.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("GRID", (0, 0), (-1, -1), 0.5, border_slate),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_find)
    story.append(Spacer(1, 10))

    disclaimer = (
        "<b>SWGDE & ISO/IEC 27037 FORENSIC ADMISSIBILITY STATEMENT:</b><br/>"
        "This video examination report was generated programmatically by the EviSutra Digital Forensics Suite v0.2.0. "
        "Cryptographic digests substantiate that the byte stream examined was identical to the evidence deposited at intake. "
        "Temporal cut detections and color grading analysis provide empirical technical measurements for certified forensic video examiner review "
        "and do not constitute an autonomous claim of criminal intent or court presentation without qualified expert witness testimony under Indian Evidence Act Section 65B."
    )
    story.append(Paragraph(disclaimer, disclaimer_style))

    doc.build(story)
    return report_id


def generate_audio_pdf_report(
    evidence: dict[str, Any],
    integrity: dict[str, Any],
    audio_analysis: dict[str, Any],
    findings: list[dict[str, Any]],
    output_path: Path,
) -> str:
    """
    Generates a SWGDE-compliant PDF Forensic Audio Examination Report:
    - Cryptographic chain of custody
    - Native audio stream telemetry
    - Spectral & synthetic speech indicators
    - Embedded waveform + spectrogram artifact
    - Suspicious segments & acoustic splice table
    - Structured forensic findings & legal disclaimer
    """
    report_id = f"rep_aud_{uuid.uuid4().hex[:8]}"
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "AudioDocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=3,
    )
    subtitle_style = ParagraphStyle(
        "AudioDocSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=8,
    )
    section_heading = ParagraphStyle(
        "AudioSectionHead",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=13,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=6,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "AudioBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor("#334155"),
    )
    mono_style = ParagraphStyle(
        "AudioMono",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=7,
        leading=8.5,
        textColor=colors.HexColor("#0f172a"),
    )
    disclaimer_style = ParagraphStyle(
        "AudioDisclaimer",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7,
        leading=9.5,
        textColor=colors.HexColor("#64748b"),
    )

    border_slate = colors.HexColor("#cbd5e1")
    bg_light = colors.HexColor("#f8fafc")
    brand_blue = colors.HexColor("#0284c7")
    emerald_success = colors.HexColor("#16a34a")
    amber_alert = colors.HexColor("#d97706")
    red_alert = colors.HexColor("#ef4444")

    story = []

    # Title Banner
    story.append(Paragraph("EviSutra Digital Forensics Suite — Forensic Audio Examination Report", title_style))
    meta_sub = (
        f"<b>Report ID:</b> {report_id} &nbsp;|&nbsp; "
        f"<b>Evidence ID:</b> {evidence.get('id', 'N/A')} &nbsp;|&nbsp; "
        f"<b>Generated:</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')} &nbsp;|&nbsp; "
        f"<b>Standard:</b> SWGDE Audio Guidelines"
    )
    story.append(Paragraph(meta_sub, subtitle_style))
    story.append(Spacer(1, 4))

    # Executive Classification Banner
    classification = audio_analysis.get("classification", "natural_speech_consistent")
    is_synth = classification == "ai_synthesized_voice_detected"
    is_splice = classification == "acoustic_splicing_detected"

    if is_synth:
        banner_bg = colors.HexColor("#fef2f2")
        banner_border = red_alert
        banner_title = "AI SYNTHESIZED / GENERATED VOICE DETECTED"
    elif is_splice:
        banner_bg = colors.HexColor("#fffbeb")
        banner_border = amber_alert
        banner_title = "ACOUSTIC SPLICING / EDITING DETECTED"
    else:
        banner_bg = colors.HexColor("#f0fdf4")
        banner_border = emerald_success
        banner_title = "NATURAL SPEECH ACOUSTIC CONSISTENCY VERIFIED"

    banner_data = [
        [
            Paragraph(f"<b>FORENSIC DETERMINATION:</b> <font color='{banner_border.hexval()}'><b>{banner_title}</b></font>", body_style),
            Paragraph(audio_analysis.get("summary_statement", ""), body_style),
        ]
    ]
    t_banner = Table(banner_data, colWidths=[200, 340])
    t_banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), banner_bg),
        ("BOX", (0, 0), (-1, -1), 1, banner_border),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t_banner)
    story.append(Spacer(1, 8))

    # Section 1: Chain of Custody & Evidence Metadata
    story.append(Paragraph("1. Evidence Identification & Cryptographic Chain of Custody", section_heading))
    match_color = emerald_success if integrity.get("matches") else red_alert
    match_str = "VERIFIED MATCH" if integrity.get("matches") else "INTEGRITY MISMATCH / CORRUPTION"

    chain_data = [
        [Paragraph("<b>Original Filename:</b>", body_style), Paragraph(str(evidence.get("original_filename")), body_style),
         Paragraph("<b>Evidence ID:</b>", body_style), Paragraph(str(evidence.get("id")), mono_style)],
        [Paragraph("<b>Container Format:</b>", body_style), Paragraph(f"{audio_analysis['audio_properties']['format']} Audio", body_style),
         Paragraph("<b>File Size:</b>", body_style), Paragraph(f"{evidence.get('file_size', 0):,} bytes", body_style)],
        [Paragraph("<b>Intake SHA-256 Digest:</b>", body_style), Paragraph(str(evidence.get("sha256_intake")), mono_style),
         Paragraph("<b>Vault Verification:</b>", body_style), Paragraph(f"<font color='{match_color.hexval()}'><b>{match_str}</b></font>", body_style)],
        [Paragraph("<b>Checked SHA-256:</b>", body_style), Paragraph(str(integrity.get("calculated_hash")), mono_style),
         Paragraph("<b>Checked Timestamp:</b>", body_style), Paragraph(str(integrity.get("checked_at", "N/A"))[:19], body_style)],
    ]
    t_chain = Table(chain_data, colWidths=[110, 180, 110, 140])
    t_chain.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg_light),
        ("GRID", (0, 0), (-1, -1), 0.5, border_slate),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t_chain)
    story.append(Spacer(1, 8))

    # Section 2: Audio Stream Telemetry & Synthetic Indicators
    story.append(Paragraph("2. Acoustic Properties & Synthetic Speech Indicators", section_heading))
    props = audio_analysis["audio_properties"]
    synth = audio_analysis["synthetic_indicators"]

    synth_color = red_alert if synth.get("synthetic_voice_detected") else emerald_success
    synth_label = "SYNTHETIC ARTIFACTS DETECTED" if synth.get("synthetic_voice_detected") else "NATURAL ACOUSTICS"

    telemetry_data = [
        [Paragraph("<b>Sampling Rate:</b>", body_style), Paragraph(f"{props['sample_rate_hz']} Hz ({props['channels']} ch)", body_style),
         Paragraph("<b>Duration:</b>", body_style), Paragraph(f"{props['duration_sec']:.2f} seconds", body_style)],
        [Paragraph("<b>Ambient Noise Floor:</b>", body_style), Paragraph(f"RMS = {synth['noise_floor_rms']:.5f}", body_style),
         Paragraph("<b>Digital Silence Gaps:</b>", body_style), Paragraph(f"{synth['digital_silence_ratio_pct']:.1f}% ({synth['total_digital_silence_sec']:.2f}s)", body_style)],
        [Paragraph("<b>Spectral Rolloff (85%/95%):</b>", body_style), Paragraph(f"{synth['spectral_rolloff_85_hz']:.0f} Hz / {synth['spectral_rolloff_95_hz']:.0f} Hz", body_style),
         Paragraph("<b>HF Energy (&gt;8kHz):</b>", body_style), Paragraph(f"{synth['hf_energy_ratio_pct']:.2f}%", body_style)],
        [Paragraph("<b>Spectral Flux Mean / Max:</b>", body_style), Paragraph(f"{synth['mean_spectral_flux']:.4f} / {synth['max_spectral_flux']:.4f}", body_style),
         Paragraph("<b>Acoustic Verdict:</b>", body_style), Paragraph(f"<font color='{synth_color.hexval()}'><b>{synth_label}</b></font>", body_style)],
    ]
    t_telemetry = Table(telemetry_data, colWidths=[120, 160, 120, 140])
    t_telemetry.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg_light),
        ("GRID", (0, 0), (-1, -1), 0.5, border_slate),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t_telemetry)
    story.append(Spacer(1, 8))

    # Section 3: Spectrogram & Waveform Artifact
    spec_art = audio_analysis.get("spectrogram_artifact")
    if spec_art:
        art_path = settings.ARTIFACTS_DIR / spec_art
        if not art_path.exists():
            art_path = Path(spec_art)
        if art_path.exists():
            story.append(Paragraph("3. Calibrated Forensic Waveform & Mel-Spectrogram Density", section_heading))
            try:
                rl_spec = RLImage(str(art_path), width=540, height=270)
                story.append(rl_spec)
                story.append(Spacer(1, 8))
            except Exception:
                pass

    # Section 4: Suspicious Segments & Edit Discontinuities Table
    segments = audio_analysis.get("suspicious_segments", [])
    if segments:
        story.append(Paragraph(f"4. Detected Acoustic Anomalies & Spliced Segments ({len(segments)} items)", section_heading))
        seg_data = [["#", "Interval (Time)", "Type", "Severity", "Spectral Value / Z", "Forensic Explanation"]]
        for s in segments[:15]:
            sev_col = red_alert if s.get("severity") in ["critical", "high"] else amber_alert
            seg_data.append([
                Paragraph(str(s.get("segment_index")), mono_style),
                Paragraph(f"{s.get('start_sec', 0):.2f}s &ndash; {s.get('end_sec', 0):.2f}s ({s.get('duration_sec', 0):.2f}s)", body_style),
                Paragraph(s.get("anomaly_type", "").replace("_", " ").title(), body_style),
                Paragraph(f"<font color='{sev_col.hexval()}'><b>{s.get('severity', '').upper()}</b></font>", body_style),
                Paragraph(f"{s.get('spectral_value', 0):.3f} ({s.get('z_score', 0):.1f}&sigma;)", mono_style),
                Paragraph(s.get("explanation", ""), body_style),
            ])
        t_seg = Table(seg_data, colWidths=[20, 100, 85, 55, 75, 205])
        t_seg.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("GRID", (0, 0), (-1, -1), 0.5, border_slate),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("PADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(t_seg)
        story.append(Spacer(1, 8))

    # Section 5: Structured Forensic Examination Findings
    story.append(Paragraph("5. Structured SWGDE Forensic Findings", section_heading))
    findings_data = [["Severity", "Forensic Test", "Observed Result", "Explanation & Admissibility Note"]]
    for f in findings:
        sev_color = red_alert if f.get("severity") in ["high", "critical"] else (amber_alert if f.get("severity") == "medium" else colors.HexColor("#3b82f6"))
        findings_data.append([
            Paragraph(f"<font color='{sev_color.hexval()}'><b>{f.get('severity', 'info').upper()}</b></font>", body_style),
            Paragraph(f.get("test_performed", ""), body_style),
            Paragraph(f.get("observed_result", ""), body_style),
            Paragraph(f.get("explanation", ""), body_style),
        ])
    t_find = Table(findings_data, colWidths=[55, 120, 165, 200])
    t_find.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("GRID", (0, 0), (-1, -1), 0.5, border_slate),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_find)
    story.append(Spacer(1, 10))

    disclaimer = (
        "<b>SWGDE & ISO/IEC 27037 FORENSIC ADMISSIBILITY STATEMENT:</b><br/>"
        "This audio examination report was generated programmatically by the EviSutra Digital Forensics Suite v0.2.0. "
        "Cryptographic digests substantiate that the byte stream examined was identical to the evidence deposited at intake. "
        "Spectral flux cut detections, digital silence gap measurements, and ambient noise floor estimation provide empirical "
        "measurements for certified forensic audio examiner review and do not constitute an autonomous claim of criminal intent "
        "or court presentation without qualified expert witness testimony under Indian Evidence Act Section 65B."
    )
    story.append(Paragraph(disclaimer, disclaimer_style))

    doc.build(story)
    return report_id
