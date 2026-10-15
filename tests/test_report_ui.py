from html.parser import HTMLParser

from uk_waste_rule_mcp.report_ui import paid_report_html, message_response


def test_report_preserves_review_status_and_keeps_recovery_optional():
    report = {
        "decision": {"status": "REVIEW_REQUIRED", "registration_required": True},
        "source_health": {"status": "STALE", "decision_usable": False},
        "findings": [{"message": "Confirm missing facts", "status": "review", "severity": "warning"}],
        "next_actions": ["Confirm the official registration tier"],
    }
    html = paid_report_html(report, "co_paid")
    assert "Review required" in html
    assert "Official-source checks require review" in html
    assert "Confirm missing facts" in html
    assert "Confirm the official registration tier" in html
    assert "REVIEW_REQUIRED" in html  # Complete result retains exact machine status.
    class Details(HTMLParser):
        def __init__(self):
            super().__init__()
            self.details = []
        def handle_starttag(self, tag, attrs):
            if tag == "details":
                self.details.append(dict(attrs))
    parser = Details()
    parser.feed(html)
    assert len(parser.details) == 2
    assert all("open" not in attrs for attrs in parser.details)


def test_report_escapes_content_and_blocks_executable_source_links():
    html = paid_report_html({
        "decision": {"status": "<script>alert(1)</script>"},
        "evidence": [{"title": "<img src=x onerror=alert(1)>", "url": "javascript:alert(1)"}],
        "current_published_fees_gbp": {"standard_registration": 191.02},
    }, '<order>')
    assert "<script>" not in html
    assert "<img" not in html
    assert 'href="javascript:' not in html
    assert "&lt;order&gt;" in html
    assert "£191.02" in html
    assert "separate from your report purchase" in html


def test_message_pages_preserve_status_and_show_navigation():
    response = message_response("Report unavailable", "<unsafe>", 403)
    assert response.status_code == 403
    html = response.body.decode()
    assert "&lt;unsafe&gt;" in html
    assert 'href="/waste-report/recover"' in html
    assert 'name="viewport"' in html
    assert "style-src 'unsafe-inline'" in response.headers["content-security-policy"]
