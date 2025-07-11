import machine
import neopixel
import time
import ntptime
import network
import urequests
import json
import socket
import struct
from font import font  # Nhập bộ font từ tệp font.py
from machine import UART, Pin, SoftI2C, SoftSPI, deepsleep, ADC
from machine import RTC, WDT

# Định nghĩa kích thước ma trận
WIDTH = 64  # Chiều rộng của ma trận LED
HEIGHT = 16  # Chiều cao của ma trận LED

# Số lượng LED
NUM_LEDS = WIDTH * HEIGHT

# Chân GPIO kết nối với DIN của LED
PIN = 32

# Khởi tạo neopixel
np = neopixel.NeoPixel(machine.Pin(PIN), NUM_LEDS)

def set_pixel(x, y, color):  # X là chiều rộng, Y là chiều cao
    if x < WIDTH and y < HEIGHT:
        # Tính toán chỉ số LED đúng
        if x % 2 == 0:  # Hàng chẵn
            index = x * HEIGHT + y
        else:  # Hàng lẻ
            index = x * HEIGHT + (HEIGHT - 1 - y)

        if 0 <= index < NUM_LEDS:  # Kiểm tra chỉ số LED
            np[index] = color

def show_matrix():
    np.write()

def clear():
    for i in range(NUM_LEDS):
        np[i] = (0, 0, 0)  # Tắt LED

def draw_char(char, x, y, color):  # X là chiều rộng, Y là chiều cao
    if char in font:
        bitmap = font[char]
        for row in range(len(bitmap)-1):
            for col in range(7):
                if bitmap[row] & (1 << (6 - col)):
                    set_pixel(x + col, y + row, color)  # Sử dụng đúng thứ tự
                else:
                    set_pixel(x + col, y + row, (0, 0, 0))  # Tắt LED

def draw_face(aqi):
    """Vẽ biểu tượng mặt cười hình tròn dựa trên giá trị AQI bằng mảng."""
    # Mặt cười được định nghĩa bằng mảng
    face_good = [
        [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0],
        [0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0],
        [0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0],
        [0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0],
        [1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 1],
        [1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 1],
        [1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1],
        [1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1],
        [1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1],
        [1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 1],
        [1, 1, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1, 1],
        [1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1],
        [0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0],
        [0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0],
        [0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0],
        [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0]
    ]
    face_fair = [
        [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0],
        [0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0],
        [0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0],
        [0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0],
        [1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 1],
        [1, 1, 0, 1, 1, 1, 1, 0, 0, 1, 1, 1, 1, 0, 1, 1],
        [1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1],
        [1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1],
        [1, 1, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1, 1],
        [1, 1, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1],
        [1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 1],
        [1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1],
        [0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0],
        [0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0],
        [0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0],
        [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0]
    ]

    # Khởi tạo màu sắc cho mặt
    if aqi == 1:  # Good
        face_color = (0, 255, 0)  # Xanh lá
        face_pattern = face_good
    elif aqi == 2:  # Fair
        face_color = (255, 255, 0)  # Vàng
        face_pattern = face_fair
    elif aqi == 3:  # Moderate
        face_color = (255, 165, 0)  # Cam
        face_pattern = face_fair
    elif aqi == 4:  # Unhealthy
        face_color = (255, 0, 0)  # Đỏ
        face_pattern = face_fair
    else:  # Hazardous
        face_color = (128, 0, 128)  # Tím
        face_pattern = face_fair

    # Vẽ mặt cười từ mảng
    for y in range(len(face_pattern)):
        for x in range(len(face_pattern[y])):
            if face_pattern[y][x] == 1:  # Nếu giá trị là 1, vẽ màu mặt
                set_pixel(x + 44, y, face_color)  # Dịch chuyển mặt về giữa ma trận
   
def scroll_text(text_scroll):
    """Chạy cả hai dòng văn bản từ phải sang trái."""    
    # Hiển thị PM2.5
    clear()
    x = WIDTH  # Bắt đầu từ bên phải
    while x > -len(text_scroll) * 8:
        for i, char in enumerate(text_scroll):
            draw_char(char, x + i * 8, 5, (255, 255, 0))  # Màu cam cho AQI
        show_matrix()
        time.sleep(0.02)  # Thời gian giữa các lần cập nhật
        x -= 1  # Di chuyển sang trái

