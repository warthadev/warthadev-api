import requests, socket, re, time

def doh_resolves(hostname, timeout=5):
    urls = [
        f"https://cloudflare-dns.com/dns-query?name={hostname}&type=A",
        f"https://dns.google/resolve?name={hostname}&type=A",
        f"https://cloudflare-dns.com/dns-query?name={hostname}&type=AAAA",
        f"https://dns.google/resolve?name={hostname}&type=AAAA"
    ]
    headers = {"Accept":"application/dns-json"}
    for u in urls:
        try:
            r = requests.get(u, headers=headers, timeout=timeout)
            if r.status_code == 200:
                j = r.json()
                if j.get("Status") == 0 and j.get("Answer"):
                    return True
        except Exception:
            continue
    try:
        socket.getaddrinfo(hostname, None)
        return True
    except Exception:
        return False