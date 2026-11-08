import unittest
from catalog import parse_product, discover, parse_sizes

class CatalogTests(unittest.TestCase):
    def test_decimal_sizes_and_pair_order(self):
        self.assertEqual(parse_sizes('50,5 × 110 cm, 60x120cm, 50,5 × 110 cm'), [[50.5,110.0],[60.0,120.0]])
    def test_product_excludes_related_work_dimensions(self):
        html = '''<meta property="og:image" content="https://luxart.com/art.jpg"><h1>[R] Sodas II</h1><div class="summary"><h3><a>Gintaras Tadauskas</a></h3><label>Dydis</label><select><option>50 x 115 cm (€160)</option><option>60 x 140 cm</option></select></div><section class="related">90x90cm</section>'''
        p = parse_product(html, 'https://luxart.com/paveikslai/sodas/')
        self.assertEqual(p['sizes'], [[50,115],[60,140]])
        self.assertEqual(p['artist'], 'Gintaras Tadauskas')
        self.assertEqual(p['image'], 'https://luxart.com/art.jpg')
    def test_discovery_rejects_foreign_links_and_pagination_as_products(self):
        d = discover('<a href="/paveikslai/sodas/">Art</a><a href="/paveikslai/page/2/">2</a><a href="https://evil.test/paveikslai/x/">X</a>')
        self.assertEqual(d['products'], ['https://luxart.com/paveikslai/sodas/'])
        self.assertEqual(d['pages'], ['https://luxart.com/paveikslai/page/2/'])
    def test_missing_dimensions_stay_missing(self):
        self.assertEqual(parse_product('<h1>Art</h1><p>No sizes</p>', 'https://luxart.com/paveikslai/x/')['sizes'], [])

if __name__ == '__main__': unittest.main()

class OrientationTests(unittest.TestCase):
    def product(self, width, height, size):
        return parse_product(f'<h1>Art</h1><div class="summary"><label>{size} cm</label></div><div class="woocommerce-product-gallery"><img src="https://luxart.com/art.jpg" data-large_image_width="{width}" data-large_image_height="{height}"></div>', 'https://luxart.com/paveikslai/art/')
    def test_landscape_height_first(self):
        self.assertEqual(self.product(1000,699,'40 x 55').get('size_order'),'hw')
    def test_portrait_width_first(self):
        self.assertEqual(self.product(500,1000,'50 x 100').get('size_order'),'wh')
    def test_square_preview_does_not_resolve_non_square_size(self):
        self.assertEqual(self.product(1000,1000,'50 x 100').get('size_order'),'unknown')
    def test_square_sizes_are_unambiguous(self):
        self.assertEqual(self.product(1000,1000,'50 x 50').get('size_order'),'square')

class CategoryTests(unittest.TestCase):
    def test_accessories_classified_from_breadcrumbs(self):
        p=parse_product('<h1>Bag</h1><div class="summary"><nav class="woocommerce-breadcrumb">Visi darbai / Aksesuarai / Kuprinės</nav></div>','https://luxart.com/paveikslai/bag/')
        self.assertEqual(p.get('category'),'Kuprinės')
        self.assertFalse(p.get('is_artwork',True))
