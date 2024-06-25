import logging
import os
import re
import ast
import pandoc

from string import Template

_log = logging.getLogger(__name__)


class Stitcher(object):

    FORMATS = {
        "plain": { "suffix": ".txt" },
        "html": { "suffix": ".html" }
    }

    def __init__(self, body, template_path="./"):
        self.body = body
        self.tmpl_path = template_path
        self.subject = None

    def parse_subject(self):
        for line in self.body.splitlines():
            if match := re.match(r"^#\s+(.+)\s*$", line):
                self.subject = match.group(1)
                break
        return self.subject

    def get_subject(self):
        if self.subject is None:
            self.parse_subject()
        return self.subject

    def convert(self, format, source):
        if len(source.strip()) == 0:
            return ""
        doc = pandoc.read(source)
        return pandoc.write(doc, format=format)

    def get_template(self, format, name, mapping={}):
        _log.debug(f"format: {format}, name: {name}, mapping: {mapping}")
        format_info = self.FORMATS.get(format)
        if format_info is None:
            return None
        tmpl_fname = f'{name}{format_info["suffix"]}'
        tmpl_path = os.path.join(self.tmpl_path, format, tmpl_fname)
        try:
            tmpl = open(tmpl_path, "r")
        except Exception as err:
            _log.error(err)
            return None
        t = Template(tmpl.read())
        tmpl.close()
        return t.safe_substitute(mapping)

    def stitch(self, format, suppress_subject=True):
        result = ""
        md_buffer = ""
        subject = False
        for line in self.body.splitlines():
            if match := re.match(r"^\s*\[([\w_-]+)\]:\s*<(.*)>\s*$", line):
                result += self.convert(format, md_buffer)
                md_buffer = ""
                # Process template
                tmpl_name = match.group(1)
                mapping = ast.literal_eval("{" + match.group(2) + "}")
                text = self.get_template(format, tmpl_name, mapping)
                if text is not None:
                    result += text
                else:
                    _log.warn(f"Template '{tmpl_name}' ({format}) not found!")
            elif not subject and (match := re.match(r"^#\s+(.+)\s*$", line)):
                self.subject = match.group(1)
                if not suppress_subject:
                    md_buffer += line + "\n"
                subject = True
            else:
                md_buffer += line + "\n"
        result += self.convert(format, md_buffer)
        return result