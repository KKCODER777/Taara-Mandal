[app]

# App identity
title = Taara Mandal
package.name = taaramandal
package.domain = org.taaramandal

# Source
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf

# Version
version = 1.0

# Entry point
entrypoint = main.py

# Requirements — these get compiled into the APK
requirements = python3,kivy==2.3.0,matplotlib,numpy,pillow

# Android settings
android.permissions = INTERNET
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a

# Orientation
orientation = portrait

# Fullscreen (0 = show status bar)
fullscreen = 0

# App icon & presplash (optional — place icon.png in project folder)
# icon.filename = %(source.dir)s/icon.png
# presplash.filename = %(source.dir)s/presplash.png
presplash.color = #0c1a45

# Android extra flags
android.enable_androidx = True

[buildozer]

# Buildozer log level (0 = error only, 2 = verbose)
log_level = 2
warn_on_root = 1
