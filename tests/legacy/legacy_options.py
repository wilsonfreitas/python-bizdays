def test_public_option_import():
    """get_option and set_option are importable and functional from the top-level package."""
    from bizdays import get_option, set_option

    original = get_option("mode")
    try:
        set_option("mode", "pandas")
        assert get_option("mode") == "pandas"
    finally:
        set_option("mode", original)
