from pathlib import Path

import shutil

assets_dir = Path(__file__).parent.parent / "assets"


def configure_ocr_model():
    shutil.copytree(
        assets_dir / "MaaCommonAssets" / "OCR" / "ppocr_v4" / "en_us",
        assets_dir / "resource" / "base" / "model" / "ocr",
        dirs_exist_ok=True,
    )

    shutil.copy2(
        assets_dir / "MaaCommonAssets" / "OCR" / "ppocr_v3" / "en_us" / "det.onnx",
        assets_dir / "resource" / "base" / "model" / "ocr" / "det.onnx",
    )


if __name__ == "__main__":
    configure_ocr_model()
