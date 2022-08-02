import re

PRNG_SEED = 0

def is_valid_config(config):
    if config[:3] != "\x0c\x0c\x0c":
        return False
    return config.count("\x0C\x0C\x0C") >= 15

def get_next_rng_value():
    global PRNG_SEED
    PRNG_SEED = ((PRNG_SEED * 1140671485 + 12820163) & 0xffffff)
    return PRNG_SEED / 65536

def decrypt_configuration(hex):
    global PRNG_SEED
    ascii = hex.decode('hex')
    tail = ascii[0x20:]

    pre_check = [ord(tail[x]) ^ 0x0c for x in xrange(3)]
    for x in xrange(0xffffff):
        PRNG_SEED = x
        if get_next_rng_value() != pre_check[0] or get_next_rng_value() != pre_check[1] or get_next_rng_value() != pre_check[2]:
            continue
        PRNG_SEED = x
        config = "".join((chr(ord(c) ^ int(get_next_rng_value())) for c in tail))
        if is_valid_config(config):
            return config.split("\x0c\x0c\x0c")

def config_extract(raw_data):
    config_pattern = re.findall('[0-9a-fA-F]{154,}', raw_data)
    for s in config_pattern:
        if (len(s) % 2) == 1:
            s = s[:-1]
        return s

def config_parser(config):
    return {
        'Domain': config[1],
        'Client Control Port': config[2],
        'Client Transfer Port': config[3],
        'Campaign ID': config[4],
        'File Name': config[5],
        'Install Path': config[6],
        'Registry Key': config[7],
        'ActiveX Key': config[8],
        'Install Flag': config[9],
        'Hide File': config[10],
        'Melt File': config[11],
        'Delay': config[12],
        'USB Spread': config[13],
        'Mutex': config[14],
        'Log File': config[15],
        'Folder Name': config[16],
        'Smart DNS': config[17],
        'Protect Process': config[18],
    }
        
def config(data):
    if raw_config := config_extract(data):
        config = decrypt_configuration(raw_config)
        if config and len(config) > 15:
            return config_parser(config)