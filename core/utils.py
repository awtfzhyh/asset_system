from io import BytesIO
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
import re

def render_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html = template.render(context_dict)
    
    # NEW: This removes extra spaces and newlines that cause the TypeError 
    # "expected str instance, list found"
    html = re.sub(r'>\s+<', '><', html).strip()

    result = BytesIO()
    # We use "latin-1" here as it's often more stable for reportlab
    pdf = pisa.pisaDocument(BytesIO(html.encode("utf-8")), result)
    
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return HttpResponse(f"Error generating PDF: {pdf.err}", status=500)