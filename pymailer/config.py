import logging
import re
import ast
import ssl

_log = logging.getLogger(__name__)


class Config(object):

    DEFAULTS = {
        "host": "smtp.example.com",
        "port": 25,
        "username": "username",
        "domain": "example.com",
        "password": "password",
        "display_name": "Test User",
        "log_level": logging.ERROR,
        "dbg_folder": "./output",
        "dry_run": False,
    }

    def __init__(self):
        for key, value in self.DEFAULTS.items():
            setattr(self, key, value)
        self.ssl_context = ssl.create_default_context()

    @property
    def email(self):
        return f"{self.username}@{self.domain}"

    @property
    def from_mailbox(self):
        if self.display_name is None or len(self.display_name) == 0:
            return self.email
        return f"{self.display_name} <{self.email}>"

    def load(self, cfg_file):
        valid_keys = self.DEFAULTS.keys()
        try:
            f = open(cfg_file, "r")
            _log.debug(f"Loading config file '{cfg_file}' ...")
            self.filename = cfg_file
            for line in f:
                match = re.match("^\s*#", line)
                if match:
                    continue
                match = re.match("([^=]+)=(.*)", line)
                if match:
                    key = match.group(1).strip()
                    raw_value = match.group(2).strip()
                    try:
                        value = ast.literal_eval(raw_value)
                    except:
                        _log.warn(f"Invalid value '{raw_value}' for {key}!")
                        continue
                    if key in valid_keys:
                        _log.debug(f"Found config: {key} = '{value}'")
                        setattr(self, key, value)
                    else:
                        _log.warn(f"Unknown config parameter: {key}!")
            f.close()
            self._loaded = True
        except IOError as e:
            _log.warn(f"Could not open config file '{cfg_file}'!")
            self.filename = None