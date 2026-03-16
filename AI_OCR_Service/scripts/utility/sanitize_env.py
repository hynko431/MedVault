import os

def sanitize_env():
    env_path = ".env"
    if not os.path.exists(env_path):
        print(f"{env_path} not found.")
        return

    with open(env_path, 'rb') as f:
        content = f.read()

    # Remove null bytes and other common UTF-16 artifacts if present
    clean_content = content.replace(b'\x00', b'')
    # If it starts with a BOM, strip it
    if clean_content.startswith(b'\xef\xbb\xbf'):
        clean_content = clean_content[3:]
    elif clean_content.startswith(b'\xff\xfe') or clean_content.startswith(b'\xfe\xff'):
        # Try to decode from UTF-16 and re-encode to UTF-8 if it's UTF-16
        try:
            text = content.decode('utf-16')
            clean_content = text.encode('utf-8')
        except:
            pass

    with open(env_path, 'wb') as f:
        f.write(clean_content)
    
    print("Sanitized .env")

if __name__ == "__main__":
    sanitize_env()
