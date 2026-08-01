from test_discount_location_scope import TestConfig, app  # noqa: F401


def test_public_layout_contains_logo_only_loading_screen(app):
    response = app.test_client().get('/')
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'id="site-loader"' in page
    assert 'site-loader__logo' in page
    assert 'loading-screen.js' in page
    assert 'جاري تجهيز' not in page


def test_loading_screen_assets_are_available(app):
    client = app.test_client()

    assert client.get('/static/css/loading-screen.css').status_code == 200
    assert client.get('/static/js/loading-screen.js').status_code == 200
