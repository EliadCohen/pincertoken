#!/usr/bin/env python
import pyotp
import pyperclip
import rumps


class PincerToken(object):
    def __init__(self, secret, prefix=""):
        self.secret = secret
        self.prefix = prefix
        self.app = rumps.App("PincerToken", "🦀")
        self.config = {
            "app_name": "PincerToken",
            "action": "Generate pin/token",
             }
        self.app = rumps.App(self.config["app_name"])
        self.generate_button = rumps.MenuItem(title=self.config["action"], callback=self.pintoken)
        self.app.menu = [self.generate_button]
        self.app.title = "🦀"

    def get_totp(self):
        totp = pyotp.TOTP(self.secret)
        try:
            res = totp.now()
            return res
        except:
            print("Illegal secrets key")

    def pintoken(self, sender):
        pin_token = self.prefix + self.get_totp()
        pyperclip.copy(pin_token)

    def run(self):
        self.app.run()

if __name__ == '__main__':
    app = PincerToken(secret="YOUR CHALLENGE KEY HERE", prefix="SOMETHING TO APPEND TO THE OTP")
    app.run()
