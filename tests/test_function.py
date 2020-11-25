"""Test kedro_kubeflow functions."""

from kedro_kubeflow import app


def test_app():
    """Test app.main function."""
    assert app.main("ah ", 3) == "ah ah ah "
