from machine import Pin, UART, WDT
from hx711 import *
import struct
from binascii import hexlify, unhexlify
import json
import uasyncio as asyncio

begin = -636200

factor = (-615100 - begin) / 100


class WatchDog:
    """
    看门狗(WDT)
    """
    timer = machine.Timer(-1)

    @classmethod
    def disable(cls):
        machine.mem32[0x40058000] = machine.mem32[0x40058000] & ~(1<<30)
        cls.timer.deinit()

    @classmethod
    def enable(cls):
        wdt = machine.WDT(timeout=5000)
        cls.timer.init(period=3000, mode=machine.Timer.PERIODIC, callback=lambda t: cls.feed(wdt=wdt))

    @classmethod
    def feed(cls, wdt):
        wdt.feed()
        
        
async def board_led_blink():
    board_led = Pin(25, Pin.OUT)
    while True:
        board_led.toggle()
        await asyncio.sleep_ms(300)
        
        
def calculate_sum_check(data):
    sum_value = sum(data) & 0xFF
    return "{:02X}".format(sum_value)


def hex_byte_spilt(hex_str: str):
    """
    将16进制字符串按字节分割，存进字节列表
    :param hex_str: 16进制字符串
    """
    byte_list = []
    length = len(hex_str)
    for index in range(0, length, 2):
        hex_byte_str = hex_str[index: index + 2]
        byte = int(hex_byte_str, 16)
        byte_list.append(byte)
    return byte_list


def hex_str_to_byte_list(hex_str: str):
    hex_byte_list = []
    number = int(hex_str, 16)
    length = len(hex_str)
    for index in range(0, length, 2):
        if index == 0:
            hex_byte_list.append(number & 0xFF)
        else:
            number = number >> 8
            hex_byte_list.insert(0, number & 0xFF)
    return hex_byte_list


def calculate_checksum(hex_str: str):
    """
    计算和校验
    :param hex_str: 16进制字符串
    :return if sumcheck is right return True, otherwise return Flase
    """
    sum_check_byte = hex_str_to_byte_list(hex_str)[-1]
    sum_value = sum(hex_str_to_byte_list(hex_str)[0: -1]) & 0xFF
    return sum_check_byte == sum_value


def float_to_hex_str(float_number: float):
    
    """
    浮点数转16进制字符串，其中 '>f' 表示大端序的格式
    :param float_number: 浮点数
    :return 大端序的16进制字符串
    """
    pack_data = struct.pack(">f", float_number)
    return ''.join('{:02X}'.format(x) for x in pack_data)


def append_checksum(hex_data: str):
    """
    最佳和校验
    :param hex_data: 16进制字符串数据
    """
    hex_byte_list = hex_str_to_byte_list(hex_data)
    sum_value = sum(hex_byte_list) & 0xFF
    sum_value = "{:02X}".format(sum_value)
    return hex_data + sum_value


def get_weight():
    """
    读取称的重量
    :return 返回当前实物重量，单位克，initalise the hx711 with pin 3 as clock pin, pin 4 as data pin
    """
    with hx711(Pin(3), Pin(4)) as hx:
        hx.set_power(hx711.power.pwr_up)
        hx.set_gain(hx711.gain.gain_128)
        value = hx.get_value()
        print("传感器系数: {}".format(value))
        weight = (value - begin) / factor
        return weight
    

def generate_reply_hex_cmd(weight: float):
    """
    生成16进制回复指令
    """
    hex_str = "0101"
    weight_hex = float_to_hex_str(weight)
    data_length_hex = "{:02X}".format(len(weight_hex))
    hex_str = hex_str + data_length_hex + weight_hex
    return append_checksum(hex_str)


def read_until_timeout(uart: UART, timeout: int = 1000):
    """
    读取串口数据直到超时
    :param uart: UART串口对象
    :param timeout: 读取超时时间，单位微妙, 默认读取1000us
    """
    start = time.ticks_us()
    receive_bytes = bytes()
    while time.ticks_us() - start < timeout:
        if size := uart.any():
            receive_bytes += uart.read(size)
    return receive_bytes

    
async def android_transmission():
    """
    Transmission to Android
    """
    print("Android Transmission Server StartUp.")
    # 安卓上位机通讯
    uart = UART(0, baudrate=115200, tx=Pin(0), rx=Pin(1))
    while True:
        try:
            if not uart.any():
                continue
            receive_bytes = read_until_timeout(uart, 1000)
            if receive_bytes == None or len(receive_bytes) == 0 or receive_bytes == b'\x00':
                continue
            receive_str = hexlify(receive_bytes).decode("utf-8")
            if not calculate_checksum(receive_str):
                raise ValueError("The checksum illegal!")
                continue
            if receive_str.upper() == "01010103":
                weight = get_weight()
                reply_hex = generate_reply_hex_cmd(weight).upper()
                uart.write(unhexlify(reply_hex))
                uart.flush()
        except Exception as e:
            print("Error: {}".format(e))


if __name__ == "__main__":
    
    WatchDog.enable()
    loop = asyncio.get_event_loop()
    loop.create_task(android_transmission())
    loop.create_task(board_led_blink())
    loop.run_forever()