"""Создаёт простой логотип, иконку и явно обозначенную заглушку для отсутствующих фото."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "import"
ASSETS.mkdir(parents=True, exist_ok=True)
FONT_PATHS = ["C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
BOLD_PATHS = ["C:/Windows/Fonts/arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]

def font(paths, size):
    for path in paths:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()

# Это иллюстрированная заглушка, а не фотография товара.
image = Image.new("RGB", (400, 300), "#F3F5F4")
draw = ImageDraw.Draw(image)
draw.rounded_rectangle((12, 12, 388, 288), radius=20, outline="#C8D7D4", width=3)
# условный диван
wood = "#A87953"
seat = "#6A8E89"
draw.rounded_rectangle((105, 112, 295, 190), radius=18, fill=seat)
draw.rounded_rectangle((85, 140, 120, 205), radius=12, fill=seat)
draw.rounded_rectangle((280, 140, 315, 205), radius=12, fill=seat)
draw.rectangle((125, 188, 137, 215), fill=wood)
draw.rectangle((265, 188, 277, 215), fill=wood)
draw.line((135, 214, 126, 227), fill=wood, width=8)
draw.line((269, 214, 278, 227), fill=wood, width=8)
text = "ФОТО НЕ ПРЕДОСТАВЛЕНО"
b = draw.textbbox((0, 0), text, font=font(BOLD_PATHS, 18))
draw.text(((400-(b[2]-b[0]))/2, 244), text, fill="#40504D", font=font(BOLD_PATHS, 18))
image.save(ASSETS / "picture.png")

# Логотип учебного приложения
logo = Image.new("RGB", (620, 150), "#008080")
draw = ImageDraw.Draw(logo)
draw.rounded_rectangle((18, 18, 132, 132), radius=24, fill="#FFFFFF")
draw.polygon([(42, 82), (75, 48), (108, 82), (100, 82), (100, 112), (83, 112), (83, 91), (67, 91), (67, 112), (50, 112), (50, 82)], fill="#008080")
draw.text((158, 35), "МЕБЕЛЬМАРКЕТ", fill="white", font=font(BOLD_PATHS, 38))
draw.text((160, 91), "УЧЕБНОЕ ПРИЛОЖЕНИЕ · ВАРИАНТ 5", fill="#E4F2EF", font=font(FONT_PATHS, 18))
logo.save(ASSETS / "logo.png")

icon = Image.new("RGBA", (256, 256), "#008080")
draw = ImageDraw.Draw(icon)
draw.rounded_rectangle((20, 20, 236, 236), radius=42, fill="white")
draw.polygon([(54, 126), (128, 58), (202, 126), (184, 126), (184, 196), (149, 196), (149, 151), (107, 151), (107, 196), (72, 196), (72, 126)], fill="#008080")
icon.save(ASSETS / "app.ico", format="ICO", sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
print("Созданы import/picture.png, logo.png, app.ico")
