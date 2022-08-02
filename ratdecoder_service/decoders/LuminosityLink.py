import re
import hashlib
from base64 import b64decode
from Crypto.Cipher import AES

def config(raw_data):
    try:
        re_pattern = '[a-zA-Z0-9+/]{60,}={0,2}'
        conf_string = re.findall(re_pattern, raw_data)[0]
        decoded = decrypt_string('Specify a Password', conf_string)
        config_dict = parse_config(decoded.split('|'))

        if config_dict["BackUp Domain"] == 'Disabled':
            return [config_dict, [config_dict["Domain"]]]
        else:
            return config_dict

    except Exception as e:
        return False
        
        
#Helper Functions Go Here
def decrypt_string(key_string, coded):
    try:
        # Derive key
        key_hash = hashlib.md5(key_string).hexdigest()
        aes_key = key_hash[:30]+key_hash+'00'
        #Crypto
        cipher = AES.new(aes_key.decode('hex'))
        return cipher.decrypt(b64decode(coded))
    except:
        return False
    
#Turn the strings in to a python config_dict
def parse_config(string_list):
    return {
        "Domain": string_list[0],
        "Port": string_list[1],
        "BackUp Domain": string_list[2],
        "Install Name": string_list[3],
        "Startup Name": string_list[4],
        "Campaign ID": string_list[5],
    }

