from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

from .ghidra import install_ghidra_dependencies, REQUIRED_GHIDRA_JARS
from .maven import find_maven_command, run_maven
from .python_env import detect_repo_root

DEFAULT_GHIDRA_VERSION = "12.0.4"
DEFAULT_GHIDRA_BUILD_DATE = "20250303"
MAMBA_DIR = Path.home() / ".mamba"
MAMBA_CONFIG = MAMBA_DIR / "config.json"


def _check_java() -> tuple[bool, str]:
    java = shutil.which("java")
    if not java:
        return False, "Java not found on PATH. Install Java 21 LTS (OpenJDK recommended)."
    try:
        result = subprocess.run(
            [java, "-version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = result.stderr + result.stdout
        match = __import__("re").search(r'version "(\d+)', output)
        if not match:
            return False, f"Could not parse Java version from: {output}"
        major = int(match.group(1))
        if major < 21:
            return False, f"Java {major} found, but Java 21+ is required."
        return True, f"Java {major} OK"
    except Exception as e:
        return False, f"Failed to check Java: {e}"


def _check_maven() -> tuple[bool, str]:
    mvn = shutil.which("mvn")
    if not mvn:
        return False, "Maven not found on PATH. Install Apache Maven 3.9+."
    try:
        result = subprocess.run(
            [mvn, "-version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = result.stdout
        match = __import__("re").search(r"Apache Maven (\d+)\.(\d+)", output)
        if not match:
            return False, f"Could not parse Maven version from: {output}"
        major, minor = int(match.group(1)), int(match.group(2))
        if major < 3 or (major == 3 and minor < 9):
            return False, f"Maven {major}.{minor} found, but Maven 3.9+ is required."
        return True, f"Maven {major}.{minor} OK"
    except Exception as e:
        return False, f"Failed to check Maven: {e}"


def _ghidra_download_url(version: str, build_date: str) -> str:
    tag = f"Ghidra_{version}_build"
    filename = f"ghidra_{version}_PUBLIC_{build_date}.zip"
    return (
        f"https://github.com/NationalSecurityAgency/ghidra/releases/download/"
        f"{tag}/{filename}"
    )


def _download_file(url: str, dest: Path, chunk_size: int = 8192) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {url} ...")
    req = urllib.request.Request(url, headers={"User-Agent": "mamba-setup/1.0"})
    with urllib.request.urlopen(req, timeout=300) as response:
        total = int(response.headers.get("Content-Length", 0))
        downloaded = 0
        with open(dest, "wb") as f:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if total > 0:
                    pct = downloaded * 100 // total
                    print(f"\r  Progress: {pct}% ({downloaded // 1024 // 1024} MB / {total // 1024 // 1024} MB)", end="", flush=True)
        print()
    return dest


def _extract_zip(zip_path: Path, dest_dir: Path) -> Path:
    print(f"Extracting {zip_path.name} ...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest_dir)
    extracted = list(dest_dir.iterdir())
    if len(extracted) == 1 and extracted[0].is_dir():
        return extracted[0]
    return dest_dir


def _find_ghidra_home(parent: Path) -> Path | None:
    for child in parent.iterdir():
        if child.is_dir() and child.name.startswith("ghidra_"):
            return child
    return None


def _load_config() -> dict:
    if MAMBA_CONFIG.exists():
        with open(MAMBA_CONFIG) as f:
            return json.load(f)
    return {}


def _save_config(config: dict) -> None:
    MAMBA_DIR.mkdir(parents=True, exist_ok=True)
    with open(MAMBA_CONFIG, "w") as f:
        json.dump(config, f, indent=2)


def _headless_jar_name(version: str) -> str:
    return f"MambaMCP-{version}-headless.jar"


def _is_server_running(port: int = 8089) -> bool:
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/health",
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def _wait_for_server(port: int = 8089, timeout: int = 60) -> bool:
    for _ in range(timeout):
        if _is_server_running(port):
            return True
        time.sleep(1)
    return False


def cmd_setup(args) -> int:
    ok, msg = _check_java()
    print(msg)
    if not ok:
        return 1

    ok, msg = _check_maven()
    print(msg)
    if not ok:
        return 1

    version = getattr(args, "ghidra_version", None) or DEFAULT_GHIDRA_VERSION
    build_date = getattr(args, "ghidra_build_date", None) or DEFAULT_GHIDRA_BUILD_DATE
    force = getattr(args, "force", False)

    MAMBA_DIR.mkdir(parents=True, exist_ok=True)
    cache_dir = MAMBA_DIR / "cache"
    cache_dir.mkdir(exist_ok=True)

    ghidra_home = _find_ghidra_home(cache_dir)
    if not ghidra_home or force:
        url = _ghidra_download_url(version, build_date)
        zip_name = url.split("/")[-1]
        zip_path = cache_dir / zip_name

        if not zip_path.exists() or force:
            try:
                _download_file(url, zip_path)
            except Exception as e:
                print(f"ERROR: Failed to download Ghidra: {e}")
                return 1
        else:
            print(f"Using cached {zip_path.name}")

        extracted = _extract_zip(zip_path, cache_dir)
        ghidra_home = _find_ghidra_home(extracted) or extracted

    print(f"Ghidra home: {ghidra_home}")

    repo_root = detect_repo_root()
    pom_versions = __import__("tools.setup.versioning", fromlist=["read_pom_versions"]).read_pom_versions(repo_root)
    plugin_version = pom_versions.plugin_version

    print("Installing Ghidra JARs into local Maven repository ...")
    ret = install_ghidra_dependencies(repo_root, ghidra_home, force=force, dry_run=False)
    if ret != 0:
        return ret

    print("Building headless server ...")
    mvn_cmd = find_maven_command()
    ret = run_maven(repo_root, ["clean", "package", "-P", "headless", "-DskipTests"], dry_run=False)
    if ret != 0:
        return ret

    headless_jar = repo_root / "target" / _headless_jar_name(plugin_version)
    if not headless_jar.exists():
        print(f"ERROR: Headless JAR not found at {headless_jar}")
        return 1

    install_jar = MAMBA_DIR / "mamba-headless.jar"
    shutil.copy(headless_jar, install_jar)
    print(f"Installed headless JAR: {install_jar}")

    config = {
        "ghidra_path": str(ghidra_home),
        "headless_jar": str(install_jar),
        "version": plugin_version,
        "port": 8089,
    }
    _save_config(config)
    print("Mamba setup complete.")
    print(f"  Config: {MAMBA_CONFIG}")
    return 0


def cmd_start(args) -> int:
    config = _load_config()
    if not config:
        print("ERROR: Mamba not set up. Run 'mamba setup' first.")
        return 1

    headless_jar = Path(config["headless_jar"])
    if not headless_jar.exists():
        print(f"ERROR: Headless JAR not found: {headless_jar}")
        return 1

    port = getattr(args, "port", None) or config.get("port", 8089)
    bind = getattr(args, "bind", None) or "127.0.0.1"
    file_arg = getattr(args, "file", None)
    project_arg = getattr(args, "project", None)
    program_arg = getattr(args, "program", None)

    java_cmd = [
        "java",
        "-Xmx4g",
        "-XX:+UseG1GC",
        "-Duser.name=" + os.environ.get("USER", os.environ.get("USERNAME", "mamba")),
        "-jar", str(headless_jar),
        "--port", str(port),
        "--bind", bind,
    ]
    if file_arg:
        java_cmd.extend(["--file", str(file_arg)])
    if project_arg:
        java_cmd.extend(["--project", str(project_arg)])
    if program_arg:
        java_cmd.extend(["--program", str(program_arg)])

    print(f"Starting Mamba headless server on {bind}:{port} ...")
    print(f"  Command: {' '.join(java_cmd)}")
    try:
        proc = subprocess.Popen(java_cmd)
        proc.wait()
    except KeyboardInterrupt:
        print("\nShutting down headless server ...")
        proc.terminate()
        proc.wait()
    return 0


def cmd_mcp(args) -> int:
    config = _load_config()
    port = getattr(args, "port", None) or (config.get("port") if config else None) or 8089

    if not _is_server_running(port):
        if not config:
            print("ERROR: Mamba not set up and no headless server running.")
            print("Run 'mamba setup' first, or start the server with 'mamba start'.")
            return 1

        headless_jar = Path(config["headless_jar"])
        if not headless_jar.exists():
            print(f"ERROR: Headless JAR not found: {headless_jar}")
            return 1

        print("Starting Mamba headless server in background ...")
        java_cmd = [
            "java",
            "-Xmx4g",
            "-XX:+UseG1GC",
            "-Duser.name=" + os.environ.get("USER", os.environ.get("USERNAME", "mamba")),
            "-jar", str(headless_jar),
            "--port", str(port),
            "--bind", "127.0.0.1",
        ]
        subprocess.Popen(
            java_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        if not _wait_for_server(port, timeout=60):
            print("ERROR: Headless server failed to start within 60s.")
            return 1
        print("Headless server ready.")
    else:
        print("Headless server already running.")

    print("Starting MCP bridge in stdio mode ...")
    from bridge_mcp_ghidra import main as bridge_main

    bridge_args = ["--transport", "stdio"]
    if getattr(args, "lazy", True):
        bridge_args.append("--lazy")
    else:
        bridge_args.append("--no-lazy")
    return bridge_main(bridge_args)