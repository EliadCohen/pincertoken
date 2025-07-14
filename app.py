#!/usr/bin/env python
from ast import List
import pyotp
import pyperclip
import rumps
import yaml
import json
from typing import Any, TextIO, TypedDict
import os

class SecretKey(TypedDict):
    name: str
    secret: str
    prefix: str
    suffix: str

class PincerToken(object):
    def __init__(self, secrets_dict: SecretKey={}, prefix: str="", **kwargs):
        if "import_file" in kwargs:
            f: TextIO = open(kwargs["import_file"], "r")
            if kwargs["import_file"].endswith(".yaml") or kwargs[
                "import_file"
            ].endswith(".yml"):
                self.secrets_raw = yaml.safe_load(f)
            elif kwargs["import_file"].endswith(".json"):
                self.secrets_raw = json.loads(f)
            f.close()

            self.secrets = {}
            for secret in self.secrets_raw["secrets"]:
                self.secrets[secret["name"]] = secret

            self.app = rumps.App("PincerToken", "🦀")
            self.config = {
                "app_name": "PincerToken",
                "action": "Generate pin/token",
            }
            self.app = rumps.App(self.config["app_name"])

            for secret in self.secrets:
                generate_button = rumps.MenuItem(
                    title=f"{secret}", callback=self.pintoken
                )
                self.app.menu = [generate_button]

            self.app.title = "🦀"

        else:

            self.secret = secrets_dict
            self.prefix = prefix
            self.app = rumps.App("PincerToken", "🦀2")
            self.config = {
                "app_name": "PincerToken2",
                "action": "Generate OTP",
            }
            self.app = rumps.App(self.config["app_name"])
            self.generate_button = rumps.MenuItem(
                title=self.config["action"], callback=self.pintoken
            )
            self.app.menu = [self.generate_button]
            self.app.title = "🦀2"

    def get_totp(self, key):
        totp = pyotp.TOTP(key)
        try:
            res = totp.now()
            return res
        except:
            print("Illegal secrets key")

    def pintoken(self, sender):
        key = sender.title
        pin_token = f"{self.secrets[key]['prefix'] if 'prefix' in self.secrets[key] else ''}{self.get_totp(self.secrets[key]['secret'])}{self.secrets[key]['suffix'] if 'suffix' in self.secrets[key] else ''}"
        pyperclip.copy(pin_token)

    def run(self):
        self.app.run()


if __name__ == "__main__":
    app = PincerToken(import_file="{os.path.expanduser('~')}/secretsfile.yaml")
    app.run()
