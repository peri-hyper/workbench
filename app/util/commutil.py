import hashlib


class CommUtil(object):
    def get_md5(input_string):
        md5_hash = hashlib.md5(input_string.encode('utf-8'))
        return md5_hash.hexdigest()


if __name__ == '__main__':
    input_string = "Hello World"
    print(CommUtil.get_md5(input_string))