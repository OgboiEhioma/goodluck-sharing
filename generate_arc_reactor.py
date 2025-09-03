from PIL import Image, ImageDraw

def create_arc_reactor_icon(size=24, filename="arc_reactor.png"):
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((2, 2, size-2, size-2), fill="#ff0000", outline="#b71c1c", width=2)
    inner_size = size * 0.6
    offset = (size - inner_size) / 2
    draw.ellipse((offset, offset, size-offset, size-offset), fill="#00b0ff", outline="#0288d1")
    image.save(filename, format="PNG")

if __name__ == "__main__":
    create_arc_reactor_icon()