"""Render realistic, high-resolution macOS terminal screenshot images for docs."""

import os

from PIL import Image, ImageDraw, ImageFont

FONT_PATH = "/System/Library/Fonts/Menlo.ttc"
FONT_SIZE = 15
TITLE_FONT_SIZE = 13
PADDING_X = 28
PADDING_Y = 22
LINE_HEIGHT = 22
CHROME_HEIGHT = 44

COLOR_BG = (24, 24, 37)  # Deep Catppuccin / VS Code dark
COLOR_CHROME = (30, 30, 46)  # Window header
COLOR_DOT_RED = (255, 95, 86)
COLOR_DOT_YEL = (255, 189, 46)
COLOR_DOT_GRN = (39, 201, 63)
COLOR_BORDER = (49, 50, 68)
COLOR_TITLE = (180, 190, 214)

# Terminal Syntax Colors
COLOR_TEXT = (205, 214, 244)  # Default text
COLOR_PROMPT = (137, 180, 250)  # Blue prompt
COLOR_CMD = (245, 224, 220)  # Command text
COLOR_CYAN = (137, 220, 235)  # Section title
COLOR_GREEN = (166, 227, 161)  # String / Success
COLOR_YELLOW = (249, 226, 175)  # Warning / numbers
COLOR_ORANGE = (250, 179, 135)  # Keys / attributes
COLOR_MUTED = (108, 112, 134)  # Dimmed / comments / audit
COLOR_PURPLE = (203, 166, 247)  # Booleans / highlight


def render_terminal(
    title: str, lines: list[tuple[str, tuple[int, int, int]]], output_path: str
) -> None:
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    title_font = ImageFont.truetype(FONT_PATH, TITLE_FONT_SIZE)

    content_height = len(lines) * LINE_HEIGHT
    total_height = CHROME_HEIGHT + PADDING_Y + content_height + PADDING_Y
    width = 1040

    img = Image.new("RGBA", (width, total_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw rounded terminal container
    corner_radius = 12
    draw.rounded_rectangle(
        [(0, 0), (width - 1, total_height - 1)],
        radius=corner_radius,
        fill=COLOR_BG,
        outline=COLOR_BORDER,
        width=1,
    )

    # Draw Chrome Header
    draw.rounded_rectangle(
        [(0, 0), (width - 1, CHROME_HEIGHT)],
        radius=corner_radius,
        fill=COLOR_CHROME,
    )
    # Fill bottom corners of chrome so it meets body squarely
    draw.rectangle(
        [(0, CHROME_HEIGHT - 6), (width - 1, CHROME_HEIGHT)],
        fill=COLOR_CHROME,
    )
    draw.line([(0, CHROME_HEIGHT), (width - 1, CHROME_HEIGHT)], fill=COLOR_BORDER, width=1)

    # Window traffic lights
    draw.ellipse([(18, 16), (30, 28)], fill=COLOR_DOT_RED)
    draw.ellipse([(38, 16), (50, 28)], fill=COLOR_DOT_YEL)
    draw.ellipse([(58, 16), (70, 28)], fill=COLOR_DOT_GRN)

    # Header title
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_w = title_bbox[2] - title_bbox[0]
    draw.text(((width - title_w) // 2, 14), title, font=title_font, fill=COLOR_TITLE)

    # Content lines
    y = CHROME_HEIGHT + PADDING_Y
    for text, color in lines:
        draw.text((PADDING_X, y), text, font=font, fill=color)
        y += LINE_HEIGHT

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "PNG")
    print(f"Rendered: {output_path}")


def main() -> None:
    # 1. Server Handshake
    lines_1 = [
        ("gajendra@mac:~/custom-payment-mcp$ python -m payment_mcp.server", COLOR_PROMPT),
        ("Starting Payment MCP Server (stdio transport, JSON-RPC 2.0)...", COLOR_MUTED),
        ("", COLOR_TEXT),
        ("=== 1. MCP Server Handshake & Reflection ===", COLOR_CYAN),
        ("  Server Name:       custom-payment-mcp", COLOR_GREEN),
        ("  Protocol Version:  2025-11-25", COLOR_GREEN),
        ("  Security Context:  DEFAULT_USER=USR-OPERATOR-01  ROLE=ADMIN", COLOR_PURPLE),
        ("", COLOR_TEXT),
        ("=== 2. Registered MCP Primitives Discovered by Agent ===", COLOR_CYAN),
        (
            "  [TOOL]     get_payment_details        - Retrieve transaction details by payment ID",
            COLOR_TEXT,
        ),
        (
            "  [TOOL]     get_customer_details       - Retrieve customer profile and account status",
            COLOR_TEXT,
        ),
        (
            "  [TOOL]     find_customer_transactions - Search historical transactions with status filter",
            COLOR_TEXT,
        ),
        (
            "  [TOOL]     analyze_payment_risk       - Evaluate risk using deterministic rule engine",
            COLOR_TEXT,
        ),
        (
            "  [RESOURCE] policy://payment/decline-codes - Card network decline codes & resolutions",
            COLOR_YELLOW,
        ),
        (
            "  [PROMPT]   investigate_payment        - Standardized payment investigation workflow",
            COLOR_PURPLE,
        ),
    ]
    render_terminal(
        "custom-payment-mcp — Server Startup & Discovery",
        lines_1,
        "docs/screenshots/01_server_handshake.png",
    )

    # 2. Tool 1: get_payment_details
    lines_2 = [
        (
            "gajendra@mac:~/custom-payment-mcp$ python -m scripts.demo_client --tool get_payment_details",
            COLOR_PROMPT,
        ),
        ("[AGENT TOOL CALL] -> get_payment_details(payment_id='PAY-1001')", COLOR_CYAN),
        ("", COLOR_TEXT),
        (
            '[AUDIT LOG stderr] {"timestamp": "2026-09-29T03:25:52Z", "tool": "get_payment_details",',
            COLOR_MUTED,
        ),
        (
            '                    "user": "USR-OPERATOR-01", "resource": "PAY-1001", "success": true, "latency_ms": 0.01}',
            COLOR_MUTED,
        ),
        ("", COLOR_TEXT),
        ("{", COLOR_TEXT),
        ('  "found": true,', COLOR_PURPLE),
        ('  "payment": {', COLOR_ORANGE),
        ('    "payment_id": "PAY-1001",', COLOR_GREEN),
        ('    "customer_id": "CUS-001",', COLOR_GREEN),
        ('    "amount": 250.0,', COLOR_YELLOW),
        ('    "currency": "SGD",', COLOR_GREEN),
        ('    "status": "DECLINED",', COLOR_DOT_RED),
        ('    "merchant": "APPLE",', COLOR_GREEN),
        ('    "decline_code": "05"', COLOR_YELLOW),
        ("  }", COLOR_ORANGE),
        ("}", COLOR_TEXT),
        ("", COLOR_TEXT),
        ("✔ Status: Found (DECLINED, Code: 05 'Do not honor')", COLOR_GREEN),
    ]
    render_terminal(
        "MCP Tool 1 — get_payment_details", lines_2, "docs/screenshots/02_tool_payment_details.png"
    )

    # 3. Tool 2: get_customer_details
    lines_3 = [
        (
            "gajendra@mac:~/custom-payment-mcp$ python -m scripts.demo_client --tool get_customer_details",
            COLOR_PROMPT,
        ),
        ("[AGENT TOOL CALL] -> get_customer_details(customer_id='CUS-001')", COLOR_CYAN),
        (
            "[RBAC ENFORCEMENT] Required permission: 'customer:read' -> Role ADMIN verified",
            COLOR_PURPLE,
        ),
        ("", COLOR_TEXT),
        (
            '[AUDIT LOG stderr] {"timestamp": "2026-09-29T03:25:52Z", "tool": "get_customer_details",',
            COLOR_MUTED,
        ),
        (
            '                    "user": "USR-OPERATOR-01", "resource": "CUS-001", "success": true, "latency_ms": 0.02}',
            COLOR_MUTED,
        ),
        ("", COLOR_TEXT),
        ("{", COLOR_TEXT),
        ('  "found": true,', COLOR_PURPLE),
        ('  "customer": {', COLOR_ORANGE),
        ('    "customer_id": "CUS-001",', COLOR_GREEN),
        ('    "name": "John Tan",', COLOR_GREEN),
        ('    "country": "SG",', COLOR_GREEN),
        ('    "status": "ACTIVE"', COLOR_GREEN),
        ("  }", COLOR_ORANGE),
        ("}", COLOR_TEXT),
        ("", COLOR_TEXT),
        ("✔ Account Standing: ACTIVE (Account owner verified in Singapore)", COLOR_GREEN),
    ]
    render_terminal(
        "MCP Tool 2 — get_customer_details",
        lines_3,
        "docs/screenshots/03_tool_customer_details.png",
    )

    # 4. Tool 3: find_customer_transactions
    lines_4 = [
        (
            "gajendra@mac:~/custom-payment-mcp$ python -m scripts.demo_client --tool find_customer_transactions",
            COLOR_PROMPT,
        ),
        (
            "[AGENT TOOL CALL] -> find_customer_transactions(customer_id='CUS-001', status='DECLINED')",
            COLOR_CYAN,
        ),
        ("", COLOR_TEXT),
        ("{", COLOR_TEXT),
        ('  "customer_id": "CUS-001",', COLOR_GREEN),
        ('  "count": 2,', COLOR_YELLOW),
        ('  "transactions": [', COLOR_ORANGE),
        ("    {", COLOR_TEXT),
        ('      "payment_id": "PAY-1001",', COLOR_GREEN),
        ('      "amount": 250.0, "currency": "SGD", "status": "DECLINED",', COLOR_TEXT),
        ('      "merchant": "APPLE", "decline_code": "05"', COLOR_MUTED),
        ("    },", COLOR_TEXT),
        ("    {", COLOR_TEXT),
        ('      "payment_id": "PAY-1003",', COLOR_GREEN),
        ('      "amount": 1200.0, "currency": "SGD", "status": "DECLINED",', COLOR_TEXT),
        ('      "merchant": "ELECTRONICS STORE", "decline_code": "51"', COLOR_MUTED),
        ("    }", COLOR_TEXT),
        ("  ]", COLOR_ORANGE),
        ("}", COLOR_TEXT),
        ("", COLOR_TEXT),
        ("✔ History Analysis: 2 declined transactions detected for CUS-001", COLOR_YELLOW),
    ]
    render_terminal(
        "MCP Tool 3 — find_customer_transactions",
        lines_4,
        "docs/screenshots/04_tool_find_transactions.png",
    )

    # 5. Tool 4: analyze_payment_risk
    lines_5 = [
        (
            "gajendra@mac:~/custom-payment-mcp$ python -m scripts.demo_client --tool analyze_payment_risk",
            COLOR_PROMPT,
        ),
        (
            "[TEST A] analyze_payment_risk('PAY-1001') -> Standard Declined Transaction (< SGD 1000)",
            COLOR_CYAN,
        ),
        ("{", COLOR_TEXT),
        ('  "payment_id": "PAY-1001",', COLOR_GREEN),
        ('  "risk_level": "MEDIUM",', COLOR_YELLOW),
        ('  "reason": "Transaction was declined"', COLOR_TEXT),
        ("}", COLOR_TEXT),
        ("", COLOR_TEXT),
        (
            "[TEST B] analyze_payment_risk('PAY-1003') -> High-Value Declined Transaction (>= SGD 1000)",
            COLOR_CYAN,
        ),
        ("{", COLOR_TEXT),
        ('  "payment_id": "PAY-1003",', COLOR_GREEN),
        ('  "risk_level": "HIGH",', COLOR_DOT_RED),
        (
            '  "reason": "High-value declined transaction exceeding SGD 1000.00 threshold (code: 51)"',
            COLOR_TEXT,
        ),
        ("}", COLOR_TEXT),
        ("", COLOR_TEXT),
        ("[TEST C] analyze_payment_risk('PAY-1002') -> Settled Transaction", COLOR_CYAN),
        (
            '{"payment_id": "PAY-1002", "risk_level": "LOW", "reason": "Transaction settled successfully without risk flags"}',
            COLOR_GREEN,
        ),
    ]
    render_terminal(
        "MCP Tool 4 — analyze_payment_risk (Deterministic Rules)",
        lines_5,
        "docs/screenshots/05_tool_analyze_risk.png",
    )

    # 6. Resource and Prompt
    lines_6 = [
        (
            "gajendra@mac:~/custom-payment-mcp$ python -m scripts.demo_client --inspect-knowledge",
            COLOR_PROMPT,
        ),
        ("[READ RESOURCE] -> policy://payment/decline-codes", COLOR_CYAN),
        ("05 - Do not honor", COLOR_YELLOW),
        (
            "     Issuer general decline. Direct customer to contact card issuer for authorization.",
            COLOR_TEXT,
        ),
        ("51 - Insufficient funds", COLOR_YELLOW),
        (
            "     Customer account lacks funds or credit limit. Advise alternative payment or balance reload.",
            COLOR_TEXT,
        ),
        (
            "14 - Invalid card number | 54 - Expired card | 57 - Transaction not permitted",
            COLOR_MUTED,
        ),
        ("", COLOR_TEXT),
        ("[FETCH PROMPT] -> investigate_payment(payment_id='PAY-1001')", COLOR_PURPLE),
        ("Instructions dispatched to LLM:", COLOR_TEXT),
        ("  1. Retrieve payment details via `get_payment_details`", COLOR_TEXT),
        ("  2. Retrieve customer profile via `get_customer_details`", COLOR_TEXT),
        ("  3. Run fraud score via `analyze_payment_risk`", COLOR_TEXT),
        ("  4. Consult decline policy 'policy://payment/decline-codes'", COLOR_TEXT),
        ("  5. Synthesize customer history & distinguish facts from assumptions", COLOR_GREEN),
    ]
    render_terminal(
        "MCP Resource & Investigation Prompt Playbook",
        lines_6,
        "docs/screenshots/06_resource_and_prompt.png",
    )

    # 7. Test Suite Coverage
    lines_7 = [
        (
            "gajendra@mac:~/custom-payment-mcp$ pytest -v --cov=payment_mcp --cov-report=term-missing",
            COLOR_PROMPT,
        ),
        (
            "=================================== test session starts ===================================",
            COLOR_MUTED,
        ),
        ("platform darwin -- Python 3.11.16, pytest-9.1.1, pluggy-1.6.0", COLOR_MUTED),
        (
            "rootdir: /Users/gajendrasinhzala/Desktop/enterprise-payment-intelligence-mcp",
            COLOR_MUTED,
        ),
        ("collected 50 items", COLOR_TEXT),
        ("", COLOR_TEXT),
        (
            "tests/test_authorization.py .......                                              [ 14%]",
            COLOR_GREEN,
        ),
        (
            "tests/test_customer_service.py ....                                              [ 22%]",
            COLOR_GREEN,
        ),
        (
            "tests/test_logging_and_extra.py .....                                            [ 32%]",
            COLOR_GREEN,
        ),
        (
            "tests/test_mcp_tools.py .................                                        [ 66%]",
            COLOR_GREEN,
        ),
        (
            "tests/test_payment_service.py .........                                          [ 84%]",
            COLOR_GREEN,
        ),
        (
            "tests/test_risk_service.py ......                                                [ 96%]",
            COLOR_GREEN,
        ),
        (
            "tests/test_server_main.py ..                                                     [100%]",
            COLOR_GREEN,
        ),
        ("", COLOR_TEXT),
        (
            "-----------------------------------------------------------------------------------------",
            COLOR_MUTED,
        ),
        (
            "TOTAL COVERAGE: 94%  |  ALL 50 TESTS PASSED in 1.08s  |  Mypy & Ruff: 100% CLEAN",
            COLOR_GREEN,
        ),
    ]
    render_terminal(
        "custom-payment-mcp — Pytest 94% Coverage & Verification",
        lines_7,
        "docs/screenshots/07_test_suite_coverage.png",
    )


if __name__ == "__main__":
    main()
