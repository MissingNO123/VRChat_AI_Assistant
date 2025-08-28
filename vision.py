import threading
import cv2 as cv
import numpy as np
import time
from pynput.keyboard import Listener, Key
from ultralytics import YOLO
from huggingface_hub import hf_hub_download
from PIL import Image
from io import BytesIO
import json
import base64
import os 

if os.name == 'nt':
    from bshot.screenshot import get_image
    import win32gui
else:
    pass  # Linux imports would go here

image_capture_size = (1280, 720)

def get_vrchat_window_windows() -> int | None:
    def callback(hwnd, hwnds):
        if win32gui.GetWindowText(hwnd) == "VRChat":
            hwnds.append(hwnd)
        return True
    hwnds = []
    win32gui.EnumWindows(callback, hwnds)
    if len(hwnds) == 0:
        return None
    return hwnds[0]


def get_vrchat_screenshot_windows() -> np.ndarray:
    hwnd = get_vrchat_window_windows()
    if hwnd is None:
        return None
    img = get_image(hwnd, method="windll")
    width, height, _ = img.shape
    img = cv.resize(img, image_capture_size, interpolation=cv.INTER_LANCZOS4) # Resize to a smaller size
    # Crop the titlebar/border
    img = img[32:, 8:]
    return img


def get_vrchat_screenshot_linux() -> np.ndarray:
    img = get_image("VRChat", method="xlib")
    if img is None:
        return None
    width, height, _ = img.shape
    img = cv.resize(img, image_capture_size, interpolation=cv.INTER_LANCZOS4) # Resize to a smaller size
    # Crop the titlebar/border
    img = img[32:, 8:]
    return img


def get_vrchat_screenshot() -> np.ndarray:
    if os.name == 'nt':
        return get_vrchat_screenshot_windows()
    else:
        return get_vrchat_screenshot_linux()


def convert_to_png(image: np.ndarray) -> BytesIO:
    rgb_image = cv.cvtColor(image, cv.COLOR_BGR2RGB)
    pil_image = Image.fromarray(rgb_image)
    with BytesIO() as output:
        pil_image.save(output, format='PNG')
        return output.getvalue()


def convert_to_b64(image: np.ndarray) -> str:
    return base64.b64encode(convert_to_png(image)).decode('utf-8')


def format_chatapi_img_obj(image_as_b64: str, text: str) -> dict:
    return {
        "role": "user",
        "content": [
            {
                "type": 'text',
                "text": text,
            },
            {
                "type": 'image_url',
                "image_url": {
                    "url": f'data:image/png;base64,{image_as_b64}'
                }
            }
        ],
    }


def truncate_dict_values(d, max_length=50, max_depth=10, depth=0):
    truncated = {}
    for k, v in d.items():
        if isinstance(v, dict) and depth < max_depth:
            truncated[k] = truncate_dict_values(v, max_length, max_depth, depth+1)
        else:
            v_str = str(v)
            if len(v_str) > max_length:
                v_str = v_str[:max_length] + "..."
            truncated[k] = v_str
    return truncated


if __name__ == "__main__":
    try:
        # Focus VRChat window
        win32gui.SetForegroundWindow(get_vrchat_window())
    except Exception as e:
        print(f"Error while focusing VRChat window: {str(e)}")

    img = get_vrchat_screenshot()
    if img is not None:
        cv.imshow("VRChat_Screenshot", img)
        cv.waitKey(0)
        cv.destroyAllWindows()
    image_as_b64 = convert_to_b64(img)
    image_as_json = format_chatapi_img_obj(image_as_b64, "Screenshot of VRChat")
    print(json.dumps(truncate_dict_values(image_as_json, max_length=500), indent=2))
