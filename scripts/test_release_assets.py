import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import release_assets as release


class ReleaseAssetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.version = '1.0.7'
        self.variant = 'self-contained'
        self.source = 'a' * 40

    def fixture(self, delta=False):
        package, channel, required, delta_name = release.names(self.version, self.variant)
        for name in required:
            (self.root / name).write_bytes(b'test fixture')
        full = f'{package}-{self.version}-{channel}-full.nupkg'
        with zipfile.ZipFile(self.root / full, 'w') as archive:
            archive.writestr('fixture.nuspec', f'<package><metadata><id>{package}</id><version>{self.version}</version></metadata></package>')
            archive.writestr('lib/app/OnlyShell.exe', b'fixture')
        with zipfile.ZipFile(self.root / f'{package}-{channel}-Portable.zip', 'w') as archive:
            archive.writestr('OnlyShell.exe', b'fixture')
        names = [full]
        if delta:
            (self.root / delta_name).write_bytes(b'fixture delta')
            names.append(delta_name)
        assets = [{'PackageId': package, 'Version': self.version,
                   'Type': 'Full' if name == full else 'Delta', 'FileName': name,
                   'Size': (self.root / name).stat().st_size, 'SHA256': release.digest(self.root / name)} for name in names]
        self.feed = self.root / f'releases.{channel}.json'
        self.feed.write_text(json.dumps({'Assets': assets}), encoding='utf-8')

    def seal(self):
        release.write_manifest(self.root, self.version, self.variant, self.source)

    def verify(self):
        release.verify(self.root, self.version, self.variant, self.source)

    def test_both_channels_with_and_without_delta(self):
        for variant in release.VARIANTS:
            for delta in [False, True]:
                with self.subTest(variant=variant, delta=delta), tempfile.TemporaryDirectory() as folder:
                    self.root = Path(folder)
                    self.variant = variant
                    self.fixture(delta)
                    self.seal()
                    self.verify()

    def test_tampered_installer_rejected(self):
        self.fixture()
        self.seal()
        next(self.root.glob('OnlyShell-*-Setup.exe')).write_bytes(b'tampered')
        with self.assertRaises(ValueError):
            self.verify()

    def test_missing_installer_rejected(self):
        self.fixture()
        next(self.root.glob('OnlyShell-*-Setup.exe')).unlink()
        with self.assertRaises(ValueError):
            self.seal()

    def test_unexpected_private_file_rejected(self):
        self.fixture()
        (self.root / 'token.txt').write_text('fixture')
        with self.assertRaises(ValueError):
            self.seal()

    def test_old_or_traversing_feed_entry_rejected(self):
        for filename in ['old.nupkg', '../outside.nupkg']:
            with self.subTest(filename=filename):
                self.fixture()
                feed = json.loads(self.feed.read_text())
                feed['Assets'][0]['FileName'] = filename
                self.feed.write_text(json.dumps(feed))
                with self.assertRaises(ValueError):
                    self.seal()

    def test_wrong_feed_hash_rejected(self):
        self.fixture()
        feed = json.loads(self.feed.read_text())
        feed['Assets'][0]['SHA256'] = '0' * 64
        self.feed.write_text(json.dumps(feed))
        with self.assertRaises(ValueError):
            self.seal()

    def test_wrong_source_or_version_rejected(self):
        self.fixture()
        self.seal()
        for source, version in [('b' * 40, self.version), (self.source, '1.0.8')]:
            with self.subTest(source=source, version=version), self.assertRaises(ValueError):
                release.verify(self.root, version, self.variant, source)

    def test_duplicate_checksums_and_manifest_tamper_rejected(self):
        self.fixture()
        self.seal()
        checksum = self.root / 'SHA256SUMS.txt'
        checksum.write_text(checksum.read_text() + checksum.read_text().splitlines()[0] + '\n')
        with self.assertRaises(ValueError):
            self.verify()
        (self.root / 'RELEASE-MANIFEST.json').write_text('{}')
        with self.assertRaises((ValueError, KeyError)):
            self.verify()

    def test_existing_manifest_not_overwritten(self):
        self.fixture()
        self.seal()
        with self.assertRaises(ValueError):
            self.seal()

    def test_unsupported_version_rejected(self):
        for version in ['01.0.7', '1.0.7-rc.1', '../1.0.7']:
            with self.subTest(version=version), self.assertRaises(ValueError):
                release.names(version, self.variant)


if __name__ == '__main__':
    unittest.main()
