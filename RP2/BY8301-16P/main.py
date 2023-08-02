from machine import UART, Pin
import random
import _thread as threading
import time
import binascii
import gc


class Infrared:
    """
    红外信号触发音乐播放
    """

    machine_pin = Pin(18, machine.Pin.IN)

    @classmethod
    def enable(cls):
        cls.machine_pin.irq(trigger=Pin.IRQ_RISING, handler=lambda pin: cls.handler())

    @classmethod
    def disable(cls):
        cls.machine_pin.irq(handler=None)

    @classmethod
    def handler(cls):
        cls.disable()
        try:
            if get_play_state() not in [1, 3, 4]:
                random_play()
        except Exception as e:
            print("Except Error {}".format(e))
        cls.enable()


class Opcode:
    """
    BY8301-16P 操作码类
    """
    # 起始码
    START = 0x7E
    
    # 结束码
    END = 0xEF
    
    # 长度为三
    THREE_LENGTH = 0x03
    
    # 长度为四
    FOUR_LENGTH = 0x04
    
    # 长度为三
    FIVE_LENGTH = 0x05
    
    class Type:
        SET = 0
        GET = 1
    
    class ReplyType:
        ACK = 0
        HEX = 1
    
    def __init__(self, **kwargs):
        for name, value in kwargs.items():
            setattr(self, name, value)
    
    def __getattr__(self, name):
        if hasattr(name):
            return getattr(self, name)
        raise AttributeError("{} object has no attribute {}".format(self.__class__.__name__, name))
    
    def __str__(self):
        result = []
        for name, value in self.__dict__.items():
            if isinstance(value, str):
                value = '"{}"'.format(value)
            result.append('{}={}'.format(name, value))
        result = ", ".join(result)
        return "{}: {}{}{}".format(self.__class__.__name__, "[", result, "]")
    

"""
控制型操作码, 回复ASCK码
"""
PLAY = Opcode(cmd=0x01, desc="播放操作码", type=Opcode.Type.SET, param_byte_length=0)
PAUSE = Opcode(cmd=0x02, desc="暂停操作码", type=Opcode.Type.SET, param_byte_length=0)
NEXT = Opcode(cmd=0x03, desc="下一曲操作码", type=Opcode.Type.SET, param_byte_length=0)
PERVIOUS = Opcode(cmd=0x04, desc="上一曲操作码", type=Opcode.Type.SET, param_byte_length=0)
VOLUME_UP = Opcode(cmd=0x05, desc="上一曲操作码", type=Opcode.Type.SET, param_byte_length=0)
VOLUME_DOWN = Opcode(cmd=0x06, desc="上一曲操作码", type=Opcode.Type.SET, param_byte_length=0)
STANDY_OR_WORKING = Opcode(cmd=0x07, desc="待机或正常工作操作码，进入待机状态电流为10mA", type=Opcode.Type.SET, param_byte_length=0)
RESET = Opcode(cmd=0x09, desc="复位操作码", type=Opcode.Type.SET, param_byte_length=0)
STOP = Opcode(cmd=0x0E, desc="停止播放操作码", type=Opcode.Type.SET, param_byte_length=0)

"""
控制型操作码, 参数长度HEX
"""
SET_VOLUME = Opcode(cmd=0x31, desc="设置音量大小操作码， 0-30级可调（掉电记忆）", type=Opcode.Type.SET, param_byte_length=1)
SET_LOOP_PLAYBACK = Opcode(cmd=0x33, desc="设置循环播放模式操作码", type=Opcode.Type.SET, param_byte_length=1)
SELECT_PLAY = Opcode(cmd=0x41, desc="选曲播放操作码，1-255首（掉电记忆）", type=Opcode.Type.GET, param_byte_length=2)

"""
查询型操作码，参数长度 2 个字节
"""
GET_VOLUME = Opcode(cmd=0x11, desc="获取音量大小操作码", type=Opcode.Type.GET, param_byte_length=0)
PLAY_STATE = Opcode(cmd=0x10, desc="查询播放状态", type=Opcode.Type.SET, param_byte_length=0)
MUSIC_QUANTITY = Opcode(cmd=0x17, desc="查询 FLASH 总音乐文件数", type=Opcode.Type.GET, param_byte_length=0)

# 锁
LOCK = threading.allocate_lock()

gc.collect()


def xor(numbers: list):
    """
    遍历数字列表，计算异或值
    :param numbers: 数字列表
    :return 返回计算的异或值
    """
    xor_result = 0
    for num in numbers:
        xor_result ^= num
    return xor_result


def decimal_to_big_byte_list(number: int, byte_wide: int = 2):
    """
    数字转为指定的字节数组列表，按大端序排列
    :param number: 数字
    :param byte_wide: 字节宽度
    :return 返回字节数组
    """
    byte_list = []
    for index in range(0, byte_wide, 1):
        if index == 0:
            byte_list.append(number & 0xFF)
        else:
            byte = (number >> 8) & 0xFF
            byte_list.insert(0, byte)
    return byte_list


def generate_command(opcode: Opcode, *args):
    """
    合成命令
    :param opcode: 操作码对象
    :param args: 参数
    :return 返回生成的指令
    """
    command = []
    if opcode.param_byte_length == 0:
        command.append(Opcode.THREE_LENGTH)
        command.append(opcode.cmd)
        command.append(xor(command))

    elif opcode.param_byte_length == 1:
        if len(args) < 1:
            raise ValueError("opcode {} need one byte length param".format(opcode.desc))
        command.append(Opcode.FOUR_LENGTH)
        command.append(opcode.cmd)
        command.append(args[0])
        command.append(xor(command))
        
    elif opcode.param_byte_length == 2:
        if len(args) < 2:
            raise ValueError("opcode {} need two byte length param".format(opcode.desc))
        command.append(Opcode.FIVE_LENGTH)
        command.append(opcode.cmd)
        for arg in args:
            command.append(arg)
        command.append(xor(command))
    else:
        raise ValueError("opcode {} byte length param illegal".format(opcode.desc))
    
    #插入起始码
    command.insert(0, Opcode.START)
    #插入结束码
    command.append(Opcode.END)
    return command


def read_until_timeout(uart: UART, timeout: int = 10):
    """
    读取数据直到超时
    :param uart: UART串口通讯
    :param timeout: 超时时长，单位毫秒
    :return 返回字节bytes
    """
    receive_bytes = bytes()
    timeout = 10 * 1000
    start = time.ticks_us()
    while time.ticks_us() - start < timeout:
        if size := uart.any():
            receive_bytes += uart.read(size)
    return receive_bytes


def send_command(command: bytes, timeout: int = 100):
    """
    通过UART发送指令，
    params: command 字节指令， timeout: 读取超时，单位毫米
    """
    with LOCK:
        # 初始化UART串口对象
        uart = UART(0, baudrate=9600, tx=Pin(16), rx=Pin(17), timeout=1, bits=8, stop=1)
        # 读取uart缓存数据
        if size := uart.any():
            uart.read(size)
        # 发送指令
        uart.write(command)
        uart.flush()
        
        # 读取回应内容
        receive_bytes = read_until_timeout(uart, timeout)
        receive_str = receive_bytes.decode("utf-8")
        print("SEND -- {} RECEIVE -- {}".format(binascii.hexlify(command), receive_str))
        time.sleep_ms(10)
        return receive_str


def get_play_state():
    """
    获取播放状态
    :return 返回播放状态，0（定制）1（播放）2（暂停）3（快进）4（快退）
    """
    cmd = bytes(generate_command(PLAY_STATE))
    receive = send_command(cmd)
    return int(receive[2:], 16)


def random_play():
    """
    随机播放音乐
    """
    cmd = bytes(generate_command(MUSIC_QUANTITY))
    receive_str = send_command(cmd)
    if not receive_str or not receive_str.startswith("OK"):
        print("Query the music quantity of flash failed. Receive ACK: {}".format(receive_str))
        return
    music_quantity_str = receive_str.strip()[2:]
    if len(music_quantity_str) != 4:
        print("Query the music quantity of flash failed. Receive ACK: {}".format(receive_str))
    
    # 生成随机的音乐曲编号
    music_quantity = int(music_quantity_str, 16)
    random_number = random.randint(1, music_quantity)
    print("GENERATE RANDOM SONG NUMBER {}", random_number)
    args = decimal_to_big_byte_list(random_number, byte_wide=2)
    
    # 发送播放音乐
    cmd = bytes(generate_command(SELECT_PLAY, args[0], args[1]))
    receive_str = send_command(cmd)
    if receive_str.startswith("OK"):
        print("Random play success")
    else:
        print("Random play failed")


if __name__ == "__main__":
    Infrared.enable()