# AUR packaging

This directory contains a PKGBUILD that repackages the prebuilt AppImage as an
Arch Linux package (`tiptoi-manager-linux-bin`).

## Publish steps

1. **Make the repository public.** AUR build bots and users download from the
   URLs in `source=`, so a private GitHub repository cannot be built or verified.

2. **Create an AUR account** at https://aur.archlinux.org/register and add your
   SSH public key (AUR pushes over SSH via `ssh://aur@aur.archlinux.org/…`).

3. **Check the name is free**: https://aur.archlinux.org/packages?K=tiptoi

4. Clone an empty AUR repo, add the PKGBUILD and generate `.SRCINFO`:

   ```
   git clone ssh://aur@aur.archlinux.org/tiptoi-manager-linux-bin.git
   cd tiptoi-manager-linux-bin
   cp /path/to/tip/toi_manager_linux/contrib/aur/PKGBUILD .
   makepkg --printsrcinfo > .SRCINFO
   ```

5. Test it before pushing:

   ```
   makepkg -sif                 # build + install locally
   namcap PKGBUILD *.pkg.tar.zst
   # ideally in a clean chroot:  extra-x86_64-build  (from devtools)
   ```

6. Push:

   ```
   git add PKGBUILD .SRCINFO
   git commit -m "tiptoi-manager-linux-bin 0.1.4"
   git push origin master
   ```

## Updating to a new release

Bump `pkgver`/`pkgrel`, update the `sha256sums` entry (the AppImage hash from
the release's `SHA256SUMS`), set `SHA256SUMS`' entry back to `SKIP`, regenerate
`.SRCINFO` (`makepkg --printsrcinfo > .SRCINFO`), and push.

## Notes

- A `-git` variant (build from `main` with `pip`) is possible once the repo is
  public, but the `-bin` package above is the most faithful way to ship what the
  release pipeline produces.
- The versioned artifact is `x86_64` only (the bundled Python AppImage base is
  x86_64).