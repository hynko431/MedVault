# Module-level environment configuration
import os
import asyncio
from typing import Optional
import io
from pathlib import Path
from app.core.logging.logger import get_logger

logger = get_logger("paddle_ocr")


class PaddleOCRError(Exception):
    """Custom exception for PaddleOCR errors."""
    pass


class PaddleOCRService:
    _instance = None
    model_lock: Optional[asyncio.Lock] = None
    _initialized = False
    model = None
    tokenizer = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PaddleOCRService, cls).__new__(cls)
            cls._instance.model_lock = asyncio.Lock()
        return cls._instance

    async def _initialize(self):
        """Async-safe lazy initialization of PaddleOCR-VL."""
        # Strict None guard for lazy initialization
        lock = self.model_lock
        if lock is None:
            raise RuntimeError("model_lock not initialized. Call __new__ logic correctly.")
            
        async with lock:
            if self._initialized:
                return
            logger.info("Initializing Local PaddleOCR (Fallback)...")
            try:
                import torch
                from transformers import AutoModelForCausalLM, AutoProcessor
                
                # Get model path from environment or use default
                model_path = os.getenv("PADDLE_OCR_MODEL_PATH")
                if not model_path:
                    # Try to find in common locations
                    possible_paths = [
                        "/app/models/PaddleOCR-VL",
                        "/opt/models/PaddleOCR-VL",
                        str(Path.home() / ".paddlex/official_models/PaddleOCR-VL"),
                        "C:\\Users\\hulkh\\.paddlex\\official_models\\PaddleOCR-VL",
                    ]
                    for path in possible_paths:
                        if Path(path).exists():
                            model_path = path
                            break
                
                if not model_path or not Path(model_path).exists():
                    raise PaddleOCRError(
                        f"PaddleOCR model not found. Set PADDLE_OCR_MODEL_PATH "
                        f"or ensure model exists at one of: {possible_paths}"
                    )
                
                logger.info(f"Loading PaddleOCR model from: {model_path}")
                self.tokenizer = AutoProcessor.from_pretrained(model_path, trust_remote_code=True)
                model = AutoModelForCausalLM.from_pretrained(
                    model_path, trust_remote_code=True, dtype=torch.float32, low_cpu_mem_usage=True
                )
                model.to("cpu")  # type: ignore
                model.eval()
                self.model = model
                self._initialized = True
            except Exception as e:
                logger.error(f"PaddleOCR init failed: {e}")
                raise PaddleOCRError(f"Init failed: {e}") from e

    async def ocr(self, image_data: bytes) -> str:
        await self._initialize()
        try:
            from PIL import Image
            import torch
            image = Image.open(io.BytesIO(image_data)).convert("RGB")
            messages = [{"role": "user", "content": [{"type": "image", "image": "placeholder"}, {"type": "text", "text": "OCR:"}]}]
            
            # Ensure model and processor are initialized
            if self.tokenizer is None or self.model is None:
                raise RuntimeError(
                    "Model/tokenizer not loaded. Call load_model() before inference."
                )
            
            # Local copies to satisfy type narrowing
            tok = self.tokenizer
            mod = self.model

            prompt = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True) # type: ignore
            inputs = tok(text=[prompt], images=[image], return_tensors="pt").to("cpu")
            with torch.no_grad():
                ids = mod.generate(**inputs, max_new_tokens=256, do_sample=False) # type: ignore
            decoded = tok.batch_decode(ids, skip_special_tokens=True) # type: ignore
            output = decoded[0]
            text = output.split("OCR:", 1)[1].strip() if "OCR:" in output else output.strip()
            return text
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            raise PaddleOCRError(str(e)) from e


async def extract_text_with_paddle(image_bytes: bytes) -> str:
    service = PaddleOCRService()
    return await service.ocr(image_bytes)