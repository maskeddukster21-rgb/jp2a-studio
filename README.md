# jp2a Studio

A live, sleek local GUI for [`jp2a`](https://github.com/Talinx/jp2a), the JPEG/PNG/WebP-to-ASCII-art
converter. Drop in an image, paste one from your clipboard, or fetch one from a URL, then tweak
width, color, edges, borders and character palettes with instant feedback — every render is real
`jp2a` output, not a reimplementation.

It runs as a tiny local web server (pure Python standard library) that opens in your browser, so
it works the same way on Linux, WSL, and Windows without needing a GUI toolkit installed.

## Install

### Linux / WSL (Debian, Ubuntu)

Download the latest `.deb` from [Releases](../../releases), then:

```sh
sudo apt install ./jp2a-studio_*.deb
```

`jp2a` and Pillow are pulled in automatically as package dependencies. Launch it from your
applications menu, or:

```sh
jp2a-studio
```

### Linux / WSL (any distro)

For Arch, Fedora, or anything else without `.deb` support, use the install script instead — it
detects your package manager, installs `jp2a` if needed, and drops a `jp2a-studio` launcher in
`~/.local/bin`:

```sh
curl -fsSL https://raw.githubusercontent.com/maskeddukster21-rgb/jp2a-studio/main/scripts/install.sh | bash
```

### Windows

Download `jp2a-studio-<version>-windows-setup.exe` from [Releases](../../releases) and run it —
it bundles a cross-compiled `jp2a.exe`, so there's nothing else to install. A portable
`jp2a-studio-<version>-windows-portable.zip` (no installer, just unzip and run) is also published
alongside it.

## Building from source

```sh
git clone https://github.com/maskeddukster21-rgb/jp2a-studio.git
cd jp2a-studio
python3 app/server.py
```

Requires `jp2a` on your `PATH` and, optionally, Pillow (`pip install pillow`) for broader image
format support beyond jpg/png/webp.

To build the `.deb` yourself:

```sh
packaging/linux/build-deb.sh 1.0.0
```

The Windows installer is built in CI (see `.github/workflows/release.yml`) by cross-compiling
`jp2a` from source with MSYS2/mingw-w64, then bundling it with a PyInstaller build of the app via
Inno Setup. Pushing a tag like `v1.0.0` triggers that pipeline and publishes a GitHub Release with
the `.deb`, the Windows installer, and the portable `.zip` attached.

## How it works

- The backend (`app/server.py`) is a plain `http.server` app — no pip installs required to run it
  from source. It normalizes any image Pillow can decode into a PNG, shells out to `jp2a` with a
  small, validated set of arguments (no shell interpolation), and returns the result as plain text
  or as `jp2a`'s own `--html-raw --colors` output.
- The frontend (`app/static/`) is hand-written HTML/CSS/JS — a dark, glassmorphism control panel
  that debounces every change and re-renders live.

## License

The jp2a Studio code in this repository is MIT-licensed — see [LICENSE](LICENSE). It depends on
the separate `jp2a` binary (GPL-2.0, https://github.com/Talinx/jp2a); the Linux `.deb` installs it
via your package manager, and the Windows installer bundles a binary built from jp2a's own public
source.
