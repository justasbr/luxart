import json
import tempfile
import unittest
from pathlib import Path
from local import rebuild, bundle

class LocalTests(unittest.TestCase):
    def test_rebuild_refuses_incomplete_import(self):
        with self.assertRaises(ValueError):rebuild({'complete':False},Path('/unused'))
    def test_rebuild_missing_cache_does_not_silently_drop_product(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                rebuild({'complete':True,'products':[{'url':'https://luxart.com/paveikslai/x/'}]},Path(directory))
    def test_bundle_embeds_data_without_external_modules_or_json_script_injection(self):
        result=bundle({'products':[{'title':'</script><script>alert(1)</script>'}]})
        self.assertIn('globalThis.__CATALOG__=',result)
        self.assertNotIn('src="app.js"',result)
        self.assertNotIn("from './search.js'",result)
        self.assertNotIn('</script><script>alert(1)',result)
        self.assertIn('\\u003c/script>',result)
