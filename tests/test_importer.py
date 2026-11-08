import unittest
from importer import sitemap_locations
from catalog import parse_product

class ImportTests(unittest.TestCase):
    def test_sitemap_namespaces(self):
        self.assertEqual(sitemap_locations('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://luxart.com/paveikslai/x/</loc></url></urlset>'), ['https://luxart.com/paveikslai/x/'])
    def test_sale_price_is_attached_to_variant(self):
        p=parse_product('<h1>Du drugeliai</h1><div class="summary"><label>50 x 65 cm (€205.00) (€174.25)</label><label>60 x 80 cm (€260.00) (€221.00)</label></div>','https://luxart.com/paveikslai/r-du-drugeliai-2011/')
        self.assertEqual(p['variants'][0]['price'],174.25)
        self.assertEqual(p['variants'][1]['size'],[60,80])
