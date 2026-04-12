from scraper.pipeline import build_parser


def test_pipeline_parser_defaults() -> None:
    parser = build_parser()
    args = parser.parse_args(["daily", "--brand", "istikbal"])
    assert args.mode == "daily"
    assert args.brand == "istikbal"


def test_pipeline_parser_report_mode() -> None:
    parser = build_parser()
    args = parser.parse_args(["report", "--email-report"])
    assert args.mode == "report"
    assert args.email_report is True
