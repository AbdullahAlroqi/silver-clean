from pathlib import Path

from PIL import Image

from test_discount_location_scope import TestConfig, app  # noqa: F401


def test_manifest_has_stable_installable_icons(app):
    client = app.test_client()
    response = client.get('/manifest.json')
    manifest = response.get_json()

    assert response.status_code == 200
    assert response.content_type == 'application/manifest+json'
    assert manifest['id'] == '/customer/'
    assert manifest['start_url'] == '/customer/'
    assert manifest['display'] == 'standalone'
    assert {icon['sizes'] for icon in manifest['icons']} == {'192x192', '512x512'}


def test_pwa_icon_files_match_manifest_dimensions():
    images = Path('app/static/images')
    assert Image.open(images / 'pwa-icon-192.png').size == (192, 192)
    assert Image.open(images / 'pwa-icon-512.png').size == (512, 512)


def test_service_worker_is_available_at_root_scope(app):
    response = app.test_client().get('/sw.js')

    assert response.status_code == 200
    assert response.headers['Service-Worker-Allowed'] == '/'
    assert 'no-cache' in response.headers['Cache-Control']
