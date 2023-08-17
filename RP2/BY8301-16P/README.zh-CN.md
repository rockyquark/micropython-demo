# 基于 BY8301-16P RP2 HC-SR501 进行随机曲目播报

## 硬件环境
+ RP2040 PICO 单片机 [Link](https://www.raspberrypi.com/documentation/microcontrollers/raspberry-pi-pico.html)
+ BY8301-16P 串口语音模块 [Link](https://detail.tmall.com/item.htm?abbucket=16&id=645690421792&ns=1&spm=a21n57.1.0.0.6456523c0vy08H) 
+ 8Ω1W 无源喇叭 [Link](https://detail.tmall.com/item.htm?abbucket=16&id=536616543645&ns=1&spm=a21n57.1.0.0.1850523clgaMc3&skuId=3740943541805)
+ HC-SR501 人体红外 [Link](https://detail.tmall.com/item.htm?abbucket=16&id=13300633795&ns=1&spm=a21n57.1.0.0.1850523clgaMc3)

## 软件环境
- MicrpPython RP2 文档 [Link](https://docs.micropython.org/en/latest/rp2/quickref.html)
- MicrpPython RP2 UF2 固件 [Link](https://micropython.org/download/rp2-pico/) [Downoad](https://micropython.org/download/rp2-pico/rp2-pico-latest.uf2)
- MicrpPython RP2 UF2 擦除固件 [Link](https://www.raspberrypi.com/documentation/microcontrollers/raspberry-pi-pico.html#resetting-flash-memory) [Download](https://datasheets.raspberrypi.com/soft/flash_nuke.uf2) [Github](https://github.com/raspberrypi/pico-examples/blob/master/flash/nuke/nuke.c)

## IDE
### Thonny 开发工具 [Link](https://thonny.org)