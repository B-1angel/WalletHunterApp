# buildozer.spec (WalletHunter optimized)

[app]

# (str) Title of your application
title = Wallet Hunter

# (str) Package name
package.name = wallethunter

# (str) Package domain (reverse domain)
package.domain = org.example

# (str) Package version
version = 1.0

# (str) Source code where the main.py is located
source.dir = .

# (list) Application requirements
requirements = python3,kivy==2.1.0,kivymd,requests,mnemonic,bip32utils

# (str) Icon of the application
icon.filename = BTCx.png

# (int) Target SDK (Android)
android.api = 33
android.minapi = 21
android.ndk = 25b
android.sdk = 33

# (list) Permissions
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

# (str) Orientation
orientation = portrait

# (str) Presplash
presplash.filename = BTCx.png

# (bool) Copy assets into project
copy_assets = True

# (str) Entry point
# main.py should be at root
# main.py is default, so no need to change

# (bool) Allow fullscreen
fullscreen = 0

# (bool) Use SDL2 (recommended)
android.entrypoint = org.kivy.android.PythonActivity
