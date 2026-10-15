import runpy, socket, sys
attempts = []
def refuse(self, *a, **k):
    attempts.append(a)
    raise OSError("socket guard: connect refused")
socket.socket.connect = refuse
socket.socket.connect_ex = refuse
script = sys.argv[1]
sys.argv = sys.argv[1:]
try:
    runpy.run_path(script, run_name="__main__")
except SystemExit as e:
    print(f"[guard] exit {e.code}; connect attempts: {len(attempts)}", file=sys.stderr)
    raise
print(f"[guard] returned; connect attempts: {len(attempts)}", file=sys.stderr)
