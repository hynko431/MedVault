import httpx
import logging
import asyncio

logger = logging.getLogger(__name__)

MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB

class ImageDownloadError(Exception):
    """Raised when image download fails"""
    pass


async def download_image(image_url: str, timeout: int = 30) -> bytes:
    """
    Download image from URL with validation and safety checks (Asynchronous).
    
    Args:
        image_url: URL of the image to download
        timeout: Request timeout in seconds
        
    Returns:
        Image bytes
        
    Raises:
        ImageDownloadError: When download fails or image is invalid
    """
    try:
        logger.debug(f"Downloading image from: {image_url}")
        
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            # We use stream=True equivalent in httpx to check size before full download
            async with client.stream("GET", image_url) as response:
                response.raise_for_status()

                # 1️⃣ Validate Content-Type
                content_type = response.headers.get("Content-Type", "").lower()
                if not content_type.startswith("image/"):
                    raise ImageDownloadError(
                        f"URL did not return an image. Content-Type: {content_type}\n"
                        f"Expected: image/*, got: {content_type}"
                    )
                
                # 2️⃣ Validate Content-Length (if present)
                content_length = response.headers.get("Content-Length")
                if content_length:
                    try:
                        size = int(content_length)
                        if size > MAX_IMAGE_SIZE_BYTES:
                            raise ImageDownloadError(
                                f"Image too large. Size: {size} bytes, Max: {MAX_IMAGE_SIZE_BYTES} bytes (5MB)"
                            )
                    except ValueError:
                        logger.warning(f"Invalid Content-Length header: {content_length}")

                # 3️⃣ Read image safely (streamed)
                image_bytes = b""
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    image_bytes += chunk
                    if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
                        raise ImageDownloadError(
                            f"Image too large. Exceeded {MAX_IMAGE_SIZE_BYTES} bytes (5MB)"
                        )

                if not image_bytes:
                    raise ImageDownloadError("Downloaded image is empty")
                
                logger.info(f"✅ Image downloaded successfully. Size: {len(image_bytes)} bytes")
                return image_bytes

    except httpx.TimeoutException:
        raise ImageDownloadError(f"Image download timed out after {timeout}s")
    
    except httpx.HTTPStatusError as e:
        status_code = e.response.status_code
        raise ImageDownloadError(
            f"HTTP error downloading image. Status: {status_code}\n"
            f"URL: {image_url}\n"
            f"Error: {str(e)}"
        )

    except httpx.RequestError as e:
        raise ImageDownloadError(
            f"Failed to download image from {image_url}: {str(e)}\n"
            f"Check that the URL is valid and the image is accessible."
        )
    except ImageDownloadError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error downloading image: {str(e)}", exc_info=True)
        raise ImageDownloadError(f"Unexpected error: {str(e)}") from e
