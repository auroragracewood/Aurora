"""
Deploy Aurora Gracewood. D:/ is the canonical source. This script:
  1. Pushes every file in DEPLOY_FILES to me-think and restarts FastAPI
     (live runtime — what users actually hit via Cloudflare Tunnel).
  2. Commits + pushes the whole repo to auroragracewood/Aurora on GitHub
     (mirror — kept in sync as a fallback / source-of-truth backup).

Usage:
    python deploy.py                 # deploy both (default)
    python deploy.py --me-think      # me-think only
    python deploy.py --github        # GitHub only
    python deploy.py -m "msg"        # override commit message
"""
import subprocess, base64, time, sys
from pathlib import Path
import urllib.request

SSH = "me@100.80.32.54"
LOCAL_ROOT = Path(__file__).parent
REMOTE_ROOT = "C:/Users/ME/aurora-gracewood"

DEPLOY_FILES = [
    "backend/main.py",
    "account/realm.css",
    "account/realm.js",
    "account/auth.js",
    "account/g-1vl00d/superuser.html",
    "account/g-1vl00d/profile-edit.html",
    "account/g-1vl00d/settings.html",
    "account/g-1vl00d/notifications.html",
    "account/g-1vl00d/sessions.html",
    "account/g-1vl00d/activity.html",
    "account/g-1vl00d/messages.html",
    "account/g-1vl00d/manage-users.html",
    "account/g-1vl00d/submissions.html",
    "account/admin/admin.html",
    "account/admin/profile-edit.html",
    "account/admin/notifications.html",
    "account/admin/activity.html",
    "account/admin/messages.html",
    "account/admin/clients.html",
    "account/admin/submissions.html",
    "account/client/client.html",
    "account/client/profile-edit.html",
    "account/client/notifications.html",
    "account/client/activity.html",
    "account/client/messages.html",
    "account/client/submissions.html",
    "start-aurora.bat",
    # Badge artwork assets (served via /awards/asset/* and /awards/badge-asset/*)
    "awards/badDB/assets/mark.svg",
    "awards/badDB/badges/starter/starter.png",
    # Awards landing page + its dependencies (served via /awards/, /awards/{file}, /assets/, /account/auth.css)
    "awards/index.html",
    "awards/styles.css",
    "awards/app.js",
    "awards/bg.js",
    "awards/config.js",
    "awards/earth-day-2k.jpg",
    "awards/earth-night-8k.jpg",
    "account/auth.css",
    "assets/logo.png",
    "assets/awardlogo.png",
]


def ssh(cmd, timeout=30):
    return subprocess.run(["ssh", SSH, cmd], capture_output=True, text=True, timeout=timeout)


def transfer(rel, content_bytes):
    target = REMOTE_ROOT + "/" + rel
    parent = "/".join(target.split("/")[:-1])
    ssh('powershell -ExecutionPolicy Bypass -NoProfile -Command "New-Item -ItemType Directory -Force -Path ' + parent + ' | Out-Null"')

    chunk_size = 5000  # ~6700 base64 chars; stays safely under Windows 8191 cmd limit
    chunks = [content_bytes[i:i + chunk_size] for i in range(0, len(content_bytes), chunk_size)]
    for i, chunk in enumerate(chunks):
        b64 = base64.b64encode(chunk).decode("ascii")
        if i == 0:
            ps = "$b=[System.Convert]::FromBase64String('" + b64 + "'); [System.IO.File]::WriteAllBytes('" + target + "',$b)"
        else:
            ps = ("$b=[System.Convert]::FromBase64String('" + b64 + "'); "
                  "$existing=[System.IO.File]::ReadAllBytes('" + target + "'); "
                  "[System.IO.File]::WriteAllBytes('" + target + "', $existing + $b)")
        r = ssh('powershell -ExecutionPolicy Bypass -NoProfile -Command "' + ps + '"')
        if r.returncode != 0:
            return False, r.stderr[:200]
    return True, ""


def main():
    print(f"Local root:  {LOCAL_ROOT}")
    print(f"Remote root: {SSH}:{REMOTE_ROOT}")
    print()
    print("=== Transferring files ===")
    for rel in DEPLOY_FILES:
        local = LOCAL_ROOT / rel.replace("/", "\\")
        if not local.exists():
            print(f"  SKIP {rel} (not on D:/)")
            continue
        ok, err = transfer(rel, local.read_bytes())
        print(f"  {'OK' if ok else 'FAIL'} {rel}  ({local.stat().st_size} bytes)")
        if not ok:
            print(f"    {err}")

    print()
    print("=== Restart FastAPI on me-think ===")
    r = ssh("netstat -ano | findstr :8000")
    for line in r.stdout.splitlines():
        if "LISTENING" in line:
            pid = line.split()[-1]
            ssh("taskkill /F /T /PID " + pid)
            print(f"  killed pid {pid}")

    # Launch FastAPI in the background. Earlier attempts used PowerShell's `Start-Process` but
    # that fails reliably when invoked over SSH (no interactive user session). `cmd /c` plus a
    # subprocess.Popen on the local side (so we don't block waiting for the .bat to return)
    # works consistently — same method used as manual fallback when the script's restart fails.
    subprocess.Popen(["ssh", SSH, 'cmd /c "C:\\Users\\ME\\aurora-gracewood\\start-aurora.bat"'],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    up = False
    for i in range(20):
        time.sleep(1.2)
        r = ssh("netstat -ano | findstr :8000")
        if "LISTENING" in r.stdout:
            print(f"  back up at s{round((i + 1) * 1.2)}")
            up = True
            break
    if not up:
        print("  FastAPI did not bind :8000 within 24s.")
        print("  Manual fallback: ssh me@me-think; cmd /c C:\\Users\\ME\\aurora-gracewood\\start-aurora.bat")
        return

    print()
    print("=== Reachability check ===")
    for path, label in [
        ("/g-1vl00d/superuser?as=1", "superuser"),
        ("/admin/admin?as=2", "admin"),
        ("/client/client?as=3", "client"),
    ]:
        try:
            resp = urllib.request.urlopen("http://me-think:8000" + path, timeout=5)
            print(f"  HTTP {resp.status}  http://me-think:8000{path}  ({label})")
        except Exception as e:
            print(f"  ERR   http://me-think:8000{path}  ({label}) -> {e}")


if __name__ == "__main__":
    main()
