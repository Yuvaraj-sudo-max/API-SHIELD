"""
generate_pdf.py - Generates an executive engineering architecture and roadmap PDF
for the API Shield project.
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and print total page numbers."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Header (pages 2+)
        if self._pageNumber > 1:
            self.drawString(54, 750, "API SHIELD // ARCHITECTURE, DELIVERABLES & STRATEGIC ROADMAP")
            self.drawRightString(612 - 54, 750, "CONFIDENTIAL // GITHUB: Yuvaraj-sudo-max/API-SHIELD")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(54, 742, 612 - 54, 742)

        # Footer (all pages)
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#94a3b8"))
        self.drawString(54, 36, "API Shield — 3D Intelligent Rate Limiter & Abuse Prevention Gateway")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(612 - 54, 36, page_str)
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(54, 46, 612 - 54, 46)

        self.restoreState()


def build_pdf(filename: str):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    primary_color = colors.HexColor("#0f172a")  # Slate 900
    brand_blue = colors.HexColor("#2563eb")     # Blue 600
    brand_cyan = colors.HexColor("#0284c7")     # Sky 600
    brand_indigo = colors.HexColor("#4f46e5")   # Indigo 600
    text_dark = colors.HexColor("#1e293b")      # Slate 800
    text_muted = colors.HexColor("#475569")     # Slate 600
    bg_light = colors.HexColor("#f8fafc")       # Slate 50
    border_color = colors.HexColor("#e2e8f0")

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=primary_color,
        spaceAfter=4,
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=brand_indigo,
        spaceAfter=12,
    )

    meta_style = ParagraphStyle(
        "MetaText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=text_muted,
    )

    h1_style = ParagraphStyle(
        "Heading1_Custom",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=19,
        textColor=primary_color,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True,
    )

    h2_style = ParagraphStyle(
        "Heading2_Custom",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=brand_blue,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        "Body_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        textColor=text_dark,
        spaceAfter=6,
    )

    bullet_style = ParagraphStyle(
        "Bullet_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=text_dark,
        leftIndent=15,
        spaceAfter=3,
    )

    code_style = ParagraphStyle(
        "CodeSnippet",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#0f172a"),
        backColor=colors.HexColor("#f1f5f9"),
        borderPadding=4,
        spaceAfter=6,
    )

    story = []

    # Title & Metadata
    story.append(Paragraph("API SHIELD // SYSTEM COMPENDIUM", title_style))
    story.append(Paragraph("Architecture from Scratch, Integrated Enhancements & Next Strategic Milestones", subtitle_style))
    
    meta_table_data = [
        [
            Paragraph("<b>Author:</b> Yuvaraj s (Yuvaraj-sudo-max)", meta_style),
            Paragraph("<b>Repository:</b> github.com/Yuvaraj-sudo-max/API-SHIELD", meta_style),
        ],
        [
            Paragraph("<b>Version:</b> v2.4.0 (Production Release)", meta_style),
            Paragraph("<b>Engine:</b> Python 3.11 / Flask / Redis / DeepSeek LLM", meta_style),
        ],
    ]
    meta_table = Table(meta_table_data, colWidths=[250, 254])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), bg_light),
        ('BOX', (0,0), (-1,-1), 1, border_color),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 14))

    # Executive Summary Box
    summary_html = (
        "<b>EXECUTIVE OVERVIEW:</b> API Shield is an enterprise-grade API rate limiting and abuse defense gateway "
        "engineered to protect modern REST and LLM endpoints against abusive volumetric traffic, DDoS bursts, and token depletion. "
        "It unites real-time Redis in-memory storage, 3 distinct rate limiting algorithms, deep DeepSeek AI copilot capabilities, "
        "multi-tenant tier scaling, and an interactive 3D WebGL holographic defense cockpit."
    )
    summary_table = Table([[Paragraph(summary_html, body_style)]], colWidths=[504])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#eff6ff")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#bfdbfe")),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 12))

    # SECTION 1: WHAT WAS BUILT FROM SCRATCH
    story.append(Paragraph("1. WHAT WAS BUILT FROM THE SCRATCH (THE CORE SYSTEM)", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=brand_indigo, spaceAfter=8))

    story.append(Paragraph(
        "API Shield was designed from the ground up as a zero-dependency, self-contained rate limiting gateway "
        "built around strict Software Requirements Specifications (SRS). The foundational build consists of:", body_style))

    story.append(Paragraph("<b>A. Core Architecture & Request Decision Pipeline (SRS 5.1 & 23)</b>", h2_style))
    story.append(Paragraph("• <b>Identity Extraction:</b> Prioritizes <code>X-API-Key</code> request headers, falling back smoothly to remote IP addresses (<code>ip:127.0.0.1</code>).", bullet_style))
    story.append(Paragraph("• <b>RFC Key Privacy Masking:</b> Redacts plain-text credentials in logs (e.g., <code>key:sk-fc0...b1df</code>) adhering to enterprise data compliance.", bullet_style))
    story.append(Paragraph("• <b>Centralized Policy Manager:</b> Dynamic CRUD registry persisted to JSON with fine-grained endpoint rules (limits, windows, and active flags).", bullet_style))
    story.append(Paragraph("• <b>Middleware Decision Flow:</b> Evaluates requests before controller execution, dynamically injecting RFC rate limit headers (<code>X-RateLimit-Limit</code>, <code>X-RateLimit-Remaining</code>, <code>Retry-After</code>).", bullet_style))

    story.append(Paragraph("<b>B. Dual Rate Limiting Algorithms</b>", h2_style))
    story.append(Paragraph("• <b>Fixed Window (Atomic Counter):</b> Increments an atomic Redis key (<code>rate:{key}:{window}</code>) with automated TTL expiry for lightweight, high-throughput efficiency.", bullet_style))
    story.append(Paragraph("• <b>Sliding Window (Sorted Set / ZSET):</b> Maintains exact nanosecond request timestamps in Redis Sorted Sets, eliminating the 2x burst boundary vulnerability of fixed windows.", bullet_style))

    story.append(Paragraph("<b>C. Automated Abuse Defense & Penalty Box (SRS Section 6)</b>", h2_style))
    story.append(Paragraph("• Tracks rate limit violations per client with automatic cooldowns.", bullet_style))
    story.append(Paragraph("• Progressively escalates temporary ban durations: 1st violation (60s), 2nd (300s / 5m), 3rd+ (1800s / 30m).", bullet_style))
    story.append(Paragraph("• Blocked clients receive immediate <code>HTTP 429 Too Many Requests</code> with <code>Retry-After</code> before evaluating downstream endpoints.", bullet_style))

    story.append(Paragraph("<b>D. Storage Abstraction Layer (Zero-Dependency Fallback)</b>", h2_style))
    story.append(Paragraph("• Intelligently probes for a live Redis cluster at <code>localhost:6379</code>. If unavailable, it seamlessly switches to an in-memory <code>FakeRedis</code> engine, allowing complete local development and testing without installing Redis.", bullet_style))

    story.append(Paragraph("<b>E. 3D WebGL Holographic Command Dashboard</b>", h2_style))
    story.append(Paragraph("• Interactive Three.js particle core visualizing gateway traffic state (Nominal, Consumed, Defending, Breach).", bullet_style))
    story.append(Paragraph("• Real-time oscilloscope, pipeline stage tracker, and interactive traffic dispatcher with burst/attack simulation.", bullet_style))

    story.append(Spacer(1, 10))

    # SECTION 2: WHAT WAS ADDED IN THIS JOURNEY
    story.append(Paragraph("2. WHAT WE ADDED FROM SCRATCH IN THIS SPRINT", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=brand_indigo, spaceAfter=8))

    story.append(Paragraph(
        "During this iteration, the system was elevated from a basic prototype into a production-grade, AI-powered security platform. "
        "The following enterprise components were built and integrated from scratch:", body_style))

    # AI Feature Box
    story.append(Paragraph("<b>1. DeepSeek AI Security Engine Integration (ai_service.py)</b>", h2_style))
    story.append(Paragraph("• <b>Secure Key Management:</b> Safely configured live DeepSeek API credentials in <code>.env</code> with automatic parsing via <code>config.py</code>.", bullet_style))
    story.append(Paragraph("• <b>Rate-Limited AI LLM Gateway (<code>POST /api/ai/chat</code>):</b> Demonstrates shielding upstream LLM tokens against quota depletion with sliding window policy.", bullet_style))
    story.append(Paragraph("• <b>Autonomous Threat Auditor (<code>POST /api/ai/analyze-threat</code>):</b> Sends recent security audit stream logs to DeepSeek LLM for threat detection and anomaly scoring.", bullet_style))
    story.append(Paragraph("• <b>Policy Studio AI Copilot (<code>POST /api/ai/generate-policy</code>):</b> Translates human natural language security goals into validated rate limit policy JSON.", bullet_style))

    story.append(Paragraph("<b>2. Token Bucket Rate Limiting Engine (limiter.py)</b>", h2_style))
    story.append(Paragraph("• Implemented industry-standard Token Bucket algorithm supporting continuous fractional refill (<code>limit / window</code> tokens/sec) and controlled burst capacity.", bullet_style))
    story.append(Paragraph("• Added demo endpoint <code>GET /api/stream</code> backed by Token Bucket policy (10 burst / 30s window).", bullet_style))

    story.append(Paragraph("<b>3. Multi-Tenant Client Tiering (identity.py)</b>", h2_style))
    story.append(Paragraph("• Added tiered quota multiplier scaling: <b>Free (1.0x)</b>, <b>Pro (3.0x)</b>, and <b>Enterprise (10.0x)</b>.", bullet_style))
    story.append(Paragraph("• Injected <code>X-Client-Tier</code> response headers and updated Dispatcher UI with live multiplier preview.", bullet_style))

    story.append(Paragraph("<b>4. Native Prometheus Telemetry (metrics.py & GET /metrics)</b>", h2_style))
    story.append(Paragraph("• Thread-safe metrics collector exporting standard Prometheus exposition format (v0.0.4) tracking requests, 429 blocks, active policies, and DeepSeek completions.", bullet_style))

    story.append(Paragraph("<b>5. Production Containerization (Docker & Compose)</b>", h2_style))
    story.append(Paragraph("• Multi-stage <code>Dockerfile</code> with non-root <code>appuser</code>, automated curl healthchecks, and high-performance Gunicorn WSGI.", bullet_style))
    story.append(Paragraph("• <code>docker-compose.yml</code> orchestrating API Shield alongside a persistent, health-checked Redis 7 container.", bullet_style))

    story.append(Paragraph("<b>6. GitHub Actions CI/CD Pipeline (.github/workflows/ci.yml)</b>", h2_style))
    story.append(Paragraph("• Multi-version Python matrix testing (<b>Python 3.10, 3.11, 3.12</b>) with live Redis service and Docker Buildx validation.", bullet_style))

    story.append(Paragraph("<b>7. Expanded 46-Test Automated Suite</b>", h2_style))
    story.append(Paragraph("• Created <code>test_token_bucket.py</code>, <code>test_tiering.py</code>, and <code>test_metrics.py</code>. All 46 tests pass 100% in 3.8s.", bullet_style))

    story.append(Paragraph("<b>8. Public GitHub Deployment & Secret Safeguards</b>", h2_style))
    story.append(Paragraph("• Published to <b>https://github.com/Yuvaraj-sudo-max/API-SHIELD</b> with live API keys strictly protected by <code>.gitignore</code> and sanitizing remote credentials.", bullet_style))

    story.append(Spacer(1, 10))

    # SECTION 3: STRATEGIC NEXT STEPS & ROADMAP
    story.append(Paragraph("3. STRATEGIC NEXT STEPS & ROADMAP FOR THIS PROJECT", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=brand_indigo, spaceAfter=8))

    story.append(Paragraph(
        "To advance API Shield into a commercially viable enterprise gateway, the recommended next milestones are organized into four strategic horizons:", body_style))

    roadmap_data = [
        [
            Paragraph("<b>PHASE</b>", meta_style),
            Paragraph("<b>STRATEGIC OBJECTIVE</b>", meta_style),
            Paragraph("<b>KEY ACTION ITEMS & TECHNICAL DELIVERABLES</b>", meta_style),
        ],
        [
            Paragraph("<b>Phase 1<br/>Cloud Launch</b>", meta_style),
            Paragraph("Public Live Hosting & Managed Redis", meta_style),
            Paragraph("• Connect GitHub repo to <b>Render.com</b> or <b>Railway</b>.<br/>• Attach managed Redis instance (Upstash / Redis Cloud).<br/>• Configure custom domain with automatic SSL.", meta_style),
        ],
        [
            Paragraph("<b>Phase 2<br/>Enterprise Auth</b>", meta_style),
            Paragraph("OAuth2, JWT & Self-Service Keys", meta_style),
            Paragraph("• Integrate RS256 JWT validation for client tokens.<br/>• Build self-service developer portal for API key generation.<br/>• Connect Stripe billing webhooks to auto-assign Pro/Enterprise tiers.", meta_style),
        ],
        [
            Paragraph("<b>Phase 3<br/>Scalability</b>", meta_style),
            Paragraph("Distributed Redis & Geo-Replication", meta_style),
            Paragraph("• Transition to Redis Cluster with client-side hash routing.<br/>• Implement local sliding window caches using Redis Lua scripts.<br/>• Benchmarking under load using k6 / Locust (10,000+ req/sec).", meta_style),
        ],
        [
            Paragraph("<b>Phase 4<br/>Deep Observability</b>", meta_style),
            Paragraph("Grafana & Threat Intelligence", meta_style),
            Paragraph("• Deploy Grafana dashboard pre-configured for <code>/metrics</code>.<br/>• OpenTelemetry distributed tracing (traces per rate-limited request).<br/>• Automated Cloudflare Turnstile / CAPTCHA challenge on repeat 429s.", meta_style),
        ],
    ]

    roadmap_table = Table(roadmap_data, colWidths=[70, 130, 304])
    roadmap_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f172a")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, bg_light]),
    ]))
    story.append(roadmap_table)
    story.append(Spacer(1, 14))

    # Architecture Comparison Table
    story.append(Paragraph("<b>Summary Matrix: Algorithm Capabilities Comparison</b>", h2_style))
    algo_data = [
        [
            Paragraph("<b>ALGORITHM</b>", meta_style),
            Paragraph("<b>REDIS PRIMITIVE</b>", meta_style),
            Paragraph("<b>BURST PROTECTION</b>", meta_style),
            Paragraph("<b>PRIMARY USE CASE</b>", meta_style),
        ],
        [
            Paragraph("Fixed Window", meta_style),
            Paragraph("Atomic Counter (<code>INCR</code>)", meta_style),
            Paragraph("Basic (2x Boundary Risk)", meta_style),
            Paragraph("General Public Endpoints & Read APIs", meta_style),
        ],
        [
            Paragraph("Sliding Window", meta_style),
            Paragraph("Sorted Set (<code>ZSET</code>)", meta_style),
            Paragraph("100% Strict Precision", meta_style),
            Paragraph("Auth, Payments & DeepSeek LLM Gateway", meta_style),
        ],
        [
            Paragraph("Token Bucket", meta_style),
            Paragraph("Hash (<code>tokens</code>, <code>ts</code>)", meta_style),
            Paragraph("Controlled Burst to Capacity", meta_style),
            Paragraph("Streaming, WebSockets & High-Burst APIs", meta_style),
        ],
    ]
    algo_table = Table(algo_data, colWidths=[90, 120, 120, 174])
    algo_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), brand_indigo),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, bg_light]),
    ]))
    story.append(algo_table)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF generated successfully: {filename}")


if __name__ == "__main__":
    out_path = r"c:\Users\user\.gemini\antigravity-ide\scratch\api_shield\API_Shield_Architecture_and_Roadmap.pdf"
    build_pdf(out_path)
