# buildozer.spec (minimal tuned for this app)
[app]

# (str) Title of your application
title = Wallet Hunter

# (str) Package name
package.name = wallethunter

# (str) Package domain (reverse domain)
package.domain = org.example

# (str) Source code where the main.py is located
source.dir = .

# (list) Application requirements
# include kivy,kivymd,requests,mnemonic,bip32utils
requirements = python3,kivy==2.1.0,kivymd,requests,mnemonic,bip32utils

# (str) Icon of the application
icon.filename = BTCx

# (int) Target SDK (Android)
android.api = 33
android.minapi = 21
android.ndk = 25b

# (list) Permissions
android.permissions = INTERNET, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE

# (str) Presplash / orientation etc
orientation = portrait

# (bool) whether to copy assets into the project
presplash.filename = BTCx

# ensure pip installs wheels where possible
# (Other buildozer options can be customized as needed)