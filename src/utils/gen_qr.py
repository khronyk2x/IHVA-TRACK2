import qrcode
import io

url = "https://shield-rainbow-travel-recipient.trycloudflare.com"

# 1. Generate PNG Image
qr = qrcode.QRCode(
    version=1,
    error_correction=qrcode.constants.ERROR_CORRECT_H,
    box_size=10,
    border=4,
)
qr.add_data(url)
qr.make(fit=True)

img = qr.make_image(fill_color="#1E3A8A", back_color="white")
img.save("/home/Onahi/Devdir/hack/doc/qrcode_tunnel.png")
print("Saved PNG to /home/Onahi/Devdir/hack/doc/qrcode_tunnel.png")

# 2. Generate ASCII QR Code to display in terminal
f = io.StringIO()
qr.print_ascii(out=f, invert=True)
f.seek(0)
ascii_qr = f.read()

with open("/home/Onahi/Devdir/hack/doc/qrcode_ascii.txt", "w", encoding="utf-8") as out:
    out.write(ascii_qr)

print("ASCII QR Generated.")