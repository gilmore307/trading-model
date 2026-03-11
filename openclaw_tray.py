import os
import socket
import subprocess
import threading
import time
import traceback
from datetime import datetime

import psutil
import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw

SSH_USER = "root"
SSH_HOST = "100.110.207.125"
LOCAL_PORT = 18789
REMOTE_PORT = 18789

TRAY_ICON_PATH = r"C:\OpenClaw\OpenClaw.jfif"
LOG_DIR = r"C:\OpenClaw\tray\logs"
TRAY_LOG_PATH = os.path.join(LOG_DIR, "win-node-2-lab.log")
NODE_STDOUT_LOG_PATH = os.path.join(LOG_DIR, "node.stdout.log")
NODE_STDERR_LOG_PATH = os.path.join(LOG_DIR, "node.stderr.log")
SSH_STDERR_LOG_PATH = os.path.join(LOG_DIR, "ssh.stderr.log")

TRAY_EXE_NAME = "win-node-2-lab"
GATEWAY_TOKEN = "40ec3c89f1cfda3e2db02edc54d0682759968b02575d771b"

NODEJS_PATH = r"C:\Program Files\nodejs\node.exe"
OPENCLAW_PATH = r"C:\Users\sunch\AppData\Roaming\npm\node_modules\openclaw\dist\index.js"

CHECK_INTERVAL = 15
AUTO_RECONNECT = True
STARTUP_WAIT = 2
SOCKET_TIMEOUT = 1.5
KILL_WAIT_TIMEOUT = 5
FAIL_THRESHOLD = 2
RECOVER_THRESHOLD = 2
MIN_RECOVERY_GAP_SECONDS = 20

state_lock = threading.Lock()
should_be_running = True
current_status = False
tray_icon = None
monitor_thread = None
stop_event = threading.Event()

fail_streak = 0
success_streak = 0
last_recovery_ts = 0.0

env = os.environ.copy()
env["OPENCLAW_GATEWAY_TOKEN"] = GATEWAY_TOKEN
env["OPENCLAW_GATEWAY_URL"] = f"ws://127.0.0.1:{LOCAL_PORT}/"
env["OPENCLAW_ALLOW_INSECURE_PRIVATE_WS"] = "1"


def ensure_log_dir():
    os.makedirs(LOG_DIR, exist_ok=True)


def write_log(msg: str):
    ensure_log_dir()
    with open(TRAY_LOG_PATH, "a", encoding="utf-8") as f:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{ts}] [tray] {msg}\n")
        f.flush()


def write_exception(prefix: str, exc: Exception):
    write_log(f"{prefix}: {exc}")
    tb = traceback.format_exc()
    for line in tb.strip().splitlines():
        write_log(f"{prefix} traceback: {line}")


def noop(icon=None, menu_item=None):
    pass


def _safe_name(proc) -> str:
    try:
        return (proc.info.get("name") or "").lower()
    except Exception:
        return ""


def _safe_cmdline_list(proc):
    try:
        return proc.info.get("cmdline") or []
    except Exception:
        return []


def _safe_cmdline(proc) -> str:
    try:
        return " ".join(_safe_cmdline_list(proc)).strip()
    except Exception:
        return ""


def _iter_processes(attrs=None):
    if attrs is None:
        attrs = ["pid", "name", "cmdline"]
    for proc in psutil.process_iter(attrs):
        try:
            yield proc
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue


def _contains_flag_with_value(cmdline: str, flag: str, value: str) -> bool:
    target = f"{flag} {value}".lower()
    return target in cmdline.lower()


def _is_target_node_process(proc) -> bool:
    name = _safe_name(proc)
    cmdline = _safe_cmdline(proc).lower()
    return (
        name == "node.exe"
        and OPENCLAW_PATH.lower() in cmdline
        and _contains_flag_with_value(cmdline, "--display-name", TRAY_EXE_NAME.lower())
        and _contains_flag_with_value(cmdline, "--port", str(LOCAL_PORT))
    )


def _is_target_ssh_process(proc) -> bool:
    name = _safe_name(proc)
    cmdline = _safe_cmdline(proc).lower()
    expected_forward = f"{LOCAL_PORT}:127.0.0.1:{REMOTE_PORT}".lower()
    expected_host = f"{SSH_USER}@{SSH_HOST}".lower()
    return name == "ssh.exe" and expected_forward in cmdline and expected_host in cmdline


def find_node_processes():
    result = []
    for proc in _iter_processes(["pid", "name", "cmdline"]):
        try:
            if _is_target_node_process(proc):
                result.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return result


def find_ssh_tunnel_processes():
    result = []
    expected_forward = f"{LOCAL_PORT}:127.0.0.1:{REMOTE_PORT}".lower()
    expected_host = f"{SSH_USER}@{SSH_HOST}".lower()
    for proc in _iter_processes(["pid", "name", "cmdline"]):
        try:
            name = _safe_name(proc)
            cmdline = _safe_cmdline(proc).lower()
            if name == "ssh.exe" and expected_forward in cmdline and expected_host in cmdline:
                result.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return result


def is_node_process_running() -> bool:
    return len(find_node_processes()) > 0


def is_ssh_tunnel_running() -> bool:
    return len(find_ssh_tunnel_processes()) > 0


def is_local_port_open(host="127.0.0.1", port=LOCAL_PORT, timeout=SOCKET_TIMEOUT) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def _kill_processes(procs, label: str):
    if not procs:
        write_log(f"No old {label} processes found.")
        return

    for proc in procs:
        try:
            pid = proc.pid
            proc.kill()
            write_log(f"Killed {label} PID={pid}")
        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            write_log(f"{label} process already exited.")
        except psutil.AccessDenied as e:
            write_log(f"Failed to kill {label} PID={getattr(proc, 'pid', '?')}: {e}")
        except Exception as e:
            write_log(f"Failed to kill {label} PID={getattr(proc, 'pid', '?')}: {e}")

    try:
        _, alive = psutil.wait_procs([p for p in procs if p.is_running()], timeout=KILL_WAIT_TIMEOUT)
        for p in alive:
            try:
                write_log(f"{label} PID={p.pid} still alive after wait timeout.")
            except Exception:
                pass
    except Exception as e:
        write_log(f"wait_procs error for {label}: {e}")


def kill_old_node_processes():
    write_log("Checking for old OpenClaw node processes...")
    _kill_processes(find_node_processes(), "node")


def kill_old_ssh_tunnels():
    write_log("Checking for old SSH tunnel processes...")
    _kill_processes(find_ssh_tunnel_processes(), "ssh")


def _open_log_file(path: str):
    ensure_log_dir()
    return open(path, "a", encoding="utf-8", buffering=1)


def start_ssh_tunnel():
    kill_old_ssh_tunnels()
    write_log(f"Starting SSH tunnel: {SSH_USER}@{SSH_HOST}:{REMOTE_PORT}->{LOCAL_PORT}")
    try:
        ssh_err = _open_log_file(SSH_STDERR_LOG_PATH)
        subprocess.Popen(
            [
                "ssh",
                "-N",
                "-o", "ExitOnForwardFailure=yes",
                "-o", "ServerAliveInterval=30",
                "-o", "ServerAliveCountMax=3",
                "-L", f"{LOCAL_PORT}:127.0.0.1:{REMOTE_PORT}",
                f"{SSH_USER}@{SSH_HOST}",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=ssh_err,
            shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
        )
        time.sleep(STARTUP_WAIT)
        write_log("SSH tunnel start command issued.")
    except Exception as e:
        write_exception("Failed to start SSH tunnel", e)


def start_node():
    kill_old_node_processes()
    write_log("Starting OpenClaw Node in background...")
    try:
        node_out = _open_log_file(NODE_STDOUT_LOG_PATH)
        node_err = _open_log_file(NODE_STDERR_LOG_PATH)
        subprocess.Popen(
            [
                NODEJS_PATH,
                OPENCLAW_PATH,
                "node",
                "run",
                "--host",
                "127.0.0.1",
                "--port",
                str(LOCAL_PORT),
                "--display-name",
                TRAY_EXE_NAME,
            ],
            stdin=subprocess.DEVNULL,
            stdout=node_out,
            stderr=node_err,
            shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
            env=env,
        )
        time.sleep(STARTUP_WAIT)
        write_log("Node start command issued.")
    except Exception as e:
        write_exception("Failed to start OpenClaw Node", e)


def recover_ssh_only():
    write_log("Recovery plan: SSH unhealthy -> restarting SSH tunnel only.")
    start_ssh_tunnel()


def recover_node_only():
    write_log("Recovery plan: node unhealthy -> restarting node only.")
    start_node()


def recover_full_chain():
    write_log("Recovery plan: full chain recovery -> restarting SSH + node.")
    start_ssh_tunnel()
    start_node()


def get_health_snapshot():
    ssh_ok = is_ssh_tunnel_running()
    node_ok = is_node_process_running()
    port_ok = is_local_port_open()
    status = ssh_ok and node_ok and port_ok
    write_log(
        f"Health check -> ssh={ssh_ok}, node={node_ok}, port={port_ok}, status={'ON' if status else 'OFF'}"
    )
    return {"ssh_ok": ssh_ok, "node_ok": node_ok, "port_ok": port_ok, "status": status}


def load_base_icon() -> Image.Image:
    img = Image.open(TRAY_ICON_PATH).convert("RGBA")
    return img.resize((64, 64))


def make_status_icon(is_on: bool) -> Image.Image:
    base = load_base_icon().copy()
    draw = ImageDraw.Draw(base)
    badge_radius = 10
    cx, cy = 52, 52
    color = (0, 200, 0, 255) if is_on else (220, 40, 40, 255)
    draw.ellipse(
        (cx - badge_radius - 2, cy - badge_radius - 2, cx + badge_radius + 2, cy + badge_radius + 2),
        fill=(255, 255, 255, 255),
    )
    draw.ellipse(
        (cx - badge_radius, cy - badge_radius, cx + badge_radius, cy + badge_radius),
        fill=color,
    )
    return base


def get_status_text(_):
    return "✓ Status: ON" if current_status else "✗ Status: OFF"


def get_start_enabled(_):
    return (not should_be_running) or (not current_status)


def get_stop_enabled(_):
    return should_be_running or current_status


def refresh_ui():
    global tray_icon
    if tray_icon is None:
        return
    try:
        tray_icon.icon = make_status_icon(current_status)
        tray_icon.title = f"OpenClaw Tray - {'ON' if current_status else 'OFF'}"
        tray_icon.update_menu()
    except Exception as e:
        write_log(f"refresh_ui error: {e}")


def do_start_sequence():
    write_log("Start sequence initiated.")
    start_ssh_tunnel()
    start_node()


def do_stop_sequence():
    write_log("Stop sequence initiated.")
    kill_old_node_processes()
    kill_old_ssh_tunnels()


def start_worker(icon=None, menu_item=None):
    global should_be_running, current_status, fail_streak, success_streak
    with state_lock:
        should_be_running = True
        fail_streak = 0
        success_streak = 0
        write_log("Manual START requested.")
        do_start_sequence()
        snap = get_health_snapshot()
        current_status = snap["status"]
        refresh_ui()
        if icon:
            icon.notify(f"OpenClaw {'started' if current_status else 'start attempted'}", "OpenClaw")


def stop_worker(icon=None, menu_item=None):
    global should_be_running, current_status, fail_streak, success_streak
    with state_lock:
        should_be_running = False
        fail_streak = 0
        success_streak = 0
        write_log("Manual STOP requested.")
        do_stop_sequence()
        current_status = False
        refresh_ui()
        if icon:
            icon.notify("OpenClaw node stopped", "OpenClaw")


def on_exit(icon=None, menu_item=None):
    global should_be_running
    write_log("Exit requested.")
    stop_event.set()
    with state_lock:
        should_be_running = False
        do_stop_sequence()
    if icon:
        icon.stop()


def monitor_loop():
    global current_status, fail_streak, success_streak, last_recovery_ts
    write_log("Monitor thread started.")
    while not stop_event.is_set():
        try:
            with state_lock:
                snap = get_health_snapshot()
                checked = snap["status"]
                previous = current_status

                if checked:
                    success_streak += 1
                    fail_streak = 0
                else:
                    fail_streak += 1
                    success_streak = 0

                if success_streak >= RECOVER_THRESHOLD:
                    current_status = True
                elif fail_streak >= FAIL_THRESHOLD:
                    current_status = False

                now = time.time()
                can_recover = (now - last_recovery_ts) >= MIN_RECOVERY_GAP_SECONDS

                if should_be_running and AUTO_RECONNECT and fail_streak >= FAIL_THRESHOLD and can_recover:
                    write_log("Detected sustained OFF while desired state is RUNNING. Auto-reconnect begins.")
                    last_recovery_ts = now

                    if not snap["ssh_ok"]:
                        recover_ssh_only()
                        time.sleep(2)
                        snap2 = get_health_snapshot()
                        if snap2["ssh_ok"] and not snap2["node_ok"]:
                            recover_node_only()
                    elif snap["ssh_ok"] and not snap["node_ok"]:
                        recover_node_only()
                    elif snap["ssh_ok"] and snap["node_ok"] and not snap["port_ok"]:
                        write_log("SSH and node look present but local port check failed. Escalating to full chain recovery.")
                        recover_full_chain()
                    else:
                        recover_full_chain()

                    time.sleep(2)
                    final_snap = get_health_snapshot()

                    if final_snap["status"]:
                        current_status = True
                        fail_streak = 0
                        success_streak = RECOVER_THRESHOLD
                        write_log("Auto-reconnect succeeded.")
                        if tray_icon:
                            tray_icon.notify("OpenClaw auto-reconnected", "OpenClaw")
                    else:
                        current_status = False
                        write_log("Auto-reconnect failed this round.")

                if previous != current_status:
                    write_log(f"Status changed: {'ON' if previous else 'OFF'} -> {'ON' if current_status else 'OFF'}")

                refresh_ui()
        except Exception as e:
            write_exception("Monitor loop error", e)

        stop_event.wait(CHECK_INTERVAL)

    write_log("Monitor thread exited.")


def main():
    global tray_icon, monitor_thread, current_status, should_be_running
    write_log("Tray started.")
    with state_lock:
        should_be_running = True
        do_start_sequence()
        snap = get_health_snapshot()
        current_status = snap["status"]

    tray_icon = pystray.Icon(
        "openclaw_tray",
        make_status_icon(current_status),
        f"OpenClaw Tray - {'ON' if current_status else 'OFF'}",
        menu=pystray.Menu(
            item(get_status_text, noop),
            pystray.Menu.SEPARATOR,
            item("Start", start_worker, enabled=get_start_enabled),
            item("Stop", stop_worker, enabled=get_stop_enabled),
            item("Exit", on_exit),
        ),
    )

    monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
    monitor_thread.start()
    tray_icon.run()


if __name__ == "__main__":
    main()
