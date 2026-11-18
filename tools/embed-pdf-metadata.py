"""Embed invisible, machine-readable metadata into an exported resume PDF.

Nothing here changes how the PDF looks. It adds:
  * Document Info fields (Title, Author, Subject, Keywords)
  * An XMP metadata packet (dc:title / creator / description / subject)
  * /Lang and DisplayDocTitle (accessibility + parsers)
  * The page's JSON-LD attached as an embedded file (resume.jsonld)

All values come from the <head> of the source HTML (meta tags and the
JSON-LD block), so the PDF always mirrors the visible resume.

Usage:
    pip install pypdf
    python tools/embed-pdf-metadata.py v3-2026.11.18.html "in.pdf" "out.pdf"

Export tip: print to PDF from Chrome/Edge with "Background graphics" on, so the
cosmetics match the screen, and leave the default tagged PDF behavior alone
(headings and lists in the HTML become structure tags in the PDF).
"""
import html
import json
import re
import sys

from pypdf import PdfReader, PdfWriter
from pypdf.generic import (BooleanObject, DecodedStreamObject, DictionaryObject,
                           NameObject, TextStringObject)

html_path, pdf_in, pdf_out = sys.argv[1:4]
page = open(html_path, encoding="utf-8").read()


def meta(name):
    m = re.search(r'<meta name="%s" content="([^"]*)"' % name, page)
    return html.unescape(m.group(1)) if m else ""


title = html.unescape(re.search(r"<title>(.*?)</title>", page, re.S).group(1)).strip()
ld_raw = re.search(r'<script type="application/ld\+json">(.*?)</script>', page, re.S).group(1)
ld = json.loads(ld_raw)
author = meta("author") or ld["name"]
subject = meta("description")
keywords = meta("keywords")

writer = PdfWriter(clone_from=PdfReader(pdf_in))
writer.add_metadata({
    "/Title": title,
    "/Author": author,
    "/Subject": subject,
    "/Keywords": keywords,
})

esc = lambda s: html.escape(s, quote=False)
xmp = f"""<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about="" xmlns:dc="http://purl.org/dc/elements/1.1/">
   <dc:title><rdf:Alt><rdf:li xml:lang="x-default">{esc(title)}</rdf:li></rdf:Alt></dc:title>
   <dc:creator><rdf:Seq><rdf:li>{esc(author)}</rdf:li></rdf:Seq></dc:creator>
   <dc:description><rdf:Alt><rdf:li xml:lang="x-default">{esc(subject)}</rdf:li></rdf:Alt></dc:description>
   <dc:subject><rdf:Bag>{''.join(f'<rdf:li>{esc(k.strip())}</rdf:li>' for k in keywords.split(',') if k.strip())}</rdf:Bag></dc:subject>
   <dc:language><rdf:Bag><rdf:li>en-US</rdf:li></rdf:Bag></dc:language>
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>"""
stream = DecodedStreamObject()
stream.set_data(xmp.encode("utf-8"))
stream.update({
    NameObject("/Type"): NameObject("/Metadata"),
    NameObject("/Subtype"): NameObject("/XML"),
})
root = writer._root_object
root[NameObject("/Metadata")] = writer._add_object(stream)
root[NameObject("/Lang")] = TextStringObject("en-US")
prefs = DictionaryObject({NameObject("/DisplayDocTitle"): BooleanObject(True)})
root[NameObject("/ViewerPreferences")] = prefs

writer.add_attachment("resume.jsonld", json.dumps(ld, indent=2, ensure_ascii=False).encode("utf-8"))

with open(pdf_out, "wb") as f:
    writer.write(f)
print("wrote", pdf_out)
