"""Verify the project's actual distributable resources and archive rejection."""
from pathlib import Path
import io
import tarfile
import tempfile
import unittest
from utils.skill_project_toolkit import validate, extract_archive


class ArtifactContract(unittest.TestCase):
    def test_project_distribution_contract(self):
        result = validate(Path(__file__).resolve().parents[1])
        self.assertTrue(result['ready'], result['errors'])

    def test_archive_cannot_write_outside_staging(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / 'bad.tgz'
            with tarfile.open(archive, 'w:gz') as bundle:
                item = tarfile.TarInfo('package/../../escape')
                item.size = 1
                bundle.addfile(item, io.BytesIO(b'x'))
            with self.assertRaises(ValueError):
                extract_archive(archive, root / 'stage')
            self.assertFalse((root / 'escape').exists())


if __name__ == '__main__':
    unittest.main()
