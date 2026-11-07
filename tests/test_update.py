"""The update button: version check, download and install. The network is simulated."""
import ast
import hashlib
import io
import json
import os
import shutil
import socket
import sys
import tempfile
import unittest
import urllib.error
import zipfile
from unittest import mock

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
os.environ["TTA_LANG"] = "es"

import tasktriggerantitrack as tta  # noqa: E402
import tta_lang  # noqa: E402
import tta_update as up  # noqa: E402

API = up.API_LATEST
ZIPBALL = "https://api.github.com/repos/javimentallab/TaskTriggerAntitrack/zipball/v1.1.0"
ASSET_BASE = "https://github.com/javimentallab/TaskTriggerAntitrack/releases/download/v1.1.0/"


# ---- a fake network --------------------------------------------------------------
class FakeResponse(io.BytesIO):
    def __init__(self, body, url, length=True):
        super().__init__(body)
        self._url = url
        self.headers = {"Content-Length": str(len(body))} if length else {}

    def geturl(self):
        return self._url


class FakeOpener:
    """Answers each URL with bytes, or raises what it is given. Records every request."""
    def __init__(self, routes):
        self.routes = routes
        self.requests = []

    def open(self, req, timeout=None):
        self.requests.append((req.full_url, dict(req.header_items()), timeout))
        answer = self.routes[req.full_url]
        if isinstance(answer, BaseException):
            raise answer
        return FakeResponse(answer, req.full_url)


def release_json(tag="v1.1.0", assets=None, **extra):
    data = {"tag_name": tag, "html_url": "https://github.com/javimentallab/TaskTriggerAntitrack/releases/tag/" + tag,
            "zipball_url": "https://api.github.com/repos/javimentallab/TaskTriggerAntitrack/zipball/" + tag,
            "assets": assets or []}
    data.update(extra)
    return json.dumps(data).encode()


def app_zip(files=None, prefix="javimentallab-TaskTriggerAntitrack-abc1234/"):
    files = files if files is not None else {
        "tasktriggerantitrack.py": "VERSION = '1.1.0'\n",
        "tta_lang.py": "X = 1\n",
        "tta_update.py": "Y = 2\n",
        "docs/new.txt": "new file\n",
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        if prefix:
            z.writestr(prefix, "")
        for name, text in files.items():
            z.writestr(prefix + name, text)
    return buf.getvalue()


# ---- versions --------------------------------------------------------------------
class Versions(unittest.TestCase):
    def test_semantic_order(self):
        self.assertTrue(up.is_newer("1.0.10", "1.0.9"))
        self.assertTrue(up.is_newer("v1.1", "1.0.0"))
        self.assertTrue(up.is_newer("2.0.0", "1.99.99"))
        self.assertFalse(up.is_newer("1.0.9", "1.0.10"))

    def test_same_version_is_not_newer(self):
        self.assertFalse(up.is_newer("v1.0.0", "1.0.0"))
        self.assertFalse(up.is_newer("1.0", "1.0.0"))

    def test_release_beats_its_pre_releases(self):
        self.assertTrue(up.is_newer("1.0.0", "1.0.0-rc.1"))
        self.assertTrue(up.is_newer("1.0.0-rc.2", "1.0.0-rc.1"))
        self.assertTrue(up.is_newer("1.0.0-rc.1", "1.0.0-beta"))
        self.assertFalse(up.is_newer("1.0.0-rc.1", "1.0.0"))

    def test_nonsense_is_never_newer(self):
        for bad in ("", None, "latest", "1.x", 5):
            self.assertIsNone(up.parse_version(bad))
            self.assertFalse(up.is_newer(bad, "1.0.0"))

    def test_app_version_is_valid(self):
        self.assertIsNotNone(up.parse_version(tta.__version__))


# ---- checking ----------------------------------------------------------------------
class Checking(unittest.TestCase):
    def test_source_archive_when_nothing_is_attached(self):
        net = FakeOpener({API: release_json()})
        rel = up.latest_release("1.0.0", opener=net)
        self.assertEqual((rel.version, rel.archive_url, rel.sha256), ("1.1.0", ZIPBALL, None))
        self.assertEqual(rel.archive_name, "TaskTriggerAntitrack-1.1.0.zip")

    def test_only_a_generic_user_agent_is_sent(self):
        net = FakeOpener({API: release_json()})
        up.latest_release("1.0.0", opener=net)
        [(url, headers, timeout)] = net.requests
        self.assertEqual(url, "https://api.github.com/repos/javimentallab/TaskTriggerAntitrack/releases/latest")
        self.assertEqual(headers["User-agent"], "TaskTriggerAntitrack-updater/1.0.0")
        self.assertEqual(set(headers), {"User-agent", "Accept"})
        self.assertLessEqual(timeout, 10)

    def test_attached_zip_with_its_digest(self):
        digest = "ab" * 32
        assets = [{"name": "TaskTriggerAntitrack-1.1.0.zip", "digest": "sha256:" + digest,
                   "browser_download_url": ASSET_BASE + "TaskTriggerAntitrack-1.1.0.zip"}]
        rel = up.latest_release("1.0.0", opener=FakeOpener({API: release_json(assets=assets)}))
        self.assertEqual(rel.archive_url, ASSET_BASE + "TaskTriggerAntitrack-1.1.0.zip")
        self.assertEqual(rel.sha256, digest)

    def test_attached_zip_with_a_sums_file(self):
        digest = "cd" * 32
        assets = [{"name": "TaskTriggerAntitrack-1.1.0.zip",
                   "browser_download_url": ASSET_BASE + "TaskTriggerAntitrack-1.1.0.zip"},
                  {"name": "SHA256SUMS", "browser_download_url": ASSET_BASE + "SHA256SUMS"}]
        net = FakeOpener({API: release_json(assets=assets),
                          ASSET_BASE + "SHA256SUMS": ("%s  TaskTriggerAntitrack-1.1.0.zip\n" % digest).encode()})
        self.assertEqual(up.latest_release("1.0.0", opener=net).sha256, digest)

    def test_files_from_somewhere_else_are_ignored(self):
        assets = [{"name": "evil.zip", "browser_download_url": "https://github.com/someone/else/releases/download/v1/evil.zip"}]
        rel = up.latest_release("1.0.0", opener=FakeOpener({API: release_json(assets=assets)}))
        self.assertEqual(rel.archive_url, ZIPBALL)

    def test_odd_page_link_falls_back_to_the_releases_page(self):
        rel = up.parse_release(json.loads(release_json(html_url="https://example.com/x")))
        self.assertEqual(rel.page, up.RELEASES_PAGE)

    def test_errors(self):
        cases = [
            (urllib.error.HTTPError(API, 403, "rate limit", {}, None), "http"),
            (urllib.error.URLError(socket.timeout("timed out")), "timeout"),
            (socket.timeout("timed out"), "timeout"),
            (urllib.error.URLError("getaddrinfo failed"), "network"),
            (ConnectionResetError(), "network"),
        ]
        for exc, kind in cases:
            with self.assertRaises(up.UpdateError) as cm:
                up.latest_release("1.0.0", opener=FakeOpener({API: exc}))
            self.assertEqual(cm.exception.kind, kind, exc)

    def test_http_error_keeps_its_code(self):
        with self.assertRaises(up.UpdateError) as cm:
            up.latest_release("1.0.0", opener=FakeOpener({API: urllib.error.HTTPError(API, 404, "x", {}, None)}))
        self.assertEqual(cm.exception.detail, "404")

    def test_bad_answers(self):
        for body in (b"<html>", b"[]", json.dumps({"tag_name": "latest"}).encode(),
                     json.dumps({"tag_name": "v1.1.0", "zipball_url": "https://example.com/z"}).encode()):
            with self.assertRaises(up.UpdateError) as cm:
                up.latest_release("1.0.0", opener=FakeOpener({API: body}))
            self.assertEqual(cm.exception.kind, "bad_response", body)

    def test_only_https_to_github(self):
        for url in ("http://api.github.com/x", "https://example.com/x", "https://github.com.evil.net/x", "file:///c:/x"):
            with self.assertRaises(up.UpdateError):
                up.check_url(url)
        up.check_url("https://codeload.github.com/x")

    def test_redirect_away_from_github_is_refused(self):
        h = up._GitHubOnlyRedirect()
        req = mock.Mock()
        with self.assertRaises(up.UpdateError):
            h.redirect_request(req, None, 302, "Found", {}, "https://example.com/evil.zip")

    def test_sums_file_formats(self):
        h = "ef" * 32
        self.assertEqual(up.sha_from_sums("%s *a.zip\n%s  b.zip" % ("00" * 32, h), "b.zip"), h)
        self.assertEqual(up.sha_from_sums(h.upper() + "\n", "a.zip"), h)
        self.assertIsNone(up.sha_from_sums("%s  other.zip\n%s  more.zip" % (h, h), "a.zip"))


# ---- downloading -------------------------------------------------------------------
class Downloading(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)

    def rel(self, sha=None):
        return up.Release("v1.1.0", "1.1.0", up.RELEASES_PAGE, ZIPBALL, "TaskTriggerAntitrack-1.1.0.zip", sha, None)

    def test_good_checksum(self):
        body = app_zip()
        path = up.download(self.rel(hashlib.sha256(body).hexdigest()), self.dir, "1.0.0",
                           opener=FakeOpener({ZIPBALL: body}))
        with open(path, "rb") as f:
            self.assertEqual(f.read(), body)

    def test_accept_header_suits_each_kind_of_file(self):
        """GitHub's API answers 415 to 'octet-stream' for the source archive (seen for real)."""
        net = FakeOpener({ZIPBALL: app_zip(), ASSET_BASE + "a.zip": app_zip()})
        up.download(self.rel(), self.dir, "1.0.0", opener=net)
        up.download(self.rel()._replace(archive_url=ASSET_BASE + "a.zip", archive_name="a.zip"),
                    self.dir, "1.0.0", opener=net)
        self.assertEqual([h["Accept"] for _u, h, _t in net.requests],
                         ["application/vnd.github+json", "application/octet-stream"])

    def test_wrong_checksum_leaves_nothing(self):
        with self.assertRaises(up.UpdateError) as cm:
            up.download(self.rel("00" * 32), self.dir, "1.0.0", opener=FakeOpener({ZIPBALL: app_zip()}))
        self.assertEqual(cm.exception.kind, "checksum")
        self.assertEqual(os.listdir(self.dir), [])

    def test_not_the_app(self):
        for body in (b"not a zip", app_zip({"README.md": "hello"})):
            with self.assertRaises(up.UpdateError) as cm:
                up.download(self.rel(), self.dir, "1.0.0", opener=FakeOpener({ZIPBALL: body}))
            self.assertEqual(cm.exception.kind, "bad_archive")
        self.assertEqual(os.listdir(self.dir), [])

    def test_too_big(self):
        with mock.patch.object(up, "MAX_ARCHIVE", 100):
            with self.assertRaises(up.UpdateError) as cm:
                up.download(self.rel(), self.dir, "1.0.0", opener=FakeOpener({ZIPBALL: b"x" * 200}))
        self.assertEqual(cm.exception.kind, "too_big")


# ---- installing --------------------------------------------------------------------
class Installing(unittest.TestCase):
    OLD = {"tasktriggerantitrack.py": "VERSION = '1.0.0'\n", "tta_lang.py": "X = 0\n",
           "alarms.json": '[{"name": "mine"}]', "error.log": "old log\n",
           "alarm_sound.wav": "MY OWN SOUND", "alarms.json.corrupto-20261101-000000": "kept"}

    def setUp(self):
        self.app = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.app, True)
        for name, text in self.OLD.items():
            with open(os.path.join(self.app, name), "w", encoding="utf-8") as f:
                f.write(text)

    def zip_file(self, files=None, **kw):
        path = os.path.join(tempfile.mkdtemp(), "new.zip")
        self.addCleanup(shutil.rmtree, os.path.dirname(path), True)
        with open(path, "wb") as f:
            f.write(app_zip(files, **kw))
        return path

    def read(self, *parts):
        with open(os.path.join(self.app, *parts), encoding="utf-8") as f:
            return f.read()

    def test_replaces_the_app_and_keeps_the_user_files(self):
        files = {"tasktriggerantitrack.py": "VERSION = '1.1.0'\n", "tta_lang.py": "X = 1\n",
                 "docs/new.txt": "new\n", "alarms.json": "[]", "error.log": "", "alarm_sound.wav": "THEIRS"}
        backup = up.install(self.zip_file(files), self.app, "1.0.0")
        self.assertEqual(self.read("tasktriggerantitrack.py"), "VERSION = '1.1.0'\n")
        self.assertEqual(self.read("docs", "new.txt"), "new\n")
        for name in ("alarms.json", "error.log", "alarm_sound.wav", "alarms.json.corrupto-20261101-000000"):
            self.assertEqual(self.read(name), self.OLD[name], name)
        self.assertTrue(os.path.basename(backup).startswith(".tta-backup-1.0.0-"))
        with open(os.path.join(backup, "tasktriggerantitrack.py"), encoding="utf-8") as f:
            self.assertEqual(f.read(), self.OLD["tasktriggerantitrack.py"])
        self.assertFalse([d for d in os.listdir(self.app) if d.startswith(".tta-update-")])

    def test_sound_comes_with_the_update_if_there_was_none(self):
        os.remove(os.path.join(self.app, "alarm_sound.wav"))
        files = {"tasktriggerantitrack.py": "A = 1\n", "tta_lang.py": "B = 1\n", "alarm_sound.wav": "NEW"}
        up.install(self.zip_file(files), self.app, "1.0.0")
        self.assertEqual(self.read("alarm_sound.wav"), "NEW")

    def test_archive_without_top_folder(self):
        up.install(self.zip_file(prefix=""), self.app, "1.0.0")
        self.assertEqual(self.read("tta_lang.py"), "X = 1\n")

    def test_broken_code_changes_nothing(self):
        files = {"tasktriggerantitrack.py": "def (:\n", "tta_lang.py": "X = 1\n"}
        with self.assertRaises(up.UpdateError) as cm:
            up.install(self.zip_file(files), self.app, "1.0.0")
        self.assertEqual(cm.exception.kind, "bad_archive")
        self.assertEqual(self.read("tasktriggerantitrack.py"), self.OLD["tasktriggerantitrack.py"])

    def test_paths_outside_the_folder_are_refused(self):
        for bad in ("../evil.py", "a/../../evil.py", "C:/evil.py", "a\\..\\evil.py"):
            files = {"tasktriggerantitrack.py": "A = 1\n", "tta_lang.py": "B = 1\n", bad: "boom"}
            with self.assertRaises(up.UpdateError, msg=bad):
                up.install(self.zip_file(files, prefix=""), self.app, "1.0.0")
        self.assertEqual(self.read("tta_lang.py"), self.OLD["tta_lang.py"])

    def test_failure_halfway_puts_everything_back(self):
        real = os.replace
        calls = []

        def flaky(src, dst):
            calls.append(dst)
            if len(calls) == 2:
                raise PermissionError("in use")
            return real(src, dst)

        with mock.patch.object(up.os, "replace", flaky):
            with self.assertRaises(up.UpdateError) as cm:
                up.install(self.zip_file(), self.app, "1.0.0")
        self.assertEqual(cm.exception.kind, "write")
        self.assertEqual(self.read("tasktriggerantitrack.py"), self.OLD["tasktriggerantitrack.py"])
        self.assertEqual(self.read("tta_lang.py"), self.OLD["tta_lang.py"])
        self.assertFalse(os.path.exists(os.path.join(self.app, "docs", "new.txt")))

    def test_where_it_can_install(self):
        self.assertIsNone(up.cannot_install_here(self.app))
        with mock.patch.object(up.tempfile, "mkstemp", side_effect=PermissionError()):
            self.assertEqual(up.cannot_install_here(self.app), "readonly")
        os.mkdir(os.path.join(self.app, ".git"))
        self.assertEqual(up.cannot_install_here(self.app), "git")

    def test_git_worktree_counts_as_git(self):
        with open(os.path.join(self.app, ".git"), "w") as f:
            f.write("gitdir: elsewhere\n")
        self.assertEqual(up.cannot_install_here(self.app), "git")


# ---- texts -------------------------------------------------------------------------
class Texts(unittest.TestCase):
    def test_every_update_text_is_translated(self):
        used = list(tta.App._UPD_ERRORS.values()) + list(tta.App._UPD_WHY.values())
        with open(os.path.join(HERE, "tasktriggerantitrack.py"), encoding="utf-8") as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "_" and node.args \
                    and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                used.append(node.args[0].value)
            if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "_upd_thread":
                used.append(node.args[2].value)
        missing = [t for t in used if t not in tta_lang.SOURCE]
        self.assertEqual(missing, [])

    def test_update_texts_fit_in_the_header(self):
        """Title, version and the button (in each of its three texts) fit in the narrowest window."""
        try:
            import tkinter as tk
            from tkinter import font
            root = tk.Tk()
        except Exception as e:      # no display (a Linux CI runner, for instance)
            self.skipTest("no Tk: %s" % e)
        try:
            root.withdraw()
            root.tk.call("tk", "scaling", 96 / 72)      # 100 % scaling, like px()
            title = font.Font(root, family="Segoe UI Semibold", size=15).measure("TaskTriggerAntitrack")
            ver = font.Font(root, family="Segoe UI", size=9).measure(tta.__version__) + 8
            btn = font.Font(root, family="Segoe UI", size=11)
            room = 580 - 18 - 14 - title - ver - 16          # window, margins and a gap
            for lang, table in tta_lang.TABLES.items():
                for text in ("Actualizar", "Buscando…", "Descargando…"):
                    w = btn.measure(table[text]) + 2 * 12 + 4  # Ghost.TButton padding and border
                    self.assertLessEqual(w, room, (lang, table[text], w, room))
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
