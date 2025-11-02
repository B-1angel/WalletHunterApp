# buildozer.spec — tuned for GitHub Actions & KivyMD APK build
[app]

# (str) Title of your application
title = Wallet Hunter

# (str) Package name
package.name = wallethunter

# (str) Package domain (reverse domain)
package.domain = org.example

# (str) Package version
version = 1.0

# (str) Source code directory (where your main.py is)
source.dir = .

# (list) Application requirements
# remove 'python3' (not needed) and pin stable versions
requirements = kivy==2.1.0, kivymd==1.1.1, requests, mnemonic, bip32utils

# (str) Icon of the application (must point to an actual image file, e.g., .png)
icon.filename = assets/icon.png

# (str) Presplash image (optional)
presplash.filename = assets/presplash.png

# (str) Supported orientation (portrait, landscape, all)
orientation = portrait

# (int) Android API targets
android.api = 33
android.minapi = 21
android.ndk = 25b

# (list) Permissions required
android.permissions = INTERNET, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE

# (bool) Include compiled Python files
include_py = true

# (bool) Optimize PNGs
android.strip = false

# (str) Entry point file (main app)
main.py = main.py

# (str) Logcat filters to use
log_level = 2

# (bool) Copy assets to project
copy_assets = 1

# (str) Application format (APK or AAB)
package.format = apk
