import os

from PIL import Image, ImageOps


def refresh_pwa_icons(app, logo_path):
    """Build installable square icons from the currently configured site logo."""
    relative_logo = (logo_path or '/static/images/logo.png').split('?', 1)[0]
    if not relative_logo.startswith('/static/'):
        relative_logo = '/static/images/logo.png'
    source_path = os.path.join(app.root_path, relative_logo.lstrip('/').replace('/', os.sep))
    if not os.path.isfile(source_path):
        source_path = os.path.join(app.root_path, 'static', 'images', 'logo.png')
    if not os.path.isfile(source_path):
        return False

    output_dir = os.path.join(app.root_path, 'static', 'images')
    os.makedirs(output_dir, exist_ok=True)
    with Image.open(source_path) as source:
        logo = source.convert('RGBA')
        for size in (192, 512):
            padding = max(12, round(size * 0.08))
            contained = ImageOps.contain(logo, (size - padding * 2, size - padding * 2), Image.Resampling.LANCZOS)
            canvas = Image.new('RGBA', (size, size), (255, 255, 255, 0))
            canvas.alpha_composite(contained, ((size - contained.width) // 2, (size - contained.height) // 2))
            canvas.save(os.path.join(output_dir, f'pwa-icon-{size}.png'), 'PNG', optimize=True)
    return True
