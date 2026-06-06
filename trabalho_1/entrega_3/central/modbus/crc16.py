def CRC16(crc, data):
    crc ^= data
    for _ in range(8):
        if crc & 1:
            crc = (crc >> 1) ^ 0xA001
        else:
            crc >>= 1
    return crc & 0xFFFF


def calcula_crc(commands: bytes):
    crc = 0
    for b in commands:
        crc = CRC16(crc, b)
    return crc


def append_crc(packet: bytes):
    crc = calcula_crc(packet)
    crc_low = crc & 0xFF
    crc_high = (crc >> 8) & 0xFF
    return packet + bytes([crc_low, crc_high])


def validate_crc(response: bytes):
    data = response[:-2]
    received_crc = (
        response[-2] |
        (response[-1] << 8)
    )
    calculated_crc = calcula_crc(data)
    return received_crc == calculated_crc
