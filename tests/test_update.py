"""Run with: python -m unittest discover -s tests -v"""
import importlib.util
from pathlib import Path
import unittest
from xml.etree import ElementTree as ET

p=Path(__file__).resolve().parents[1]/'scripts/update.py'
spec=importlib.util.spec_from_file_location('vicewire_updater',p)
u=importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)

class SourceTests(unittest.TestCase):
    def sample(self, source='PC Gamer', url='https://www.pcgamer.com'):
        return f'''<rss><channel><item><title>Cyberleek GTA VI files claim - {source}</title>
        <link>https://news.google.com/rss/articles/ABCD</link>
        <pubDate>Sun, 22 Nov 2026 09:00:00 GMT</pubDate>
        <source url="{url}">{source}</source></item></channel></rss>'''.encode()

    def test_coverage_is_not_official_even_if_category_is_official(self):
        r=u.read_google_rss(self.sample(),['official','piracy'])
        self.assertEqual(r[0]['credibility'],'coverage')
        self.assertIn('official',r[0]['categories'])
        self.assertIn('Why', 'Why')
        self.assertTrue(r[0]['why_it_matters'])

    def test_only_x_publisher_gets_social_label(self):
        self.assertEqual(u.read_google_rss(self.sample(),['social'],'x-index'),[])
        r=u.read_google_rss(self.sample('X','https://x.com'),['social'],'x-index')
        self.assertEqual(r[0]['credibility'],'social')

    def test_blocks_download_ads(self):
        src=self.sample().replace(b'Cyberleek GTA VI files claim', b'GTA VI free download now')
        self.assertEqual(u.read_google_rss(src,['piracy']),[])

    def test_feed_is_valid_xml(self):
        articles=u.read_google_rss(self.sample(),['piracy'])
        self.assertEqual(ET.fromstring(u.build_feed(articles)).tag,'rss')

if __name__=='__main__':unittest.main()
