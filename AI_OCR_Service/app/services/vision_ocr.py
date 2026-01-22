import requests
from google.cloud import vision

def download_image(image_url: str) -> bytes:
    response = requests.get(image_url, timeout=10)
    response.raise_for_status()
    image_bytes = response.content
    return image_bytes


def extract_text_from_image(image_bytes: bytes) -> str:
    client = vision.ImageAnnotatorClient()

    image = vision.Image(content=image_bytes)
    
    # Use annotate_image with TEXT_DETECTION feature
    response = client.annotate_image({
        'image': image,
        'features': [{'type_': vision.Feature.Type.TEXT_DETECTION}],
    })

    if response.error.message:
        raise RuntimeError(response.error.message)

    # Full extracted text
    return response.full_text_annotation.text