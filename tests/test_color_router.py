from src.bot.routers.tools import color_tools


def test_build_color_summary_outputs_expected_data() -> None:
    summary, palette, swatch = color_tools.build_color_summary("#336699")
    assert "#336699" in summary
    assert "RGB: 51, 102, 153" in summary
    assert "Contrast vs white" in summary
    assert len(palette) == 5
    assert swatch.startswith(b"\x89PNG")
