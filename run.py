"""JARVIS Master Runtime Entry Point matching 01_SYSTEM_ARCHITECTURE.md and 18_FEATURE_ROADMAP.md."""

import argparse
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

from jarvis.core.config import load_config
from jarvis.core.errors import JarvisError
from jarvis.core.state_machine import State
from jarvis.packaging.installer import EnvironmentValidator
from jarvis.pipeline import ExecutionPipeline
from jarvis.router.router import InputEvent
from jarvis.ui.hud_server import HUDServer


BANNER = r"""
============================================================================
       ___  ___  ______ _   _ _____ _____ 
      |_  |/ _ \ | ___ \ | | |_   _/  ___|
        | / /_\ \| |_/ / | | | | | \ `--. 
        | |  _  ||    /| | | | | |  `--. \
    /\__/ / | | || |\ \\ \_/ /_| |_/\__/ /
    \____/\_| |_/\_| \_|\___/ \___/\____/ 

    J.A.R.V.I.S. Personal Hybrid Assistant v1.0.0
    Offline-First Multi-Modal Assistant with Strict Safety Policy
============================================================================
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch the JARVIS Personal Assistant.")
    parser.add_argument("--host", default="127.0.0.1", help="HUD Server host interface")
    parser.add_argument("--port", type=int, default=8080, help="HUD Server port")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open browser HUD")
    parser.add_argument("--skip-diagnostics", action="store_true", help="Skip pre-flight diagnostics")
    parser.add_argument("--minimized", action="store_true", help="Run minimized/daemon mode")

    # Execution mode: Virtual (default, safe demo) vs Real (actual OS control)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--real",
        action="store_true",
        help="Use REAL OS backends (actually launches apps, changes volume, locks screen, etc.)",
    )
    mode_group.add_argument(
        "--virtual",
        action="store_true",
        default=True,
        help="Use VIRTUAL/simulation backends (default, safe for demos and tests)",
    )
    args = parser.parse_args()

    print(BANNER)

    # 1. Pre-flight diagnostics
    if not args.skip_diagnostics:
        print("[*] Running pre-flight diagnostic validator...")
        validator = EnvironmentValidator()
        report = validator.run_diagnostics()
        if not report.all_passed:
            print("[!] Pre-flight diagnostics encountered warnings:")
            for note in report.notes:
                print(f"    - {note}")
        else:
            print("[+] Pre-flight diagnostics: ALL CHECKS PASSED (Python, dependencies, workspace layout, tools).")
    else:
        print("[*] Skipping pre-flight diagnostics.")

    # 2. Load Configuration
    config = load_config()
    print(f"[*] Configuration loaded: Wake Word='{config.jarvis.wake_word}', Privacy Opt-In: Camera={'ON' if config.vision.enabled else 'OFF'}, Mic={'ON' if config.voice.always_listen else 'OFF (Push/Wake)'}")

    # 3. Initialize Execution Pipeline
    use_real = args.real
    mode_label = "REAL (live OS execution)" if use_real else "VIRTUAL (simulation / safe demo)"
    pipeline = ExecutionPipeline(config=config, use_real_backends=use_real)
    print(f"[+] Execution Pipeline initialized. Session ID: {pipeline.session_id}")
    print(f"[+] Execution mode : {mode_label}")
    print(f"[+] Registered Tools: {len(pipeline.registry.list_tools())} verified actions available.")

    # 4. Start HUD Server
    hud_server = HUDServer(
        hud_state=pipeline.hud_state,
        pipeline=pipeline,
        host=args.host,
        port=args.port,
    )
    hud_server.start()
    hud_url = f"http://{args.host}:{args.port}/"
    print(f"[+] Tactical Web HUD online at: {hud_url}")

    # 5. Open Web Browser
    if not args.no_browser and not args.minimized:
        try:
            webbrowser.open(hud_url)
        except Exception:
            pass

    print("\n[!] JARVIS is ready. Type a command (e.g. 'set volume 75', 'open notepad', 'read_setting') or use the Web HUD.")
    print("[!] Type 'confirm' to accept pending actions, 'stop' for emergency stop, or 'exit' to quit.\n")

    # 6. Interactive Command Loop
    try:
        while True:
            try:
                user_input = input(f"[{pipeline.state_machine.current_state.value}] JARVIS> ").strip()
            except EOFError:
                break

            if not user_input:
                continue

            lowered = user_input.lower()
            if lowered in {"exit", "quit"}:
                print("[*] Shutting down JARVIS...")
                break

            if lowered in {"stop", "cancel", "emergency stop"}:
                pipeline.trigger_emergency_stop()
                print("[!] EMERGENCY STOP triggered. All active tasks cancelled.")
                continue

            if lowered in {"confirm", "yes"}:
                res = pipeline.confirm_pending(confirmed=True)
                print(f"[>] Confirmed: {res.get('response_text') or res.get('status')}")
                continue

            if lowered in {"reject", "no"}:
                res = pipeline.confirm_pending(confirmed=False)
                print(f"[>] Cancelled: {res.get('response_text') or res.get('status')}")
                continue

            # Route input event
            event = InputEvent(
                event_id=f"cli-{hex(int(time.time()*1000))[-4:]}",
                channel="voice",
                raw_payload=user_input,
            )
            result = pipeline.process_event(event)

            status = result.get("status")
            response = result.get("response_text", "")
            verified = result.get("verified", False)

            if status == "needs_confirmation":
                print(f"\n[?] CONFIRMATION REQUIRED (Risk Gated): {response}")
                print("    Type 'confirm' to execute or 'reject' to cancel.")
            elif status == "success":
                v_badge = "[VERIFIED: OK]" if verified else "[UNVERIFIED]"
                print(f"[+] {v_badge} {response}")
            else:
                print(f"[-] [{status.upper()}] {response}")

    except KeyboardInterrupt:
        print("\n[*] Interrupted by user. Exiting gracefully...")
    finally:
        hud_server.stop()
        print("[*] Tactical HUD server stopped. Goodbye.")


if __name__ == "__main__":
    main()
