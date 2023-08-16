import hashlib
import struct
import time
import math
import numpy as np

# 定义4个自定义函数
F = lambda b, c, d: (b & c) | (~b & d)
G = lambda b, c, d: (b & d) | (c & ~d)
H = lambda b, c, d: b ^ c ^ d
I = lambda b, c, d: c ^ (b | ~d)
# 定义左循环操作
L = lambda x, n: ((x << n) | (x >> (32 - n)))
# 定义每轮中循环左移的位数，用元组表示 4*4*4=64
R = (7, 12, 17, 22) * 4 + (5, 9, 14, 20) * 4 + \
    (4, 11, 16, 23) * 4 + (6, 10, 15, 21) * 4
# 定义常数K 64
K = tuple(((int(abs(math.sin(i + 1)) * 2 ** 32)) & 0xffffffff for i in range(0, 64, 1)))
np.set_printoptions(linewidth=1000)
np.set_printoptions(formatter={'int': '0x{:0>8x}'.format})
print('自定义常量数组')
print(f'K = tuple(((int(abs(math.sin(i + 1)) * 2 ** 32)) & 0xffffffff for i in range(0, 64, 1))), {np.array(K).reshape((-1,4))}')
# 将四个8位无符号数转化为一个32位无符号数，小端序
W = lambda i4, i3, i2, i1: (i1 << 24) | (i2 << 16) | (i3 << 8) | i4
# 字节翻转 0x12345678 -> 0x78563412 将一个32位无符号数的高位和低位进行对换
reverse = lambda x: (x << 24) & 0xff000000 | (x << 8) & 0x00ff0000 | \
                    (x >> 8) & 0x0000ff00 | (x >> 24) & 0x000000ff
# 符号集合
symbol = lambda i: ['a', 'b', 'c', 'd'][i % 4]


# 填充，分组
def pre_deal(data: bytes) -> list:
    # data 转换为数字列表
    chars = [x for x in data]
    msg_length = len(chars) * 8
    # 对每一个输入先添加一个'0x80'，即'0b10000000', 即128
    chars.append(128)
    # 补充0
    while (len(chars) * 8 + 64) % 512 != 0:
        chars.append(0)
    # 最后64为存放消息长度，以小端数存放。
    for i in range(8):
        chars.append((msg_length >> (8 * i)) & 0xff)
    return chars


# 输入previous vector, 一组数据， 得到 updated vector
def vector_update(pre_vector_a: int, pre_vector_b: int, pre_vector_c: int, pre_vector_d: int, chars: list):
    assert chars.__len__() == 64
    a, b, c, d = pre_vector_a, pre_vector_b, pre_vector_c, pre_vector_d
    print(f'初始向量为 a: 0x{a:x} b: 0x{b:x} c: 0x{c:x} d: 0x{d:x}')
    for i in range(64):
        # a d c b的顺序进行更新，每次更新后通过移动位置来保证公式一致性
        # g表示chars 中的第几个 32bit word,一共16个32bit word
        if 0 <= i <= 15:
            f = F(b, c, d) & 0xffffffff
            g = i
        elif 16 <= i <= 31:
            f = G(b, c, d) & 0xffffffff
            g = ((5 * i) + 1) % 16
        elif 32 <= i <= 47:
            f = H(b, c, d) & 0xffffffff
            g = ((3 * i) + 5) % 16
        else:
            f = I(b, c, d) & 0xffffffff
            g = (7 * i) % 16
        # 第g个32-bit
        a_before = a
        w = W(chars[g * 4], chars[g * 4 + 1], chars[g * 4 + 2], chars[g * 4 + 3])
        a = (L((a + f + K[i] + w) & 0xffffffff, R[i]) + b) & 0xffffffff
        # print(i,a,b,c,d) #debug 使用
        if i // 16 == 0:
            # F = lambda b, c, d: (b & c) | ((~b) & d)
            print('-'*20)
            print(f'{symbol(-i)}= ({symbol(-i)}  + (({symbol(-i + 1)} & {symbol(-i + 2)}) | (~ {symbol(-i + 1)} & {symbol(-i + 3)})) + 常量K{i+1} + W[{g}] )<< {R[i]} + {symbol(-i + 1)} ')
            print(f'0x{a:x} = (0x{a_before:x} + (( 0x{b:x} & 0x{c:x} ) | (~ 0x{b:x} & 0x{d:x})) + 0x{K[i]:x} + 0x{w:0>8x} )<< {R[i]} + 0x{b:x} ')
        if i // 16 == 1:
            # G = lambda b, c, d: (b & d) | (c & ~d)
            print('-'*20)
            print(f'{symbol(-i)}= ({symbol(-i)}  + (({symbol(-i + 1)} & {symbol(-i + 3)}) | ({symbol(-i + 2)} & ~ {symbol(-i + 3)})) + 常量K{i+1} + W[{g}] )<< {R[i]} + {symbol(-i + 1)} ')
            print(f'0x{a:x} = (0x{a_before:x} + (( 0x{b:x} & 0x{d:x} ) | (0x{c:x} & ~ 0x{d:x})) + 0x{K[i]:x} + 0x{w:0>8x} )<< {R[i]} + 0x{b:x} ')
        if i // 16 == 2:
            # H = lambda b, c, d: b ^ c ^ d
            print('-'*20)
            print(f'{symbol(-i)}= ({symbol(-i)}  + ({symbol(-i + 1)} ^ {symbol(-i + 2)} ^ {symbol(-i + 3)}) + 常量K{i+1} + W[{g}]<< {R[i]} + {symbol(-i + 1)} ')
            print(f'0x{a:x} = (0x{a_before:x} + ( 0x{b:x} ^ 0x{c:x} ^ 0x{d:x}) + 0x{K[i]:x} + 0x{w:0>8x} )<< {R[i]} + 0x{b:x} ')
        if i // 16 == 3:
            # I = lambda b, c, d: c ^ (b | ~d)
            print('-'*20)
            print(f'{symbol(-i)}= ({symbol(-i)}  + ({symbol(-i + 2)} ^ ( {symbol(-i + 1)} | ~  {symbol(-i + 3)})) + 常量K{i+1} + W[{g}]<< {R[i]} + {symbol(-i + 1)} ')
            print(f'0x{a:x} = (0x{a_before:x} + ( 0x{c:x}  ^ ( 0x{b:x} | ~ 0x{d:x})) + 0x{K[i]:x} + 0x{w:0>8x} )<< {R[i]} + 0x{b:x} ')
        a, b, c, d = d, a, b, c
        if i % 4 == 0:
            print(f'第{i + 1: >2}轮, 更新a：\033[0;37;41m0x{b:x}\033[0m 0x{c:x} 0x{d:x} 0x{a:x}')
        if i % 4 == 1:
            print(f'第{i + 1: >2}轮, 更新d：0x{c:x} 0x{d:x} 0x{a:x} \033[0;37;41m0x{b:x}\033[0m')
        if i % 4 == 2:
            print(f'第{i + 1: >2}轮, 更新c：0x{d:x} 0x{a:x} \033[0;37;41m0x{b:x}\033[0m 0x{c:x}')
        if i % 4 == 3:
            print(f'第{i + 1: >2}轮, 更新b：0x{a:x} \033[0;37;41m0x{b:x}\033[0m 0x{c:x} 0x{d:x}')
    update_vector_a = (pre_vector_a + a)&0xffffffff
    update_vector_b = (pre_vector_b + b)&0xffffffff
    update_vector_c = (pre_vector_c + c)&0xffffffff
    update_vector_d = (pre_vector_d + d)&0xffffffff
    print('-' * 20)
    print(f'update_vector_a = pre_vector_a + a = 0x{pre_vector_a:0>8x} + 0x{a:0>8x} = 0x{update_vector_a:0>8x}')
    print(f'update_vector_b = pre_vector_b + b = 0x{pre_vector_b:0>8x} + 0x{b:0>8x} = 0x{update_vector_b:0>8x}')
    print(f'update_vector_c = pre_vector_c + c = 0x{pre_vector_c:0>8x} + 0x{c:0>8x} = 0x{update_vector_c:0>8x}')
    print(f'update_vector_d = pre_vector_d + d = 0x{pre_vector_d:0>8x} + 0x{d:0>8x} = 0x{update_vector_d:0>8x}')
    print(f'更新所有向量：0x{update_vector_a:0>8x} 0x{update_vector_b:0>8x} 0x{update_vector_c:0>8x} 0x{update_vector_d:0>8x}')
    return update_vector_a, update_vector_b, update_vector_c, update_vector_d


def udf_md5(data: bytes):
    a = 0x67452301
    b = 0xefcdab89
    c = 0x98badcfe
    d = 0x10325476
    chars = pre_deal(data)
    np.set_printoptions(linewidth=1000)
    np.set_printoptions(formatter={'int': '0x{:0>2x}'.format})
    print('\nstep 1: 原始数据进行填充和分段，每一段512bit')
    print('data数据单个字节(8bit) 16进制表示')
    for i in range(chars.__len__() // 64):
        print(f'第{i + 1}段')
        print(np.array(chars[64 * i:64 * i + 64]).reshape((4, 16)))
    chars_32 = [W(chars[4 * i], chars[4 * i + 1], chars[4 * i + 2], chars[4 * i + 3]) for i in
                range(chars.__len__() // 4)]
    np.set_printoptions(formatter={'int': '0x{:0>8x}'.format})
    print('\ndata数据32bit word 16进制表示')
    for i in range(chars_32.__len__() // 16):
        print(f'第{i + 1}段')
        print(np.array(chars_32[16 * i:16 * i + 16]).reshape((4, 4)))
    print('\n\nstep 2: 定义初始化向量')
    print(f'a: 0x{a:0>8x}')
    print(f'b: 0x{b:0>8x}')
    print(f'c: 0x{c:0>8x}')
    print(f'd: 0x{d:0>8x}')
    turns = chars.__len__() // 64
    print('\n\nstep 3: 更新向量')
    for turn in range(turns):
        print(f'\n\n第{turn + 1} 段数据更新向量(共64轮)：')
        a, b, c, d = vector_update(a, b, c, d, chars[64 * turn:64 * turn + 64])
    print('\n\nstep 4: 得到结果')
    print(f'向量为 a: 0x{a:0>8x} b: 0x{b:0>8x} c: 0x{c:0>8x} d: 0x{d:0>8x}')
    a, b, c, d = reverse(a), reverse(b), reverse(c), reverse(d)
    digest = (a << 96) | (b << 64) | (c << 32) | d
    print(f'digest: {hex(digest)[2:].rjust(32,"0")}')
    return hex(digest)[2:].rjust(32, '0')


if __name__ == '__main__':
    data = b'hello world'*10
    print(f'\n\n输入data: {data}')
    hashlib.md5(data)
    time1 = time.time()
    md51 = udf_md5(data)
    time2 = time.time()
    md52 = hashlib.md5(data).hexdigest()
    time3 = time.time()
    print(f'udf_md5:{md51}, time consumpt: {time2 - time1}')
    print(f'hexdigest:{md52}, time consumpt: {time3 - time2}')
