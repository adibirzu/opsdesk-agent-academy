"""Learner route and publication privacy regression checks."""
from html.parser import HTMLParser
from pathlib import Path
import importlib.util
import unittest
ROOT=Path(__file__).resolve().parents[1]
C=ROOT/'workshops/app-first'
class Navigation(HTMLParser):
    def __init__(self): super().__init__(); self.in_nav=False; self.links=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='nav' and a.get('aria-label')=='Course navigation': self.in_nav=True
        if self.in_nav and tag=='a': self.links.append(a.get('href'))
    def handle_endtag(self,tag):
        if tag=='nav': self.in_nav=False
class OciRouteTests(unittest.TestCase):
    def test_first_navigation_choice_is_oci_across_course_pages(self):
        for name in ('index.html','course.html','present.html','lovable.html','build-on-oci.html','part-6-ready-for-oci.html'):
            parser=Navigation(); parser.feed((C/name).read_text())
            self.assertEqual(parser.links[0],'build-on-oci.html',name)
    def test_export_does_not_ship_portrait_or_qr_assets(self):
        spec=importlib.util.spec_from_file_location('oci_export',ROOT/'scripts/build_student_site.py')
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        self.assertTrue({'build-on-oci.html','BUILD-ON-OCI.md'} <= set(m.FILES))
        for name in m.FILES:
            self.assertNotIn('-qr.',name)
            self.assertNotIn('presenter-linkedin',name)
            if name.endswith('.html'):
                text=(C/name).read_text()
                self.assertNotIn('-qr.svg',text,name)
                self.assertNotIn('presenter-linkedin',text,name)
        cover=(C/'present.html').read_text().split('id="welcome"',1)[1].split('</section>',1)[0]
        self.assertNotIn('linkedin.com',cover)
        self.assertNotIn('Adrian Birzu',cover)
        self.assertIn('github.com/adibirzu/opsdesk-agent-academy',cover)
    def test_route_keeps_deployment_and_telemetry_acceptance_separate(self):
        page=(C/'build-on-oci.html').read_text()
        for term in ('Responses API','hosted applications','OCI APM','Log Analytics','Langfuse','approval_required','live acceptance','BUILD-ON-OCI.md'):
            self.assertIn(term,page)
        self.assertIn('does not deploy resources or send model requests',page)
        self.assertIn('Agent instructions',(C/'BUILD-ON-OCI.md').read_text().replace('agent instructions','Agent instructions'))
