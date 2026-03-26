import win32gui
import mss
from PIL import Image
import pytesseract

hwnds = []
def callback(w, _):
    if win32gui.IsWindowVisible(w) and "Grass" in win32gui.GetWindowText(w):
        hwnds.append(w)
win32gui.EnumWindows(callback, None)

if not hwnds:
    print("Grass not found")
    exit()

hwnd = hwnds[0]
rect = win32gui.GetWindowRect(hwnd)
left, top, right, bottom = rect

with mss.mss() as sct:
    monitor = {"top": top, "left": left, "width": right-left, "height": bottom-top}
    sct_img = sct.grab(monitor)
    img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
    
    img = img.convert('L')
    img = img.resize((img.width * 2, img.height * 2), Image.Resampling.LANCZOS)
    
    print("------ PSM 11 (Sparse Text) ------")
    data = pytesseract.image_to_string(img, config='--psm 11')
    print(data)
    
    print("\n------ PSM 3 (Auto OS) ------")
    data = pytesseract.image_to_string(img, config='--psm 3')
    print(data)
    
    # Let's try aggressive thresholding
    img_thresh = img.point(lambda x: 0 if x < 150 else 255)
    print("\n------ PSM 11 + Hard Threshold ------")
    data = pytesseract.image_to_string(img_thresh, config='--psm 11')
    print(data)
