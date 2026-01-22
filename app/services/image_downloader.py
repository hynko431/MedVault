import requests

MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB

class ImageDownloadError(Exception):
    pass

def download_image(image_url: str) -> bytes:
    try:
        response = requests.get(image_url, timeout=10,stream=True)
        response.raise_for_status()

        # 1️⃣ Validate Content-Type
        content_type = response.headers.get("Content-Type", "")
        if not content_type.startswith("image/"):
            raise ImageDownloadError(
                f"URL did not return an image. Content-Type={content_type}"
            )
        
        # 2️⃣ Validate Content-Length (if present)
        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) > MAX_IMAGE_SIZE_BYTES:
            raise ImageDownloadError("Image too large (>5MB)")

        # 3️⃣ Read image safely (streamed)
        image_bytes = b""
        for chunk in response.iter_content(chunk_size=8192):
            image_bytes += chunk
            if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
                raise ImageDownloadError("Image too large (>5MB)")

        if not image_bytes:
            raise ImageDownloadError("Downloaded image is empty")
        
        # return response.content
        return image_bytes

    except requests.exceptions.Timeout:
        raise ImageDownloadError("Image download timed out")
    
    except requests.exceptions.HTTPError as e:
        raise ImageDownloadError(f"S3 returned HTTP error: {str(e)}")

    except requests.exceptions.RequestException as e:
        raise ImageDownloadError(f"Failed to download image: {str(e)}")
