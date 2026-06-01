import json, urllib.request, urllib.error, uuid

env = {}
with open('/home/ubuntu/.hermes/.env') as f:
    for line in f:
        line = line.strip()
        if line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        env[k.strip()] = v.strip()

email = env['CLOUDFLARE_EMAIL']
key = env['CLOUDFLARE_API_KEY']
acct = 'd112c7b38b3591cf210c334705454023'

# Resource IDs
D1_DB_ID = "b01c5c3e-99b3-4b06-b199-96b572fa9fee"
KV_NS_ID = "193f502738064686bdd4d673eea14f6b"
DO_NS_ID = "a54542a817634c29b0b16cfe1117d931"

# Read worker script
with open('/tmp/forexai-worker/worker.js', 'rb') as f:
    script = f.read()

print(f"Script size: {len(script):,} bytes")

# Build metadata - NO secrets (they persist from previous deploy)
metadata = {
    "main_module": "worker.js",
    "compatibility_date": "2024-01-01",
    "bindings": [
        # === EXISTING (9 non-secret) ===
        {"name": "DB", "type": "d1", "id": D1_DB_ID},
        {"name": "CACHE", "type": "kv_namespace", "namespace_id": KV_NS_ID},
        {"name": "USER_SESSION", "type": "durable_object_namespace", "class_name": "UserSessionDO", "namespace_id": DO_NS_ID},
        {"name": "FOREX_QUEUE", "type": "queue", "queue_name": "forex"},
        # === NEW (3) ===
        {"name": "AI", "type": "ai"},
        {"name": "R2", "type": "r2_bucket", "bucket_name": "forexai-reports"},
        {"name": "VECTOR_DB", "type": "vectorize", "index_name": "forexai-signals"}
    ]
}

print(f"Total bindings in metadata: {len(metadata['bindings'])}")
print("(8 secrets persist from previous deploy)")

boundary = uuid.uuid4().hex

parts = []
parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"metadata\"; filename=\"metadata.json\"\r\nContent-Type: application/json\r\n\r\n".encode())
parts.append(json.dumps(metadata).encode())
parts.append(f"\r\n--{boundary}\r\nContent-Disposition: form-data; name=\"worker.js\"; filename=\"worker.js\"\r\nContent-Type: application/javascript+module\r\n\r\n".encode())
parts.append(script)
parts.append(f"\r\n--{boundary}--\r\n".encode())

body = b"".join(parts)

url = f"https://api.cloudflare.com/client/v4/accounts/{acct}/workers/scripts/forexai"
req = urllib.request.Request(url, data=body, method="PUT", headers={
    "X-Auth-Email": email,
    "X-Auth-Key": key,
    "Content-Type": f"multipart/form-data; boundary={boundary}"
})

try:
    resp = urllib.request.urlopen(req)
    result = json.loads(resp.read())
    print(f"\nSUCCESS: {result.get('success', False)}")
    if result.get('result', {}).get('id'):
        print(f"Worker ID: {result['result']['id']}")
        print(f"Modified: {result['result'].get('modified_on', 'n/a')}")
        print(f"URL: https://forexai.airdropongol.workers.dev")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"\nHTTP {e.code}: {body[:500]}")
