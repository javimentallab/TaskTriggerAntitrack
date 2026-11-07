"""
Update check for TaskTriggerAntitrack (standard library only, no window).

Nothing here runs on its own: the app calls it only when the user presses the update
button. It asks GitHub for the latest release and compares the versions. A clean git
clone is moved to the release tag of the official repository (fast-forward only); any
other copy gets that release's archive (checking its SHA-256 when the release publishes
one), installed over the current files when the folder allows it. The user's tasks
(alarms.json), error.log and sound are never overwritten, and replaced files are backed up.

Only HTTPS to GitHub's own hosts is allowed, redirects included. The only thing sent is
a generic User-Agent with the app's version.
"""
import hashlib
import http.client
import json
import os
import re
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections import namedtuple

REPO = "javimentallab/TaskTriggerAntitrack"
API_LATEST = "https://api.github.com/repos/%s/releases/latest" % REPO
RELEASES_PAGE = "https://github.com/%s/releases/latest" % REPO
ALLOWED_HOSTS = frozenset({
    "api.github.com", "github.com", "codeload.github.com",
    "objects.githubusercontent.com", "release-assets.githubusercontent.com",
})
TIMEOUT = 8                         # seconds per connection or read
MAX_JSON = 1024 * 1024              # the release description
MAX_ARCHIVE = 20 * 1024 * 1024      # the downloaded zip
MAX_UNZIPPED = 50 * 1024 * 1024     # everything inside it
REQUIRED = ("tasktriggerantitrack.py", "tta_lang.py")
USER_FILES = ("alarms.json", "error.log")           # never overwritten
USER_FILES_IF_PRESENT = ("alarm_sound.wav",)        # the user may have put their own sound
SUMS_NAMES = ("sha256sums", "sha256sums.txt")

Release = namedtuple("Release", "tag version page archive_url archive_name sha256 sums_url")


class UpdateError(Exception):
    """kind: network, timeout, http, bad_response, checksum, bad_archive, too_big, write, git;
    and why a git clone is not updated: no_git, local_changes, not_git, diverged."""
    def __init__(self, kind, detail=""):
        super().__init__("%s: %s" % (kind, detail) if detail else kind)
        self.kind = kind
        self.detail = str(detail)


# ---- versions --------------------------------------------------------------------
_VER = re.compile(r"^[vV]?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?$")


def parse_version(text):
    """Sortable key for 'v1.2.3', '1.2' or '1.2.3-rc.1' (semantic versioning), or None."""
    m = _VER.match((text or "").strip()) if isinstance(text, str) else None
    if not m:
        return None
    nums = tuple(int(x or 0) for x in m.group(1, 2, 3))
    pre = m.group(4)
    if pre is None:                 # a release sorts after its own pre-releases
        return nums + ((1,),)
    parts = tuple((0, int(p), "") if p.isdigit() else (1, 0, p) for p in pre.split("."))
    return nums + ((0,) + parts,)


def is_newer(remote, local):
    r, l = parse_version(remote), parse_version(local)
    return bool(r and l and r > l)


# ---- network ---------------------------------------------------------------------
def check_url(url):
    p = urllib.parse.urlsplit(url or "")
    if p.scheme != "https" or (p.hostname or "").lower() not in ALLOWED_HOSTS:
        raise UpdateError("bad_response", "URL not allowed: %s" % url)


class _GitHubOnlyRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        check_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def make_opener():
    return urllib.request.build_opener(
        _GitHubOnlyRedirect(), urllib.request.HTTPSHandler(context=ssl.create_default_context()))


def _headers(version, accept):
    return {"User-Agent": "TaskTriggerAntitrack-updater/%s" % version, "Accept": accept}


def _open(url, version, accept, opener, timeout):
    """Response of a GET to GitHub, with the errors turned into UpdateError."""
    check_url(url)
    req = urllib.request.Request(url, headers=_headers(version, accept))
    try:
        r = (opener or make_opener()).open(req, timeout=timeout)
    except UpdateError:
        raise
    except urllib.error.HTTPError as e:
        raise UpdateError("http", e.code)
    except urllib.error.URLError as e:
        if isinstance(e.reason, socket.timeout):
            raise UpdateError("timeout")
        raise UpdateError("network", e.reason)
    except socket.timeout:
        raise UpdateError("timeout")
    except (OSError, http.client.HTTPException, ValueError) as e:
        raise UpdateError("network", e)
    try:
        check_url(r.geturl())
    except UpdateError:
        r.close()
        raise
    return r


def _chunks(r, limit):
    """The body in pieces, stopping at `limit` bytes."""
    try:
        size = int(r.headers.get("Content-Length") or 0)
    except (TypeError, ValueError, AttributeError):
        size = 0
    if size > limit:
        raise UpdateError("too_big", size)
    total = 0
    while True:
        try:
            block = r.read(64 * 1024)
        except socket.timeout:
            raise UpdateError("timeout")
        except (OSError, http.client.HTTPException) as e:
            raise UpdateError("network", e)
        if not block:
            return
        total += len(block)
        if total > limit:
            raise UpdateError("too_big", total)
        yield block


def _get_bytes(url, version, accept, opener, timeout, limit):
    with _open(url, version, accept, opener, timeout) as r:
        return b"".join(_chunks(r, limit))


# ---- the release -----------------------------------------------------------------
def _safe_name(name, fallback):
    name = os.path.basename(name or "")
    return name if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,120}", name) else fallback


def parse_release(data):
    """Release from GitHub's /releases/latest answer. Only files of that release are used."""
    if not isinstance(data, dict):
        raise UpdateError("bad_response", "not an object")
    tag = data.get("tag_name")
    if not isinstance(tag, str) or parse_version(tag) is None:
        raise UpdateError("bad_response", "tag %r" % (tag,))
    version = tag[1:] if tag[:1] in "vV" else tag
    page = data.get("html_url")
    if not (isinstance(page, str) and page.startswith("https://github.com/%s/releases/" % REPO)):
        page = RELEASES_PAGE
    qtag = urllib.parse.quote(tag)
    asset_prefix = "https://github.com/%s/releases/download/%s/" % (REPO, qtag)
    assets = [a for a in (data.get("assets") or []) if isinstance(a, dict)
              and isinstance(a.get("name"), str)
              and str(a.get("browser_download_url", "")).startswith(asset_prefix)]

    zips = [a for a in assets if a["name"].lower().endswith(".zip")]
    zips.sort(key=lambda a: "tasktriggerantitrack" not in a["name"].lower())
    fallback_name = "TaskTriggerAntitrack-%s.zip" % version
    if zips:
        a = zips[0]
        url, name = a["browser_download_url"], _safe_name(a["name"], fallback_name)
        digest = str(a.get("digest") or "")
        sha = digest[7:].lower() if re.fullmatch(r"sha256:[0-9a-fA-F]{64}", digest) else None
        sums = [s for s in assets if s["name"].lower() in SUMS_NAMES
                or s["name"].lower() == a["name"].lower() + ".sha256"]
        sums_url = sums[0]["browser_download_url"] if sums and not sha else None
    else:                           # no zip attached: GitHub's source archive of the tag
        url = data.get("zipball_url")
        if not (isinstance(url, str) and url.startswith(
                "https://api.github.com/repos/%s/zipball/%s" % (REPO, qtag))):
            raise UpdateError("bad_response", "no archive")
        name, sha, sums_url = fallback_name, None, None
    return Release(tag, version, page, url, name, sha, sums_url)


def latest_release(current, opener=None, timeout=TIMEOUT):
    """The latest published release; with its SHA-256 when it comes in a separate file."""
    raw = _get_bytes(API_LATEST, current, "application/vnd.github+json", opener, timeout, MAX_JSON)
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise UpdateError("bad_response", "not JSON")
    rel = parse_release(data)
    if rel.sums_url:
        text = _get_bytes(rel.sums_url, current, "application/octet-stream", opener, timeout, 64 * 1024)
        sha = sha_from_sums(text.decode("utf-8", "replace"), rel.archive_name)
        if not sha:
            raise UpdateError("checksum", "no line for %s" % rel.archive_name)
        rel = rel._replace(sha256=sha)
    return rel


def sha_from_sums(text, name):
    """The SHA-256 of `name` in a 'sha256sum' style list (or a file with just the hash)."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for line in lines:
        parts = line.split(None, 1)
        if len(parts) == 2 and parts[1].lstrip("*").strip() == name:
            h = parts[0].lower()
            return h if re.fullmatch(r"[0-9a-f]{64}", h) else None
    if len(lines) == 1 and re.fullmatch(r"[0-9a-fA-F]{64}", lines[0].split()[0]):
        return lines[0].split()[0].lower()
    return None


def download(rel, dest_dir, current, opener=None, timeout=TIMEOUT):
    """Downloads the release archive into dest_dir and checks it. Returns its path."""
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, rel.archive_name)
    part = dest + ".part"
    h = hashlib.sha256()
    # the API (source archive) refuses 'octet-stream' with a 415; attached files want it
    api = urllib.parse.urlsplit(rel.archive_url).hostname == "api.github.com"
    accept = "application/vnd.github+json" if api else "application/octet-stream"
    try:
        with _open(rel.archive_url, current, accept, opener, timeout) as r, \
                open(part, "wb") as f:
            for block in _chunks(r, MAX_ARCHIVE):
                h.update(block)
                f.write(block)
        if rel.sha256 and h.hexdigest() != rel.sha256.lower():
            raise UpdateError("checksum", h.hexdigest())
        read_archive(part)          # a valid copy of the app, before keeping it
        os.replace(part, dest)
    except OSError as e:
        raise UpdateError("write", e)
    finally:
        if os.path.exists(part):
            try:
                os.remove(part)
            except OSError:
                pass
    return dest


# ---- installing ------------------------------------------------------------------
def downloads_dir():
    d = os.path.join(os.path.expanduser("~"), "Downloads")
    return d if os.path.isdir(d) else tempfile.gettempdir()


def install_plan(app_dir):
    """How this copy can be updated, as (method, blocker):

    ('git', None)      a clean git clone: fetch the release tag and fast-forward to it;
    ('git', reason)    a git clone that cannot be updated safely (no_git, local_changes, not_git);
    ('zip', None)      a folder it can write to: replace the files from the release archive;
    ('download', 'readonly')  anything else: save the archive and open the release page.
    """
    if os.path.exists(os.path.join(app_dir, ".git")):
        return "git", git_blocker(app_dir)   # replacing files would leave git out of step
    try:
        fd, probe = tempfile.mkstemp(prefix=".tta-probe-", dir=app_dir)
        os.close(fd)
        os.remove(probe)
    except OSError:
        return "download", "readonly"
    return "zip", None


# ---- updating a git clone ----------------------------------------------------------
REPO_GIT = "https://github.com/%s.git" % REPO     # always the official one, not the clone's origin
GIT_TIMEOUT = 60


def _git_exe():
    return shutil.which("git")


def _git(root, *args, timeout=15, check=True):
    exe = _git_exe()
    if not exe:
        raise UpdateError("no_git")
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never", LC_ALL="C")
    flags = 0x08000000 if sys.platform == "win32" else 0     # CREATE_NO_WINDOW under pythonw
    try:
        r = subprocess.run([exe, "-C", root] + list(args), env=env, stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=timeout, creationflags=flags)
    except subprocess.TimeoutExpired:
        raise UpdateError("git", "no answer after %d s" % timeout)
    except OSError as e:
        raise UpdateError("git", e)
    if check and r.returncode != 0:
        lines = (r.stderr or r.stdout).strip().splitlines()
        raise UpdateError("git", lines[-1] if lines else r.returncode)
    return r


def git_blocker(app_dir):
    """None if this clone can be fast-forwarded safely; otherwise why not."""
    if not _git_exe():
        return "no_git"
    same = lambda p: os.path.normcase(os.path.realpath(p))  # noqa: E731
    try:
        top = _git(app_dir, "rev-parse", "--show-toplevel").stdout.strip()
        if not top or same(top) != same(app_dir):
            return "not_git"
        if _git(app_dir, "status", "--porcelain", "--untracked-files=no").stdout.strip():
            return "local_changes"
    except UpdateError:
        return "not_git"
    return None


def git_update(tag, app_dir, repo_url=REPO_GIT):
    """Moves the clone to `tag` of the official repository, fast-forward only. Returns the commit.

    Nothing changes unless every check passes: a clean clone, the tag downloaded, and no
    commits of its own. Git checks what it downloads by its hashes. The user's files
    (alarms.json, error.log) are not tracked by git, so they are left alone.
    """
    if parse_version(tag) is None:          # also keeps it a safe refspec
        raise UpdateError("bad_response", "tag %r" % (tag,))
    blocker = git_blocker(app_dir)
    if blocker:
        raise UpdateError(blocker)
    _git(app_dir, "fetch", "--no-tags", "--quiet", repo_url, "refs/tags/%s" % tag, timeout=GIT_TIMEOUT)
    new = _git(app_dir, "rev-parse", "--verify", "--quiet", "FETCH_HEAD^{commit}").stdout.strip()
    if not re.fullmatch(r"[0-9a-f]{40,64}", new):
        raise UpdateError("git", "the release tag was not downloaded")
    if _git(app_dir, "merge-base", "--is-ancestor", new, "HEAD", check=False).returncode == 0:
        return new                          # the clone already has it
    if _git(app_dir, "merge-base", "--is-ancestor", "HEAD", new, check=False).returncode != 0:
        raise UpdateError("diverged")       # commits of its own: no fast-forward possible
    _git(app_dir, "merge", "--ff-only", "--quiet", new, timeout=GIT_TIMEOUT)
    return new


def _safe_member(rel):
    parts = rel.split("/")
    return (rel and "\\" not in rel and ":" not in rel and not rel.startswith("/")
            and all(p not in ("", ".", "..") for p in parts))


def read_archive(zip_path):
    """{path inside the app: ZipInfo}, with GitHub's top folder removed. Checks it is the app."""
    try:
        z = zipfile.ZipFile(zip_path)
    except (zipfile.BadZipFile, OSError) as e:
        raise UpdateError("bad_archive", e)
    with z:
        infos = z.infolist()
        files = [i for i in infos if not i.is_dir()]
        tops = {i.filename.split("/", 1)[0] for i in infos}
        prefix = ""
        if len(tops) == 1 and files and all("/" in i.filename for i in files):
            prefix = tops.pop() + "/"
        out = {}
        for i in files:
            rel = i.filename[len(prefix):]
            if not _safe_member(rel):
                raise UpdateError("bad_archive", "unsafe path %r" % i.filename)
            out[rel] = i
        if sum(i.file_size for i in files) > MAX_UNZIPPED:
            raise UpdateError("too_big", "unzipped")
        missing = [r for r in REQUIRED if r not in out]
        if missing:
            raise UpdateError("bad_archive", "missing %s" % ", ".join(missing))
    return out


def is_user_file(rel, app_dir):
    """Files of the user that an update never overwrites."""
    first = rel.split("/", 1)[0]
    return (rel in USER_FILES or rel.startswith("alarms.json.corrupto-")
            or first in (".git", "__pycache__") or first.startswith(".tta-")
            or (rel in USER_FILES_IF_PRESENT and os.path.exists(os.path.join(app_dir, rel))))


def install(zip_path, app_dir, current):
    """Replaces the app's files with the archive's. Returns the folder with the old ones.

    The new files are unpacked and compiled next to the app first; then each old file is
    copied to the backup folder and the new one moved over it. If anything fails halfway,
    the files already replaced are put back, so the app is left as it was.
    """
    members = read_archive(zip_path)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    staging = os.path.join(app_dir, ".tta-update-%s" % stamp)
    backup = os.path.join(app_dir, ".tta-backup-%s-%s" % (_safe_name(current, "old"), stamp))
    wanted = sorted(r for r in members if not is_user_file(r, app_dir))
    done = []                       # (target, had_old_file)
    try:
        with zipfile.ZipFile(zip_path) as z:
            for rel in wanted:
                dst = os.path.join(staging, *rel.split("/"))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                with z.open(members[rel]) as src, open(dst, "wb") as f:
                    shutil.copyfileobj(src, f)
                if rel.endswith(".py"):
                    with open(dst, "rb") as f:
                        compile(f.read(), rel, "exec")
        for rel in wanted:
            target = os.path.join(app_dir, *rel.split("/"))
            old = os.path.isfile(target)
            if old:
                keep = os.path.join(backup, *rel.split("/"))
                os.makedirs(os.path.dirname(keep), exist_ok=True)
                shutil.copy2(target, keep)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            os.replace(os.path.join(staging, *rel.split("/")), target)
            done.append((rel, old))
    except (SyntaxError, ValueError, zipfile.BadZipFile) as e:
        _undo(done, app_dir, backup)
        raise UpdateError("bad_archive", e)
    except OSError as e:
        _undo(done, app_dir, backup)
        raise UpdateError("write", e)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return backup


def _undo(done, app_dir, backup):
    for rel, old in reversed(done):
        target = os.path.join(app_dir, *rel.split("/"))
        try:
            if old:
                shutil.copy2(os.path.join(backup, *rel.split("/")), target)
            else:
                os.remove(target)
        except OSError:
            pass
