from scraper.selector_harness import build_parser


def test_selector_harness_parser() -> None:
    parser = build_parser()
    args = parser.parse_args(["--brand", "bellona"])
    assert args.brand == "bellona"
