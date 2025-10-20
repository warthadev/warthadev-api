import os, subprocess, time, re, signal, socket, requests

CLOUDFLARED_BIN = os.path.join(os.getcwd(), "cloudflared-linux-amd64")
CLOUDFLARE_TIMEOUT = 60
DNS_CHECK_TIMEOUT = 90
CLOUDFLARED_RESTARTS = 3
RETRY_DELAY = 2

def doh_resolves(hostname, timeout=5):
    urls = [f"https://cloudflare-dns.com/dns-query?name={hostname}&type=A",
            f"https://dns.google/resolve?name={hostname}&type=A"]
    headers = {"Accept":"application/dns-json"}
    for u in urls:
        try:
            r = requests.get(u, headers=headers, timeout=timeout)
            if r.status_code==200 and r.json().get("Answer"): return True
        except: continue
    try: socket.getaddrinfo(hostname, None); return True
    except: return False

def ensure_cloudflared():
    if os.path.exists(CLOUDFLARED_BIN) and os.access(CLOUDFLARED_BIN, os.X_OK): return True
    os.system(f"wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O {CLOUDFLARED_BIN}")
    os.chmod(CLOUDFLARED_BIN,0o755)
    return True

def start_cloudflared(proc_args):
    return subprocess.Popen(proc_args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, preexec_fn=os.setsid)

def stop_proc(proc):
    try:
        if proc and proc.poll() is None:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            time.sleep(0.3)
            if proc.poll() is None: os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except: pass

def run_tunnel(port):
    if not ensure_cloudflared():
        print("cloudflared tidak tersedia."); return
    proc=None
    restarts=0
    while restarts<=CLOUDFLARED_RESTARTS:
        restarts+=1
        print(f"[TUNNEL] mencoba (attempt {restarts}/{CLOUDFLARED_RESTARTS})...")
        args=[CLOUDFLARED_BIN, "tunnel", "--url", f"http://127.0.0.1:{port}", "--no-autoupdate"]
        proc=start_cloudflared(args)
        if not proc: time.sleep(2); continue
        start=time.time(); public_url=None
        while time.time()-start < CLOUDFLARE_TIMEOUT:
            try: line=proc.stdout.readline()
            except: line=""
            if not line: time.sleep(RETRY_DELAY); continue
            m=re.search(r'(https://[^\s]+\.trycloudflare\.com)', line)
            if m: public_url=m.group(1); break
        if public_url:
            hostname=re.sub(r'^https?://', '', public_url).split('/')[0]
            dns_start=time.time(); resolved=False
            while time.time()-dns_start<DNS_CHECK_TIMEOUT:
                if doh_resolves(hostname, timeout=3): resolved=True; break
                time.sleep(1)
            if resolved: print(f"[TUNNEL] URL publik: {public_url}"); return
        stop_proc(proc)