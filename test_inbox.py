import unittest
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime

# Import the functions to be tested from inbox.py
from inbox import classificar, calcular_arquivo, destino_seguro, coletar_arquivos

class TestInbox(unittest.TestCase):
    def test_classificar(self):
        test_cases = [
            # (filename, expected_category, expected_sub)
            ("photo.jpg", "Imagens", ""),
            ("image.PNG", "Imagens", ""),
            ("vector.svg", "Imagens", ""),
            ("movie.mp4", "Videos", ""),
            ("clip.mkv", "Videos", ""),
            ("song.mp3", "Musica", ""),
            ("track.flac", "Musica", ""),
            ("script.py", "Dev", ""),
            ("styles.css", "Dev", ""),
            ("data.json", "Dev", ""),
            ("doc.pdf", "Documentos", ""),
            ("sheet.xlsx", "Documentos", ""),
            ("archive.zip", "Documentos", ""),
            # Double extensions
            ("backup.tar.gz", "Documentos", ""),
            ("bundle.tar.bz2", "Documentos", ""),
            # Unknown extensions
            ("unknown.extension", "Documentos", "Outros"),
            ("no_extension", "Documentos", "Outros"),
            # Case insensitivity
            ("PHOTO.JPEG", "Imagens", ""),
        ]

        for filename, expected_cat, expected_sub in test_cases:
            with self.subTest(filename=filename):
                cat, sub = classificar(Path(filename))
                self.assertEqual(cat, expected_cat)
                self.assertEqual(sub, expected_sub)

    def test_destino_seguro(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            nome = "test.txt"

            # Scenario 1: File doesn't exist
            dest = destino_seguro(tmp_path, nome)
            self.assertEqual(dest, tmp_path / nome)

            # Scenario 2: File exists
            (tmp_path / nome).touch()
            dest = destino_seguro(tmp_path, nome)
            self.assertEqual(dest, tmp_path / "test_(1).txt")

            # Scenario 3: Multiple files exist
            (tmp_path / "test_(1).txt").touch()
            dest = destino_seguro(tmp_path, nome)
            self.assertEqual(dest, tmp_path / "test_(2).txt")

    @patch("inbox.Path.stat")
    def test_calcular_arquivo(self, mock_stat):
        # Mock stat to return a specific mtime
        # 1704067200 is 2024-01-01 00:00:00
        mock_stat_obj = MagicMock()
        mock_stat_obj.st_mtime = 1704067200
        mock_stat.return_value = mock_stat_obj

        arq = Path("test.jpg")
        res = calcular_arquivo(arq)

        self.assertEqual(res, (arq, "Imagens", "", 2024))

    def test_coletar_arquivos(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            # Create a structure:
            # tmp/
            #  file1.txt
            #  subdir/
            #    file2.txt
            (tmp_path / "file1.txt").touch()
            subdir = tmp_path / "subdir"
            subdir.mkdir()
            (subdir / "file2.txt").touch()

            arqs = coletar_arquivos(tmp_path)

            names = {a.name for a in arqs}
            self.assertEqual(len(names), 2)
            self.assertIn("file1.txt", names)
            self.assertIn("file2.txt", names)

if __name__ == "__main__":
    unittest.main()
