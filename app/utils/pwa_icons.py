import os

from PIL import Image, ImageOps


def refresh_pwa_icons(app, logo_path, background_color='#303030'):
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
            # Full-bleed square icons avoid the white frame iOS adds around
            # transparent/padded touch icons. Non-square logos are contained on
            # the site's own background color instead of white.
            if abs(logo.width - logo.height) <= max(2, round(max(logo.size) * 0.03)):
                canvas = ImageOps.fit(logo, (size, size), Image.Resampling.LANCZOS)
            else:
                canvas = Image.new('RGBA', (size, size), background_color)
                contained = ImageOps.contain(logo, (size, size), Image.Resampling.LANCZOS)
                canvas.alpha_composite(contained, ((size - contained.width) // 2, (size - contained.height) // 2))
            canvas.convert('RGB').save(os.path.join(output_dir, f'pwa-icon-{size}.png'), 'PNG', optimize=True)
    return True
