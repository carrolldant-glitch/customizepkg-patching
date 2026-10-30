# Contributor: Danny (https://github.com/carrolldant-glitch) <carrolldant@gmail.com>
# Former Maintainer: Michael Duell <michael.duell@rub.de>
# Contributor: Daniel Oertwig <Daniel.Oertwig+customizepkgpatching at gmail dot com>
# SPDX-License-Identifier: GPL-2.0-only
pkgname=customizepkg-patching
pkgver=20
pkgrel=3
pkgdesc='Preview and apply reviewed local PKGBUILD patches with failure checks'
url='https://github.com/musteresel/customizepkg-patching'
license=('GPL-2.0-only')
arch=('any')
depends=('bash' 'coreutils' 'diffutils' 'patch')
checkdepends=('python' 'shellcheck')
optdepends=('vim: For using vimdiff')
provides=('customizepkg')
conflicts=('customizepkg')
source=('customizepkg-patching' 'check.py' 'README.arch' 'AUTHORS' 'COPYING')
sha256sums=('8726cb2656c1f515277acdd7f1e56d5fd3c0d7813ca5434441c8f7777f33f73a'
            '8dec9094fd3ab0e95492689c6fe313b4a034184f6d9b7a8f12fa762a2e858509'
            '1b06321514f94be3e8368369c6a01f5ba271db45b28aeae6563d5c6c4b497c7c'
            '66140fa87fd0a315e84e06f252cc2d919c97f92e1f4c481dda52c6f50ea64ab9'
            'dcc100d4161cc0b7177545ab6e47216f84857cda3843847c792a25289852dcaa')

check() {
  bash -n customizepkg-patching
  shellcheck customizepkg-patching
  python check.py "$srcdir/customizepkg-patching"
}

package() {
  install -Dm755 customizepkg-patching "$pkgdir/usr/bin/customizepkg"
  install -dm755 "$pkgdir/etc/customizepkg.d"
  install -Dm644 README.arch "$pkgdir/usr/share/doc/$pkgname/README.arch"
  install -Dm644 AUTHORS "$pkgdir/usr/share/licenses/$pkgname/AUTHORS"
  install -Dm644 COPYING "$pkgdir/usr/share/licenses/$pkgname/COPYING"
}
