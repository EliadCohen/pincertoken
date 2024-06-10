# PincerToken - Lazy TOTP for mac

## How to use

Edit app.py and put it your challenge key and prefix (if you have a prefix)

```
app = PincerToken(secret="YOUR CHALLENGE KEY HERE", prefix="SOMETHING TO APPEND TO THE OTP")
```

Warning: Do not upload this file back to github, it includes your secret secrets.

install the prerequisites and build

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python setup.py py2app
```

Copy the app from `./dist/pincertoken.app` to wherever and run it

I am not responsible for any damage done from using this script

