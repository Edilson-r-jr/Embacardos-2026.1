import struct

MATRICULA = bytes([6,5,4,3,2,1])

def print_hex(label, data):
    print(f"{label}: {' '.join(f'{b:02X}' for b in data)}")

def pack_int(value):
    return struct.pack('<i', value)

def unpack_int(data):
    return struct.unpack('<i', data)[0]

def pack_float(value):
    return struct.pack('<f', value)

def unpack_float(data):
    return struct.unpack('<f', data)[0]