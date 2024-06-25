import logging
import os
import mimetypes


from email.message import EmailMessage
from email.utils import make_msgid
from html.parser import HTMLParser
from premailer import transform

_log = logging.getLogger(__name__)


class Email(object):

    def __init__(self, from_mailbox, to_mailbox, subject, text, html=None):
        self.em= EmailMessage()
        self.em["From"] = from_mailbox
        self.em["To"] = to_mailbox
        self.em["Subject"] = subject
        self.em.set_content(text)
        if html is not None:
            self.set_html_content(html)

    @property
    def from_mailbox(self):
        return self.em["From"]

    @property
    def to_mailbox(self):
        return self.em["To"]

    @property
    def domain(self):
        try:
            return self.em["From"].groups[0].addresses[0].domain
        except:
            _log.warn("Unable to get domain for e-mail!")
            return None

    def set_html_content(self, html):
        # Find all images in the HTML code
        img_finder = ImageFinder()
        img_finder.feed(html.data)
        # Replace external images in HTML with CID resources
        html_lines = html.data.splitlines()
        resources = []
        for img in img_finder.images:
            if img.src.startswith("data:"):
                # Do replace inline images
                continue
            # Get local image path, if possible
            img_path = os.path.join(html.root_path, img.src)
            img_path = os.path.relpath(img_path)
            # Only replace image if it exists
            if not os.path.exists(img_path):
                continue
            # Create HTML resource
            res = CidResource(img.alt, self.domain, img_path)
            resources.append(res)
            line_idx = img.html_line - 1
            orig_line = html_lines[line_idx]
            replaced_line = orig_line.replace(img.src, res.cid_src)
            html_lines[line_idx] = replaced_line
        html.data = "\n".join(html_lines)
        # Turn CSS blocks into style attributes
        html.data = transform(html.data, base_path=html.root_path,
                allow_loading_external_files=True,
                cssutils_logging_level=logging.ERROR)
        # Add HTML part to email
        self.em.add_alternative(html.data, subtype="html")
        # Add related Resources to email
        for i, res in enumerate(resources):
            with open(res.path, "rb") as f:
                maintype, subtype = mimetypes.guess_type(f.name)[0].split("/")
                self.em.get_payload()[1].add_related(f.read(),
                        maintype=maintype, subtype=subtype,
                        filename=res.name, cid=res.cid)

    def send(self, smtp_server):
        smtp_server.send_message(self.em)

    def get_data(self):
        return self.em.as_string()


    class Html(object):

        def __init__(self, data, root_path):
            self.data = data
            self.root_path = root_path


    class Error(Exception):
        pass


class ImageFinder(HTMLParser):

    def __init__(self):
        super().__init__()
        self.images = []

    def handle_starttag(self, tag, attrs):
        if tag != "img":
            return
        image = self.Image(*self.getpos())
        for key, value in attrs:
            if key == "src":
                image.src = value
            elif key == "alt":
                image.alt = value
        if image.src is not None:
            self.images.append(image)


    class Image(object):

        def __init__(self, line, pos):
            self.html_line = line
            self.html_pos = pos
            self.src = None
            self.alt = "Image"


class CidResource(object):

    def __init__(self, name, domain, path):
        self.name = name
        self.cid = make_msgid(domain=domain)
        self.path = path
    
    @property
    def cid_src(self):
        return "cid:%s" % self.cid[1:-1]