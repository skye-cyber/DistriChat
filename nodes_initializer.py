import subprocess
import os


def start_all_nodes():
    # Start nodes
    commands = [
        ["python", "node1/manage.py", "runserver", "0.0.0.0:8002"],
        ["python", "node2/manage.py", "runserver", "0.0.0.0:8003"],
    ]

    processes = [subprocess.Popen(cmd) for cmd in commands]
    for i, p in enumerate(processes):
        print(f"\033[94mStarting node{1}\033[0m")

        p.wait()


def start_all_nodes_shell():
    commands = [
        "python node1/manage.py runserver 0.0.0.0:8002",
        "python node2/manage.py runserver 0.0.0.0:8003",
    ]
    for cmd in commands:
        subprocess.Popen(["gnome-terminal", "--", "bash", "-c", cmd])


if __name__ == "__main__":
    if os.name.lower() == "posix":
        try:
            start_all_nodes_shell()
        except Exception:
            start_all_nodes()
    else:
        start_all_nodes()
