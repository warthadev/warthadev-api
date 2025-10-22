# utils.py
import os, math, shutil, socket, subprocess, time, signal

def format_size(size_bytes):
    if size_bytes is None or size_bytes < 0: return "0 B"
    if size_bytes == 0: return "0 B"
    size_name = ("B","KB","MB","GB","TB")
    i = int(math.floor(math.log(size_bytes,1024))) if size_bytes>0 else 0
    p = math.pow(1024,i)
    s = round(size_bytes/p,2)
    return f"{s} {size_name[i]}"

def get_directory_size(start_path='.'):
    total_size = 0
    for dirpath, _, filenames in os.walk(start_path):
        for fname in filenames:
            fp = os.path.join(dirpath, fname)
            try:
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)
            except Exception:
                continue
    return total_size

def list_dir(path, root_path=None):
    try:
        files=[]
        if not os.path.exists(path): return files
        entries = sorted(os.listdir(path), key=lambda n: (not os.path.isdir(os.path.join(path, n)), n.lower()))
        for name in entries:
            full_path = os.path.join(path, name)
            is_dir = os.path.isdir(full_path)
            try:
                if is_dir:
                    size_bytes = get_directory_size(full_path)
                    size = format_size(size_bytes)
                    icon = "fa-folder"
                else:
                    st = os.stat(full_path)
                    size_bytes = st.st_size
                    size = format_size(size_bytes)
                    icon = "fa-file"
            except:
                size, size_bytes, icon = "Error", 0, "fa-exclamation-triangle"
            files.append({
                "name": name,
                "is_dir": is_dir,
                "full_path": full_path,
                "size": size,
                "size_bytes": size_bytes,
                "icon": icon
            })
        return files
    except Exception as e:
        return [{"name":f"ERROR: {e}", "is_dir":False, "full_path":"", "size":"", "size_bytes":0, "icon":"fa-exclamation-triangle"}]

def is_port_in_use(port, host="127.0.0.1"):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(0.5)
        s.connect((host, port))
        s.close()
        return True
    except:
        return False

def find_free_port(start=8000, end=9000, host="127.0.0.1"):
    for p in range(start, end):
        if not is_port_in_use(p, host=host):
            return p
    raise RuntimeError("No free port found in range")

def kill_proc_group(pid):
    try:
        pgid = os.getpgid(pid)
        os.killpg(pgid, signal.SIGTERM)
        time.sleep(0.2)
        if os.killpg(pgid, 0):
            pass
    except Exception:
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception:
            pass