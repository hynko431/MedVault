from google.cloud import vision

class OCRError(Exception):
    pass

def extract_text_from_image(image_bytes: bytes) -> str:
    try:
        # ADC is picked up automatically here
        client = vision.ImageAnnotatorClient()

        image = vision.Image(content=image_bytes)
        response = client.annotate_image({
            'image': image,
            'features': [{'type_': vision.Feature.Type.TEXT_DETECTION}],
        })
        # response = client.text_detection(image=image)

        if response.error.message:
            raise RuntimeError(response.error.message)
        
        texts = response.text_annotations
        if not texts:
            return ""
        
        # Full extracted text
        # return response.full_text_annotation.text
        
        #  Full OCR text is always the first entry
        return texts[0].description
    
    except Exception as e:
        raise OCRError(f"Vision OCR failed: {str(e)}")