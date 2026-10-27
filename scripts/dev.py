"""Run the local API and worker together; stop both on exit."""

import argparse, os, pathlib, signal, socket, subprocess, sys, time

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if not (ROOT / "web/dist/index.html").exists():
        parser.error("Frontend is missing. Run make web first.")
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", args.port)) == 0:
            parser.error(
                f"Port {args.port} is already in use; stop the existing local instance or choose --port."
            )
    env = os.environ.copy()
    env.setdefault("ENTITYLENS_DB", str(ROOT / "entitylens-v1.db"))
    env.setdefault("OMP_NUM_THREADS", "2")
    env.setdefault("OPENBLAS_NUM_THREADS", "2")
    stopped = False

    def stop(*_):
        nonlocal stopped
        stopped = True

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    commands = [
        [
            "-m",
            "uvicorn",
            "entitylens.api:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(args.port),
        ],
        ["-m", "entitylens.worker"],
    ]
    children = []
    try:
        for command in commands:
            children.append(
                subprocess.Popen(
                    [sys.executable, *command],
                    cwd=ROOT,
                    env=env,
                    start_new_session=True,
                )
            )
        print(
            f"EntityLens: http://127.0.0.1:{args.port} | Database: {env['ENTITYLENS_DB']}",
            flush=True,
        )
        while not stopped:
            for child in children:
                if child.poll() is not None:
                    print(
                        "API or worker exited; stopping both processes.",
                        file=sys.stderr,
                    )
                    return child.returncode or 1
            time.sleep(0.2)
        return 0
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()


if __name__ == "__main__":
    sys.exit(main())
